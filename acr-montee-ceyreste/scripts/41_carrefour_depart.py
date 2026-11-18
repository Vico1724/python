"""Carrefour du départ (Plan de Masse) : voie latérale, îlots, trottoir, marquage, panneaux, poteaux et lignes, coffrets,
potelets, végétation des jardins au-dessus du mur (cinquième passe, 19/11/2026).

Demande de l'utilisateur (mots exacts) : « les zones visibles doivent être vraiment bien faites » ; la zone de départ
(PK -150 à 100) est la plus vue. La planche figures/affinage/facades/depart_synthese_4_directions.jpg montrait, sur la
photo et pas dans le rendu : l'îlot et le trottoir en enrobé rouge à bordures, la voie latérale (Voie Romaine) et son
arrêt de bus (« BUS », zigzag jaune), les panneaux du carrefour, les poteaux et lignes aériennes, les coffrets, les
potelets, la végétation des jardins au-dessus du mur ; et un talus de terrain devant le mur de pierre.

Entrée : data/reference/depart_carrefour.json (relevé versionné ; chaque élément cite ses images Panoramax),
         modele/terrain.glb (08 ; les surfaces en suivent exactement les triangles, 3 cm au-dessus), MNT et MNS LiDAR HD.
Sorties :
  modele/depart.glb             décor : un maillage par élément et par matière (UV en mètres) ; lu par 15 (rendu de
                                contrôle), 16 (paquet Unreal, famille « depart », StartJunction/Meshes) et 33 (export neutre)
  modele/depart_collision.glb   surfaces de roulage (matière « enrobe_* » : sol TSD+ de 09) et obstacles (poteaux,
                                mâts : « beton », « cloture »), lus par 09
  data/processed/depart_bilan.json   ce qui est posé, compté, et ce qui est vu mais non posé
Terrain : le terrain plat jusqu'au pied du mur vient de scripts/aplanissements.py (lu par 08), qui lit le même relevé.
Usage :
  python scripts/41_carrefour_depart.py                 géométrie
  python scripts/41_carrefour_depart.py controle IMAGE CAP TANGAGE FOV [SORTIE]
        projette le relevé (contours, mâts, plaques, pied et hauteurs du mur) sur une vue du panorama IMAGE (cap
        Lambert-93 en degrés) : contrôle et calage des positions et des hauteurs (sortie non versionnée)
"""
from __future__ import annotations

import importlib.util
import json
import zlib
import math
import sys
from pathlib import Path

import numpy as np
import shapely
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from shapely.geometry import LineString, Point, Polygon

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from acr_geo import OUT, RAW, REF, ROOT  # noqa: E402


def _charger(nom, f):
    s = importlib.util.spec_from_file_location(nom, ICI / f)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


m37 = _charger("m37", "37_clotures.py")
m11, m08 = m37.m11, m37.m08
MOD = ROOT / "modele"
RELEVE = REF / "depart_carrefour.json"
SURELEV = 0.03           # m : surfaces au-dessus du terrain de 08 (comme 12)
PEINTURE = 0.012         # m : marquage au-dessus de sa surface
PIED = 0.3


def releve():
    R = json.loads(RELEVE.read_text(encoding="utf-8"))
    O = np.array(R["origine_l93"], float)
    return R, O


def L93(p, O):
    return np.asarray(p, float) + O


# ----------------------------------------------------------------------------------------------- emprises
def chaussee_ruban():
    ch = m08.chaussee()
    G, D = ch["G"][:, :2], ch["D"][:, :2]
    return ch, shapely.union_all(shapely.make_valid(shapely.polygons(
        [np.array([G[i], G[i + 1], D[i + 1], D[i], G[i]]) for i in range(len(G) - 1)])))


def pied_du_mur(R, O):
    return L93(R["mur"]["pied"], O)


def normale_route(P):
    """Normale horizontale au pied du mur, tournée vers la voie : le pied est donné du sud-ouest au nord-est, la voie est
    à sa gauche."""
    t = np.gradient(P, axis=0)
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
    return np.column_stack([-t[:, 1], t[:, 0]]), t


def trottoir_polygone(R, O):
    """Bande de largeur_m le long du pied du mur, côté voie, des sommets de_k à a_k du pied ; elle commence 5 cm sous le
    mur (pas de jour entre trottoir et mur)."""
    t = R["surfaces"]["trottoir"]
    P = pied_du_mur(R, O)[t["de_k"]:t["a_k"] + 1]
    n, _ = normale_route(P)
    A = P - n * 0.05
    B = P + n * t["largeur_m"]
    return Polygon(np.vstack([A, B[::-1]])), P, n


def emprise_voie(R, O):
    return shapely.make_valid(Polygon(L93(R["surfaces"]["voie_laterale"]["polygone"], O)))


def ilots(R, O):
    out = []
    for e in R["surfaces"]["ilots"]:
        peint = shapely.make_valid(Polygon(L93(e["contour_peint"], O)))
        out.append((e, peint, peint.buffer(-e["bande_peinte_m"], join_style=2)))
    return out


def plateformes():
    """Polygones (L93) des terrains ramenés au niveau de la voie, et polylignes de rupture (pied du mur) : lus par
    scripts/aplanissements.py."""
    if not RELEVE.exists():
        return []
    R, O = releve()
    P = pied_du_mur(R, O)
    voie = emprise_voie(R, O)
    return [{"nom": R["plateformes"][0]["nom"], "poly": voie, "rupture": P}]


# ----------------------------------------------------------------------------------------------- contrôle sur photo
class Camera:
    """Projection exacte de la vue sténopé de 40_facades.vue_pinhole (cap Lambert-93, tangage, champ horizontal)."""

    def __init__(self, r, cap_l93, tang, fov_h, W, H, m40):
        self.c = np.array([float(r["x_l93"]), float(r["y_l93"])])
        self.zc = m40.z_camera(r, m40.Relief() if not hasattr(m40, "_rel") else m40._rel)
        self.cap, self.t, self.W, self.H = math.radians(cap_l93), math.radians(tang), W, H
        self.f = (W / 2) / math.tan(math.radians(fov_h) / 2)

    def proj(self, X):
        X = np.atleast_2d(np.asarray(X, float))
        d = X[:, :2] - self.c
        right = d[:, 0] * math.cos(self.cap) - d[:, 1] * math.sin(self.cap)
        fwd = d[:, 0] * math.sin(self.cap) + d[:, 1] * math.cos(self.cap)
        up = X[:, 2] - self.zc
        f2 = fwd * math.cos(self.t) + up * math.sin(self.t)
        u2 = -fwd * math.sin(self.t) + up * math.cos(self.t)
        out = np.column_stack([self.f * right / f2 + self.W / 2, -self.f * u2 / f2 + self.H / 2])
        out[f2 < 0.3] = np.nan
        return out

    def sol(self, u, v, T, z_plus=0.0, dmax=80.0):
        """Point du sol (MNT + z_plus) vu au pixel (u, v) : relevé des positions sur la photo (pied d'un mât, trait peint)."""
        r_, u2, f = u - self.W / 2, -(v - self.H / 2), self.f
        fwd = f * math.cos(self.t) - u2 * math.sin(self.t)
        up = f * math.sin(self.t) + u2 * math.cos(self.t)
        hx = fwd * math.sin(self.cap) + r_ * math.cos(self.cap)
        hy = fwd * math.cos(self.cap) - r_ * math.sin(self.cap)
        nh = math.hypot(hx, hy)
        s = np.arange(0.3, dmax, 0.02)
        X, Y = self.c[0] + hx / nh * s, self.c[1] + hy / nh * s
        Z = self.zc + up / nh * s
        k = np.flatnonzero(Z <= T.z(X, Y) + z_plus)
        return None if not len(k) else np.array([X[k[0]], Y[k[0]]])


def lignes_controle(R, O, T):
    """Polylignes 3D (L93) du relevé, avec couleur et étiquette, pour le contrôle sur photo."""
    L = []
    zt = lambda P: T.z(*np.asarray(P)[:, :2].T)                     # noqa: E731
    P = pied_du_mur(R, O)
    nP, _ = normale_route(P)
    zP = T.z(*(P + nP * 0.8).T)
    for h, c in ((0.0, (255, 0, 0)), (1.0, (255, 120, 0)), (2.0, (255, 200, 0)), (3.0, (255, 255, 0))):
        L.append((np.column_stack([P, zP + h]), c, f"mur +{h:.0f}" if h else "pied du mur"))
    poly, _, _ = trottoir_polygone(R, O)
    Q = np.asarray(poly.exterior.coords)
    L.append((np.column_stack([Q, zt(Q) + 0.14]), (255, 0, 255), "trottoir"))
    Q = np.asarray(emprise_voie(R, O).exterior.coords)
    L.append((np.column_stack([Q, zt(Q) + 0.02]), (0, 255, 255), "voie"))
    for e, peint, cur in ilots(R, O):
        for g, c in ((peint, (255, 255, 255)), (cur, (255, 60, 60))):
            for gg in getattr(g, "geoms", [g]):
                Q = np.asarray(gg.exterior.coords)
                L.append((np.column_stack([Q, zt(Q) + 0.14]), c, e["id"]))
    for m in R.get("marquage", []):
        for Q in polylignes_marquage(m, R, O):
            L.append((np.column_stack([Q, zt(Q) + 0.02]), (255, 255, 0) if m["couleur"] == "jaune" else (230, 230, 255), m["id"]))
    for p in R.get("panneaux", []):
        c = L93(p["position"], O); z = float(T.z(*c)) + p.get("socle_m", 0.0)
        L.append((np.array([[*c, z], [*c, z + max(p["hauteur_mat_m"], 0.5)]]), (0, 255, 0), p["id"]))
        for pl in p["plaques"]:
            q = plaque_coins(c, p, pl, z)
            L.append((np.vstack([q, q[:1]]), (0, 255, 0), None))
    for p in R.get("poteaux", []):
        c = L93(p["position"], O); z = float(T.z(*c))
        L.append((np.array([[*c, z], [*c, z + p["hauteur_m"]]]), (0, 160, 255), p["id"]))
    for p in R.get("coffrets", []) + R.get("potelets", []):
        c = L93(p["position"], O); z = float(T.z(*c)) + p.get("z_m", 0.0)
        L.append((np.array([[*c, z], [*c, z + p.get("hauteur_m", 1.0)]]), (255, 140, 200), p["id"]))
    for v in R.get("vegetation", []):
        c = L93(v["centre"], O); z = float(T.z(*c)) + v.get("base_m", 0.0)
        r = v["rayon_m"]
        a = np.linspace(0, 2 * np.pi, 25)
        L.append((np.column_stack([c[0] + r * np.cos(a), c[1] + r * np.sin(a), np.full(25, z + v["hauteur_m"] / 2)]), (120, 255, 120), v["id"]))
    return L


def cmd_controle(img, cap, tang, fov, sortie=None):
    m40 = _charger("m40", "40_facades.py")
    R, O = releve()
    T = m37.Terrain()
    r = next(x for x in m40.photos() if x["id"].startswith(img))
    W, H = 1800, 1012
    gam = m40.convergence(float(r["x_l93"]), float(r["y_l93"]))
    eq = np.asarray(Image.open(m40.DOSSIER / f"{r['id']}.jpg").convert("RGB"))
    im = Image.fromarray(m40.vue_pinhole(eq, float(r["azimut_deg"]), cap - gam, tang, fov, W, H))
    cam = Camera(r, cap, tang, fov, W, H, m40)
    d = ImageDraw.Draw(im)
    try:
        F = ImageFont.truetype("DejaVuSans-Bold.ttf", 15)
    except OSError:
        F = None
    for Q, col, lab in lignes_controle(R, O, T):
        p = cam.proj(Q)
        seg = []
        for q in p:
            if np.isnan(q).any() or abs(q[0]) > 5 * W or abs(q[1]) > 5 * H:
                if len(seg) > 1:
                    d.line(seg, fill=col, width=2)
                seg = []
            else:
                seg.append(tuple(q))
        if len(seg) > 1:
            d.line(seg, fill=col, width=2)
        if lab and not np.isnan(p).all():
            q = p[~np.isnan(p).any(1)][-1]
            if 0 <= q[0] < W and 0 <= q[1] < H:
                d.text((q[0] + 3, q[1] - 16), lab, fill=col, font=F, stroke_width=2, stroke_fill=(0, 0, 0))
    out = Path(sortie) if sortie else RAW / "panoramax" / "depart" / f"controle_{img[:8]}_{int(cap)}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=90)
    print(out)


# ----------------------------------------------------------------------------------------------- marquage
def polylignes_marquage(m, R, O):
    """Axes des traits (L93, (k, 2)) d'un marquage : lignes (continues ou discontinues), zigzag ; le texte et le zébra
    sont des surfaces (traits = leur contour, pour le contrôle)."""
    if m.get("le_long_du_trottoir"):
        poly, P, n = trottoir_polygone(R, O)
        Pc = P + n * R["surfaces"]["trottoir"]["largeur_m"]           # bordure côté voie
        nn = n
    if m["type"] == "polyligne":
        return [L93(m["polyligne"], O)]
    if m["type"] == "ligne":
        if m.get("le_long_du_trottoir"):
            base = Pc + nn * m.get("decalage_m", 0.2)
            base = sous_polyligne(base, m["de_k"], m["a_k"])
        else:
            base = L93(m["polyligne"], O)
        return tirets(base, m.get("trait_m"), m.get("vide_m"))
    if m["type"] == "zigzag":
        base = sous_polyligne(Pc, m["de_k"], m["a_k"])
        nb = sous_polyligne(nn, m["de_k"], m["a_k"])
        Lc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(base, axis=0), axis=1))])
        s = np.arange(0, Lc[-1] + 1e-6, m["pas_m"] / 2)
        pts = []
        for k, si in enumerate(s):
            q = np.array([np.interp(si, Lc, base[:, 0]), np.interp(si, Lc, base[:, 1])])
            nq = np.array([np.interp(si, Lc, nb[:, 0]), np.interp(si, Lc, nb[:, 1])])
            pts.append(q + nq * (0.3 + (m["amplitude_m"] if k % 2 else 0.0)))
        return [np.array(pts)]
    if m["type"] == "zebra":
        a, b = L93(m["de"], O), L93(m["a"], O)
        return [np.array([a, b])]
    if m["type"] == "texte":
        c = L93(m["centre"], O)
        return [np.array([c - 1.0, c + 1.0])]
    return []


def sous_polyligne(P, k0, k1):
    """Portion de P entre les indices (réels) k0 et k1."""
    idx = np.arange(len(P))
    ks = np.arange(k0, k1 + 1e-6, 0.25)
    return np.column_stack([np.interp(ks, idx, P[:, j]) for j in range(P.shape[1])])


def tirets(P, trait=None, vide=None):
    if not trait:
        return [P]
    Lc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    out, s = [], 0.0
    while s < Lc[-1]:
        e = min(s + trait, Lc[-1])
        ss = np.linspace(s, e, 4)
        out.append(np.column_stack([np.interp(ss, Lc, P[:, 0]), np.interp(ss, Lc, P[:, 1])]))
        s = e + vide
    return out


def plaque_coins(c, p, pl, z):
    """Coins 3D (L93) du rectangle englobant d'une plaque : centre du mât c, cap de la face, décalage le long de la face."""
    a = math.radians(p["cap_face_deg"])
    nrm = np.array([math.sin(a), math.cos(a)])                       # direction vers laquelle la face regarde
    t = np.array([-nrm[1], nrm[0]])                                    # droite vue de face
    cc = c + t * pl.get("decalage_m", 0.0) + nrm * 0.05
    w, h = pl["largeur_m"], pl["hauteur_m"]
    zb = z + pl["bas_m"]
    return np.array([[*(cc - t * w / 2), zb], [*(cc + t * w / 2), zb], [*(cc + t * w / 2), zb + h], [*(cc - t * w / 2), zb + h]])


# ----------------------------------------------------------------------------------------------- géométrie
def _gl_n(n):
    n = np.atleast_2d(np.asarray(n, float))
    return np.column_stack([n[:, 0], n[:, 2], -n[:, 1]])


def maille(P, tri, uv, ref, nrm=None):
    """Positions Lambert-93 (N, 3), triangles, UV -> partie de maillage glTF (normales lissées si nrm absent)."""
    G = m08.to_gltf(np.asarray(P, float), ref).astype(np.float64)
    tri = np.asarray(tri, np.int64)
    N = m08.normales(G, tri) if nrm is None else _gl_n(nrm).astype(np.float32)
    return {"pos": G, "nrm": N, "uv": np.asarray(uv, np.float32), "idx": tri.astype(np.uint32)}


def face_plane(Q, normale, uv, ref):
    """Polygone plan convexe (k, 3) en éventail, orienté vers `normale` (L93), sommets propres (arêtes vives)."""
    Q = np.asarray(Q, float); k = len(Q)
    tri = np.column_stack([np.zeros(k - 2, int), np.arange(1, k - 1), np.arange(2, k)])
    f = np.cross(Q[tri[0, 1]] - Q[tri[0, 0]], Q[tri[0, 2]] - Q[tri[0, 0]])
    if f @ np.asarray(normale, float) < 0:
        tri = tri[:, ::-1]
    return maille(Q, tri, uv, ref, np.tile(np.asarray(normale, float), (k, 1)))


def cylindre(c0, c1, z0, z1, r0, r1, ref, n=8, s_uv=1.0, chapeau=True):
    """Fût (cercles horizontaux de centres c0 en bas, c1 en haut ; un fût penché si c0 != c1), normales radiales."""
    a = np.linspace(0, 2 * np.pi, n + 1)
    ca, sa = np.cos(a), np.sin(a)
    B = np.column_stack([c0[0] + r0 * ca, c0[1] + r0 * sa, np.full(n + 1, z0)])
    T = np.column_stack([c1[0] + r1 * ca, c1[1] + r1 * sa, np.full(n + 1, z1)])
    P = np.vstack([B, T])
    i = np.arange(n)
    tri = np.concatenate([np.column_stack([i, i + 1, n + 2 + i]), np.column_stack([i, n + 2 + i, n + 1 + i])])
    nr = np.column_stack([np.r_[ca, ca], np.r_[sa, sa], np.zeros(2 * n + 2)])
    per = 2 * np.pi * max(r0, r1)
    uv = np.column_stack([np.r_[a, a] / (2 * np.pi) * per / s_uv, np.r_[np.zeros(n + 1), np.full(n + 1, z1 - z0)] / s_uv])
    parts = [maille(P, tri, uv, ref, nr)]
    if chapeau:
        parts.append(face_plane(T[:-1], [0, 0, 1], np.column_stack([ca[:-1], sa[:-1]]) * 0.5 + 0.5, ref))
    return parts


def tube(A, B, r, ref, n=5):
    """Tube de section n-gonale de A à B (L93, 3D) : crosses, câbles, jambes de force."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    d = B - A; L = np.linalg.norm(d)
    if L < 1e-6:
        return []
    d /= L
    u = np.cross(d, [0, 0, 1.0]) if abs(d[2]) < 0.95 else np.cross(d, [1.0, 0, 0])
    u /= np.linalg.norm(u); v = np.cross(d, u)
    a = np.linspace(0, 2 * np.pi, n + 1)
    R = np.outer(np.cos(a), u) + np.outer(np.sin(a), v)
    P = np.vstack([A + r * R, B + r * R])
    i = np.arange(n)
    tri = np.concatenate([np.column_stack([i, i + 1, n + 2 + i]), np.column_stack([i, n + 2 + i, n + 1 + i])])
    uv = np.column_stack([np.r_[a, a] / (2 * np.pi) * 0.1, np.r_[np.zeros(n + 1), np.full(n + 1, L)]])
    return [maille(P, tri, uv, ref, np.vstack([R, R]))]


def boite(c, cap_deg, lx, ly, z0, z1, ref, s_uv=1.0):
    """Pavé centré en c, côté lx le long de t (cap_deg + 90), ly le long de n (cap_deg = direction de la face avant)."""
    a = math.radians(cap_deg)
    n = np.array([math.sin(a), math.cos(a)]); t = np.array([n[1], -n[0]])
    c = np.asarray(c, float)
    coins = [c - t * lx / 2 - n * ly / 2, c + t * lx / 2 - n * ly / 2, c + t * lx / 2 + n * ly / 2, c - t * lx / 2 + n * ly / 2]
    parts = []
    for k in range(4):
        p, q = coins[k], coins[(k + 1) % 4]
        Q = np.array([[*p, z0], [*q, z0], [*q, z1], [*p, z1]])
        e = q - p; L = np.linalg.norm(e)
        nn = np.array([e[1], -e[0], 0]) / max(L, 1e-9)
        if nn[:2] @ (p + q - 2 * c) < 0:
            nn = -nn
        parts.append(face_plane(Q, nn, np.array([[0, 0], [L, 0], [L, z1 - z0], [0, z1 - z0]]) / s_uv, ref))
    for z, s in ((z1, 1), (z0, -1)):
        Q = np.array([[*q, z] for q in coins])
        parts.append(face_plane(Q, [0, 0, s], np.array([[0, 0], [lx, 0], [lx, ly], [0, ly]]) / s_uv, ref))
    return parts


def massif(c, z0, rx, ry, h, ref, seed, s_uv=1.5):
    """Massif de feuillage : ellipsoïde bosselé (bruit à graine fixe), pied à z0, haut de h."""
    rng = np.random.default_rng(seed)
    nu, nv = 12, 7
    th = np.linspace(0, 2 * np.pi, nu + 1)
    ph = np.linspace(-0.25 * np.pi, 0.5 * np.pi, nv)
    TH, PH = np.meshgrid(th, ph)
    bos = 1 + 0.18 * rng.standard_normal(TH.shape)
    bos[:, -1] = bos[:, 0]
    bos[-1, :] = 1.0
    X = c[0] + rx * np.cos(PH) * np.cos(TH) * bos
    Y = c[1] + ry * np.cos(PH) * np.sin(TH) * bos
    zc = z0 + h * 0.42
    Z = np.maximum(zc + (h * 0.58) * np.sin(PH) * bos, z0 - 0.1)
    P = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    W = nu + 1
    tri = []
    for j in range(nv - 1):
        for i in range(nu):
            a, b, d, e = j * W + i, j * W + i + 1, (j + 1) * W + i, (j + 1) * W + i + 1
            tri += [[a, b, e], [a, e, d]]
    per = np.pi * (rx + ry)
    uv = np.column_stack([(TH / (2 * np.pi) * per).ravel(), ((PH + 0.25 * np.pi) * h / 1.2).ravel()]) / s_uv
    return [maille(P, np.array(tri), uv, ref)]


def contour_forme(forme, w, h):
    if forme == "rond":
        a = np.linspace(0, 2 * np.pi, 33)[:-1]
        return np.column_stack([w / 2 * np.cos(a), h / 2 + h / 2 * np.sin(a)])
    if forme == "triangle_bas":
        return np.array([[0, 0], [w / 2, h], [-w / 2, h]])
    if forme == "fleche_gauche":
        return np.array([[-w / 2, h / 2], [-w / 2 + h * 0.5, 0], [w / 2, 0], [w / 2, h], [-w / 2 + h * 0.5, h]])
    return np.array([[-w / 2, 0], [w / 2, 0], [w / 2, h], [-w / 2, h]])


def plaque(c, cap_deg, pl, z_sol, ref, ecart=0.04):
    """Plaque de panneau en forme (sans transparence) : face avant texturée (UV 0-1 sur son cadre), dos gris."""
    a = math.radians(cap_deg)
    nrm = np.array([math.sin(a), math.cos(a)]); t = np.array([-nrm[1], nrm[0]])       # t : droite vue de face
    w, h = pl["largeur_m"], pl["hauteur_m"]
    cc = np.asarray(c, float) + t * pl.get("decalage_m", 0.0)
    zb = z_sol + pl["bas_m"]
    F = contour_forme(pl.get("forme", "rect"), w, h)
    uv = np.column_stack([(F[:, 0] + w / 2) / w, 1 - F[:, 1] / h])
    av = np.column_stack([cc[0] + t[0] * F[:, 0] + nrm[0] * ecart, cc[1] + t[1] * F[:, 0] + nrm[1] * ecart, zb + F[:, 1]])
    ar = av - np.array([*nrm, 0]) * 0.015
    return face_plane(av, [*nrm, 0], uv, ref), face_plane(ar, [*(-nrm), 0], uv, ref)


def chainette(A, B, fils, ref):
    """Câbles entre deux têtes de poteau : flèche de 0,8 m pour 60 m (comme CABLES de 16), écartés de 0,3 m."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    L = np.linalg.norm(B[:2] - A[:2])
    d = (B[:2] - A[:2]) / max(L, 1e-9); e = np.array([-d[1], d[0]])
    f = 0.8 * (L / 60.0) ** 2 + 0.15
    parts = []
    for k in range(fils):
        o = (k - (fils - 1) / 2) * 0.3
        s = np.linspace(0, 1, 13)
        Q = np.column_stack([A[0] + (B[0] - A[0]) * s + e[0] * o, A[1] + (B[1] - A[1]) * s + e[1] * o,
                             A[2] + (B[2] - A[2]) * s - 4 * f * s * (1 - s) - 0.1 * k])
        for q0, q1 in zip(Q[:-1], Q[1:]):
            parts += tube(q0, q1, 0.009, ref, 4)
    return parts


# --- textures (calculées ; puissances de 2 pour Unreal) ---------------------------------------------------------------
def _bruit_rgb(base, px=256, amp=14, seed=1, grain=1.2):
    rng = np.random.default_rng(seed)
    a = rng.normal(0, 1, (px, px))
    im = Image.fromarray(np.clip(128 + a * 40, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(grain))
    v = (np.asarray(im).astype(float) - 128) / 40
    rgb = np.array(base, float)[None, None] + v[..., None] * amp
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def tex_fleurs(base_fond, fleur, densite, seed):
    im = m37.tex_haie(256, seed)
    a = np.asarray(im).astype(float) * np.array(base_fond)[None, None] / np.array([66, 89, 49])[None, None]
    rng = np.random.default_rng(seed)
    m = Image.fromarray((rng.random((256, 256)) < densite).astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1))
    k = np.asarray(m).astype(float)[..., None] / 255
    a = a * (1 - k) + np.array(fleur)[None, None] * k * (0.85 + 0.3 * rng.random((256, 256, 1)))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def police(t):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", t)
    except OSError:
        return ImageFont.load_default()


def faces_panneaux():
    """Faces redessinées d'après les photos (texte lu ; aucun logo) ; images opaques (la forme est dans la géométrie)."""
    m39 = _charger("m39", "39_panneaux_neutres.py")
    blanc = lambda im: Image.alpha_composite(Image.new("RGBA", im.size, (250, 250, 250, 255)), im).convert("RGB")  # noqa: E731
    F = {}
    F["B14_50"] = blanc(m39.rond("50")).resize((256, 256))
    F["B13_19t"] = blanc(m39.rond("19t")).resize((256, 256))
    im = Image.new("RGB", (256, 256), (200, 20, 30)); d = ImageDraw.Draw(im)
    d.rectangle([40, 104, 216, 152], fill=(250, 250, 250)); F["B1"] = im
    im = Image.new("RGB", (256, 256), (30, 80, 160)); d = ImageDraw.Draw(im)
    d.line([(70, 70), (178, 178)], fill=(250, 250, 250), width=30)
    d.polygon([(190, 110), (190, 190), (110, 190)], fill=(250, 250, 250)); F["B21"] = im
    im = Image.new("RGB", (256, 256), (200, 20, 30)); d = ImageDraw.Draw(im)
    d.polygon([(38, 30), (218, 30), (128, 210)], fill=(250, 250, 250)); F["AB3a"] = im
    im = Image.new("RGB", (256, 256), (30, 80, 160)); d = ImageDraw.Draw(im)
    d.rectangle([12, 12, 243, 243], outline=(250, 250, 250), width=8)
    d.rectangle([104, 90, 152, 230], fill=(250, 250, 250)); d.rectangle([60, 50, 196, 100], fill=(200, 20, 30)); F["C13a"] = im
    im = Image.new("RGB", (256, 256), (30, 80, 160)); d = ImageDraw.Draw(im)
    d.rectangle([12, 12, 243, 243], outline=(250, 250, 250), width=8)
    d.polygon([(128, 34), (226, 214), (30, 214)], fill=(250, 250, 250))
    for k in range(4):
        d.rectangle([70 + 30 * k, 196, 86 + 30 * k, 210], fill=(30, 30, 30))
    d.ellipse([118, 92, 138, 112], fill=(20, 20, 20)); d.line([(128, 112), (122, 160), (110, 190)], fill=(20, 20, 20), width=8)
    d.line([(122, 160), (140, 190)], fill=(20, 20, 20), width=8); F["C20a"] = im
    im = Image.new("RGB", (128, 64), (240, 200, 20)); d = ImageDraw.Draw(im)
    d.rectangle([2, 2, 125, 61], outline=(30, 30, 30), width=3); d.text((64, 33), "D 3", fill=(20, 20, 20), font=police(36), anchor="mm")
    F["cartouche_D3"] = im
    for txt in ("SIGNES", "CAUNET", "Circuit du Castellet"):
        im = Image.new("RGB", (512, 128), (245, 245, 240)); d = ImageDraw.Draw(im)
        d.polygon([(4, 64), (58, 6), (507, 6), (507, 121), (58, 121)], outline=(30, 110, 60), width=8)
        d.text((290, 66), txt, fill=(30, 90, 50), font=police(52 if len(txt) < 10 else 40), anchor="mm")
        F[f"dir_{txt}"] = im
    im = Image.new("RGB", (128, 64), (245, 245, 240)); d = ImageDraw.Draw(im)
    d.rectangle([2, 2, 125, 61], outline=(60, 60, 60), width=3); F["plaque_blanche"] = im
    im = Image.new("RGB", (256, 128), (245, 245, 240)); d = ImageDraw.Draw(im)
    d.rectangle([3, 3, 252, 124], outline=(30, 30, 30), width=5)
    d.text((128, 38), "SAUF", fill=(20, 20, 20), font=police(36), anchor="mm")
    d.text((200, 92), "BUS", fill=(20, 20, 20), font=police(34), anchor="mm"); F["panonceau_SAUF_BUS"] = im
    return F


def matieres_depart():
    img = lambda im, rough=0.9, metal=0.0: {"img": m37._jpeg(im), "mime": "image/jpeg", "rough": rough, "metal": metal}  # noqa: E731
    M = {"enrobe_neuf": img(_bruit_rgb((62, 63, 65), 512, 10, 3, 0.8), 0.85),
         "enrobe_rouge": img(_bruit_rgb((106, 60, 55), 512, 9, 5, 0.8), 0.85),   # rouge éteint de la photo (89d3561a)
         "bordure_beton": img(m37.tex_cc0("white_plaster_rough_01", (196, 194, 188), 256)),
         "peinture_blanche": img(_bruit_rgb((236, 236, 232), 64, 5, 7), 0.6),
         "peinture_jaune": img(_bruit_rgb((222, 176, 38), 64, 5, 8), 0.6),
         "mat_galva": img(m37.tex_unie((160, 162, 165)), 0.4, 0.6),
         "dos_panneau": img(m37.tex_unie((150, 152, 155)), 0.5, 0.4),
         "poteau_beton": img(m37.tex_cc0("white_plaster_rough_01", (188, 182, 170), 256)),
         "poteau_bois": img(_bruit_rgb((104, 92, 80), 256, 12, 9, 2.5)),
         "lierre": img(m37.tex_haie(256, 11)),
         "lanterne": img(m37.tex_unie((96, 98, 102)), 0.5, 0.5),
         "transformateur": img(m37.tex_unie((150, 154, 150)), 0.6, 0.3),
         "cable": img(m37.tex_unie((40, 40, 42)), 0.6),
         "coffret_gris_clair": img(m37.tex_unie((196, 196, 190)), 0.6),
         "coffret_blanc": img(m37.tex_unie((226, 226, 220)), 0.6),
         "boite_jaune": img(m37.tex_unie((228, 186, 30)), 0.5),
         "potelet_vert": img(m37.tex_unie((38, 88, 62)), 0.5),
         "feuillage_haie": img(tex_fleurs((92, 116, 62), (92, 116, 62), 0.0, 13)),   # vert plus clair que la haie taillée de 37 (photos)
         "feuillage_bougainvillier": img(tex_fleurs((74, 100, 54), (196, 40, 132), 0.008, 17)),
         "feuillage_laurier_rose": img(tex_fleurs((58, 82, 50), (214, 70, 100), 0.012, 19))}
    for k, im in faces_panneaux().items():
        M["panneau_" + k.replace(" ", "_")] = img(im, 0.45)
    return M


def lettres(texte, longueur, haut, centre, cap_lecture, px=60):
    """Polygones (L93) d'un texte peint : rastérisé puis contours (cv2), lettres pleines avec leurs trous."""
    import cv2
    f = police(px)
    w = int(f.getlength(texte)) + 20
    im = Image.new("L", (w, px + 20), 0)
    ImageDraw.Draw(im).text((10, 10), texte, fill=255, font=f)
    a = np.asarray(im)
    ys, xs = np.nonzero(a > 127)
    cs, hier = cv2.findContours((a > 127).astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    d = np.array([math.sin(math.radians(cap_lecture)), math.cos(math.radians(cap_lecture))])
    up = np.array([-d[1], d[0]])
    def vers(c):                                    # noqa: E306
        c = c.reshape(-1, 2).astype(float)
        u = ((c[:, 0] - x0) / (x1 - x0) - 0.5) * longueur
        v = (0.5 - (c[:, 1] - y0) / (y1 - y0)) * haut
        return np.asarray(centre) + np.outer(u, d) + np.outer(v, up)
    polys = []
    for i, c in enumerate(cs):
        if hier[0][i][3] != -1 or len(c) < 3:
            continue
        trous = [vers(cs[j]) for j in range(len(cs)) if hier[0][j][3] == i and len(cs[j]) >= 3]
        polys.append(shapely.make_valid(Polygon(vers(c), trous)))
    return shapely.union_all(polys)


def marquage_polygones(m, R, O):
    if m["type"] == "texte":
        return lettres(m["texte"], m["longueur_m"], m["hauteur_lettres_m"], L93(m["centre"], O), m["cap_lecture_deg"])
    if m["type"] == "zebra":
        a, b = L93(m["de"], O), L93(m["a"], O)
        L = np.linalg.norm(b - a); d = (b - a) / L; e = np.array([-d[1], d[0]])
        out, s = [], 0.25
        while s + m["bande_m"] <= L:
            p, q = a + d * s, a + d * (s + m["bande_m"])
            out.append(Polygon([p - e * m["largeur_m"] / 2, q - e * m["largeur_m"] / 2, q + e * m["largeur_m"] / 2, p + e * m["largeur_m"] / 2]))
            s += 2 * m["bande_m"]
        return shapely.union_all(out)
    w = m.get("largeur_m", 0.12)
    return shapely.union_all([LineString(Q).buffer(w / 2, cap_style=2, join_style=2) for Q in polylignes_marquage(m, R, O)])


def construire():
    R, O = releve()
    ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    m12 = _charger("m12", "12_carrefours_annexes.py")
    voie = emprise_voie(R, O)
    b = voie.buffer(25).bounds
    st = m12.SolTerrain(ref, b)
    T = m37.Terrain()

    def zs(XY):
        XY = np.atleast_2d(np.asarray(XY, float))
        z = st.z(XY)
        bad = ~np.isfinite(z)
        if bad.any():
            z[bad] = T.z(XY[bad, 0], XY[bad, 1])
        return z

    import aplanissements
    plates = aplanissements.plateformes()
    ch, ruban = chaussee_ruban()
    ruban_l = ruban.buffer(0.02)
    meshes, coll, sol_coll = [], {}, []
    bilan = {"surfaces_m2": {}, "marquage_m2": {}, "panneaux": [], "poteaux": [], "lignes_aeriennes_m": 0.0, "coffrets": 0,
             "potelets": 0, "massifs": {}, "vu_non_pose": R.get("vu_non_pose", [])}

    def ajoute(parts, nom, mat):
        parts = [p for p in parts if p is not None]
        if parts:
            meshes.append(m37.fusion(parts, nom, mat))

    def surf(P, mat, nom, dz=0.0, uv_s=m11.S_ENROBE, roulage=True):
        P = shapely.make_valid(P)
        if P.is_empty or P.area < 0.05:
            return 0.0
        me, aire = m12.maillage_sur_terrain(P, st, zs, ref, mat, nom, uv_s, [])
        me["pos"] = me["pos"].astype(np.float64); me["pos"][:, 1] += dz
        # au pied du mur, les triangles du terrain montent dans la marche (ligne de rupture de 08) : la surface est
        # plafonnée au niveau de la plateforme (sinon des dents rouges sortaient devant le mur, vu sur la planche)
        for k in plates:
            X = me["pos"][:, 0] + ref["x0"]; Y = ref["y0"] - me["pos"][:, 2]
            dans = shapely.contains_xy(k["poly"].buffer(0.6), X, Y)
            zmax = aplanissements.z_plateforme(k, X, Y) - ref["z0"] + SURELEV + dz + 0.01
            me["pos"][:, 1] = np.where(dans, np.minimum(me["pos"][:, 1], zmax), me["pos"][:, 1])
        me["pos"] = me["pos"].astype(np.float32)
        meshes.append(me)
        if roulage:
            sol_coll.append(dict(me, mat="enrobe_depart" if "rouge" not in mat else "enrobe_depart_rouge"))
        return aire

    def bordure(P, h, nom):
        parts = []
        for g in getattr(P, "geoms", [P]):
            g = shapely.orient_polygons(g)
            Q = np.asarray(g.exterior.segmentize(0.5).coords)
            t = np.gradient(Q, axis=0); t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
            n = np.column_stack([t[:, 1], -t[:, 0]])                       # extérieur (anneau trigonométrique)
            z = zs(Q)
            parts.append(m37.ruban(Q, n, -0.15, 0.0, z - 0.08, z + h + 0.005, ref, 1.0, caps=False))
        ajoute(parts, nom, "bordure_beton")

    # --- surfaces ---------------------------------------------------------------------------------------------------
    trot, Pt, nt = trottoir_polygone(R, O)
    il = ilots(R, O)
    parv = shapely.make_valid(Polygon(L93(R["surfaces"]["parvis_abri"]["polygone"], O)))
    hauts = [(trot.difference(ruban_l), R["surfaces"]["trottoir"]["hauteur_m"], "trottoir")]
    hauts += [(cur.difference(ruban_l), e["hauteur_m"], e["id"]) for e, _, cur in il]
    hauts += [(parv.difference(ruban_l), R["surfaces"]["parvis_abri"]["hauteur_m"], "parvis_abri")]
    enrobe = voie.difference(ruban_l)
    for g, _, _ in hauts:
        enrobe = enrobe.difference(g)
    bilan["surfaces_m2"]["voie_laterale_enrobe"] = round(surf(enrobe, "enrobe_neuf", "voie_laterale_enrobe"), 1)
    for g, h, nom in hauts:
        bilan["surfaces_m2"][nom] = round(surf(g, "enrobe_rouge", f"{nom}_enrobe_rouge", h - SURELEV, 2.0), 1)
        bordure(g, h, f"{nom}_bordure")
    # --- marquage ----------------------------------------------------------------------------------------------------
    sur_enrobe = enrobe.buffer(-0.02)
    for e, peint, cur in il:
        bande = peint.difference(cur.buffer(0.01)).intersection(sur_enrobe)
        bilan["marquage_m2"][f"{e['id']}_liseré"] = round(surf(bande, "peinture_blanche", f"{e['id']}_liseré", PEINTURE, 1.0, False), 1)
    for m in R.get("marquage", []):
        g = marquage_polygones(m, R, O).intersection(sur_enrobe)
        mat = "peinture_jaune" if m["couleur"] == "jaune" else "peinture_blanche"
        bilan["marquage_m2"][m["id"]] = round(surf(g, mat, m["id"], PEINTURE, 1.0, False), 1)
    # --- poteaux et lignes ---------------------------------------------------------------------------------------------
    tetes = {}
    for p in R.get("poteaux", []):
        c = L93(p["position"], O); z = float(zs(c)[0]); H = p["hauteur_m"]
        if p["type"] == "bois":
            ajoute(cylindre(c, c, z - PIED, z + H, 0.13, 0.10, ref, 10), f"{p['id']}_fut", "poteau_bois")
            coll.setdefault("cloture", []).append(m37.boite_collision(np.array([c - [0.12, 0], c + [0.12, 0]]), np.array([[0, 1.0]] * 2), -0.12, 0.12, z - 0.3, z + 3.5, ref))
            if p.get("jambe_de_force_cap_deg") is not None:
                a = math.radians(p["jambe_de_force_cap_deg"]); dd = np.array([math.sin(a), math.cos(a)])
                ajoute(tube([*(c + dd * 1.8), z - 0.2], [*(c + dd * 0.15), z + H * 0.7], 0.1, ref, 8), f"{p['id']}_jambe", "poteau_bois")
        else:
            ajoute(cylindre(c, c, z - PIED, z + H, 0.17, 0.11, ref, 8), f"{p['id']}_fut", "poteau_lierre" if p.get("lierre") else "poteau_beton")
            if p.get("lierre"):
                ajoute(cylindre(c, c, z, z + H * 0.85, 0.30, 0.20, ref, 9), f"{p['id']}_lierre", "lierre")
            coll.setdefault("beton", []).append(m37.boite_collision(np.array([c - [0.15, 0], c + [0.15, 0]]), np.array([[0, 1.0]] * 2), -0.15, 0.15, z - 0.3, z + 3.5, ref))
        if p.get("lampe_cap_deg") is not None:
            a = math.radians(p["lampe_cap_deg"]); dd = np.array([math.sin(a), math.cos(a)])
            A = [*c, z + H - 1.2]; B = [*(c + dd * 1.4), z + H - 0.6]
            ajoute(tube(A, B, 0.035, ref, 6), f"{p['id']}_crosse", "lanterne")
            ajoute(boite(c + dd * 1.55, p["lampe_cap_deg"] + 90, 0.28, 0.55, z + H - 0.8, z + H - 0.6, ref), f"{p['id']}_lanterne", "lanterne")
        if p.get("transfo"):
            ajoute(boite(c + np.array([0.0, -0.32]), 180, 0.6, 0.4, z + 4.5, z + 5.4, ref), f"{p['id']}_transformateur", "transformateur")
        tetes[p["id"]] = np.array([*c, z + H - 0.35])
        bilan["poteaux"].append({"id": p["id"], "type": p["type"], "hauteur_m": H})
    for li in R.get("lignes_aeriennes", []):
        A, B = tetes[li["de"]], tetes[li["a"]]
        ajoute(chainette(A, B, li.get("fils", 2), ref), f"ligne_{li['de']}_{li['a']}", "cable")
        bilan["lignes_aeriennes_m"] += round(float(np.linalg.norm(B[:2] - A[:2])), 1)
    # --- panneaux -------------------------------------------------------------------------------------------------------
    for p in R.get("panneaux", []):
        c = L93(p["position"], O); z = float(zs(c)[0]) + p.get("socle_m", 0.0)
        if p.get("sur_poteau"):
            c = L93(next(q["position"] for q in R["poteaux"] if q["id"] == p["sur_poteau"]), O)
            a = math.radians(p["cap_face_deg"]); c = c + np.array([math.sin(a), math.cos(a)]) * 0.12
        else:
            ajoute(cylindre(c, c, z - 0.4, z + p["hauteur_mat_m"], 0.035, 0.035, ref, 8), f"{p['id']}_mat", "mat_galva")
            coll.setdefault("cloture", []).append(m37.boite_collision(np.array([c - [0.05, 0], c + [0.05, 0]]), np.array([[0, 1.0]] * 2), -0.05, 0.05, z - 0.3, z + 2.0, ref))
        for k, pl in enumerate(p["plaques"]):
            av, ar = plaque(c, p["cap_face_deg"], pl, z, ref)
            ajoute([av], f"{p['id']}_face{k}", "panneau_" + pl["face"].replace(" ", "_"))
            ajoute([ar], f"{p['id']}_dos{k}", "dos_panneau")
        bilan["panneaux"].append({"id": p["id"], "plaques": [pl["face"] for pl in p["plaques"]]})
    # --- coffrets, boîte aux lettres, potelets --------------------------------------------------------------------------
    Pw = pied_du_mur(R, O); nw, _ = normale_route(Pw)
    for cf in R.get("coffrets", []):
        c = L93(cf["position"], O)
        k = int(np.argmin(np.linalg.norm(Pw - c, axis=1)))
        cap = math.degrees(math.atan2(nw[k, 0], nw[k, 1]))
        cc = Pw[k] + (c - Pw[k]) @ np.array([nw[k, 1], -nw[k, 0]]) * np.array([nw[k, 1], -nw[k, 0]]) + nw[k] * 0.02
        z = float(zs(Pw[k] + nw[k] * 0.8)[0])
        mat = {"jaune": "boite_jaune", "blanc": "coffret_blanc"}.get(cf["couleur"], "coffret_gris_clair")
        ajoute(boite(cc, cap, cf["largeur_m"], 0.26, z + cf["z_m"], z + cf["z_m"] + cf["hauteur_m"], ref), cf["id"], mat)
        bilan["coffrets"] += 1
    for pt in R.get("potelets", []):
        c = L93(pt["position"], O); z = float(zs(c)[0]) + pt.get("socle_m", 0.14 if trot.contains(Point(c)) else 0.0)
        if pt.get("inclinaison_deg"):
            a = math.radians(pt["cap_inclinaison_deg"]); dd = np.array([math.sin(a), math.cos(a)])
            top = c + dd * pt["hauteur_m"] * math.tan(math.radians(pt["inclinaison_deg"]))
            ajoute(tube([*c, z - 0.2], [*top, z + pt["hauteur_m"]], 0.04, ref, 8), pt["id"], "mat_galva")
        else:
            ajoute(cylindre(c, c, z - 0.2, z + pt["hauteur_m"], 0.07, 0.07, ref, 10), pt["id"], "potelet_vert")
            ajoute(cylindre(c, c, z + pt["hauteur_m"] - 0.22, z + pt["hauteur_m"] - 0.14, 0.072, 0.072, ref, 10, chapeau=False), f"{pt['id']}_bande", "peinture_blanche")
            coll.setdefault("cloture", []).append(m37.boite_collision(np.array([c - [0.07, 0], c + [0.07, 0]]), np.array([[0, 1.0]] * 2), -0.07, 0.07, z - 0.2, z + pt["hauteur_m"], ref))
        bilan["potelets"] += 1
    # --- végétation des jardins -----------------------------------------------------------------------------------------
    import rasterio
    with rasterio.open(RAW / "mns_lidarhd_50cm.tif") as s:
        mns, inv = s.read(1), ~s.transform
    def z_mns(x, y):                                  # noqa: E306
        cc, rr = inv * (np.asarray(x, float), np.asarray(y, float))
        return mns[np.clip(np.floor(rr).astype(int), 0, mns.shape[0] - 1), np.clip(np.floor(cc).astype(int), 0, mns.shape[1] - 1)].astype(float)
    hj = R.get("haie_jardins")
    n_haie = 0
    if hj:
        Pk = sous_polyligne(Pw, hj["de_k"], hj["a_k"])
        nk = sous_polyligne(nw, hj["de_k"], hj["a_k"])
        Lc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(Pk, axis=0), axis=1))])
        parts, rng = [], np.random.default_rng(41)
        for sdist in np.arange(0.5, Lc[-1], 1.3):
            q = np.array([np.interp(sdist, Lc, Pk[:, 0]), np.interp(sdist, Lc, Pk[:, 1])])
            nq = np.array([np.interp(sdist, Lc, nk[:, 0]), np.interp(sdist, Lc, nk[:, 1])]); nq /= np.linalg.norm(nq)
            for o in np.arange(hj["recul_derriere_pied_m"][0], hj["recul_derriere_pied_m"][1] + 1e-6, 1.4):
                Q = q - nq * (o + rng.uniform(-0.3, 0.3))
                zg = float(T.z(*Q))
                h = float(z_mns(*Q)) - zg
                if h < hj["hauteur_min_m"]:
                    continue
                h = min(h, hj["hauteur_max_m"])
                r = rng.uniform(0.8, 1.15)
                parts += massif(Q, zg, r, r, h, ref, int(rng.integers(1e6)))
                n_haie += 1
        ajoute(parts, "haie_jardins", "feuillage_haie")
    bilan["massifs"]["haie_jardins (MNS - MNT)"] = n_haie
    for mj in R.get("murets_jardin", []):
        Pk = sous_polyligne(Pw, mj["de_k"], mj["a_k"])
        nk = sous_polyligne(nw, mj["de_k"], mj["a_k"]); nk /= np.linalg.norm(nk, axis=1, keepdims=True)
        Q = Pk - nk * mj["recul_derriere_pied_m"]
        # pied posé sur le dessus du mur de pierre tel que le calcule 37 (pied_de_mur : max(pied + h, MNT 1 m derrière + 0,15))
        zb = T.z(*(Pk + nk * 0.8).T)
        top = np.maximum(zb + 2.5, T.z(*(Pk - nk * 1.0).T) + 0.15)
        z0, z1 = top - 0.3, top + mj["hauteur_m"]
        ajoute([m37.ruban(Q, -nk, 0.0, 0.2, z0, z1, ref, 2.0)], f"{mj['id']}_muret", "enduit_blanc")
        ajoute(m37.poteaux(Q, -nk, 0.1, z1, z1 + mj["grillage_m"], ref), f"{mj['id']}_poteaux", "potelet_vert")
        ajoute([m37.plaque(Q, -nk, 0.1, z1, z1 + mj["grillage_m"], ref, 0.5)], f"{mj['id']}_grillage", "grillage")
        bilan["massifs"][mj["id"] + " (m)"] = round(float(np.linalg.norm(np.diff(Q, axis=0), axis=1).sum()), 1)
    for v in R.get("vegetation", []):
        c = L93(v["centre"], O); z = float(T.z(*c))
        ajoute(massif(c, z, v["rayon_m"], v["rayon_m"] * 0.85, v["hauteur_m"], ref, zlib.crc32(v["id"].encode()) % 10000),
               v["id"], "feuillage_" + v["espece"])
        bilan["massifs"][v["id"]] = 1
    # --- écriture -------------------------------------------------------------------------------------------------------
    M = matieres_depart()
    M["poteau_lierre"] = M["poteau_beton"]
    M37 = m37.matieres()                     # mêmes noms et mêmes images que 37 : 16 n'en garde qu'une par nom
    M["enduit_blanc"], M["grillage"] = M37["enduit_blanc"], M37["grillage"]
    used = {m["mat"] for m in meshes}
    manque = used - set(M)
    if manque:
        raise SystemExit(f"matières sans texture : {sorted(manque)}")
    m37.ecrire_glb(MOD / "depart.glb", meshes, {k: v for k, v in M.items() if k in used})
    cm = [m11.fusion([dict(pos=x["pos"], nrm=x["nrm"], uv=x["uv"], idx=x["idx"]) for x in sol_coll if x["mat"] == k], f"depart_{k}", k)
          for k in sorted({x["mat"] for x in sol_coll})]
    cm += [m11.fusion([b for b in v if b is not None], f"depart_{k}_collision", k) for k, v in coll.items()]
    m11.ecrire_glb(MOD / "depart_collision.glb", cm, {m["mat"]: {"color": [0.5, 0.5, 0.5]} for m in cm})
    bilan["maillages"] = len(meshes)
    bilan["triangles"] = int(sum(len(m["idx"]) for m in meshes))
    bilan["lignes_aeriennes_m"] = round(bilan["lignes_aeriennes_m"], 1)
    bilan["collision"] = {k: len(v) for k, v in coll.items()}
    bilan["sol_de_roulage_m2"] = round(float(sum(m12.aire_plan(np.column_stack([x["pos"][:, 0], -x["pos"][:, 2]]).astype(float), x["idx"].astype(np.int64)).sum() for x in sol_coll)), 1)
    (OUT / "depart_bilan.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in bilan.items() if k != "vu_non_pose"}, ensure_ascii=False))


def cmd_sol(img, cap, tang, fov, pixels, z_plus=0.0):
    """Coordonnées (repère du relevé) des points du sol vus aux pixels donnés d'une vue de controle (1800 x 1012)."""
    m40 = _charger("m40", "40_facades.py")
    R, O = releve()
    T = m37.Terrain()
    r = next(x for x in m40.photos() if x["id"].startswith(img))
    cam = Camera(r, cap, tang, fov, 1800, 1012, m40)
    for px in pixels:
        u, v = map(float, px.split(","))
        q = cam.sol(u, v, T, z_plus)
        print(px, None if q is None else np.round(q - O, 2).tolist())


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "sol":
        zp = float(a[5]) if len(a) > 5 and "," not in a[5] else 0.0
        cmd_sol(a[1], float(a[2]), float(a[3]), float(a[4]), [x for x in a[5:] if "," in x], zp)
    elif a and a[0] == "controle":
        cmd_controle(a[1], float(a[2]), float(a[3]), float(a[4]), a[5] if len(a) > 5 else None)
    else:
        construire()
