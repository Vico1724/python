"""Étape 12 - Carrefours : voies non empruntées par la spéciale, terre-plein, parapets, balisage.

Au carrefour du Lion d'Or, la chaussée de la spéciale (07, zone 2 des corrections) suit la
branche de gauche de la patte d'oie ; son bord droit y est une ligne de fermeture qui barre la
branche de droite (D1 vers le nord) puis longe le terre-plein. Ce script modélise ce qui est
au-delà : l'enrobé de la branche de droite et de l'amorce de la D1 nord (avec son ponceau),
le terre-plein en terre, les parapets (pierre, ponceau), les panneaux et la rubalise de
fermeture. Le plan (polygones, polylignes, hauteurs, sources) est dans le JSON : il a été
établi sur le nuage de points LiDAR HD classé de l'IGN, le MNT, Street View et la vidéo.
Section « constructions de la zone de départ » : volumes qui ne suivent pas la route (bâtiments, murs en
travers, portail, pilier, monolithe, rampe, barrières) de data/reference/zone_depart.json, ajoutés à
annexes.glb et annexes_collision.glb.

Entrées : data/reference/carrefours_annexes.json, data/reference/zone_depart.json (liste « constructions »),
          data/processed/chaussee_precise.csv, data/raw/mnt_lidarhd_50cm.tif, mns_lidarhd_50cm.tif (hauteur
          des bâtiments), modele/repere.json, modele/ouvrages_collision.glb (parapets
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
def controle(ref, ruban, fermetures, revetu, terre, parapets_int, lignes_b, dossier, n_ferm=None):
    """fermetures : toutes les lignes de raccord (écart vertical) ; les n_ferm premières sont des
    fermetures (couverture vérifiée du côté droit)."""
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
            for F in fermetures[:n_ferm]:                      # couverture à 0,2 m au-delà du bord
                L = LineString(F[:, :2])
                s = np.arange(0.25, L.length - 0.25, 0.5)
                q = np.array([L.interpolate(x).coords[0] for x in s])
                tg = np.gradient(q, axis=0)
                q2 = q + 0.2 * np.column_stack([tg[:, 1], -tg[:, 0]]) / np.linalg.norm(tg, axis=1, keepdims=True)
                couvert.append(shapely.contains_xy(shapely.union_all([revetu, terre]).buffer(1e-3), q2[:, 0], q2[:, 1]))
            e = np.concatenate(ecarts) if ecarts else np.zeros(0)
            r[f]["raccord_fermeture"] = {"sommets_sur_la_ligne": int(len(e)),
                                         "ecart_vertical_max_m": round(float(np.abs(e).max()), 4) if len(e) else None,
                                         "bord_couvert_a_0_2_m_pct": round(float(np.concatenate(couvert).mean() * 100), 1) if couvert else None}
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
        for h_ in g.interiors:
            ax.fill(*h_.xy, color="#e8efe2", lw=0)
    for g in ([] if terre.is_empty else getattr(terre, "geoms", [terre])):
        ax.fill(*g.exterior.xy, color="#c9b48a", lw=0)
    if c.get("ponceau"):
        ax.fill(*Polygon(c["ponceau"]["polygone"]).exterior.xy, facecolor="none", edgecolor="#555", hatch="///", lw=0.8)
    if c.get("zone_hachuree"):
        ax.fill(*Polygon(c["zone_hachuree"]["polygone"]).exterior.xy, facecolor="white", edgecolor="white", alpha=0.8, hatch="\\\\", lw=0.5)
        zh = np.array(Polygon(c["zone_hachuree"]["polygone"]).centroid.coords[0])
        ax.annotate("zone hachurée peinte", zh, xytext=(zh[0] - 22, zh[1] - 10), fontsize=8, arrowprops=dict(arrowstyle="->"),
                    bbox=dict(boxstyle="round", fc="white", alpha=0.85))
    if c.get("fosse"):
        fo = np.array(c["fosse"]["polyligne"])
        ax.plot(fo[:, 0], fo[:, 1], color="#2b7bba", lw=2.5, ls=(0, (4, 2)))
    for il in c.get("ilots", []):
        ax.fill(*Polygon(il["polygone"]).exterior.xy, color="#8fbf6a", lw=0)
        ax.annotate(il["nom"], np.array(Polygon(il["polygone"]).centroid.coords[0]), fontsize=8, ha="center",
                    bbox=dict(boxstyle="round", fc="white", alpha=0.8))
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
    pin = (c.get("terre_plein") or {}).get("pin")
    if pin:
        ax.scatter(*pin["xy"], marker="^", s=160, color="#2ca02c", edgecolor="k", zorder=6)
    # légendes en clair
    txt = [(t_, np.asarray(xy_)) for t_, xy_ in c.get("etiquettes", [])]
    if fermetures_pk:
        s_a, s_b = fermetures_pk[0][1], fermetures_pk[-1][2]
        txt += [("D3D (arrivée)", ch["A"][np.argmin(np.abs(ch["pk"] - s_a + 14))]),
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
    if not terre.is_empty:
        tp = np.array(terre.representative_point().coords[0])
        ax.annotate("terre-plein", tp, fontsize=10, ha="center", bbox=dict(boxstyle="round", fc="white", alpha=0.8))
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    leg = [Patch(color="#5d6066", label="chaussée de la spéciale"), Patch(color="#9aa0a8", label="surface revêtue annexe (modélisée à part)"),
           Patch(color="#c9b48a", label="terre-plein (terre)"), Patch(facecolor="none", edgecolor="#555", hatch="///", label="tablier du ponceau"),
           Line2D([], [], color="#8a6d3b", lw=4, label="parapet de pierre"), Line2D([], [], color="#3b3b3b", lw=4, label="parapet sombre (ponceau)"),
           Line2D([], [], color="#2b7bba", lw=2.5, ls="--", label="ruisseau / fossé"), Line2D([], [], color="#d62728", lw=2, label="ligne de fermeture"),
           Line2D([], [], marker="o", color="w", markerfacecolor="#d62728", label="piquets de rubalise"),
           Line2D([], [], marker="s", color="w", markerfacecolor="#1f77b4", markersize=9, label="panneaux"),
           Line2D([], [], marker="^", color="w", markerfacecolor="#2ca02c", markersize=11, label="grand pin"),
           Line2D([], [], color="k", lw=1.2, ls="--", label="axe de la spéciale")]
    present = {"terre-plein (terre)": not terre.is_empty, "tablier du ponceau": bool(c.get("ponceau")),
               "parapet de pierre": any(t_ != "pierre_sombre" for _, _, t_ in parapets),
               "parapet sombre (ponceau)": any(t_ == "pierre_sombre" for _, _, t_ in parapets), "ruisseau / fossé": bool(c.get("fosse")),
               "ligne de fermeture": bool(fermetures), "piquets de rubalise": bool(lignes_b), "panneaux": bool(panneaux),
               "grand pin": bool((c.get("terre_plein") or {}).get("pin"))}
    leg = [h_ for h_ in leg if present.get(h_.get_label(), True)]
    if c.get("ilots"):
        leg.append(Patch(color="#8fbf6a", label="îlot (herbe)"))
    ax.legend(handles=leg, loc="lower left", fontsize=8, framealpha=0.9)
    b = shapely.union_all([revetu, terre]).buffer(8).bounds
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
    ax.set_title(f"{c['nom']} - plan (Lambert-93, quadrillage de 10 m, nord en haut)", fontsize=11)
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
            npm, node = shutil.which("npm"), shutil.which("node")      # npm.cmd sous Windows : chemin complet
            if not (npm and node):
                print("rendu WebGL impossible : Node.js (npm, node) introuvable ; rendus sautés")
                return False
            node_path = subprocess.run([npm, "root", "-g"], capture_output=True, text=True).stdout.strip()
            res = subprocess.run([node, "rendu.js", json.dumps(views)], cwd=tmp, capture_output=True, text=True,
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


# --- constructions de la zone de départ -------------------------------------------------------------------
# Volumes qui ne suivent pas la route (data/reference/zone_depart.json, liste « constructions ») : bâtiments de la BD TOPO
# et cabanon, murs en travers, portail, pilier, monolithe, rampe, barrières. Coordonnées Lambert-93, pied sur le MNT
# LiDAR. Les matières nouvelles sont des couleurs unies (16_paquet_unreal.py en fait une matière à couleur unie) ; béton
# et pierre reprennent les matières des parapets. Physique : un volume balayé (m11.boite) par mur ou par face de
# bâtiment, matière de choc prise dans la table OBSTACLES de 09_export_stage_ir.py (beton, pierre, metal_glissiere).
ZD_MATIERES = {          # couleurs linéaires (glTF), d'après les captures Street View
    "enduit_clair": {"color": [0.60, 0.52, 0.40], "rough": 0.95},      # enduit beige rosé (mur du parking, maisons)
    "enduit_blanc": {"color": [0.74, 0.72, 0.66], "rough": 0.9},       # enduit blanc cassé (cabanon, pans du portail)
    "tuile": {"color": [0.42, 0.13, 0.06], "rough": 0.9},              # tuiles canal rouge orangé
    "portail_blanc": {"color": [0.83, 0.83, 0.80], "rough": 0.5},      # portail métallique plein
    "barriere_noire": {"color": [0.018, 0.018, 0.02], "rough": 0.5},   # lisses et montants des barrières
    "barriere_rouge": {"color": [0.55, 0.02, 0.02], "rough": 0.6},     # bandes des poteaux, disque « sens interdit »
    "barriere_blanc": {"color": [0.80, 0.80, 0.78], "rough": 0.6},
    "plaque_jaune": {"color": [0.80, 0.52, 0.01], "rough": 0.6},       # plaque de la barrière DFCI
}
ZD_COLLISION = {"metal_glissiere": {"color": [0.72, 0.74, 0.76]}, "beton": {"color": [0.7, 0.7, 0.68]}}
ZD_EP_TOIT = 0.15        # m : épaisseur de la dalle de toit (débord compris)
ZD_ENFOUI = 0.3          # m : les murs descendent sous le terrain le plus bas de leur pied
ZD_PAS_COLLISION = 1.0   # m : longueur maximale d'un tronçon de collision des faces de bâtiment (un pavé par tronçon dans 09)
ZD_ASSISE_COLLISION = 1.25  # m : hauteur maximale d'une assise de collision des faces de bâtiment


def _vers_gltf_n(n):
    """Normale Lambert-93 (x est, y nord, z haut) -> repère glTF du modèle (X, Y haut, Z sud)."""
    n = np.atleast_2d(np.asarray(n, float))
    return np.column_stack([n[:, 0], n[:, 2], -n[:, 1]])


class _Lot:
    """Faces planes accumulées par matériau : sommets propres à chaque face (arêtes vives), normale de la face, UV en
    mètres, triangles orientés dans le sens de la normale."""

    def __init__(self, ref):
        self.ref, self.parts = ref, {}

    def face(self, mat, P, n, uv):
        """P : (k, 3) Lambert-93, polygone plan convexe (éventail) ; n : normale L93 ; uv : (k, 2) en mètres."""
        P = np.asarray(P, float)
        pos = m08.to_gltf(P, self.ref).astype(np.float64)
        k = len(P)
        tri = np.column_stack([np.zeros(k - 2, int), np.arange(1, k - 1), np.arange(2, k)])
        ng = _vers_gltf_n(n)[0]
        ng /= max(np.linalg.norm(ng), 1e-12)
        tri = m11.oriente(pos, tri, ng)
        self.parts.setdefault(mat, []).append({"pos": pos, "nrm": np.tile(ng, (k, 1)).astype(np.float32),
                                               "uv": np.asarray(uv, np.float32), "idx": tri})

    def triangles(self, mat, T, n, uv):
        """T : (m, 3, 3) triangles Lambert-93 de même normale n ; uv : (m, 3, 2)."""
        for t, u in zip(T, uv):
            self.face(mat, t, n, u)

    def meshes(self, nom):
        out = []
        for mat, parts in self.parts.items():
            m = m11.fusion(parts, f"{nom}_{mat}", mat)
            m["pos"] = m["pos"].astype(np.float32)
            out.append(m)
        return out


def _anneau(poly, ligne=None):
    """Sommets de l'anneau extérieur (sens trigonométrique, sans répétition), avec les points où il coupe la ligne de
    faîtage (pour que le haut des murs et des rives suive exactement les deux pans)."""
    R = np.asarray(shapely.orient_polygons(poly).exterior.coords)[:-1, :2]
    if ligne is None:
        return R
    c, v = ligne
    out = []
    for a, b in zip(R, np.roll(R, -1, axis=0)):
        out.append(a)
        da, db = (a - c) @ v, (b - c) @ v
        if da * db < 0:
            out.append(a + (b - a) * da / (da - db))
    return np.array(out)


def _batiment(e, lot, mnt, mns, ref):
    """Bâtiment : murs extrudés du pied (MNT le plus bas du contour, moins ZD_ENFOUI) au toit ; toit plat ou à deux pans
    (faîtage dans l'axe long du rectangle d'emprise minimal, ou selon « faitage_direction »), dalle de toit fermée
    (dessus, dessous, rives) avec débord. Hauteur = faîtage au-dessus du terrain : hauteur_m, ou MNS - MNT LiDAR."""
    P = shapely.orient_polygons(Polygon(e["polygone_l93"]))
    x0, y0, x1, y1 = P.bounds
    gx, gy = np.meshgrid(np.arange(x0, x1, 0.5), np.arange(y0, y1, 0.5))
    Q = np.column_stack([gx.ravel(), gy.ravel()])
    Q = Q[shapely.contains_xy(P.buffer(-0.5), Q[:, 0], Q[:, 1])]
    if len(Q) < 4:
        Q = np.asarray(P.exterior.coords)[:-1]
    z_terrain = mnt.z(Q[:, 0], Q[:, 1])
    z_ref = float(np.median(z_terrain))
    H, h_src = e.get("hauteur_m"), "donnée"
    if H is None:
        # Faîtage : 90e centile du MNS - MNT si le toit est net (écart p90 - p50 < 1,5 m) ; sinon des arbres débordent sur
        # le toit et l'on prend le 75e centile, plafonné à la hauteur BD TOPO + 0,5 m.
        h = mns.z(Q[:, 0], Q[:, 1]) - z_terrain
        p50, p75, p90 = np.percentile(h, [50, 75, 90])
        if p90 - p50 < 1.5:
            H, h_src = float(p90), "MNS - MNT, 90e centile"
        else:
            H = float(p75) if e.get("hauteur_bd_topo_m") is None else float(min(p75, e["hauteur_bd_topo_m"] + 0.5))
            H, h_src = H, "MNS - MNT, 75e centile (arbres au-dessus du toit), plafonné à BD TOPO + 0,5 m"
        H = max(H, 2.2)
    deux_pans = e.get("toit", "deux_pans") == "deux_pans"
    debord = float(e.get("debord_toit_m", 0.3)) if deux_pans else 0.0
    # repère du faîtage : u le long, v en travers
    if e.get("faitage_direction"):
        u = np.asarray(e["faitage_direction"], float)
    else:
        R = np.asarray(P.minimum_rotated_rectangle.exterior.coords)[:4]
        a, b = R[1] - R[0], R[2] - R[1]
        u = a if np.linalg.norm(a) >= np.linalg.norm(b) else b
    u = u / np.linalg.norm(u)
    v = np.array([-u[1], u[0]])
    S = np.asarray(P.exterior.coords)[:-1]
    sv = S @ v
    c = S.mean(0) - v * (S.mean(0) @ v) + v * (sv.min() + sv.max()) / 2       # faîtage au milieu de la largeur
    hw = (sv.max() - sv.min()) / 2
    # montée du toit : pente donnée, sans dépasser 45 % de la hauteur ni descendre l'égout sous 2,2 m
    monte = max(min(float(e.get("pente_toit", 0.30)) * hw, 0.45 * H, H - 2.2), 0.0) if deux_pans else 0.0
    pente = monte / hw if hw > 1e-6 else 0.0
    ligne = (c, v) if deux_pans else None

    def z_toit(XY):
        return z_ref + H - pente * np.abs((np.atleast_2d(XY) - c) @ v)

    z_bas = float(mnt.z(*_anneau(P).T).min()) - ZD_ENFOUI
    mm, mt = e.get("materiau_murs", "enduit_clair"), e.get("materiau_toit", "tuile")
    # murs
    W = _anneau(P, ligne)
    cum = 0.0
    for a, b in zip(W, np.roll(W, -1, axis=0)):
        L = float(np.linalg.norm(b - a))
        if L < 1e-3:
            continue
        ta, tb = z_toit(np.array([a, b])) - ZD_EP_TOIT
        n = np.array([(b - a)[1], -(b - a)[0], 0.0]) / L                       # anneau trigonométrique : extérieur à droite
        lot.face(mm, [[*a, z_bas], [*b, z_bas], [*b, tb], [*a, ta]], n,
                 [[cum, 0], [cum + L, 0], [cum + L, tb - z_bas], [cum, ta - z_bas]])
        cum += L
    # toit : dessus et dessous de chaque pan (triangulation contrainte), rives tout autour
    Rt = shapely.orient_polygons(P.buffer(debord, join_style="mitre")) if debord > 0 else P
    if deux_pans:
        grand = 4 * (hw + debord + 50)
        pans = [Rt.intersection(Polygon([c - u * grand, c + u * grand, c + u * grand + s * v * grand, c - u * grand + s * v * grand]))
                for s in (1.0, -1.0)]
    else:
        pans = [Rt]
    for s, pan in zip((1.0, -1.0), pans):
        for g in getattr(pan, "geoms", [pan]):
            if g.is_empty or g.geom_type != "Polygon" or g.area < 1e-4:
                continue
            for t in shapely.get_parts(shapely.constrained_delaunay_triangles(g)):
                T = np.asarray(t.exterior.coords)[:3]
                zt = z_toit(T)
                # pan s : z = z_ref + H - pente * s * (p - c).v, normale (s * pente * v, 1) (plat : verticale)
                nh = np.array([s * pente * v[0], s * pente * v[1], 1.0])
                uvt = np.column_stack([(T - c) @ u, (T - c) @ v])
                lot.face(mt, np.column_stack([T, zt]), nh, uvt)
                lot.face(mt, np.column_stack([T, zt - ZD_EP_TOIT]), -nh, uvt)
    Rr = _anneau(Rt, ligne)
    cum = 0.0
    for a, b in zip(Rr, np.roll(Rr, -1, axis=0)):
        L = float(np.linalg.norm(b - a))
        if L < 1e-3:
            continue
        ta, tb = z_toit(np.array([a, b]))
        n = np.array([(b - a)[1], -(b - a)[0], 0.0]) / L
        lot.face(mt, [[*a, ta - ZD_EP_TOIT], [*b, tb - ZD_EP_TOIT], [*b, tb], [*a, ta]], n,
                 [[cum, 0], [cum + L, 0], [cum + L, ZD_EP_TOIT], [cum, ZD_EP_TOIT]])
        cum += L
    # physique : un volume balayé de 0,3 m par face de mur, du pied jusqu'à l'égout (le pignon au-dessus n'arrête rien).
    # Chaque face est découpée en tronçons d'au plus ZD_PAS_COLLISION et en assises d'au plus ZD_ASSISE_COLLISION :
    # 09_export_stage_ir.py en fait un pavé par tronçon, et son contrôle cherche le pavé qui couvre un sommet parmi les 8
    # centres les plus proches ; une face d'un seul pavé de 10 à 18 m (centre à 5-9 m de ses coins), ou haute de 5 m
    # (centre à 2,4 m de son pied), n'y figurait pas quand des pavés courts ou bas (mur voisin, bâtiment mitoyen plus
    # bas) étaient plus près.
    coll = []
    R0 = _anneau(P)
    for a, b in zip(R0, np.roll(R0, -1, axis=0)):
        L = float(np.linalg.norm(b - a))
        if L < 0.2:
            continue
        n = np.array([(b - a)[1], -(b - a)[0]]) / L
        zt = float(min(z_toit(np.array([a, b])).min() - ZD_EP_TOIT, z_ref + H - monte - ZD_EP_TOIT))
        k_ = max(int(np.ceil(L / ZD_PAS_COLLISION)), 1)
        Pp = a + (b - a) * np.linspace(0.0, 1.0, k_ + 1)[:, None]
        zs = np.linspace(z_bas, zt, max(int(np.ceil((zt - z_bas) / ZD_ASSISE_COLLISION)), 1) + 1)
        for z0_, z1_ in zip(zs[:-1], zs[1:]):
            coins = [np.column_stack([Pp + n * o, np.full(len(Pp), zz)])
                     for o, zz in ((-0.3, z0_), (0.0, z0_), (0.0, z1_), (-0.3, z1_))]
            coll.append(m11.boite(coins, ref))
    return coll, {"hauteur_faitage_m": round(H, 2), "hauteur_methode": h_src, "egout_m": round(H - monte, 2),
                  "toit": "deux pans" if deux_pans else "plat", "z_terrain_m": round(z_ref, 2)}


def _mur(e, mnt, ref, ruban):
    """Mur libre le long d'une polyligne : épaisseur centrée, dessus à hauteur_m au-dessus du pied le plus bas (MNT des deux
    côtés), dessous ZD_ENFOUI sous le terrain le plus bas. Jamais à moins de 0,3 m de la chaussée de la spéciale."""
    ep = float(e["epaisseur_m"])
    L_ = LineString(e["polyligne_l93"]).difference(ruban.buffer(0.3 + ep / 2))
    L_ = max(shapely.get_parts(L_), key=lambda g: g.length)
    P = np.asarray(L_.segmentize(1.0).coords)
    tg = np.gradient(P, axis=0)
    n = np.column_stack([tg[:, 1], -tg[:, 0]]) / np.linalg.norm(tg, axis=1, keepdims=True)
    cotes = [mnt.z(*(P + n * o).T) for o in (-(ep / 2 + 0.7), 0.0, ep / 2 + 0.7)]
    pied = np.minimum.reduce(cotes)
    haut = pied + float(e["hauteur_m"])
    bas = pied - ZD_ENFOUI
    coins = [np.column_stack([P + n * o, z_]) for o, z_ in ((-ep / 2, bas), (ep / 2, bas), (ep / 2, haut), (-ep / 2, haut))]
    v = m11.boite(coins, ref)
    return v, {"longueur_m": round(L_.length, 1), "hauteur_au_dessus_du_pied_m": e["hauteur_m"],
               "denivele_entre_les_deux_faces_m": round(float(np.max(np.abs(cotes[0] - cotes[2]))), 2)}, P


def _bloc(c, t, L, W, z_bas, z_haut0, z_haut1, ref):
    """Pavé horizontal centré en c (x, y), long de L selon t, large de W, dessus de z_haut0 (début) à z_haut1 (fin)."""
    t = np.asarray(t, float) / np.linalg.norm(t)
    n = np.array([-t[1], t[0]])
    P = np.array([np.asarray(c) - t * L / 2, np.asarray(c) + t * L / 2])
    zh = np.array([z_haut0, z_haut1])
    co = lambda o, z_: np.column_stack([P + o * n, np.broadcast_to(z_, 2)])     # noqa: E731
    return m11.boite([co(-W / 2, z_bas), co(W / 2, z_bas), co(W / 2, zh), co(-W / 2, zh)], ref)


def _disque(lot, mat, c3, t, r, ep, k=16):
    """Disque vertical (prisme à k côtés) centré en c3 (L93), dans le plan de la direction t, épais de ep."""
    t = np.asarray(t, float) / np.linalg.norm(t)
    n = np.array([-t[1], t[0], 0.0])
    T = np.array([t[0], t[1], 0.0])
    a = np.linspace(0, 2 * np.pi, k, endpoint=False)
    ring = np.asarray(c3)[None] + r * (np.cos(a)[:, None] * T + np.sin(a)[:, None] * np.array([0, 0, 1.0]))
    uv = np.column_stack([np.cos(a), np.sin(a)]) * r
    for s in (1.0, -1.0):
        lot.face(mat, ring + s * n * ep / 2, s * n, uv)
    for i in range(k):
        j = (i + 1) % k
        q = [ring[i] - n * ep / 2, ring[j] - n * ep / 2, ring[j] + n * ep / 2, ring[i] + n * ep / 2]
        nm = (ring[i] + ring[j]) / 2 - np.asarray(c3)
        lot.face(mat, q, nm / np.linalg.norm(nm), [[0, 0], [1, 0], [1, 1], [0, 1]])


def _barriere(e, mnt, ref):
    """Barrière de piste ou de parking : deux poteaux (rayés rouge et blanc ou noirs), lisses et montants noirs, plaque
    (disque « sens interdit » ou plaque jaune) au milieu. Renvoie (pièces par matériau, lot de faces, collision, segment)."""
    a, b = (np.asarray(p, float) for p in e["segment_l93"])
    t = (b - a) / np.linalg.norm(b - a)
    m = (a + b) / 2
    L = float(e.get("longueur_m") or np.linalg.norm(b - a))
    a, b = m - t * L / 2, m + t * L / 2
    zs = mnt.z(np.array([a[0], m[0], b[0]]), np.array([a[1], m[1], b[1]]))
    z0 = float(zs.mean())
    pieces = {}
    sec, hp = 0.10, float(e.get("hauteur_poteaux_m", 1.2))
    for p, zp in ((a, zs[0]), (b, zs[2])):
        # haut des poteaux au niveau des lisses (z0 : terrain moyen), pied sous le terrain local (terrain en pente)
        pied = float(min(zp, z0)) - ZD_ENFOUI
        if e.get("poteaux") == "rouge_blanc":                 # bandes de 25 cm, la plus haute rouge
            bornes = np.append(np.arange(0.0, hp, 0.25), hp)
            for k_, (h0, h1) in enumerate(zip(bornes[:-1], bornes[1:])):
                mat = "barriere_rouge" if (len(bornes) - 2 - k_) % 2 == 0 else "barriere_blanc"
                pieces.setdefault(mat, []).append(pave(p, t, sec, sec, pied if k_ == 0 else z0 + h0, z0 + h1, ref))
        else:
            pieces.setdefault("barriere_noire", []).append(pave(p, t, sec, sec, pied, z0 + hp, ref))
    lisses = sorted(e.get("lisses_a_m", [1.0, 0.5]))
    Li = L - sec
    for zl in lisses:
        pieces.setdefault("barriere_noire", []).append(pave(m, t, Li, 0.06, z0 + zl - 0.03, z0 + zl + 0.03, ref))
    pas = float(e.get("pas_montants_m", 0.75))
    nb = max(int(round(Li / pas)), 1)
    for k_ in range(1, nb):
        p = a + t * (sec / 2 + Li * k_ / nb)
        pieces.setdefault("barriere_noire", []).append(pave(p, t, 0.04, 0.04, z0 + lisses[0], z0 + lisses[-1], ref))
    lot = _Lot(ref)
    zc = z0 + (lisses[0] + lisses[-1]) / 2
    nrm = np.array([-t[1], t[0]])
    if e.get("plaque") == "disque_sens_interdit":
        _disque(lot, "barriere_rouge", [*(m + nrm * 0.05), zc], t, 0.30, 0.02)
        pieces.setdefault("barriere_blanc", []).append(pave(m + nrm * 0.075, t, 0.40, 0.012, zc - 0.05, zc + 0.05, ref))
    elif e.get("plaque") == "plaque_jaune":
        pieces.setdefault("plaque_jaune", []).append(pave(m + nrm * 0.05, t, 0.45, 0.02, zc - 0.17, zc + 0.17, ref))
    coll = _bloc(m, t, L, 0.10, float(zs.min()) - 0.2,z0 + float(e["hauteur_m"]), z0 + float(e["hauteur_m"]), ref)
    return pieces, lot, coll, np.array([a, b])


def constructions_depart(ch, mnt, ref):
    """Section « constructions de la zone de départ » : maillages du décor (à ajouter à annexes.glb), volumes de collision
    (annexes_collision.glb), bilan et éléments du plan de contrôle."""
    f = REF / "zone_depart.json"
    if not f.exists():
        return [], [], {}, []
    cfg = json.loads(f.read_text(encoding="utf-8")).get("constructions", [])
    if not cfg:
        return [], [], {}, []

    class MNS(m08.MNT):
        def __init__(self):
            import rasterio
            with rasterio.open(ROOT / "data" / "raw" / "mns_lidarhd_50cm.tif") as s:
                self.a, self.inv = s.read(1), ~s.transform

    mns = MNS()
    ruban = ruban_poly(ch, ch["pk"][0], 100.0)              # la zone de départ ne va pas au-delà du PK +20
    shapely.prepare(ruban)
    deco, coll, bilan, plan = [], [], {}, []
    sol = None
    for k, e in enumerate(cfg):
        cle = f"depart_{k:02d}_{e['type']}"
        info = {"nom": e["nom"], "type": e["type"]}
        if e["type"] == "batiment":
            lot = _Lot(ref)
            cb, inf = _batiment(e, lot, mnt, mns, ref)
            deco += lot.meshes(cle)
            coll += [(cb, e.get("materiau_collision", "beton"))]
            info.update(inf)
            plan.append(("batiment", np.asarray(e["polygone_l93"]), e["nom"]))
        elif e["type"] == "mur":
            v, inf, P = _mur(e, mnt, ref, ruban)
            deco.append(m11.fusion([v], f"{cle}_{e['materiau']}", e["materiau"]))
            coll += [([v], e.get("materiau_collision", "beton"))]
            info.update(inf)
            plan.append(("mur", P, e["nom"]))
        elif e["type"] == "bloc":
            c = np.asarray(e["centre_l93"], float)
            t = np.asarray(e.get("direction", [1.0, 0.0]), float)
            L, W = float(e["longueur_m"]), float(e["largeur_m"])
            tn = t / np.linalg.norm(t)
            Q = np.array([c + s1 * tn * L / 2 + s2 * np.array([-tn[1], tn[0]]) * W / 2 for s1 in (-1, 1) for s2 in (-1, 1)])
            zq = mnt.z(Q[:, 0], Q[:, 1])
            zc = float(mnt.z(c[:1], c[1:])[0])
            v = _bloc(c, t, L, W, float(zq.min()) - ZD_ENFOUI, zc + float(e["hauteur_m"]), zc + float(e.get("hauteur_fin_m", e["hauteur_m"])), ref)
            deco.append(m11.fusion([v], f"{cle}_{e['materiau']}", e["materiau"]))
            coll += [([v], e.get("materiau_collision", "pierre"))]
            plan.append(("bloc", Q[[0, 1, 3, 2]], e["nom"]))
        elif e["type"] == "portail":
            a, b = (np.asarray(p, float) for p in e["segment_l93"])
            t = (b - a) / np.linalg.norm(b - a)
            pl = e.get("piliers") or {}
            sp = float(pl.get("section_m", 0.0))
            zab = mnt.z(np.array([a[0], b[0]]), np.array([a[1], b[1]]))
            z0 = float(zab.mean())
            Lg = float(np.linalg.norm(b - a)) - sp
            v = _bloc((a + b) / 2, t, Lg, float(e["epaisseur_m"]), float(zab.min()) - 0.05, z0 + float(e["hauteur_m"]), z0 + float(e["hauteur_m"]), ref)
            deco.append(m11.fusion([v], f"{cle}_{e['materiau']}", e["materiau"]))
            vs = [v]
            if pl:
                pil = [_bloc(p, t, sp, sp, float(zp) - ZD_ENFOUI, float(zp) + float(pl["hauteur_m"]), float(zp) + float(pl["hauteur_m"]), ref)
                       for p, zp in ((a, zab[0]), (b, zab[1]))]
                deco.append(m11.fusion(pil, f"{cle}_piliers_{pl['materiau']}", pl["materiau"]))
                vs += pil
            coll += [(vs, e.get("materiau_collision", "beton"))]
            plan.append(("portail", np.array([a, b]), e["nom"]))
        elif e["type"] == "barriere":
            pieces, lot, cb, seg = _barriere(e, mnt, ref)
            for mat, vs in pieces.items():
                deco.append(m11.fusion(vs, f"{cle}_{mat}", mat))
            deco += lot.meshes(f"{cle}_plaque")
            coll += [([cb], e.get("materiau_collision", "metal_glissiere"))]
            plan.append(("barriere", seg, e["nom"]))
        elif e["type"] == "rampe":
            P = Polygon(e["polygone_l93"]).difference(ruban.buffer(0.05))
            P = max(getattr(P, "geoms", [P]), key=lambda g: g.area)
            if sol is None and (MOD / "terrain.glb").exists():
                sol = SolTerrain(ref, P.buffer(8).bounds)
            z_de = lambda XY: mnt.z(XY[:, 0], XY[:, 1]) + SURELEV                          # noqa: E731
            if sol is not None:
                sm, aire = maillage_sur_terrain(P, sol, z_de, ref, e["materiau"], f"{cle}_{e['materiau']}", m11.S_PAROI, [])
            else:
                sm, aire = maillage_surface(P, z_de, ref, e["materiau"], f"{cle}_{e['materiau']}", m11.S_PAROI)
            deco.append(sm)                                            # décor seul : le sol physique reste le terrain
            ring = np.asarray(P.exterior.coords)
            zr = mnt.z(ring[:, 0], ring[:, 1])
            info.update({"aire_m2": round(aire, 1), "denivele_mnt_m": round(float(zr.max() - zr.min()), 2)})
            plan.append(("rampe", ring, e["nom"]))
        else:
            info["non_construit"] = f"type inconnu « {e['type']} »"
        bilan[cle] = info
    # garde-fou : aucun volume à moins de 0,3 m de la chaussée de la spéciale (la rampe s'y raccorde, elle est exclue)
    for m in deco:
        cle = "_".join(m["name"].split("_")[:3])
        if bilan[cle]["type"] == "rampe":
            continue
        pp = m["pos"].astype(np.float64)
        XY = np.column_stack([pp[:, 0] + ref["x0"], ref["y0"] - pp[:, 2]])
        d = float(shapely.distance(ruban, shapely.points(XY)).min())
        bilan[cle]["distance_min_a_la_chaussee_m"] = round(min(d, bilan[cle].get("distance_min_a_la_chaussee_m", np.inf)), 2)
    trop_pres = [b["nom"] for b in bilan.values() if b.get("distance_min_a_la_chaussee_m", np.inf) <= 0.3]
    if trop_pres:
        raise SystemExit(f"constructions de la zone de départ à moins de 0,3 m de la chaussée : {trop_pres}")
    # collision : un maillage par matière de choc
    par_mat = {}
    for vs, mat in coll:
        par_mat.setdefault(mat, []).extend(vs)
    m_coll = [m11.fusion(vs, f"constructions_depart_{mat}_collision", mat) for mat, vs in par_mat.items()]
    return deco, m_coll, bilan, plan


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
        cle = c.get("cle") or "".join(ch_ if ch_.isalnum() else "_" for ch_ in nom.lower())
        pk0, pk1 = c["pk"]
        ruban = ruban_poly(ch, pk0 - 60, pk1 + 60)
        # fermetures : du point « de » au point « a » le long du bord droit
        ferm_pk = [(f["nom"], pk_du_bord(ch, f["de"], "droite", pk0, pk1), pk_du_bord(ch, f["a"], "droite", pk0, pk1))
                   for f in c["fermetures"]]
        fermetures = [bord_3d(rg, s0, s1)[1] for _, s0, s1 in ferm_pk]
        # raccords : bords de la chaussée (ou son début) contre lesquels une surface vient se coller sans fermeture
        raccords = []
        for r_ in c.get("raccords", []):
            if r_["cote"] == "debut":
                raccords.append(np.array([ch["G"][0], ch["A"][0], ch["D"][0]]))
            else:
                a_, b_ = max(r_["pk"][0], ch["pk"][0]), min(r_["pk"][1], ch["pk"][-1])
                raccords.append(bord_3d(rg, a_, b_, r_["cote"])[1])
        lignes3 = fermetures + raccords
        ponceau = c.get("ponceau")
        z_de = fabrique_altitude(mnt, lignes3, ponceau)
        # surfaces : enrobé fermé et terre-plein, moins la chaussée de la spéciale
        revetu = shapely.union_all([Polygon(s["polygone"], s.get("trous", [])) for s in c.get("surfaces_revetues", [])]).difference(ruban)
        terre = (Polygon(c["terre_plein"]["polygone"]).difference(ruban).difference(revetu.buffer(0.05)) if c.get("terre_plein")
                 else Polygon())
        bx = shapely.union_all([revetu, terre]).buffer(5).bounds
        sol = SolTerrain(ref, bx) if (MOD / "terrain.glb").exists() else None
        lignes = [LineString(F[:, :2]) for F in lignes3]
        tab = Polygon(ponceau["polygone"]) if ponceau else None
        aire_enr = aire_ter = 0.0
        for P_, mat_, nm_, uv_ in ((revetu, "enrobe", f"enrobe_{cle}", m11.S_ENROBE), (terre, "terre", f"terre_plein_{cle}", 2.0)):
            if P_.is_empty:
                continue
            if sol is not None:
                sm, a2 = maillage_sur_terrain(P_, sol, z_de, ref, mat_, nm_, uv_, lignes, tab)
            else:
                sm, a2 = maillage_surface(P_, z_de, ref, mat_, nm_, uv_)
            m_ann.append(sm)
            m_coll.append({**sm, "name": f"{nm_}_collision"})
            if mat_ == "enrobe":
                aire_enr = a2
            else:
                aire_ter = a2
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
                L_ = shapely.LineString(p["polyligne"]).difference(ruban.buffer(0.05))   # jamais sur la chaussée de la spéciale
                if L_.is_empty:
                    continue
                L_ = max(shapely.get_parts(L_), key=lambda g: g.length)
                P = np.asarray(L_.segmentize(1.0).coords)
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
        pin = (c.get("terre_plein") or {}).get("pin")
        if pin:
            obstacles = np.vstack([obstacles, np.asarray(pin["xy"])[None]])
        # balisage : piquets et rubalise
        lignes_b, mb = (balisage(cfg["balisage_par_defaut"], rg, ferm_pk, obstacles, ruban, z_de, ref) if ferm_pk
                        else ([], {"piquet": [], "piquet_tete": [], "rubalise": []}))
        for k, v in mb.items():
            if v:
                m_bal.append(m11.fusion(v, f"balisage_{cle}_{k}", k))
        if mb["piquet"]:
            m_bcoll.append(m11.fusion(mb["piquet"], f"piquets_{cle}", "plastique_piquet"))
        for b in lignes_b:
            lignes_csv.append({**b, "carrefour": nom})
        # geojson WGS84
        to_wgs = lambda g: shapely.ops.transform(lambda x, y, z=None: TO_WGS.transform(x, y), g)   # noqa: E731
        for g, typ, rq in ((revetu, "surface revêtue annexe : " + "; ".join(s_["nom"] for s_ in c.get("surfaces_revetues", [])),
                            "TSD+ (asphalte), à appliquer dans 09"),
                           (terre, "terre-plein", "DBK+ (terre), à appliquer dans 09")):
            for gg in ([] if g.is_empty else getattr(g, "geoms", [g])):
                feats.append({"type": "Feature", "geometry": mapping(to_wgs(gg)),
                              "properties": {"carrefour": nom, "type": typ, "surface_m2": round(gg.area, 1), "code_surface_jeu_propose": rq}})
        for nom_p, P, typ in parapets_plan:
            feats.append({"type": "Feature", "geometry": mapping(to_wgs(LineString(P))),
                          "properties": {"carrefour": nom, "type": f"parapet ({typ})", "nom": nom_p}})
        rapport[nom] = {"fermetures_pk": [(n_, s0, s1) for n_, s0, s1 in ferm_pk],
                        "enrobe_ferme_m2": round(revetu.area, 1), "terre_plein_m2": round(terre.area, 1),
                        "aire_triangulee_m2": {"enrobe": round(aire_enr, 1), "terre": round(aire_ter, 1)},
                        "balisage": {k: sum(1 for b in lignes_b if b["type"] == k) for k in ("piquet de rubalise", "rubalise")},
                        "_ctx": (ruban, lignes3, revetu, terre, parapets_int, lignes_b, c, parapets_plan, panneaux, cle)}

    # --- constructions de la zone de départ (zone_depart.json) : ajoutées au décor et à la physique des annexes
    deco_d, coll_d, bilan_d, _ = constructions_depart(ch, mnt, ref)
    m_ann += deco_d
    m_coll += coll_d

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
                "rubalise": {"color": [0.85, 0.1, 0.08], "rough": 0.5}, **ZD_MATIERES}
        m11.ecrire_glb(dossier / "annexes.glb", m_ann, mats)
        m11.ecrire_glb(dossier / "balisage.glb", m_bal, mats)
        if version == "complet":
            mc = {"enrobe": {"color": [0.3, 0.3, 0.3]}, "terre": {"color": [0.47, 0.39, 0.29]}, "pierre": {"color": [0.6, 0.58, 0.54]},
                  "plastique_piquet": {"color": [0.92, 0.92, 0.92]}, **ZD_COLLISION}
            m11.ecrire_glb(dossier / "annexes_collision.glb", m_coll, mc)
            m11.ecrire_glb(dossier / "balisage_collision.glb", m_bcoll, mc)
    for f in ("balisage_collision.glb",):                   # le balisage n'a plus de barrières
        if not m_bcoll and (MOD / f).exists():
            (MOD / f).unlink()
    ctx = {}
    for k_, (nom, d) in enumerate(rapport.items()):
        ruban, lignes3, revetu, terre, parapets_int, lignes_b, c, parapets_plan, panneaux, cle = d.pop("_ctx")
        ctx[nom] = (ruban, revetu, terre)
        d["controle"] = {v: controle(ref, ruban, lignes3, revetu, terre, parapets_int, lignes_b, MOD if v == "complet" else MOD / "apercu",
                                     len(d["fermetures_pk"])) for v in m11.VERSIONS}
        FIG4.mkdir(parents=True, exist_ok=True)
        plan_figure(c, ch, ruban, revetu, terre, parapets_plan, panneaux, lignes3[:len(d["fermetures_pk"])], lignes_b,
                    FIG4 / ("carrefour_plan.png" if k_ == 0 else f"carrefour_plan_{cle}.png"), d["fermetures_pk"])
    rapport["constructions_zone_depart"] = bilan_d
    # obstacles (parapets, panneaux, piquets) sur la chaussée de la spéciale, sur tout le parcours
    XYo = []
    for f in ("annexes_collision.glb", "balisage_collision.glb"):
        if (MOD / f).exists():
            for nm, pp, _, _, _ in m11.lire_glb(MOD / f):
                if not nm.startswith(("enrobe", "terre")):
                    pp = pp.astype(np.float64)
                    XYo.append(np.column_stack([pp[:, 0] + ref["x0"], ref["y0"] - pp[:, 2]]))
    sur = m11.obstacles_sur_chaussee(np.vstack(XYo), ch) if XYo else []
    rapport["obstacles_sur_la_chaussee"] = {"sommets": len(sur), "profondeur_max_m": max([q for _, q in sur], default=0.0),
                                            "pk": sorted({p_ for p_, _ in sur})[:20]}
    print(json.dumps(rapport, ensure_ascii=False, indent=1))

    # --- rendus déclarés dans le JSON (plongeante au-dessus des surfaces, ou vue conducteur par PK)
    vues = []
    for c in actifs:
        ruban, revetu, terre = ctx[c["nom"]]
        for v in c.get("rendus", []):
            if v["type"] == "plongeante":
                ctr = np.array(shapely.union_all([revetu, terre]).centroid.coords[0])
                zc = float(mnt.z(ctr[:1], ctr[1:])[0])
                i0 = int(np.argmin(np.hypot(*(ch["A"][:, :2] - ctr).T)))
                A2 = ch["A"][[max(i0 - 15, 0), min(i0 + 15, len(ch["pk"]) - 1)], :2]
                dirv = (A2[1] - A2[0]) / np.linalg.norm(A2[1] - A2[0])
                lat = np.array([dirv[1], -dirv[0]])
                eye = np.array([[*(ctr - v.get("recul_m", 30) * dirv + v.get("lateral_m", 0) * lat), zc + v.get("hauteur_m", 40)]])
                vues.append((v["nom"], m08.to_gltf(eye, ref)[0], m08.to_gltf(np.array([[*ctr, zc]]), ref)[0], v.get("fov", 50)))
            else:
                eye = rg.point(np.array([float(v["pk"])]), v.get("decalage_m", 1.6), 1.3)
                cible = rg.point(np.array([float(v["regard_pk"])]), v.get("regard_decalage_m", 0.0), 0.8)
                vues.append((v["nom"], m08.to_gltf(eye, ref)[0], m08.to_gltf(cible, ref)[0], v.get("fov", 70)))
    if vues:
        fichiers = [MOD / "terrain.glb", MOD / "route_habillee.glb", MOD / "ouvrages.glb", MOD / "annexes.glb", MOD / "balisage.glb"]
        print("rendus :", rendus(vues, [f for f in fichiers if f.exists()], prefixe="carrefour"))
    print(f"durée : {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
