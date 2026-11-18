"""Étape 5 - Découpe les couches IGN au couloir de l'ES et dresse l'inventaire du décor.

Sorties (data/processed) :
  couloir/<couche>.geojson   objets situés à moins de 300 m de l'axe (WGS84)
  carrefours_es.csv          routes, pistes et sentiers qui débouchent sur l'ES, avec leur PK
  inventaire_couloir.json    comptages : bâtiments, végétation, essences forestières...
"""
import csv
import json

import numpy as np
import shapely
from shapely.geometry import LineString, Point, mapping, shape

from acr_geo import OUT, RAW, TO_L93, TO_WGS, longueur_es, project_on_line

BUFFER = 300
CLIP = {"zone_de_vegetation", "bdforet_formation_vegetale", "surface_hydrographique", "commune"}
SKIP = {"commune"}


def to_l93(geom):
    return shapely.transform(shapely.force_2d(geom), lambda c: np.column_stack(TO_L93.transform(c[:, 0], c[:, 1])))


def to_wgs(geom):
    return shapely.transform(geom, lambda c: np.round(np.column_stack(TO_WGS.transform(c[:, 0], c[:, 1])), 7))


def canopy(axis, near=30):
    """Hauteur du couvert (MNS - MNT LiDAR HD) à moins de `near` m de l'axe, hors chaussée."""
    import rasterio
    from rasterio.features import geometry_mask
    if not (RAW / "mns_lidarhd_50cm.tif").exists():
        return None
    ring = axis.buffer(near).difference(axis.buffer(5))
    x0, y0, x1, y1 = ring.bounds
    with rasterio.open(RAW / "mns_lidarhd_50cm.tif") as a, rasterio.open(RAW / "mnt_lidarhd_50cm.tif") as b:
        win = rasterio.windows.from_bounds(x0, y0, x1, y1, a.transform).round_offsets().round_lengths()
        mns, mnt = a.read(1, window=win), b.read(1, window=win)
        tr = a.window_transform(win)
    ok = geometry_mask([ring], out_shape=mns.shape, transform=tr, invert=True) & (mns > -1000) & (mnt > -1000)
    h = (mns - mnt)[ok]
    return {"bande_m": f"5 à {near} m de l'axe", "part_couvert_sup_2m_pct": round(float((h > 2).mean() * 100)),
            "mediane_des_arbres_m": round(float(np.median(h[h > 2])), 1),
            "p90_des_arbres_m": round(float(np.percentile(h[h > 2], 90)), 1),
            "max_m": round(float(np.percentile(h, 99.9)), 1)}


def main():
    L = longueur_es()
    with open(OUT / "axe_bdtopo_l93.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    pk0 = float(rows[0]["pk_m"])
    xy = np.array([[float(r["x_l93"]), float(r["y_l93"])] for r in rows])
    axis = LineString(xy)
    zone = axis.buffer(BUFFER)
    (OUT / "couloir").mkdir(exist_ok=True)
    inv, layers = {"rayon_couloir_m": BUFFER, "couches": {}}, {}

    for path in sorted(RAW.glob("*.geojson")):
        name = path.stem
        if name in SKIP:
            continue
        kept = []
        for f in json.loads(path.read_text(encoding="utf-8"))["features"]:
            if not f.get("geometry"):
                continue
            g = to_l93(shape(f["geometry"]))
            if not g.is_valid:
                g = g.buffer(0)
            if not g.intersects(zone):
                continue
            if name in CLIP:
                g = g.intersection(zone)
                if g.is_empty:
                    continue
            props = {k: v for k, v in f["properties"].items() if v not in (None, "", False)}
            props["dist_axe_m"] = round(g.distance(axis), 1)
            kept.append((g, props))
        layers[name] = kept
        inv["couches"][name] = len(kept)
        if kept:
            fc = {"type": "FeatureCollection", "name": name, "features": [
                {"type": "Feature", "properties": p, "geometry": mapping(to_wgs(g))} for g, p in kept]}
            (OUT / "couloir" / f"{name}.geojson").write_text(
                json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # --- carrefours : tout tronçon qui touche l'axe sans en faire partie ------
    used = set()
    with open(OUT / "troncons_es.csv", encoding="utf-8") as f:
        used = {r["cleabs"] for r in csv.DictReader(f)}
    junctions = {}
    cum = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    for g, p in layers.get("troncon_de_route", []):
        if p.get("cleabs") in used or g.distance(axis) > 1.0:
            continue
        ends = [g.coords[0], g.coords[-1]]
        pt = min(ends, key=lambda c: axis.distance(Point(c)))
        s, _ = project_on_line(xy, pt[:2])
        k = round(s + pk0)
        i = int(np.clip(np.searchsorted(cum, s), 1, len(xy) - 1))
        t = xy[i] - xy[i - 1]                                   # sens de marche
        far = g.interpolate(min(15, g.length / 2) if pt == ends[0] else g.length - min(15, g.length / 2))
        v = np.array(far.coords[0][:2]) - np.array(pt[:2])      # direction de la voie adjacente
        side = t[0] * v[1] - t[1] * v[0]
        junctions.setdefault(k, []).append({
            "pk_m": k, "cote": "gauche" if side > 0 else "droite", "nature": p.get("nature"),
            "numero": p.get("cpx_numero", ""), "nom": p.get("nom_collaboratif_gauche", ""),
            "largeur_m": p.get("largeur_de_chaussee", ""), "dans_es": 0 <= k <= L})
    flat = [j for k in sorted(junctions) for j in junctions[k]]
    with open(OUT / "carrefours_es.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(flat[0]))
        w.writeheader()
        w.writerows(flat)

    # --- inventaire -----------------------------------------------------------
    b = [p["dist_axe_m"] for _, p in layers.get("batiment", [])]
    inv["batiments"] = {f"a_moins_de_{d}_m": sum(x <= d for x in b) for d in (25, 50, 100, 300)}
    near = axis.buffer(100)
    for name, field in (("bdforet_formation_vegetale", "tfv"), ("zone_de_vegetation", "nature")):
        area = {}
        for g, p in layers.get(name, []):
            a = g.intersection(near).area
            if a > 0:
                area[p.get(field, "?")] = area.get(p.get(field, "?"), 0) + a
        inv[f"{name}_part_dans_100m_pct"] = {k: round(v / near.area * 100, 1)
                                             for k, v in sorted(area.items(), key=lambda kv: -kv[1])}
    inv["carrefours_dans_es"] = {}
    for j in flat:
        if j["dans_es"]:
            inv["carrefours_dans_es"][j["nature"]] = inv["carrefours_dans_es"].get(j["nature"], 0) + 1
    inv["hauteur_vegetation_m"] = canopy(axis)
    communes = {}
    for f in json.loads((RAW / "commune.geojson").read_text(encoding="utf-8"))["features"]:
        ln = to_l93(shape(f["geometry"])).buffer(0).intersection(axis).length
        if ln > 1:
            communes[f"{f['properties'].get('nom_officiel')} ({f['properties'].get('code_insee')})"] = round(ln)
    inv["communes_longueur_axe_complet_m"] = communes
    (OUT / "inventaire_couloir.json").write_text(json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(inv, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
