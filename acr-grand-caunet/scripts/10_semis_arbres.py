"""Étape 10 - Semis des arbres : position, essence et hauteur de chaque arbre du couloir.

Entrées : data/raw/mns_lidarhd_50cm.tif, mnt_lidarhd_50cm.tif (LiDAR HD, 0,5 m),
          data/raw/ortho_irc_20cm.tif, ortho_20cm.tif (BD ORTHO IRC et RVB, 20 cm),
          data/processed/chaussee_precise.csv, data/processed/couloir/*.geojson (BD Forêt V2,
          BD TOPO : bâtiments, haies, zones de végétation),
          data/reference/catalogue_jeu_25170642.txt.gz (noms des éléments du jeu)
Sorties : data/processed/arbres.csv(.gz)     un arbre par ligne (houppier > 2 m)
          data/processed/arbustes.csv(.gz)   couche « arbustes / garrigue » (0,4 à 2 m), semée
          data/processed/semis_resume.json   comptages, contrôles, table de correspondance jeu
          figures/phase4/semis_planche_ortho.png, semis_synthese.png
          modele/apercu/arbres.glb           aperçu 3D des arbres à moins de 40 m de l'axe

Méthode
  1. Modèle de hauteur du couvert MNH = MNS - MNT (0,5 m), lissé (gaussien, sigma 0,5 m).
  2. Apex = maxima locaux du MNH lissé dans un disque dont le rayon croît avec la hauteur
     (r = 0,5 + 0,15 h, borné à 1-3 m), au-dessus de 2 m ; plateaux ramenés à un point.
     Exclusions : chaussée (ruban bord gauche - bord droit + 0,5 m), bâtiments BD TOPO + 2 m.
     Pas de ligne électrique dans le couloir (la seule ligne BD TOPO est à 15 km).
  3. Houppiers : segmentation par ligne de partage des eaux (scikit-image) du MNH lissé,
     marqueurs = apex, limitée aux pixels > 2 m, à ceux qui dépassent 40 % de la hauteur de
     l'apex et à un rayon maximal 1 + 0,45 h ; diamètre = diamètre du disque de même surface.
     Rejet des « arbres » sans chlorophylle (NDVI moyen du houppier < 0,08 : rochers, murs,
     toits non cadastrés) et des pointes isolées (houppier < 1 m²).
  4. Essence : tirage pondéré selon le type de formation BD Forêt qui contient l'apex
     (table FORMATIONS), modulé par la hauteur ; règles par défaut hors polygone.
     C'est une attribution STATISTIQUE : la donnée ne permet pas d'identifier un arbre.
  5. Arbustes : chaque pixel de végétation basse (MNH 0,4-2 m et NDVI > 0,12) porte un
     arbuste avec une probabilité 0,25 m² / surface moyenne d'un arbuste, modulée par le
     NDVI ; densité juste à l'échelle de quelques mètres, position individuelle fictive.
"""
import csv
import gzip
import json
import math
from collections import Counter, defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import rasterio
import shapely
from matplotlib.patches import Circle
from matplotlib.lines import Line2D
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.windows import from_bounds
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Polygon, shape
from skimage.segmentation import watershed

from acr_geo import FIG, OUT, RAW, REF, ROOT, TO_L93, l93

SEED = 20261111
BANDE = 135.0               # m de part et d'autre de l'axe (emprise du modèle 3D : 130 m)
H_ARBRE = 2.0               # m : seuil arbre / arbuste
H_ARBUSTE = 0.4             # m : seuil bas des arbustes
MARGE_CHAUSSEE = 0.5        # m autour du ruban de chaussée
MARGE_BATI = 2.0            # m autour des emprises BD TOPO
NDVI_ARBRE = 0.08           # NDVI moyen minimal d'un houppier
NDVI_ARBUSTE = 0.12         # NDVI minimal d'un pixel d'arbuste
GLB_DIST = 40.0             # m : aperçu 3D
RES = 0.5
FIG4 = FIG / "phase4"
CATALOGUE = REF / "catalogue_jeu_25170642.txt.gz"

# --- Essences et proportions par type de formation BD Forêt V2 ---------------------------
# Définitions BD Forêt : « pur » = l'essence fait au moins 75 % du couvert libre ;
# « mélange de X prépondérants et Y » = X entre 50 et 75 % ; « forêt ouverte » = couvert
# arboré 10-40 % ; « lande » = couvert arboré < 10 %, ligneux bas dominants.
# Les proportions ci-dessous sont des hypothèses régionales (massif calcaire provençal :
# pin d'Alep, chêne vert, un peu de chêne pubescent), pas des mesures. Elles sont ensuite
# modulées par la hauteur (MOD_HAUTEUR) : les conifères sont favorisés au-dessus de 8 m,
# les feuillus en dessous (le chêne vert dépasse rarement 10-12 m ici, le pin d'Alep 20 m).
ESSENCES = {   # code : (nom, groupe, couleur des figures)
    "pin_alep": ("pin d'Alep", "conifere", "#2a78d6"),
    "chene_vert": ("chêne vert", "feuillu", "#eb6834"),
    "chene_pubescent": ("chêne pubescent", "feuillu", "#9b5de5"),
    "autre_pin": ("autre pin (pignon ou maritime)", "conifere", "#00a6a6"),
    "cypres": ("cyprès", "conifere", "#1b4332"),
    "olivier": ("olivier", "feuillu", "#d4a017"),
}
FORMATIONS = {
    "Forêt fermée de pin d'Alep pur": {"pin_alep": .85, "chene_vert": .13, "chene_pubescent": .02},
    "Forêt fermée de chênes sempervirents purs": {"chene_vert": .85, "pin_alep": .12, "chene_pubescent": .03},
    "Forêt fermée d'un autre pin pur": {"autre_pin": .80, "pin_alep": .15, "chene_vert": .05},
    "Forêt fermée à mélange de feuillus prépondérants et conifères":
        {"chene_vert": .50, "chene_pubescent": .12, "pin_alep": .38},
    "Forêt fermée à mélange de conifères prépondérants et feuillus":
        {"pin_alep": .62, "chene_vert": .30, "chene_pubescent": .08},
    "Forêt fermée à mélange de feuillus": {"chene_vert": .60, "chene_pubescent": .40},
    "Forêt ouverte de feuillus purs": {"chene_vert": .75, "chene_pubescent": .25},
    "Forêt ouverte de conifères purs": {"pin_alep": .88, "autre_pin": .04, "chene_vert": .08},
    "Forêt ouverte à mélange de feuillus et conifères": {"pin_alep": .45, "chene_vert": .45, "chene_pubescent": .10},
    "Lande": {"pin_alep": .50, "chene_vert": .50},
    # règles par défaut, hors polygone BD Forêt (dans l'ordre de priorité)
    "hors forêt : haie (BD TOPO, 4 m)": {"cypres": .40, "chene_vert": .25, "pin_alep": .25, "chene_pubescent": .10},
    "hors forêt : abords bâtis (< 40 m)": {"pin_alep": .35, "cypres": .25, "chene_vert": .20, "olivier": .20},
    "hors forêt : autre": {"pin_alep": .55, "chene_vert": .40, "chene_pubescent": .05},
}


def mod_hauteur(groupe, h):
    """Multiplicateur de poids : 0,4 à 1,6, bascule autour de 8 m."""
    s = 1.0 / (1.0 + np.exp(-(h - 8.0) / 2.0))
    return 0.4 + 1.2 * (s if groupe == "conifere" else 1.0 - s)


# --- Correspondance essence -> éléments du jeu (dossiers acr/Content/Foliage/...) ---------
# Les noms de maillages sont relus dans le catalogue ; aucun n'est écrit à la main.
JEU = {
    "pin_alep": [("Trees/AleppoPine", 0, 99, "même essence")],
    "chene_vert": [("Trees/Smoketree", 0, 6, "SUBSTITUT A ARBITRER : petits chênes verts (taillis)"),
                   ("Trees/BlackmapleMonteCarlo", 6, 99, "SUBSTITUT A ARBITRER : chênes verts > 6 m")],
    "chene_pubescent": [("Trees/Blackmaple", 0, 99, "substitut : feuillu caduc à houppier arrondi")],
    "autre_pin": [("Trees/BlackpineMonteCarlo", 0, 99, "pin noir, habillage Monte-Carlo")],
    "cypres": [("Trees/Cypress", 0, 99, "même essence (cyprès d'ornement)")],
    "olivier": [("Trees/Olivetree", 0, 99, "même essence")],
    "arbuste": [("GroundCover/BroomCreeper", 0, 1.0, "genêt rampant : arbustes < 1 m"),
                ("Trees/Boxthorn", 1.0, 99, "lyciet : arbustes de garrigue 1-2 m")],
}
SUBSTITUT_CHENE_VERT = {
    "probleme": "le catalogue n'a aucun chêne (ni Quercus, ni Oak, ni Holm) : le chêne vert, 2e essence du couloir, n'a pas d'équivalent",
    "proposition": "Smoketree (arbre à perruque, Cotinus) sous 6 m, BlackmapleMonteCarlo au-dessus",
    "justification": ["feuillus à houppier dense et arrondi, sans tronc dégagé, comme le chêne vert en taillis",
                      "Cotinus est une essence de la garrigue provençale, de la taille des taillis de chêne vert",
                      "la variante MonteCarlo de l'érable a été habillée par le studio pour les spéciales de "
                      "Haute-Provence, la plus proche de notre palette de couleurs"],
    "alternative": "Olivetree : persistant et méditerranéen, mais feuillage gris argenté et tronc d'arbre de verger",
    "defaut": "les deux sont caducs dans la réalité ; si le jeu les montre en livrée automnale ou dénudée, "
              "l'olivier devient préférable",
    "a_arbitrer": "directeur : choix sur rendu dans l'éditeur, les maillages n'ayant pas été vus (noms seulement)",
}

INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
HALO = [pe.withStroke(linewidth=2.5, foreground="white")]
plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "figure.facecolor": SURFACE,
                     "axes.facecolor": SURFACE, "axes.spines.top": False, "axes.spines.right": False})


# --- données -------------------------------------------------------------------------------
def norm_tfv(s):
    return (s or "?").replace("\x92", "'").replace("’", "'").strip()


def couche(name):
    """Géométries Lambert-93 et propriétés d'une couche du couloir (WGS84 sur disque)."""
    path = OUT / "couloir" / f"{name}.geojson"
    if not path.exists():
        return []
    out = []
    for f in json.loads(path.read_text(encoding="utf-8"))["features"]:
        if f.get("geometry"):
            g = shapely.transform(shapely.force_2d(shape(f["geometry"])),
                                  lambda c: np.column_stack(TO_L93.transform(c[:, 0], c[:, 1])))
            out.append((g if g.is_valid else g.buffer(0), f["properties"]))
    return out


def chaussee():
    with open(OUT / "chaussee_precise.csv") as f:
        rows = list(csv.DictReader(f))
    g = lambda *k: np.array([[float(r[c]) for c in k] for r in rows])   # noqa: E731
    return {"pk": g("pk_m")[:, 0], "A": g("x_axe", "y_axe"), "G": g("x_gauche", "y_gauche"),
            "D": g("x_droite", "y_droite")}


def ruban(ch):
    """Chaussée : quadrilatères bord gauche / bord droit entre deux points successifs."""
    G, D = ch["G"], ch["D"]
    quads = shapely.polygons([np.array([G[i], G[i + 1], D[i + 1], D[i], G[i]]) for i in range(len(G) - 1)])
    return shapely.union_all(shapely.make_valid(quads))


def catalogue_jeu():
    """{dossier relatif à Foliage : [maillages SM_...]} lus dans le catalogue."""
    fam = defaultdict(list)
    with gzip.open(CATALOGUE, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("acr/Content/Foliage/") and line.endswith(".uasset"):
                d, name = line[len("acr/Content/Foliage/"):-len(".uasset")].rsplit("/", 1)
                if name.startswith("SM_"):
                    fam[d].append(name)
    return {k: sorted(v) for k, v in fam.items()}


class Grille:
    """Rasters LiDAR et ortho ramenés à la grille 0,5 m du MNS."""

    def __init__(self):
        with rasterio.open(RAW / "mns_lidarhd_50cm.tif") as a, rasterio.open(RAW / "mnt_lidarhd_50cm.tif") as b:
            mns, self.mnt = a.read(1), b.read(1)
            self.tr, self.shape, self.crs = a.transform, a.shape, a.crs
        self.valid = (mns > -1000) & (self.mnt > -1000)
        self.h = np.where(self.valid, mns - self.mnt, 0).astype(np.float32)
        del mns
        np.clip(self.h, 0, 40, out=self.h)
        self.hs = ndi.gaussian_filter(self.h, 1.0).astype(np.float32)      # sigma 1 px = 0,5 m
        self.hs[~self.valid] = 0
        self.ndvi = self._ndvi()

    def _ndvi(self):
        """NDVI (PIR-R)/(PIR+R) de l'ortho IRC moyennée à 0,5 m ; là où l'IRC manque (dalles
        non téléchargées, > 100 m de l'axe), indice vert-rouge de l'ortho RVB recalé."""
        shp = (3, *self.shape)
        with rasterio.open(RAW / "ortho_irc_20cm.tif") as s:
            irc = s.read(out_shape=shp, resampling=Resampling.average).astype(np.float32)
        with rasterio.open(RAW / "ortho_20cm.tif") as s:
            rgb = s.read(out_shape=shp, resampling=Resampling.average).astype(np.float32)
        has_irc = irc.sum(0) > 0
        nd = (irc[0] - irc[1]) / (irc[0] + irc[1] + 1e-6)
        gr = (rgb[1] - rgb[0]) / (rgb[1] + rgb[0] + 1e-6)
        both = has_irc & self.valid & (rgb.sum(0) > 0)
        a, b = np.polyfit(gr[both][::50], nd[both][::50], 1)              # recalage linéaire
        self.has_irc = has_irc
        self.recalage_rvb = (round(float(a), 3), round(float(b), 3),
                             round(float(np.corrcoef(gr[both][::50], nd[both][::50])[0, 1]), 2))
        return np.where(has_irc, nd, a * gr + b).astype(np.float32)

    def burn(self, geoms, dtype=np.uint8):
        """Rastérise des géométries (valeur 1) ou des couples (géométrie, valeur)."""
        geoms = [g if isinstance(g, tuple) else (g, 1) for g in geoms]
        geoms = [(g, v) for g, v in geoms if g is not None and not g.is_empty]
        if not geoms:
            return np.zeros(self.shape, dtype)
        return rasterize(geoms, out_shape=self.shape, transform=self.tr, fill=0, dtype=dtype, all_touched=False)

    def xy(self, r, c):
        return self.tr.c + (np.asarray(c) + 0.5) * RES, self.tr.f - (np.asarray(r) + 0.5) * RES

    def rc(self, x, y):
        return ((self.tr.f - np.asarray(y)) / RES).astype(int), ((np.asarray(x) - self.tr.c) / RES).astype(int)


# --- détection ------------------------------------------------------------------------------
def disque(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r + 0.5


def rayon_fenetre(h):
    return np.clip(0.5 + 0.15 * h, 1.0, 3.0)            # m


def apex(hs, cand):
    """Maxima locaux à fenêtre variable : un pixel candidat est apex s'il est le plus haut du
    disque de rayon rayon_fenetre(h) qui l'entoure."""
    rpx = np.rint(rayon_fenetre(hs) / RES).astype(np.int8)
    cand = cand & (hs >= H_ARBRE)
    seed = np.zeros(hs.shape, bool)
    for r in range(int(rpx[cand].min()), int(rpx[cand].max()) + 1):
        sel = cand & (rpx == r)
        if sel.any():
            seed |= sel & (hs >= ndi.maximum_filter(hs, footprint=disque(r)))
    lab, n = ndi.label(seed, structure=np.ones((3, 3)))            # plateaux -> un point
    rc = np.rint(np.array(ndi.center_of_mass(seed, lab, range(1, n + 1)))).astype(int).reshape(-1, 2)
    return rc[seed[rc[:, 0], rc[:, 1]]]


def houppiers(G, rc, mask):
    """Ligne de partage des eaux du MNH lissé à partir des apex, puis contraintes :
    pixel > 40 % de la hauteur de l'apex et à moins de 1 + 0,45 h de l'apex."""
    markers = np.zeros(G.shape, np.int32)
    markers[rc[:, 0], rc[:, 1]] = np.arange(1, len(rc) + 1)
    lab = watershed(-G.hs, markers, mask=mask)
    happ = np.concatenate([[0], G.hs[rc[:, 0], rc[:, 1]]])
    ok = lab > 0
    ok[ok] = G.hs[ok] >= 0.4 * happ[lab[ok]]
    rr, cc = np.nonzero(ok)
    li = lab[rr, cc]
    d = np.hypot(rr - rc[li - 1, 0], cc - rc[li - 1, 1]) * RES
    far = d > 1.0 + 0.45 * happ[li]
    ok[rr[far], cc[far]] = False
    lab[~ok] = 0
    return lab


def detecte(G, ch, axis):
    """Apex, houppiers et filtres. Deux passes : la seconde cherche des apex dans le couvert
    > 2 m resté hors de tout houppier (taillis jointifs, flancs de gros houppiers).
    Un apex au-dessus de la chaussée (houppier en surplomb) n'est gardé que s'il est
    chlorophyllien et à moins de 2,5 m du bord ; son tronc est reporté au bord + 0,8 m."""
    bande = G.burn([axis.buffer(BANDE)]).astype(bool)
    rb = ruban(ch)
    route = G.burn([rb.buffer(MARGE_CHAUSSEE)]).astype(bool)
    coeur = G.burn([rb.buffer(-2.5)]).astype(bool)
    bats = [g for g, _ in couche("batiment")]
    bati = G.burn([g.buffer(MARGE_BATI) for g in bats]).astype(bool)
    pousse = (G.hs >= H_ARBRE) & G.valid & ~bati & ~(route & (G.ndvi < NDVI_ARBRE))   # croissance des houppiers
    cand = bande & G.valid & ~bati & ~coeur & ~(route & (G.ndvi < 0.15))
    rc1 = apex(G.hs, cand)
    lab = houppiers(G, rc1, pousse)
    reste = ndi.binary_opening(cand & pousse & (lab == 0), structure=disque(2))   # sans les liserés < 2 m
    rc2 = apex(np.where(reste, G.hs, 0).astype(np.float32), reste)
    rc = np.vstack([rc1, rc2])
    origine = np.r_[np.zeros(len(rc1), int), np.ones(len(rc2), int)]
    lab = houppiers(G, rc, pousse)
    n = len(rc)
    idx = np.arange(1, n + 1)
    area = ndi.sum_labels(np.ones(G.shape, np.float32), lab, idx) * RES * RES
    ndv = ndi.mean(G.ndvi, lab, idx)
    amin = np.where(origine == 0, 1.0, 3.0)                       # m² : pointe isolée / fragment
    keep = (area >= amin) & (ndv >= NDVI_ARBRE)
    rejets = {"apex_passe_1": int(len(rc1)), "apex_passe_2_couvert_restant": int(len(rc2)),
              "houppier_trop_petit_1m2_ou_3m2_en_passe_2": int((area < amin).sum()),
              "sans_chlorophylle_ndvi": int(((area >= amin) & (ndv < NDVI_ARBRE)).sum())}
    rej_xy = np.column_stack(G.xy(rc[~keep, 0], rc[~keep, 1]))
    remap = np.zeros(n + 1, np.int32)                              # renumérote les houppiers gardés
    remap[idx[keep]] = np.arange(1, keep.sum() + 1)
    lab = remap[lab]
    rc, area, origine = rc[keep], area[keep], origine[keep]
    x, y = G.xy(rc[:, 0], rc[:, 1])
    sur = route[rc[:, 0], rc[:, 1]]
    bord = rb.buffer(MARGE_CHAUSSEE + 0.3).exterior if rb.geom_type == "Polygon" else rb.buffer(0.8).boundary
    for i in np.flatnonzero(sur):                                  # tronc reporté au bord
        q = bord.interpolate(bord.project(shapely.Point(x[i], y[i])))
        x[i], y[i] = q.x, q.y
    rejets["apex_au_dessus_de_la_chaussee_tronc_reporte_au_bord"] = int(sur.sum())
    masks = {"bande": bande, "route": route, "bati": bati, "batiments": bats, "rejets_xy": rej_xy}
    return x, y, rc, area, origine, lab, masks, rejets


# --- essences --------------------------------------------------------------------------------
def zones_essence(G, axis):
    """Raster d'index de règle : formations BD Forêt, puis règles par défaut."""
    noms = list(FORMATIONS)
    z = np.zeros(G.shape, np.uint8)
    hors = len(noms)  # index 1-based des règles par défaut
    k_haie, k_bati, k_autre = noms.index("hors forêt : haie (BD TOPO, 4 m)") + 1, \
        noms.index("hors forêt : abords bâtis (< 40 m)") + 1, noms.index("hors forêt : autre") + 1
    z[:] = k_autre
    near = G.burn([g.buffer(40) for g, _ in couche("batiment")]).astype(bool)
    z[near] = k_bati
    haies = [g.buffer(4) for g, _ in couche("haie")]
    haies += [g for g, p in couche("zone_de_vegetation") if p.get("nature") == "Haie"]
    z[G.burn(haies).astype(bool)] = k_haie
    inconnus = Counter()
    pairs = []
    for g, p in couche("bdforet_formation_vegetale"):
        t = norm_tfv(p.get("tfv"))
        if t not in FORMATIONS:
            inconnus[t] += 1
            continue
        pairs.append((g, noms.index(t) + 1))
    zf = G.burn(pairs)
    z = np.where(zf > 0, zf, z)
    assert hors == len(noms)
    return z, noms, dict(inconnus)


def tirage(rng, regle, h):
    w = {e: p * mod_hauteur(ESSENCES[e][1], h) for e, p in FORMATIONS[regle].items()}
    k = list(w)
    p = np.array([w[e] for e in k])
    return k[rng.choice(len(k), p=p / p.sum())]


def famille(fams, code, h):
    for d, lo, hi, _ in JEU[code]:
        if lo <= h < hi:
            return d, fams[d]
    d = JEU[code][-1][0]
    return d, fams[d]


# --- géométrie axe ----------------------------------------------------------------------------
def reperes_axe(ch, axis, x, y):
    tree = cKDTree(ch["A"])
    _, i = tree.query(np.column_stack([x, y]))
    i = np.clip(i, 1, len(ch["A"]) - 2)
    t = ch["A"][i + 1] - ch["A"][i - 1]
    v = np.column_stack([x, y]) - ch["A"][i]
    side = np.where(t[:, 0] * v[:, 1] - t[:, 1] * v[:, 0] > 0, "gauche", "droite")
    dist = shapely.distance(shapely.points(x, y), axis)
    return ch["pk"][i], dist, side


def ecrire_csv(path, header, rows):
    """CSV, compressé en .csv.gz s'il dépasse ~8 Mo."""
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    data = buf.getvalue().encode("utf-8")
    for p in (path, path.with_suffix(".csv.gz")):
        if p.exists():
            p.unlink()
    if len(data) > 8e6:
        path = path.with_suffix(".csv.gz")
        with gzip.open(path, "wb", compresslevel=9) as f:
            f.write(data)
    else:
        path.write_bytes(data)
    return path


# --- arbustes ---------------------------------------------------------------------------------
def arbustes(G, rng, masks, lab):
    """Arbustes semés : pixels de végétation basse, probabilité ∝ surface / surface moyenne."""
    d_moy = 1.4                                    # m : diamètre moyen d'un arbuste
    a_moy = math.pi * (d_moy / 2) ** 2
    low = (G.h >= H_ARBUSTE) & (G.h < H_ARBRE) & G.valid & masks["bande"] & ~masks["route"] & ~masks["bati"]
    low &= (G.ndvi >= NDVI_ARBUSTE) & (lab == 0)
    rr, cc = np.nonzero(low)
    ndv = G.ndvi[rr, cc]
    p = RES * RES / a_moy * np.clip((ndv - NDVI_ARBUSTE) / 0.15, 0.3, 1.0)
    pick = rng.random(len(rr)) < p
    rr, cc = rr[pick], cc[pick]
    x, y = G.xy(rr, cc)
    x = x + rng.uniform(-RES / 2, RES / 2, len(x))
    y = y + rng.uniform(-RES / 2, RES / 2, len(y))
    h = np.clip(G.h[rr, cc], H_ARBUSTE, H_ARBRE)
    d = np.clip(0.6 + 0.6 * h + rng.normal(0, 0.2, len(h)), 0.5, 2.5)
    return x, y, G.mnt[rr, cc], h, d, int(low.sum())


# --- figures ----------------------------------------------------------------------------------
def ortho_rgb(x0, y0, x1, y1):
    with rasterio.open(RAW / "ortho_20cm.tif") as s:
        w = from_bounds(x0, y0, x1, y1, s.transform)
        return np.moveaxis(s.read(window=w), 0, -1)


def choisir_extraits(T, S, ch):
    """Centres des six extraits de 60 m."""
    out = []
    tree = cKDTree(np.column_stack([T["x"], T["y"]]))
    dens = np.array([len(v) for v in tree.query_ball_point(np.column_stack([T["x"], T["y"]]), 25)])

    def best(sel, score):
        i = np.flatnonzero(sel)
        return i[np.argmax(score[i])]

    near = (T["dist"] > 25) & (T["dist"] < 60)
    i = best(near & (T["regle"] == "Forêt fermée de pin d'Alep pur"), dens)
    out.append(("Pinède dense (pin d'Alep pur)", T["x"][i], T["y"][i]))
    i = best(near & (T["regle"] == "Forêt fermée de chênes sempervirents purs"), dens)
    out.append(("Chênaie verte (chênes sempervirents)", T["x"][i], T["y"][i]))
    sx, sy = S
    st = cKDTree(np.column_stack([sx, sy]))
    li = np.flatnonzero(near & (T["regle"] == "Lande"))
    dl = np.array([len(v) for v in st.query_ball_point(np.column_stack([T["x"][li], T["y"][li]]), 25)])
    i = li[np.argmax(dl)] if len(li) else 0
    out.append(("Lande / garrigue", T["x"][i], T["y"][i]))
    with open(OUT / "virages_es.csv") as f:
        v = [r for r in csv.DictReader(f) if r["categorie"] == "épingle" and r["dans_es"] == "True"]
    k = float(v[0]["pk_corde_m"]) if v else 2215
    j = int(np.argmin(np.abs(ch["pk"] - k)))
    out.append((f"Bord de route en virage (épingle, PK {k:.0f})", *ch["A"][j]))
    # zone ouverte de la D1 : PK 3700-6700, minimum de couvert à moins de 30 m
    kk = np.arange(3700, 6700, 20)
    cnt = []
    for k2 in kk:
        j = int(np.argmin(np.abs(ch["pk"] - k2)))
        cnt.append(len(tree.query_ball_point(ch["A"][j], 30)))
    k2 = kk[int(np.argmin(cnt))]
    j = int(np.argmin(np.abs(ch["pk"] - k2)))
    out.append((f"Zone ouverte de la D1 (PK {k2:.0f})", *ch["A"][j]))
    with open(OUT / "ouvrages_es.csv") as f:
        b = max((r for r in csv.DictReader(f) if r["dans_es"] == "True"), key=lambda r: float(r["longueur_bdtopo_m"]))
    bx, by = l93(float(b["lon"]), float(b["lat"]))
    out.append((f"Abords d'un pont (PK {b['pk_debut_m']}-{b['pk_fin_m']}, {float(b['longueur_bdtopo_m']):.0f} m)", bx, by))
    return out


def planche(T, S, ch, extraits, path, half=30.0, ncol=3, dpi=100):
    nrow = math.ceil(len(extraits) / ncol)
    fig, axs = plt.subplots(nrow, ncol, figsize=(4.6 * ncol, 5.1 * nrow + 0.6), gridspec_kw={"hspace": 0.22, "wspace": 0.04})
    tree = cKDTree(np.column_stack([T["x"], T["y"]]))
    st = cKDTree(np.column_stack(S[:2]))
    for ax, (titre, cx, cy) in zip(np.ravel(axs), extraits):
        x0, y0, x1, y1 = (round(v * 5) / 5 for v in (cx - half, cy - half, cx + half, cy + half))
        ax.imshow(ortho_rgb(x0, y0, x1, y1), extent=(x0, x1, y0, y1), interpolation="bilinear")
        for k in (["G", "D"]):
            sel = (np.abs(ch[k][:, 0] - cx) < half + 5) & (np.abs(ch[k][:, 1] - cy) < half + 5)
            if sel.any():
                ax.plot(ch[k][sel, 0], ch[k][sel, 1], ".", ms=1.2, color="white", alpha=0.8)
        for i in tree.query_ball_point([cx, cy], half * 1.5):
            ax.add_patch(Circle((T["x"][i], T["y"][i]), T["d"][i] / 2, fill=False, lw=1.0,
                                ec=ESSENCES[T["ess"][i]][2]))
            ax.plot(T["x"][i], T["y"][i], "+", ms=3, mew=0.8, color=ESSENCES[T["ess"][i]][2])
        js = st.query_ball_point([cx, cy], half * 1.5)
        ax.plot(S[0][js], S[1][js], "o", ms=1.6, mfc="#ffd400", mec="none", alpha=0.9)
        n = sum(1 for i in tree.query_ball_point([cx, cy], half * 1.5)
                if abs(T["x"][i] - cx) < half and abs(T["y"][i] - cy) < half)
        ax.set_xlim(x0, x1), ax.set_ylim(y0, y1)
        ax.set_xticks([]), ax.set_yticks([])
        ax.set_title(f"{titre}\n{n} arbres détectés sur 60 m x 60 m", loc="left", fontsize=9, color=INK)
        ax.plot([x0 + 3, x0 + 13], [y0 + 3, y0 + 3], color="white", lw=4)
        ax.plot([x0 + 3, x0 + 13], [y0 + 3, y0 + 3], color=INK, lw=2)
        ax.text(x0 + 8, y0 + 4.5, "10 m", ha="center", fontsize=8, color=INK, path_effects=HALO)
    for ax in np.ravel(axs)[len(extraits):]:
        ax.set_axis_off()
    present = [e for e in ESSENCES if (T["ess"] == e).any()]
    hand = [Line2D([], [], marker="o", ls="", mfc="none", mec=ESSENCES[e][2], mew=1.5, ms=9, label=ESSENCES[e][0])
            for e in present]
    hand.append(Line2D([], [], marker="o", ls="", mfc="#ffd400", mec="none", ms=4, label="arbuste semé (0,4-2 m)"))
    hand.append(Line2D([], [], marker=".", ls="", color="#9a9a9a", ms=5, label="bords de chaussée"))
    fig.legend(handles=hand, loc="lower center", ncol=len(hand), frameon=False, fontsize=9)
    fig.suptitle("Semis des arbres - BD ORTHO 20 cm (IGN) ; cercle = houppier segmenté dans le LiDAR HD, "
                 "couleur = essence attribuée (statistique, d'après BD Forêt)", x=0.01, ha="left", color=INK, fontsize=11)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.91, bottom=0.05)
    fig.savefig(path, dpi=dpi)
    plt.close(fig)


def synthese(T, path):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6), width_ratios=[1, 1.5])
    codes = sorted(ESSENCES, key=lambda e: -(T["ess"] == e).sum())
    codes = [e for e in codes if (T["ess"] == e).any()]
    n = np.array([(T["ess"] == e).sum() for e in codes])
    y = np.arange(len(codes))[::-1]
    a1.barh(y, n, color=[ESSENCES[e][2] for e in codes], height=0.65)
    for yi, ni in zip(y, n):
        a1.text(ni, yi, f"  {ni:,} ({ni / n.sum() * 100:.0f} %)".replace(",", " "), va="center", color=INK, fontsize=8)
    a1.set_yticks(y, [ESSENCES[e][0] for e in codes])
    a1.set_xlim(0, n.max() * 1.35)
    a1.set_xlabel("nombre d'arbres (houppier > 2 m)")
    a1.set_title(f"Répartition par essence attribuée ({n.sum():,} arbres)".replace(",", " "), loc="left", color=INK)
    a1.grid(axis="x", color=GRID, lw=0.8)
    bins = np.arange(2, 27, 1)
    bottom = np.zeros(len(bins) - 1)
    for e in codes:
        c, _ = np.histogram(T["h"][T["ess"] == e], bins)
        a2.bar(bins[:-1], c, width=0.9, align="edge", bottom=bottom, color=ESSENCES[e][2], label=ESSENCES[e][0])
        bottom += c
    med = np.median(T["h"])
    a2.axvline(med, color=INK, lw=1, ls=(0, (3, 2)))
    a2.annotate(f"médiane {med:.1f} m", (med, bottom.max() * 0.95), xytext=(5, 0), textcoords="offset points", color=INK)
    a2.set_xlabel("hauteur de l'arbre (m, MNH LiDAR lissé à l'apex)")
    a2.set_ylabel("arbres")
    a2.legend(frameon=False, fontsize=8)
    a2.grid(axis="y", color=GRID, lw=0.8)
    a2.set_title("Distribution des hauteurs", loc="left", color=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


# --- aperçu 3D ----------------------------------------------------------------------------------
def glb_arbres(T, path):
    """Cône (conifères) ou octaèdre étiré (feuillus) + tronc triangulaire, une maille par essence,
    positions et normales seulement. Repère de modele/repere.json."""
    ref = json.loads((ROOT / "modele" / "repere.json").read_text(encoding="utf-8"))
    sel = T["dist"] <= GLB_DIST
    gl = {"asset": {"version": "2.0", "generator": "acr-grand-caunet 10_semis_arbres.py"}, "scene": 0,
          "scenes": [{"nodes": []}], "nodes": [], "meshes": [], "accessors": [], "bufferViews": [],
          "materials": [], "buffers": []}
    blob = bytearray()

    def acc(arr, kind, target, minmax=False):
        while len(blob) % 4:
            blob.append(0)
        gl["bufferViews"].append({"buffer": 0, "byteOffset": len(blob), "byteLength": arr.nbytes, "target": target})
        blob.extend(arr.tobytes())
        a = {"bufferView": len(gl["bufferViews"]) - 1, "componentType": 5126 if arr.dtype == np.float32 else 5125,
             "count": int(arr.size // {"VEC3": 3, "SCALAR": 1}[kind]), "type": kind}
        if minmax:
            a["min"], a["max"] = arr.min(0).tolist(), arr.max(0).tolist()
        gl["accessors"].append(a)
        return len(gl["accessors"]) - 1

    ang = np.linspace(0, 2 * np.pi, 6, endpoint=False)
    ta = np.linspace(0, 2 * np.pi, 3, endpoint=False)

    def gabarit(groupe):
        """Sommets (ux, uy, rayon houppier ?, a, b) avec z = sol + a * base_houppier + b * (h - base),
        triangles orientés vers l'extérieur (est, nord, haut)."""
        V = [(math.cos(t), math.sin(t), 0, 0, 0) for t in ta] + [(math.cos(t), math.sin(t), 0, 1, 0) for t in ta]
        F = []
        for k in range(3):
            F += [(k, (k + 1) % 3, 3 + k), ((k + 1) % 3, 3 + (k + 1) % 3, 3 + k)]
        b_ring = 0.0 if groupe == "conifere" else 0.45
        V += [(math.cos(t), math.sin(t), 1, 1, b_ring) for t in ang] + [(0, 0, 0, 1, 1), (0, 0, 0, 1, 0)]
        for k in range(6):
            F += [(6 + k, 6 + (k + 1) % 6, 12), (6 + (k + 1) % 6, 6 + k, 13)]
        return np.array(V, np.float64), np.array(F, np.uint32)

    for e in ESSENCES:
        m = sel & (T["ess"] == e)
        if not m.any():
            continue
        V0, F0 = gabarit(ESSENCES[e][1])
        x, y, z, h, d = (T[k][m][:, None] for k in ("x", "y", "z", "h", "d"))
        cb = (0.35 if ESSENCES[e][1] == "conifere" else 0.2) * h      # base du houppier
        rad = np.where(V0[:, 2][None] > 0, d / 2, np.maximum(0.08, 0.025 * h))
        X = x + V0[:, 0][None] * rad
        Y = y + V0[:, 1][None] * rad
        Zs = z + V0[:, 3][None] * cb + V0[:, 4][None] * (h - cb)
        pos = np.column_stack([X.ravel() - ref["x0"], Zs.ravel() - ref["z0"], -(Y.ravel() - ref["y0"])]).astype(np.float32)
        F = (F0[None] + (np.arange(m.sum()) * len(V0))[:, None, None].astype(np.uint32)).reshape(-1, 3)
        nrm = np.zeros(pos.shape, np.float64)
        tri = pos[F].astype(np.float64)
        fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        for k in range(3):
            np.add.at(nrm, F[:, k], fn)
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
        col = matplotlib.colors.to_rgb(ESSENCES[e][2])
        gl["materials"].append({"name": e, "pbrMetallicRoughness": {"baseColorFactor": [*col, 1.0],
                                "metallicFactor": 0.0, "roughnessFactor": 0.9}})
        prim = {"attributes": {"POSITION": acc(pos, "VEC3", 34962, True), "NORMAL": acc(nrm.astype(np.float32), "VEC3", 34962)},
                "indices": acc(F.astype(np.uint32).ravel(), "SCALAR", 34963), "material": len(gl["materials"]) - 1, "mode": 4}
        gl["meshes"].append({"name": f"arbres_{e}", "primitives": [prim]})
        gl["nodes"].append({"name": f"arbres_{e}", "mesh": len(gl["meshes"]) - 1})
        gl["scenes"][0]["nodes"].append(len(gl["nodes"]) - 1)
    while len(blob) % 4:
        blob.append(0)
    gl["buffers"].append({"byteLength": len(blob)})
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    with open(path, "wb") as f:
        f.write(b"glTF" + np.array([2, 28 + len(js) + len(blob)], "<u4").tobytes())
        f.write(np.array([len(js), 0x4E4F534A], "<u4").tobytes() + js)
        f.write(np.array([len(blob), 0x004E4942], "<u4").tobytes() + bytes(blob))
    return int(sel.sum())


# --- principal ------------------------------------------------------------------------------------
def main():
    rng = np.random.default_rng(SEED)
    FIG4.mkdir(parents=True, exist_ok=True)
    fams = catalogue_jeu()
    for code, lst in JEU.items():
        for d, *_ in lst:
            if d not in fams:
                raise SystemExit(f"famille absente du catalogue : {d}")
    ch = chaussee()
    axis = LineString(ch["A"])
    print("rasters...")
    G = Grille()
    print("détection...")
    x, y, rc, area, origine, lab, masks, rejets = detecte(G, ch, axis)
    h = G.hs[rc[:, 0], rc[:, 1]].astype(float)
    hmax = ndi.maximum(G.h, lab, np.arange(1, len(rc) + 1))       # hauteur brute du houppier
    rt, ct = G.rc(x, y)
    z = G.mnt[rt, ct].astype(float)
    d = 2 * np.sqrt(area / math.pi)
    pk, dist, side = reperes_axe(ch, axis, x, y)
    print(f"{len(x)} arbres")

    zr, noms, inconnus = zones_essence(G, axis)
    regle = np.array([noms[k - 1] for k in zr[rc[:, 0], rc[:, 1]]])
    ess = np.array([tirage(rng, r, hh) for r, hh in zip(regle, h)])
    fam, elem = [], []
    for e, hh in zip(ess, h):
        dd, lst = famille(fams, e, hh)
        fam.append("Foliage/" + dd)
        elem.append(lst[rng.integers(len(lst))])
    T = {"x": x, "y": y, "z": z, "h": h, "d": d, "ess": ess, "regle": regle, "dist": dist}

    rows = [(f"{x[i]:.2f}", f"{y[i]:.2f}", f"{z[i]:.2f}", f"{h[i]:.1f}", f"{d[i]:.1f}", ESSENCES[ess[i]][0],
             fam[i], elem[i], regle[i], f"{dist[i]:.1f}", f"{pk[i]:.0f}", side[i],
             ("apex", "couvert_restant")[origine[i]]) for i in range(len(x))]
    p_arbres = ecrire_csv(OUT / "arbres.csv", ["x_l93", "y_l93", "z_sol_m", "hauteur_m", "diametre_houppier_m", "essence",
                                               "famille_jeu", "element_jeu_propose", "regle_essence", "dist_axe_m",
                                               "pk_m", "cote", "detection"], rows)

    print("arbustes...")
    sx, sy, sz, sh, sd, n_low = arbustes(G, rng, masks, lab)
    spk, sdist, sside = reperes_axe(ch, axis, sx, sy)
    sfam, selem = [], []
    for hh in sh:
        dd, lst = famille(fams, "arbuste", hh)
        sfam.append("Foliage/" + dd)
        selem.append(lst[rng.integers(len(lst))])
    srows = [(f"{sx[i]:.1f}", f"{sy[i]:.1f}", f"{sz[i]:.1f}", f"{sh[i]:.1f}", f"{sd[i]:.1f}", sfam[i], selem[i],
              f"{sdist[i]:.0f}", f"{spk[i]:.0f}", sside[i]) for i in range(len(sx))]
    p_arbustes = ecrire_csv(OUT / "arbustes.csv", ["x_l93", "y_l93", "z_sol_m", "hauteur_m", "diametre_m",
                                                   "famille_jeu", "element_jeu_propose", "dist_axe_m", "pk_m", "cote"], srows)

    # --- contrôles ---------------------------------------------------------------------------
    zone = masks["bande"] & G.valid & ~masks["route"] & ~masks["bati"]
    couv = zone & (G.h > H_ARBRE)
    seg = zone & (lab > 0)
    ha_zone = zone.sum() * RES * RES / 1e4
    circ = float((math.pi * (d / 2) ** 2).sum())
    dens = {}
    zz = zr[zone]
    lab_z = lab[zone]
    couv_z = couv[zone]
    tree_regle = Counter(regle)
    for k, nom in enumerate(noms, 1):
        m = zz == k
        if m.sum() == 0:
            continue
        ha = m.sum() * RES * RES / 1e4
        sel = regle == nom
        dens[nom] = {"surface_ha": round(ha, 1), "arbres": int(tree_regle[nom]),
                     "arbres_par_ha": round(tree_regle[nom] / ha), "couvert_sup_2m_pct": round(float(couv_z[m].mean() * 100), 1),
                     "part_couvert_dans_houppiers_pct": round(float((lab_z[m] > 0)[couv_z[m]].mean() * 100), 1) if couv_z[m].any() else None,
                     "hauteur_mediane_m": round(float(np.median(h[sel])), 1) if sel.any() else None,
                     "essences_tirees_pct": {ESSENCES[e][0]: round(c / sel.sum() * 100) for e, c in Counter(ess[sel]).most_common()}}
    bins = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 25, 40]
    hist = np.histogram(h, bins)[0]
    s_count = Counter(sfam)
    resume = {
        "methode": __doc__.split("Méthode")[1].strip(),
        "graine_aleatoire": SEED,
        "bande_m": f"0 à {BANDE:.0f} m de l'axe (PK {ch['pk'][0]:.0f} à {ch['pk'][-1]:.0f})",
        "surface_analysee_ha": round(ha_zone, 1),
        "mesure": {
            "couvert_sup_2m_pct_de_la_bande": round(float(couv.sum() / zone.sum() * 100), 1),
            "part_du_couvert_sup_2m_dans_un_houppier_segmente_pct": round(float((seg & couv).sum() / couv.sum() * 100), 1),
            "surface_cumulee_disques_de_houppier_sur_surface_couverte": round(circ / (couv.sum() * RES * RES), 3),
            "ndvi_rvb_recale_sur_irc_(pente, ordonnee, correlation)": G.recalage_rvb,
            "part_de_la_bande_couverte_par_l_irc_pct": round(float(G.has_irc[zone].mean() * 100), 1),
            "vegetation_basse_0.4_2m_ha": round(n_low * RES * RES / 1e4, 1),
        },
        "arbres": {
            "nombre": int(len(x)), "rejets": rejets,
            "par_passe": {"apex (passe 1)": int((origine == 0).sum()), "couvert restant (passe 2)": int((origine == 1).sum())},
            "a_moins_de_40m": int((dist <= 40).sum()), "a_moins_de_15m": int((dist <= 15).sum()),
            "densite_moyenne_par_ha": round(len(x) / ha_zone),
            "hauteur_m": {"mediane": round(float(np.median(h)), 1), "p10": round(float(np.percentile(h, 10)), 1),
                          "p90": round(float(np.percentile(h, 90)), 1), "max": round(float(h.max()), 1),
                          "histogramme": {f"{a}-{b}": int(c) for a, b, c in zip(bins[:-1], bins[1:], hist)}},
            "ecart_hauteur_brute_max_moins_lissee_m_mediane": round(float(np.median(hmax - h)), 2),
            "diametre_houppier_m": {"mediane": round(float(np.median(d)), 1), "p10": round(float(np.percentile(d, 10)), 1),
                                    "p90": round(float(np.percentile(d, 90)), 1)},
            "par_essence": {ESSENCES[e][0]: {"nombre": int(c), "pct": round(c / len(x) * 100, 1),
                                             "hauteur_mediane_m": round(float(np.median(h[ess == e])), 1)}
                            for e, c in Counter(ess).most_common()},
            "par_famille_jeu": dict(Counter(fam).most_common()),
        },
        "arbustes": {"nombre": int(len(sx)), "par_famille_jeu": dict(s_count.most_common()),
                     "densite_par_ha_de_vegetation_basse": round(len(sx) / max(n_low * RES * RES / 1e4, 1e-6))},
        "par_type_de_formation": dens,
        "formations_bdforet_non_reconnues": inconnus,
        "proportions_hypothese": FORMATIONS,
        "correspondance_jeu": {
            ESSENCES[c][0] if c in ESSENCES else "arbuste / garrigue": [
                {"famille": "acr/Content/Foliage/" + dd, "hauteur_m": f"{lo:g}-{hi:g}" if hi < 99 else f">= {lo:g}",
                 "note": note, "maillages": fams[dd]} for dd, lo, hi, note in lst] for c, lst in JEU.items()},
        "chene_vert_substitut": SUBSTITUT_CHENE_VERT,
        "autres_elements_utiles_du_catalogue": {
            "pins_destructibles": [n for n in ("DestructibleTrees/Aleppopine/Aleppopine_07/BP_Aleppopine_07_Replacement",
                                               "DestructibleTrees/Aleppopine/Aleppopine_08/BP_Aleppopine_08_Replacement")],
            "cypres_sauvage_MonteCarlo": fams.get("Trees/CypressWildMonteCarlo", []),
            "haies": fams.get("Trees/Hedge", []) + fams.get("Trees/CypressHedge", []),
        },
        "limites": [
            "Essence attribuée par tirage dans des proportions supposées par type de formation BD Forêt : "
            "juste en moyenne sur un polygone, fausse arbre par arbre (aucune identification spectrale).",
            "BD Forêt : unité minimale 0,5 ha, contours à quelques mètres, photos plus anciennes que le LiDAR.",
            "Le MNS ne voit que la surface : le sous-étage (chênes et arbustes sous les pins) est absent.",
            "Pinède dense à houppiers jointifs : plusieurs pins peuvent être fusionnés en un seul houppier, "
            "et de gros houppiers étalés peuvent être coupés en deux ; le nombre d'arbres y est incertain d'environ 20-30 %.",
            "Taillis de chêne vert : cépées multi-tiges vues comme un seul houppier large et bas.",
            "Arbustes : seule la densité (pixel 0,5 m) est mesurée ; positions, tailles et genres sont semés.",
            "Ortho et LiDAR ne sont pas pris le même jour ; l'ortho a un dévers (houppiers hauts décalés de 1-3 m "
            "vers l'extérieur de l'image), d'où des cercles parfois légèrement décalés sur les planches.",
            "Les maillages du jeu ne sont connus que par leur nom : hauteurs natives et aspect non vérifiés.",
        ],
        "fichiers": [str(p.relative_to(ROOT)) for p in (p_arbres, p_arbustes)],
    }

    print("figures...")
    ext = choisir_extraits(T, (sx, sy), ch)
    resume["extraits_planche"] = [{"titre": t, "x_l93": round(float(a), 1), "y_l93": round(float(b), 1)} for t, a, b in ext]
    planche(T, (sx, sy, sh), ch, ext, FIG4 / "semis_planche_ortho.png")
    synthese(T, FIG4 / "semis_synthese.png")
    n3d = glb_arbres(T, ROOT / "modele" / "apercu" / "arbres.glb")
    resume["apercu_3d"] = {"fichier": "modele/apercu/arbres.glb", "arbres": n3d, "rayon_m": GLB_DIST,
                           "taille_mo": round((ROOT / "modele" / "apercu" / "arbres.glb").stat().st_size / 1e6, 2)}
    (OUT / "semis_resume.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: resume[k] for k in ("mesure", "arbres", "arbustes")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
