"""Préparation du village de Ceyreste (demande du 18/11/2026) : emprise, relief, bâti, rues, figure, chiffrage.

NE MODIFIE PAS l'emprise jouable : produit seulement des données et deux options chiffrées pour décision.
Sources : BD TOPO (bâtiments, tronçons de route, zones d'intérêt ; WFS Géoplateforme, Etalab 2.0), OpenStreetMap
(rues, salle polyvalente ; ODbL, Overpass et Nominatim), LiDAR HD (MNT 2 m du lointain déjà téléchargé).
Sorties :
  data/raw/village/*.geojson               collectes (non versionnées)
  data/processed/village/approche.geojson   itinéraire salle polyvalente -> mairie -> départ (D3)
  data/processed/village/batiments_*.geojson bâtiments retenus par option (emprise, hauteur BD TOPO)
  data/processed/village/chiffrage.json     longueurs, nombres de bâtiments, poids estimé par option
  figures/affinage/village_ceyreste.png     carte de l'extension
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString, Point, mapping, shape
import warnings
from shapely.ops import transform as stransform
warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acr_geo import FIG, OUT, RAW, TO_L93, TO_WGS, wfs_layer  # noqa: E402

DR = RAW / "village"; DR.mkdir(parents=True, exist_ok=True)
DO = OUT / "village"; DO.mkdir(parents=True, exist_ok=True)
DF = FIG / "affinage"; DF.mkdir(parents=True, exist_ok=True)
BBOX = (5.618, 43.204, 5.652, 43.228)
# Lieux : salle polyvalente (OSM, nœud 4374868094, via Nominatim), mairie (BD TOPO, zone d'intérêt « Mairie »)
SALLE = (5.6265816, 43.2102209)
MAIRIE = (5.63182, 43.21431)


def l93(g):
    return stransform(lambda x, y, z=None: TO_L93.transform(x, y), g)


def collecte():
    for nom, couche in (("batiment", "BDTOPO_V3:batiment"), ("troncon_de_route", "BDTOPO_V3:troncon_de_route"),
                        ("zone_d_activite", "BDTOPO_V3:zone_d_activite_ou_d_interet")):
        f = DR / f"{nom}.geojson"
        if not f.exists():
            try:
                feats = wfs_layer(couche, bbox_lonlat=BBOX)
            except Exception as e:  # couche facultative
                print(nom, "ECHEC", e); continue
            f.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")
        if f.exists():
            print(nom, len(json.loads(f.read_text(encoding="utf-8"))["features"]))


def itineraire():
    """Plus court chemin sur les tronçons BD TOPO (graphe par extrémités arrondies au mètre) : salle -> mairie -> départ
    de l'axe modélisé (PK -150)."""
    import networkx as nx
    G = nx.Graph()
    tr = json.loads((DR / "troncon_de_route.geojson").read_text(encoding="utf-8"))["features"]
    geoms = {}
    for f in tr:
        p = f["properties"]
        if p.get("nature") in ("Sentier", "Escalier", "Bac ou liaison maritime") or p.get("position_par_rapport_au_sol") not in (0, "0", None):
            continue
        g = l93(shape(f["geometry"]))
        for part in (g.geoms if g.geom_type == "MultiLineString" else [g]):
            c = np.asarray(part.coords)[:, :2]
            a, b = tuple(np.round(c[0])), tuple(np.round(c[-1]))
            k = (a, b)
            # la D3 est préférée (itinéraire du public et des concurrents vers le Plan de Masse) : autres voies x 3
            G.add_edge(a, b, weight=part.length * (1.0 if p.get("cpx_numero") == "D3" else 3.0), key=k)
            geoms[frozenset((a, b))] = (LineString(c), p)
    nodes = np.array(list(G.nodes))

    def proche(x, y):
        return tuple(nodes[np.argmin(((nodes - (x, y)) ** 2).sum(1))])
    with open(OUT / "chaussee_precise.csv", encoding="utf-8") as fh:
        r0 = next(csv.DictReader(fh))
    dep = (float(r0["x_axe"]), float(r0["y_axe"]))
    pts = [TO_L93.transform(*SALLE), TO_L93.transform(*MAIRIE), dep]
    chemin = []
    for a, b in zip(pts[:-1], pts[1:]):
        p = nx.shortest_path(G, proche(*a), proche(*b), weight="weight")
        chemin += p if not chemin else p[1:]
    segs, noms = [], []
    for a, b in zip(chemin[:-1], chemin[1:]):
        g, p = geoms[frozenset((a, b))]
        c = np.asarray(g.coords)
        if tuple(np.round(c[0])) != a:
            c = c[::-1]
        segs.append(c); noms.append((p.get("cpx_numero") or "", p.get("nom_collaboratif_gauche") or "", round(g.length),
                                     p.get("largeur_de_chaussee")))
    ligne = LineString(np.vstack(segs))
    return ligne, noms, [Point(p) for p in pts]


def main():
    collecte()
    ligne, noms, pts = itineraire()
    L_salle_mairie = shapely.line_locate_point(ligne, pts[1])
    bats = []
    for f in json.loads((DR / "batiment.geojson").read_text(encoding="utf-8"))["features"]:
        g = l93(shape(f["geometry"]))
        p = f["properties"]
        bats.append((g, p))
    G = np.array([b[0].centroid.coords[0] for b in bats])
    dep = np.asarray(pts[2].coords[0])
    # Option A - décor lointain : bâtiments à moins de 1,5 km du départ visibles depuis la route (champ ouvert vers
    # l'ouest et le sud-ouest), hors couloir déjà modélisé (> 150 m de l'axe). Filtre de visibilité : ligne de vue
    # sur le MNT 2 m depuis 1,2 m au-dessus de la chaussée, à 4 points du début de la montée (PK -150, 0, 150, 300).
    import rasterio
    with rasterio.open(RAW / "lointain" / "mnt_lidarhd_2m.tif") as s:
        Z = s.read(1); inv = ~s.transform; tr = s.transform

    def z(x, y):
        c, r = inv * (np.asarray(x), np.asarray(y))
        r = np.clip(np.round(r).astype(int), 0, Z.shape[0] - 1); c = np.clip(np.round(c).astype(int), 0, Z.shape[1] - 1)
        return Z[r, c]
    obs = []
    with open(OUT / "chaussee_precise.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if float(r["pk_m"]) in (-149.0, 0.0, 150.0, 300.0):
                obs.append((float(r["x_axe"]), float(r["y_axe"]), float(r["z_axe"]) + 1.2))
    axe_pts = []
    with open(OUT / "chaussee_precise.csv", encoding="utf-8") as fh:
        axe_pts = np.array([[float(r["x_axe"]), float(r["y_axe"])] for r in csv.DictReader(fh)])
    axe = LineString(axe_pts)
    d_axe = shapely.distance(axe, shapely.points(G))
    d_dep = np.hypot(*(G - dep).T)
    d_app = shapely.distance(ligne, shapely.points(G))

    def visible(i):
        g, p = bats[i]
        tx, ty = G[i]
        top = z(tx, ty) + (p.get("hauteur") or 4.0)
        for ox, oy, oz in obs:
            n = int(math.hypot(tx - ox, ty - oy) / 4) + 2
            xs, ys = np.linspace(ox, tx, n)[1:-1], np.linspace(oy, ty, n)[1:-1]
            zl = np.linspace(oz, top, n)[1:-1]
            if (z(xs, ys) <= zl + 0.5).all():
                return True
        return False
    candA = np.flatnonzero((d_dep < 1500) & (d_axe > 150))
    visA = [i for i in candA if visible(i)]
    # Option B - village parcourable : bâtiments à moins de 40 m de l'itinéraire salle -> mairie -> départ, plus ceux
    # du cœur du village (250 m autour de la mairie) pour le parc d'assistance et l'approche.
    mairie = np.asarray(pts[1].coords[0]); salle = np.asarray(pts[0].coords[0])
    candB = np.flatnonzero(((d_app < 40) | (np.hypot(*(G - mairie).T) < 250) | (np.hypot(*(G - salle).T) < 120))
                           & (d_axe > 30))
    def ecrire(nom, idx):
        feats = [{"type": "Feature", "geometry": mapping(stransform(lambda x, y, z=None: TO_WGS.transform(x, y), bats[i][0])),
                  "properties": {"cleabs": bats[i][1].get("cleabs"), "hauteur_bdtopo_m": bats[i][1].get("hauteur"),
                                 "usage": bats[i][1].get("usage_1"), "surface_m2": round(bats[i][0].area, 1)}}
                 for i in idx]
        (DO / f"batiments_{nom}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                                ensure_ascii=False), encoding="utf-8")
    ecrire("option_a_visibles_du_depart", visA)
    ecrire("option_b_village_parcourable", candB)
    (DO / "approche.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": mapping(stransform(lambda x, y, z=None: TO_WGS.transform(x, y), ligne)),
         "properties": {"nom": "salle polyvalente -> mairie -> départ (PK -150 de l'axe modélisé)",
                        "longueur_m": round(ligne.length), "dont_salle_mairie_m": round(L_salle_mairie)}}]},
        ensure_ascii=False), encoding="utf-8")
    surf = lambda idx: float(sum(bats[i][0].area for i in idx))
    # poids : volumes simples de 12_carrefours_annexes (_batiment) ≈ 60 triangles et 2 à 6 Ko de glTF par bâtiment ;
    # en Unreal, un acteur par bâtiment (ou instances de façades si on passe aux assets du jeu)
    chif = {
        "date": "2026-11-18",
        "itineraire": {"longueur_m": round(ligne.length), "salle_polyvalente_a_mairie_m": round(L_salle_mairie),
                       "mairie_au_depart_modelise_m": round(ligne.length - L_salle_mairie),
                       "troncons": [{"route": a, "nom": b, "longueur_m": c, "largeur_bdtopo_m": d} for a, b, c, d in noms]},
        "option_a_decor_lointain": {
            "batiments": len(visA), "surface_au_sol_m2": round(surf(visA)),
            "regle": "à moins de 1,5 km du départ, à plus de 150 m de l'axe, vus (ligne de vue MNT 2 m) depuis au moins un "
                     "des PK -149, 0, 150, 300",
            "route_ajoutee_m": 0, "emprise_jouable": "inchangée",
        },
        "option_b_village_parcourable": {
            "batiments": int(len(candB)), "surface_au_sol_m2": round(surf(candB)),
            "regle": "à moins de 40 m de l'itinéraire, ou à moins de 250 m de la mairie, ou de 120 m de la salle polyvalente",
            "route_ajoutee_m": round(ligne.length), "emprise_jouable": "étendue vers le village (à décider)",
        },
    }
    (DO / "chiffrage.json").write_text(json.dumps(chif, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in chif.items() if k != "itineraire"}, ensure_ascii=False, indent=1))
    print("itinéraire", chif["itineraire"]["longueur_m"], "m ;", [(a, b, c) for a, b, c, d in noms][:20])
    figure(bats, visA, candB, ligne, pts, axe_pts)


def figure(bats, visA, candB, ligne, pts, axe_pts):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MP
    fig, ax = plt.subplots(figsize=(13, 11))
    tr = json.loads((DR / "troncon_de_route.geojson").read_text(encoding="utf-8"))["features"]
    for f in tr:
        g = l93(shape(f["geometry"]))
        for part in (g.geoms if g.geom_type == "MultiLineString" else [g]):
            c = np.asarray(part.coords); ax.plot(c[:, 0], c[:, 1], color="0.75", lw=0.6, zorder=1)
    A, B = set(visA), set(candB)
    for i, (g, p) in enumerate(bats):
        for poly in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
            col = "#c0392b" if i in B else ("#e67e22" if i in A else "0.6")
            ax.add_patch(MP(np.asarray(poly.exterior.coords)[:, :2], closed=True, fc=col, ec="none", zorder=2))
    c = np.asarray(ligne.coords); ax.plot(c[:, 0], c[:, 1], color="#2471a3", lw=2.5, zorder=3,
                                          label=f"approche salle polyvalente -> mairie -> départ ({ligne.length:.0f} m)")
    ax.plot(axe_pts[:, 0], axe_pts[:, 1], color="k", lw=2.5, zorder=3, label="route modélisée (PK -150 -> 3768)")
    for p, nom in zip(pts, ("salle polyvalente (OSM)", "mairie (BD TOPO)", "début de l'axe modélisé (PK -150)")):
        ax.plot(*p.coords[0], "o", ms=9, mfc="w", mec="k", zorder=4)
        ax.annotate(nom, p.coords[0], xytext=(8, 8), textcoords="offset points", fontsize=9, zorder=5,
                    bbox=dict(fc="w", ec="0.5", alpha=0.85))
    ax.plot([], [], "s", color="#c0392b", label=f"option B : bâtiments du village parcourable ({len(B)})")
    ax.plot([], [], "s", color="#e67e22", label=f"option A : bâtiments vus depuis le départ ({len(A)})")
    ax.set_xlim(912900, 916000); ax.set_ylim(6237700, 6240400)
    ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.legend(loc="upper left", fontsize=9)
    ax.set_title("Village de Ceyreste : extension possible de la carte (BD TOPO, OSM) - à décider, rien n'est construit")
    fig.tight_layout(); fig.savefig(DF / "village_ceyreste.png", dpi=110); plt.close(fig)


if __name__ == "__main__":
    main()
