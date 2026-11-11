"""Étape 12 - Carrefours : voies non empruntées par la spéciale, îlot et balisage de fermeture.

Au carrefour du Lion d'Or, la chaussée de la spéciale (07, zone 2 des corrections) suit la
branche de gauche ; son bord droit y est une ligne de fermeture qui barre la branche de
droite et l'embouchure de la D1 nord. Ce script modélise l'enrobé réel au-delà de cette ligne,
l'îlot de la patte d'oie et le balisage qui ferme les branches.

Entrées : data/reference/carrefours_annexes.json (un objet par carrefour : fenêtre, germes,
          lignes de coupe, amorces de voies, îlot, segments de fermeture, balisage),
          data/processed/chaussee_precise.csv, couloir/troncon_de_route.geojson (axe des amorces),
          data/raw/mnt_lidarhd_50cm.tif, modele/repere.json, modele/ouvrages_collision.glb (parapets)
Méthode : surface revêtue = région plane et lisse du MNT (pente < seuil sur le MNT lissé 0,5 m,
          rugosité locale < seuil : écart-type du MNT autour de sa moyenne sur ~0,75 m) connexe aux
          germes, bornée par la fenêtre et les lignes de coupe, moins la chaussée de la spéciale
          et l'îlot ; contour lissé (ouverture / fermeture de ~0,5 m) puis recollé exactement au
          bord droit de la chaussée le long des segments de fermeture. Altitudes : MNT, recalé
          sur 2 m vers l'altitude du bord de chaussée (raccord sans marche), +3 cm ailleurs pour
          passer au-dessus du terrain de 08 (qui n'est pas troué sous les annexes).
          Îlot : bosse du MNT au-dessus d'un plan ajusté sur ses abords.
Sorties : data/processed/annexes_revetues.geojson (WGS84), data/processed/balisage.csv,
          modele/annexes.glb, annexes_collision.glb, balisage.glb, balisage_collision.glb,
          modele/apercu/{annexes,balisage}.glb, figures/phase4/carrefour_*.png
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
import rasterio
import rasterio.features
import shapely
import shapely.ops
from PIL import Image
from rasterio.windows import from_bounds
from scipy import ndimage
from scipy.spatial import Delaunay, cKDTree
from shapely.geometry import LineString, Polygon, box, mapping

from acr_geo import FIG, OUT, RAW, REF, ROOT, TO_WGS, l93, write_geojson

_spec = importlib.util.spec_from_file_location("route_ouvrages", Path(__file__).with_name("11_route_ouvrages.py"))
m11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m11)
m08 = m11.m08

MOD = ROOT / "modele"
FIG4 = FIG / "phase4"
RACCORD = 2.0        # m : recalage du MNT sur l'altitude du bord de chaussée
SURELEV = 0.03       # m : annexes au-dessus du MNT (hors raccord) pour couvrir le terrain de 08
PAS_INT = 1.0        # m : maille intérieure des annexes
PAS_BORD = 0.5       # m : échantillonnage des contours
BORDURE = 0.15       # m : largeur de la bordure de l'îlot


# --- géométrie de la chaussée de la spéciale ---------------------------------------------
def ruban_poly(ch, pk0, pk1):
    """Emprise exacte du ruban (union des quadrilatères gauche-axe et axe-droite de chaque maille)."""
    i = np.flatnonzero((ch["pk"] >= pk0) & (ch["pk"] <= pk1))
    quads = []
    for a, b in zip(i[:-1], i[1:]):
        for P, Q in ((ch["G"], ch["A"]), (ch["A"], ch["D"])):
            q = Polygon([P[a, :2], P[b, :2], Q[b, :2], Q[a, :2]])
            quads.append(q if q.is_valid else shapely.make_valid(q))
    return shapely.union_all(quads)


def bord_3d(rg, s0, s1, cote="droite", pas=0.5):
    s = m11.echant(s0, s1, pas)
    E, n = rg.bord(s, cote)
    return s, E, n


# --- lignes de coupe -----------------------------------------------------------------------
def amorce(cfg_a, ruban):
    """Coupe perpendiculaire à l'axe BD TOPO de la voie, à longueur_m du point de départ."""
    g = json.loads((OUT / "couloir" / "troncon_de_route.geojson").read_text(encoding="utf-8"))
    lignes = []
    for f in g["features"]:
        if f["properties"].get("cpx_numero") != cfg_a["troncon_bdtopo"]:
            continue
        c = f["geometry"]["coordinates"]
        c = c[0] if f["geometry"]["type"] != "LineString" else c
        lignes.append(np.array([l93(*p[:2]) for p in c]))
    dep = np.array(cfg_a["depart"])
    chaine, bout, utilises = None, dep, set()
    for _ in range(10):                     # on enchaîne les tronçons qui partent du bout courant
        cand = []
        for k, L in enumerate(lignes):
            if k in utilises:
                continue
            for P in (L, L[::-1]):
                if np.hypot(*(P[0] - bout)) < 1.0:
                    cand.append((k, P))
        if chaine is None:                  # au départ : la branche qui s'éloigne de la spéciale
            cand = [(k, P) for k, P in cand
                    if LineString(P).interpolate(min(15, LineString(P).length - 0.1)).distance(ruban) > 3]
        if not cand:
            break
        k, P = cand[0]
        utilises.add(k)
        chaine = P if chaine is None else np.vstack([chaine, P[1:]])
        bout = chaine[-1]
        if LineString(chaine).length >= cfg_a["longueur_m"]:
            break
    if chaine is None:
        raise SystemExit(f"amorce {cfg_a['nom']} : aucun tronçon {cfg_a['troncon_bdtopo']} au départ")
    L = LineString(chaine)
    s = min(cfg_a["longueur_m"], L.length)
    p, q = np.array(L.interpolate(s).coords[0]), np.array(L.interpolate(max(s - 2, 0)).coords[0])
    t = (p - q) / np.linalg.norm(p - q)
    n = np.array([-t[1], t[0]]) * cfg_a["largeur_coupe_m"] / 2
    return LineString([p - n, p + n]), L


def lignes_de_coupe(c, rg, ruban):
    out, axes = [], []
    for lc in c.get("lignes_de_coupe", []):
        if "points" in lc:
            out.append(LineString(lc["points"]))
        else:
            E, n = rg.bord(np.array([float(lc["pk"])]), lc["cote"])
            out.append(LineString([E[0, :2] - 0.5 * n[0], E[0, :2] + lc["longueur_m"] * n[0]]))
    for a in c.get("amorces", []):
        coupe, axe = amorce(a, ruban)
        out.append(coupe)
        axes.append((a["nom"], axe))
    return out, axes


# --- îlot ----------------------------------------------------------------------------------
def ilot(c, mnt_a, tr):
    """Bosse du MNT au-dessus d'un plan ajusté sur un anneau de 0,5 à 3 m autour de la boîte."""
    x0, y0, x1, y1 = c["ilot"]["boite"]
    rows, cols = np.indices(mnt_a.shape)
    px, py = rasterio.transform.xy(tr, rows.ravel(), cols.ravel())
    px, py, z = np.asarray(px), np.asarray(py), mnt_a.ravel()
    b = box(x0, y0, x1, y1)
    dans = shapely.contains_xy(b, px, py)
    anneau = shapely.contains_xy(b.buffer(3), px, py) & ~shapely.contains_xy(b.buffer(0.5), px, py)
    M = np.column_stack([px[anneau], py[anneau], np.ones(anneau.sum())])
    coef = np.linalg.lstsq(M, z[anneau], rcond=None)[0]
    plan = lambda x, y: coef[0] * x + coef[1] * y + coef[2]           # noqa: E731
    bosse = z - plan(px, py)
    sel = dans & (bosse > c["ilot"]["seuil_bosse_m"])
    carres = [box(x - 0.25, y - 0.25, x + 0.25, y + 0.25) for x, y in zip(px[sel], py[sel])]
    P = shapely.union_all(carres).buffer(0.2).buffer(-0.2)
    if P.geom_type != "Polygon":
        P = max(P.geoms, key=lambda g: g.area)
    P = P.convex_hull.simplify(0.15)
    h = float(np.clip(np.median(bosse[sel]), 0.08, 0.3))
    return P, h, plan, {"surface_m2": round(P.area, 1), "hauteur_m": round(h, 2), "pixels": int(sel.sum()),
                        "bosse_max_m": round(float(bosse[sel].max()), 2)}


# --- surfaces revêtues --------------------------------------------------------------------
def region(c, mnt_a, tr, ruban, ilot_p, coupes, fermetures):
    rows, cols = np.indices(mnt_a.shape)
    px, py = (np.asarray(v).reshape(mnt_a.shape) for v in rasterio.transform.xy(tr, rows.ravel(), cols.ravel()))
    zs = ndimage.gaussian_filter(mnt_a, 1.0)
    gy, gx = np.gradient(zs, -tr.e, tr.a)
    pente = np.degrees(np.arctan(np.hypot(gx, gy)))
    x0, y0, x1, y1 = c["fenetre"]
    res = mnt_a - ndimage.gaussian_filter(mnt_a, 1.5)
    rugo = np.sqrt(ndimage.gaussian_filter(res ** 2, 1.5))             # l'enrobé est lisse, le sous-bois non
    m = (pente < c["pente_max_deg"]) & (rugo < c["rugosite_max_m"]) & (px > x0) & (px < x1) & (py > y0) & (py < y1)
    m &= ~shapely.contains_xy(ruban, px, py)
    m &= ~shapely.contains_xy(ilot_p.buffer(0.1), px, py)
    for L in coupes:
        m &= shapely.distance(L, shapely.points(px, py)) > 0.6
    m = ndimage.binary_opening(m, np.ones((3, 3)))                   # coupe les fuites d'un pixel

    def garde(mm):
        lab, _ = ndimage.label(mm)
        ids = set()
        for gx_, gy_ in c["germes"]:
            r, k = rasterio.transform.rowcol(tr, gx_, gy_)
            win = lab[max(r - 6, 0):r + 7, max(k - 6, 0):k + 7]
            if (win > 0).any():
                ids.add(int(np.bincount(win[win > 0]).argmax()))
        return np.isin(lab, list(ids))

    m = ndimage.binary_fill_holes(garde(m))
    polys = [shapely.geometry.shape(g) for g, v in rasterio.features.shapes(m.astype(np.uint8), mask=m, transform=tr) if v]
    P = shapely.union_all(polys)
    L = c["lissage_m"]
    P = P.buffer(L).buffer(-2 * L).buffer(L).simplify(0.1)           # fermeture puis ouverture ~0,5 m
    # embouchures : au moins profondeur_min_m d'enrobé derrière chaque ligne de fermeture, là où le
    # sol est praticable (pente < pente_embouchure_deg), puis recollage exact au bord de chaussée
    lache = ndimage.binary_opening((pente < c["pente_embouchure_deg"]) & ~shapely.contains_xy(ruban, px, py), np.ones((3, 3)))
    Pl = shapely.union_all([shapely.geometry.shape(g) for g, v in
                            rasterio.features.shapes(lache.astype(np.uint8), mask=lache, transform=tr) if v])
    band = shapely.union_all([LineString(f[:, :2]).offset_curve(-c["profondeur_min_m"] / 2).buffer(
        c["profondeur_min_m"] / 2 + 0.3, cap_style="flat") for f in fermetures])
    P = shapely.union_all([P, band.intersection(Pl.buffer(0.3))]).buffer(L).buffer(-L)
    P = P.difference(ruban).difference(ilot_p).intersection(box(x0, y0, x1, y1))
    for Lc in coupes:
        P = P.difference(Lc.buffer(0.01))
    parts = [g for g in getattr(P, "geoms", [P]) if g.area >= c["surface_min_m2"]]
    return shapely.union_all(parts), float((m.sum()) * abs(tr.a * tr.e))


def aire_plan(XY, tri):
    u, v = XY[tri[:, 1]] - XY[tri[:, 0]], XY[tri[:, 2]] - XY[tri[:, 0]]
    return np.abs(u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]) / 2


def maillage_surface(P, z_de, ref, mat, name, uv_s=m11.S_ENROBE):
    """Triangulation : contours tous les 0,5 m + grille de 1 m à l'intérieur ; normales vers le haut."""
    bords = []
    for g in getattr(P, "geoms", [P]):
        for ring in [g.exterior, *g.interiors]:
            bords.append(np.asarray(ring.segmentize(PAS_BORD).coords)[:-1, :2])
    B = np.vstack(bords)
    x0, y0, x1, y1 = P.bounds
    gx, gy = np.meshgrid(np.arange(np.floor(x0), x1, PAS_INT), np.arange(np.floor(y0), y1, PAS_INT))
    G = np.column_stack([gx.ravel(), gy.ravel()])
    pts = shapely.points(G)
    G = G[shapely.contains(P, pts) & (shapely.distance(P.boundary, pts) > 0.35)]
    XY = np.unique(np.round(np.vstack([B, G]), 4), axis=0)
    tri = Delaunay(XY - XY.mean(0)).simplices        # centré : en Lambert-93 brut, qhull perd des points
    cen = XY[tri].mean(1)
    Pp = P.buffer(1e-6)
    shapely.prepare(Pp)
    tri = tri[shapely.contains_xy(Pp, cen[:, 0], cen[:, 1]) & (aire_plan(XY, tri) > 1e-4)]
    used, inv = np.unique(tri, return_inverse=True)
    XY, tri = XY[used], inv.reshape(-1, 3)
    Z = z_de(XY)
    pos = m08.to_gltf(np.column_stack([XY, Z]), ref).astype(np.float64)
    tri = m11.oriente(pos, tri, np.array([0.0, 1.0, 0.0])).astype(np.uint32)
    uv = (XY - np.floor(XY.min(0))) / uv_s
    aire_mesh = float(aire_plan(XY, tri).sum())
    return {"name": name, "pos": pos.astype(np.float32), "nrm": m08.normales(pos, tri), "uv": uv.astype(np.float32),
            "idx": tri, "mat": mat}, aire_mesh


def altitude_annexes(mnt, fermetures):
    """z(x, y) des annexes : MNT, raccordé sur RACCORD m à l'altitude du bord de chaussée le
    long des fermetures (exactement sur la ligne), SURELEV au-dessus du MNT au-delà de 0,5 m."""
    lignes = [(LineString(f[:, :2]), np.concatenate([[0], np.cumsum(np.hypot(*np.diff(f[:, :2], axis=0).T))]), f[:, 2])
              for f in fermetures]

    def z(XY):
        XY = np.asarray(XY, float)
        zm = mnt.z(XY[:, 0], XY[:, 1])
        best_d = np.full(len(XY), np.inf)
        dz = np.zeros(len(XY))
        pts = shapely.points(XY)
        for L, cum, ze in lignes:
            d = shapely.distance(L, pts)
            s = shapely.line_locate_point(L, pts)
            q = shapely.line_interpolate_point(L, s)
            qx, qy = shapely.get_x(q), shapely.get_y(q)
            dze = np.interp(s, cum, ze) - mnt.z(qx, qy)
            better = d < best_d
            best_d[better], dz[better] = d[better], dze[better]
        w = np.clip(1 - best_d / RACCORD, 0, 1)
        return zm + w * dz + SURELEV * np.clip(best_d / 0.5, 0, 1)
    return z


# --- îlot : volume --------------------------------------------------------------------------
def pave(c, axe, L, W, z0, z1, ref):
    """Pavé centré en c (x, y), long de L selon axe (unitaire 2D), large de W, de z0 à z1."""
    t = np.asarray(axe, float) / np.linalg.norm(axe)
    n = np.array([-t[1], t[0]])
    a, b = np.asarray(c) - t * L / 2, np.asarray(c) + t * L / 2
    P = np.array([a, b])
    co = lambda o, z: np.column_stack([P + o * n, np.full(2, z)])     # noqa: E731
    return m11.boite([co(-W / 2, z0), co(W / 2, z0), co(W / 2, z1), co(-W / 2, z1)], ref)


def maillage_ilot(P, h, plan, ref, vers_trafic, cfg_p, mnt):
    """Îlot : murs de bordure, dessus (bordure de BORDURE m puis terre), poteau et panneaux.
    La terre suit le MNT (+3 cm) là où il dépasse la bordure, pour couvrir le terrain de 08."""
    ring = np.asarray(P.exterior.segmentize(0.3).coords)[:-1]
    if Polygon(ring).exterior.is_ccw is False:
        ring = ring[::-1]
    zb = plan(ring[:, 0], ring[:, 1])
    bas = np.column_stack([ring, zb - 0.05])
    haut = np.column_stack([ring, zb + h])
    n = len(ring)
    pos = np.vstack([bas, haut])
    i = np.arange(n)
    j = (i + 1) % n
    tri = np.vstack([np.column_stack([i, j, n + j]), np.column_stack([i, n + j, n + i])])
    cen = np.asarray(P.centroid.coords[0])
    gp = m08.to_gltf(pos, ref).astype(np.float64)
    mid = (gp[tri[:, 0]] + gp[tri[:, 2]]) / 2 - m08.to_gltf(np.array([[*cen, plan(*cen)]]), ref)[0]
    mid[:, 1] = 0
    tri = m11.oriente(gp, tri, mid)
    long_ = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(ring, axis=0).T))])
    murs = {"pos": gp.astype(np.float32), "nrm": m08.normales(gp, tri),
            "uv": np.column_stack([np.tile(long_, 2), np.repeat([0, h + 0.05], n)]) / 1.0, "idx": tri.astype(np.uint32)}
    # dessus
    inner = P.buffer(-BORDURE)
    pts = [ring] + ([np.asarray(inner.exterior.segmentize(0.3).coords)[:-1]] if not inner.is_empty else [])
    x0, y0, x1, y1 = P.bounds
    gx, gy = np.meshgrid(np.arange(x0, x1, 0.5), np.arange(y0, y1, 0.5))
    G = np.column_stack([gx.ravel(), gy.ravel()])
    G = G[shapely.contains_xy(inner.buffer(-0.15), G[:, 0], G[:, 1])] if not inner.is_empty else G[:0]
    XY = np.vstack(pts + [G])
    t2 = Delaunay(XY - XY.mean(0)).simplices
    cc = XY[t2].mean(1)
    t2 = t2[shapely.contains_xy(P.buffer(1e-6), cc[:, 0], cc[:, 1]) & (aire_plan(XY, t2) > 1e-4)]
    terre = shapely.contains_xy(inner.buffer(1e-6), *XY[t2].mean(1).T) if not inner.is_empty else np.zeros(len(t2), bool)
    out = {}
    for nom, sel in (("ilot_terre", terre), ("bordure", ~terre)):
        tt = t2[sel]
        used, inv = np.unique(tt, return_inverse=True)
        q = XY[used]
        zt = plan(q[:, 0], q[:, 1]) + h
        if nom == "ilot_terre":
            zt = np.maximum(zt, mnt.z(q[:, 0], q[:, 1]) + SURELEV)
        p3 = m08.to_gltf(np.column_stack([q, zt]), ref).astype(np.float64)
        tt = m11.oriente(p3, inv.reshape(-1, 3), np.array([0.0, 1.0, 0.0]))
        out[nom] = {"pos": p3.astype(np.float32), "nrm": m08.normales(p3, tt), "uv": (q - q.min(0)).astype(np.float32),
                    "idx": tt.astype(np.uint32)}
    # poteau et panneaux directionnels (face au trafic qui arrive de la D3D)
    rp = np.asarray(P.representative_point().coords[0])
    zb0 = float(plan(*rp)) + h
    face = np.asarray(vers_trafic, float)
    face /= np.linalg.norm(face)
    lat = np.array([-face[1], face[0]])
    H = cfg_p["hauteur_m"]
    poteau = pave(rp, face, 0.08, 0.08, zb0 - 0.05, zb0 + H, ref)
    panneaux = [pave(rp + lat * 0.3, lat, 1.1, 0.04, zb0 + H - 0.35 - 0.4 * k - 0.25, zb0 + H - 0.35 - 0.4 * k, ref)
                for k in range(cfg_p["nombre"])]
    return murs, out["bordure"], out["ilot_terre"], poteau, panneaux


# --- balisage -------------------------------------------------------------------------------
def balisage(c, cfg_b, rg, fermetures_pk, ilot_p, ruban, parapets_xy, z_de, ref):
    """Rubalise sur piquets au premier rang, barrières derrière, le long des segments de fermeture,
    sauf là où l'îlot ou un parapet ferme déjà."""
    rb, br = cfg_b["rubalise"], cfg_b["barriere"]
    dmin = cfg_b["distance_min_ilot_parapet_m"]
    arbre = cKDTree(parapets_xy) if len(parapets_xy) else None

    def libre(P):
        ok = shapely.distance(ilot_p, shapely.points(P)) > dmin
        if arbre is not None:
            ok &= arbre.query(P)[0] > dmin
        return ok & ~shapely.contains_xy(ruban.buffer(0.3), P[:, 0], P[:, 1])

    def cap(t):
        return float(np.degrees(np.arctan2(t[0], t[1])) % 360)

    lignes, meshes = [], {"piquet": [], "piquet_tete": [], "rubalise": [], "barriere_rouge": [], "barriere_blanche": []}
    for f in fermetures_pk:
        s = m11.echant(f["pk_debut"], f["pk_fin"], 0.25)
        E, n = rg.bord(s, "droite")
        for kind, d in (("rubalise", rb["decalage_bord_m"]), ("barriere", br["decalage_bord_m"])):
            Q = E[:, :2] + n * d
            cum = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(Q, axis=0).T))])
            pas = rb["pas_poteaux_m"] if kind == "rubalise" else br["longueur_element_m"]
            m_ = max(int(np.floor(cum[-1] / pas)), 1)
            marge = (cum[-1] - m_ * pas) / 2
            if kind == "rubalise":
                at = marge + np.arange(m_ + 1) * pas
            else:
                at = marge + pas / 2 + np.arange(m_) * pas
            P = np.column_stack([np.interp(at, cum, Q[:, 0]), np.interp(at, cum, Q[:, 1])])
            T = np.column_stack([np.interp(at + 0.3, cum, Q[:, 0]) - np.interp(at - 0.3, cum, Q[:, 0]),
                                 np.interp(at + 0.3, cum, Q[:, 1]) - np.interp(at - 0.3, cum, Q[:, 1])])
            T /= np.linalg.norm(T, axis=1, keepdims=True)
            ok = libre(P)
            Z = z_de(P)
            for k in np.flatnonzero(ok):
                if kind == "rubalise":
                    lignes.append({"type": "piquet de rubalise", "xy": P[k], "z": Z[k], "cap": cap(T[k]), "L": 0.0,
                                   "famille": rb["famille_jeu"], "maillage": rb["maillage_jeu"], "f": f["nom"]})
                    meshes["piquet"].append(pave(P[k], T[k], 0.04, 0.04, Z[k] - 0.05, Z[k] + rb["hauteur_m"], ref))
                    meshes["piquet_tete"].append(pave(P[k], T[k], 0.05, 0.05, Z[k] + rb["hauteur_m"] - 0.15,
                                                      Z[k] + rb["hauteur_m"] + 0.02, ref))
                    if k + 1 < len(P) and ok[k + 1]:
                        c_, d_ = (P[k] + P[k + 1]) / 2, P[k + 1] - P[k]
                        L = float(np.linalg.norm(d_))
                        zc = (Z[k] + Z[k + 1]) / 2 + rb["hauteur_m"] - 0.1
                        lignes.append({"type": "rubalise", "xy": c_, "z": zc, "cap": cap(d_ / L), "L": L,
                                       "famille": rb["famille_jeu"], "maillage": rb["acteur_ruban_jeu"], "f": f["nom"]})
                        meshes["rubalise"].append(pave(c_, d_, L, 0.01, zc - 0.035, zc + 0.035, ref))
                else:
                    lignes.append({"type": "barrière", "xy": P[k], "z": Z[k], "cap": cap(T[k]), "L": pas,
                                   "famille": br["famille_jeu"], "maillage": br["maillage_jeu"], "f": f["nom"],
                                   "alt": br["alternative_jeu"]})
                    coul = "barriere_rouge" if k % 2 == 0 else "barriere_blanche"
                    meshes[coul].append(pave(P[k], T[k], pas - 0.05, br["epaisseur_m"], Z[k] - 0.05, Z[k] + br["hauteur_m"], ref))
    return lignes, meshes


# --- contrôles -------------------------------------------------------------------------------
def controle(ch, ref, rg, c, ruban, fermetures, annexe_p, ilot_p, lignes_b, version_dir):
    r = {}
    for f in ("annexes.glb", "annexes_collision.glb", "balisage.glb", "balisage_collision.glb"):
        p = version_dir / f
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
                "triangles": int(sum(len(m[4]) for m in ms)),
                "nan": bool(np.isnan(pos).any() or np.isnan(nrm).any()),
                "faces_dans_le_sens_des_normales_pct": round(float(np.concatenate(acc).mean() * 100), 2),
                "bornes_min": np.round(pos.min(0), 1).tolist(), "bornes_max": np.round(pos.max(0), 1).tolist()}
        surf = [m for m in ms if m[0].startswith(("annexe", "ilot_dessus"))]
        if surf:
            up = []
            for _, pp, _, _, t in surf:
                fn = np.cross(pp[t[:, 1]] - pp[t[:, 0]], pp[t[:, 2]] - pp[t[:, 0]])
                up.append(fn[:, 1] > 0)
            r[f]["surfaces_normales_vers_le_haut_pct"] = round(float(np.concatenate(up).mean() * 100), 2)
        if f == "annexes.glb":
            _, pp, _, _, t = next(m for m in ms if m[0].startswith("annexe"))
            pp = pp.astype(np.float64)                     # avant d'ajouter l'origine (float32 : 6 cm à 900 km)
            XY = np.column_stack([pp[:, 0] + ref["x0"], ref["y0"] - pp[:, 2]])
            Zv = pp[:, 1] + ref["z0"]
            # sommets posés sur une ligne de fermeture : écart à l'altitude du bord de chaussée
            ecarts, couvert = [], []
            for F in fermetures:
                L = LineString(F[:, :2])
                cum = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(F[:, :2], axis=0).T))])
                pts = shapely.points(XY)
                d = shapely.distance(L, pts)
                on = d < 0.01
                ecarts.append(Zv[on] - np.interp(shapely.line_locate_point(L, pts[on]), cum, F[:, 2]))
                # couverture : points à 0,2 m au-delà du bord, hors îlot
                s = np.arange(0.5, L.length - 0.5, 0.5)
                q = np.array([L.interpolate(x).coords[0] for x in s])
                tg = np.gradient(q, axis=0)
                nrm_ = np.column_stack([tg[:, 1], -tg[:, 0]]) / np.linalg.norm(tg, axis=1, keepdims=True)
                q2 = q + 0.2 * nrm_
                hors_ilot = shapely.distance(ilot_p, shapely.points(q2)) > 0.3
                couvert.append(shapely.contains_xy(annexe_p.buffer(1e-3), q2[hors_ilot, 0], q2[hors_ilot, 1]))
            e = np.concatenate(ecarts)
            # triangles d'annexe sous la chaussée de la spéciale
            tris = shapely.polygons(XY[t])
            sous = float(shapely.area(shapely.intersection(tris, ruban.buffer(-0.01))).sum())
            r[f]["raccord_fermeture"] = {"sommets_sur_la_ligne": int(len(e)),
                                         "ecart_vertical_max_m": round(float(np.abs(e).max()), 4) if len(e) else None,
                                         "bord_couvert_a_0_2_m_pct": round(float(np.concatenate(couvert).mean() * 100), 1)}
            r[f]["aire_sous_la_chaussee_m2"] = round(sous, 3)
    if lignes_b:
        P = np.array([b["xy"] for b in lignes_b])
        d = shapely.distance(ruban, shapely.points(P))
        r["balisage_distance_min_a_la_chaussee_m"] = round(float(d.min()), 2)
        r["balisage_distance_min_a_l_ilot_m"] = round(float(shapely.distance(ilot_p, shapely.points(P)).min()), 2)
    return r


# --- rendus ----------------------------------------------------------------------------------
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


# --- programme principal -----------------------------------------------------------------------
def main():
    t0 = time.time()
    cfg = json.loads((REF / "carrefours_annexes.json").read_text(encoding="utf-8"))
    ch = m08.chaussee()
    mnt = m08.MNT()
    ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    rg = m11.Rangs(ch)
    parapets_xy = np.zeros((0, 2))
    if (MOD / "ouvrages_collision.glb").exists():
        pp = np.vstack([m[1] for m in m11.lire_glb(MOD / "ouvrages_collision.glb")]).astype(np.float64)
        parapets_xy = np.column_stack([pp[:, 0] + ref["x0"], ref["y0"] - pp[:, 2]])

    m_ann, m_coll, m_bal, m_bcoll, feats, lignes_csv, rapport = [], [], [], [], [], [], {}
    actifs = [c for c in cfg["carrefours"] if c.get("actif")]
    for c in actifs:
        nom = c["nom"]
        cle = "".join(ch_ if ch_.isalnum() else "_" for ch_ in nom.lower())
        ruban = ruban_poly(ch, c["pk"][0] - 60, c["pk"][1] + 60)
        x0, y0, x1, y1 = c["fenetre"]
        with rasterio.open(RAW / "mnt_lidarhd_50cm.tif") as s:
            w = from_bounds(x0 - 5, y0 - 5, x1 + 5, y1 + 5, s.transform)
            a = s.read(1, window=w).astype(np.float64)
            tr = s.window_transform(w)
        ilot_p, h_ilot, plan, info_ilot = ilot(c, a, tr)
        fermetures = [bord_3d(rg, f["pk_debut"], f["pk_fin"])[1] for f in c["fermetures"]]
        coupes, axes = lignes_de_coupe(c, rg, ruban)
        P, aire_brute = region(c, a, tr, ruban, ilot_p, coupes, fermetures)
        z_de = altitude_annexes(mnt, fermetures)
        surf, aire_mesh = maillage_surface(P, z_de, ref, "enrobe", f"annexe_{cle}")
        m_ann.append(surf)
        m_coll.append({**surf, "name": f"annexe_{cle}_collision", "mat": "enrobe"})
        # îlot : vers le trafic = vers l'axe de la spéciale 15 m avant la première fermeture
        A0 = rg(np.array([c["fermetures"][0]["pk_debut"] - 15.0]))[0][0, :2]
        murs, bord, terre, poteau, panneaux = maillage_ilot(ilot_p, h_ilot, plan, ref,
                                                            A0 - np.asarray(ilot_p.centroid.coords[0]), c["ilot"]["panneaux"], mnt)
        m_ann += [{**murs, "name": f"ilot_{cle}_bordure_flancs", "mat": "bordure"},
                  {**bord, "name": f"ilot_dessus_{cle}_bordure", "mat": "bordure"},
                  {**terre, "name": f"ilot_dessus_{cle}_terre", "mat": "terre"},
                  {**m11.fusion([poteau], f"ilot_{cle}_poteau", "metal")},
                  {**m11.fusion(panneaux, f"ilot_{cle}_panneaux", "panneau")}]
        m_coll.append(m11.fusion([murs, bord, terre, poteau], f"ilot_{cle}_collision", "ilot_terre"))
        lignes_b, mb = balisage(c, cfg["balisage_par_defaut"], rg, c["fermetures"], ilot_p, ruban, parapets_xy, z_de, ref)
        for k, v in mb.items():
            if v:
                m_bal.append(m11.fusion(v, f"balisage_{cle}_{k}", k))
        coll_b = mb["barriere_rouge"] + mb["barriere_blanche"]
        if coll_b:
            m_bcoll.append(m11.fusion(coll_b, f"barrieres_{cle}", "plastique_barriere"))
        if mb["piquet"]:
            m_bcoll.append(m11.fusion(mb["piquet"], f"piquets_{cle}", "plastique_piquet"))
        for b in lignes_b:
            lignes_csv.append({**b, "carrefour": nom})
        # geojson WGS84
        to_wgs = lambda g: shapely.ops.transform(lambda x, y, z=None: TO_WGS.transform(x, y), g)   # noqa: E731
        for g in getattr(P, "geoms", [P]):
            feats.append({"type": "Feature", "geometry": mapping(to_wgs(g)),
                          "properties": {"carrefour": nom, "type": "surface revêtue annexe", "surface_m2": round(g.area, 1),
                                         "code_surface_jeu_propose": "TSD+ (asphalte), à appliquer dans 09"}})
        feats.append({"type": "Feature", "geometry": mapping(to_wgs(ilot_p)),
                      "properties": {"carrefour": nom, "type": "îlot", "surface_m2": round(ilot_p.area, 1),
                                     "hauteur_m": round(h_ilot, 2)}})
        for n_, L in axes:
            feats.append({"type": "Feature", "geometry": mapping(to_wgs(L)),
                          "properties": {"carrefour": nom, "type": f"axe BD TOPO de l'amorce {n_}"}})
        rapport[nom] = {"surface_revetue_m2": round(P.area, 1), "morceaux": len(getattr(P, "geoms", [P])),
                        "aire_triangulee_m2": round(aire_mesh, 1), "region_brute_m2": round(aire_brute, 1),
                        "ilot": info_ilot, "balisage": {k: sum(1 for b in lignes_b if b["type"] == k)
                                                        for k in ("piquet de rubalise", "rubalise", "barrière")},
                        "_ctx": (ruban, fermetures, P, ilot_p, lignes_b, c)}

    # --- écriture
    write_geojson(OUT / "annexes_revetues.geojson", feats, "annexes_revetues")
    with open(OUT / "balisage.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["carrefour", "fermeture", "x_l93", "y_l93", "z_m", "cap_deg", "type", "famille_jeu",
                     "maillage_jeu_propose", "longueur_supposee_m", "remarque"])
        for b in lignes_csv:
            rq = "dimensions du maillage du jeu inconnues ; cap = direction de l'alignement (0 = nord, sens horaire)"
            if b.get("alt"):
                rq += f" ; alternative : {b['alt']}"
            wr.writerow([b["carrefour"], b["f"], f"{b['xy'][0]:.2f}", f"{b['xy'][1]:.2f}", f"{b['z']:.2f}", f"{b['cap']:.1f}",
                         b["type"], b["famille"], b["maillage"], f"{b['L']:.2f}" if b["L"] else "", rq])
    for version, px in m11.VERSIONS.items():
        dossier = MOD if version == "complet" else MOD / "apercu"
        mats = {"enrobe": {"jpeg": m11.tex_enrobe(px), "rough": 0.92}, "bordure": {"color": [0.78, 0.77, 0.74], "rough": 0.85},
                "terre": {"color": [0.45, 0.38, 0.29], "rough": 1.0}, "metal": {"color": [0.6, 0.6, 0.62], "rough": 0.5},
                "panneau": {"color": [0.92, 0.92, 0.9], "rough": 0.6},
                "piquet": {"color": [0.92, 0.92, 0.92], "rough": 0.6}, "piquet_tete": {"color": [0.8, 0.08, 0.06], "rough": 0.6},
                "rubalise": {"color": [0.85, 0.1, 0.08], "rough": 0.5}, "barriere_rouge": {"color": [0.8, 0.08, 0.06], "rough": 0.5},
                "barriere_blanche": {"color": [0.93, 0.93, 0.93], "rough": 0.5}}
        m11.ecrire_glb(dossier / "annexes.glb", m_ann, mats)
        m11.ecrire_glb(dossier / "balisage.glb", m_bal, mats)
        if version == "complet":
            mc = {"enrobe": {"color": [0.3, 0.3, 0.3]}, "ilot_terre": {"color": [0.45, 0.38, 0.29]},
                  "plastique_barriere": {"color": [0.8, 0.08, 0.06]}, "plastique_piquet": {"color": [0.92, 0.92, 0.92]}}
            m11.ecrire_glb(dossier / "annexes_collision.glb", m_coll, mc)
            m11.ecrire_glb(dossier / "balisage_collision.glb", m_bcoll, mc)
    for nom, d in rapport.items():
        ruban, fermetures, P, ilot_p, lignes_b, c = d.pop("_ctx")
        d["controle"] = {v: controle(ch, ref, rg, c, ruban, fermetures, P, ilot_p, lignes_b, MOD if v == "complet" else MOD / "apercu")
                         for v in m11.VERSIONS}
    print(json.dumps(rapport, ensure_ascii=False, indent=1))

    # --- rendus (premier carrefour actif)
    if actifs:
        c = actifs[0]
        x0, y0, x1, y1 = c["fenetre"]
        ctr = np.array([[(x0 + x1) / 2, (y0 + y1) / 2]])
        zc = float(mnt.z(ctr[:, 0], ctr[:, 1])[0])
        A = rg(np.array([c["fermetures"][0]["pk_debut"] - 45.0, c["fermetures"][0]["pk_debut"] - 30.0,
                         c["fermetures"][0]["pk_fin"]]))[0]
        dirv = A[1, :2] - A[0, :2]
        dirv /= np.linalg.norm(dirv)
        lat = np.array([dirv[1], -dirv[0]])                    # à droite du sens de marche
        eye_h = np.array([[ctr[0, 0] - 25 * dirv[0] - 18 * lat[0], ctr[0, 1] - 25 * dirv[1] - 18 * lat[1], zc + 42]])
        conducteur = rg.point(np.array([c["fermetures"][0]["pk_debut"] - 40.0]), 1.6, 1.25)
        cible = rg.point(np.array([c["fermetures"][0]["pk_debut"] + 22.0]), 0.0, 0.5)
        vues = [("plongeante", m08.to_gltf(eye_h, ref)[0], m08.to_gltf(np.array([[ctr[0, 0], ctr[0, 1], zc]]), ref)[0], 50),
                ("conducteur_d3d", m08.to_gltf(conducteur, ref)[0], m08.to_gltf(cible, ref)[0], 60)]
        fichiers = [MOD / "terrain.glb", MOD / "route_habillee.glb", MOD / "ouvrages.glb", MOD / "annexes.glb",
                    MOD / "balisage.glb"]
        print("rendus :", rendus(vues, [f for f in fichiers if f.exists()]))
    print(f"durée : {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
