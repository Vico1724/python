"""Étape 12 - Carrefours : voies non empruntées par la spéciale, terre-plein, parapets, balisage.

Au carrefour du Lion d'Or, la chaussée de la spéciale (07, zone 2 des corrections) suit la
branche de gauche de la patte d'oie ; son bord droit y est une ligne de fermeture qui barre la
branche de droite (D1 vers le nord) puis longe le terre-plein. Ce script modélise ce qui est
au-delà : l'enrobé de la branche de droite et de l'amorce de la D1 nord (avec son ponceau),
le terre-plein en terre, les parapets (pierre, ponceau), les panneaux et la rubalise de
fermeture. Le plan (polygones, polylignes, hauteurs, sources) est dans le JSON : il a été
établi sur le nuage de points LiDAR HD classé de l'IGN, le MNT, Street View et la vidéo.

Entrées : data/reference/carrefours_annexes.json, data/processed/chaussee_precise.csv,
          data/raw/mnt_lidarhd_50cm.tif, modele/repere.json, modele/ouvrages_collision.glb (parapets
          de l'étape 11, pour écarter le balisage)
Méthode : surfaces = polygones du plan moins la chaussée de la spéciale (ce qui recolle leur bord
          exactement sur la ligne de fermeture), triangulées (contour tous les 0,5 m, grille de 1 m).
          Altitudes : MNT +3 cm (au-dessus du terrain de 08, non troué ici), recalé sur 2 m vers
          l'altitude du bord de chaussée le long des fermetures (raccord sans marche) ; sur le
          ponceau, tablier interpolé entre ses deux extrémités (le MNT y est le fond du ruisseau).
Sorties : data/processed/annexes_revetues.geojson (WGS84), data/processed/balisage.csv,
          modele/annexes.glb, annexes_collision.glb (enrobé / terre / pierre), balisage.glb,
          balisage_collision.glb, modele/apercu/{annexes,balisage}.glb,
          figures/phase4/carrefour_plan.png, carrefour_plongeante.png, carrefour_conducteur_d3d.png
"""
import csv
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import shapely
import shapely.ops
from PIL import Image
from scipy.spatial import Delaunay, cKDTree
from shapely.geometry import LineString, Point, Polygon, mapping

from acr_geo import FIG, OUT, REF, ROOT, TO_WGS, write_geojson

_spec = importlib.util.spec_from_file_location("route_ouvrages", Path(__file__).with_name("11_route_ouvrages.py"))
m11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m11)
m08 = m11.m08

MOD = ROOT / "modele"
FIG4 = FIG / "phase4"
RACCORD = 2.0        # m : recalage du MNT sur l'altitude du bord de chaussée
SURELEV = 0.03       # m : surfaces au-dessus du MNT (hors raccord) pour couvrir le terrain de 08
PAS_INT = 1.0        # m : maille intérieure des surfaces
PAS_BORD = 0.5       # m : échantillonnage des contours


# --- chaussée de la spéciale ---------------------------------------------------------------
def ruban_poly(ch, pk0, pk1):
    """Emprise exacte du ruban (union des quadrilatères gauche-axe et axe-droite de chaque maille)."""
    i = np.flatnonzero((ch["pk"] >= pk0) & (ch["pk"] <= pk1))
    quads = []
    for a, b in zip(i[:-1], i[1:]):
        for P, Q in ((ch["G"], ch["A"]), (ch["A"], ch["D"])):
            q = Polygon([P[a, :2], P[b, :2], Q[b, :2], Q[a, :2]])
            quads.append(q if q.is_valid else shapely.make_valid(q))
    return shapely.union_all(quads)


def pk_du_bord(ch, xy, cote, pk0, pk1):
    """PK de la ligne dont le bord (G ou D) est le plus proche du point (dans [pk0, pk1])."""
    E = ch["D"] if cote == "droite" else ch["G"]
    s = np.flatnonzero((ch["pk"] >= pk0) & (ch["pk"] <= pk1))
    return float(ch["pk"][s[np.argmin(np.hypot(*(E[s, :2] - np.asarray(xy)).T))]])


def bord_3d(rg, s0, s1, cote="droite", pas=0.5):
    s = m11.echant(s0, s1, pas)
    E, n = rg.bord(s, cote)
    return s, E, n


# --- altitudes ---------------------------------------------------------------------------------
def fabrique_altitude(mnt, fermetures, ponceau):
    """z(XY) : MNT + SURELEV, raccordé sur RACCORD m (exactement sur la ligne) à l'altitude du bord
    de chaussée le long des fermetures ; tablier du ponceau interpolé le long de son axe."""
    lignes = [(LineString(F[:, :2]), np.concatenate([[0], np.cumsum(np.hypot(*np.diff(F[:, :2], axis=0).T))]), F[:, 2])
              for F in fermetures]
    if ponceau:
        a, b = (np.asarray(p, float) for p in ponceau["axe"])
        za, zb = mnt.z(np.array([a[0], b[0]]), np.array([a[1], b[1]]))
        poly_p = Polygon(ponceau["polygone"]).buffer(0.05)

    def z(XY):
        XY = np.asarray(XY, float)
        zm = mnt.z(XY[:, 0], XY[:, 1])
        if ponceau:                                         # tablier : le MNT y est le fond du ruisseau
            dans = shapely.contains_xy(poly_p, XY[:, 0], XY[:, 1])
            t = np.clip(((XY - a) @ (b - a)) / ((b - a) @ (b - a)), 0, 1)
            zm = np.where(dans, za + t * (zb - za) - SURELEV, zm)
        best_d = np.full(len(XY), np.inf)
        dz = np.zeros(len(XY))
        pts = shapely.points(XY)
        for L, cum, ze in lignes:
            d = shapely.distance(L, pts)
            s = shapely.line_locate_point(L, pts)
            q = shapely.line_interpolate_point(L, s)
            dze = np.interp(s, cum, ze) - mnt.z(shapely.get_x(q), shapely.get_y(q))
            better = d < best_d
            best_d[better], dz[better] = d[better], dze[better]
        w = np.clip(1 - best_d / RACCORD, 0, 1)
        return zm + w * dz + SURELEV * np.clip(best_d / 0.5, 0, 1)
    return z


# --- surfaces ----------------------------------------------------------------------------------
def aire_plan(XY, tri):
    u, v = XY[tri[:, 1]] - XY[tri[:, 0]], XY[tri[:, 2]] - XY[tri[:, 0]]
    return np.abs(u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]) / 2


class SolTerrain:
    """Triangles réels du terrain de 08 (modele/terrain.glb) autour d'un carrefour. Les surfaces
    sont découpées dans ces triangles et relevées de SURELEV : le terrain ne peut pas les percer
    (une nouvelle triangulation de Delaunay ne suffirait pas : sur la grille de 1 m, les deux
    diagonales d'une maille sont également valides et 08 a choisi les siennes)."""

    def __init__(self, ref, bornes):
        x0, y0, x1, y1 = bornes
        V, T, base = [], [], 0
        for _, p, _, _, t in m11.lire_glb(MOD / "terrain.glb"):
            p = p.astype(np.float64)
            q = np.column_stack([p[:, 0] + ref["x0"], ref["y0"] - p[:, 2], p[:, 1] + ref["z0"]])
            c = q[t].mean(1)
            sel = (c[:, 0] > x0) & (c[:, 0] < x1) & (c[:, 1] > y0) & (c[:, 1] < y1)
            V.append(q)
            T.append(t[sel] + base)
            base += len(q)
        self.V, self.T = np.vstack(V), np.vstack(T)
        self.tris = shapely.polygons(self.V[self.T][:, :, :2])
        self.arbre = shapely.STRtree(self.tris)

    def z(self, XY):
        """Altitude du terrain sous chaque point (la plus haute si plusieurs triangles)."""
        XY = np.asarray(XY, float)
        out = np.full(len(XY), -np.inf)
        ip, it = self.arbre.query(shapely.points(XY), predicate="intersects")
        a, b, c = (self.V[self.T[it, k]] for k in range(3))
        det = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])
        u = ((XY[ip, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (XY[ip, 1] - a[:, 1])) / det
        v = ((b[:, 0] - a[:, 0]) * (XY[ip, 1] - a[:, 1]) - (XY[ip, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])) / det
        zz = a[:, 2] + u * (b[:, 2] - a[:, 2]) + v * (c[:, 2] - a[:, 2])
        np.maximum.at(out, ip, zz)
        return out


def maillage_sur_terrain(P, sol, z_de, ref, mat, name, uv_s, lignes, tablier=None):
    """Surface calquée sur le terrain de 08 : ses triangles sont découpés par le polygone et relevés
    de SURELEV (rampe de 0 à SURELEV sur 0,5 m depuis les lignes de fermeture, où l'altitude est
    celle du bord de chaussée). Le terrain ne peut donc pas percer la surface. Sur le tablier du
    ponceau (où le terrain est le lit du ruisseau), triangulation propre à l'altitude du tablier."""
    parts = []
    R = P.difference(tablier) if tablier is not None else P
    T = sol.T
    tris = sol.tris
    cand = np.flatnonzero(shapely.intersects(tris, R))
    XY, Z, F = [], [], []
    for k in cand:
        g = shapely.intersection(tris[k], R)
        if g.is_empty or g.area < 1e-6:
            continue
        a, b, c = sol.V[T[k]]
        M = np.array([[b[0] - a[0], c[0] - a[0]], [b[1] - a[1], c[1] - a[1]]])
        Minv = np.linalg.inv(M)
        for pc in shapely.get_parts(shapely.constrained_delaunay_triangles(g) if g.geom_type != "Polygon" or len(g.exterior.coords) > 4 or g.interiors
                                    else shapely.GeometryCollection([g])):
            q = np.asarray(pc.exterior.coords)[:3] if pc.geom_type == "Polygon" else None
            if q is None or len(q) < 3:
                continue
            w = (Minv @ (q - a[:2]).T).T
            zq = a[2] + w[:, 0] * (b[2] - a[2]) + w[:, 1] * (c[2] - a[2])
            F.append(np.arange(3) + len(XY) * 0 + sum(len(x) for x in XY))
            XY.append(q)
            Z.append(zq)
    XY, Z = np.vstack(XY), np.concatenate(Z)
    tri = np.vstack(F)
    pts = shapely.points(XY)
    d = np.full(len(XY), np.inf)
    for L in lignes:
        d = np.minimum(d, shapely.distance(L, pts))
    Z = np.where(d < 0.01, z_de(XY), Z + SURELEV * np.clip(d / 0.5, 0, 1))
    # fusion des sommets confondus (mêmes x, y au 0,1 mm)
    key = np.round(XY, 4)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    zf = np.full(len(first), -np.inf)
    np.maximum.at(zf, inv, Z)
    XY, Z, tri = XY[first], zf, inv[tri]
    tri = tri[aire_plan(XY, tri) > 1e-3]                 # pas de triangles dégénérés (normales indéfinies)
    pos = m08.to_gltf(np.column_stack([XY, Z]), ref).astype(np.float64)
    tri = m11.oriente(pos, tri, np.array([0.0, 1.0, 0.0])).astype(np.uint32)
    parts.append({"pos": pos.astype(np.float32), "nrm": m08.normales(pos, tri), "uv": (XY / uv_s).astype(np.float32), "idx": tri})
    aire = float(aire_plan(XY, tri).sum())
    if tablier is not None and not P.intersection(tablier).is_empty:
        sd, a2 = maillage_surface(P.intersection(tablier), lambda XY: np.maximum(z_de(XY), sol.z(XY) + SURELEV), ref, mat, name, uv_s)
        parts.append(sd)
        aire += a2
    out = m11.fusion(parts, name, mat)
    return out, aire


def maillage_surface(P, z_de, ref, mat, name, uv_s=m11.S_ENROBE):
    """Triangulation propre (contour tous les 0,5 m, grille de 1 m), altitude z_de ; normales vers le haut."""
    bords = []
    for g in getattr(P, "geoms", [P]):
        for ring in [g.exterior, *g.interiors]:
            bords.append(np.asarray(ring.segmentize(PAS_BORD).coords)[:-1, :2])
    B = np.vstack(bords)
    x0, y0, x1, y1 = P.bounds
    gx, gy = np.meshgrid(np.arange(np.floor(x0), x1, PAS_INT), np.arange(np.floor(y0), y1, PAS_INT))
    G = np.column_stack([gx.ravel(), gy.ravel()])
    pts = shapely.points(G)
    G = G[shapely.contains(P, pts) & (shapely.distance(P.boundary, pts) > 0.2)]
    XY = np.unique(np.round(np.vstack([B, G]), 4), axis=0)
    tri = Delaunay(XY - XY.mean(0)).simplices        # centré : en Lambert-93 brut, qhull perd des points
    cen = XY[tri].mean(1)
    Pp = P.buffer(1e-6)
    shapely.prepare(Pp)
    tri = tri[shapely.contains_xy(Pp, cen[:, 0], cen[:, 1]) & (aire_plan(XY, tri) > 1e-4)]
    used, inv = np.unique(tri, return_inverse=True)
    XY, tri = XY[used], inv.reshape(-1, 3)
    pos = m08.to_gltf(np.column_stack([XY, z_de(XY)]), ref).astype(np.float64)
    tri = m11.oriente(pos, tri, np.array([0.0, 1.0, 0.0])).astype(np.uint32)
    uv = (XY - np.floor(XY.min(0))) / uv_s
    return {"name": name, "pos": pos.astype(np.float32), "nrm": m08.normales(pos, tri), "uv": uv.astype(np.float32),
            "idx": tri, "mat": mat}, float(aire_plan(XY, tri).sum())


# --- volumes simples ---------------------------------------------------------------------------
def pave(c, axe, L, W, z0, z1, ref):
    """Pavé centré en c (x, y), long de L selon axe (unitaire 2D), large de W, de z0 à z1."""
    t = np.asarray(axe, float) / np.linalg.norm(axe)
    n = np.array([-t[1], t[0]])
    a, b = np.asarray(c) - t * L / 2, np.asarray(c) + t * L / 2
    P = np.array([a, b])
    co = lambda o, z: np.column_stack([P + o * n, np.full(2, z)])     # noqa: E731
    return m11.boite([co(-W / 2, z0), co(W / 2, z0), co(W / 2, z1), co(-W / 2, z1)], ref)


def mur(poly, sortant, h, ep, z_pied, z_bas, ref):
    """Parapet le long d'une polyligne (face intérieure), épais de ep du côté sortant (unitaire par
    sommet) ; dessus à z_pied + h, dessous à z_bas (par sommet)."""
    P = np.asarray(poly, float)
    o3 = lambda o: np.column_stack([P + sortant * o, np.zeros(len(P))])  # noqa: E731
    zp, zb = np.asarray(z_pied), np.asarray(z_bas)
    coins = [o3(0) + np.column_stack([0 * zp, 0 * zp, zb]), o3(ep) + np.column_stack([0 * zp, 0 * zp, zb]),
             o3(ep) + np.column_stack([0 * zp, 0 * zp, zp + h]), o3(0) + np.column_stack([0 * zp, 0 * zp, zp + h])]
    return m11.boite(coins, ref)


def normales_sortantes(P, surfaces):
    """Normale horizontale à la polyligne, orientée vers l'extérieur des surfaces revêtues."""
    P = np.asarray(P, float)
    tg = np.gradient(P, axis=0)
    n = np.column_stack([tg[:, 1], -tg[:, 0]]) / np.linalg.norm(tg, axis=1, keepdims=True)
    k = len(P) // 2
    test = P[k] + 0.3 * n[k]
    if surfaces.buffer(0.05).contains(Point(test)):
        n = -n
    return n


# --- balisage -------------------------------------------------------------------------------------
def balisage(cfg_b, rg, ferm_pk, obstacles, ruban, z_de, ref):
    """Piquets et rubalise le long des segments de fermeture, à decalage_bord_m au-delà du bord,
    sauf à moins de distance_min_obstacle_m d'un parapet, d'un panneau ou d'un tronc."""
    rb = cfg_b["rubalise"]
    dmin = cfg_b["distance_min_obstacle_m"]
    arbre = cKDTree(obstacles) if len(obstacles) else None
    cap = lambda t: float(np.degrees(np.arctan2(t[0], t[1])) % 360)    # noqa: E731
    lignes, meshes = [], {"piquet": [], "piquet_tete": [], "rubalise": []}
    for nom, s0, s1 in ferm_pk:
        s = m11.echant(s0, s1, 0.25)
        E, n = rg.bord(s, "droite")
        Q = E[:, :2] + n * rb["decalage_bord_m"]
        cum = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(Q, axis=0).T))])
        m_ = max(int(np.floor(cum[-1] / rb["pas_poteaux_m"])), 1)
        at = (cum[-1] - m_ * rb["pas_poteaux_m"]) / 2 + np.arange(m_ + 1) * rb["pas_poteaux_m"]
        P = np.column_stack([np.interp(at, cum, Q[:, 0]), np.interp(at, cum, Q[:, 1])])
        T = np.column_stack([np.interp(at + 0.3, cum, Q[:, 0]) - np.interp(at - 0.3, cum, Q[:, 0]),
                             np.interp(at + 0.3, cum, Q[:, 1]) - np.interp(at - 0.3, cum, Q[:, 1])])
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        ok = ~shapely.contains_xy(ruban.buffer(0.3), P[:, 0], P[:, 1])
        if arbre is not None:
            ok &= arbre.query(P)[0] > dmin
        Z = z_de(P)
        for k in np.flatnonzero(ok):
            lignes.append({"type": "piquet de rubalise", "xy": P[k], "z": Z[k], "cap": cap(T[k]), "L": 0.0,
                           "maillage": rb["maillage_jeu"], "f": nom})
            meshes["piquet"].append(pave(P[k], T[k], 0.04, 0.04, Z[k] - 0.05, Z[k] + rb["hauteur_m"], ref))
            meshes["piquet_tete"].append(pave(P[k], T[k], 0.05, 0.05, Z[k] + rb["hauteur_m"] - 0.15, Z[k] + rb["hauteur_m"] + 0.02, ref))
            if k + 1 < len(P) and ok[k + 1]:
                c_, d_ = (P[k] + P[k + 1]) / 2, P[k + 1] - P[k]
                L = float(np.linalg.norm(d_))
                zc = (Z[k] + Z[k + 1]) / 2 + rb["hauteur_m"] - 0.1
                lignes.append({"type": "rubalise", "xy": c_, "z": zc, "cap": cap(d_ / L), "L": L,
                               "maillage": rb["acteur_ruban_jeu"], "f": nom})
                meshes["rubalise"].append(pave(c_, d_, L, 0.01, zc - 0.035, zc + 0.035, ref))
    return lignes, meshes


# --- contrôles ---------------------------------------------------------------------------------------
def controle(ref, ruban, fermetures, revetu, terre, parapets_int, lignes_b, dossier):
    r = {}
    for f in ("annexes.glb", "annexes_collision.glb", "balisage.glb", "balisage_collision.glb"):
        p = dossier / f
        if not p.exists():
            continue
        ms = m11.lire_glb(p)
        pos = np.vstack([m[1] for m in ms])
        nrm = np.vstack([m[2] for m in ms])
        acc = []
        for _, pp, nn, _, t in ms:
            fn = np.cross(pp[t[:, 1]] - pp[t[:, 0]], pp[t[:, 2]] - pp[t[:, 0]])
            acc.append((fn * nn[t].sum(1)).sum(1) > 0)
        r[f] = {"taille_ko": round(p.stat().st_size / 1e3), "maillages": len(ms), "sommets": int(len(pos)),
                "triangles": int(sum(len(m[4]) for m in ms)), "nan": bool(np.isnan(pos).any() or np.isnan(nrm).any()),
                "faces_dans_le_sens_des_normales_pct": round(float(np.concatenate(acc).mean() * 100), 2),
                "bornes_min": np.round(pos.min(0), 1).tolist(), "bornes_max": np.round(pos.max(0), 1).tolist()}
        surf = [m for m in ms if m[0].startswith(("enrobe", "terre"))]
        if surf:
            up = [np.cross(pp[t[:, 1]] - pp[t[:, 0]], pp[t[:, 2]] - pp[t[:, 0]])[:, 1] > 0 for _, pp, _, _, t in surf]
            r[f]["surfaces_normales_vers_le_haut_pct"] = round(float(np.concatenate(up).mean() * 100), 2)
        if f == "annexes.glb":
            ecarts, couvert, sous = [], [], 0.0
            for nom, pp, _, _, t in surf:
                pp = pp.astype(np.float64)                 # avant d'ajouter l'origine (float32 : 6 cm à 900 km)
                XY = np.column_stack([pp[:, 0] + ref["x0"], ref["y0"] - pp[:, 2]])
                Zv = pp[:, 1] + ref["z0"]
                pts = shapely.points(XY)
                for F in fermetures:
                    L = LineString(F[:, :2])
                    cum = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(F[:, :2], axis=0).T))])
                    on = shapely.distance(L, pts) < 0.01
                    ecarts.append(Zv[on] - np.interp(shapely.line_locate_point(L, pts[on]), cum, F[:, 2]))
                sous += float(shapely.area(shapely.intersection(shapely.polygons(XY[t]), ruban.buffer(-0.01))).sum())
            for F in fermetures:                               # couverture à 0,2 m au-delà du bord
                L = LineString(F[:, :2])
                s = np.arange(0.25, L.length - 0.25, 0.5)
                q = np.array([L.interpolate(x).coords[0] for x in s])
                tg = np.gradient(q, axis=0)
                q2 = q + 0.2 * np.column_stack([tg[:, 1], -tg[:, 0]]) / np.linalg.norm(tg, axis=1, keepdims=True)
                couvert.append(shapely.contains_xy(shapely.union_all([revetu, terre]).buffer(1e-3), q2[:, 0], q2[:, 1]))
            e = np.concatenate(ecarts)
            r[f]["raccord_fermeture"] = {"sommets_sur_la_ligne": int(len(e)),
                                         "ecart_vertical_max_m": round(float(np.abs(e).max()), 4) if len(e) else None,
                                         "bord_couvert_a_0_2_m_pct": round(float(np.concatenate(couvert).mean() * 100), 1)}
            r[f]["aire_sous_la_chaussee_m2"] = round(sous, 3)
            # parapets : face intérieure contre le bord de l'enrobé
            d = [float(shapely.distance(revetu.boundary, Point(p))) for P in parapets_int for p in P]
            r[f]["parapets_face_interieure_au_bord_enrobe_max_m"] = round(max(d), 3) if d else None
    if lignes_b:
        P = np.array([b["xy"] for b in lignes_b if b["type"] != "rubalise"])
        r["balisage_distance_min_a_la_chaussee_m"] = round(float(shapely.distance(ruban, shapely.points(P)).min()), 2)
    return r


# --- plan coté ---------------------------------------------------------------------------------------
def plan_figure(c, ch, ruban, revetu, terre, parapets, panneaux, fermetures, lignes_b, chemin, fermetures_pk):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 11))
    for g in getattr(ruban, "geoms", [ruban]):
        ax.fill(*g.exterior.xy, color="#5d6066", alpha=0.85, lw=0)
    for g in getattr(revetu, "geoms", [revetu]):
        ax.fill(*g.exterior.xy, color="#9aa0a8", lw=0)
    for g in getattr(terre, "geoms", [terre]):
        ax.fill(*g.exterior.xy, color="#c9b48a", lw=0)
    if c.get("ponceau"):
        ax.fill(*Polygon(c["ponceau"]["polygone"]).exterior.xy, facecolor="none", edgecolor="#555", hatch="///", lw=0.8)
    if c.get("zone_hachuree"):
        ax.fill(*Polygon(c["zone_hachuree"]["polygone"]).exterior.xy, facecolor="white", edgecolor="white", alpha=0.8, hatch="\\\\", lw=0.5)
        zh = np.array(Polygon(c["zone_hachuree"]["polygone"]).centroid.coords[0])
        ax.annotate("zone hachurée peinte", zh, xytext=(zh[0] - 22, zh[1] - 10), fontsize=8, arrowprops=dict(arrowstyle="->"),
                    bbox=dict(boxstyle="round", fc="white", alpha=0.85))
    fo = np.array(c["fosse"]["polyligne"])
    ax.plot(fo[:, 0], fo[:, 1], color="#2b7bba", lw=2.5, ls=(0, (4, 2)))
    for (nom, P, typ) in parapets:
        ax.plot(P[:, 0], P[:, 1], color="#3b3b3b" if typ == "pierre_sombre" else "#8a6d3b", lw=4, solid_capstyle="butt")
    for F in fermetures:
        ax.plot(F[:, 0], F[:, 1], color="#d62728", lw=2)
    sel = (ch["pk"] >= c["pk"][0] - 30) & (ch["pk"] <= c["pk"][1] + 30)
    ax.plot(ch["A"][sel, 0], ch["A"][sel, 1], color="white", lw=1.2, ls="--")
    pb = np.array([b["xy"] for b in lignes_b if b["type"] != "rubalise"])
    if len(pb):
        ax.scatter(pb[:, 0], pb[:, 1], s=12, color="#d62728", edgecolor="white", lw=0.5, zorder=5)
    for nom, xy in panneaux:
        ax.scatter(*xy, marker="s", s=60, color="#1f77b4", edgecolor="white", zorder=6)
    pin = c["terre_plein"].get("pin")
    if pin:
        ax.scatter(*pin["xy"], marker="^", s=160, color="#2ca02c", edgecolor="k", zorder=6)
    # légendes en clair
    s_a, s_b = fermetures_pk[0][1], fermetures_pk[-1][2]
    txt = [("D3D (arrivée)", ch["A"][np.argmin(np.abs(ch["pk"] - s_a + 14))]),
           ("D1 vers l'ouest\n(spéciale)", ch["A"][np.argmin(np.abs(ch["pk"] - s_b + 6))]),
           ("D1 vers le nord\n(fermée)", np.array(revetu.representative_point().coords[0]) if not revetu.is_empty else None)]
    for t, xy in txt:
        if xy is not None:
            ax.annotate(t, xy[:2], fontsize=10, ha="center", color="k", bbox=dict(boxstyle="round", fc="white", alpha=0.8))
    for nom_pn, xy in panneaux[1:2]:
        ax.annotate("bloc blanc et panneaux au départ du\nparapet de pierre (la « bosse » prise\npour un îlot)", xy, xytext=(xy[0] + 4, xy[1] + 4),
                    fontsize=8, arrowprops=dict(arrowstyle="->"), bbox=dict(boxstyle="round", fc="white", alpha=0.85))
    if c.get("ponceau"):
        cp = np.array(Polygon(c["ponceau"]["polygone"]).centroid.coords[0])
        ax.annotate("ponceau", cp, xytext=(cp[0] + 9, cp[1] - 4), fontsize=8, arrowprops=dict(arrowstyle="->"),
                    bbox=dict(boxstyle="round", fc="white", alpha=0.85))
    tp = np.array(terre.representative_point().coords[0])
    ax.annotate("terre-plein", tp, fontsize=10, ha="center", bbox=dict(boxstyle="round", fc="white", alpha=0.8))
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    leg = [Patch(color="#5d6066", label="chaussée de la spéciale"), Patch(color="#9aa0a8", label="enrobé fermé (modélisé à part)"),
           Patch(color="#c9b48a", label="terre-plein (terre)"), Patch(facecolor="none", edgecolor="#555", hatch="///", label="tablier du ponceau"),
           Line2D([], [], color="#8a6d3b", lw=4, label="parapet de pierre"), Line2D([], [], color="#3b3b3b", lw=4, label="parapet sombre (ponceau)"),
           Line2D([], [], color="#2b7bba", lw=2.5, ls="--", label="ruisseau / fossé"), Line2D([], [], color="#d62728", lw=2, label="ligne de fermeture"),
           Line2D([], [], marker="o", color="w", markerfacecolor="#d62728", label="piquets de rubalise"),
           Line2D([], [], marker="s", color="w", markerfacecolor="#1f77b4", markersize=9, label="panneaux"),
           Line2D([], [], marker="^", color="w", markerfacecolor="#2ca02c", markersize=11, label="grand pin"),
           Line2D([], [], color="k", lw=1.2, ls="--", label="axe de la spéciale")]
    ax.legend(handles=leg, loc="lower left", fontsize=8, framealpha=0.9)
    b = shapely.union_all([revetu, terre]).bounds
    ax.set_xlim(b[0] - 12, b[2] + 15)
    ax.set_ylim(b[1] - 22, b[3] + 6)
    ax.set_aspect("equal")
    ax.set_facecolor("#e8efe2")
    xt = np.arange(np.ceil((b[0] - 12) / 10) * 10, b[2] + 15, 10)
    yt = np.arange(np.ceil((b[1] - 22) / 10) * 10, b[3] + 6, 10)
    ax.set_xticks(xt)
    ax.set_yticks(yt)
    ax.set_xticklabels([f"{v:.0f}" for v in xt], rotation=90, fontsize=7)
    ax.set_yticklabels([f"{v:.0f}" for v in yt], fontsize=7)
    ax.grid(alpha=0.3)
    ax.set_title(f"Carrefour du {c['nom']} - plan (Lambert-93, quadrillage de 10 m, nord en haut)", fontsize=11)
    fig.savefig(chemin, dpi=110, bbox_inches="tight")
    plt.close(fig)


# --- rendus ---------------------------------------------------------------------------------------------
def rendus(vues, fichiers, prefixe="carrefour"):
    tmp = Path(tempfile.mkdtemp())
    try:
        (tmp / "rendu.html").write_text(m11.RENDER_HTML, encoding="utf-8")
        (tmp / "rendu.js").write_text(m08.RENDER_JS, encoding="utf-8")
        for f in fichiers:
            shutil.copy(f, tmp / f.name)
        srv = subprocess.Popen([sys.executable, "-m", "http.server", "8767", "--bind", "127.0.0.1"], cwd=tmp,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(0.5)
            views, outs = [], []
            for name, eye, at, fov in vues:
                q = (f"w=1400&h=800&fov={fov}&files={','.join(f.name for f in fichiers)}"
                     f"&eye={','.join(f'{v:.2f}' for v in eye)}&at={','.join(f'{v:.2f}' for v in at)}")
                outs.append((tmp / f"{name}.png", FIG4 / f"{prefixe}_{name}.png"))
                views.append({"url": f"http://127.0.0.1:8767/rendu.html?{q}", "out": str(outs[-1][0])})
            node_path = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
            res = subprocess.run(["node", "rendu.js", json.dumps(views)], cwd=tmp, capture_output=True, text=True,
                                 timeout=900, env={**os.environ, "NODE_PATH": node_path})
        finally:
            srv.terminate()
        if res.returncode != 0:
            print("rendu WebGL impossible :", res.stderr[-500:])
            return False
        FIG4.mkdir(parents=True, exist_ok=True)
        for src, dst in outs:
            im = Image.open(src).convert("RGB")
            im.save(dst, optimize=True)
            if dst.stat().st_size > 1.4e6:
                im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(dst, optimize=True)
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --- programme principal ---------------------------------------------------------------------------------
def main():
    t0 = time.time()
    cfg = json.loads((REF / "carrefours_annexes.json").read_text(encoding="utf-8"))
    ch = m08.chaussee()
    mnt = m08.MNT()
    ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    rg = m11.Rangs(ch)
    obstacles = np.zeros((0, 2))
    if (MOD / "ouvrages_collision.glb").exists():
        pp = np.vstack([m[1] for m in m11.lire_glb(MOD / "ouvrages_collision.glb")]).astype(np.float64)
        obstacles = np.column_stack([pp[:, 0] + ref["x0"], ref["y0"] - pp[:, 2]])

    m_ann, m_coll, m_bal, m_bcoll, feats, lignes_csv, rapport = [], [], [], [], [], [], {}
    actifs = [c for c in cfg["carrefours"] if c.get("actif")]
    for c in actifs:
        nom = c["nom"]
        cle = "".join(ch_ if ch_.isalnum() else "_" for ch_ in nom.lower())
        pk0, pk1 = c["pk"]
        ruban = ruban_poly(ch, pk0 - 60, pk1 + 60)
        # fermetures : du point « de » au point « a » le long du bord droit
        ferm_pk = [(f["nom"], pk_du_bord(ch, f["de"], "droite", pk0, pk1), pk_du_bord(ch, f["a"], "droite", pk0, pk1))
                   for f in c["fermetures"]]
        fermetures = [bord_3d(rg, s0, s1)[1] for _, s0, s1 in ferm_pk]
        ponceau = c.get("ponceau")
        z_de = fabrique_altitude(mnt, fermetures, ponceau)
        # surfaces : enrobé fermé et terre-plein, moins la chaussée de la spéciale
        revetu = shapely.union_all([Polygon(s["polygone"]) for s in c.get("surfaces_revetues", [])]).difference(ruban)
        terre = Polygon(c["terre_plein"]["polygone"]).difference(ruban).difference(revetu.buffer(0.05))
        bx = shapely.union_all([revetu, terre]).buffer(5).bounds
        sol = SolTerrain(ref, bx) if (MOD / "terrain.glb").exists() else None
        lignes = [LineString(F[:, :2]) for F in fermetures]
        tab = Polygon(ponceau["polygone"]) if ponceau else None
        if sol is not None:
            s_enr, aire_enr = maillage_sur_terrain(revetu, sol, z_de, ref, "enrobe", f"enrobe_{cle}", m11.S_ENROBE, lignes, tab)
            s_ter, aire_ter = maillage_sur_terrain(terre, sol, z_de, ref, "terre", f"terre_plein_{cle}", 2.0, lignes, tab)
        else:
            s_enr, aire_enr = maillage_surface(revetu, z_de, ref, "enrobe", f"enrobe_{cle}")
            s_ter, aire_ter = maillage_surface(terre, z_de, ref, "terre", f"terre_plein_{cle}", uv_s=2.0)
        m_ann += [s_enr, s_ter]
        m_coll += [{**s_enr, "name": f"enrobe_{cle}_collision"}, {**s_ter, "name": f"terre_plein_{cle}_collision"}]
        # ponceau : dalle sous le tablier (le terrain de 08 y garde le lit du ruisseau)
        if ponceau:
            Pp = Polygon(ponceau["polygone"])
            ring = np.asarray(Pp.exterior.coords)[:-1]
            zt = z_de(ring) - 0.02
            coins = [np.column_stack([ring, zt - ponceau["epaisseur_m"]]), np.column_stack([ring, zt])]
            n_ = len(ring)
            pos = m08.to_gltf(np.vstack(coins), ref).astype(np.float64)
            i = np.arange(n_)
            j = (i + 1) % n_
            tri = np.vstack([np.column_stack([i, j, n_ + j]), np.column_stack([i, n_ + j, n_ + i]),
                             np.column_stack([np.zeros(n_ - 2, int), np.arange(2, n_), np.arange(1, n_ - 1)])])
            cen = pos.mean(0)
            mid = pos[tri].mean(1) - cen
            tri = m11.oriente(pos, tri, mid)
            dalle = {"name": f"ponceau_{cle}", "pos": pos.astype(np.float32), "nrm": m08.normales(pos, tri),
                     "uv": (pos[:, [0, 2]] - pos[:, [0, 2]].min(0)).astype(np.float32) / 2, "idx": tri.astype(np.uint32), "mat": "beton"}
            m_ann.append(dalle)
        # parapets
        par_pierre, par_sombre, parapets_int, parapets_plan = [], [], [], []
        for p in c.get("parapets", []):
            if "le_long_du_bord" in p:
                lb = p["le_long_du_bord"]
                s0, s1 = (pk_du_bord(ch, lb[k], lb["cote"], pk0, pk1) for k in ("de", "a"))
                _, E, n = bord_3d(rg, s0, s1, lb["cote"], 1.0)
                P, sortant, zp = E[:, :2], n, E[:, 2]
            else:
                P = np.asarray(shapely.LineString(p["polyligne"]).segmentize(1.0).coords)
                sortant = normales_sortantes(P, revetu)
                zp = z_de(P)
            zb = np.minimum(mnt.z(*(P + sortant * p["epaisseur_m"]).T), zp) - 0.3
            if ponceau:
                dans = shapely.contains_xy(Polygon(ponceau["polygone"]).buffer(0.2), P[:, 0], P[:, 1])
                zb = np.where(dans, zp - ponceau["epaisseur_m"], zb)
            v = mur(P, sortant, p["hauteur_m"], p["epaisseur_m"], zp - 0.02, zb, ref)
            (par_sombre if p["type"] == "pierre_sombre" else par_pierre).append(v)
            parapets_plan.append((p["nom"], P, p["type"]))
            if "le_long_du_bord" not in p:
                parapets_int.append(P)
            obstacles = np.vstack([obstacles, P])
        if par_pierre:
            m_ann.append(m11.fusion(par_pierre, f"parapets_pierre_{cle}", "pierre"))
        if par_sombre:
            m_ann.append(m11.fusion(par_sombre, f"parapets_sombres_{cle}", "pierre_sombre"))
        if par_pierre or par_sombre:
            m_coll.append(m11.fusion(par_pierre + par_sombre, f"parapets_{cle}_collision", "pierre"))
        # panneaux : poteau et panneaux (volumes simples), pied sur le MNT
        pan_meshes, panneaux = [], []
        for pn in c.get("panneaux", []):
            xy = np.asarray(pn["xy"], float)
            zs = float(mnt.z(xy[:1], xy[1:])[0])
            vers = rg(np.array([pk0 + 10.0]))[0][0, :2] - xy             # face au trafic qui arrive de la D3D
            lat = np.array([-vers[1], vers[0]])
            pan_meshes.append(pave(xy, vers, 0.08, 0.08, zs - 0.1, pn["haut_m_ngf"], ref))
            for k in range(pn["nombre"]):
                ztop = pn["haut_m_ngf"] - 0.05 - 0.4 * k
                pan_meshes.append(pave(xy + 0.06 * vers / np.linalg.norm(vers), lat, 1.0, 0.04, ztop - 0.25, ztop, ref))
            panneaux.append((pn["nom"], xy))
            obstacles = np.vstack([obstacles, xy[None]])
        if pan_meshes:
            m_ann.append(m11.fusion(pan_meshes, f"panneaux_{cle}", "panneau"))
        pin = c["terre_plein"].get("pin")
        if pin:
            obstacles = np.vstack([obstacles, np.asarray(pin["xy"])[None]])
        # balisage : piquets et rubalise
        lignes_b, mb = balisage(cfg["balisage_par_defaut"], rg, ferm_pk, obstacles, ruban, z_de, ref)
        for k, v in mb.items():
            if v:
                m_bal.append(m11.fusion(v, f"balisage_{cle}_{k}", k))
        if mb["piquet"]:
            m_bcoll.append(m11.fusion(mb["piquet"], f"piquets_{cle}", "plastique_piquet"))
        for b in lignes_b:
            lignes_csv.append({**b, "carrefour": nom})
        # geojson WGS84
        to_wgs = lambda g: shapely.ops.transform(lambda x, y, z=None: TO_WGS.transform(x, y), g)   # noqa: E731
        for g, typ, rq in ((revetu, "enrobé fermé (branche de droite, amorce de la D1 nord)", "TSD+ (asphalte), à appliquer dans 09"),
                           (terre, "terre-plein", "DBK+ (terre), à appliquer dans 09")):
            for gg in getattr(g, "geoms", [g]):
                feats.append({"type": "Feature", "geometry": mapping(to_wgs(gg)),
                              "properties": {"carrefour": nom, "type": typ, "surface_m2": round(gg.area, 1), "code_surface_jeu_propose": rq}})
        for nom_p, P, typ in parapets_plan:
            feats.append({"type": "Feature", "geometry": mapping(to_wgs(LineString(P))),
                          "properties": {"carrefour": nom, "type": f"parapet ({typ})", "nom": nom_p}})
        rapport[nom] = {"fermetures_pk": [(n_, s0, s1) for n_, s0, s1 in ferm_pk],
                        "enrobe_ferme_m2": round(revetu.area, 1), "terre_plein_m2": round(terre.area, 1),
                        "aire_triangulee_m2": {"enrobe": round(aire_enr, 1), "terre": round(aire_ter, 1)},
                        "balisage": {k: sum(1 for b in lignes_b if b["type"] == k) for k in ("piquet de rubalise", "rubalise")},
                        "_ctx": (ruban, fermetures, revetu, terre, parapets_int, lignes_b, c, parapets_plan, panneaux)}

    # --- écriture
    write_geojson(OUT / "annexes_revetues.geojson", feats, "annexes_revetues")
    with open(OUT / "balisage.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["carrefour", "fermeture", "x_l93", "y_l93", "z_m", "cap_deg", "type", "maillage_jeu_propose",
                     "longueur_supposee_m", "remarque"])
        for b in lignes_csv:
            wr.writerow([b["carrefour"], b["f"], f"{b['xy'][0]:.2f}", f"{b['xy'][1]:.2f}", f"{b['z']:.2f}", f"{b['cap']:.1f}",
                         b["type"], b["maillage"], f"{b['L']:.2f}" if b["L"] else "",
                         "dimensions du maillage du jeu inconnues ; cap = direction de l'alignement (0 = nord, sens horaire)"])
    for version, px in m11.VERSIONS.items():
        dossier = MOD if version == "complet" else MOD / "apercu"
        mats = {"enrobe": {"jpeg": m11.tex_enrobe(px), "rough": 0.92}, "terre": {"color": [0.47, 0.39, 0.29], "rough": 1.0},
                "pierre": {"jpeg": m11.tex_pierre(px // 2), "rough": 0.95},
                "pierre_sombre": {"color": [0.33, 0.32, 0.30], "rough": 0.95}, "beton": {"jpeg": m11.tex_beton(px // 2), "rough": 0.9},
                "panneau": {"color": [0.9, 0.9, 0.88], "rough": 0.6},
                "piquet": {"color": [0.92, 0.92, 0.92], "rough": 0.6}, "piquet_tete": {"color": [0.8, 0.08, 0.06], "rough": 0.6},
                "rubalise": {"color": [0.85, 0.1, 0.08], "rough": 0.5}}
        m11.ecrire_glb(dossier / "annexes.glb", m_ann, mats)
        m11.ecrire_glb(dossier / "balisage.glb", m_bal, mats)
        if version == "complet":
            mc = {"enrobe": {"color": [0.3, 0.3, 0.3]}, "terre": {"color": [0.47, 0.39, 0.29]}, "pierre": {"color": [0.6, 0.58, 0.54]},
                  "plastique_piquet": {"color": [0.92, 0.92, 0.92]}}
            m11.ecrire_glb(dossier / "annexes_collision.glb", m_coll, mc)
            m11.ecrire_glb(dossier / "balisage_collision.glb", m_bcoll, mc)
    for f in ("balisage_collision.glb",):                   # le balisage n'a plus de barrières
        if not m_bcoll and (MOD / f).exists():
            (MOD / f).unlink()
    for nom, d in rapport.items():
        ruban, fermetures, revetu, terre, parapets_int, lignes_b, c, parapets_plan, panneaux = d.pop("_ctx")
        d["controle"] = {v: controle(ref, ruban, fermetures, revetu, terre, parapets_int, lignes_b, MOD if v == "complet" else MOD / "apercu")
                         for v in m11.VERSIONS}
        FIG4.mkdir(parents=True, exist_ok=True)
        plan_figure(c, ch, ruban, revetu, terre, parapets_plan, panneaux, fermetures, lignes_b, FIG4 / "carrefour_plan.png",
                    d["fermetures_pk"])
    print(json.dumps(rapport, ensure_ascii=False, indent=1))

    # --- rendus (premier carrefour actif)
    if actifs:
        c = actifs[0]
        P = shapely.union_all([Polygon(s["polygone"]) for s in c["surfaces_revetues"]] + [Polygon(c["terre_plein"]["polygone"])])
        ctr = np.array(P.centroid.coords[0])
        zc = float(mnt.z(ctr[:1], ctr[1:])[0])
        s_f = rapport[c["nom"]]["fermetures_pk"][0][1]
        A = rg(np.array([s_f - 45.0, s_f - 30.0]))[0]
        dirv = (A[1, :2] - A[0, :2]) / np.linalg.norm(A[1, :2] - A[0, :2])
        lat = np.array([dirv[1], -dirv[0]])
        eye_h = np.array([[ctr[0] - 30 * dirv[0] + 6 * lat[0], ctr[1] - 30 * dirv[1] + 6 * lat[1], zc + 40]])
        conducteur = rg.point(np.array([s_f - 14.0]), 1.8, 1.4)          # à peu près la prise de vue de Street View 4
        cible = rg.point(np.array([s_f + 9.0]), 3.0, 1.2)
        vues = [("plongeante", m08.to_gltf(eye_h, ref)[0], m08.to_gltf(np.array([[ctr[0], ctr[1], zc]]), ref)[0], 50),
                ("conducteur_d3d", m08.to_gltf(conducteur, ref)[0], m08.to_gltf(cible, ref)[0], 80)]
        fichiers = [MOD / "terrain.glb", MOD / "route_habillee.glb", MOD / "ouvrages.glb", MOD / "annexes.glb", MOD / "balisage.glb"]
        print("rendus :", rendus(vues, [f for f in fichiers if f.exists()]))
    print(f"durée : {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
