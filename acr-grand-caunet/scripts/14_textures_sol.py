"""Étape 14 - Images de sol par dalle, « sous les arbres », et textures de relief.

La photo aérienne posée sur les dalles de 08 montre le DESSUS des arbres et leurs ombres :
c'est faux dès que de vrais arbres 3D sont posés dessus. Ce script fabrique, pour chaque dalle
du terrain de 08, une image du sol tel qu'on le verrait sous les arbres.

Entrées : modele/terrain.glb et modele/apercu/terrain.glb (géométrie de 08, relue telle quelle),
          data/raw/ortho_20cm.tif, ortho_irc_20cm.tif, mnt_lidarhd_50cm.tif, mns_lidarhd_50cm.tif,
          data/processed/chaussee_precise.csv, arbres.csv (essence et houppier de chaque arbre),
          data/processed/couloir/bdforet_formation_vegetale.geojson,
          textures CC0 de Poly Haven (téléchargées une fois dans data/raw/cc0/, provenance dans
          data/reference/ressources_cc0.json)
Méthode (grille de 20 cm, résolution native de l'ortho)
  1. Sol visible = ni couvert (MNS - MNT lissé > 0,6 m, dilaté de 0,6 m), ni végétation de la
     photo à moins de 4 m d'un couvert (décalage des houppiers : l'ortho n'est pas une vraie
     ortho), ni ombre portée (luminance < 0,62 x luminance locale du sol éclairé), ni chaussée.
     Là, la couleur de la photo est gardée telle quelle.
  2. Ailleurs, sol reconstruit : couleur de fond = couleur des sols visibles voisins, propagée
     par « push-pull » (moyenne pondérée multi-échelle, contexte de 100 m pour éviter les
     coutures entre dalles), mélangée, à mesure qu'on s'éloigne du sol visible (2 à 14 m), à une
     palette de sols : litière d'aiguilles de pin sous les pins, litière de chêne vert sous les
     feuillus (essence et houppier de arbres.csv ; BD Forêt hors arbre détecté), sol caillouteux
     et herbes sèches ailleurs (garrigue), roche claire sur les pentes > 35°. Variation de
     teinte et motif à grande échelle par un bruit défini en coordonnées Lambert-93 (continu
     d'une dalle à l'autre).
  3. Bande de la route (sous-dalles de 100 m, toutes celles qui portent du terrain à moins de
     18 m du bord de chaussée) : image à 5 cm par pixel = image de 20 cm agrandie, multipliée
     par le détail fin de textures CC0 (rapport à leur moyenne, donc la couleur moyenne reste
     celle de la photo ou de la reconstruction), mélangées selon la nature du sol par hauteur
     (les cailloux percent la litière), à trois échelles et rotations pour casser la répétition.
  4. Relief (normal map, espace tangent, convention glTF / OpenGL : rouge = est, vert = nord) :
     écart entre la normale du MNT 0,5 m et celle du MNT lissé à la maille du maillage ; sur les
     sous-dalles, s'y ajoute le relief fin des textures CC0.
Sorties : modele/textures_sol/ (non versionné) : dalle_X_Y_couleur.jpg (20 cm), dalle_X_Y_relief.png
          (0,5 m), sous_X_Y_couleur.jpg (5 cm), sous_X_Y_relief.jpg (10 cm)
          modele/terrain_sol.glb (géométrie de 08, images en références externes textures_sol/...)
          modele/apercu/terrain_sol.glb (géométrie légère de 08, images 512 px intégrées)
          data/processed/textures_sol.json (manifeste par dalle), figures/phase5/sol_avant_apres.jpg
Rejouable : quelques minutes (4 processus) ; « python 14_textures_sol.py apercu » ne refait que
l'aperçu et le manifeste à partir des images déjà produites.
"""
import csv
import importlib.util
import io
import json
import math
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np
import rasterio
import shapely
from PIL import Image
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.windows import from_bounds
from scipy import ndimage as ndi
from shapely.geometry import shape

from acr_geo import FIG, OUT, RAW, REF, ROOT, TO_L93, get

_spec = importlib.util.spec_from_file_location("modele_3d", Path(__file__).with_name("08_modele_3d.py"))
m08 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m08)

MOD = ROOT / "modele"
TEX = MOD / "textures_sol"
CC0 = RAW / "cc0"
FIG5 = FIG / "phase5"
TILE = 500.0                 # m : dalle de 08
RES = 0.2                    # m/pixel : image de base (ortho native)
MARGE = 16.0                 # m autour de la dalle (les triangles de bord débordent de la dalle)
CONTEXTE = 100.0             # m de contexte pour la propagation des couleurs (pas de couture)
SOUS = 100.0                 # m : sous-dalle de la bande route
SOUS_MARGE = 2.4             # m
SOUS_PX = 2048               # px -> 104,8 m / 2048 = 5,1 cm
SOUS_NOR_PX = 1024           # px -> 10 cm
BANDE = 18.0                 # m au-delà du bord de chaussée : sous-dalles fines
NOR_RES = 0.5                # m/pixel : relief des dalles
H_COUVERT = 0.6              # m : seuil de couvert (MNS - MNT lissé)
SEED = 14

# Textures CC0 (Poly Haven) : rôle -> identifiant. Taille physique lue dans l'API (mm).
CC0_TEXTURES = {
    "aiguilles": "forrest_ground_03",      # litière d'aiguilles de pin
    "litiere": "forest_ground_04",         # litière de feuillus sur sol caillouteux (chêne vert)
    "cailloux": "rocks_ground_01",         # garrigue : cailloux calcaires
    "herbes": "withered_grass",            # herbes sèches
    "roche": "rock_boulder_dry",           # affleurement calcaire clair
    "gravier": "rock_ground_02",           # accotement gravillonné
}
MATIERES = list(CC0_TEXTURES)
# Couleur de fond des sols reconstruits (sRVB, dans la radiométrie de l'ortho BD ORTHO : mesurée
# sur les sols visibles du couloir, puis assombrie pour les litières). Voir le manifeste.
PALETTE = {
    "aiguilles": (122, 104, 82),
    "litiere": (104, 94, 80),
    "cailloux": (150, 142, 124),
    "herbes": (146, 136, 106),
    "roche": (176, 170, 156),
    "gravier": (150, 146, 136),
}
# amplitude du détail fin (5 cm) par matière, et part de la chrominance de la texture CC0
DETAIL = {"aiguilles": (0.9, 0.5), "litiere": (0.9, 0.4), "cailloux": (1.0, 0.3), "herbes": (0.8, 0.5),
          "roche": (0.7, 0.2), "gravier": (0.9, 0.2)}


# --- textures CC0 ------------------------------------------------------------------------------
def telecharge_cc0():
    """Télécharge (une fois) diffuse et normale OpenGL 2k des textures, note la provenance."""
    CC0.mkdir(parents=True, exist_ok=True)
    prov_path = REF / "ressources_cc0.json"
    prov = json.loads(prov_path.read_text(encoding="utf-8")) if prov_path.exists() else {}
    textures = prov.get("textures_sol", {})
    for role, ident in CC0_TEXTURES.items():
        if ident in textures and all((CC0 / f"{ident}_{k}.jpg").exists() for k in ("diff", "nor_gl")):
            continue
        info = get(f"https://api.polyhaven.com/info/{ident}", {}).json()
        files = get(f"https://api.polyhaven.com/files/{ident}", {}).json()
        urls = {"diff": files["Diffuse"]["2k"]["jpg"]["url"], "nor_gl": files["nor_gl"]["2k"]["jpg"]["url"]}
        for k, u in urls.items():
            (CC0 / f"{ident}_{k}.jpg").write_bytes(get(u, {}).content)
        textures[ident] = {"role": role, "nom": info["name"], "auteurs": list(info["authors"]),
                           "licence": "CC0 1.0 (domaine public), Poly Haven",
                           "page": f"https://polyhaven.com/a/{ident}", "fichiers": urls,
                           "taille_physique_m": round(info["dimensions"][0] / 1000.0, 3),
                           "utilisation": "détail fin (couleur et relief) des sous-dalles de la bande route, "
                                          "motif à grande échelle des sols reconstruits (14_textures_sol.py)"}
    prov["textures_sol"] = textures
    prov.setdefault("note", "Seules des ressources CC0 (Poly Haven) ou IGN (Licence Ouverte) sont utilisées.")
    prov_path.write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")
    return {role: textures[ident] for role, ident in CC0_TEXTURES.items()}


class Matiere:
    """Une texture CC0 préparée à une résolution donnée : rapport de couleur (moyenne 1),
    relief (normale tangente) et « hauteur » (luminance relative) pour le mélange."""

    def __init__(self, ident, taille_m, res, echelle=1.0):
        diff = cv2.cvtColor(cv2.imread(str(CC0 / f"{ident}_diff.jpg")), cv2.COLOR_BGR2RGB).astype(np.float32)
        nor = cv2.cvtColor(cv2.imread(str(CC0 / f"{ident}_nor_gl.jpg")), cv2.COLOR_BGR2RGB).astype(np.float32)
        self.taille = taille_m * echelle
        n = max(8, int(round(self.taille / res)))
        self.diff = cv2.resize(diff, (n, n), interpolation=cv2.INTER_AREA)
        nn = cv2.resize(nor, (n, n), interpolation=cv2.INTER_AREA) / 127.5 - 1.0
        self.nor = nn / np.linalg.norm(nn, axis=2, keepdims=True)
        lum = self.diff @ np.array([0.299, 0.587, 0.114], np.float32)
        self.moy = self.diff.reshape(-1, 3).mean(0)
        self.lum = lum / lum.mean()
        self.n = n

    def echantillon(self, X, Y, angle, decal, quoi):
        """Échantillonne (bilinéaire, périodique) aux coordonnées monde X, Y (m)."""
        c, s = math.cos(angle), math.sin(angle)
        u = ((c * X + s * Y) / self.taille + decal[0]) * self.n
        v = ((-s * X + c * Y) / self.taille + decal[1]) * self.n
        u = np.mod(u, self.n).astype(np.float32)
        v = np.mod(v, self.n).astype(np.float32)
        src = {"diff": self.diff, "nor": self.nor.astype(np.float32), "lum": self.lum.astype(np.float32)}[quoi]
        out = cv2.remap(src, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        if quoi == "nor":
            # +u de l'image va vers (c, s) dans le monde, le « haut » de l'image (vert) vers (s, -c)
            nx, ny = out[..., 0].copy(), out[..., 1].copy()
            out[..., 0] = nx * c + ny * s
            out[..., 1] = nx * s - ny * c
        return out


# --- bruit défini en coordonnées monde (continu d'une dalle à l'autre) ---------------------------
def _hash(i, j, seed):
    h = (i.astype(np.int64) * 374761393 + j.astype(np.int64) * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return (((h ^ (h >> 16)) & 0xFFFF) / 65535.0).astype(np.float32)


def bruit(x0, y1, res, shape, pas, seed):
    """Bruit de valeur lissé (bicubique) de maille `pas` m, dans [-1, 1], sur une grille
    (x0 = bord ouest, y1 = bord nord, res m/px)."""
    h, w = shape
    i0, j0 = math.floor(x0 / pas) - 2, math.floor((y1 - h * res) / pas) - 2
    i1, j1 = math.ceil((x0 + w * res) / pas) + 2, math.ceil(y1 / pas) + 2
    I, J = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j1, j0 - 1, -1))      # lignes : nord -> sud
    lat = _hash(I, J, seed) * 2 - 1
    xs = (x0 + (np.arange(w) + 0.5) * res) / pas - i0
    ys = (j1 - (y1 - (np.arange(h) + 0.5) * res) / pas)
    mx, my = np.meshgrid(xs.astype(np.float32), ys.astype(np.float32))
    return cv2.remap(lat, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def fbm(x0, y1, res, shape, pas, octaves, seed, gain=0.5):
    tot, a, s = np.zeros(shape, np.float32), 1.0, 0.0
    for k in range(octaves):
        if pas / 2 ** k < 2 * res:
            break
        tot += a * bruit(x0, y1, res, shape, pas / 2 ** k, seed + 31 * k)
        s += a
        a *= gain
    return tot / s


# --- outils raster -----------------------------------------------------------------------------
def lire(path, bounds, res, bands=None, interp=cv2.INTER_LINEAR, fill=0):
    """Lit une fenêtre (x0, y0, x1, y1) d'un raster et la ramène à la résolution res."""
    x0, y0, x1, y1 = bounds
    w, h = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    with rasterio.open(path) as s:
        a = s.read(bands, window=from_bounds(x0, y0, x1, y1, s.transform), boundless=True, fill_value=fill)
    a = a.astype(np.float32)
    if a.ndim == 2:
        return a if a.shape == (h, w) else cv2.resize(a, (w, h), interpolation=interp)
    a = np.moveaxis(a, 0, 2)
    return a if a.shape[:2] == (h, w) else cv2.resize(a, (w, h), interpolation=interp)


def push_pull(img, w):
    """Remplit les trous (w = 0) par moyenne pondérée multi-échelle (pyramide « push-pull »)."""
    img = img if img.ndim == 3 else img[..., None]
    niveaux = [(img * w[..., None], w.astype(np.float32))]
    while min(niveaux[-1][1].shape) > 2:
        c, ww = niveaux[-1]
        h, wd = ww.shape
        nh, nw = (h + 1) // 2, (wd + 1) // 2
        c2 = cv2.resize(c, (nw, nh), interpolation=cv2.INTER_AREA)
        w2 = cv2.resize(ww, (nw, nh), interpolation=cv2.INTER_AREA)
        niveaux.append((c2.reshape(nh, nw, -1), w2))
    c, ww = niveaux[-1]
    tot = ww.sum()
    moy = c.reshape(-1, c.shape[-1]).sum(0) / max(tot, 1e-6)
    val = np.where(ww[..., None] > 1e-6, c / np.maximum(ww[..., None], 1e-6), moy)
    for c, ww in reversed(niveaux[:-1]):
        up = cv2.resize(val, (ww.shape[1], ww.shape[0]), interpolation=cv2.INTER_LINEAR).reshape(c.shape)
        a = np.clip(ww * 3.0, 0, 1)[..., None]
        val = a * (c / np.maximum(ww[..., None], 1e-6)) + (1 - a) * up
    return val


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def normales_mnt(z, res, sigma_bas):
    """Normale du MNT dans l'espace tangent de sa version lissée (sigma_bas m) : (H, W, 3),
    composantes (est, nord, haut). Les lignes de z vont du nord au sud."""
    def n_de(a):
        gy, gx = np.gradient(a, res)          # gy : vers le sud
        n = np.dstack([-gx, gy, np.ones_like(a)])
        return n / np.linalg.norm(n, axis=2, keepdims=True)
    hi = n_de(z)
    lo = n_de(ndi.gaussian_filter(z, sigma_bas / res))
    est = np.zeros_like(hi)
    est[..., 0] = 1
    T = est - (est * lo).sum(2, keepdims=True) * lo
    T /= np.linalg.norm(T, axis=2, keepdims=True)
    B = np.cross(lo, T)
    t = np.dstack([(hi * T).sum(2), (hi * B).sum(2), (hi * lo).sum(2)])
    return t / np.linalg.norm(t, axis=2, keepdims=True)


def code_normale(n):
    return np.clip((n * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8)


def jpeg(rgb, q):
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, "JPEG", quality=q, optimize=True)
    return buf.getvalue()


# --- données communes ----------------------------------------------------------------------------
def couche(name):
    path = OUT / "couloir" / f"{name}.geojson"
    out = []
    for f in json.loads(path.read_text(encoding="utf-8"))["features"]:
        if f.get("geometry"):
            g = shapely.transform(shapely.force_2d(shape(f["geometry"])),
                                  lambda c: np.column_stack(TO_L93.transform(c[:, 0], c[:, 1])))
            out.append((g if g.is_valid else g.buffer(0), f["properties"]))
    return out


def part_pin_bdforet(tfv):
    """Part de litière d'aiguilles selon la formation BD Forêt (-1 : lande / garrigue)."""
    t = (tfv or "").replace("\x92", "'").replace("’", "'")
    if t.startswith("Lande"):
        return -1.0
    if "pin" in t or "conifères purs" in t:
        return 0.9
    if "conifères prépondérants" in t:
        return 0.65
    if "feuillus et conifères" in t or "feuillus prépondérants et conifères" in t:
        return 0.4
    if "feuillus" in t or "chênes" in t:
        return 0.1
    return 0.5


def charge_communs():
    ch = m08.chaussee()
    G, D = ch["G"][:, :2], ch["D"][:, :2]
    quads = shapely.polygons([np.array([G[i], G[i + 1], D[i + 1], D[i], G[i]]) for i in range(len(G) - 1)])
    ruban = shapely.union_all(shapely.make_valid(quads))
    with open(OUT / "arbres.csv") as f:
        rows = list(csv.DictReader(f))
    arbres = np.array([[float(r["x_l93"]), float(r["y_l93"]), float(r["diametre_houppier_m"]),
                        1.0 if r["essence"] in ("pin d'Alep", "autre pin (pignon ou maritime)", "cyprès") else 0.0]
                       for r in rows], np.float64)
    foret = [(g, part_pin_bdforet(p.get("tfv"))) for g, p in couche("bdforet_formation_vegetale")]
    return {"ruban": ruban, "arbres": arbres, "foret": foret}


# --- composition d'une dalle ---------------------------------------------------------------------
def burn(geoms, bounds, res, fill=0.0, dtype=np.float32):
    x0, y0, x1, y1 = bounds
    w, h = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    geoms = [(g, v) for g, v in geoms if g is not None and not g.is_empty]
    if not geoms:
        return np.full((h, w), fill, dtype)
    return rasterize(geoms, out_shape=(h, w), transform=from_origin(x0, y1, res, res), fill=fill, dtype=dtype)


def classes_1m(C, bounds, couvert_1m, pente):
    """Poids des matières à 1 m (H, W, 6) pour les sols reconstruits."""
    x0, y0, x1, y1 = bounds
    w, h = int(round(x1 - x0)), int(round(y1 - y0))
    A = C["arbres"]
    sel = (A[:, 0] > x0 - 20) & (A[:, 0] < x1 + 20) & (A[:, 1] > y0 - 20) & (A[:, 1] < y1 + 20)
    pin, feu = np.zeros((h, w), np.float32), np.zeros((h, w), np.float32)
    for x, y, d, conif in A[sel]:
        c, r = int((x - x0)), int((y1 - y))
        cv2.circle(pin if conif else feu, (c, r), max(1, int(round(0.6 * d))), 1.0, -1)
    pin = cv2.GaussianBlur(pin, (0, 0), 2.5)
    feu = cv2.GaussianBlur(feu, (0, 0), 2.0)
    bd = burn([(g, v + 2.0) for g, v in C["foret"]], bounds, 1.0, fill=0.0)    # 0 : hors forêt
    bd_pin = np.where(bd > 0, np.clip(bd - 2.0, 0, 1), 0.5)
    lande = (bd > 0) & (bd < 1.5)
    arbre = np.clip(pin + feu, 0, 1)
    p_pin = np.where(pin + feu > 0.05, pin / np.maximum(pin + feu, 1e-6), bd_pin)
    # litière : sous les houppiers détectés ; sous un couvert sans arbre détecté, selon BD Forêt
    litiere = np.maximum(arbre, np.where(lande, 0.0, 0.6) * cv2.GaussianBlur(couvert_1m, (0, 0), 1.5))
    roche = smoothstep(33, 45, pente)
    litiere = litiere * (1 - roche)
    n = fbm(x0, y1, 1.0, (h, w), 24.0, 3, SEED + 5)
    herbes_part = np.clip(0.35 + 0.35 * n, 0, 1)
    reste = np.clip(1 - litiere - roche, 0, 1)
    W = np.zeros((h, w, len(MATIERES)), np.float32)
    W[..., MATIERES.index("aiguilles")] = litiere * p_pin
    W[..., MATIERES.index("litiere")] = litiere * (1 - p_pin)
    W[..., MATIERES.index("roche")] = roche
    W[..., MATIERES.index("cailloux")] = reste * (1 - herbes_part)
    W[..., MATIERES.index("herbes")] = reste * herbes_part
    return W / np.maximum(W.sum(2, keepdims=True), 1e-6)


def compose(C, bx, by):
    """Image de sol à 20 cm de la dalle (bx, by) et cartes associées (emprise + MARGE)."""
    b = (bx - MARGE, by - MARGE, bx + TILE + MARGE, by + TILE + MARGE)
    bc = (b[0] - CONTEXTE, b[1] - CONTEXTE, b[2] + CONTEXTE, b[3] + CONTEXTE)
    # --- contexte à 1 m : couvert, sol visible, propagation des couleurs, classes
    cx = int(round(CONTEXTE))
    mnt1 = lire(RAW / "mnt_lidarhd_50cm.tif", bc, 1.0, 1, cv2.INTER_AREA, fill=-9999)
    valide1 = mnt1 > -1000
    mnt1f = np.where(valide1, mnt1, np.nanmedian(np.where(valide1, mnt1, np.nan)) if valide1.any() else 0)
    gy, gx = np.gradient(ndi.gaussian_filter(mnt1f, 1.0), 1.0)
    pente1 = np.degrees(np.arctan(np.hypot(gx, gy)))
    # --- grille 20 cm (dalle + contexte réduit de 20 m pour les ombres et la propagation fine)
    b2 = (b[0] - 20, b[1] - 20, b[2] + 20, b[3] + 20)
    rgb = lire(RAW / "ortho_20cm.tif", b2, RES, [1, 2, 3])
    irc = lire(RAW / "ortho_irc_20cm.tif", b2, RES, [1, 2, 3])
    mnt = lire(RAW / "mnt_lidarhd_50cm.tif", b2, RES, 1, fill=-9999)
    mns = lire(RAW / "mns_lidarhd_50cm.tif", b2, RES, 1, fill=-9999)
    valide = (mnt > -1000) & (mns > -1000) & (rgb.sum(2) > 0)
    chm = np.where(valide, ndi.gaussian_filter(np.clip(mns - mnt, 0, 40), 1.5), 0)
    has_irc = irc.sum(2) > 0
    nd = (irc[..., 0] - irc[..., 1]) / (irc[..., 0] + irc[..., 1] + 1e-6)
    gr = (rgb[..., 1] - rgb[..., 0]) / (rgb[..., 1] + rgb[..., 0] + 1e-6)
    ndvi = np.where(has_irc, nd, 1.6 * gr + 0.22)          # recalage moyen (cf. 10_semis_arbres)
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    r_dil = lambda m: int(round(m / RES))                    # noqa: E731
    couvert = cv2.dilate((chm > H_COUVERT).astype(np.uint8), cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * r_dil(0.6) + 1,) * 2)).astype(bool)
    pres_couvert = cv2.dilate(couvert.astype(np.uint8), cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * r_dil(4.0) + 1,) * 2)).astype(bool)
    ruban = burn([(C["ruban"], 1.0)], b2, RES) > 0
    route_dist = ndi.distance_transform_edt(~ruban) * RES
    sol0 = valide & ~couvert & ~ruban
    ref = push_pull(lum, sol0.astype(np.float32) * (lum > 25))[..., 0]       # luminance locale du sol
    ref = cv2.GaussianBlur(ref, (0, 0), 6.0 / RES)
    veg_photo = (ndvi > 0.22) & (lum < 0.85 * ref) & pres_couvert
    ombre = (lum < 0.62 * ref) & ~couvert
    ombre = cv2.dilate(ombre.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    connu = sol0 & ~veg_photo & ~ombre
    connu = cv2.morphologyEx(connu.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)

    # --- couleur de fond : propagation à 1 m sur le grand contexte
    h1, w1 = mnt1.shape
    # le sol visible n'est connu qu'à 20 cm sur b2 : on le ramène à 1 m et on le place dans le contexte
    k = int(round(1.0 / RES))
    o = int(round((b2[0] - bc[0])))
    hh, ww = connu.shape[0] // k, connu.shape[1] // k
    c_f = cv2.resize(connu[:hh * k, :ww * k].astype(np.float32), (ww, hh), interpolation=cv2.INTER_AREA)
    rgb_c = cv2.resize((rgb * connu[..., None])[:hh * k, :ww * k], (ww, hh), interpolation=cv2.INTER_AREA)
    W1 = np.zeros((h1, w1), np.float32)
    S1 = np.zeros((h1, w1, 3), np.float32)
    W1[o:o + hh, o:o + ww] = c_f
    S1[o:o + hh, o:o + ww] = rgb_c
    # hors de la grille 20 cm (contexte lointain) : sol visible estimé à 1 m depuis l'ortho et le MNS
    big_rgb = lire(RAW / "ortho_20cm.tif", bc, 1.0, [1, 2, 3], cv2.INTER_AREA)
    big_chm = np.clip(lire(RAW / "mns_lidarhd_50cm.tif", bc, 1.0, 1, cv2.INTER_AREA, fill=-9999) - mnt1, 0, 40)
    big_lum = big_rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    big_ok = valide1 & (big_chm < 0.3) & (big_lum > 60) & (big_rgb.sum(2) > 0)
    dedans = np.zeros((h1, w1), bool)
    dedans[o:o + hh, o:o + ww] = True
    W1 = np.where(dedans, W1, big_ok.astype(np.float32))
    S1 = np.where(dedans[..., None], S1, big_rgb * big_ok[..., None])
    fond_visible = push_pull(S1 / np.maximum(W1[..., None], 1e-6), W1)
    fond_visible = cv2.GaussianBlur(fond_visible, (0, 0), 1.5)
    d_connu = ndi.distance_transform_edt(W1 < 0.35)                             # m
    couvert_1m = np.zeros((h1, w1), np.float32)
    couvert_1m[o:o + hh, o:o + ww] = cv2.resize(couvert[:hh * k, :ww * k].astype(np.float32), (ww, hh),
                                                interpolation=cv2.INTER_AREA)
    couvert_1m = np.where(dedans, couvert_1m, (big_chm > 1.0).astype(np.float32))
    Wm = classes_1m(C, bc, couvert_1m, pente1)
    pal = np.array([PALETTE[m] for m in MATIERES], np.float32)
    fond_pal = Wm @ pal
    teinte = fbm(bc[0], bc[3], 1.0, (h1, w1), 40.0, 3, SEED + 1)
    fond_pal *= (1 + 0.07 * teinte)[..., None]
    wp = 0.85 * smoothstep(2.0, 14.0, d_connu)
    fond = (1 - wp[..., None]) * fond_visible + wp[..., None] * fond_pal

    # --- retour à la grille 20 cm de la dalle (sans le contexte)
    c0 = int(round((b[0] - bc[0])))
    n1 = int(round(b[2] - b[0]))
    sl1 = (slice(c0, c0 + n1), slice(c0, c0 + n1))
    npx = int(round((b[2] - b[0]) / RES))
    up = lambda a: cv2.resize(np.ascontiguousarray(a[sl1]), (npx, npx), interpolation=cv2.INTER_LINEAR)  # noqa: E731
    fond20 = up(fond)
    W20 = up(Wm)
    pente20 = up(pente1)
    c2 = int(round(20 / RES))
    sl2 = (slice(c2, c2 + npx), slice(c2, c2 + npx))
    # motif à grande échelle des sols reconstruits (20 cm) : bruit + textures CC0 étirées
    mot = 1 + 0.10 * fbm(b[0], b[3], RES, (npx, npx), 6.0, 4, SEED + 2)
    mat20 = C["mat20"]
    X, Y = np.meshgrid(b[0] + (np.arange(npx) + 0.5) * RES, b[3] - (np.arange(npx) + 0.5) * RES)
    X, Y = X.astype(np.float32), Y.astype(np.float32)
    det = np.zeros((npx, npx), np.float32)
    for i, m in enumerate(MATIERES):
        det += W20[..., i] * mat20[m].echantillon(X, Y, 0.7 * i, (0.13 * i, 0.29 * i), "lum")
    recon = fond20 * (mot * (1 + 0.5 * (det - 1)))[..., None]
    a = cv2.GaussianBlur(connu[sl2].astype(np.float32), (0, 0), 1.2)
    a = np.where(connu[sl2], np.maximum(a, 0.5), a * 0.8)
    img = a[..., None] * rgb[sl2] + (1 - a[..., None]) * recon
    img = np.where(valide[sl2][..., None] | (fond20.sum(2) > 0)[..., None], img, recon)
    # nature du sol visible, pour le choix des textures fines
    vis = {"connu": connu[sl2], "ndvi": ndvi[sl2], "lum_rel": lum[sl2] / np.maximum(ref[sl2], 1),
           "route_dist": route_dist[sl2], "chm": chm[sl2], "pente": pente20}
    stats = {"couvert": couvert[sl2], "ombre": ombre[sl2] & ~couvert[sl2], "connu": connu[sl2], "ruban": ruban[sl2]}
    z = mnt[sl2]
    return b, np.clip(img, 0, 255), W20, vis, stats, z


# --- matières fines (bande route) --------------------------------------------------------------------
def poids_fins(W20, vis):
    """Poids des matières à 20 cm pour la bande route : sols reconstruits (W20) corrigés, sur le
    sol visible, par ce que montre la photo (herbe verte ou sèche, roche claire, accotement)."""
    W = W20.copy()
    connu = vis["connu"]
    herbe = smoothstep(0.08, 0.25, vis["ndvi"]) * connu
    roche = smoothstep(1.05, 1.3, vis["lum_rel"]) * smoothstep(0.12, 0.0, vis["ndvi"]) * connu
    caill = connu * (1 - herbe) * (1 - roche)
    vis_w = np.zeros_like(W)
    vis_w[..., MATIERES.index("herbes")] = herbe
    vis_w[..., MATIERES.index("roche")] = roche + 0.3 * smoothstep(30, 45, vis["pente"])
    vis_w[..., MATIERES.index("cailloux")] = caill
    c = connu[..., None].astype(np.float32)
    W = (1 - c) * W + c * vis_w
    grav = smoothstep(1.6, 0.4, vis["route_dist"])
    W *= (1 - grav)[..., None]
    W[..., MATIERES.index("gravier")] += grav
    W = cv2.GaussianBlur(W, (0, 0), 1.5)
    return W / np.maximum(W.sum(2, keepdims=True), 1e-6)


def sous_dalle(C, b, img20, Wf20, connu20, z05, cell, mats, nor_mats):
    """Image 5 cm et relief 10 cm d'une sous-dalle de 100 m."""
    sx, sy = cell
    sb = (sx - SOUS_MARGE, sy - SOUS_MARGE, sx + SOUS + SOUS_MARGE, sy + SOUS + SOUS_MARGE)
    c0, r0 = int(round((sb[0] - b[0]) / RES)), int(round((b[3] - sb[3]) / RES))
    n20 = int(round((sb[2] - sb[0]) / RES))
    crop = lambda a: np.ascontiguousarray(a[r0:r0 + n20, c0:c0 + n20])      # noqa: E731
    res = (sb[2] - sb[0]) / SOUS_PX
    base = cv2.resize(crop(img20), (SOUS_PX, SOUS_PX), interpolation=cv2.INTER_CUBIC)
    Wf = cv2.resize(crop(Wf20), (SOUS_PX, SOUS_PX), interpolation=cv2.INTER_LINEAR)
    kn = cv2.resize(crop(connu20.astype(np.float32)), (SOUS_PX, SOUS_PX), interpolation=cv2.INTER_LINEAR)
    X, Y = np.meshgrid(sb[0] + (np.arange(SOUS_PX) + 0.5) * res, sb[3] - (np.arange(SOUS_PX) + 0.5) * res)
    X, Y = X.astype(np.float32), Y.astype(np.float32)
    # trois échantillonnages par matière (échelle, rotation), mêlés par un bruit monde
    m3 = [bruit(sb[0], sb[3], res, (SOUS_PX, SOUS_PX), 3.7, SEED + 50 + k) for k in range(3)]
    e = np.exp(np.stack(m3) * 3.0)
    e /= e.sum(0)
    comp = math.sqrt(1.0 / 0.45)            # compense la perte de contraste du mélange
    scores, details = [], []
    for i, m in enumerate(MATIERES):
        if Wf[..., i].max() < 0.02:
            scores.append(np.full((SOUS_PX, SOUS_PX), -9, np.float32))
            details.append(None)
            continue
        d = np.zeros((SOUS_PX, SOUS_PX, 3), np.float32)
        h = np.zeros((SOUS_PX, SOUS_PX), np.float32)
        for k, (sc, ang) in enumerate(((1.0, 0.3 + i), (1.37, 2.1 + i), (0.81, 4.0 + i))):
            M = mats[m][k]
            d += e[k][..., None] * M.echantillon(X, Y, ang, (0.17 * k + 0.07 * i, 0.31 * k), "diff")
            h += e[k] * M.echantillon(X, Y, ang, (0.17 * k + 0.07 * i, 0.31 * k), "lum")
        amp, chroma = DETAIL[m]
        moy = mats[m][0].moy
        lum_r = (d @ np.array([0.299, 0.587, 0.114], np.float32)) / float(moy @ np.array([0.299, 0.587, 0.114]))
        rgb_r = d / moy
        r = (1 - chroma) * lum_r[..., None] + chroma * rgb_r
        r = 1 + amp * comp * (r - 1)
        details.append(np.clip(r, 0.25, 2.2))
        scores.append(Wf[..., i] + 0.35 * (h - 1))
    S = np.stack(scores)
    P = np.exp((S - S.max(0)) / 0.06)
    P /= P.sum(0)
    ratio = np.zeros((SOUS_PX, SOUS_PX, 3), np.float32)
    for i, d in enumerate(details):
        if d is not None:
            ratio += P[i][..., None] * d
    # détail un peu atténué sur le sol visible (la photo porte déjà son grain), et vers le bord de la bande
    dist = cv2.resize(crop(C["_route_dist20"]), (SOUS_PX, SOUS_PX), interpolation=cv2.INTER_LINEAR)
    att = (1 - 0.3 * kn) * (1 - 0.5 * smoothstep(12.0, BANDE + 2, dist))
    out = base * (1 + att[..., None] * (ratio - 1))
    couleur = np.clip(out, 0, 255).astype(np.uint8)
    # relief : MNT (0,5 m) agrandi + relief fin des textures
    zc = z05_crop(z05, b, sb)
    zn = cv2.resize(zc, (SOUS_NOR_PX, SOUS_NOR_PX), interpolation=cv2.INTER_CUBIC)
    nres = (sb[2] - sb[0]) / SOUS_NOR_PX
    nm = normales_mnt(zn, nres, 1.0)
    Pn = cv2.resize(np.moveaxis(P, 0, 2), (SOUS_NOR_PX, SOUS_NOR_PX), interpolation=cv2.INTER_AREA)
    Xn, Yn = np.meshgrid(sb[0] + (np.arange(SOUS_NOR_PX) + 0.5) * nres, sb[3] - (np.arange(SOUS_NOR_PX) + 0.5) * nres)
    Xn, Yn = Xn.astype(np.float32), Yn.astype(np.float32)
    nd = np.zeros((SOUS_NOR_PX, SOUS_NOR_PX, 3), np.float32)
    for i, m in enumerate(MATIERES):
        if details[i] is None:
            continue
        nn = nor_mats[m].echantillon(Xn, Yn, 0.3 + i, (0.07 * i, 0.0), "nor")
        nd += Pn[..., i:i + 1] * nn
    nd[..., 2] = np.maximum(nd[..., 2], 0.2)
    nd /= np.linalg.norm(nd, axis=2, keepdims=True)
    # mélange « whiteout » : relief du terrain + relief fin (atténué de moitié)
    nd[..., :2] *= 0.5
    n = np.dstack([nm[..., 0] + nd[..., 0], nm[..., 1] + nd[..., 1], nm[..., 2] * nd[..., 2]])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return sb, couleur, code_normale(n), res


def z05_crop(z05, b, sb):
    """MNT 0,5 m (grille de la dalle, lignes nord -> sud) découpé sur l'emprise sb."""
    c0, r0 = int(round((sb[0] - b[0]) / NOR_RES)), int(round((b[3] - sb[3]) / NOR_RES))
    n = int(round((sb[2] - sb[0]) / NOR_RES))
    return np.ascontiguousarray(z05[r0:r0 + n, c0:c0 + n])


# --- géométrie de 08 ------------------------------------------------------------------------------
def dalles_08(path, ref):
    """{(bx, by): (positions L93 (N,3), triangles)} relus dans un terrain.glb de 08."""
    out = {}
    for name, pos, nrm, _uv, idx in m08.read_glb(path):
        _, bx, by = name.split("_")
        P = np.column_stack([pos[:, 0] + ref["x0"], ref["y0"] - pos[:, 2], pos[:, 1] + ref["z0"]]).astype(np.float64)
        out[(int(bx), int(by))] = (P, np.asarray(idx, np.int64), pos, nrm)
    return out


def decoupe(P, tri, route_dist_fn):
    """Sépare les triangles de la bande route (centroïde à moins de BANDE du bord) par sous-dalle."""
    c = P[tri, :2].mean(1)
    d = route_dist_fn(c[:, 0], c[:, 1])
    bande = d <= BANDE
    cles = np.floor(c / SOUS).astype(int) * int(SOUS)
    groupes = {}
    for k in {tuple(v) for v in cles[bande]}:
        groupes[k] = np.flatnonzero(bande & (cles[:, 0] == k[0]) & (cles[:, 1] == k[1]))
    return np.flatnonzero(~bande), groupes


# --- traitement d'une dalle (processus fils) --------------------------------------------------------
_C = {}


def _init():
    _C.update(charge_communs())
    prov = json.loads((REF / "ressources_cc0.json").read_text(encoding="utf-8"))["textures_sol"]
    tex = {v["role"]: v["taille_physique_m"] for v in prov.values()}
    _C["mat20"] = {m: Matiere(CC0_TEXTURES[m], tex[m], RES, echelle=4.0) for m in MATIERES}
    res5 = (SOUS + 2 * SOUS_MARGE) / SOUS_PX
    _C["mats"] = {m: [Matiere(CC0_TEXTURES[m], tex[m], res5, echelle=s) for s in (1.0, 1.37, 0.81)] for m in MATIERES}
    _C["nor_mats"] = {m: Matiere(CC0_TEXTURES[m], tex[m], (SOUS + 2 * SOUS_MARGE) / SOUS_NOR_PX) for m in MATIERES}


def traite_dalle(args):
    (bx, by), P, tri = args
    t0 = time.time()
    C = _C
    b, img, W20, vis, st, z20 = compose(C, bx, by)
    npx = img.shape[0]
    rd = vis["route_dist"]
    C["_route_dist20"] = rd

    def route_dist_fn(x, y):
        c = np.clip(((x - b[0]) / RES).astype(int), 0, npx - 1)
        r = np.clip(((b[3] - y) / RES).astype(int), 0, npx - 1)
        return rd[r, c]

    base_tri, groupes = decoupe(P, tri, route_dist_fn)
    nom = f"dalle_{bx}_{by}"
    couleur = np.clip(img, 0, 255).astype(np.uint8)
    (TEX / f"{nom}_couleur.jpg").write_bytes(jpeg(couleur, 88))
    # relief de la dalle : MNT 0,5 m
    z05 = lire(RAW / "mnt_lidarhd_50cm.tif", b, NOR_RES, 1, fill=-9999)
    ok = z05 > -1000
    if not ok.all():
        z05 = np.where(ok, z05, ndi.grey_dilation(np.where(ok, z05, -1e9), size=3))
        z05 = np.where(z05 < -1000, np.median(z05[ok]) if ok.any() else 0, z05)
    nm = normales_mnt(z05, NOR_RES, 1.5)
    Image.fromarray(code_normale(nm)).save(TEX / f"{nom}_relief.png", optimize=True)
    # part reconstruite, mesurée là où la dalle porte des triangles (masque des triangles à 1 m)
    m1 = np.zeros((int(round((b[2] - b[0]))),) * 2, np.uint8)
    pts = np.stack([(P[tri, 0] - b[0]), (b[3] - P[tri, 1])], axis=2).round().astype(np.int32)
    cv2.fillPoly(m1, list(pts), 1)
    m20 = cv2.resize(m1, (npx, npx), interpolation=cv2.INTER_NEAREST).astype(bool) & ~st["ruban"]
    tot = max(int(m20.sum()), 1)
    info = {"nom": nom, "emprise_l93": [round(v, 2) for v in b], "dalle_l93": [bx, by, bx + TILE, by + TILE],
            "couleur": f"textures_sol/{nom}_couleur.jpg", "couleur_px": npx, "couleur_m_par_px": RES,
            "relief": f"textures_sol/{nom}_relief.png", "relief_px": int(nm.shape[0]), "relief_m_par_px": NOR_RES,
            "surface_terrain_m2": round(tot * RES * RES),
            "part_sous_couvert": round(float((st["couvert"] & m20).sum() / tot), 3),
            "part_ombre_reconstruite": round(float((st["ombre"] & m20).sum() / tot), 3),
            "part_reconstruite": round(float((~st["connu"] & m20).sum() / tot), 3),
            "triangles_hors_bande": int(len(base_tri)), "sous_dalles": []}
    Wf20 = poids_fins(W20, vis)
    for (sx, sy), sel in sorted(groupes.items()):
        sb, col, nor, res = sous_dalle(C, b, img, Wf20, vis["connu"], z05, (sx, sy), C["mats"], C["nor_mats"])
        sn = f"sous_{sx}_{sy}"
        (TEX / f"{sn}_couleur.jpg").write_bytes(jpeg(col, 85))
        (TEX / f"{sn}_relief.jpg").write_bytes(jpeg(nor, 92))
        r0, c0 = int(round((b[3] - sb[3]) / RES)), int(round((sb[0] - b[0]) / RES))
        n20 = int(round((sb[2] - sb[0]) / RES))
        mm = m20[r0:r0 + n20, c0:c0 + n20]
        info["sous_dalles"].append({"nom": sn, "emprise_l93": [round(v, 2) for v in sb], "cellule_l93": [sx, sy, sx + SOUS, sy + SOUS],
                                    "couleur": f"textures_sol/{sn}_couleur.jpg", "couleur_px": SOUS_PX,
                                    "couleur_m_par_px": round(res, 5), "relief": f"textures_sol/{sn}_relief.jpg",
                                    "relief_px": SOUS_NOR_PX, "relief_m_par_px": round((sb[2] - sb[0]) / SOUS_NOR_PX, 4),
                                    "triangles": int(len(sel)),
                                    "part_reconstruite": round(float((~st["connu"][r0:r0 + n20, c0:c0 + n20] & mm).sum()
                                                                     / max(mm.sum(), 1)), 3)})
    info["duree_s"] = round(time.time() - t0, 1)
    print(f"  {nom} : {len(groupes)} sous-dalles, {info['part_reconstruite'] * 100:.0f} % reconstruit, {info['duree_s']} s",
          flush=True)
    return info, base_tri, {k: v for k, v in groupes.items()}


# --- écriture glb (images externes ou intégrées, normal map) ---------------------------------------
def ecrire_glb(path, meshes, generator="acr-grand-caunet 14_textures_sol.py"):
    """meshes : dict(name, pos, nrm, uv, idx, couleur, relief) ; couleur / relief = str (uri
    relative) ou bytes (image intégrée, JPEG ou PNG) ou None ; ou color (RVBA)."""
    gl = {"asset": {"version": "2.0", "generator": generator}, "scene": 0,
          "scenes": [{"nodes": list(range(len(meshes)))}], "nodes": [], "meshes": [], "accessors": [],
          "bufferViews": [], "materials": [], "buffers": []}
    blob = bytearray()

    def view(data, target=None):
        while len(blob) % 4:
            blob.append(0)
        v = {"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)}
        if target:
            v["target"] = target
        blob.extend(data)
        gl["bufferViews"].append(v)
        return len(gl["bufferViews"]) - 1

    def acc(arr, kind, target, minmax=False):
        a = {"bufferView": view(arr.tobytes(), target),
             "componentType": {np.float32: 5126, np.uint32: 5125, np.uint16: 5123}[arr.dtype.type],
             "count": len(arr), "type": kind}
        if minmax:
            a["min"], a["max"] = arr.min(0).tolist(), arr.max(0).tolist()
        gl["accessors"].append(a)
        return len(gl["accessors"]) - 1

    def texture(src):
        if isinstance(src, str):
            im = {"uri": src, "mimeType": "image/png" if src.endswith(".png") else "image/jpeg"}
        else:
            im = {"bufferView": view(src), "mimeType": "image/png" if src[:4] == b"\x89PNG" else "image/jpeg"}
        gl.setdefault("images", []).append(im)
        gl.setdefault("samplers", [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}])
        gl.setdefault("textures", []).append({"sampler": 0, "source": len(gl["images"]) - 1})
        return len(gl["textures"]) - 1

    for m in meshes:
        mat = {"name": m["name"], "pbrMetallicRoughness": {"metallicFactor": 0.0, "roughnessFactor": m.get("rough", 0.95)}}
        if m.get("couleur") is not None:
            mat["pbrMetallicRoughness"]["baseColorTexture"] = {"index": texture(m["couleur"])}
        else:
            mat["pbrMetallicRoughness"]["baseColorFactor"] = m.get("color", [0.5, 0.5, 0.5, 1.0])
        if m.get("relief") is not None:
            mat["normalTexture"] = {"index": texture(m["relief"]), "scale": 1.0}
        if m.get("double"):
            mat["doubleSided"] = True
        gl["materials"].append(mat)
        attrs = {"POSITION": acc(m["pos"].astype(np.float32), "VEC3", 34962, True),
                 "NORMAL": acc(m["nrm"].astype(np.float32), "VEC3", 34962)}
        if m.get("uv") is not None:
            attrs["TEXCOORD_0"] = acc(m["uv"].astype(np.float32), "VEC2", 34962)
        idx = m["idx"].ravel().astype(np.uint16 if len(m["pos"]) < 65536 else np.uint32)
        prim = {"attributes": attrs, "indices": acc(idx, "SCALAR", 34963), "material": len(gl["materials"]) - 1, "mode": 4}
        gl["meshes"].append({"name": m["name"], "primitives": [prim]})
        gl["nodes"].append({"name": m["name"], "mesh": len(gl["meshes"]) - 1})
    while len(blob) % 4:
        blob.append(0)
    gl["buffers"].append({"byteLength": len(blob)})
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    with open(path, "wb") as f:
        f.write(b"glTF" + np.array([2, 12 + 8 + len(js) + 8 + len(blob)], "<u4").tobytes())
        f.write(np.array([len(js), 0x4E4F534A], "<u4").tobytes() + js)
        f.write(np.array([len(blob), 0x004E4942], "<u4").tobytes() + bytes(blob))


def lire_glb(path):
    """Relit un glb (indices 16 ou 32 bits) : liste de dict(name, pos, nrm, uv, idx, images)."""
    b = Path(path).read_bytes()
    n = int(np.frombuffer(b, "<u4", 1, 12)[0])
    gl = json.loads(b[20:20 + n])
    binoff = 20 + n + 8

    def arr(i):
        a = gl["accessors"][i]
        v = gl["bufferViews"][a["bufferView"]]
        dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}[a["componentType"]]
        k = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[a["type"]]
        return np.frombuffer(b, dt, a["count"] * k, binoff + v.get("byteOffset", 0)).reshape(-1, k)

    out = []
    for m in gl["meshes"]:
        p = m["primitives"][0]
        mat = gl["materials"][p["material"]]
        ims = []
        for key in ("baseColorTexture",):
            t = mat["pbrMetallicRoughness"].get(key)
            if t:
                ims.append(gl["images"][gl["textures"][t["index"]]["source"]])
        if "normalTexture" in mat:
            ims.append(gl["images"][gl["textures"][mat["normalTexture"]["index"]]["source"]])
        out.append({"name": m["name"], "pos": arr(p["attributes"]["POSITION"]), "nrm": arr(p["attributes"]["NORMAL"]),
                    "uv": arr(p["attributes"]["TEXCOORD_0"]) if "TEXCOORD_0" in p["attributes"] else None,
                    "idx": arr(p["indices"]).reshape(-1, 3).astype(np.int64), "images": ims})
    return out


def uv_de(P, e):
    return np.column_stack([(P[:, 0] - e[0]) / (e[2] - e[0]), (e[3] - P[:, 1]) / (e[3] - e[1])]).astype(np.float32)


def sous_maillage(P, pos, nrm, tri, sel):
    used, inv = np.unique(tri[sel], return_inverse=True)
    return P[used], pos[used], nrm[used], inv.reshape(-1, 3)


# --- glb complet et aperçu ---------------------------------------------------------------------------
def glb_complet(dalles, manifeste, decoupes):
    meshes = []
    for d in manifeste["dalles"]:
        bx, by = d["dalle_l93"][:2]
        P, tri, pos, nrm = dalles[(bx, by)]
        base_tri, groupes = decoupes[d["nom"]]
        Pm, pm, nm, ti = sous_maillage(P, pos, nrm, tri, base_tri)
        meshes.append({"name": d["nom"], "pos": pm, "nrm": nm, "uv": uv_de(Pm, d["emprise_l93"]), "idx": ti,
                       "couleur": d["couleur"], "relief": d["relief"]})
        for s in d["sous_dalles"]:
            sx, sy = s["cellule_l93"][:2]
            Pm, pm, nm, ti = sous_maillage(P, pos, nrm, tri, groupes[(sx, sy)])
            meshes.append({"name": s["nom"], "pos": pm, "nrm": nm, "uv": uv_de(Pm, s["emprise_l93"]), "idx": ti,
                           "couleur": s["couleur"], "relief": s["relief"]})
    ecrire_glb(MOD / "terrain_sol.glb", meshes)
    return meshes


def glb_apercu(manifeste, ref):
    """Géométrie légère de 08 (apercu/terrain.glb), images de base réduites à 512 px, intégrées."""
    dalles = dalles_08(MOD / "apercu" / "terrain.glb", ref)
    meshes = []
    for d in manifeste["dalles"]:
        bx, by = d["dalle_l93"][:2]
        if (bx, by) not in dalles:
            continue
        P, tri, pos, nrm = dalles[(bx, by)]
        im = Image.open(TEX / Path(d["couleur"]).name).resize((512, 512), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=80, optimize=True)
        meshes.append({"name": d["nom"], "pos": pos, "nrm": nrm, "uv": uv_de(P, d["emprise_l93"]), "idx": tri,
                       "couleur": buf.getvalue()})
    ecrire_glb(MOD / "apercu" / "terrain_sol.glb", meshes)


# --- contrôles relus sur disque -------------------------------------------------------------------------
def controle(manifeste, ref):
    r = {}
    ms = lire_glb(MOD / "terrain_sol.glb")
    orig = m08.read_glb(MOD / "terrain.glb")
    pos = np.vstack([m["pos"] for m in ms])
    nrm = np.vstack([m["nrm"] for m in ms])
    uv = np.vstack([m["uv"] for m in ms])
    ntri = sum(len(m["idx"]) for m in ms)
    r["terrain_sol_glb"] = {
        "taille_mo": round((MOD / "terrain_sol.glb").stat().st_size / 1e6, 2), "maillages": len(ms),
        "triangles": int(ntri), "triangles_terrain_08": int(sum(len(o[4]) for o in orig)),
        "nan": bool(np.isnan(pos).any() or np.isnan(nrm).any() or np.isnan(uv).any()),
        "normales_unitaires_ecart_max": round(float(np.abs(np.linalg.norm(nrm, axis=1) - 1).max()), 4),
        "normales_vers_le_haut_pct": round(float((nrm[:, 1] > 0).mean() * 100), 2),
        "uv_hors_0_1": int(((uv < -1e-4) | (uv > 1 + 1e-4)).any(1).sum()),
        "images_manquantes": sorted({i["uri"] for m in ms for i in m["images"] if "uri" in i
                                     and not (MOD / i["uri"]).exists()})}
    # raccords : sommets communs (même position) entre maillages voisins, déjà garantis par la
    # réutilisation de la géométrie ; on vérifie que l'ensemble des sommets est inchangé
    p08 = np.unique(np.round(np.vstack([o[1] for o in orig]), 3), axis=0)
    p14 = np.unique(np.round(pos, 3), axis=0)
    r["terrain_sol_glb"]["sommets_identiques_a_08"] = bool(len(p08) == len(p14) and np.array_equal(p08, p14))
    # images : tailles, valeurs, couleur moyenne des parts reconstruites
    tailles, moy = [], []
    for d in manifeste["dalles"]:
        for f in [d["couleur"], d["relief"]] + [s[k] for s in d["sous_dalles"] for k in ("couleur", "relief")]:
            p = MOD / f
            tailles.append(p.stat().st_size)
        a = np.asarray(Image.open(MOD / d["couleur"]))
        moy.append(a.reshape(-1, 3).mean(0))
    nmap = np.asarray(Image.open(MOD / manifeste["dalles"][0]["relief"])).astype(float) / 127.5 - 1
    r["images"] = {"nombre": len(tailles), "total_mo": round(sum(tailles) / 1e6, 1), "max_mo": round(max(tailles) / 1e6, 2),
                   "couleur_moyenne_dalles_rvb": np.round(np.mean(moy, 0)).tolist(),
                   "relief_norme_moyenne": round(float(np.linalg.norm(nmap, axis=2).mean()), 3),
                   "relief_z_min": round(float(nmap[..., 2].min()), 3)}
    # coutures : écart de couleur de part et d'autre des limites de dalles (même pixel monde)
    ec = []
    idx = {tuple(d["dalle_l93"][:2]): d for d in manifeste["dalles"]}
    for (bx, by), d in idx.items():
        if (bx + int(TILE), by) in idx:
            a = np.asarray(Image.open(MOD / d["couleur"])).astype(float)
            bimg = np.asarray(Image.open(MOD / idx[(bx + int(TILE), by)]["couleur"])).astype(float)
            ca = int(round((bx + TILE - 2 - d["emprise_l93"][0]) / RES))
            cb = int(round((bx + TILE - 2 - idx[(bx + int(TILE), by)]["emprise_l93"][0]) / RES))
            ec.append(float(np.abs(a[:, ca - 5:ca + 5].mean(1) - bimg[:, cb - 5:cb + 5].mean(1)).mean()))
    r["coutures_entre_dalles_ecart_moyen_rvb"] = round(float(np.mean(ec)), 2) if ec else None
    a = MOD / "apercu" / "terrain_sol.glb"
    r["apercu_glb_mo"] = round(a.stat().st_size / 1e6, 2) if a.exists() else None
    return r


def planche(manifeste):
    """Avant / après sur quelques extraits (photo brute, sol reconstruit 20 cm, détail 5 cm)."""
    FIG5.mkdir(parents=True, exist_ok=True)
    ch = m08.chaussee()
    vues = []
    for pk in (1000, 2225, 3650, 5000, 6000):
        i = int(np.argmin(np.abs(ch["pk"] - pk)))
        vues.append((pk, ch["A"][i, 0], ch["A"][i, 1]))
    W = 360
    out = Image.new("RGB", (W * 3 + 20, (W + 4) * len(vues)), (255, 255, 255))
    for k, (pk, x, y) in enumerate(vues):
        d = next((d for d in manifeste["dalles"] if d["dalle_l93"][0] <= x < d["dalle_l93"][2]
                  and d["dalle_l93"][1] <= y < d["dalle_l93"][3]), None)
        if d is None:
            continue
        e = d["emprise_l93"]
        h = 40.0
        ph = lire(RAW / "ortho_20cm.tif", (x - h, y - h, x + h, y + h), RES, [1, 2, 3]).astype(np.uint8)
        im = np.asarray(Image.open(MOD / d["couleur"]))
        c0, r0 = int((x - h - e[0]) / RES), int((e[3] - y - h) / RES)
        n = int(2 * h / RES)
        cr = im[r0:r0 + n, c0:c0 + n]
        s = next((s for s in d["sous_dalles"] if s["emprise_l93"][0] <= x - 6 < s["emprise_l93"][2] - 12
                  and s["emprise_l93"][1] + 12 <= y + 6 < s["emprise_l93"][3]), None)
        out.paste(Image.fromarray(ph).resize((W, W)), (0, k * (W + 4)))
        out.paste(Image.fromarray(cr).resize((W, W)), (W + 10, k * (W + 4)))
        if s:
            si = Image.open(MOD / s["couleur"])
            se = s["emprise_l93"]
            r = s["couleur_m_par_px"]
            cc, rr = int((x - 6 - se[0]) / r), int((se[3] - y - 6) / r)
            out.paste(si.crop((cc, rr, cc + int(12 / r), rr + int(12 / r))).resize((W, W)), (2 * W + 20, k * (W + 4)))
    out.save(FIG5 / "sol_avant_apres.jpg", quality=85, optimize=True)


def main():
    t0 = time.time()
    TEX.mkdir(parents=True, exist_ok=True)
    telecharge_cc0()
    ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    dalles = dalles_08(MOD / "terrain.glb", ref)
    seulement_apercu = "apercu" in sys.argv[1:]
    man_path = OUT / "textures_sol.json"
    if "essai" in sys.argv[1:]:                      # une dalle, pour la mise au point
        _init()
        k = (int(sys.argv[2]), int(sys.argv[3]))
        P, tri, _, _ = dalles[k]
        traite_dalle((k, P, tri))
        return
    if seulement_apercu:
        manifeste = json.loads(man_path.read_text(encoding="utf-8"))
    else:
        print(f"{len(dalles)} dalles de 08 ; traitement sur {min(4, os.cpu_count())} processus")
        taches = [((bx, by), P, tri) for (bx, by), (P, tri, _, _) in sorted(dalles.items())]
        with Pool(min(4, os.cpu_count()), initializer=_init) as pool:
            res = pool.map(traite_dalle, taches, chunksize=1)
        decoupes = {info["nom"]: (bt, gr) for info, bt, gr in res}
        infos = [info for info, _, _ in res]
        tot = sum(i["surface_terrain_m2"] for i in infos)
        manifeste = {
            "description": "Images de sol « sous les arbres » des dalles du terrain de 08 (14_textures_sol.py)",
            "repere": "Lambert-93 (EPSG:2154), mètres ; emprise = [x_min, y_min, x_max, y_max] couverte par l'image",
            "uv": "u = (x - x_min) / (x_max - x_min), v = (y_max - y) / (y_max - y_min) (ligne 0 de l'image = nord)",
            "couleur": "sRVB, JPEG ; sol visible = photo BD ORTHO 20 cm, sol sous couvert ou à l'ombre = reconstruit",
            "relief": ("normal map en espace tangent, convention glTF / OpenGL (Y+) : rouge = est, vert = nord, bleu = haut ; "
                       "pour Unreal (DirectX), cocher « Flip Green Channel » à l'import"),
            "dimensions_non_puissance_de_2": ("les images de dalle font 2660 px (532 m à 20 cm) : à l'import dans Unreal, "
                                              "régler « Power Of Two Mode » sur « Stretch to power of two » (4096) ou "
                                              "les réduire à 2048 px (26 cm) ; les sous-dalles font 2048 px"),
            "bande_route": f"triangles dont le centre est à moins de {BANDE} m du bord de chaussée : sous-dalles de "
                           f"{SOUS:.0f} m, image {SOUS_PX} px ({(SOUS + 2 * SOUS_MARGE) / SOUS_PX * 100:.1f} cm/px)",
            "palette_sols_reconstruits_rvb": PALETTE,
            "matieres_cc0": CC0_TEXTURES, "provenance": "data/reference/ressources_cc0.json",
            "glb": {"complet": "modele/terrain_sol.glb (images externes, chemins relatifs à modele/)",
                    "apercu": "modele/apercu/terrain_sol.glb (images 512 px intégrées, sans sous-dalles)"},
            "totaux": {"dalles": len(infos), "sous_dalles": sum(len(i["sous_dalles"]) for i in infos),
                       "surface_terrain_m2": tot,
                       "part_reconstruite": round(sum(i["part_reconstruite"] * i["surface_terrain_m2"] for i in infos) / tot, 3),
                       "part_sous_couvert": round(sum(i["part_sous_couvert"] * i["surface_terrain_m2"] for i in infos) / tot, 3),
                       "part_ombre_reconstruite": round(sum(i["part_ombre_reconstruite"] * i["surface_terrain_m2"]
                                                            for i in infos) / tot, 3)},
            "dalles": infos}
        glb_complet(dalles, manifeste, decoupes)
    glb_apercu(manifeste, ref)
    manifeste["controle"] = controle(manifeste, ref)
    man_path.write_text(json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8")
    planche(manifeste)
    print(json.dumps({"totaux": manifeste["totaux"], "controle": manifeste["controle"]}, ensure_ascii=False, indent=1))
    print(f"durée : {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
