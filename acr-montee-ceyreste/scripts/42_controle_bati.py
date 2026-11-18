"""Contrôle chiffré des bâtiments de premier plan (cinquième passe, 19/11/2026).

Demande de l'utilisateur (transmise par le coordinateur, mots exacts) : « il y a encore des maisons buggées, des trucs
pas très bien modélisés, pas très bien intégrés […] des maisons un peu plus grandes que la normale peut-être par
moment ». Pour chacun des 30 bâtiments de premier plan (data/processed/visibilite.json), on mesure sur le maillage
posé (modele/bati_bord.glb, 31_bati.py) :
  - faîtage : point le plus haut du maillage au-dessus du pied (MNT le plus bas du contour), contre le LiDAR (MNS -
    MNT, 95e centile dans l'emprise réduite de 0,5 m) quand le relevé ne le déclare pas invalide (bâtiment plus récent
    que le LiDAR, ou couvert d'arbres) ; sinon contre la hauteur relevée sur photo (relevé de façades) ;
  - égout : celui du relevé (ou de 31) contre le MNS médian sur une bande de 0,4 à 1,2 m à l'intérieur du contour ;
  - emprise : aire du contour des murs du maillage (sommets entre 0,3 et 1,5 m au-dessus du pied) contre l'emprise
    BD TOPO, et contre l'emprise « haute » du LiDAR (MNS - MNT > 2 m dans l'emprise élargie de 1,5 m : majorant, les
    arbres y entrent) ;
  - assise : sur le contour, pied des murs du maillage contre le MNT (flottant si au-dessus de plus de 5 cm, enterré
    trop profond si plus de 1 m dessous) ;
  - faces : triangles dont l'ordre des sommets contredit la normale enregistrée (faces retournées).
Sortie : data/processed/controle_bati.json, et le tableau en Markdown sur la sortie standard.
Usage : python scripts/42_controle_bati.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import shapely

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from acr_geo import OUT, REF, ROOT  # noqa: E402


def _charger(nom, f):
    s = importlib.util.spec_from_file_location(nom, ICI / f)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def main():
    m31 = _charger("m31", "31_bati.py")
    m11 = _charger("m11", "11_route_ouvrages.py")
    rel = m31.Relief()
    zt = lambda x, y: rel.z(np.atleast_1d(x), np.atleast_1d(y))                       # noqa: E731
    zs = lambda x, y: rel._z(rel.mns, np.atleast_1d(x), np.atleast_1d(y))             # noqa: E731
    ref = json.loads((ROOT / "modele" / "repere.json").read_text(encoding="utf-8"))
    V, N, T, Mv, base = [], [], [], [], 0
    for nom, p, n, _, t in m11.lire_glb(ROOT / "modele" / "bati_bord.glb"):
        p = p.astype(np.float64)
        V.append(np.column_stack([p[:, 0] + ref["x0"], ref["y0"] - p[:, 2], p[:, 1] + ref["z0"]]))
        N.append(np.column_stack([n[:, 0], -n[:, 2], n[:, 1]])); T.append(t + base); base += len(p)
        Mv += [nom] * len(p)                    # nom du maillage : bati_bord_<matière> (31_bati.py : un par matière)
    V, N, T, Mv = np.vstack(V), np.vstack(N), np.vstack(T), np.array(Mv)
    geo = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    retourne = (geo * N[T].sum(1)).sum(1) < 0
    cen = V[T].mean(1)
    pts_v = shapely.points(V[:, :2])
    E = {str(p.get("cleabs")): P for p, P in m31.lire(OUT / "couloir" / "batiment.geojson")}
    vis = json.loads((OUT / "visibilite.json").read_text(encoding="utf-8"))
    # chaque sommet appartient au bâtiment du bord de route le plus proche (les maillages sont réunis par matière)
    cles_bord = [b["cleabs"] for b in json.loads((OUT / "bati_bilan.json").read_text(encoding="utf-8"))["batiments"]
                 if b.get("groupe") == "bati_bord" and b["cleabs"] in E]
    arbre = shapely.STRtree([E[c] for c in cles_bord])
    iv, ig = arbre.query_nearest(pts_v, return_distance=False, all_matches=False)
    proprio = np.full(len(V), -1); proprio[iv] = ig
    dist_p = shapely.distance(np.array([E[c] for c in cles_bord], dtype=object)[np.maximum(proprio, 0)], pts_v)
    bb = {b["cleabs"]: b for b in json.loads((OUT / "bati_bilan.json").read_text(encoding="utf-8"))["batiments"]}
    lignes = []
    for b in sorted([b for b in vis["batiments"] if b["niveau"] == "premier_plan"], key=lambda b: b["pk_m"]):
        cle = b["cleabs"]; P = E[cle]; bi = bb.get(cle, {})
        fr = REF / "facades" / f"{cle}.json"
        R = json.loads(fr.read_text(encoding="utf-8")) if fr.exists() else {}
        lidar_ok = "invalide" not in R.get("lidar", "").lower() and "pris sur" not in R.get("lidar", "")
        C = np.asarray(P.exterior.segmentize(0.5).coords)[:-1]
        zc = zt(C[:, 0], C[:, 1]); z0 = float(zc.min())
        a_lui = (proprio == cles_bord.index(cle)) & (dist_p < 1.8) if cle in cles_bord else np.zeros(len(V), bool)
        toit = a_lui & (np.char.find(Mv.astype(str), "tuile") >= 0)
        dans = a_lui
        if not dans.any():
            lignes.append({"cleabs": cle, "pk_m": b["pk_m"], "cote": b["cote"], "etat": "absent du maillage"}); continue
        haut_mod = float(V[toit if toit.any() else dans, 2].max() - z0)        # toit seul (sans les cheminées)
        # LiDAR
        x0, y0, x1, y1 = P.bounds
        gx, gy = np.meshgrid(np.arange(x0, x1, 0.5), np.arange(y0, y1, 0.5))
        G = np.column_stack([gx.ravel(), gy.ravel()])
        Pi = P.buffer(-0.5)
        Gi = G[shapely.contains_xy(Pi, G[:, 0], G[:, 1])] if not Pi.is_empty else G[shapely.contains_xy(P, G[:, 0], G[:, 1])]
        haut_lid = float(np.percentile(zs(Gi[:, 0], Gi[:, 1]), 95) - z0) if len(Gi) else float("nan")
        anneau = P.buffer(-0.4).difference(P.buffer(-1.2))
        Ga = G[shapely.contains_xy(anneau, G[:, 0], G[:, 1])] if not anneau.is_empty else Gi
        egout_lid = float(np.median(zs(Ga[:, 0], Ga[:, 1])) - z0) if len(Ga) else float("nan")
        vols = R.get("volumes", [])
        egout_mod = max([v["egout_z"] for v in vols]) if vols else float(bi.get("egout_m", np.nan)) + float(bi.get("z_terrain_m", z0)) - z0
        # emprise
        mur = a_lui & (np.abs(N[:, 2]) < 0.3) & (V[:, 2] < z0 + 1.0)
        aire_mod = float(shapely.convex_hull(shapely.multipoints(V[mur, :2])).area) if mur.sum() > 3 else float("nan")
        Gl = np.column_stack([np.meshgrid(np.arange(x0 - 1.5, x1 + 1.5, 0.5), np.arange(y0 - 1.5, y1 + 1.5, 0.5))[k].ravel() for k in (0, 1)])
        Gl = Gl[shapely.contains_xy(P.buffer(1.5), Gl[:, 0], Gl[:, 1])]
        aire_lid = float(((zs(Gl[:, 0], Gl[:, 1]) - zt(Gl[:, 0], Gl[:, 1])) > 2.0).sum() * 0.25)
        # assise : pied des murs sur le contour
        # assise : bas de chaque grande face verticale du bâtiment (plus de 2 m de haut) contre le MNT sous ce sommet
        flott, enf, gap = 0, 0, 0.0
        tv = T[a_lui[T[:, 0]]]
        if len(tv):
            hz = V[tv, 2]
            nz = np.abs(N[tv[:, 0], 2])
            grands = (nz < 0.3) & (hz.max(1) - hz.min(1) > 2.0)
            for t3 in tv[grands]:
                k = t3[np.argmin(V[t3, 2])]
                d = float(V[k, 2] - zt(V[k, 0], V[k, 1])[0])
                flott += d > 0.05; enf += d < -1.0; gap = max(gap, d)
        nret = int((retourne & a_lui[T[:, 0]]).sum())
        ecart_h = haut_mod - (haut_lid if lidar_ok else (max([v["egout_z"] for v in vols]) + 1.5 if vols else haut_lid))
        etat = []
        if lidar_ok and abs(haut_mod - haut_lid) > 1.0:
            etat.append(f"faîtage {haut_mod - haut_lid:+.1f} m / LiDAR")
        if lidar_ok and abs(egout_mod - egout_lid) > 1.0 and not vols:
            etat.append(f"égout {egout_mod - egout_lid:+.1f} m / LiDAR")
        if aire_mod == aire_mod and aire_mod > 1.15 * P.area + 2:
            etat.append(f"emprise {aire_mod / P.area:.2f} x BD TOPO")
        if flott:
            etat.append(f"pied au-dessus du MNT en {flott} points (jusqu'à {gap:.2f} m)")
        if nret:
            etat.append(f"{nret} faces retournées")
        lignes.append({"cleabs": cle, "pk_m": b["pk_m"], "cote": b["cote"], "lidar_valide": lidar_ok,
                       "faitage_modele_m": round(haut_mod, 2), "faitage_lidar_m": round(haut_lid, 2),
                       "egout_modele_m": round(egout_mod, 2), "egout_lidar_m": round(egout_lid, 2),
                       "aire_bdtopo_m2": round(P.area, 1), "aire_murs_modele_m2": round(aire_mod, 1),
                       "aire_haute_lidar_max_m2": round(aire_lid, 1), "pied_flottant": int(flott), "pied_enterre_1m": int(enf), "pied_flottant_max_m": round(gap, 2),
                       "faces_retournees": nret, "ecarts": etat,
                       "etat": ("conforme" if not etat else "écart") if lidar_ok else ("non vérifiable au LiDAR (" + R.get("lidar", "") + ")" if not etat else "écart")})
    (OUT / "controle_bati.json").write_text(json.dumps({"note": __doc__.split("Sortie")[0].strip(), "batiments": lignes},
                                                       ensure_ascii=False, indent=1), encoding="utf-8")
    print("| bâtiment | PK | faîtage modèle / LiDAR (m) | égout modèle / LiDAR (m) | emprise murs / BD TOPO (m²) | état |")
    print("|---|---|---|---|---|---|")
    for x in lignes:
        if "faitage_modele_m" not in x:
            print(f"| {x['cleabs'][-9:]} | {x['pk_m']:.0f} {x['cote'][0].upper()} | | | | {x['etat']} |"); continue
        print(f"| {x['cleabs'][-9:]} | {x['pk_m']:.0f} {x['cote'][0].upper()} | {x['faitage_modele_m']:.1f} / {x['faitage_lidar_m']:.1f} | "
              f"{x['egout_modele_m']:.1f} / {x['egout_lidar_m']:.1f} | {x['aire_murs_modele_m2']:.0f} / {x['aire_bdtopo_m2']:.0f} | "
              f"{x['etat']}{' : ' + ' ; '.join(x['ecarts']) if x['ecarts'] else ''} |")


if __name__ == "__main__":
    main()
