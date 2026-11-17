"""Étape 13 - Paysage lointain : anneau de terrain autour du couloir, jusqu'à l'horizon.

Pourquoi jusqu'à 30 km : depuis la route, l'horizon est fermé à moins de 3 km dans 81 % des
directions, mais sur la D1 (PK 4 250 à 6 700) il est fait, au nord-est, par la crête de la
Sainte-Baume (1 135 m, à 10-24 km) et, au nord-ouest, par les reliefs au-delà d'Aubagne
(jusqu'à 28 km). Calcul : depuis l'œil (axe + 1,1 m) tous les 50 m de PK, 360 directions,
MNT RGE ALTI à 50 m sur 80 x 80 km, courbure terrestre et réfraction (k = 0,13) ; 8 % des
couples (PK, direction) ont leur horizon au-delà de 10 km, 0,7 % au-delà de 20 km, aucun
au-delà de 30 km. La MER (golfe de La Ciotat, 7 à 9 km au sud-ouest) n'est visible d'aucun
point de la route, même sans arbres : la crête du Grand Caunet et de la Canaille la cache.
Elle est donc seulement présente comme surface plate à l'altitude 0, texturée par l'ortho,
dans l'anneau (pas de plan d'eau animé). Ce calcul est refait par ce script (rapport).

Entrées : modele/terrain.glb et modele/apercu/terrain.glb (bord extérieur du terrain de 08,
          repris sommet pour sommet), data/raw/mnt_lidarhd_50cm.tif (raccord), Géoplateforme
          IGN (Licence Ouverte) : RGE ALTI (ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES) à 5 m jusqu'à
          4,5 km de l'axe et à 25 m au-delà, hauteur de végétation LiDAR HD (MNH) aux mêmes pas,
          BD ORTHO (HR.ORTHOIMAGERY.ORTHOPHOTOS) de 1 m (près) à 10 m (au-delà de 10 km) par pixel
Maillage : une seule triangulation (pas de fissure entre niveaux), pas croissant avec la
          distance à l'axe : 5 m jusqu'à 400 m, 10 m jusqu'à 2 km, 20 m jusqu'à 4 km, 50 m
          jusqu'à 10 km, 100 m jusqu'à 20 km, 200 m jusqu'à 30 km.
Raccord : le bord intérieur de l'anneau EST le bord extérieur du terrain de 08 (mêmes sommets,
          mêmes positions) : ni marche ni trou. Jusqu'à 280 m de l'axe, l'altitude vient du MNT
          LiDAR (celui de 08), puis vient du MNT LiDAR HD à 2 m jusqu'à 2 km, puis passe au RGE ALTI.
Altitude : sol + hauteur de la végétation (MNH x 0,9, lissé), introduite de 140 à 220 m de l'axe :
          au loin, on voit le dessus des bois, pas le sol ; au bord du couloir, la surface
          rejoint le sol sous les arbres 3D. Au-delà de 1 km, abaissement dû à la courbure de
          la Terre (0,87 d² / 2R, d depuis le centre de l'ES : 42 m à 25 km), pour que les crêtes
          lointaines se voient à leur vraie hauteur angulaire dans un monde de jeu plat.
Sorties : modele/lointain.glb (complet, non versionné), modele/apercu/lointain.glb (léger),
          data/raw/lointain/ (bruts), modele/apercu/lointain_controle.json
"""
import io
import json
import math
import sys
import time
from pathlib import Path

import importlib.util
import numpy as np
import rasterio
import shapely
from PIL import Image
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from scipy.ndimage import map_coordinates
from scipy.spatial import Delaunay, cKDTree
from shapely.geometry import LineString, Polygon

from acr_geo import RAW, ROOT, wms_tile, LAYER_MNS, LAYER_MNT, LAYER_ORTHO

_spec = importlib.util.spec_from_file_location("modele_3d", Path(__file__).with_name("08_modele_3d.py"))
m08 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m08)
_spec14 = importlib.util.spec_from_file_location("textures_sol", Path(__file__).with_name("14_textures_sol.py"))
m14 = importlib.util.module_from_spec(_spec14)
_spec14.loader.exec_module(m14)

MOD = ROOT / "modele"
BRUT = RAW / "lointain"
LAYER_ALTI = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"                  # RGE ALTI 1 m / 5 m
LAYER_MNH = "IGNF_LIDAR-HD_MNH_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93"   # hauteur de végétation
R_PROCHE = 4500.0          # m de l'axe : RGE ALTI à 5 m
R_MAX = 30000.0            # m de l'axe
RAYON_TERRE = 6371000.0
K_REFRACTION = 0.13
VERSIONS = {   # (bandes (distance max à l'axe, pas)), (px texture près / moyen / loin)
    # pas de 10 m jusqu'à 2 km (1,2 km jusqu'au 14/11/2026) : toute la bande où l'altitude vient du relevé laser
    "complet": ([(400, 5), (2000, 10), (4000, 20), (10000, 50), (20000, 100), (R_MAX, 200)], (1024, 1024, 512)),
    "apercu": ([(400, 16), (1200, 40), (4000, 80), (10000, 200), (20000, 400), (R_MAX, 800)], (256, 128, 64)),
}
# Vu en jeu le 13/11/2026 (quatrième version) : « les reliefs moyennement lointains font tas de sable avec une photo
# de dessus ». La surface passait à hauteur de cime dès 140 à 220 m de l'axe : une nappe lisse d'où ne sortaient que
# quelques cimes. Elle reste désormais au niveau du SOL jusqu'à 450 m, où des arbres et des buissons entiers sont
# plantés à la densité du relevé laser (16_paquet_unreal.py, ARBRES_LOIN), et ne monte à hauteur de cime qu'ensuite.
CANOPEE = (450.0, 650.0)   # m : introduction de la hauteur de végétation
# Falaises : le pas de 5, 10 puis 20 m écrase les barres rocheuses en talus. Jusqu'à 4 km de l'axe, là où la pente du
# RGE ALTI à 5 m dépasse RAIDE_DEG, des points sont ajoutés au demi-pas (2,5 m à moins de 400 m).
RAIDE_DEG = 30.0
LIDAR = (550.0, 650.0)     # m : passage du MNT LiDAR (50 cm) au RGE ALTI (5 m) ; 220 à 280 m jusqu'au 13/11/2026.
                           # Le relevé laser couvre toute cette bande : barres rocheuses et ravins y gardent leur forme.
# Redit par le directeur le 14/11/2026 : falaises lointaines « floues, sombres, trop petites », relief « géométrique ». Les
# grandes barres calcaires vues de la route (PK 3900 à 4300) sont à 0,8-2 km : au-delà de LIDAR[1], le RGE ALTI à 5 m
# les écrasait en talus. Le MNT LiDAR HD est donc pris aussi à 2 m (Géoplateforme, même flux WMS que l'étape 03, dalles
# de 2 km) jusqu'à LIDAR_LOIN_M de l'axe, et sert d'altitude jusqu'à LIDAR_2M (fondu vers le RGE ALTI au-delà, et
# sur 60 m avant le bord de son image ou d'un trou). Le MNS au même pas est gardé à côté (MNS - MNT : hauteur des arbres).
LIDAR_LOIN_M = 2200.0      # m de l'axe : emprise du MNT et du MNS LiDAR HD à 2 m (data/raw/lointain/m?s_lidarhd_2m.tif)
LIDAR_2M = (1950.0, 2150.0)  # m : passage du MNT LiDAR à 2 m au RGE ALTI à 5 m
# Maillage des barres rocheuses : la pente est lue sur ce MNT à 2 m (base de 2 x RAIDE_BASE_M), et plus sur le RGE ALTI.
# Au-delà de RAIDE_DEG, demi-pas ; au-delà de RAIDE_FORT_DEG (paroi), quart de pas (5 m dans la bande à 20 m, 2,5 m dans
# celle à 10 m), jamais sous RAIDE_PAS_MIN_M (le relevé n'a pas plus fin).
RAIDE_FORT_DEG = 50.0
RAIDE_BASE_M = 4.0
RAIDE_PAS_MIN_M = 2.5
TRES_PRES_M = 600.0        # m de l'axe : en deçà, image des dalles à 50 cm par point


# --- téléchargements -----------------------------------------------------------------------------
def mosaique(layer, path, bounds, res, dalle_px=1000):
    """Mosaïque GeoTIFF float32 d'une couche d'altitude WMS (mise en cache dans data/raw/lointain)."""
    if path.exists():
        with rasterio.open(path) as s:
            return s.read(1), s.transform
    x0, y0, x1, y1 = bounds
    w, h = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    a = np.full((h, w), -99999.0, np.float32)
    n, k = math.ceil(w / dalle_px) * math.ceil(h / dalle_px), 0
    for r0 in range(0, h, dalle_px):
        for c0 in range(0, w, dalle_px):
            k += 1
            cw, rh = min(dalle_px, w - c0), min(dalle_px, h - r0)
            tx, ty = x0 + c0 * res, y1 - r0 * res
            raw = wms_tile(layer, tx, ty - rh * res, tx + cw * res, ty, res)
            with rasterio.open(io.BytesIO(raw)) as s:
                a[r0:r0 + rh, c0:c0 + cw] = s.read(1)[:rh, :cw]
            print(f"\r{path.name} : dalle {k}/{n}", end="", flush=True)
    print()
    tr = from_origin(x0, y1, res, res)
    with rasterio.open(path, "w", driver="GTiff", width=w, height=h, count=1, dtype="float32", crs="EPSG:2154",
                       transform=tr, nodata=-99999.0, compress="deflate", predictor=3, tiled=True) as d:
        d.write(a, 1)
    return a, tr


def ortho(bounds, px, cache):
    """Image BD ORTHO (JPEG) d'une emprise, mise en cache."""
    if cache.exists():
        return Image.open(cache).convert("RGB")
    x0, y0, x1, y1 = bounds
    raw = wms_tile(LAYER_ORTHO, x0, y0, x1, y1, (x1 - x0) / px, fmt="image/jpeg")
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    if im.size != (px, px):
        im = im.resize((px, px), Image.LANCZOS)
    cache.parent.mkdir(parents=True, exist_ok=True)
    im.save(cache, quality=90)
    return im


class Raster:
    def __init__(self, a, tr, nodata=-1000):
        self.a, self.tr = a, tr
        self.ok = a > nodata

    def __call__(self, x, y, order=1):
        c = (np.asarray(x) - self.tr.c) / self.tr.a - 0.5
        r = (self.tr.f - np.asarray(y)) / -self.tr.e - 0.5
        return map_coordinates(self.a, [r, c], order=order, mode="nearest")

    def dedans(self, x, y, marge=2):
        c = (np.asarray(x) - self.tr.c) / self.tr.a
        r = (self.tr.f - np.asarray(y)) / -self.tr.e
        return (c >= marge) & (r >= marge) & (c < self.a.shape[1] - marge) & (r < self.a.shape[0] - marge)


# --- bord extérieur du terrain de 08 -------------------------------------------------------------------
def bord_exterieur(path, ref):
    """Boucle du bord extérieur du terrain de 08 : sommets (L93 x, y, z) dans l'ordre."""
    ms = m08.read_glb(path)
    pos = np.vstack([m[1] for m in ms]).astype(np.float64)
    off = np.cumsum([0] + [len(m[1]) for m in ms])
    tri = np.vstack([m[4].astype(np.int64) + off[i] for i, m in enumerate(ms)])
    # fusion des sommets identiques d'une dalle à l'autre
    key = np.round(pos * 1000).astype(np.int64)
    _, uid, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    P = pos[uid]
    T = inv[tri]
    e = np.sort(np.vstack([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1)
    ue, cnt = np.unique(e, axis=0, return_counts=True)
    b = ue[cnt == 1]
    voisins = {}
    for a, c in b:
        voisins.setdefault(a, []).append(c)
        voisins.setdefault(c, []).append(a)
    # parcours des boucles (sommets « pincés » : on prend le voisin non visité qui tourne le plus à droite)
    vus_aretes = set()
    boucles = []
    for a0, c0 in b:
        if (a0, c0) in vus_aretes or (c0, a0) in vus_aretes:
            continue
        boucle = [a0, c0]
        vus_aretes.add((a0, c0))
        while True:
            prev, cur = boucle[-2], boucle[-1]
            cands = [v for v in voisins[cur] if (cur, v) not in vus_aretes and (v, cur) not in vus_aretes]
            if not cands:
                break
            if len(cands) > 1:                 # sommet pincé : virage le plus à droite
                d0 = P[cur, [0, 2]] - P[prev, [0, 2]]
                ang = []
                for v in cands:
                    d1 = P[v, [0, 2]] - P[cur, [0, 2]]
                    ang.append(math.atan2(d0[0] * d1[1] - d0[1] * d1[0], float(d0 @ d1)))
                nxt = cands[int(np.argmin(ang))]
            else:
                nxt = cands[0]
            vus_aretes.add((cur, nxt))
            if nxt == boucle[0]:
                break
            boucle.append(nxt)
        boucles.append(boucle)
    aires = [abs(Polygon(P[bc][:, [0, 2]]).area) if len(bc) > 2 else 0 for bc in boucles]
    ext = boucles[int(np.argmax(aires))]
    G = P[ext]
    L = np.column_stack([G[:, 0] + ref["x0"], ref["y0"] - G[:, 2], G[:, 1] + ref["z0"]])
    return L, {"boucles_de_bord": len(boucles), "sommets_bord_exterieur": len(ext),
               "aretes_de_bord_total": int(len(b)), "gltf": G.astype(np.float32)}


# --- maillage ------------------------------------------------------------------------------------------
def points_anneau(axe, bord, bandes, raide=None):
    """Grilles imbriquées (pas multiples les uns des autres) selon la distance à l'axe. `raide(x, y)` : pente en
    degrés ; là où elle dépasse RAIDE_DEG, la grille est doublée (bandes de pas 10 et 20 m)."""
    line = LineString(axe)
    poly = shapely.make_valid(Polygon(bord[:, :2]))
    shapely.prepare(poly)
    ligne_bord = LineString(np.vstack([bord[:, :2], bord[:1, :2]]))
    shapely.prepare(ligne_bord)
    x0, y0 = axe.min(0) - R_MAX
    x1, y1 = axe.max(0) + R_MAX
    pts = []
    lo = 0.0
    for dmax, pas in bandes:
        # emprise utile de la bande : boîte de l'axe élargie de dmax
        bx0, by0 = (np.floor((axe.min(0) - dmax) / pas) * pas)
        bx1, by1 = axe.max(0) + dmax
        xs = np.arange(bx0, bx1 + pas, pas)
        ys = np.arange(by0, by1 + pas, pas)
        X, Y = np.meshgrid(xs, ys)
        X, Y = X.ravel(), Y.ravel()
        # filtre grossier par boîte puis distance exacte
        d = shapely.distance(line, shapely.points(X, Y)) if len(X) < 3e6 else None
        if d is None:
            # grande grille : distance à une version simplifiée de l'axe (erreur < 20 m, sans effet à ce pas)
            d = shapely.distance(line.simplify(20), shapely.points(X, Y))
        sel = (d > lo) & (d <= dmax)
        pts.append(np.column_stack([X[sel], Y[sel], d[sel]]))
        if raide is not None and pas <= 20:
            # points intermédiaires sur les versants raides : demi-pas (milieux d'arêtes et centres de mailles) au-delà de
            # RAIDE_DEG, quart de pas au-delà de RAIDE_FORT_DEG (parois), pente lue au point ajouté
            k = 4 if pas / 4 >= RAIDE_PAS_MIN_M else 2
            ajout = []
            for i in range(k):
                for j in range(k):
                    if i == 0 and j == 0:
                        continue
                    seuil = RAIDE_DEG if (i * 2) % k == 0 and (j * 2) % k == 0 else RAIDE_FORT_DEG
                    xa, ya = X[sel] + i * pas / k, Y[sel] + j * pas / k
                    r = raide(xa, ya) >= seuil
                    ajout.append(np.column_stack([xa[r], ya[r], d[sel][r]]))
            ajout = np.vstack(ajout)
            print(f"  bande jusqu'à {dmax:.0f} m (pas {pas} m) : {len(ajout)} points ajoutés sur les versants raides, pour {int(sel.sum())}")
            pts.append(ajout)
        lo = dmax
    Q = np.vstack(pts)
    Q = Q[(Q[:, 0] >= x0) & (Q[:, 0] <= x1) & (Q[:, 1] >= y0) & (Q[:, 1] <= y1)]
    # hors du couloir de 08, et pas trop près de son bord
    dedans = shapely.contains_xy(poly, Q[:, 0], Q[:, 1])
    dbord = shapely.distance(ligne_bord, shapely.points(Q[:, 0], Q[:, 1]))
    pas_local = np.interp(Q[:, 2], [b[0] for b in bandes], [b[1] for b in bandes])
    garde = ~dedans & (dbord > 0.55 * np.minimum(pas_local, 8.0))
    return Q[garde], poly


def triangule(bord, Q, poly, tentatives=6):
    """Delaunay du bord + points ; triangles hors du couloir ; on vérifie que chaque arête du bord
    est une arête de la triangulation (sinon, on retire les points qui la gênent et on recommence)."""
    nb = len(bord)
    aretes_bord = {tuple(sorted((i, (i + 1) % nb))) for i in range(nb)}
    for k in range(tentatives):
        P = np.vstack([bord[:, :2], Q[:, :2]])
        T = Delaunay(P).simplices
        c = P[T].mean(1)
        T = T[~shapely.contains_xy(poly, c[:, 0], c[:, 1])]
        e = np.sort(np.vstack([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1)
        presentes = set(map(tuple, e[(e[:, 0] < nb) & (e[:, 1] < nb)]))
        manque = [a for a in aretes_bord if a not in presentes]
        if not manque:
            return P, T, 0, k
        # points de grille dans le disque de chaque arête manquante
        m = np.array(manque)
        mid = (bord[m[:, 0], :2] + bord[m[:, 1], :2]) / 2
        rad = np.linalg.norm(bord[m[:, 0], :2] - bord[m[:, 1], :2], axis=1) / 2 + 0.5
        tree = cKDTree(Q[:, :2])
        retire = set()
        for p, r in zip(mid, rad):
            retire.update(tree.query_ball_point(p, r * 1.6 + 1.0 * k))
        Q = np.delete(Q, sorted(retire), axis=0)
    return P, T, len(manque), tentatives


def altitudes(Pxy, dist, nb, bord, src, centre):
    """Altitude des sommets (le bord garde exactement celle de 08)."""
    x, y = Pxy[:, 0], Pxy[:, 1]
    z = np.empty(len(Pxy))
    proche = src["alti5"].dedans(x, y)
    z_far = src["alti25"](x, y)
    z_near = np.where(proche, src["alti5"](x, y), z_far)
    w = np.clip((dist - (R_PROCHE - 600)) / 500, 0, 1)
    z_rge = (1 - w) * z_near + w * z_far
    # MNT LiDAR à 2 m jusqu'à LIDAR_2M[1] de l'axe, fondu vers le RGE ALTI au-delà, au bord de son image et autour de
    # ses trous (60 m)
    l2 = src.get("lidar2")
    if l2 is not None:
        z_2 = l2(x, y)
        ok_2 = l2.dedans(x, y, marge=4) & (z_2 > -1000)
        w2 = np.where(ok_2, 1 - np.clip((dist - LIDAR_2M[0]) / (LIDAR_2M[1] - LIDAR_2M[0]), 0, 1), 0)
        w2 = w2 * np.clip((src["lidar2_bord"](x, y) - 10.0) / 60.0, 0, 1)
        z_rge = w2 * np.where(ok_2, z_2, 0.0) + (1 - w2) * z_rge
    # MNT LiDAR près du couloir
    lid = src["lidar"]
    ok_l = lid.dedans(x, y, marge=4)
    z_l = np.where(ok_l, lid(x, y), z_rge)
    ok_l &= z_l > -1000
    wl = np.where(ok_l, 1 - np.clip((dist - LIDAR[0]) / (LIDAR[1] - LIDAR[0]), 0, 1), 0)
    # le relevé laser ne couvre pas partout LIDAR[1] mètres autour de l'axe : fondu sur 60 m avant le bord de son image,
    # pour ne pas laisser une marche là où il s'arrête
    cb = (np.asarray(x) - lid.tr.c) / lid.tr.a
    rb = (lid.tr.f - np.asarray(y)) / -lid.tr.e
    au_bord = np.minimum(np.minimum(cb, rb), np.minimum(lid.a.shape[1] - cb, lid.a.shape[0] - rb)) * abs(lid.tr.a)
    wl = wl * np.clip((au_bord - 10.0) / 60.0, 0, 1)
    zg = wl * z_l + (1 - wl) * z_rge
    # mer : RGE ALTI sans valeur (-99999) ; l'interpolation près de la côte mélange cette valeur
    # aux altitudes : tout ce qui passe sous -20 m est la mer
    mer = (zg < -20) | (src["alti25"](x, y, order=0) < -1000) & (dist > R_PROCHE)
    zg = np.where(mer, 0.0, zg)
    # végétation
    mnh = np.where(src["mnh5"].dedans(x, y), src["mnh5"](x, y), src["mnh25"](x, y))
    mnh = np.clip(np.where(mnh < -1000, 0, mnh), 0, 35)
    t = np.clip((dist - CANOPEE[0]) / (CANOPEE[1] - CANOPEE[0]), 0, 1)
    z = zg + 0.9 * mnh * t * t * (3 - 2 * t)
    z = np.where(mer, 0.0, z)
    # courbure de la Terre, depuis le centre de l'ES
    dc = np.hypot(x - centre[0], y - centre[1])
    z -= (1 - K_REFRACTION) * dc ** 2 / (2 * RAYON_TERRE) * np.clip((dist - 600) / 400, 0, 1)
    z[:nb] = bord[:, 2]
    return z, mer


# --- textures et dalles -----------------------------------------------------------------------------------
def dalles_texture(P, T, dist_tri, axe_box, px_niveaux, version):
    """Découpe en dalles carrées : 1 km près de l'axe (< R_PROCHE), 5 km au-delà."""
    c = P[T, :2].mean(1)
    pres = dist_tri <= R_PROCHE
    cle = np.where(pres[:, None], np.floor(c / 1000) * 1000, np.floor(c / 5000) * 5000).astype(np.int64)
    taille = np.where(pres, 1000, 5000)
    groupes = {}
    ordre = np.lexsort((cle[:, 1], cle[:, 0], taille))
    cl = np.column_stack([taille, cle])[ordre]
    coupe = np.flatnonzero(np.any(np.diff(cl, axis=0) != 0, axis=1)) + 1
    for g in np.split(ordre, coupe):
        t, kx, ky = int(taille[g[0]]), int(cle[g[0], 0]), int(cle[g[0], 1])
        groupes[(t, kx, ky)] = g
    out = []
    for (t, kx, ky), g in sorted(groupes.items()):
        used = np.unique(T[g])
        e0 = np.floor(P[used, :2].min(0)) - 1
        e1 = np.ceil(P[used, :2].max(0)) + 1
        cote = float(max(e1 - e0))
        e1 = e0 + cote
        dmin = float(dist_tri[g].min())
        px = px_niveaux[0] if dmin < 1500 else px_niveaux[1] if dmin < 10000 else px_niveaux[2]
        # pas plus fin que 1 m (près), 4 m (moyen), 10 m (loin) : petites dalles de bord -> petites images
        cible = 1.0 if dmin < 1500 else 4.0 if dmin < 10000 else 10.0
        # Vu en jeu le 13/11/2026 : les versants juste au-delà du bord de route sont flous. Les dalles qui touchent le
        # couloir (moins de TRES_PRES_M de l'axe) portent une image deux fois plus fine : 50 cm par point.
        if dmin < TRES_PRES_M and px_niveaux[0] >= 1024:
            px, cible = 2 * px_niveaux[0], 0.5
        px = int(min(px, max(64, 2 ** math.ceil(math.log2(max(cote / cible, 1))))))
        out.append({"nom": f"lointain_{t // 1000}km_{kx}_{ky}", "tri": g, "emprise": (e0[0], e0[1], e1[0], e1[1]),
                    "px": px, "m_par_px": round(cote / px, 2), "distance_min_axe_m": round(dmin)})
    return out


def construit(version, ref, axe, src, centre, rapport):
    bandes, px_niv = VERSIONS[version]
    dossier = MOD if version == "complet" else MOD / "apercu"
    bord, info_bord = bord_exterieur(dossier / "terrain.glb", ref)
    def pente(r, x, y, h):
        ok = r.dedans(x - h, y - h) & r.dedans(x + h, y + h)
        p = np.zeros(len(x))
        if ok.any():
            gx = (r(x[ok] + h, y[ok]) - r(x[ok] - h, y[ok])) / (2 * h)
            gy = (r(x[ok], y[ok] + h) - r(x[ok], y[ok] - h)) / (2 * h)
            p[ok] = np.degrees(np.arctan(np.hypot(gx, gy)))
            p[ok] = np.where(np.abs(r(x[ok], y[ok])) < 5000, p[ok], 0.0)      # hors données (mer, bord) : pas de falaise
        return p

    def raide(x, y):
        """Pente en degrés : MNT LiDAR à 2 m là où il est sûr (loin de son bord et de ses trous), RGE ALTI à 5 m ailleurs."""
        p = pente(src["alti5"], x, y, 5.0)
        if "lidar2" in src:
            sur = src["lidar2_bord"](x, y) > 20.0
            if sur.any():
                p[sur] = pente(src["lidar2"], x[sur], y[sur], RAIDE_BASE_M)
        return p

    Q, poly = points_anneau(axe, bord, bandes, raide if version == "complet" else None)
    P2, T, manque, essais = triangule(bord, Q, poly)
    nb = len(bord)
    line = LineString(axe)
    dist = np.concatenate([np.full(nb, 130.0), shapely.distance(line, shapely.points(P2[nb:, 0], P2[nb:, 1]))])
    z, mer = altitudes(P2, dist, nb, bord, src, centre)
    P = np.column_stack([P2, z])
    # orientation vers le haut
    v1, v2 = P[T[:, 1], :2] - P[T[:, 0], :2], P[T[:, 2], :2] - P[T[:, 0], :2]
    neg = v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0] < 0
    T[neg] = T[neg][:, [0, 2, 1]]
    pos = m08.to_gltf(P, ref)
    pos[:nb] = info_bord["gltf"]                 # bord : positions de 08 au bit près
    nrm = m08.normales(pos, T)
    dist_tri = dist[T].mean(1)
    meshes = []
    tex_px = []
    for d in dalles_texture(P, T, dist_tri, None, px_niv, version):
        used, inv = np.unique(T[d["tri"]], return_inverse=True)
        e = d["emprise"]
        req = d["px"]
        im = ortho(e, req, BRUT / "ortho" / f"{version}_{d['nom']}_{int(e[0])}_{int(e[1])}_{req}.jpg")
        if im.size[0] != d["px"]:
            im = im.resize((d["px"], d["px"]), Image.LANCZOS)
        # la BD ORTHO est sombre et bleutée sur les bois : éclaircie (gamma) et réchauffée, pour que
        # l'anneau ne fasse pas une bande sombre derrière les arbres 3D du couloir
        a = np.asarray(im).astype(np.float32) / 255.0
        a = np.clip(a ** 0.85 * np.array([1.05, 1.0, 0.92]), 0, 1)
        im = Image.fromarray((a * 255 + 0.5).astype(np.uint8))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85 if version == "complet" else 75, optimize=True)
        uv = np.column_stack([(P[used, 0] - e[0]) / (e[2] - e[0]), (e[3] - P[used, 1]) / (e[3] - e[1])]).astype(np.float32)
        meshes.append({"name": d["nom"], "pos": pos[used], "nrm": nrm[used], "uv": uv,
                       "idx": inv.reshape(-1, 3), "couleur": buf.getvalue(), "rough": 1.0})
        tex_px.append((d["px"], d["m_par_px"], d["distance_min_axe_m"]))
    m14.ecrire_glb(dossier / "lointain.glb", meshes, generator="acr-grand-caunet 13_paysage_lointain.py")
    rapport[version] = {"bandes_m": bandes, "sommets": int(len(P)), "triangles": int(len(T)), "dalles": len(meshes),
                        "bord": {k: v for k, v in info_bord.items() if k != "gltf"},
                        "aretes_de_bord_absentes_de_la_triangulation": manque, "reprises_triangulation": essais,
                        "sommets_en_mer": int(mer.sum()),
                        "textures": {"px_min": min(t[0] for t in tex_px), "px_max": max(t[0] for t in tex_px),
                                     "m_par_px_jusqu_a_1500m": min(t[1] for t in tex_px),
                                     "m_par_px_max": max(t[1] for t in tex_px)}}
    rapport[version]["relecture"] = controle(dossier, ref, bord, info_bord)
    print(version, json.dumps(rapport[version], ensure_ascii=False))


# --- contrôles ------------------------------------------------------------------------------------------
def controle(dossier, ref, bord, info_bord):
    ms = m14.lire_glb(dossier / "lointain.glb")
    pos = np.vstack([m["pos"] for m in ms])
    nrm = np.vstack([m["nrm"] for m in ms])
    uv = np.vstack([m["uv"] for m in ms])
    r = {"taille_mo": round((dossier / "lointain.glb").stat().st_size / 1e6, 2), "maillages": len(ms),
         "nan": bool(np.isnan(pos).any() or np.isnan(nrm).any() or np.isnan(uv).any()),
         "normales_vers_le_haut_pct": round(float((nrm[:, 1] > 0).mean() * 100), 2),
         "uv_hors_0_1": int(((uv < -1e-4) | (uv > 1 + 1e-4)).any(1).sum()),
         "bornes_min": np.round(pos.min(0), 1).tolist(), "bornes_max": np.round(pos.max(0), 1).tolist()}
    # raccord : chaque sommet du bord extérieur de 08 existe dans l'anneau à la même position
    t = cKDTree(pos.astype(np.float64))
    d, _ = t.query(info_bord["gltf"].astype(np.float64))
    r["raccord_08"] = {"sommets_du_bord": int(len(d)), "retrouves_a_1mm_pct": round(float((d < 1e-3).mean() * 100), 3),
                       "ecart_max_m": round(float(d.max()), 4)}
    # recouvrement : aucun sommet de l'anneau à l'intérieur du couloir (hors bord)
    poly = Polygon(info_bord["gltf"][:, [0, 2]])
    dedans = shapely.contains_xy(poly.buffer(-0.05), pos[:, 0], pos[:, 2])
    r["sommets_dans_le_couloir"] = int(dedans.sum())
    # marche : pente maximale des triangles qui touchent le bord (doit rester celle du terrain)
    return r


# --- horizon ----------------------------------------------------------------------------------------------
def horizon(src, ch):
    """Distance de l'horizon et visibilité de la mer depuis la route (sol nu)."""
    a = src["alti50"]
    sea = (a.a < -1000).astype(np.float32)
    z0 = np.where(a.a < -1000, 0, a.a)
    za = Raster(z0, a.tr)
    sr = Raster(sea, a.tr)
    az = np.radians(np.arange(0, 360, 2.0))
    d = np.concatenate([np.arange(50, 2000, 12.5), np.arange(2000, 38000, 50)])
    D, mer_vue = [], []
    for pk in np.arange(0, ch["pk"].max(), 100):
        i = int(np.argmin(np.abs(ch["pk"] - pk)))
        x, y, z = ch["A"][i]
        z += 1.1
        X = x + np.sin(az)[:, None] * d
        Y = y + np.cos(az)[:, None] * d
        h = za(X.ravel(), Y.ravel()).reshape(X.shape) - (1 - K_REFRACTION) * d ** 2 / (2 * RAYON_TERRE)
        ang = np.arctan2(h - z, d)
        cm = np.maximum.accumulate(ang, axis=1)
        prev = np.concatenate([np.full((len(az), 1), -9.0), cm[:, :-1]], axis=1)
        s = sr(X.ravel(), Y.ravel(), order=0).reshape(X.shape) > 0.5
        mer_vue.append(int((s & (ang >= prev)).any(1).sum()))
        D.append(d[np.argmax(ang, axis=1)])
    D = np.concatenate(D)
    return {"points_de_route": len(mer_vue), "directions": len(az),
            "part_horizon_au_dela_m": {str(v): round(float((D > v).mean()), 4) for v in (3000, 5000, 10000, 20000, 30000)},
            "horizon_max_m": float(D.max()), "directions_ou_la_mer_est_visible": int(sum(mer_vue))}


def main():
    t0 = time.time()
    BRUT.mkdir(parents=True, exist_ok=True)
    ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    ch = m08.chaussee()
    axe = ch["A"][:, :2]
    centre = (axe.min(0) + axe.max(0)) / 2
    # bruts : RGE ALTI et MNH à 5 m près, 25 m loin ; RGE ALTI 50 m pour l'horizon
    bp = tuple(np.r_[np.floor((axe.min(0) - R_PROCHE - 100) / 100) * 100, np.ceil((axe.max(0) + R_PROCHE + 100) / 100) * 100])
    bl = tuple(np.r_[np.floor((axe.min(0) - R_MAX - 500) / 500) * 500, np.ceil((axe.max(0) + R_MAX + 500) / 500) * 500])
    bh = (centre[0] - 40000, centre[1] - 40000, centre[0] + 40000, centre[1] + 40000)
    bh = tuple(np.round(np.array(bh) / 100) * 100)
    src = {"alti5": Raster(*mosaique(LAYER_ALTI, BRUT / "rgealti_5m.tif", bp, 5.0)),
           "alti25": Raster(*mosaique(LAYER_ALTI, BRUT / "rgealti_25m.tif", bl, 25.0)),
           "mnh5": Raster(*mosaique(LAYER_MNH, BRUT / "mnh_5m.tif", bp, 5.0)),
           "mnh25": Raster(*mosaique(LAYER_MNH, BRUT / "mnh_25m.tif", bl, 25.0)),
           "alti50": Raster(*mosaique(LAYER_ALTI, BRUT / "rgealti_50m_horizon.tif", bh, 50.0, dalle_px=800))}
    # MNT (et MNS) LiDAR HD à 2 m jusqu'à LIDAR_LOIN_M de l'axe ; distance de chaque point au bord des données (m)
    b2 = tuple(np.r_[np.floor((axe.min(0) - LIDAR_LOIN_M - 100) / 100) * 100, np.ceil((axe.max(0) + LIDAR_LOIN_M + 100) / 100) * 100])
    src["lidar2"] = Raster(*mosaique(LAYER_MNT, BRUT / "mnt_lidarhd_2m.tif", b2, 2.0))
    mosaique(LAYER_MNS, BRUT / "mns_lidarhd_2m.tif", b2, 2.0)
    from scipy.ndimage import distance_transform_edt
    ok2 = np.pad(src["lidar2"].ok & (src["lidar2"].a < 5000), 1)
    src["lidar2_bord"] = Raster((distance_transform_edt(ok2)[1:-1, 1:-1] * 2.0).astype(np.float32), src["lidar2"].tr)
    print(f"MNT LiDAR à 2 m : {src['lidar2'].a.shape[1]} x {src['lidar2'].a.shape[0]} points, "
          f"{100 * (1 - ok2[1:-1, 1:-1].mean()):.2f} % sans valeur")
    with rasterio.open(RAW / "mnt_lidarhd_50cm.tif") as s:
        a = s.read(1, out_shape=(s.height // 4, s.width // 4), resampling=Resampling.average, masked=True)
        a = a.filled(-9999.0)
        src["lidar"] = Raster(a.astype(np.float32), s.transform * s.transform.scale(4, 4))
    rapport = {"emprise_l93": {"pres_5m": bp, "loin_25m": bl}, "rayon_max_axe_m": R_MAX,
               "horizon": horizon(src, ch)}
    print("horizon :", json.dumps(rapport["horizon"], ensure_ascii=False))
    # écart LiDAR / RGE ALTI dans la zone de raccord (contrôle)
    versions = [v for v in VERSIONS if len(sys.argv) < 2 or v in sys.argv[1:]]
    for v in versions:
        construit(v, ref, axe, src, centre, rapport)
    rapport["duree_s"] = round(time.time() - t0)
    chemin = MOD / "apercu" / "lointain_controle.json"
    ancien = json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else {}
    ancien.update(rapport)                       # une version refaite seule ne retire pas l'autre
    chemin.write_text(json.dumps(ancien, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(f"durée : {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
