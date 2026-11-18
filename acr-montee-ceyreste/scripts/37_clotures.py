"""Géométrie des murs, murets, clôtures, portails, haies et objets du départ relevés par 36 (troisième passe, 18/11/2026).

Entrée : data/reference/clotures_murets.json (36_releve_clotures.py verser).
Sorties :
  modele/clotures.glb              décor : un maillage par élément et par matière (UV en mètres), lu par 15 (rendu de
                                   contrôle), 16 (paquet Unreal, famille « clotures ») et 33 (export neutre)
  modele/clotures_collision.glb    pavés des éléments à moins de 15 m de la chaussée (matières pierre, beton,
                                   cloture, haie), lus par 09 (obstacles du Stage IR)
  data/processed/clotures_bilan.json   longueurs par type et par côté, part calée au mètre, ce qui a un asset du jeu

Formes (paramétriques, posées sur le MNT LiDAR HD 0,5 m, pied enterré de 0,3 m, rien de flottant) :
  pierre_seche      corps de pierre (texture CC0 old_stone_wall, Poly Haven) + couronnement de pierres plates
  mur_enduit        corps enduit (CC0 white_plaster_rough_01 teinté) + chaperon
  muret_grillage    muret (pierre, béton ou enduit) + poteaux tous les 2,5 m + grillage simple torsion (texture ajourée)
  muret_occultant   idem + toile brise-vue (verte ou grise)
  grillage, grillage_occultant   poteaux + grillage (+ toile), posés sur le terrain ou sur un muret (base_sur_muret_m)
  haie_taillee      volume à flancs droits, feuillage
  portail, pilier, barriere_tube, bloc_beton, boites_aux_lettres, caniveau
  panneau           EB20, panneau temporaire, plaques de rue, panneau d'affichage du départ : mât + plaque
Usage : python scripts/37_clotures.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from acr_geo import OUT, RAW, REF, ROOT  # noqa: E402

_s = importlib.util.spec_from_file_location("route_ouvrages", ICI / "11_route_ouvrages.py")
m11 = importlib.util.module_from_spec(_s); _s.loader.exec_module(m11)
m08 = m11.m08

MOD = ROOT / "modele"
CC0 = RAW / "cc0"
RAYON_COLLISION_M = 15.0
PIED = 0.3                # m enterrés sous le terrain
PAS_POTEAUX = 2.5

# matière -> (rendu, collision). Couleurs relevées sur les photos (sRGB 0-255) quand pas d'image.
TEINTES = {"enduit_beige": (222, 205, 176), "enduit_rose": (214, 178, 150), "blanc": (232, 230, 222),
           "metal_gris": (118, 120, 122), "vert": (58, 92, 64), "bleu": (40, 98, 150), "brun": (96, 70, 48),
           "fer_noir": (38, 38, 40), "pierre": (150, 140, 124)}
ASSETS_JEU = {
    "pierre_seche": "matière du jeu MI_MonBolStoneWallsA (pierre claire de Bollène, déjà utilisée par les parapets) "
                    "sur notre géométrie ; texture libre old_stone_wall dans l'export neutre",
    "grillage": "matière du jeu MI_ChainlinkFenceA1 (grillage ajouré, masqué) sur notre géométrie ; maillages "
                "SM_ChainlinkFenceA1..11 du jeu non utilisés (longueur de module inconnue, à mesurer)",
    "haie": "aucun : SM_CypressHedge01 existe dans le jeu (haie de cyprès) mais ses dimensions ne sont pas relevées",
    "portail": "aucun asset posé : SM_FarmGateA, SM_FraChaGateA/B, SM_FraSavGateB1/B2 existent dans le jeu, "
               "dimensions non relevées",
}


# ----------------------------------------------------------------------------------------------- textures
def _jpeg(im, q=88):
    b = io.BytesIO(); im.convert("RGB").save(b, "JPEG", quality=q); return b.getvalue()


def _png(im):
    b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()


def tex_cc0(nom, teinte=None, px=512, gain=1.0):
    p = CC0 / f"{nom}_diff.jpg"
    im = Image.open(p).convert("RGB").resize((px, px), Image.LANCZOS)
    a = np.asarray(im).astype(float) * gain
    if teinte is not None:
        lum = a.mean(2, keepdims=True)
        a = lum / max(lum.mean(), 1) * np.array(teinte)[None, None, :] * 0.5 + a * 0.5
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def tex_grillage(px=256, maille=8, fil=2, couleur=(52, 86, 58)):
    """Grillage simple torsion : losanges de `maille` px (1 répétition = 0,5 m : maille de 5 cm), fond transparent."""
    im = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pas = px // (px // (maille * 4)) // 2 * 2 if px >= maille * 4 else maille
    pas = px // 10
    for k in range(-px, 2 * px, pas):
        d.line([(k, 0), (k + px, px)], fill=couleur + (255,), width=fil)
        d.line([(k, px), (k + px, 0)], fill=couleur + (255,), width=fil)
    return im


def tex_occultant(couleur=(46, 78, 56), px=256, seed=3):
    rng = np.random.default_rng(seed)
    a = np.ones((px, px, 3)) * np.array(couleur)
    tr = (np.arange(px) % 4 < 2)[None, :, None] * 8.0          # tissage
    a = a + tr - 4 + rng.normal(0, 5, (px, px, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def tex_haie(px=256, seed=5):
    rng = np.random.default_rng(seed)
    a = rng.random((px, px))
    im = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))
    v = np.asarray(im).astype(float) / 255
    base = np.array([44, 66, 38]); clair = np.array([88, 112, 60])
    rgb = base[None, None] * (1 - v[..., None]) + clair[None, None] * v[..., None]
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def tex_unie(c, px=8):
    return Image.new("RGB", (px, px), tuple(c))


def tex_grille_fer(px=256):
    im = Image.new("RGBA", (px, px), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for k in range(0, px, px // 8):
        d.rectangle([k, 0, k + 5, px], fill=(38, 38, 40, 255))
    d.rectangle([0, 0, px, 8], fill=(38, 38, 40, 255)); d.rectangle([0, px - 8, px, px], fill=(38, 38, 40, 255))
    return im


# ----------------------------------------------------------------------------------------------- glb (images PNG/JPEG, masque)
def ecrire_glb(path, meshes, mats):
    """meshes : dict(name, pos (N,3) glTF, nrm, uv, idx, mat) ; mats : nom -> dict(img octets, mime, alpha, double, rough)."""
    gl = {"asset": {"version": "2.0", "generator": "37_clotures.py"}, "scenes": [{"nodes": []}], "scene": 0,
          "nodes": [], "meshes": [], "materials": [], "accessors": [], "bufferViews": [], "buffers": []}
    blob = bytearray()

    def view(data, target=None):
        while len(blob) % 4:
            blob.append(0)
        v = {"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)}
        if target:
            v["target"] = target
        blob.extend(data); gl["bufferViews"].append(v); return len(gl["bufferViews"]) - 1

    def acc(arr, kind, ctype, target, minmax=False):
        a = {"bufferView": view(arr.tobytes(), target), "componentType": ctype, "count": len(arr), "type": kind}
        if minmax:
            a["min"] = arr.min(0).tolist(); a["max"] = arr.max(0).tolist()
        gl["accessors"].append(a); return len(gl["accessors"]) - 1

    idx_mat = {}
    for nom, d in mats.items():
        m = {"name": nom, "pbrMetallicRoughness": {"metallicFactor": d.get("metal", 0.0), "roughnessFactor": d.get("rough", 0.9)}}
        if "img" in d:
            gl.setdefault("images", []).append({"bufferView": view(d["img"]), "mimeType": d["mime"]})
            gl.setdefault("samplers", [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}])
            gl.setdefault("textures", []).append({"sampler": 0, "source": len(gl["images"]) - 1})
            m["pbrMetallicRoughness"]["baseColorTexture"] = {"index": len(gl["textures"]) - 1}
        if d.get("alpha"):
            m["alphaMode"] = "MASK"; m["alphaCutoff"] = 0.5
        if d.get("double"):
            m["doubleSided"] = True
        idx_mat[nom] = len(gl["materials"]); gl["materials"].append(m)
    for me in meshes:
        pos = me["pos"].astype(np.float32); nrm = me["nrm"].astype(np.float32)
        uv = me["uv"].astype(np.float32); idx = me["idx"].astype(np.uint32).ravel()
        pr = {"attributes": {"POSITION": acc(pos, "VEC3", 5126, 34962, True), "NORMAL": acc(nrm, "VEC3", 5126, 34962),
                             "TEXCOORD_0": acc(uv, "VEC2", 5126, 34962)},
              "indices": acc(idx, "SCALAR", 5125, 34963), "material": idx_mat[me["mat"]], "mode": 4}
        gl["meshes"].append({"name": me["name"], "primitives": [pr]})
        gl["nodes"].append({"name": me["name"], "mesh": len(gl["meshes"]) - 1})
        gl["scenes"][0]["nodes"].append(len(gl["nodes"]) - 1)
    while len(blob) % 4:
        blob.append(0)
    gl["buffers"].append({"byteLength": len(blob)})
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob))
    out += struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(blob), 0x004E4942) + bytes(blob)
    Path(path).write_bytes(out)


# ----------------------------------------------------------------------------------------------- formes
class Terrain:
    def __init__(self):
        import rasterio
        with rasterio.open(RAW / "mnt_lidarhd_50cm.tif") as s:
            self.a, self.inv = s.read(1), ~s.transform

    def z(self, x, y):
        c, r = self.inv * (np.asarray(x, float), np.asarray(y, float))
        r = np.clip(np.floor(r).astype(int), 0, self.a.shape[0] - 1); c = np.clip(np.floor(c).astype(int), 0, self.a.shape[1] - 1)
        return self.a[r, c].astype(float)


def normales_ext(P, cote):
    t = np.gradient(P, axis=0)
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
    n = np.column_stack([-t[:, 1], t[:, 0]])               # gauche du sens de la montée
    return n if cote == "gauche" else -n, t


def ruban(P, n, o0, o1, z0, z1, ref, s_uv=2.0, caps=True, haut=True):
    """Volume balayé le long de la polyligne P (N,2) entre les décalages o0 et o1 (le long de n) et les altitudes z0,
    z1 (N,) : faces côté route, arrière, dessus (et bouts). UV en mètres / s_uv."""
    N = len(P)
    if N < 2:
        return None
    A = np.column_stack([P + n * o0, z0]); Bk = np.column_stack([P + n * o1, z0])
    C = np.column_stack([P + n * o1, z1]); D = np.column_stack([P + n * o0, z1])
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    parts = []
    sg = 1.0 if o1 >= o0 else -1.0
    nz = np.column_stack([n, np.zeros(N)])
    faces = [(A, D, -sg * nz), (C, Bk, sg * nz)] + ([(D, C, np.tile([0, 0, 1.0], (N, 1)))] if haut else [])
    for Q0, Q1, ext in faces:
        pos = np.vstack([Q0, Q1])
        i = np.arange(N - 1)
        tri = np.concatenate([np.column_stack([i, N + i, N + i + 1]), np.column_stack([i, N + i + 1, i + 1])])
        hgt = np.linalg.norm(Q1 - Q0, axis=1)
        uv = np.column_stack([np.concatenate([L, L]), np.concatenate([np.zeros(N), hgt])]) / s_uv
        parts.append((pos, tri, uv, np.vstack([ext, ext])))
    if caps:
        tt = np.gradient(P, axis=0)
        for j, sgn in ((0, -1.0), (-1, 1.0)):
            pos = np.array([A[j], Bk[j], C[j], D[j]])
            tri = np.array([[0, 1, 2], [0, 2, 3]])
            w = abs(o1 - o0); h = float(np.max(z1 - z0))
            uv = np.array([[0, 0], [w, 0], [w, h], [0, h]]) / s_uv
            e = np.array([*(sgn * tt[j] / max(np.linalg.norm(tt[j]), 1e-9)), 0.0])
            parts.append((pos, tri, uv, np.tile(e, (4, 1))))
    return assemble(parts, ref)


def assemble(parts, ref):
    """parts : (positions L93, triangles, UV, direction extérieure L93 par sommet). Chaque triangle est orienté vers
    sa direction extérieure (une orientation par rapport au centre du volume se trompe sur un mur long et courbe)."""
    pos, tri, uv, ext, off = [], [], [], [], 0
    for p, t, u, x in parts:
        pos.append(p); tri.append(t + off); uv.append(u); ext.append(x); off += len(p)
    pos = np.vstack(pos); tri = np.vstack(tri); uv = np.vstack(uv); ext = np.vstack(ext)
    G = m08.to_gltf(pos, ref).astype(np.float64)
    E = np.column_stack([ext[:, 0], ext[:, 2], -ext[:, 1]])
    f = np.cross(G[tri[:, 1]] - G[tri[:, 0]], G[tri[:, 2]] - G[tri[:, 0]])
    inv = (f * E[tri].mean(1)).sum(1) < 0
    tri[inv] = tri[inv][:, ::-1]
    # sommets propres à chaque triangle : arêtes vives
    P2 = G[tri].reshape(-1, 3); U2 = uv[tri].reshape(-1, 2)
    T2 = np.arange(len(P2)).reshape(-1, 3)
    return {"pos": P2, "nrm": m08.normales(P2, T2), "uv": U2, "idx": T2}


def plaque(P, n, o, z0, z1, ref, s_uv=1.0):
    """Surface simple (grillage, toile, portail) le long de P au décalage o, double face (matière doubleSided)."""
    N = len(P)
    Q0 = np.column_stack([P + n * o, z0]); Q1 = np.column_stack([P + n * o, z1])
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    pos = np.vstack([Q0, Q1]); i = np.arange(N - 1)
    tri = np.concatenate([np.column_stack([i, N + i, N + i + 1]), np.column_stack([i, N + i + 1, i + 1])])
    uv = np.column_stack([np.concatenate([L, L]), np.concatenate([np.zeros(N), z1 - z0])]) / s_uv
    G = m08.to_gltf(pos, ref)
    return {"pos": G, "nrm": m08.normales(G, tri), "uv": uv, "idx": tri}


def poteaux(P, n, o, z0, z1, ref, cote_m=0.05, pas=PAS_POTEAUX):
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    out = []
    for s in np.arange(0, L[-1] + 1e-6, pas).tolist() + ([L[-1]] if L[-1] % pas > 0.3 else []):
        k = int(np.clip(np.searchsorted(L, s), 1, len(P) - 1))
        a = (s - L[k - 1]) / max(L[k] - L[k - 1], 1e-9)
        c = P[k - 1] + a * (P[k] - P[k - 1]); za = z0[k - 1] + a * (z0[k] - z0[k - 1]); zb = z1[k - 1] + a * (z1[k] - z1[k - 1])
        t = (P[k] - P[k - 1]) / max(np.linalg.norm(P[k] - P[k - 1]), 1e-9)
        Q = np.array([c - t * cote_m / 2, c + t * cote_m / 2])
        nn = np.array([n[k], n[k]])
        out.append(ruban(Q, nn, o - cote_m / 2, o + cote_m / 2, np.array([za, za]), np.array([zb, zb]), ref, 1.0))
    return [x for x in out if x]


def fusion(parts, nom, mat):
    parts = [p for p in parts if p is not None]
    if not parts:
        return None
    pos = np.vstack([p["pos"] for p in parts]); nrm = np.vstack([p["nrm"] for p in parts]); uv = np.vstack([p["uv"] for p in parts])
    off = np.cumsum([0] + [len(p["pos"]) for p in parts]); idx = np.vstack([p["idx"] + off[i] for i, p in enumerate(parts)])
    return {"name": nom, "pos": pos, "nrm": nrm, "uv": uv, "idx": idx, "mat": mat}


def densifier(P, pas=1.0):
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    if L[-1] < 1e-6:
        return P
    s = np.linspace(0, L[-1], max(2, int(np.ceil(L[-1] / pas)) + 1))
    return np.column_stack([np.interp(s, L, P[:, 0]), np.interp(s, L, P[:, 1])])


def matiere_muret(e):
    m = e.get("muret", "pierre")
    return {"pierre": "pierre_seche", "beton": "beton", "enduit_rose": "enduit_rose"}.get(m, "pierre_seche")


def pied_de_mur(P, n, T, h, ep):
    """Mur (de soutènement ou non) : le MNT lisse la marche d'un mur en talus sur 1 à 1,5 m ; sans précaution le mur
    posé au milieu de la pente disparaît dans le terrain (vu au départ le 18/11/2026). La face est ramenée au pied de la
    montée (premier point, en allant du bord vers l'extérieur, plus haut de 0,3 m que le terrain 1,5 m devant), le pied
    part du terrain devant la face et le dessus dépasse de 0,15 m le terrain derrière le mur (talus couvert)."""
    offs = np.arange(-1.5, 1.01, 0.25)
    Z = np.stack([T.z(*(P + n * o).T) for o in offs], 1)            # (N, k)
    z_av = Z[:, 0]
    monte = Z - z_av[:, None] > 0.3
    k = np.where(monte.any(1), monte.argmax(1), len(offs) - 1)
    o_face = np.minimum(offs[np.clip(k - 1, 0, None)], 0.0)
    o_face = np.where(monte.any(1), o_face, 0.0)
    o_face = np.convolve(np.pad(o_face, 3, mode="edge"), np.ones(7) / 7, mode="valid")
    P2 = P + n * o_face[:, None]
    zb = np.minimum(T.z(*(P2 - n * 0.3).T), T.z(*P2.T))
    derriere = T.z(*(P2 + n * (ep + 0.5)).T)
    top = np.maximum(zb + h, derriere + 0.15)
    return P2, zb, top


def construire(e, T, ref):
    """-> liste de (maillage, matière de collision ou None)."""
    P = densifier(np.array(e["trace_l93"], float))
    if len(P) < 2:
        P = np.array([P[0], P[0] + 0.01])
    n, t = normales_ext(P, e["cote"])
    zr = T.z(*(P - n * 0.3).T)                   # terrain côté route, 0,3 m devant le pied
    zp = T.z(*P.T)
    zb = np.minimum(zr, zp)                      # le mur part du plus bas des deux : pas de pied en l'air
    h = float(e["hauteur_m"]); ty = e["type"]; nom = e["id"]
    base = float(e.get("base_sur_muret_m", 0.0))
    out = []
    # hauteur relevée = hauteur vue depuis le pied côté route ; le dessus dépasse toujours le terrain arrière de 0,2 m
    # (un mur de soutènement retient un terrain plus haut : sa hauteur visible part du pied, pas du haut du talus)
    top = np.maximum(zr, zp + 0.2 - h)
    if ty == "pierre_seche":
        P2, zb2, top2 = pied_de_mur(P, n, T, h, 0.5 if h > 1.2 else 0.45)
        ep = 0.5 if h > 1.2 else 0.45
        out.append((fusion([ruban(P2, n, 0, ep, zb2 - PIED, top2 - 0.08, ref, 2.0)], f"{nom}_corps", "pierre_seche"), ("pierre", (P2, n, 0, ep, zb2 - PIED, top2))))
        out.append((fusion([ruban(P2, n, -0.03, ep + 0.03, top2 - 0.08, top2, ref, 2.0)], f"{nom}_couronnement", "pierre_couronnement"), None))
    elif ty == "mur_enduit":
        mat = {"blanc": "enduit_blanc", "enduit_rose": "enduit_rose"}.get(e.get("teinte"), "enduit_beige")
        P2, zb2, top2 = pied_de_mur(P, n, T, h, 0.25)
        out.append((fusion([ruban(P2, n, 0, 0.25, zb2 - PIED, top2 - 0.06, ref, 2.0)], f"{nom}_corps", mat), ("beton", (P2, n, 0, 0.25, zb2 - PIED, top2))))
        out.append((fusion([ruban(P2, n, -0.03, 0.28, top2 - 0.06, top2, ref, 1.0)], f"{nom}_chaperon", mat), None))
    elif ty in ("muret_grillage", "muret_occultant", "grillage", "grillage_occultant"):
        mh = float(e.get("muret_h", 0.0)) if ty.startswith("muret") else base
        if ty.startswith("muret"):
            mm = matiere_muret(e)
            out.append((fusion([ruban(P, n, 0, 0.4, zb - PIED, top + mh, ref, 2.0)], f"{nom}_muret", mm),
                        ("pierre" if mm == "pierre_seche" else "beton", (P, n, 0, 0.4, zb - PIED, top + mh))))
        o = 0.2 if (ty.startswith("muret") or base > 0) else 0.0
        z0 = top + mh; z1 = top + h
        if not ty.startswith("muret"):
            # grillage seul : h est sa propre hauteur, posé sur le terrain ou sur un muret de base_sur_muret_m
            z0 = zp - 0.05 if base == 0 else top + base
            z1 = z0 + h
        zpied = z0 - PIED if (base == 0 and not ty.startswith("muret")) else z0
        out.append((fusion(poteaux(P, n, o, zpied, z1, ref), f"{nom}_poteaux", "poteau_vert"), None))
        out.append((fusion([plaque(P, n, o, z0 + 0.03, z1 - 0.03, ref, 0.5)], f"{nom}_grillage", "grillage"), ("cloture", (P, n, o - 0.05, o + 0.05, z0, z1))))
        if "occultant" in ty:
            mat = "occultant_gris" if e.get("teinte") == "gris" else "occultant_vert"
            out.append((fusion([plaque(P, n, o + 0.03, z0 + 0.05, z1 - 0.05, ref, 1.0)], f"{nom}_toile", mat), None))
    elif ty == "haie_taillee":
        out.append((fusion([ruban(P, n, 0.05, 0.85, zp - 0.1 + base, top + base + h, ref, 1.5)], f"{nom}_haie", "haie"), ("haie", (P, n, 0.05, 0.85, zp - 0.1 + base, top + base + h))))
    elif ty == "portail":
        mat = "grille_fer" if e.get("ajouree") else f"portail_{e.get('teinte', 'metal_gris')}"
        out.append((fusion([plaque(P, n, 0.1, zp + 0.05, zp + h, ref, h)], f"{nom}_portail", mat), ("cloture", (P, n, 0.05, 0.15, zp - 0.1, zp + h))))
    elif ty == "pilier":
        c = P.mean(0); tt = t[0]
        Q = np.array([c - tt * 0.2, c + tt * 0.2]); nn = np.array([n[0], n[0]])
        zz = float(T.z(*c)); te = e.get("teinte", "blanc")
        mat = {"pierre": "pierre_seche", "enduit_beige": "enduit_beige", "enduit_rose": "enduit_rose"}.get(te, "enduit_blanc")
        out.append((fusion([ruban(Q, nn, -0.05, 0.35, np.full(2, zz - PIED), np.full(2, zz + h), ref, 1.0)], f"{nom}_pilier", mat), ("beton", (Q, nn, -0.05, 0.35, np.full(2, zz - PIED), np.full(2, zz + h)))))
        out.append((fusion([ruban(Q + 0, nn, -0.08, 0.38, np.full(2, zz + h), np.full(2, zz + h + 0.06), ref, 1.0)], f"{nom}_chapeau", mat), None))
    elif ty == "barriere_tube":
        parts = poteaux(P, n, 0.1, zp - PIED, zp + h, ref, 0.08, 4.0)
        for hh in (0.5, 0.95):
            parts.append(ruban(P, n, 0.07, 0.13, zp + hh * h - 0.03, zp + hh * h + 0.03, ref, 1.0))
        out.append((fusion(parts, f"{nom}_barriere", "tube_blanc"), ("cloture", (P, n, 0.05, 0.15, zp - 0.1, zp + h))))
    elif ty == "bloc_beton":
        out.append((fusion([ruban(P, n, 0, 0.6, zb - 0.1, top + h, ref, 1.0)], f"{nom}_bloc", "beton_blanc"), ("beton", (P, n, 0, 0.6, zb - 0.1, top + h))))
    elif ty == "boites_aux_lettres":
        c = P[0]; tt = t[0]; zz = float(T.z(*c)); nn = np.array([n[0], n[0]])
        parts = [ruban(np.array([c - tt * 0.03, c + tt * 0.03]), nn, -0.03, 0.03, np.full(2, zz - PIED), np.full(2, zz + 0.9), ref, 1.0)]
        for k in range(4):
            q = c + tt * (-0.6 + 0.4 * k)
            parts.append(ruban(np.array([q - tt * 0.17, q + tt * 0.17]), nn, -0.15, 0.15, np.full(2, zz + 0.9), np.full(2, zz + 1.3), ref, 0.5))
        out.append((fusion(parts, f"{nom}_boites", "boite"), None))
    elif ty == "caniveau":
        out.append((fusion([ruban(P, n, -0.15, 0.35, zp - 0.2, zp + 0.05, ref, 1.0)], f"{nom}_caniveau", "beton"), None))
    return out


def panneau(e, B, T, ref):
    """Objets ponctuels du départ : mât(s) + plaque, d'après la photo citée (forme et texte redessinés simplement)."""
    m = e.get("modele")
    P0 = np.array(e["position_l93"], float)
    zz = float(T.z(*P0))
    # orientation : plaque face à la route (normale = vers l'axe)
    pk = float(e["pk_m"])
    t = np.array([np.interp(pk + 1, B.pk, B.A[:, 0]) - np.interp(pk - 1, B.pk, B.A[:, 0]),
                  np.interp(pk + 1, B.pk, B.A[:, 1]) - np.interp(pk - 1, B.pk, B.A[:, 1])])
    t /= np.linalg.norm(t)
    nn = np.array([[-t[1], t[0]]] * 2) * (1 if e["cote"] == "gauche" else -1)
    out = []
    if e["type"] == "regard" or m is None:
        return out
    if m == "EB20":
        L, H, hb = 1.3, 0.5, 1.6        # plaque 1,3 x 0,5 m, bas à 1,6 m, portique de deux tubes verts
        tex = "plaque_EB20"
    elif m == "KD_jaune":
        L, H, hb = 0.8, 1.1, 0.7; tex = "plaque_jaune"
    elif m == "plaques_rue":
        L, H, hb = 0.7, 0.45, 2.0; tex = "plaque_rue"
    else:
        L, H, hb = 3.0, 1.5, 1.5; tex = "plaque_affichage"
    for s in (-L / 2 + 0.05, L / 2 - 0.05) if m in ("EB20", "affichage") else (0.0,):
        c = P0 + t * s
        out.append((fusion([ruban(np.array([c - t * 0.03, c + t * 0.03]), nn, -0.03, 0.03, np.full(2, zz - PIED),
                                  np.full(2, zz + hb + H + 0.1), ref, 1.0)], f"{e['id']}_mat{len(out)}", "poteau_vert" if m == "EB20" else "tube_gris"), None))
    Q = np.array([P0 - t * L / 2, P0 + t * L / 2])
    out.append((fusion([ruban(Q, nn, -0.06, -0.04, np.full(2, zz + hb), np.full(2, zz + hb + H), ref, L)], f"{e['id']}_plaque", tex), None))
    return out


def plaques():
    """Faces des plaques du départ, redessinées d'après les photos (pas de logo ni de texte inventé)."""
    try:
        f = ImageFont.truetype("DejaVuSans-Bold.ttf", 64)
        fs = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    except OSError:
        f = fs = ImageFont.load_default()
    eb = Image.new("RGB", (520, 200), (245, 245, 240)); d = ImageDraw.Draw(eb)
    d.rectangle([6, 6, 513, 193], outline=(200, 20, 30), width=10)
    d.text((260, 100), "CEYRESTE", fill=(20, 20, 20), font=f, anchor="mm")
    d.line([(20, 185), (500, 15)], fill=(200, 20, 30), width=16)
    jaune = Image.new("RGB", (160, 220), (240, 200, 20)); d = ImageDraw.Draw(jaune)
    d.rectangle([4, 4, 155, 215], outline=(20, 20, 20), width=4)
    rue = Image.new("RGB", (280, 180), (30, 70, 150)); d = ImageDraw.Draw(rue)
    for k, txt in enumerate(("Route du", "Grand Caunet", "CD 3")):
        d.text((140, 35 + 50 * k), txt, fill=(240, 240, 240), font=fs, anchor="mm")
    aff = Image.new("RGB", (300, 150), (205, 200, 190)); d = ImageDraw.Draw(aff)
    d.rectangle([0, 0, 299, 149], outline=(60, 60, 60), width=6)
    # Unreal (et 16_paquet_unreal.py) exige des textures en puissances de 2
    p2 = lambda im, w, h: im.resize((w, h), Image.LANCZOS)          # noqa: E731
    return {"plaque_EB20": p2(eb, 512, 256), "plaque_jaune": p2(jaune, 256, 256), "plaque_rue": p2(rue, 256, 256),
            "plaque_affichage": p2(aff, 256, 128)}


def matieres():
    img = lambda im, a=False, dbl=False, rough=0.9, metal=0.0: {"img": _png(im) if a else _jpeg(im), "mime": "image/png" if a else "image/jpeg",  # noqa: E731
                                                            "alpha": a, "double": dbl, "rough": rough, "metal": metal}
    M = {
        "pierre_seche": img(tex_cc0("old_stone_wall", (160, 154, 142), gain=1.05)),
        "pierre_couronnement": img(tex_cc0("old_stone_wall", (172, 166, 152), gain=1.15)),
        "enduit_beige": img(tex_cc0("white_plaster_rough_01", TEINTES["enduit_beige"])),
        "enduit_rose": img(tex_cc0("white_plaster_rough_01", TEINTES["enduit_rose"])),
        "enduit_blanc": img(tex_cc0("white_plaster_rough_01", TEINTES["blanc"])),
        "beton": img(tex_cc0("white_plaster_rough_01", (175, 172, 165))),
        "beton_blanc": img(tex_cc0("white_plaster_rough_01", (225, 223, 215))),
        "grillage": img(tex_grillage(), a=True, dbl=True, rough=0.6),
        "occultant_vert": img(tex_occultant(), dbl=True),
        "occultant_gris": img(tex_occultant((150, 152, 150)), dbl=True),
        "haie": img(tex_haie()),
        "poteau_vert": img(tex_unie((52, 86, 58)), rough=0.6),
        "tube_blanc": img(tex_unie((228, 228, 224)), rough=0.5),
        "tube_gris": img(tex_unie((140, 142, 145)), rough=0.5),
        "grille_fer": img(tex_grille_fer(), a=True, dbl=True, rough=0.5),
        "boite": img(tex_unie((200, 196, 186)), rough=0.6),
    }
    for k in ("metal_gris", "vert", "bleu", "brun", "fer_noir"):
        M[f"portail_{k}"] = img(tex_unie(TEINTES[k]), dbl=True, rough=0.6)
    for k, im in plaques().items():
        M[k] = img(im, dbl=True, rough=0.5)
    return M


def boite_collision(P, n, o0, o1, z0, z1, ref):
    """Volume de collision au format de 11_route_ouvrages.boite() (4 polylignes de coins, sommets C0C1, C1C2, C2C3, C3C0
    puis deux bouchons), le seul que 09_export_stage_ir.py sait découper en pavés."""
    z0 = np.broadcast_to(np.asarray(z0, float), (len(P),)); z1 = np.broadcast_to(np.asarray(z1, float), (len(P),))
    # points à moins de 0,2 m du précédent écartés : 09 arrondit les dimensions au 0,1 mm, un pavé de longueur nulle
    # y donne une division par zéro (vu le 18/11/2026)
    garde = np.concatenate([[True], np.linalg.norm(np.diff(P, axis=0), axis=1) > 0.2])
    if garde.sum() < 2:
        garde[-1] = True
    P, n, z0, z1 = P[garde], n[garde], z0[garde], z1[garde]
    if np.linalg.norm(P[-1] - P[0]) < 0.05:
        return None
    lo, hi = min(o0, o1), max(o0, o1)
    C0 = np.column_stack([P + n * lo, z0]); C1 = np.column_stack([P + n * hi, z0])
    C2 = np.column_stack([P + n * hi, z1]); C3 = np.column_stack([P + n * lo, z1])
    return m11.boite([C0, C1, C2, C3], ref)


COLL_MAT = {"pierre": "pierre", "beton": "beton", "cloture": "cloture", "haie": "haie"}


def main():
    _s29 = importlib.util.spec_from_file_location("r36", ICI / "36_releve_clotures.py")
    r36 = importlib.util.module_from_spec(_s29); _s29.loader.exec_module(r36)
    B = r36.Bord()
    doc = json.loads((REF / "clotures_murets.json").read_text(encoding="utf-8"))
    ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    T = Terrain()
    meshes, coll = [], {}
    bilan = {"par_type_et_cote_m": {}, "nombre_par_type": {}, "cale_au_metre_m": 0.0, "photo_m": 0.0, "collision": 0,
             "elements": []}
    for e in doc["elements"]:
        res = construire(e, T, ref)
        L = float(e["longueur_m"]) if e["type"] not in ("pilier", "boites_aux_lettres") else 0.0
        k = f"{e['type']} {e['cote']}"
        bilan["par_type_et_cote_m"][k] = round(bilan["par_type_et_cote_m"].get(k, 0) + L, 1)
        bilan["nombre_par_type"][e["type"]] = bilan["nombre_par_type"].get(e["type"], 0) + 1
        bilan["cale_au_metre_m" if e["calage"].startswith("au mètre") else "photo_m"] += L
        proche = float(e["recul_applique_m"][0]) < RAYON_COLLISION_M
        for m, c in res:
            if m is None:
                continue
            meshes.append(m)
            if c and proche:
                b = boite_collision(*c[1], ref)
                if b is not None:
                    coll.setdefault(COLL_MAT[c[0]], []).append(b)
        if proche and any(c for _, c in res):
            bilan["collision"] += 1
        bilan["elements"].append({"id": e["id"], "type": e["type"], "cote": e["cote"], "pk": [e["pk_debut_m"], e["pk_fin_m"]],
                                  "longueur_m": L, "calage": e["calage"], "images": e["images"],
                                  "collision": bool(proche and any(c for _, c in res))})
    for e in doc.get("ponctuels", []):
        for m, _ in panneau(e, B, T, ref):
            meshes.append(m)
    M = matieres()
    used = {m["mat"] for m in meshes}
    ecrire_glb(MOD / "clotures.glb", meshes, {k: v for k, v in M.items() if k in used})
    cm = [m11.fusion(v, f"clotures_{k}_collision", k) for k, v in coll.items()]
    m11.ecrire_glb(MOD / "clotures_collision.glb", cm, {k: {"color": [0.7, 0.7, 0.68]} for k in coll})
    bilan["cale_au_metre_m"] = round(bilan["cale_au_metre_m"], 1); bilan["photo_m"] = round(bilan["photo_m"], 1)
    bilan["assets_du_jeu"] = ASSETS_JEU
    bilan["maillages"] = len(meshes); bilan["triangles"] = int(sum(len(m["idx"]) for m in meshes))
    (OUT / "clotures_bilan.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(meshes)} maillages, {bilan['triangles']} triangles ; collision : {bilan['collision']} éléments ; "
          f"calé au mètre {bilan['cale_au_metre_m']} m, photo {bilan['photo_m']} m")


if __name__ == "__main__":
    main()
