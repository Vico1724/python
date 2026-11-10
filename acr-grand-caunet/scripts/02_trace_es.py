"""Étape 2 - Reconstruit le tracé de l'ES sur le réseau routier IGN (BD TOPO).

Méthode : chaque point GPS officiel est accroché au tronçon de route le plus
proche, puis on cherche le plus court chemin routier d'un point au suivant.
Le résultat est comparé aux PK officiels : c'est le contrôle de validité.

Sorties (data/processed) :
  axe_bdtopo_l93.csv            axe complet (Lambert-93 + altitude BD TOPO + PK)
  trace_es.geojson/.gpx/.kml    tracé et points, lisibles dans Google Earth, QGIS...
  points_officiels_recales.csv  contrôle PK officiel / PK mesuré
  troncons_es.csv               attributs IGN des tronçons empruntés (largeur, etc.)
"""
import csv
import heapq
import json
import math
from collections import defaultdict
from xml.sax.saxutils import escape

import numpy as np

from acr_geo import OUT, RAW, REF, cumdist, l93, load_official, project_on_line, wgs, write_geojson

# L'ES emprunte la D3D puis la D1 (carte officielle + avis de fermeture de routes) ;
# la D3 ne sert qu'à l'approche du CH. On n'accroche les points officiels qu'à ces
# routes : sinon un point imprimé à 5 décimales peut tomber sur une piste voisine.
STAGE_ROADS = {"D3D", "D1", "D3"}
KEEP = ("cleabs", "cpx_numero", "nature", "largeur_de_chaussee", "nombre_de_voies",
        "sens_de_circulation", "importance", "nom_collaboratif_gauche",
        "precision_planimetrique", "precision_altimetrique",
        "methode_d_acquisition_planimetrique", "insee_commune_gauche",
        "position_par_rapport_au_sol", "date_modification")


def load_edges():
    edges = []
    for f in json.loads((RAW / "troncon_de_route.geojson").read_text(encoding="utf-8"))["features"]:
        p = f["properties"]
        if p.get("cpx_numero") not in STAGE_ROADS or f["geometry"]["type"] != "LineString":
            continue
        c = f["geometry"]["coordinates"]
        xyz = np.array([[*l93(pt[0], pt[1]), pt[2] if len(pt) > 2 else np.nan] for pt in c])
        edges.append({"xyz": xyz, "props": {k: p.get(k) for k in KEEP}})
    return edges


def key(pt):
    return (round(pt[0], 1), round(pt[1], 1))


def split_edge(edges, p):
    """Accroche p au tronçon le plus proche et le coupe en deux à cet endroit."""
    best = (math.inf, None, 0.0)
    for i, e in enumerate(edges):
        xy = e["xyz"][:, :2]
        if (abs(xy[:, 0] - p[0]).min() > 150) or (abs(xy[:, 1] - p[1]).min() > 150):
            continue
        s, d = project_on_line(xy, p)
        if d < best[0]:
            best = (d, i, s)
    d, i, s = best
    e = edges.pop(i)
    xyz = e["xyz"]
    cs = cumdist(xyz[:, :2])
    q = np.array([np.interp(s, cs, xyz[:, k]) for k in range(3)])
    j = int(np.searchsorted(cs, s, side="right"))
    a = np.vstack([xyz[:j], q]) if s > 1e-6 else np.vstack([q, q])
    b = np.vstack([q, xyz[j:]]) if cs[-1] - s > 1e-6 else np.vstack([q, q])
    edges += [{"xyz": a, "props": e["props"]}, {"xyz": b, "props": e["props"]}]
    return key(q), d


def dijkstra(adj, src, dst):
    dist, prev, pq = {src: 0.0}, {}, [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == dst:
            break
        if d > dist.get(u, math.inf):
            continue
        for v, w, ei, rev in adj[u]:
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v], prev[v] = nd, (u, ei, rev)
                heapq.heappush(pq, (nd, v))
    path, u = [], dst
    while u != src:
        u0, ei, rev = prev[u]
        path.append((ei, rev))
        u = u0
    return path[::-1]


def main():
    off = load_official()
    pts = off["points"]
    edges = load_edges()
    # Un point imprimé à plus de 25 m de la route (cas du « Départ » sur la carte 2026)
    # n'est pas utilisé pour le routage : sa position est recalée plus bas par les PK.
    nodes = []
    for p in pts:
        n, d = split_edge(edges, l93(p["lon"], p["lat"]))
        if d <= 25:
            nodes.append(n)

    adj = defaultdict(list)
    for i, e in enumerate(edges):
        L = float(cumdist(e["xyz"][:, :2])[-1])
        u, v = key(e["xyz"][0]), key(e["xyz"][-1])
        adj[u].append((v, L, i, False))
        adj[v].append((u, L, i, True))

    chain, used, seen = [], [], set()
    for a, b in zip(nodes[:-1], nodes[1:]):
        for ei, rev in dijkstra(adj, a, b):
            xyz = edges[ei]["xyz"][::-1] if rev else edges[ei]["xyz"]
            chain.append(xyz if not chain else xyz[1:])
            if ei in seen:
                print("ATTENTION : tronçon parcouru deux fois (aller-retour suspect)", edges[ei]["props"]["cleabs"])
            seen.add(ei)
            used.append((ei, float(cumdist(xyz[:, :2])[-1])))
    axis = np.vstack(chain)
    axis = axis[np.concatenate([[True], np.abs(np.diff(axis[:, :2], axis=0)).sum(axis=1) > 1e-6])]
    s = cumdist(axis[:, :2])

    # --- calage : origine des PK ----------------------------------------------
    # Les PK officiels (mesurés au compteur par l'organisateur) font foi ; les
    # coordonnées imprimées sont indicatives. L'origine est choisie pour annuler
    # l'écart médian sur les 9 points intermédiaires.
    proj = {p["id"]: project_on_line(axis[:, :2], l93(p["lon"], p["lat"])) for p in pts}
    inter = [p for p in pts if p["role"] == "intermediaire"]
    s0_cal = float(np.median([proj[p["id"]][0] - p["pk_km"] * 1000 for p in inter]))
    # Lignes retenues (data/reference/lignes_es.json) : le PK 0 du projet est la ligne de
    # départ réelle, décalée par rapport à l'origine des PK officiels ; l'arrivée garde
    # sa position dans le calage officiel.
    lignes = json.loads((REF / "lignes_es.json").read_text(encoding="utf-8"))
    dec = lignes["depart"]["decalage_par_rapport_au_calage_pk_m"]
    s0 = s0_cal + dec
    pk = s - s0
    L_off = off["longueur_officielle_km"] * 1000
    L = lignes["arrivee"]["pk_dans_le_calage_officiel_m"] - dec     # PK de l'arrivée, départ = 0
    rows = []
    for p in pts:
        si, d = proj[p["id"]]
        x, y = l93(p["lon"], p["lat"])
        rows.append({"id": p["id"], "role": p["role"], "lat": p["lat"], "lon": p["lon"],
                     "x_l93": round(x, 1), "y_l93": round(y, 1),
                     "pk_officiel_m": round(p["pk_km"] * 1000),
                     "pk_mesure_m": round(si - s0, 1),
                     "ecart_pk_m": round(si - s0 - p["pk_km"] * 1000, 1),
                     "ecart_lateral_m": round(d, 1)})
    # résidus du calage officiel (hors décalage du départ retenu)
    res = np.array([r["ecart_pk_m"] for r in rows if r["role"] == "intermediaire"]) + dec

    def at(k):
        x, y = (float(np.interp(k, pk, axis[:, c])) for c in (0, 1))
        lon, lat = wgs(x, y)
        return {"pk_m": k, "lat": round(lat, 6), "lon": round(lon, 6), "x_l93": round(x, 1), "y_l93": round(y, 1)}

    (OUT / "calage_es.json").write_text(json.dumps({
        "methode": "calage officiel = médiane des écarts sur les 9 points intermédiaires de la carte ; "
                   "PK 0 du projet = ligne de départ retenue (lignes_es.json), décalée de ce calage ; "
                   "PK mesurés en distance horizontale sur l'axe BD TOPO",
        "decalage_depart_par_rapport_au_calage_officiel_m": dec,
        "longueur_officielle_m": L_off,
        "longueur_entre_lignes_axe_bdtopo_m": L,
        "depart_cale": at(0.0), "arrivee_calee": at(L),
        "ecart_type_residus_intermediaires_m": round(float(res.std()), 1),
        "residu_max_intermediaires_m": round(float(np.abs(res).max()), 1),
        "arrivee_imprimee_pk_mesure_m": next(r["pk_mesure_m"] for r in rows if r["id"] == "ARRIVEE"),
        "depart_imprime_ecart_lateral_m": next(r["ecart_lateral_m"] for r in rows if r["id"] == "DEPART"),
        "incertitude_position_lignes_m": 15,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    with open(OUT / "points_officiels_recales.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    with open(OUT / "axe_bdtopo_l93.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pk_m", "x_l93", "y_l93", "z_bdtopo", "lon", "lat"])
        for (x, y, z), k in zip(axis, pk):
            lon, lat = wgs(x, y)
            w.writerow([round(k, 2), round(x, 2), round(y, 2), round(z, 1), round(lon, 7), round(lat, 7)])

    # --- tronçons empruntés ---------------------------------------------------
    with open(OUT / "troncons_es.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pk_debut_m", "longueur_m", *KEEP])
        acc = -s0  # s0 = abscisse du départ calé
        for ei, L in used:
            if L > 0.01:
                w.writerow([round(acc, 1), round(L, 1), *[edges[ei]["props"][k] for k in KEEP]])
            acc += L

    # --- exports cartographiques ---------------------------------------------
    def ll(sub):
        return [[*map(lambda v: round(v, 7), wgs(x, y)), round(z, 1)] for x, y, z in sub]

    i0, i1 = np.searchsorted(pk, 0.0), np.searchsorted(pk, L)
    feats = [
        {"type": "Feature", "properties": {"name": "ES Le Grand Caunet - secteur chronométré",
                                           "longueur_officielle_m": 6702, "longueur_axe_m": L},
         "geometry": {"type": "LineString", "coordinates": ll(axis[i0:i1])}},
        {"type": "Feature", "properties": {"name": "Tracé complet (CH -> fin de zone fermée)"},
         "geometry": {"type": "LineString", "coordinates": ll(axis)}},
    ] + [{"type": "Feature", "properties": {k: r[k] for k in ("id", "role", "pk_officiel_m", "pk_mesure_m")}
          | {"label": p["label"]},
          "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]}} for p, r in zip(pts, rows)]
    write_geojson(OUT / "trace_es.geojson", feats, "ES Le Grand Caunet 2026")

    trk = "".join(f'<trkpt lat="{la}" lon="{lo}"><ele>{z}</ele></trkpt>' for lo, la, z in ll(axis))
    wpt = "".join(f'<wpt lat="{p["lat"]}" lon="{p["lon"]}"><name>{escape(p["id"])}</name>'
                  f'<desc>{escape(p["label"])}</desc></wpt>' for p in pts)
    (OUT / "trace_es.gpx").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><gpx version="1.1" creator="acr-grand-caunet" '
        'xmlns="http://www.topografix.com/GPX/1/1">' + wpt +
        f"<trk><name>ES Le Grand Caunet 2026</name><trkseg>{trk}</trkseg></trk></gpx>", encoding="utf-8")
    coords = " ".join(f"{lo},{la},{z}" for lo, la, z in ll(axis))
    pm = "".join(f"<Placemark><name>{escape(p['id'])}</name><description>{escape(p['label'])}</description>"
                 f"<Point><coordinates>{p['lon']},{p['lat']},0</coordinates></Point></Placemark>" for p in pts)
    (OUT / "trace_es.kml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        "<name>ES Le Grand Caunet 2026</name><Placemark><name>Tracé</name><Style><LineStyle>"
        "<color>ff0000ff</color><width>4</width></LineStyle></Style><LineString><tessellate>1</tessellate>"
        f"<coordinates>{coords}</coordinates></LineString></Placemark>{pm}</Document></kml>", encoding="utf-8")

    print(f"axe : {len(axis)} sommets, {s[-1]:.0f} m au total ; résidus intermédiaires : "
          f"écart-type {res.std():.1f} m, max {np.abs(res).max():.1f} m")
    print(f"{'point':9s} {'PK off.':>8s} {'PK mes.':>8s} {'écart':>7s} {'latéral':>8s}")
    for r in rows:
        print(f"{r['id']:9s} {r['pk_officiel_m']:8d} {r['pk_mesure_m']:8.1f} {r['ecart_pk_m']:7.1f} {r['ecart_lateral_m']:8.1f}")


if __name__ == "__main__":
    main()
