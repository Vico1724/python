"""Terrains aplanis : emprises où le relief du MNT LiDAR est remplacé par un plan (parking du Grand Caunet).

Pourquoi : essai de la treizième version (14/11/2026, capture 3) : le parking forme « une butte de gravier qui borde
la route à gauche, les voitures posées dessus », là où Street View (data/reference/zone_depart.json, captures 6 à 16)
montre un parking plat au niveau de la route. Le MNT LiDAR HD y a un bourrelet de 0,3 à 0,5 m entre 1 et 5 m du
bord de chaussée (PK -55 à -40 ; talus de bordure, ou voitures garées mal classées) et des creux et bosses de
± 0,4 m dans le corps du parking. Les deux deviennent un plan.

Emprise : polygone du parking (zone_depart.json, objet de genre « parking », emprise_l93) réuni aux bandes de
data/reference/aires_et_pistes.json qui le prolongent jusqu'au bord de chaussée (notes « parking du Grand Caunet »
et « accès nord du parking »). Plan : ajusté au MNT dans l'emprise par moindres carrés, en écartant à chaque passe les
points à plus de 12 cm (bourrelet, creux) ; il garde donc la pente réelle du parking. Hors de l'emprise, raccord en
douceur au MNT sur MARGE_M. Le raccord à la chaussée reste celui de 08_modele_3d.py (2 m recalés sur le bord).

Lu par 08_modele_3d.py (MNT.z : terrain du décor et de la physique, donc 09, 12, 14) et par mobilier.py
(Route.z_terrain : altitude des objets posés au bord de la route).
"""
import json
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
MARGE_M = 3.0            # raccord au MNT autour de l'emprise
ECART_MAX_M = 0.12       # points écartés de l'ajustement du plan (bourrelet, creux)
NOTES = ("parking du Grand Caunet", "accès nord du parking")

_zones = None


def _bande(route, e, pas=1.0):
    """Polygone (x, y) d'une emprise d'aires_et_pistes.json : du décalage au décalage + profondeur, de pk_debut à pk_fin."""
    pks = np.arange(e["pk_debut_m"], e["pk_fin_m"] + 1e-6, pas)
    if pks[-1] < e["pk_fin_m"]:
        pks = np.append(pks, e["pk_fin_m"])
    pres = [route.point(p, e["cote"], e["decalage_m"])[:2] for p in pks]
    loin = [route.point(p, e["cote"], e["decalage_m"] + e["profondeur_m"])[:2] for p in pks]
    return pres + loin[::-1]


def zones():
    """[(polygone shapely préparé, polygone élargi de MARGE_M, coefficients (a, b, c) du plan z = a + b(x-x0) + c(y-y0), (x0, y0))]"""
    global _zones
    if _zones is not None:
        return _zones
    import shapely
    from shapely.geometry import Polygon
    import mobilier
    _zones = []
    fz = RACINE / "data" / "reference" / "zone_depart.json"
    fa = RACINE / "data" / "reference" / "aires_et_pistes.json"
    fm = RACINE / "data" / "raw" / "mnt_lidarhd_50cm.tif"
    if not (fz.exists() and fa.exists() and fm.exists()):
        return _zones
    parts = [Polygon(o["emprise_l93"]) for o in json.loads(fz.read_text(encoding="utf-8"))["objets"]
             if o.get("genre") == "parking" and o.get("emprise_l93")]
    route = mobilier.Route()
    parts += [Polygon(_bande(route, e)) for e in json.loads(fa.read_text(encoding="utf-8"))["emprises"]
              if any(n in e.get("note", "") for n in NOTES)]
    if not parts:
        return _zones
    poly = shapely.make_valid(shapely.union_all([p.buffer(0) for p in parts])).buffer(0.5).buffer(-0.5)
    # plan ajusté au MNT dans l'emprise
    import rasterio
    from rasterio.windows import from_bounds
    with rasterio.open(fm) as s:
        b = poly.bounds
        w = from_bounds(b[0] - 1, b[1] - 1, b[2] + 1, b[3] + 1, s.transform)
        a = s.read(1, window=w).astype(float)
        t = s.window_transform(w)
    ii, jj = np.indices(a.shape)
    xs, ys = t.c + (jj + 0.5) * t.a, t.f + (ii + 0.5) * t.e
    dans = shapely.contains_xy(poly, xs, ys) & (a > -1000)
    x, y, z = xs[dans], ys[dans], a[dans]
    x0, y0 = float(x.mean()), float(y.mean())
    garde = np.ones(len(z), bool)
    for _ in range(4):
        A = np.column_stack([np.ones(garde.sum()), x[garde] - x0, y[garde] - y0])
        coef = np.linalg.lstsq(A, z[garde], rcond=None)[0]
        res = z - (coef[0] + coef[1] * (x - x0) + coef[2] * (y - y0))
        garde = np.abs(res) <= max(ECART_MAX_M, float(np.percentile(np.abs(res), 60)))
    shapely.prepare(poly)
    large = poly.buffer(MARGE_M)
    shapely.prepare(large)
    _zones.append({"nom": "parking du Grand Caunet", "poly": poly, "large": large, "coef": coef, "origine": (x0, y0),
                   "points_gardes": int(garde.sum()), "points": int(len(z)),
                   "ecart_mnt_m": [round(float(res.min()), 2), round(float(res.max()), 2)]})
    return _zones


def aplanir(x, y, z):
    """Altitudes `z` (MNT) aux points (x, y) Lambert-93, remplacées par le plan dans les emprises aplanies et raccordées
    sur MARGE_M autour. Tableaux numpy ou scalaires ; renvoie un tableau de même forme que z."""
    zs = zones()
    z = np.asarray(z, float)
    if not zs:
        return z
    import shapely
    x, y = np.broadcast_to(np.asarray(x, float), z.shape), np.broadcast_to(np.asarray(y, float), z.shape)
    out = z.copy()
    for k in zs:
        pres = shapely.contains_xy(k["large"], x, y)
        if not pres.any():
            continue
        xp, yp = x[pres], y[pres]
        a, b, c = k["coef"]
        zp = a + b * (xp - k["origine"][0]) + c * (yp - k["origine"][1])
        d = shapely.distance(k["poly"], shapely.points(xp, yp))      # 0 dedans
        w = np.clip(1.0 - d / MARGE_M, 0.0, 1.0)
        w = w * w * (3 - 2 * w)
        out[pres] = w * zp + (1 - w) * out[pres]
    return out
