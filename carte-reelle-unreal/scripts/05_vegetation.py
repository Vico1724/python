"""Étape 5 - Végétation : un arbre par ligne (position, altitude du pied, hauteur, rayon, type).

Méthode LiDAR (si relief/mnt_50cm.tif et mns_50cm.tif existent, étape 02) :
  hauteur du couvert MNH = MNS - MNT à 0,5 m, lissée ; apex = maxima locaux dans un disque dont le
  rayon croît avec la hauteur (1 à 3 m), au-dessus de hauteur_min_m (2 m), hors bâtiments + 2 m ;
  houppiers par ligne de partage des eaux, deux passes complémentaires dans le couvert resté hors
  houppier ; rejet des houppiers trop petits et, si l'infrarouge IGN répond, des sursols minéraux
  (NDVI). Reprise de la méthode éprouvée des projets d'origine.
Méthode semis (sans LiDAR, ou --methode semis) : points en grille jitterée dans les zones de
  végétation BD TOPO (ou OSM), espacement et hauteur selon la nature ; arbres isolés OSM ajoutés.
Type = famille (conifere, feuillu, mixte, indetermine, d'après la zone de végétation qui contient
  l'arbre) + taille (petit < 6 m, moyen < 12 m, grand) ; « arbuste » pour la lande basse.

Usage : python 05_vegetation.py --zone zone.json --sortie DOSSIER [--methode auto|lidar|semis]
Sorties : vegetation/arbres.csv (x,y,z,hauteur,rayon,type ; repère local, m), journaux/05_vegetation.json
"""
import csv

import numpy as np
import shapely
from scipy import ndimage as ndi
from shapely.geometry import shape

import geo

H_ARBRE = 2.0        # m : seuil arbre / végétation basse (défaut de vegetation.hauteur_min_m)
MARGE_BATI = 2.0     # m autour des bâtiments : les toits et façades ne sont pas des arbres
NDVI_VERT = 0.12     # NDVI d'un pixel de végétation (valeur des projets d'origine, Provence)
PART_VERTE = 0.15    # part minimale de pixels verts dans un houppier
# Semis : (espacement m, hauteur moyenne m, famille) par nature de zone BD TOPO ou OSM.
SEMIS = {
    "Forêt fermée de conifères": (5.0, 11.0, "conifere"), "Forêt fermée de feuillus": (6.0, 14.0, "feuillu"),
    "Forêt fermée mixte": (5.5, 12.0, "mixte"), "Forêt ouverte": (9.0, 8.0, "indetermine"),
    "Bois": (6.0, 10.0, "indetermine"), "Zone arborée": (7.0, 9.0, "indetermine"),
    "Peupleraie": (7.0, 18.0, "feuillu"), "Verger": (6.0, 5.0, "feuillu"), "Lande ligneuse": (4.0, 1.5, "arbuste"),
    "Haie": (3.0, 4.0, "feuillu"), "wood": (6.0, 10.0, "indetermine"), "forest": (6.0, 12.0, "indetermine"),
    "scrub": (4.0, 1.5, "arbuste"), "heath": (4.0, 1.2, "arbuste"), "orchard": (6.0, 5.0, "feuillu"),
}


def disque(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r + 0.5


def apex(hs, cand, res, hmin):
    """Pixel apex : le plus haut du disque de rayon 0,5 + 0,15 h (borné à 1-3 m)."""
    rpx = np.rint(np.clip(0.5 + 0.15 * hs, 1.0, 3.0) / res).astype(np.int16)
    cand = cand & (hs >= hmin)
    seed = np.zeros(hs.shape, bool)
    if not cand.any():
        return np.zeros((0, 2), int)
    for r in range(int(rpx[cand].min()), int(rpx[cand].max()) + 1):
        sel = cand & (rpx == r)
        if sel.any():
            seed |= sel & (hs >= ndi.maximum_filter(hs, footprint=disque(r)))
    lab, n = ndi.label(seed, structure=np.ones((3, 3)))            # plateau -> un seul point
    if n == 0:
        return np.zeros((0, 2), int)
    rc = np.rint(np.array(ndi.center_of_mass(seed, lab, range(1, n + 1)))).astype(int).reshape(-1, 2)
    return rc[seed[rc[:, 0], rc[:, 1]]]


def houppiers(hs, rc, masque, res):
    """Partage des eaux depuis les apex ; un pixel reste s'il dépasse 40 % de la hauteur de l'apex
    et se trouve à moins de 1 + 0,45 h de lui (forme de houppier plausible)."""
    from skimage.segmentation import watershed
    markers = np.zeros(hs.shape, np.int32)
    markers[rc[:, 0], rc[:, 1]] = np.arange(1, len(rc) + 1)
    lab = watershed(-hs, markers, mask=masque)
    happ = np.concatenate([[0], hs[rc[:, 0], rc[:, 1]]])
    ok = lab > 0
    ok[ok] = hs[ok] >= 0.4 * happ[lab[ok]]
    rr, cc = np.nonzero(ok)
    li = lab[rr, cc]
    loin = np.hypot(rr - rc[li - 1, 0], cc - rc[li - 1, 1]) * res > 1.0 + 0.45 * happ[li]
    ok[rr[loin], cc[loin]] = False
    lab[~ok] = 0
    return lab


def zones_vegetation(ctx):
    """[(polygone local, nature, famille)] : BD TOPO, sinon OSM."""
    out = []
    for f in geo.lire_geojson(ctx.sortie / "vecteurs" / "bdtopo_vegetation.geojson"):
        nat = f["properties"].get("nature", "")
        out.append((shape(f["geometry"]), nat, famille_nature(nat)))
    if not out:
        for f in geo.lire_geojson(ctx.sortie / "vecteurs" / "osm_vegetation.geojson"):
            t = f["properties"]
            nat = t.get("natural") or t.get("landuse") or ""
            fam = {"needleleaved": "conifere", "broadleaved": "feuillu", "mixed": "mixte"}.get(t.get("leaf_type"),
                                                                                              famille_nature(nat))
            out.append((shape(f["geometry"]), nat, fam))
    return [(g, n, f) for g, n, f in out if g.geom_type in ("Polygon", "MultiPolygon")]


def famille_nature(nat):
    n = nat.lower()
    if "conif" in n:
        return "conifere"
    if "feuillu" in n or n in ("peupleraie", "verger", "orchard", "haie"):
        return "feuillu"
    if "mixte" in n:
        return "mixte"
    if "lande" in n or n in ("scrub", "heath"):
        return "arbuste"
    return "indetermine"


def batiments(ctx):
    g = [shape(f["geometry"]) for nom in ("bdtopo_batiments", "osm_batiments")
         for f in geo.lire_geojson(ctx.sortie / "vecteurs" / f"{nom}.geojson")]
    return [x for x in g if x.geom_type in ("Polygon", "MultiPolygon")]


def type_arbre(fam, h):
    if fam == "arbuste" and h < 4:
        return "arbuste"
    if fam == "arbuste":
        fam = "indetermine"
    return f"{fam}_{'petit' if h < 6 else 'moyen' if h < 12 else 'grand'}"


def familles(ctx, x, y):
    fam = np.full(len(x), "indetermine", dtype=object)
    pts = shapely.points(x, y)
    for g, _, f in zones_vegetation(ctx):
        fam[shapely.contains(g, pts)] = f
    return fam


def par_lidar(ctx, hmin):
    from rasterio.features import rasterize
    from affine import Affine
    rel = ctx.sortie / "relief"
    mnt, tr = geo.lire_tif(rel / "mnt_50cm.tif")
    mns, _ = geo.lire_tif(rel / "mns_50cm.tif")
    res = tr.a
    trl = Affine(tr.a, 0, tr.c - ctx.ox, 0, tr.e, tr.f - ctx.oy)            # transform en repère local
    shp = mnt.shape
    zone = ctx.emprise_locale()
    dans = rasterize([zone], out_shape=shp, transform=trl).astype(bool)
    valide = np.isfinite(mnt) & np.isfinite(mns) & dans
    mnh = np.where(valide, np.clip(mns - mnt, 0, 60), 0).astype(np.float32)
    hs = ndi.gaussian_filter(mnh, 0.5 / res)
    bats = batiments(ctx)
    brule = lambda geoms: (rasterize(geoms, out_shape=shp, transform=trl).astype(bool) if geoms else np.zeros(shp, bool))
    cand = valide & ~brule([g.buffer(MARGE_BATI) for g in bats])
    pousse = cand & (hs >= hmin)

    ndvi, note_ndvi = None, "NDVI non utilisé"
    if ctx.en_france():
        try:
            b = (tr.c, tr.f + tr.e * shp[0], tr.c + tr.a * shp[1], tr.f)
            irc = geo.wms_mosaique(ctx.cache, geo.COUCHE_IRC, b, res, fmt="image/jpeg", bandes=3,
                                   progres="infrarouge").astype(np.float32)
            ndvi = (irc[0] - irc[1]) / np.maximum(irc[0] + irc[1], 1)        # PIR, R, V
            note_ndvi = "NDVI IRC IGN"
        except Exception as e:      # l'infrarouge n'est qu'un filtre : on s'en passe
            note_ndvi = f"NDVI indisponible ({str(e)[:80]})"

    rc = apex(hs, cand, res, hmin)
    lab = houppiers(hs, rc, pousse, res) if len(rc) else np.zeros(shp, np.int32)
    passe = np.zeros(len(rc), int)
    for _ in (2, 3):                                  # couvert resté hors des houppiers
        reste = ndi.binary_opening(pousse & (lab == 0), structure=disque(2))
        rc2 = apex(np.where(reste, hs, 0).astype(np.float32), reste, res, hmin)
        if not len(rc2):
            break
        lab2 = houppiers(hs, rc2, reste, res)
        lab = np.where(lab > 0, lab, np.where(lab2 > 0, lab2 + len(rc), 0)).astype(np.int32)
        rc, passe = np.vstack([rc, rc2]), np.concatenate([passe, np.ones(len(rc2), int)])
    if not len(rc):
        return [], {"apex": 0, "ndvi": note_ndvi}
    idx = np.arange(1, len(rc) + 1)
    aire = ndi.sum_labels(np.ones(shp, np.float32), lab, idx) * res * res
    hmax = ndi.maximum(mnh, lab, idx)
    amin = np.where(passe == 0, 1.0, 3.0)                 # m² : en dessous, pointe isolée (poteau, bord de toit)
    garde = (aire >= amin) & (hmax >= hmin)
    mineral = np.zeros(len(rc), bool)
    if ndvi is not None:
        vert = ndi.mean((ndvi >= NDVI_VERT).astype(np.float32), lab, idx)
        mineral = (vert < PART_VERTE) & (ndi.mean(ndvi, lab, idx) < -0.05)
        garde &= ~mineral
    r, c = rc[garde, 0], rc[garde, 1]
    x = trl.c + (c + 0.5) * res
    y = trl.f - (r + 0.5) * res
    z = mnt[r, c] - ctx.repere["z0_m"]
    h = hmax[garde]
    ray = np.sqrt(aire[garde] / np.pi)
    fam = familles(ctx, x, y)
    rows = [(x[i], y[i], z[i], h[i], ray[i], type_arbre(fam[i], h[i])) for i in range(len(x))]
    return rows, {"apex": int(len(rc)), "rejets_petits": int((aire < amin).sum()),
                  "rejets_mineraux": int(mineral.sum()), "ndvi": note_ndvi, "pas_m": res,
                  "couvert_pct": round(float((pousse.sum() / max(valide.sum(), 1)) * 100), 1)}


def par_semis(ctx):
    rng = np.random.default_rng(12345)               # graine fixe : même résultat à chaque lancement
    zone = ctx.emprise_locale()
    exclu = shapely.union_all([g.buffer(MARGE_BATI) for g in batiments(ctx)] +
                              [shape(f["geometry"]).buffer(max(float(f["properties"].get("largeur_de_chaussee") or 4), 2) / 2)
                               for f in geo.lire_geojson(ctx.sortie / "vecteurs" / "bdtopo_routes.geojson")])
    rows, par_nature = [], {}
    zones = zones_vegetation(ctx)
    haies = [(shape(f["geometry"]).buffer(1.0), "Haie", "feuillu")
             for f in geo.lire_geojson(ctx.sortie / "vecteurs" / "bdtopo_haies.geojson")]
    for g, nat, fam in zones + haies:
        esp, hm, fam2 = SEMIS.get(nat, (8.0, 8.0, fam))
        if fam == "indetermine":
            fam = fam2
        g = g.intersection(zone)
        if exclu is not None and not exclu.is_empty:
            g = g.difference(exclu)
        if g.is_empty:
            continue
        x0, y0, x1, y1 = g.bounds
        gx, gy = np.meshgrid(np.arange(x0, x1, esp), np.arange(y0, y1, esp))
        px = gx.ravel() + rng.uniform(0, esp, gx.size)
        py = gy.ravel() + rng.uniform(0, esp, gy.size)
        m = shapely.contains_xy(g, px, py)
        px, py = px[m], py[m]
        h = np.clip(rng.normal(hm, 0.25 * hm, len(px)), 0.5, 40)
        par_nature[nat] = par_nature.get(nat, 0) + len(px)
        rows += [(px[i], py[i], h[i], fam) for i in range(len(px))]
    for f in geo.lire_geojson(ctx.sortie / "vecteurs" / "osm_arbres.geojson"):
        g = shape(f["geometry"])
        pts = [g] if g.geom_type == "Point" else [g.interpolate(d) for d in np.arange(0, g.length, 6.0)]
        h = float(str(f["properties"].get("height", "8")).split()[0].replace(",", ".") or 8) if f["properties"].get("height") else 8.0
        rows += [(p.x, p.y, h, famille_nature(f["properties"].get("leaf_type", ""))) for p in pts]
    if not rows:
        return [], {"par_nature": par_nature}
    rel = geo.Relief(ctx)
    x = np.array([r[0] for r in rows])
    y = np.array([r[1] for r in rows])
    z = rel.z(x, y)
    out = [(x[i], y[i], z[i], rows[i][2], max(0.6, 0.3 * rows[i][2]), type_arbre(rows[i][3], rows[i][2]))
           for i in range(len(rows))]
    return out, {"par_nature": par_nature, "osm_arbres": len(geo.lire_geojson(ctx.sortie / "vecteurs" / "osm_arbres.geojson"))}


def main():
    ap = geo.parser(__doc__.splitlines()[0])
    ap.add_argument("--methode", choices=("auto", "lidar", "semis"), help="défaut : vegetation.methode de zone.json")
    args = ap.parse_args()
    ctx = geo.Contexte(args)
    if ctx.repere.get("z0_m") is None:
        raise SystemExit("ERREUR 05_vegetation : lancer d'abord 02_relief.py (relief et z0)")
    vcfg = ctx.cfg["vegetation"]
    methode = args.methode or vcfg.get("methode", "auto")
    d = ctx.dossier("vegetation")
    sortie = d / "arbres.csv"
    j = ctx.deja_fait("05_vegetation", [sortie], methode=methode)
    if j:
        geo.resume([f"05_vegetation : déjà fait ({j['resume']}) ; --force pour refaire"])
        return
    lidar_ok = (ctx.sortie / "relief" / "mnt_50cm.tif").exists() and (ctx.sortie / "relief" / "mns_50cm.tif").exists()
    if methode == "lidar" and not lidar_ok:
        raise SystemExit("ERREUR 05_vegetation : pas de MNT/MNS LiDAR fin (relief/*_50cm.tif) : relancer 02_relief.py "
                         "sans --sans-lidar-fin, ou --methode semis")
    if methode == "auto":
        methode = "lidar" if lidar_ok else "semis"
    if not (ctx.sortie / "vecteurs").exists():
        print("  (vecteurs absents : pas de masque des bâtiments ni de familles ; lancer 04_vecteurs.py d'abord)")
    rows, info = par_lidar(ctx, float(vcfg.get("hauteur_min_m", H_ARBRE))) if methode == "lidar" else par_semis(ctx)
    rows.sort(key=lambda r: (-r[1], r[0]))
    with open(sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["x", "y", "z", "hauteur", "rayon", "type"])
        for x, y, z, h, r, t in rows:
            w.writerow([f"{x:.2f}", f"{y:.2f}", f"{z:.2f}", f"{h:.1f}", f"{r:.1f}", t])
    types = {}
    for r in rows:
        types[r[5]] = types.get(r[5], 0) + 1
    h = np.array([r[3] for r in rows]) if rows else np.zeros(1)
    ha = ctx.emprise_locale().area / 1e4
    txt = f"{len(rows)} arbres ({methode}), {len(rows) / ha:.0f}/ha, hauteur médiane {np.median(h):.1f} m"
    ctx.journal("05_vegetation", {"options": {"methode": args.methode or vcfg.get("methode", "auto")}, "resume": txt,
                                  "methode": methode, "types": types, "details": info,
                                  "hauteur_m": {"mediane": round(float(np.median(h)), 1), "max": round(float(h.max()), 1)}})
    lignes = [f"05_vegetation : {txt}",
              "  types : " + ", ".join(f"{k} {v}" for k, v in sorted(types.items(), key=lambda kv: -kv[1])[:6]),
              f"  téléchargé : {geo.volume_telecharge()} ; {ctx.duree()}"]
    geo.resume(lignes)


if __name__ == "__main__":
    main()
