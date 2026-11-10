"""Étape 7 (phase 3) - Axe précis et bords de la chaussée, tous les mètres.

L'axe BD TOPO (précision annoncée 2,5 m) sert seulement de guide. Tous les mètres,
un profil en travers de ±15 m (pas 0,25 m), perpendiculaire à l'axe courant, est lu
dans deux sources indépendantes :
  - le MNT LiDAR HD (sol nu, 0,5 m) : la chaussée est une plate-forme lisse, de pente
    transversale faible ; on la fait croître depuis le centre jusqu'aux ruptures
    (fossé, talus, bourrelet) ;
  - l'ortho infrarouge (IRC) et RVB 20 cm : l'asphalte n'a pas de chlorophylle (NDVI
    bas) et garde la luminosité de la route ; ce masque n'est lu que là où rien ne
    couvre la route (hauteur MNS - MNT < 1 m) et hors ombre portée.
Fusion côté par côté : le bord image fait foi quand il est mesuré (il coïncide avec
le bord visible de l'asphalte, alors que la plate-forme LiDAR inclut parfois un
accotement plat), le LiDAR seul ailleurs (sous les arbres, à l'ombre). Chaque bord
est ensuite filtré le long du parcours (médianes glissantes, rejet des sauts et des
surlargeurs locales, largeur bornée), interpolé sur les ponts sans image, aux
débouchés et là où aucune source ne tranche, puis lissé. L'axe est le milieu des
deux bords ; deux itérations recentrent les profils avant la mesure finale.
Les altitudes sont lues dans le MNT (interpolées entre culées sur les ponts) ; le
dévers est la pente de la droite ajustée sur le profil en travers entre les bords.
Étendue : de l'origine de l'axe BD TOPO (contrôle horaire) au point stop + 60 m ;
colonne `zone` = approche / es / sortie, PK 0 = départ. Les statistiques de qualité
portent sur la zone es. Les stations restent calées sur la grille métrique de l'axe
BD TOPO : le résultat en un point ne dépend pas de l'étendue traitée.

Entrées : data/raw (MNT, MNS, ortho RVB ; ortho IRC téléchargée si absente),
          data/processed/axe_bdtopo_l93.csv, ouvrages_es.csv, carrefours_es.csv, calage_es.json
Sorties : data/processed/chaussee_precise.csv, .geojson, _qualite.json ; figures/phase3/*.png
"""
import csv
import io
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from PIL import Image
from rasterio.windows import Window, from_bounds
from scipy.ndimage import (gaussian_filter1d, grey_closing, map_coordinates, median_filter, percentile_filter,
                           uniform_filter1d)
from scipy.signal import savgol_filter
from shapely.geometry import LineString, Point, box

from acr_geo import FIG, OUT, RAW, cumdist, resample, wgs, wms_tile, write_geojson

LAYER_IRC = "ORTHOIMAGERY.ORTHOPHOTOS.IRC"   # ortho infrarouge couleur 20 cm (PIR, R, V)
TILE = 500
PK_MIN, PK_MAX = -200.0, 7460.0   # PK BD TOPO traités : du début de l'axe (CH) au point stop + marge
def _pk_stop() -> float:
    """PK du point stop officiel sur l'axe BD TOPO (points_officiels_recales.csv)."""
    with open(OUT / "points_officiels_recales.csv", encoding="utf-8") as f:
        return next(float(r["pk_mesure_m"]) for r in csv.DictReader(f) if r["id"] == "STOP")


PK_STOP_BDTOPO = _pk_stop()
SORTIE_APRES_STOP = 60.0          # m conservés après le point stop

DT, HALF = 0.25, 15.0             # profils en travers : pas et demi-largeur (m)
T = np.arange(-HALF, HALF + DT / 2, DT)   # t > 0 : à droite dans le sens de marche
C = len(T) // 2
W_MIN, W_MAX = 4.0, 9.5           # largeur admissible de la chaussée (m)
CANOPY = 1.0                      # m : au-dessus, l'image ne voit pas le sol
BRIDGE_MARGIN = 8                 # m ajoutés de part et d'autre d'un ouvrage
WIDEN = 1.5                       # m : surlargeur locale d'un bord traitée comme débouché / refuge
GAP_MAX = 3                       # m : trou de mesure plus court = non compté comme interpolé
JUNCTION_HALF = 14                # m : demi-zone neutralisée au débouché d'une voie (côté concerné)
FIG3 = FIG / "phase3"
FIG3.mkdir(parents=True, exist_ok=True)

INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
BLUE, ORANGE, GREEN, RED = "#2a78d6", "#eb6834", "#2f9e5b", "#d03b3b"
SRC_COLORS = {"lidar+ortho": GREEN, "lidar": BLUE, "ortho": ORANGE, "interpole": RED}
plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "figure.facecolor": SURFACE,
                     "axes.facecolor": SURFACE, "axes.spines.top": False, "axes.spines.right": False})


# --- données -------------------------------------------------------------------
def axe_bdtopo():
    with open(OUT / "axe_bdtopo_l93.csv") as f:
        rows = list(csv.DictReader(f))
    return np.array([float(r["pk_m"]) for r in rows]), np.array([[float(r["x_l93"]), float(r["y_l93"])] for r in rows])


def collecte_irc(path=RAW / "ortho_irc_20cm.tif", buf=45.0):
    """Ortho IRC 20 cm sur les dalles de 500 m qui touchent l'axe traité (même grille que
    l'ortho RVB). Le fichier est refait si une dalle nécessaire y manque."""
    pk, xy = axe_bdtopo()
    keep = (pk >= PK_MIN - 50) & (pk <= PK_MAX + 50)
    zone = LineString(xy[keep]).buffer(buf)
    with rasterio.open(RAW / "ortho_20cm.tif") as ref:
        prof = ref.profile.copy()
        x0, y1 = ref.bounds.left, ref.bounds.top
    gx0, gy0, gx1, gy1 = (int(v // TILE * TILE) for v in zone.bounds)
    todo = [(x, y) for x in range(gx0, gx1 + TILE, TILE) for y in range(gy0, gy1 + TILE, TILE)
            if zone.intersects(box(x, y, x + TILE, y + TILE))]
    if path.exists():
        with rasterio.open(path) as src:              # une dalle écrite n'est jamais toute noire
            if all(src.read(1, window=from_bounds(x + 200, y + 200, x + 300, y + 300, src.transform)).any()
                   for x, y in todo):
                return path
    prof.update(compress="jpeg", photometric="ycbcr", jpeg_quality=88, tiled=True, blockxsize=512, blockysize=512)
    tmp = path.with_suffix(".part.tif")
    n = round(TILE / 0.2)
    with rasterio.open(tmp, "w", **prof) as dst:
        for k, (tx, ty) in enumerate(todo, 1):
            raw = wms_tile(LAYER_IRC, tx, ty, tx + TILE, ty + TILE, 0.2, fmt="image/jpeg")
            im = np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"))
            win = Window(round((tx - x0) / 0.2), round((y1 - ty - TILE) / 0.2), n, n)
            dst.write(np.moveaxis(im, 2, 0), window=win)
            print(f"\rortho IRC : dalle {k}/{len(todo)}", end="", flush=True)
    print()
    tmp.rename(path)
    return path


class Rasters:
    """MNT et MNS en mémoire ; orthos lues par fenêtres."""

    def __init__(self):
        with rasterio.open(RAW / "mnt_lidarhd_50cm.tif") as s:
            self.mnt, self.inv = s.read(1), ~s.transform
        with rasterio.open(RAW / "mns_lidarhd_50cm.tif") as s:
            self.mns = s.read(1)
        self.rgb = rasterio.open(RAW / "ortho_20cm.tif")
        self.irc = rasterio.open(collecte_irc())

    def z(self, x, y, grid="mnt"):
        c, r = self.inv * (np.asarray(x), np.asarray(y))
        return map_coordinates(getattr(self, grid), [np.asarray(r) - 0.5, np.asarray(c) - 0.5], order=1, mode="nearest")

    def image(self, src, X, Y, chunk=250):
        inv = ~src.transform
        c, r = inv * (X, Y)
        out = np.zeros(X.shape + (3,), np.float32)
        for a in range(0, len(X), chunk):
            cc, rr = c[a:a + chunk], r[a:a + chunk]
            c0, r0 = int(cc.min()) - 2, int(rr.min()) - 2
            win = Window(c0, r0, int(cc.max()) + 3 - c0, int(rr.max()) + 3 - r0)
            im = src.read(window=win, boundless=True, fill_value=0).astype(np.float32)
            for b in range(3):
                out[a:a + chunk, :, b] = map_coordinates(im[b], [rr - r0 - 0.5, cc - c0 - 0.5], order=1)
        return out


def normales(xy):
    """Normale à droite (sens de marche) d'une polyligne échantillonnée à 1 m, lissée sur 21 m."""
    xs, ys = (savgol_filter(xy[:, k], 21, 2) for k in (0, 1))
    dx, dy = np.gradient(xs), np.gradient(ys)
    n = np.hypot(dx, dy)
    return np.column_stack([dy / n, -dx / n])


def profils(R, xy, nr):
    X = xy[:, 0, None] + T[None] * nr[:, 0, None]
    Y = xy[:, 1, None] + T[None] * nr[:, 1, None]
    Z, S = R.z(X, Y), R.z(X, Y, "mns")
    irc, rgb = R.image(R.irc, X, Y), R.image(R.rgb, X, Y)
    ndvi = (irc[..., 0] - irc[..., 1]) / (irc[..., 0] + irc[..., 1] + 1.0)
    return {"Z": Z, "can": S - Z, "ndvi": ndvi, "bri": rgb.mean(axis=2)}


# --- estimateur LiDAR : plate-forme lisse autour du centre ---------------------
def bords_lidar(Z, gtol=0.09, gabs=0.14, rtol=0.12, seed_max=6.0):
    """Renvoie (N,2) décalages des bords (NaN si pas de rupture nette) et la graine."""
    N = len(Z)
    out, seed = np.full((N, 2), np.nan), np.full(N, np.nan)
    G = uniform_filter1d(np.gradient(uniform_filter1d(Z, 3, axis=1), DT, axis=1), 3, axis=1)
    hw = 6                          # demi-fenêtre de la graine : 1,5 m
    order = sorted(range(C - int(seed_max / DT), C + int(seed_max / DT) + 1), key=lambda k: abs(k - C))
    for i in range(N):
        z, g = Z[i], G[i]
        if (z < -1000).any():
            continue
        best = next((c for c in order if np.abs(g[c - hw:c + hw + 1]).max() < 0.10
                     and np.ptp(g[c - hw:c + hw + 1]) < 0.06), None)
        if best is None:
            continue
        seed[i] = T[best]
        gref = np.median(g[best - hw:best + hw + 1])
        lo, hi = best - hw, best + hw

        def ok(k):
            if k < 0 or k >= len(z) or abs(g[k] - gref) > gtol or abs(g[k]) > gabs:
                return False
            a, b = np.polyfit(T[lo:hi + 1], z[lo:hi + 1], 1)
            return abs(z[k] - (a * T[k] + b)) < rtol

        stop = [False, False]
        while not all(stop):
            if not stop[0]:
                if ok(lo - 1):
                    lo -= 1
                elif ok(lo - 2):           # tolère un point isolé
                    lo -= 2
                else:
                    stop[0] = True
            if not stop[1]:
                if ok(hi + 1):
                    hi += 1
                elif ok(hi + 2):
                    hi += 2
                else:
                    stop[1] = True
        out[i, 0] = T[lo] - DT / 2 if lo > 1 else np.nan       # pas de rupture dans le profil
        out[i, 1] = T[hi] + DT / 2 if hi < len(z) - 2 else np.nan
    return out, seed


# --- estimateur image : asphalte = NDVI bas, ni éblouissant ni sous couvert ------
def bords_ortho(P, centre, bridge):
    """Bords de l'asphalte visible sur l'image, profil par profil (NaN si indécidable).

    Un point est « asphalte » s'il est sans chlorophylle (NDVI sous le mi-chemin entre la
    route et la végétation du secteur) et de luminosité proche de celle de la route
    (0,72 à 1,35 fois la référence) : la végétation, les gravillons clairs et les
    accotements gris plus sombres en sont exclus. Un point sous les arbres (MNS - MNT
    > 1 m) ou à l'ombre (sombre mais sans chlorophylle) est indécidable : si on en
    rencontre avant le bord, le bord n'est pas mesuré de ce côté.
    """
    ndvi, bri, can = P["ndvi"], P["bri"], P["can"]
    N = len(ndvi)
    ci = np.clip(np.round((np.nan_to_num(centre) + HALF) / DT).astype(int), 6, len(T) - 7)
    near = np.abs(np.arange(len(T))[None] - ci[:, None]) <= 6
    clear = (can < CANOPY) | bridge[:, None]   # sur un pont, le MNS décrit le tablier, pas un arbre
    # références locales (médianes glissantes sur ±30 m) : route au centre, végétation autour
    nc = near & clear
    road_nd = np.array([np.median(ndvi[i][nc[i]]) if nc[i].sum() > 4 else np.nan for i in range(N)])
    road_br = np.array([np.median(bri[i][nc[i]]) if nc[i].sum() > 4 else np.nan for i in range(N)])
    veg_nd = np.array([np.median(ndvi[i][can[i] > 2.0]) if (can[i] > 2.0).sum() > 8 else np.nan for i in range(N)])

    def glisse(v, w=61):
        ok = np.isfinite(v)
        v = np.interp(np.arange(N), np.flatnonzero(ok), v[ok])
        return median_filter(v, w, mode="nearest")
    road_nd, road_br, veg_nd = glisse(road_nd), glisse(road_br), glisse(veg_nd)
    thr = (road_nd + 0.5 * np.maximum(veg_nd - road_nd, 0.12))[:, None]  # mi-chemin route / végétation
    rb = road_br[:, None]
    mineral = ndvi < thr
    road = mineral & (bri >= 0.72 * rb) & (bri <= np.maximum(1.35 * rb, rb + 35))
    road = uniform_filter1d(road.astype(float), 3, axis=1) > 0.5           # vote sur 0,75 m
    unknown = ~clear | (mineral & (bri < 0.6 * rb))                           # couvert ou ombre portée
    out = np.full((N, 2), np.nan)
    contrast = (veg_nd - road_nd) > 0.12
    for i in range(N):
        if not contrast[i] or not road[i, ci[i]]:
            continue
        for side, step in ((0, -1), (1, 1)):
            k = ci[i]
            while 0 < k + 3 * step < len(T) - 1:
                nxt = k + step
                if road[i, nxt]:
                    k = nxt
                    continue
                if unknown[i, nxt]:
                    k = None                      # couvert ou ombre avant le bord : indécidable
                    break
                if not road[i, nxt:nxt + 3 * step:step].any() if step > 0 else not road[i, nxt - 2:nxt + 1].any():
                    break
                k = nxt
            if k is not None and 0 < k + 3 * step < len(T) - 1:
                out[i, side] = T[k] + step * DT / 2
    return out


# --- fusion et filtrage le long du parcours ---------------------------------------
def zones_neutres(pk_ref):
    """Masques (N,2) : côtés à ignorer aux ponts (deux côtés) et aux débouchés (un côté)."""
    N = len(pk_ref)
    bridge = np.zeros(N, bool)
    with open(OUT / "ouvrages_es.csv") as f:
        for r in csv.DictReader(f):
            bridge |= (pk_ref >= float(r["pk_debut_m"]) - BRIDGE_MARGIN) & (pk_ref <= float(r["pk_fin_m"]) + BRIDGE_MARGIN)
    junc = np.zeros((N, 2), bool)
    with open(OUT / "carrefours_es.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["nature"] == "Sentier":
                continue
            half = 30 if r["numero"] == "D1" else JUNCTION_HALF
            junc[np.abs(pk_ref - float(r["pk_m"])) <= half, 0 if r["cote"] == "gauche" else 1] = True
    return bridge, junc


def tendance(v, valid, w):
    """Médiane glissante des seules valeurs valides (trous comblés linéairement)."""
    idx = np.flatnonzero(valid)
    return median_filter(np.interp(np.arange(len(v)), idx, v[idx]), w, mode="nearest")


def fusion(lid, ort, bridge, junc, tol=0.8, agree=1.0):
    """Fusion côté par côté des deux estimateurs, filtrée le long du parcours.

    Contrôle sur les profils où le bord de l'asphalte est net sur l'ortho (route claire,
    ciel dégagé) : la rupture LiDAR s'en écarte souvent de 1 à 2 m (accotement plat
    compris dans la plate-forme, ou arrondi pris trop tôt), alors que le bord image y
    est précis. Règle : le bord image, quand il est mesuré, fait foi ; s'il concorde
    avec le LiDAR (< `agree`), on garde 0,7 image + 0,3 LiDAR (source « les deux ») ;
    ailleurs (arbres, ombre, contraste faible) le LiDAR seul. Chaque source est d'abord
    filtrée contre sa propre tendance ; une tendance commune (médiane glissante, hors
    débouchés) rejette ensuite les sauts restants et les surlargeurs locales.
    Codes : 1 LiDAR, 2 image, 3 les deux concordent, 0 interpolé.
    """
    N = len(lid)
    lid = lid.copy()
    lid[bridge] = np.nan                        # sous un tablier, le MNT décrit le vallon
    lid[(np.abs(lid) < 1.2) | (np.abs(lid) > 8.0)] = np.nan
    ort = np.where((np.abs(ort) < 1.2) | (np.abs(ort) > 8.0), np.nan, ort)

    def filtre(v, s):                           # chaque source est d'abord filtrée contre elle-même
        ok = np.isfinite(v)
        for w, t in ((41, 1.5), (31, tol)):
            if ok.sum() < 20:
                return np.full(N, np.nan)
            ref = tendance(v, ok & ~junc[:, s], w)
            ok = np.isfinite(v) & (np.abs(v - ref) < t)
        return np.where(ok, v, np.nan)

    val, code = np.full((N, 2), np.nan), np.zeros((N, 2), int)
    for s, sign in ((0, -1), (1, 1)):
        a, b = filtre(lid[:, s], s), filtre(ort[:, s], s)
        fa, fb = np.isfinite(a), np.isfinite(b)
        d = sign * (a - b)                       # > 0 : la plate-forme LiDAR est plus large
        for m, v, c in ((fa, a, 1), (fb, b, 2), (fa & fb & (np.abs(d) <= agree), 0.7 * b + 0.3 * a, 3)):
            val[m, s], code[m, s] = v[m], c
        ok = np.isfinite(val[:, s])              # garde-fou : sauts restants
        ref = tendance(val[:, s], ok & ~junc[:, s], 31)
        ok &= np.abs(val[:, s] - ref) < 1.2
        # surlargeurs locales (débouché, refuge, accotement plat) : le bord s'écarte de plus de
        # WIDEN m de sa ligne de base (30e centile de |décalage| sur 81 m)
        idx = np.flatnonzero(ok)
        if len(idx) > 20:
            av = np.abs(np.interp(np.arange(N), idx, val[idx, s]))
            base = percentile_filter(av, 30, size=81, mode="nearest")
            ok &= np.abs(val[:, s]) < base + WIDEN
        code[~ok, s] = 0
    # largeur : bornes absolues et écart à la largeur habituelle du secteur (médiane sur 400 m
    # des profils dont un bord au moins est vu par l'image). Le côté écarté est celui que
    # l'image ne confirme pas, sinon le plus éloigné de sa tendance.
    for _ in range(2):
        e = np.where(code > 0, val, np.nan)
        w = e[:, 1] - e[:, 0]
        seen = np.isfinite(w) & (code >= 2).any(axis=1)
        wref = tendance(w, seen, 401) if seen.sum() > 100 else np.full(N, np.nanmedian(w))
        bad = np.isfinite(w) & ((w < W_MIN) | (w > W_MAX) | (np.abs(w - wref) > 2.0))
        dev = np.stack([np.abs(e[:, s] - tendance(e[:, s], np.isfinite(e[:, s]), 61)) for s in (0, 1)], axis=1)
        dev = dev + 10 * (code >= 2)            # un bord vu par l'image est gardé en priorité
        drop = np.where(dev[:, 0] >= dev[:, 1], 0, 1)
        for s in (0, 1):
            code[bad & (drop == s), s] = 0
    edge = np.empty((N, 2))
    for s in (0, 1):
        idx = np.flatnonzero(code[:, s] > 0)
        for i0, i1 in runs(code[:, s] == 0):     # trou de 3 m au plus : absorbé par le lissage
            if i1 - i0 < GAP_MAX and i0 > 0 and i1 < N - 1:
                code[i0:i1 + 1, s] = np.where(np.arange(i0, i1 + 1) - i0 < (i1 - i0 + 1) / 2,
                                              code[i0 - 1, s], code[i1 + 1, s])
        v = median_filter(np.interp(np.arange(N), idx, val[idx, s]), 5, mode="nearest")
        edge[:, s] = gaussian_filter1d(v, 2.0, mode="nearest")
    # le milieu est lissé plus fort (σ 4 m) que la largeur : l'axe d'une route n'ondule pas
    w = np.clip(edge[:, 1] - edge[:, 0], W_MIN, W_MAX)  # garde-fou final après interpolation
    mid = gaussian_filter1d(edge.mean(axis=1), 4.0, mode="nearest")
    return np.column_stack([mid - w / 2, mid + w / 2]), code


def passe(R, xy, pk_ref):
    nr = normales(xy)
    P = profils(R, xy, nr)
    lid, seed = bords_lidar(P["Z"])
    centre = np.where(np.isfinite(lid).all(axis=1), lid.mean(axis=1), np.nan)
    centre = np.where(np.isfinite(centre), centre, seed)
    ok = np.isfinite(centre)
    centre = median_filter(np.interp(np.arange(len(xy)), np.flatnonzero(ok), centre[ok]), 15, mode="nearest")
    bridge, junc = zones_neutres(pk_ref)
    ort = bords_ortho(P, centre, bridge)
    edge, code = fusion(lid, ort, bridge, junc)
    return {"nr": nr, "P": P, "lid": lid, "ort": ort, "edge": edge, "code": code, "bridge": bridge}


def recentre(xy, pk_ref, res):
    """Nouvel axe = milieu des bords, lissé. Les stations restent calées sur la grille
    métrique des PK BD TOPO (pk_ref entiers + constante) : le résultat en un point ne dépend
    pas de l'étendue traitée."""
    mid = res["edge"].mean(axis=1)
    m = xy + mid[:, None] * res["nr"]
    m = np.column_stack([savgol_filter(m[:, k], 11, 2) for k in (0, 1)])
    s = cumdist(m)
    g = pk_ref[0] + np.arange(0, np.floor(pk_ref[-1] - pk_ref[0]) + 1)
    t = np.interp(g, pk_ref, s)
    return np.column_stack([np.interp(t, s, m[:, k]) for k in (0, 1)]), g


def source_profil(code):
    """Code par côté -> source du point (la plus faible des deux)."""
    out = []
    for a, b in code:
        if a == 0 or b == 0:
            out.append("interpole")
        elif a == 3 and b == 3:
            out.append("lidar+ortho")
        elif 2 not in (a, b):
            out.append("lidar")
        elif 1 not in (a, b):
            out.append("ortho")
        else:
            out.append("lidar+ortho")
    return np.array(out)


def runs(mask):
    """Plages contiguës (i0, i1 inclus) d'un masque booléen."""
    d = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1))


# --- figures ---------------------------------------------------------------------
def planche(R, old_xy, pk, axe, gl, dr, src, picks, h, name, dpi, grille=(2, 4), titre=None):
    """Extraits d'ortho RVB (2h x 2h m) centrés sur le nouvel axe, avec les tracés superposés."""
    nl, nc = grille
    fig, axs = plt.subplots(nl, nc, figsize=(4 * nc, 4.8 * nl))
    px = round(2 * h / 0.2)
    halo = [pe.withStroke(linewidth=2.6, foreground=INK)]
    for ax, (k, label) in zip(axs.flat, picks):
        i = int(np.argmin(np.abs(pk - k)))
        cx, cy = axe[i]
        b = (round(cx - h), round(cy - h), round(cx + h), round(cy + h))
        im = R.rgb.read(window=from_bounds(*b, R.rgb.transform), out_shape=(3, px, px))
        ax.imshow(np.moveaxis(im, 0, 2), extent=(b[0], b[2], b[1], b[3]))
        ax.plot(old_xy[:, 0], old_xy[:, 1], color="white", lw=1.2, ls=(0, (4, 3)), path_effects=halo,
                label="axe BD TOPO")
        win = np.abs(pk - k) < 1.5 * h + 20
        for xy_, col, lab in ((gl, "#ffd23f", "bord gauche"), (dr, "#3fd6ff", "bord droit")):
            ax.plot(xy_[win, 0], xy_[win, 1], color=col, lw=1.3, label=lab)
        ax.plot(axe[win, 0], axe[win, 1], color=ORANGE, lw=1.0, ls=(0, (6, 3)), label="nouvel axe")
        interp = win & (src == "interpole")
        ax.plot(axe[interp, 0], axe[interp, 1], "o", color=RED, ms=2.2, label="bords interpolés")
        ax.plot([b[0] + 0.06 * 2 * h, b[0] + 0.06 * 2 * h + (10 if h > 20 else 5)], [b[1] + 0.06 * 2 * h] * 2,
                color="white", lw=3, path_effects=halo)
        ax.text(b[0] + 0.06 * 2 * h, b[1] + 0.09 * 2 * h, "10 m" if h > 20 else "5 m", color="white", fontsize=8,
                path_effects=halo)
        ax.set_xlim(b[0], b[2]), ax.set_ylim(b[1], b[3])
        ax.set_xticks([]), ax.set_yticks([])
        ax.set_title(f"PK {k:.0f} - {label}", loc="left", fontsize=9, color=INK, pad=4)
    h_, l_ = axs.flat[0].get_legend_handles_labels()
    leg = fig.legend(h_, l_, loc="lower center", ncol=5, frameon=True, facecolor="#9a9990", edgecolor="none")
    for t in leg.get_texts():
        t.set_color("white")
    fig.suptitle(titre or f"ES Le Grand Caunet - bords de chaussée détectés (LiDAR HD + ortho IRC), fond BD ORTHO "
                 f"20 cm, extraits de {2 * h:.0f} m - PK sur le nouvel axe", x=0.01, ha="left", color=INK, fontsize=11)
    fig.tight_layout(rect=(0, 0.09 / nl, 1, 1 - 0.06 / nl), h_pad=3.0)
    path = FIG3 / name
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
    Image.open(path).convert("RGB").quantize(256, method=Image.Quantize.MEDIANCUT).save(path, optimize=True)


def courbes(pk, width, offset, src, bridges, L):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(13, 6.2), sharex=True, gridspec_kw={"hspace": 0.12})
    for name, col in SRC_COLORS.items():
        for i0, i1 in runs(src == name):
            a1.axvspan(pk[i0] - 0.5, pk[i1] + 0.5, ymin=0, ymax=0.04, color=col, lw=0)
    a1.plot(pk, width, color=INK, lw=0.9)
    a1.axhline(np.median(width[(pk >= 0) & (pk <= L)]), color=MUTED, lw=0.8, ls="--")  # médiane de l'ES
    for a, b in bridges:
        a1.axvspan(a, b, color=GRID, lw=0, zorder=0)
    a1.set_ylim(3.0, 10.5)
    a1.set_ylabel("largeur de chaussée (m)")
    a1.grid(axis="y", color=GRID, lw=0.8)
    hs = [plt.Rectangle((0, 0), 1, 1, color=c) for c in SRC_COLORS.values()] + [plt.Rectangle((0, 0), 1, 1, color=GRID)]
    a1.legend(hs, [f"source : {k}" for k in SRC_COLORS] + ["pont / ponceau"], loc="upper right", ncol=5,
              frameon=False, fontsize=8)
    a1.set_title("ES Le Grand Caunet - largeur mesurée et décalage du nouvel axe par rapport à la BD TOPO",
                 loc="left", color=INK, fontsize=11)
    a2.fill_between(pk, offset, 0, color=BLUE, alpha=0.25, lw=0)
    a2.plot(pk, offset, color=BLUE, lw=0.9)
    a2.axhline(0, color="#c3c2b7", lw=1)
    a2.set_ylabel("décalage latéral (m)\n+ nouvel axe à droite")
    a2.set_xlabel("PK sur le nouvel axe (m)")
    a2.grid(axis="y", color=GRID, lw=0.8)
    for a in (a1, a2):
        for k in (0, L):
            a.axvline(k, color=INK2, lw=0.8, ls=":")
    a2.set_xlim(pk[0] - 20, pk[-1] + 20)
    fig.savefig(FIG3 / "largeur_decalage.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


# --- chaîne principale -------------------------------------------------------------
def main():
    R = Rasters()
    pk_old, old_xy = axe_bdtopo()
    s, xy = resample(old_xy, 1.0)
    pk_ref = s + pk_old[0]
    keep = (pk_ref >= PK_MIN) & (pk_ref <= PK_MAX)
    xy, pk_ref = xy[keep], pk_ref[keep]

    for it in (1, 2):                                   # recentrage itératif
        res = passe(R, xy, pk_ref)
        new_xy, new_ref = recentre(xy, pk_ref, res)
        shift = np.median(np.abs(res["edge"].mean(axis=1)))
        print(f"itération {it} : recentrage médian {shift:.2f} m, max {np.abs(res['edge'].mean(axis=1)).max():.1f} m")
        xy, pk_ref = new_xy, new_ref
    res = passe(R, xy, pk_ref)                          # mesure finale sur l'axe recentré
    nr, edge = res["nr"], res["edge"]
    gl, dr = xy + edge[:, :1] * nr, xy + edge[:, 1:] * nr
    axe = (gl + dr) / 2

    # PK : origine et arrivée = projection des points calés sur l'ancien axe
    cal = json.loads((OUT / "calage_es.json").read_text(encoding="utf-8"))
    line = LineString(axe)
    s_ax = cumdist(axe)
    s0 = line.project(Point(cal["depart_cale"]["x_l93"], cal["depart_cale"]["y_l93"]))
    s1 = line.project(Point(cal["arrivee_calee"]["x_l93"], cal["arrivee_calee"]["y_l93"]))
    L = s1 - s0
    # étendue : du début de l'axe (contrôle horaire) au point stop + SORTIE_APRES_STOP,
    # ce dernier pris sur l'ancien axe puis projeté ; l'arrivée garde son point exact
    p_end = [np.interp(PK_STOP_BDTOPO + SORTIE_APRES_STOP, pk_old, old_xy[:, k]) for k in (0, 1)]
    s_end = line.project(Point(*p_end))
    pk = np.arange(np.ceil(-s0), s_end - s0, 1.0)
    pk = np.sort(np.append(pk, L)) if np.min(np.abs(pk - L)) > 1e-6 else pk
    zone = np.where(pk < 0, "approche", np.where(pk <= L + 1e-6, "es", "sortie"))
    es = zone == "es"
    p_stop = [np.interp(PK_STOP_BDTOPO, pk_old, old_xy[:, k]) for k in (0, 1)]
    pk_stop = line.project(Point(*p_stop)) - s0
    def at(v):
        return np.column_stack([np.interp(pk + s0, s_ax, v[:, k]) for k in range(v.shape[1])])
    A, G, D = at(axe), at(gl), at(dr)
    near = np.clip(np.rint(np.interp(pk + s0, s_ax, np.arange(len(s_ax)))).astype(int), 0, len(s_ax) - 1)
    code, bridge = res["code"][near], res["bridge"][near]
    ref = at(pk_ref[:, None])[:, 0]
    src = source_profil(code)
    width = np.hypot(*(D - G).T)

    # altitudes : MNT à l'axe et aux bords ; dévers = pente de la droite ajustée sur le
    # profil en travers entre les bords (0,5 m en retrait), lu dans le MNT
    za, zg, zd = R.z(A[:, 0], A[:, 1]), R.z(G[:, 0], G[:, 1]), R.z(D[:, 0], D[:, 1])
    nA = normales(A)
    Zp = R.z(A[:, 0, None] + T[None] * nA[:, 0, None], A[:, 1, None] + T[None] * nA[:, 1, None])
    m = np.abs(T[None]) <= (width[:, None] / 2 - 0.5)
    n_, st, sz = m.sum(1), (m * T).sum(1), (m * Zp).sum(1)
    slope = (n_ * (m * T * Zp).sum(1) - st * sz) / (n_ * (m * T * T).sum(1) - st ** 2)
    devers = -slope * 100                               # > 0 : bord droit plus bas
    # ponts : altitude interpolée entre culées, dévers interpolé entre les abords
    spans = []
    for i0, i1 in runs(bridge):
        a, b = max(i0 - 1, 0), min(i1 + 1, len(pk) - 1)
        spans.append((pk[i0], pk[i1]))
        za[i0:i1 + 1] = np.interp(pk[i0:i1 + 1], [pk[a], pk[b]], [za[max(a - 2, 0):a + 1].mean(), za[b:b + 3].mean()])
        devers[i0:i1 + 1] = np.interp(pk[i0:i1 + 1], [pk[a], pk[b]], [devers[a], devers[b]])
        zg[i0:i1 + 1] = za[i0:i1 + 1] + devers[i0:i1 + 1] / 100 * width[i0:i1 + 1] / 2
        zd[i0:i1 + 1] = za[i0:i1 + 1] - devers[i0:i1 + 1] / 100 * width[i0:i1 + 1] / 2
    # creux résiduels : un ponceau que la BD TOPO situe quelques mètres à côté de sa position
    # réelle laisse une entaille étroite du MNT dans le profil. Fermeture morphologique sur
    # 31 m ; seuls les creux de plus de 40 cm sont comblés, les cuvettes de la route restent.
    creux = []
    for i0, i1 in runs((grey_closing(za, size=31) - za) > 0.4):
        a, b = max(i0 - 3, 0), min(i1 + 3, len(pk) - 1)
        dz = np.maximum(np.interp(pk[a:b + 1], [pk[a], pk[b]], [za[a], za[b]]) - za[a:b + 1], 0)
        for z in (za, zg, zd):
            z[a:b + 1] += dz
        creux.append((round(float(pk[i0])), round(float(pk[i1])), round(float(dz.max()), 2)))
    print("creux comblés hors ouvrages BD TOPO (pk début, pk fin, profondeur m) :", creux)
    za, zg, zd = (savgol_filter(z, 7, 2) for z in (za, zg, zd))
    devers = savgol_filter(devers, 7, 2)

    # décalage latéral signé entre l'ancien axe et le nouveau (+ : nouvel axe à droite)
    old_line = LineString(old_xy)
    off = np.array([old_line.distance(Point(p)) for p in A])
    for i, p in enumerate(A):
        q = old_line.interpolate(old_line.project(Point(p)))
        off[i] *= 1 if (p - np.array(q.coords[0])) @ nA[i] >= 0 else -1

    # --- écritures ------------------------------------------------------------------
    with open(OUT / "chaussee_precise.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pk_m", "x_axe", "y_axe", "z_axe", "x_gauche", "y_gauche", "z_gauche", "x_droite", "y_droite",
                    "z_droite", "largeur_m", "devers_pct", "source", "zone"])
        for i in range(len(pk)):
            w.writerow([round(pk[i], 1), *np.round(A[i], 2), round(float(za[i]), 2), *np.round(G[i], 2),
                        round(float(zg[i]), 2), *np.round(D[i], 2), round(float(zd[i]), 2), round(float(width[i]), 2),
                        round(float(devers[i]), 1), src[i], zone[i]])
    feats = []
    for name, P_, Z_ in (("axe", A, za), ("bord_gauche", G, zg), ("bord_droit", D, zd)):
        coords = [[*map(lambda v: round(v, 7), wgs(x, y)), round(float(z), 2)] for (x, y), z in zip(P_, Z_)]
        feats.append({"type": "Feature", "properties": {"nom": name, "longueur_es_m": round(L, 1),
                                                        "pk_debut_m": round(float(pk[0]), 1),
                                                        "pk_fin_m": round(float(pk[-1]), 1)},
                      "geometry": {"type": "LineString", "coordinates": coords}})
    write_geojson(OUT / "chaussee_precise.geojson", feats, "chaussee_precise")

    _, junc = zones_neutres(ref)
    interp_runs = []
    for a, b in runs((src == "interpole") & es):
        if pk[b] - pk[a] + 1 > 20:
            motif = " + ".join(m for m, hit in (("pont", bridge[a:b + 1].any()), ("débouché", junc[a:b + 1].any()))
                               if hit) or "surlargeur ou bord indécidable"
            interp_runs.append({"pk_debut": round(float(pk[a])), "pk_fin": round(float(pk[b])), "motif": motif})
    # concordance brute des deux estimateurs (profils de la passe finale où les deux mesurent)
    lid_, ort_ = res["lid"][near[es]], res["ort"][near[es]]
    both = np.isfinite(lid_) & np.isfinite(ort_)
    dd = np.abs(lid_ - ort_)[both]
    imax = int(np.argmax(np.abs(off) * es))
    W, S, O, DV = width[es], src[es], np.abs(off[es]), devers[es]
    hors = {}
    for zn in ("approche", "sortie"):
        mz = zone == zn
        hors[zn] = {"pk_debut_m": round(float(pk[mz][0]), 1), "pk_fin_m": round(float(pk[mz][-1]), 1),
                    "longueur_m": int(mz.sum()), "part_interpolee_pct": round(float((src[mz] == "interpole").mean() * 100), 1),
                    "troncons_interpoles_sup_20m": [(round(float(pk[a])), round(float(pk[b])))
                                                    for a, b in runs((src == "interpole") & mz)
                                                    if pk[b] - pk[a] + 1 > 20]}
    hors["note"] = ("statistiques ci-dessus calculées sur la seule zone es ; approche = début de l'axe BD TOPO "
                    "(contrôle horaire) -> départ, sortie = arrivée -> point stop + 60 m "
                    f"(point stop au PK {pk_stop:.0f} du nouvel axe)")
    q = {
        "longueur_depart_arrivee_m": round(float(L), 1),
        "longueur_officielle_m": 6702,
        "largeur_m": {"mediane": round(float(np.median(W)), 2), "p5": round(float(np.percentile(W, 5)), 2),
                      "p95": round(float(np.percentile(W, 95)), 2)},
        "part_lineaire_par_source_pct": {k: round(float((S == k).mean() * 100), 1) for k in SRC_COLORS},
        "decalage_lateral_bdtopo_m": {"mediane": round(float(np.median(O)), 2),
                                      "p95": round(float(np.percentile(O, 95)), 2),
                                      "max": round(float(O.max()), 2), "pk_max": round(float(pk[imax]))},
        "troncons_interpoles_sup_20m": {"nombre": len(interp_runs), "troncons": interp_runs},
        "concordance_lidar_image": {"part_des_bords_mesures_par_les_deux_pct": round(float(both.mean() * 100), 1),
                                    "ecart_median_m": round(float(np.median(dd)), 2),
                                    "ecart_p90_m": round(float(np.percentile(dd, 90)), 2)},
        "devers_pct": {"mediane_abs": round(float(np.median(np.abs(DV))), 1),
                       "p95_abs": round(float(np.percentile(np.abs(DV), 95)), 1)},
        "hors_es": hors,
        "sources": {"lidar+ortho": "les deux bords mesurés, LiDAR et image concordent (< 1 m)",
                    "lidar": "au moins un bord pris sur la seule rupture LiDAR (sous les arbres, à l'ombre)",
                    "ortho": "au moins un bord pris sur la seule image (pont, plate-forme sans rupture)",
                    "interpole": "au moins un bord interpolé sur plus de 3 m (pont sans image, débouché, "
                                 "surlargeur rejetée, aucune source fiable)"},
        "methode": "profils en travers tous les mètres (±15 m, pas 0,25 m) sur l'axe courant ; bord LiDAR = fin "
                   "de la plate-forme lisse du MNT ; bord image = fin de l'asphalte visible (NDVI bas, luminosité "
                   "de la route) hors arbres et ombre ; l'image fait foi quand elle mesure ; filtrage le long du "
                   "parcours, interpolation, lissage (milieu σ 4 m, bords σ 2 m) ; 2 recentrages de l'axe",
        "precision_indicative": "bords : ±0,5 m là où l'asphalte est visible ; 1 à 2 m possibles sous les arbres "
                                "(plate-forme LiDAR incluant un accotement plat) ; axe : bien meilleur que la BD TOPO",
    }
    (OUT / "chaussee_precise_qualite.json").write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(q, ensure_ascii=False, indent=2))

    # --- figures de contrôle ------------------------------------------------------------
    # couvert : part du profil entre les bords sous plus de 2 m de végétation (hors ponts)
    cover = np.array([(c[(T > a) & (T < b)] > 2.0).mean() for c, (a, b) in zip(res["P"]["can"], edge)])
    cover = uniform_filter1d(cover[near], 41)
    far_bridge = np.ones(len(pk), bool)
    for a, b in spans:
        far_bridge &= (pk < a - 40) | (pk > b + 40)
    dense = int(np.argmax(np.where((pk > 100) & (pk < L - 100) & far_bridge, cover, 0)))
    picks = [(pk[dense], f"couvert dense ({cover[dense] * 100:.0f} % de la chaussée sous les arbres)"),
             (pk[imax], f"décalage BD TOPO max ({abs(off[imax]):.1f} m)"), (3620.0, "carrefour du Lion d'Or")]
    b5 = max(spans, key=lambda ab: ab[1] - ab[0]) if spans else (5500, 5540)
    picks.append(((b5[0] + b5[1]) / 2, "pont (plus long ouvrage)"))
    for k in (400, 1300, 2300, 4700, 6400, 5100, 2900):
        if len(picks) == 8:
            break
        if all(abs(k - p) > 250 for p, _ in picks):
            picks.append((float(k), "extrait courant"))
    picks.sort()
    planche(R, old_xy, pk, A, G, D, src, picks, 40, "planche_extraits.png", 110)
    planche(R, old_xy, pk, A, G, D, src, picks, 15, "planche_zooms_30m.png", 110)
    ext = [(pk[0] + 30, "approche : contrôle horaire, carrefour D3 / D3D"), (-90.0, "approche : parking"),
           (0.0, "départ"), (L, "arrivée"), (pk_stop, "point stop"), (pk[-1] - 25, "fin de la sortie (stop + 60 m)")]
    planche(R, old_xy, pk, A, G, D, src, ext, 30, "planche_extremites.png", 95, grille=(2, 3),
            titre="Extrémités : approche (avant départ) et sortie (après arrivée), extraits de 60 m - PK sur le nouvel axe")
    courbes(pk, width, off, src, spans, L)
    print("figures écrites dans", FIG3)


if __name__ == "__main__":
    main()
