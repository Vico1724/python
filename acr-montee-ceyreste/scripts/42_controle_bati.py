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
import facades as FA  # noqa: E402


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
        # sommets du bâtiment : les plus proches de lui ET dans son emprise élargie du débord de toit (0,45 m), hors de
        # l'emprise d'un autre bâtiment (sixième passe : la tolérance de 1,8 m prenait le toit du voisin pour celui
        # d'une annexe accolée : 257167974, 257168051, 257172626)
        a_lui = (proprio == cles_bord.index(cle)) & (dist_p < 0.45) if cle in cles_bord else np.zeros(len(V), bool)
        autres = [E[c] for c in cles_bord if c != cle and E[c].distance(P) < 3.0]
        for Q in autres:
            a_lui &= ~shapely.contains_xy(Q.buffer(-0.05), V[:, 0], V[:, 1])
        toit = a_lui & (np.char.find(Mv.astype(str), "tuile") >= 0)
        # le débord du toit d'un voisin accolé passe au-dessus de l'annexe : pour le faîtage, on écarte les sommets de
        # toit à moins de 0,45 m d'un autre bâtiment
        propre = f"bati_bord_tuile_{FA.srgb_hex(FA.rgb_releve(R['toit']))}" if R.get("toit") else None
        toit_propre = (Mv == propre) & shapely.contains_xy(P.buffer(0.45), V[:, 0], V[:, 1]) if propre else np.zeros(len(V), bool)
        if toit_propre.any():                    # la tuile du bâtiment (teinte relevée, 31_bati.py) : sans ambiguïté
            toit = toit_propre
        else:
            for Q in autres:
                toit &= ~shapely.contains_xy(Q.buffer(0.45), V[:, 0], V[:, 1])
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
        # murs : faces verticales sur le contour (à 0,3 m au plus), hors éléments posés devant (auvents, bancs, coffrets)
        mur = a_lui & (np.abs(N[:, 2]) < 0.3) & (dist_p < 0.3) & (V[:, 2] < zt(V[:, 0], V[:, 1]) + 1.5)
        aire_mod = float(shapely.convex_hull(shapely.multipoints(V[mur, :2])).area) if mur.sum() > 3 else float("nan")
        Gl = np.column_stack([np.meshgrid(np.arange(x0 - 1.5, x1 + 1.5, 0.5), np.arange(y0 - 1.5, y1 + 1.5, 0.5))[k].ravel() for k in (0, 1)])
        Gl = Gl[shapely.contains_xy(P.buffer(1.5), Gl[:, 0], Gl[:, 1])]
        aire_lid = float(((zs(Gl[:, 0], Gl[:, 1]) - zt(Gl[:, 0], Gl[:, 1])) > 2.0).sum() * 0.25)
        # assise (refaite à la sixième passe) : tous les 0,5 m du contour BD TOPO, le plus bas des pieds de mur du
        # bâtiment (arête basse de chaque triangle de mur) à moins de 0,35 m de ce point, contre le MNT au même point. Un étage posé sur un corps bas ne compte
        # pas : seul le plus bas des murs au droit du point est retenu. Flottant : plus de 10 cm au-dessus du MNT ;
        # sans mur : point du contour où aucun mur ne descend à moins de 1,5 m du MNT (mur absent ou très haut).
        # murs seuls : les tableaux d'ouverture (verre, menuiserie, porte), les rives de toit et les éléments ne descendent
        # pas au sol et faisaient croire à un pied flottant
        est_mur = np.array([str(m).startswith(tuple(f"bati_bord_{k}" for k in ("enduit", "soubassement", "pierre", "bardage", "beton", "tole"))) for m in Mv])
        Vm = np.flatnonzero(a_lui & (np.abs(N[:, 2]) < 0.3) & est_mur)
        flott, enf, gap, sans_mur, tres_haut = 0, 0, 0.0, 0, 0
        # arêtes basses des triangles de mur (les deux sommets au plus bas du triangle) : un segment horizontal par mur
        tw = T[np.isin(T[:, 0], Vm) & np.isin(T[:, 1], Vm) & np.isin(T[:, 2], Vm)]
        segs, zseg = [], []
        for t3 in tw:
            z3 = V[t3, 2]
            bas = t3[z3 <= z3.min() + 0.05]
            if len(bas) >= 2 and np.hypot(*(V[bas[0], :2] - V[bas[1], :2])) > 0.05:
                segs.append(shapely.LineString(V[bas[:2], :2])); zseg.append(float(z3.min()))
        # baies et portes (vitrage, menuiserie) : sous elles, pas de mur au sol, ce n'est pas un pied flottant
        est_ouv = np.array([str(m).startswith(tuple(f"bati_bord_{k}" for k in ("verre", "menuiserie", "porte", "garage"))) for m in Mv])
        To = T[np.isin(T[:, 0], np.flatnonzero(a_lui & est_ouv))]
        ouv = [shapely.LineString(V[t3[:2], :2]) for t3 in To if np.hypot(*(V[t3[0], :2] - V[t3[1], :2])) > 0.05]
        ouv += [shapely.LineString(V[t3[1:], :2]) for t3 in To if np.hypot(*(V[t3[1], :2] - V[t3[2], :2])) > 0.05]
        arbre_o = shapely.STRtree(ouv) if ouv else None
        n_ouv = 0
        if segs:
            arbre_m = shapely.STRtree(segs); zseg = np.array(zseg)
            for q in C:
                if arbre_o is not None and len(arbre_o.query(shapely.Point(q).buffer(0.45))):
                    n_ouv += 1; continue
                kk = arbre_m.query(shapely.Point(q).buffer(0.35))
                if not len(kk):
                    sans_mur += 1; continue
                d = float(zseg[kk].min() - zt(q[0], q[1])[0])
                if d > 1.5:
                    tres_haut += 1; gap = max(gap, d); continue
                flott += d > 0.10; enf += d < -1.0; gap = max(gap, d)
        nret = int((retourne & a_lui[T[:, 0]]).sum())
        ecart_h = haut_mod - (haut_lid if lidar_ok else (max([v["egout_z"] for v in vols]) + 1.5 if vols else haut_lid))
        etat = []
        if lidar_ok and abs(haut_mod - haut_lid) > 1.0:
            etat.append(f"faîtage {haut_mod - haut_lid:+.1f} m / LiDAR")
        if lidar_ok and abs(egout_mod - egout_lid) > 1.0 and not vols:
            etat.append(f"égout {egout_mod - egout_lid:+.1f} m / LiDAR")
        # comparé à l'enveloppe convexe de l'emprise BD TOPO (sixième passe : l'enveloppe des murs d'une maison en L
        # était comparée à l'aire du L, d'où les « emprises gonflées » du PK -149)
        aire_cvx = float(P.convex_hull.area)
        if aire_mod == aire_mod and aire_mod > 1.10 * aire_cvx + 2:
            etat.append(f"emprise {aire_mod / aire_cvx:.2f} x BD TOPO (enveloppes convexes)")
        if tres_haut:
            etat.append(f"pied à plus de 1,5 m au-dessus du MNT en {tres_haut} points")
        if flott:
            etat.append(f"pied au-dessus du MNT en {flott} points sur {len(C)} (jusqu'à {gap:.2f} m)")
        if nret:
            etat.append(f"{nret} faces retournées")
        lignes.append({"cleabs": cle, "pk_m": b["pk_m"], "cote": b["cote"], "lidar_valide": lidar_ok,
                       "faitage_modele_m": round(haut_mod, 2), "faitage_lidar_m": round(haut_lid, 2),
                       "egout_modele_m": round(egout_mod, 2), "egout_lidar_m": round(egout_lid, 2),
                       "aire_bdtopo_m2": round(P.area, 1), "aire_bdtopo_convexe_m2": round(float(P.convex_hull.area), 1), "aire_murs_modele_m2": round(aire_mod, 1),
                       "aire_haute_lidar_max_m2": round(aire_lid, 1), "pied_flottant": int(flott), "pied_enterre_1m": int(enf), "pied_flottant_max_m": round(gap, 2),
                       "contour_sans_mur_au_sol": int(sans_mur), "pied_a_plus_de_1_5_m": int(tres_haut), "points_sous_une_ouverture": int(n_ouv), "points_contour": len(C),
                       "faces_retournees": nret, "ecarts": etat,
                       "etat": ("conforme" if not etat else "écart") if lidar_ok else ("non vérifiable au LiDAR (" + R.get("lidar", "") + ")" if not etat else "écart")})
    (OUT / "controle_bati.json").write_text(json.dumps({"note": __doc__.split("Sortie")[0].strip(), "batiments": lignes},
                                                       ensure_ascii=False, indent=1), encoding="utf-8")
    print("| bâtiment | PK | faîtage modèle / LiDAR (m) | égout modèle / LiDAR (m) | enveloppe des murs / de la BD TOPO (m²) | état |")
    print("|---|---|---|---|---|---|")
    for x in lignes:
        if "faitage_modele_m" not in x:
            print(f"| {x['cleabs'][-9:]} | {x['pk_m']:.0f} {x['cote'][0].upper()} | | | | {x['etat']} |"); continue
        print(f"| {x['cleabs'][-9:]} | {x['pk_m']:.0f} {x['cote'][0].upper()} | {x['faitage_modele_m']:.1f} / {x['faitage_lidar_m']:.1f} | "
              f"{x['egout_modele_m']:.1f} / {x['egout_lidar_m']:.1f} | {x['aire_murs_modele_m2']:.0f} / {x['aire_bdtopo_convexe_m2']:.0f} | "
              f"{x['etat']}{' : ' + ' ; '.join(x['ecarts']) if x['ecarts'] else ''} |")


if __name__ == "__main__":
    main()
