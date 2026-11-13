"""Étape 11 - Habillage de la route (enrobé, marquage) et ouvrages (tabliers, parapets).

Entrées : data/processed/chaussee_precise.csv (relu à chaque exécution), ouvrages_es.csv,
          axe_bdtopo_l93.csv, couloir/construction_lineaire.geojson, data/raw/mnt_lidarhd_50cm.tif,
          data/reference/marquage_route.json (tronçons de marquage par PK, provenance de chaque valeur),
          data/reference/ouvrages_parapets.json (type, hauteur, épaisseur des parapets, ouvrage par ouvrage),
          modele/repere.json (repère commun avec terrain.glb)
Sorties (modele/, et modele/apercu/ en léger) :
  route_habillee.glb      la chaussée de 08_modele_3d.py (mêmes sommets, mêmes triangles) avec une
                          texture d'enrobé procédurale répétée (UV métriques : u = décalage latéral,
                          v = PK, même échelle) et le marquage en fines bandes 1,5 cm au-dessus.
                          route.glb (écrit par 08) n'est pas écrasé : relancer 08 ne défait rien ici.
  ouvrages.glb            par tablier détecté : dalle épaisse fermée (faces, sous-face, abouts),
                          culées jusqu'au sol, parapets (pierre à dés blancs, pierre, béton)
  ouvrages_collision.glb  (modele/ seulement) parapets et murs en volumes simples, un maillage
                          et un matériau par type : pierre, béton
  figures/phase4/route_*.png  rendus three.js (Chromium de Playwright), comme 08_modele_3d.py

Textures : bruit périodique construit par FFT (répétable sans couture), aucune ressource externe.
Les fonctions de lecture, de détection des tabliers et de repère viennent de 08_modele_3d.py.
"""
import importlib.util
import io
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
from PIL import Image
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Polygon

from acr_geo import FIG, OUT, REF, ROOT, l93

_spec = importlib.util.spec_from_file_location("modele_3d", Path(__file__).with_name("08_modele_3d.py"))
m08 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m08)

MOD = ROOT / "modele"
FIG4 = FIG / "phase4"
VERSIONS = {"complet": 1024, "apercu": 512}   # px des textures
S_ENROBE = 4.0        # m couverts par une répétition de la texture d'enrobé
S_PAROI = 2.0         # m couverts par une répétition des textures pierre / béton
DALLE_EP = 0.6        # m : épaisseur du tablier sous le bord de chaussée
DALLE_RETRAIT = 0.03  # m : dessus de la dalle sous la chaussée (évite le scintillement)
CORNICHE = 0.3        # m : débord de la dalle côté sans parapet
DALLE_DEBORD = 2      # m (rangs) : la dalle entre dans le remblai à chaque bout
CHAPERON = 0.08       # m : hauteur du chaperon (couronnement)
RAYON_T3_M = 140.0    # m : sous ce rayon, l'axiale discontinue passe en traits rapprochés (T3)
BISEAU_M, BISEAU_BAS = 1.0, 0.3   # extrémités des parapets : biseau d'un mètre, partant de 30 % de la hauteur
DES_PAS, DES_LONG = 3.5, 0.35   # m : dés blancs (supposé : 3 à 4 m sur la vidéo)
MUR_DIST_MAX = 15.0   # m : murs BD TOPO retenus à moins de cette distance de l'axe


# --- textures procédurales (périodiques) -------------------------------------------
def _spectre(n):
    k = np.fft.fftfreq(n)
    return np.hypot(*np.meshgrid(k, k))


def bruit(n, rng, pente):
    """Bruit périodique n x n, spectre en 1/f^pente, centré réduit."""
    f = _spectre(n)
    f[0, 0] = 1
    a = np.real(np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) / f ** pente))
    return (a - a.mean()) / a.std()


def flou(a, sigma):
    """Flou gaussien circulaire (garde la périodicité)."""
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2 * (np.pi * sigma * _spectre(len(a))) ** 2)))


def jpeg(rgb, q=85):
    buf = io.BytesIO()
    Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(buf, "JPEG", quality=q, optimize=True)
    return buf.getvalue()


def tex_enrobe(n, seed=11):
    """Béton bitumineux usé : marbrure lente, grain, gravillons clairs, pores sombres."""
    rng = np.random.default_rng(seed)
    px = S_ENROBE / n
    v = 0.36 + 0.015 * bruit(n, rng, 2.0) + 0.015 * bruit(n, rng, 1.0)
    v += 0.05 * flou(rng.standard_normal((n, n)), 0.6)
    grav = flou((rng.random((n, n)) < 0.035 * (px / 0.004) ** 2).astype(float), 0.004 / px * 0.6)
    pores = flou((rng.random((n, n)) < 0.02 * (px / 0.004) ** 2).astype(float), 0.004 / px * 0.5)
    v += 0.9 * grav / max(grav.max(), 1e-6) * 0.22 - 0.9 * pores / max(pores.max(), 1e-6) * 0.15
    teinte = 0.003 * bruit(n, rng, 1.5)
    return jpeg(np.dstack([v + teinte, v, v - 0.008 - teinte]))


def tex_pierre(n, seed=5):
    """Moellons calcaires à joints : Voronoï périodique étiré en longueur (pierres ~ 30 x 18 cm)."""
    rng = np.random.default_rng(seed)
    k = int(S_PAROI ** 2 / (0.3 * 0.18))
    pts = rng.random((k, 2)) * [1.0, 1.7]
    tree = cKDTree(pts, boxsize=[1.0, 1.7])
    g = (np.arange(n) + 0.5) / n
    xx, yy = np.meshgrid(g, g * 1.7)
    d, i = tree.query(np.column_stack([xx.ravel(), yy.ravel()]), k=2)
    joint = ((d[:, 1] - d[:, 0]) * n).reshape(n, n)
    couleur = np.array([0.74, 0.71, 0.65]) * (0.8 + 0.3 * rng.random((k, 1))) + 0.012 * rng.standard_normal((k, 3))
    rgb = couleur[i[:, 0]].reshape(n, n, 3) * (1 + 0.06 * bruit(n, rng, 1.2))[..., None]
    rgb *= (1 - 0.15 * np.clip(d[:, 0].reshape(n, n) * n / 40, 0, 1))[..., None]   # pierres bombées
    m = np.clip((joint - 3) / 3, 0, 1)[..., None]                                   # joints
    rgb = rgb * m + np.array([0.58, 0.56, 0.52]) * (1 - m)
    return jpeg(rgb)


def tex_beton(n, seed=7):
    """Béton banché clair : nuages, grain, joints de banche horizontaux tous les 0,5 m."""
    rng = np.random.default_rng(seed)
    v = 0.70 + 0.03 * bruit(n, rng, 1.8) + 0.015 * flou(rng.standard_normal((n, n)), 0.7)
    rows = np.arange(n) % (n // 4)
    v[(rows == 0) | (rows == 1)] -= 0.06
    return jpeg(np.dstack([v, v - 0.005, v - 0.02]))


# --- écriture glb (matériaux partagés, textures répétées) ----------------------------
def ecrire_glb(path, meshes, mats):
    """meshes : dict(name, pos, nrm, uv, idx, mat) ; mats : nom -> dict(color | jpeg, rough)."""
    gl = {"asset": {"version": "2.0", "generator": "acr-grand-caunet 11_route_ouvrages.py"},
          "scene": 0, "scenes": [{"nodes": list(range(len(meshes)))}], "nodes": [], "meshes": [],
          "accessors": [], "bufferViews": [], "materials": [], "buffers": []}
    blob = bytearray()

    def view(data, target=None):
        while len(blob) % 4:
            blob.append(0)
        v = {"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)}
        if target:
            v["target"] = target
        blob.extend(data)
        gl["bufferViews"].append(v)
        return len(gl["bufferViews"]) - 1

    def acc(arr, kind, target, minmax=False):
        a = {"bufferView": view(arr.tobytes(), target),
             "componentType": {np.float32: 5126, np.uint32: 5125, np.uint16: 5123}[arr.dtype.type],
             "count": len(arr), "type": kind}
        if minmax:
            a["min"], a["max"] = arr.min(0).tolist(), arr.max(0).tolist()
        gl["accessors"].append(a)
        return len(gl["accessors"]) - 1

    index = {}
    for nom in dict.fromkeys(m["mat"] for m in meshes):
        d = mats[nom]
        mat = {"name": nom, "pbrMetallicRoughness": {"metallicFactor": 0.0, "roughnessFactor": d.get("rough", 0.9)}}
        if "jpeg" in d:
            gl.setdefault("images", []).append({"bufferView": view(d["jpeg"]), "mimeType": "image/jpeg"})
            gl.setdefault("samplers", [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}])
            gl.setdefault("textures", []).append({"sampler": 0, "source": len(gl["images"]) - 1})
            mat["pbrMetallicRoughness"]["baseColorTexture"] = {"index": len(gl["textures"]) - 1}
        else:
            mat["pbrMetallicRoughness"]["baseColorFactor"] = list(d["color"]) + [1.0]
        gl["materials"].append(mat)
        index[nom] = len(gl["materials"]) - 1
    for m in meshes:
        attrs = {"POSITION": acc(m["pos"].astype(np.float32), "VEC3", 34962, True),
                 "NORMAL": acc(m["nrm"].astype(np.float32), "VEC3", 34962),
                 "TEXCOORD_0": acc(m["uv"].astype(np.float32), "VEC2", 34962)}
        idx = m["idx"].ravel().astype(np.uint16 if len(m["pos"]) < 65536 else np.uint32)   # 16 bits si possible
        prim = {"attributes": attrs, "indices": acc(idx, "SCALAR", 34963),
                "material": index[m["mat"]], "mode": 4}
        gl["meshes"].append({"name": m["name"], "primitives": [prim]})
        gl["nodes"].append({"name": m["name"], "mesh": len(gl["meshes"]) - 1})
    while len(blob) % 4:
        blob.append(0)
    gl["buffers"].append({"byteLength": len(blob)})
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    with open(path, "wb") as f:
        f.write(b"glTF" + np.array([2, 12 + 8 + len(js) + 8 + len(blob)], "<u4").tobytes())
        f.write(np.array([len(js), 0x4E4F534A], "<u4").tobytes() + js)
        f.write(np.array([len(blob), 0x004E4942], "<u4").tobytes() + bytes(blob))


def lire_glb(path):
    """Relit un glb : liste de (nom, positions, normales, uv, indices) ; indices 16 ou 32 bits."""
    b = Path(path).read_bytes()
    n = int(np.frombuffer(b, "<u4", 1, 12)[0])
    gl = json.loads(b[20:20 + n])
    binoff = 20 + n + 8

    def arr(i):
        a = gl["accessors"][i]
        v = gl["bufferViews"][a["bufferView"]]
        dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}[a["componentType"]]
        k = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[a["type"]]
        return np.frombuffer(b, dt, a["count"] * k, binoff + v["byteOffset"]).reshape(-1, k)

    return [(m["name"], arr(m["primitives"][0]["attributes"]["POSITION"]), arr(m["primitives"][0]["attributes"]["NORMAL"]),
             arr(m["primitives"][0]["attributes"]["TEXCOORD_0"]), arr(m["primitives"][0]["indices"]).reshape(-1, 3).astype(np.int64))
            for m in gl["meshes"]]


# --- géométrie commune -------------------------------------------------------------------
class Rangs:
    """Interpolation de l'axe et des bords à un PK quelconque (rangs tous les mètres)."""

    def __init__(self, ch):
        self.ch = ch

    def __call__(self, s):
        s = np.atleast_1d(np.asarray(s, float))
        out = [np.column_stack([np.interp(s, self.ch["pk"], P[:, k]) for k in range(3)])
               for P in (self.ch["A"], self.ch["G"], self.ch["D"])]
        A, G, D = out
        hG = np.linalg.norm((G - A)[:, :2], axis=1)
        hD = np.linalg.norm((D - A)[:, :2], axis=1)
        return A, G, D, hG, hD

    def point(self, s, o, dz=0.0):
        """Point de la chaussée au PK s, à o m de l'axe (o > 0 vers la droite), dz au-dessus."""
        A, G, D, hG, hD = self(s)
        o = np.broadcast_to(o, s.shape).astype(float)
        f = np.where(o >= 0, o / hD, -o / hG)
        B = np.where((o >= 0)[:, None], D, G)
        P = A + f[:, None] * (B - A)
        P[:, 2] += dz
        return P

    def bord(self, s, cote):
        """Bord de chaussée (G ou D) au PK s et normale horizontale sortante."""
        A, G, D, _, _ = self(s)
        E = G if cote == "gauche" else D
        n = (E - A)[:, :2]
        n /= np.linalg.norm(n, axis=1, keepdims=True)
        return E, n


def oriente(pos, tri, attendu):
    """Retourne les triangles dont la normale s'oppose à la direction attendue."""
    f = np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])
    neg = (f * attendu).sum(1) < 0
    tri[neg] = tri[neg][:, [0, 2, 1]]
    return tri


def fusion(parts, name, mat):
    pos, nrm, uv, idx, k = [], [], [], [], 0
    for p in parts:
        pos.append(p["pos"]); nrm.append(p["nrm"]); uv.append(p["uv"]); idx.append(p["idx"] + k)
        k += len(p["pos"])
    return {"name": name, "pos": np.vstack(pos), "nrm": np.vstack(nrm), "uv": np.vstack(uv),
            "idx": np.vstack(idx).astype(np.uint32), "mat": mat}


def boite(coins, ref, fond=True):
    """Volume balayé : coins = 4 polylignes (N,3) L93 qui font le tour de la section (convexe).
    Chaque face a ses propres sommets (arêtes vives) ; UV métriques (S_PAROI)."""
    C = [m08.to_gltf(c, ref).astype(np.float64) for c in coins]
    cen = sum(C) / 4
    long_ = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(cen, axis=0), axis=1))])
    parts = []
    for k in range(4):
        if not fond and k == 0:
            continue
        P, Q = C[k], C[(k + 1) % 4]
        n = len(P)
        pos = np.vstack([P, Q])
        i = np.arange(n - 1)
        tri = np.concatenate([np.column_stack([i, n + i, n + i + 1]), np.column_stack([i, n + i + 1, i + 1])])
        mid = (P + Q) / 2 - cen
        tri = oriente(pos, tri, mid[tri[:, 0] % n])
        larg = np.linalg.norm(Q - P, axis=1)
        uv = np.column_stack([np.concatenate([long_, long_]), np.concatenate([np.zeros(n), larg])]) / S_PAROI
        parts.append({"pos": pos, "nrm": m08.normales(pos, tri), "uv": uv, "idx": tri})
    t = cen[-1] - cen[0]
    for j, sgn in ((0, -1), (-1, 1)):
        pos = np.array([c[j] for c in C])
        tri = oriente(pos, np.array([[0, 1, 2], [0, 2, 3]]), sgn * t)
        uv = np.column_stack([[0, 1, 1, 0], [0, 0, 1, 1]]) * np.linalg.norm(pos[1] - pos[0]) / S_PAROI
        parts.append({"pos": pos, "nrm": m08.normales(pos, tri), "uv": uv, "idx": tri})
    out = fusion(parts, "", "")
    out["pos"] = out["pos"].astype(np.float32)
    return out


def echant(a, b, pas=1.0):
    s = np.arange(a, b, pas)
    return np.append(s, b) if b - s[-1] > 1e-6 else s


# --- route : enrobé ------------------------------------------------------------------------
def chaussee_texturee(ch, ref, rg):
    r = m08.route(ch, ref)
    _, _, _, hG, hD = rg(ch["pk"])
    u = np.column_stack([-hG, np.zeros_like(hG), hD]).ravel() / S_ENROBE
    r["uv"] = np.column_stack([u, np.repeat(ch["pk"], 3) / S_ENROBE]).astype(np.float32)
    r["mat"] = "enrobe"
    del r["color"]
    return r


# --- marquage ----------------------------------------------------------------------------
def plan_marquage(ch, cfg, decks):
    """Type de ligne tous les 0,25 m pour l'axiale et chaque rive (le dernier tronçon l'emporte)."""
    grille = np.arange(ch["pk"][0], ch["pk"][-1] + 1e-6, 0.25)
    plan = {k: np.full(len(grille), "aucune", dtype=object) for k in ("axiale", "rive_gauche", "rive_droite")}
    for t in cfg["troncons"]:
        cles = ("rive_gauche", "rive_droite") if t["ligne"] == "rives" else (t["ligne"],)
        sel = (grille >= t["pk_debut_m"]) & (grille < t["pk_fin_m"])
        for k in cles:
            plan[k][sel] = t["type"]
    # Dans les virages, l'axiale discontinue est faite de traits rapprochés (T3 : 3 m de trait, 1,33 m d'intervalle), comme
    # sur la route réelle. Relevé du quatrième essai (13/11/2026) : dans les virages, deux ou trois tirets visibles dans le
    # jeu contre huit à dix sur la reconnaissance (PK 3800, 5960, 6240). Virage : rayon de l'axe, lissé sur 20 m, sous
    # RAYON_T3_M ; la zone est étendue de 12 m de part et d'autre.
    A = np.asarray(ch["A"], float)[:, :2]
    cap = np.unwrap(np.arctan2(np.gradient(A[:, 1]), np.gradient(A[:, 0])))
    noyau = np.ones(21) / 21.0
    courbure = np.abs(np.gradient(np.convolve(cap, noyau, mode="same"), ch["pk"]))
    virage = np.convolve((courbure > 1.0 / RAYON_T3_M).astype(float), np.ones(25), mode="same") > 0
    en_virage = np.interp(grille, ch["pk"], virage.astype(float)) > 0.5
    plan["axiale"][en_virage & (plan["axiale"] == "T1")] = "T3"
    reg = cfg["regle_ouvrages"]
    for d in decks:
        sel = (grille >= d["pk"][0] - reg["marge_m"]) & (grille <= d["pk"][1] + reg["marge_m"])
        for k in ("rive_gauche", "rive_droite"):
            plan[k][sel & (plan[k] != "aucune")] = reg["rives"]
    return grille, plan


def marquage(ch, ref, rg, cfg, decks, ruban):
    geo = cfg["geometrie"]
    w, e, dz = geo["largeur_axiale_m"]["valeur"], geo["rive_axe_depuis_bord_m"]["valeur"], geo["hauteur_au_dessus_chaussee_m"]["valeur"]
    wr = geo["largeur_rive_m"]["valeur"]
    mod = cfg["modulations"]
    grille, plan = plan_marquage(ch, cfg, decks)
    parts, stats = [], {}
    for ligne, typ in plan.items():
        chg = np.flatnonzero(typ[1:] != typ[:-1]) + 1
        bornes = np.concatenate([[0], chg, [len(typ)]])
        tirets = []
        for a, b in zip(bornes[:-1], bornes[1:]):
            t = typ[a]
            s0, s1 = grille[a], min(grille[b - 1] + 0.25, ch["pk"][-1])
            if t == "aucune":
                continue
            if t == "continue":
                tirets.append((s0, s1))
            else:
                T, I = mod[t]["trait_m"], mod[t]["intervalle_m"]
                tirets += [(x, min(x + T, s1)) for x in np.arange(s0, s1, T + I) if min(x + T, s1) - x >= 0.5]
        stats[ligne] = {"tirets": len(tirets), "longueur_peinte_m": round(sum(b - a for a, b in tirets))}
        if not tirets:
            continue
        # échantillons calés sur les rangs du ruban (PK entiers) : chaque bande reste dans une maille
        S = [np.unique(np.concatenate([[a], np.arange(np.floor(a) + 1, b), [b]])) for a, b in tirets]
        n = np.array([len(x) for x in S])
        S = np.concatenate(S)
        _, _, _, hG, hD = rg(S)
        larg = w if ligne == "axiale" else wr
        o = np.zeros_like(S) if ligne == "axiale" else (hD - e if ligne == "rive_droite" else -(hG - e))
        P = np.empty((2 * len(S), 3))
        P[0::2] = rg.point(S, o - larg / 2, dz)
        P[1::2] = rg.point(S, o + larg / 2, dz)
        debut = np.concatenate([[0], np.cumsum(n)[:-1]])
        i = np.setdiff1d(np.arange(len(S) - 1), debut[1:] - 1)          # pas de lien entre deux tirets
        tri = np.concatenate([np.column_stack([2 * i, 2 * i + 1, 2 * i + 3]), np.column_stack([2 * i, 2 * i + 3, 2 * i + 2])])
        pos = m08.to_gltf(P, ref).astype(np.float64)
        # recalage exact sur le triangle du ruban sous chaque sommet (bouts de tirets dans une maille vrillée)
        ecart = hauteur_sur_ruban(ruban["pos"].astype(np.float64), ruban["idx"], pos, np.repeat(S, 2), ch["pk"]) - dz
        pos[:, 1] -= np.nan_to_num(ecart)
        pos = pos.astype(np.float32)
        tri = oriente(pos.astype(np.float64), tri, np.array([0.0, 1.0, 0.0]))
        uv = np.column_stack([np.tile([0.0, 1.0], len(S)), np.repeat(S, 2)])
        parts.append({"pos": pos, "nrm": np.tile([0, 1, 0], (len(P), 1)).astype(np.float32), "uv": uv, "idx": tri})

    # zones hachurées (marquage_route.json, zones_hachurees) : un fuseau entre deux voies, contour continu et bandes obliques
    def bande_libre(Sa, Oa, Sb, Ob):
        """Bande entre deux lignes de points (station, décalage) de même longueur, posée sur le ruban."""
        Sa, Oa, Sb, Ob = (np.asarray(x, float) for x in (Sa, Oa, Sb, Ob))
        P = np.empty((2 * len(Sa), 3))
        P[0::2] = rg.point(Sa, Oa, dz)
        P[1::2] = rg.point(Sb, Ob, dz)
        i = np.arange(len(Sa) - 1)
        tri = np.concatenate([np.column_stack([2 * i, 2 * i + 1, 2 * i + 3]), np.column_stack([2 * i, 2 * i + 3, 2 * i + 2])])
        pos = m08.to_gltf(P, ref).astype(np.float64)
        Sv = np.empty(2 * len(Sa))
        Sv[0::2], Sv[1::2] = Sa, Sb
        ecart = hauteur_sur_ruban(ruban["pos"].astype(np.float64), ruban["idx"], pos, Sv, ch["pk"]) - dz
        pos[:, 1] -= np.nan_to_num(ecart)
        tri = oriente(pos, tri, np.array([0.0, 1.0, 0.0]))
        parts.append({"pos": pos.astype(np.float32), "nrm": np.tile([0, 1, 0], (len(P), 1)).astype(np.float32),
                      "uv": np.column_stack([np.tile([0.0, 1.0], len(Sa)), np.repeat(Sa, 2)]), "idx": tri})

    for zh in cfg.get("zones_hachurees", []):
        s0, s1 = float(zh["pk_pointe_m"]), float(zh["pk_bout_m"])

        def centre(s):
            return zh["decalage_pointe_m"] + (zh["decalage_bout_m"] - zh["decalage_pointe_m"]) * (s - s0) / (s1 - s0)

        def demi(s):
            u = np.clip((np.asarray(s, float) - s0) / (s1 - s0), 0.0, 1.0)
            h = zh["largeur_max_m"] / 2 * (0.75 + 0.25 * np.clip(u * (s1 - s0) / zh["pleine_largeur_a_m"], 0.0, 1.0))
            b0, b1 = np.clip(u / 0.1, 0.0, 1.0), np.clip((1.0 - u) / 0.1, 0.0, 1.0)      # deux bouts arrondis
            return h * np.sqrt(b0 * (2.0 - b0)) * np.sqrt(b1 * (2.0 - b1))

        S = np.arange(s0, s1 + 1e-6, 0.5)
        lc = zh["contour_m"]
        for signe in (-1.0, 1.0):                                         # les deux contours
            o = centre(S) + signe * demi(S)
            bande_libre(S, o - lc / 2, S, o + lc / 2)
        n_bandes = 0
        for sk in np.arange(s0 + 1.6, s1 - 0.8, zh["pas_m"]):             # bandes obliques
            Sd = sk + np.linspace(0.0, zh["biais_m"], 6)
            if Sd[-1] > s1 - 0.3 or demi(Sd).min() < 0.25:
                continue
            o = centre(Sd) - demi(Sd) + np.linspace(0.0, 1.0, 6) * 2 * demi(Sd)
            bande_libre(Sd - zh["bande_m"] / 2, o, Sd + zh["bande_m"] / 2, o)
            n_bandes += 1
        stats[f"zone hachurée : {zh['nom']}"] = {"bandes": n_bandes, "longueur_m": round(s1 - s0, 1)}
    return fusion(parts, "marquage", "marquage"), stats


# --- aspect de la chaussée -----------------------------------------------------------------
def aspect_chaussee(ch, ref, rg, ruban):
    """Pièces d'enrobé plus sombres et fissures pontées (data/reference/aspect_chaussee.json), en bandes minces
    posées sur l'enrobé, sous le marquage. Rend deux maillages (« reprise », « fissure ») et un bilan."""
    f = REF / "aspect_chaussee.json"
    if not f.exists():
        return [], {}
    cfg = json.loads(f.read_text(encoding="utf-8"))
    geo = cfg["geometrie"]
    marge = geo["marge_au_bord_m"]
    parts = {"reprise": [], "fissure": []}

    def bande(S, o, larg, dz, mat):
        _, _, _, hG, hD = rg(S)
        larg = np.minimum(np.broadcast_to(larg, S.shape).astype(float), hG + hD - 2 * marge)
        o = np.clip(o, -(hG - marge) + larg / 2, (hD - marge) - larg / 2)                 # la bande reste sur l'enrobé
        P = np.empty((2 * len(S), 3))
        P[0::2] = rg.point(S, o - larg / 2, dz)
        P[1::2] = rg.point(S, o + larg / 2, dz)
        i = np.arange(len(S) - 1)
        tri = np.concatenate([np.column_stack([2 * i, 2 * i + 1, 2 * i + 3]), np.column_stack([2 * i, 2 * i + 3, 2 * i + 2])])
        pos = m08.to_gltf(P, ref).astype(np.float64)
        ecart = hauteur_sur_ruban(ruban["pos"].astype(np.float64), ruban["idx"], pos, np.repeat(S, 2), ch["pk"]) - dz
        pos[:, 1] -= np.nan_to_num(ecart)
        tri = oriente(pos, tri, np.array([0.0, 1.0, 0.0]))
        parts[mat].append({"pos": pos.astype(np.float32), "nrm": np.tile([0, 1, 0], (len(P), 1)).astype(np.float32),
                           "uv": np.column_stack([np.tile([0.0, 1.0], len(S)), np.repeat(S, 2)]), "idx": tri})

    def centre(S, voie):
        _, _, _, hG, hD = rg(S)
        return {"gauche": -hG / 2, "droite": hD / 2}.get(voie, np.zeros_like(S))

    for k, e in enumerate(cfg["elements"]):
        a, b = max(e["pk"][0], ch["pk"][0] + 1), min(e["pk"][1], ch["pk"][-1] - 1)
        if b - a < 0.05:
            continue
        S = np.unique(np.concatenate([[a], np.arange(np.floor(a) + 1, b), [b]]))
        _, _, _, hG, hD = rg(S)
        if e["genre"] != "piece" and not geo.get("fissures_rendues", True):     # refusées en jeu le 13/11/2026
            continue
        if e["genre"] == "raccord":
            bande(S, (hD - hG) / 2, hG + hD, geo["hauteur_fissure_m"], "fissure")
        elif e["genre"] == "piece":
            if not geo.get("pieces_rendues", True):          # aplats refusés en jeu le 13/11/2026 : voir la note du fichier
                continue
            larg = e.get("largeur_m") or geo["part_de_voie_d_une_piece"] * (hG if e["voie"] == "gauche" else hD)
            bande(S, centre(S, e["voie"]) + e.get("decalage_m", 0.0), larg, geo["hauteur_piece_m"], "reprise")
        else:
            n = int(e.get("nombre", 1))
            amp = e.get("ondulation_m", geo["ondulation_m"])
            for j in range(n):
                g = np.random.default_rng(1000 * k + j)
                if "de_a" in e:                                                     # fissure en biais, d'un bord vers l'autre
                    o = np.interp(S, [a, b], e["de_a"])
                else:
                    o = centre(S, e["voie"]) + e.get("decalage_m", 0.0) + (j - (n - 1) / 2) * 0.55 * (1.0 if e["voie"] != "axe" else 0.4)
                # ondulation lente (deux sinusoïdes de phase tirée au sort) : une fissure ne file jamais droit
                o = o + amp * (np.sin(S / g.uniform(6, 11) + g.uniform(0, 6.3)) + 0.5 * np.sin(S / g.uniform(2.2, 3.5) + g.uniform(0, 6.3)))
                # le faïençage : fissures voisines qui ne commencent ni ne finissent ensemble
                d0, d1 = (g.uniform(0, 0.25) * (b - a), g.uniform(0, 0.25) * (b - a)) if n > 1 else (0.0, 0.0)
                sel = (S >= a + d0) & (S <= b - d1)
                if sel.sum() >= 2:
                    bande(S[sel], o[sel], e.get("largeur_m", geo["largeur_fissure_m"]), geo["hauteur_fissure_m"], "fissure")
    meshes = [fusion(p, nom, nom) for nom, p in parts.items() if p]
    bilan = {nom: {"bandes": len(p), "triangles": int(sum(len(x["idx"]) for x in p))} for nom, p in parts.items()}
    return meshes, {**bilan, "couleurs": {"reprise": geo["couleur_piece_rgb"], "fissure": geo["couleur_fissure_rgb"]}}


# --- ouvrages ------------------------------------------------------------------------------
def config_ouvrages(ch, deck):
    cfg = json.loads((REF / "ouvrages_parapets.json").read_text(encoding="utf-8"))
    dflt = cfg["valeurs_par_defaut"]
    out = []
    for a, b in m08.runs(deck):
        pa, pb = float(ch["pk"][a]), float(ch["pk"][b])
        c = (pa + pb) / 2
        ent = min(cfg["ouvrages"], key=lambda o: abs(o["pk_centre_m"] - c))
        if abs(ent["pk_centre_m"] - c) > 40:
            route = "D3D" if c < dflt["pk_limite_D3D_D1_m"] else "D1"
            ent = {"pk_centre_m": c, "route": route, "gauche": dict(dflt[route]), "droite": dict(dflt[route])}
        out.append({"rangs": (a, b), "pk": (pa, pb), "cfg": ent})
    return out, dflt["prolongement_par_defaut_m"]


def parapet(rg, ref, cote, s0, s1, p, mnt=None):
    """Parapet posé sur le bord de chaussée : (pièces par matériau, boîte de collision).
    Avec mnt (parapet hors tablier), le pied descend jusqu'à 0,3 m sous le terrain extérieur."""
    s = echant(s0, s1)
    E, n = rg.bord(s, cote)
    h, t = p["hauteur_m"], p["epaisseur_m"]
    dec = float(p.get("decalage_m", 0.0))                 # recul par rapport au bord de chaussée (0 : posé sur le bord)
    biseau = float(p.get("biseau_m", BISEAU_M))

    def haut(ss):
        """Hauteur du dessus : extrémités en biseau (vu sur la vidéo du 12/11/2026 : tous les parapets, de pierre
        comme de béton, finissent en sifflet), de BISEAU_BAS x h au bout jusqu'à h sur BISEAU_M."""
        ss = np.asarray(ss, float)
        # "sans_biseau_debut" / "sans_biseau_fin" : le parapet se raccorde à un autre, pas de sifflet de ce côté
        d0 = np.full(len(ss), np.inf) if p.get("sans_biseau_debut") else ss - s0
        d1 = np.full(len(ss), np.inf) if p.get("sans_biseau_fin") else s1 - ss
        return h * np.clip(BISEAU_BAS + (1.0 - BISEAU_BAS) * np.minimum(d0, d1) / biseau, BISEAU_BAS, 1.0)

    def base(ss):
        if mnt is None:
            return np.full(len(ss), -DALLE_RETRAIT - 0.02)
        EE, nn = rg.bord(ss, cote)
        q = EE[:, :2] + nn * (dec + t)
        return np.minimum(mnt.z(q[:, 0], q[:, 1]) - EE[:, 2], 0) - 0.3

    def bloc(ss, o0, o1, z0, z1):
        EE, nn = rg.bord(ss, cote)
        o3 = lambda o: np.column_stack([nn * (o + dec), np.zeros(len(ss))])    # noqa: E731
        zz = lambda v: np.column_stack([np.zeros(len(ss)), np.zeros(len(ss)), np.broadcast_to(v, len(ss))])  # noqa: E731
        z0 = base(ss) if isinstance(z0, str) else z0(ss) if callable(z0) else z0
        z1 = z1(ss) if callable(z1) else z1
        return [EE + o3(o0) + zz(z0), EE + o3(o1) + zz(z0), EE + o3(o1) + zz(z1), EE + o3(o0) + zz(z1)]

    pieces = {}
    base_ = "pied"
    if p["type"] == "beton":
        pieces["beton"] = [boite(bloc(s, 0, t, base_, haut), ref)]
    else:
        sous = lambda q: haut(q) - CHAPERON                                 # noqa: E731
        pieces["pierre"] = [boite(bloc(s, 0, t, base_, sous), ref)]
        blanc = p["type"] == "pierre_des_blancs"
        if blanc:
            pieces["blanc"] = []
        # Couronnement toujours en béton gris. Vu en jeu le 13/11/2026 (quatrième version) : un couronnement blanc faisait
        # des parapets « à lisse et poteaux blanc vif » ; sur la route réelle seuls les dés sont peints en blanc.
        pieces["chaperon"] = [boite(bloc(s, -0.02, t + 0.02, sous, haut), ref)]
        if blanc:
            L = s1 - s0
            for c in s0 + (L - np.floor(L / DES_PAS) * DES_PAS) / 2 + np.arange(np.floor(L / DES_PAS) + 1) * DES_PAS:
                ss = np.array([max(c - DES_LONG / 2, s0), min(c + DES_LONG / 2, s1)])
                if ss[1] - ss[0] > 0.1:
                    pieces["blanc"].append(boite(bloc(ss, -0.015, t + 0.015, base_, sous), ref, fond=False))
    coll = boite(bloc(s, 0, t, base_, h), ref)
    return pieces, coll, E


def glissieres(rg, ref, mnt, ch):
    """Glissières simples (data/reference/glissieres.json) : lisse à deux ondes (deux bandes en
    saillie et un creux), poteaux tous les pas_poteaux_m, posés à decalage_depuis_bord_m du bord.
    Renvoie (pièces de rendu par matériau, boîtes de collision, bilan)."""
    cfg = json.loads((REF / "glissieres.json").read_text(encoding="utf-8"))
    g = {k: v["valeur"] for k, v in cfg["geometrie"].items()}
    H, hl, sa, pas, sp, dec, anc = (g[k] for k in ("hauteur_haut_lisse_m", "hauteur_lisse_m", "saillie_ondes_m", "pas_poteaux_m",
                                                   "section_poteau_m", "decalage_depuis_bord_m", "ancrage_poteaux_m"))
    lisses, poteaux, coll, bilan = [], [], [], []
    for t in cfg["troncons"]:
        s0, s1 = max(t["pk_debut_m"], ch["pk"][0]), min(t["pk_fin_m"], ch["pk"][-1])
        if s1 - s0 < 2:
            continue
        cote = t["cote"]

        def bande(ss, o0, o1, z0, z1):
            EE, nn = rg.bord(ss, cote)
            o3 = lambda o: np.column_stack([nn * o, np.zeros(len(ss))])      # noqa: E731
            zz = lambda v: np.column_stack([np.zeros(len(ss)), np.zeros(len(ss)), np.broadcast_to(v, len(ss))])  # noqa: E731
            return [EE + o3(o0) + zz(z0), EE + o3(o1) + zz(z0), EE + o3(o1) + zz(z1), EE + o3(o0) + zz(z1)]

        s = echant(s0, s1)
        b = H - hl                                                           # bas de la lisse
        lisses += [boite(bande(s, dec, dec + 0.03, b, b + hl * 0.42), ref),     # onde basse (en saillie)
                   boite(bande(s, dec + 0.03, dec + sa, b + hl * 0.35, b + hl * 0.65), ref),  # creux (en retrait)
                   boite(bande(s, dec, dec + 0.03, b + hl * 0.58, H), ref)]     # onde haute
        for c in s0 + (s1 - s0 - np.floor((s1 - s0) / pas) * pas) / 2 + np.arange(np.floor((s1 - s0) / pas) + 1) * pas:
            ss = np.array([c - sp / 2, c + sp / 2])
            EE, nn = rg.bord(ss, cote)
            q = EE[:, :2] + nn * (dec + sa + sp / 2)
            zb = float(min(mnt.z(q[:, 0], q[:, 1]).min() - EE[:, 2].max(), 0)) - anc
            poteaux.append(boite(bande(ss, dec + sa, dec + sa + sp, zb, H - 0.02), ref))
        EE, nn = rg.bord(s, cote)
        q = EE[:, :2] + nn * (dec + 0.1)
        zpied = np.minimum(mnt.z(q[:, 0], q[:, 1]) - EE[:, 2], 0) - 0.2
        coll.append(boite(bande(s, dec, dec + 0.2, zpied, H), ref))
        bilan.append({"pk": [s0, s1], "cote": cote, "longueur_m": round(s1 - s0)})
    return {"glissiere_lisse": lisses, "glissiere_poteau": poteaux}, coll, bilan


def tablier_epais(rg, ref, mnt, d, ep):
    """Dalle fermée du rang a-2 au rang b+2, plus culées (dalle -> sol) sur les deux débords."""
    pa, pb = d["pk"]
    s = echant(pa - DALLE_DEBORD, pb + DALLE_DEBORD)
    EG, nG = rg.bord(s, "gauche")
    ED, nD = rg.bord(s, "droite")
    z0 = np.zeros(len(s))
    eg = np.column_stack([nG * ep["gauche"], z0])
    ed = np.column_stack([nD * ep["droite"], z0])
    hautG, hautD = EG + eg - [0, 0, DALLE_RETRAIT], ED + ed - [0, 0, DALLE_RETRAIT]
    basG, basD = EG + eg - [0, 0, DALLE_EP], ED + ed - [0, 0, DALLE_EP]
    pieces = [boite([basG, basD, hautD, hautG], ref)]
    # culées : sous les débords, de la sous-face de la dalle jusqu'à 0,3 m sous le MNT
    for ss in (echant(pa - DALLE_DEBORD, pa), echant(pb, pb + DALLE_DEBORD)):
        if len(ss) < 2:
            continue
        EG, nG = rg.bord(ss, "gauche")
        ED, nD = rg.bord(ss, "droite")
        z0 = np.zeros(len(ss))
        g = EG + np.column_stack([nG * ep["gauche"], z0])
        dd = ED + np.column_stack([nD * ep["droite"], z0])
        zs = np.minimum(mnt.z(g[:, 0], g[:, 1]), mnt.z(dd[:, 0], dd[:, 1])) - 0.3
        haut_g, haut_d = g - [0, 0, DALLE_EP], dd - [0, 0, DALLE_EP]
        if (zs < haut_g[:, 2]).any() or (zs < haut_d[:, 2]).any():
            bg, bd = haut_g.copy(), haut_d.copy()
            bg[:, 2] = np.minimum(zs, haut_g[:, 2] - 0.05)
            bd[:, 2] = np.minimum(zs, haut_d[:, 2] - 0.05)
            pieces.append(boite([bg, bd, haut_d, haut_g], ref))
    return pieces


def murs(ch, ref, mnt, rg):
    """Murs de soutènement BD TOPO à moins de MUR_DIST_MAX de l'axe : voile de 0,5 m du pied
    (MNT mini sur ±1,5 m, -0,3 m) à la tête (MNT maxi), 1 m de haut au moins."""
    g = json.loads((OUT / "couloir" / "construction_lineaire.geojson").read_text(encoding="utf-8"))
    axe = LineString(ch["A"][:, :2])
    route_poly = shapely.make_valid(Polygon(np.vstack([ch["G"][:, :2], ch["D"][::-1, :2]])))
    out, info = [], []
    for f in g["features"]:
        if f["properties"].get("nature") != "Mur de soutènement" or f["geometry"]["type"] != "LineString":
            continue
        L = LineString([l93(*p[:2]) for p in f["geometry"]["coordinates"]])
        if L.distance(axe) > MUR_DIST_MAX:
            continue
        d = np.arange(0, L.length, 1.0)
        xy = np.array([L.interpolate(x).coords[0] for x in np.append(d, L.length)])
        xy = xy[shapely.distance(route_poly, shapely.points(xy)) > 0.3]       # hors chaussée
        if len(xy) < 2:
            continue
        tg = np.gradient(xy, axis=0)
        n = np.column_stack([-tg[:, 1], tg[:, 0]]) / np.linalg.norm(tg, axis=1, keepdims=True)
        prof = np.stack([mnt.z(xy[:, 0] + k * n[:, 0], xy[:, 1] + k * n[:, 1]) for k in np.linspace(-1.5, 1.5, 7)])
        bas, haut = prof.min(0) - 0.3, prof.max(0)
        haut = np.maximum(haut, bas + 1.3)
        c = [np.column_stack([xy + o * n, z]) for o, z in ((-0.25, bas), (0.25, bas), (0.25, haut), (-0.25, haut))]
        out.append(boite(c, ref))
        info.append({"longueur_m": round(L.length), "distance_axe_m": round(L.distance(axe), 1)})
    return out, info


# --- contrôles -----------------------------------------------------------------------------
def hauteur_sur_ruban(p, t, q, s, pk):
    """Hauteur de chaque point q au-dessus du triangle du ruban qui le contient en plan.
    Le ruban de 08 range ses triangles en 4 blocs de n-1 (un par quart de rang)."""
    n1 = len(pk) - 1
    i0 = np.clip(np.floor(s - pk[0]).astype(int), 0, n1 - 1)
    dy = np.full(len(q), np.nan)
    for di in (0, -1, 1):
        i = np.clip(i0 + di, 0, n1 - 1)
        for blk in range(4):
            tr = t[blk * n1 + i]
            a, b, c = p[tr[:, 0]], p[tr[:, 1]], p[tr[:, 2]]
            v0, v1, v2 = (b - a)[:, [0, 2]], (c - a)[:, [0, 2]], (q - a)[:, [0, 2]]
            den = v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]
            l1 = (v2[:, 0] * v1[:, 1] - v2[:, 1] * v1[:, 0]) / den
            l2 = (v0[:, 0] * v2[:, 1] - v0[:, 1] * v2[:, 0]) / den
            ok = np.isnan(dy) & (l1 >= -1e-5) & (l2 >= -1e-5) & (l1 + l2 <= 1 + 1e-5)
            y = a[:, 1] + l1 * (b - a)[:, 1] + l2 * (c - a)[:, 1]
            dy[ok] = q[ok, 1] - y[ok]
    return dy


def obstacles_sur_chaussee(XY, ch, seuil=0.02):
    """Points (L93) à l'intérieur de la chaussée de la spéciale de plus de seuil m : liste (PK, profondeur)."""
    tree = cKDTree(ch["A"][:, :2])
    _, i = tree.query(XY, k=3)
    out = []
    for k in range(XY.shape[0]):
        for j in i[k]:
            A, G, D = ch["A"][j, :2], ch["G"][j, :2], ch["D"][j, :2]
            for E in (G, D):
                u = E - A
                h = np.linalg.norm(u)
                o = (XY[k] - A) @ (u / h)
                t = abs((XY[k] - A) @ np.array([-u[1], u[0]]) / h)
                if 0 <= o < h - seuil and t < 0.75:
                    out.append((float(ch["pk"][j]), round(float(h - o), 3)))
                    break
            else:
                continue
            break
    return out


def controle(dossier, ch, ref):
    r = {}
    for f in ("route_habillee.glb", "ouvrages.glb", "ouvrages_collision.glb"):
        if not (dossier / f).exists():
            continue
        ms = lire_glb(dossier / f)
        pos = np.vstack([m[1] for m in ms])
        nrm = np.vstack([m[2] for m in ms])
        ln = np.linalg.norm(nrm, axis=1)
        r[f] = {"taille_mo": round((dossier / f).stat().st_size / 1e6, 2), "maillages": len(ms),
                "sommets": int(len(pos)), "triangles": int(sum(len(m[4]) for m in ms)),
                "nan": bool(np.isnan(pos).any() or np.isnan(nrm).any() or any(np.isnan(m[3]).any() for m in ms)),
                "normales_unitaires_pct": round(float((np.abs(ln - 1) < 1e-3).mean() * 100), 3),
                "bornes_min": np.round(pos.min(0), 1).tolist(), "bornes_max": np.round(pos.max(0), 1).tolist()}
        # cohérence normales de sommet / normales de face (orientation)
        acc = []
        for _, p, nn, _, t in ms:
            fn = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])
            acc.append((fn * nn[t].sum(1)).sum(1) > 0)
        r[f]["faces_dans_le_sens_des_normales_pct"] = round(float(np.concatenate(acc).mean() * 100), 3)
        if f == "route_habillee.glb":
            ch_m = {m[0]: m for m in ms}
            _, p, _, _, t = ch_m["chaussee"]
            fn = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])
            r[f]["chaussee_normales_vers_le_haut_pct"] = round(float((fn[:, 1] > 0).mean() * 100), 2)
            # marquage : à l'intérieur de la chaussée, distance au bord, hauteur au-dessus
            mp = ch_m["marquage"][1].astype(np.float64)
            xy = np.column_stack([mp[:, 0] + ref["x0"], ref["y0"] - mp[:, 2]])
            pts = shapely.points(xy)
            poly = shapely.make_valid(Polygon(np.vstack([ch["G"][:, :2], ch["D"][::-1, :2]])))
            dist = np.minimum(shapely.distance(LineString(ch["G"][:, :2]), pts), shapely.distance(LineString(ch["D"][:, :2]), pts))
            dedans = shapely.contains_xy(poly, xy[:, 0], xy[:, 1])
            dy = hauteur_sur_ruban(p.astype(np.float64), t, mp, ch_m["marquage"][3][:, 1].astype(np.float64), ch["pk"])
            r[f]["marquage"] = {"sommets": int(len(mp)), "hors_chaussee": int((~dedans).sum()),
                                "distance_min_au_bord_m": round(float(dist[dedans].min()), 3),
                                "distance_au_bord_p1_m": round(float(np.percentile(dist, 1)), 3),
                                "sans_triangle_trouve": int(np.isnan(dy).sum()),
                                "hauteur_sur_chaussee_m": {"min": round(float(np.nanmin(dy)), 4),
                                                           "p0_1": round(float(np.nanpercentile(dy, 0.1)), 4),
                                                           "mediane": round(float(np.nanmedian(dy)), 4),
                                                           "p99_9": round(float(np.nanpercentile(dy, 99.9)), 4),
                                                           "max": round(float(np.nanmax(dy)), 4)}}
        if f == "ouvrages.glb":
            # parapets : pied intérieur (sommets les plus proches de la chaussée) contre le bord
            ecarts = []
            for nom, p, _, _, _ in ms:
                if not nom.startswith("parapet_") or nom.endswith(("_chaperon", "_des")):
                    continue
                cote = "gauche" if "_gauche" in nom else "droite"
                E = m08.to_gltf(ch["G"] if cote == "gauche" else ch["D"], ref).astype(np.float64)
                tree = cKDTree(E[:, [0, 2]])
                dd, k = tree.query(p[:, [0, 2]].astype(np.float64))
                pied = dd < np.percentile(dd, 25) + 0.02           # face intérieure
                seg = LineString(E[:, [0, 2]])
                q = shapely.points(p[pied][:, [0, 2]].astype(np.float64))
                dh = shapely.distance(seg, q)
                cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(E[:, [0, 2]], axis=0), axis=1))])
                dv = p[pied][:, 1] - np.interp(shapely.line_locate_point(seg, q), cum, E[:, 1])
                ecarts.append({"maillage": nom, "ecart_horizontal_max_m": round(float(dh.max()), 3),
                               "pied_sous_bord_m": round(float(-dv.min()), 3),
                               "tete_au_dessus_du_bord_m": round(float(dv.max()), 2)})
            r[f]["parapets"] = ecarts
        if f == "ouvrages_collision.glb" or (f == "ouvrages.glb" and not (dossier / "ouvrages_collision.glb").exists()):
            pp = np.vstack([m[1] for m in ms]).astype(np.float64)
            XY = np.column_stack([pp[:, 0] + ref["x0"], ref["y0"] - pp[:, 2]])
            sur = obstacles_sur_chaussee(XY, ch)
            r[f]["sommets_sur_la_chaussee"] = {"nombre": len(sur), "profondeur_max_m": max([d for _, d in sur], default=0.0),
                                               "pk": sorted({p for p, _ in sur})[:20]}
    return r


# --- rendus ----------------------------------------------------------------------------------
RENDER_HTML = m08.RENDER_HTML.replace("W / H, 1, 20000", "W / H, 0.2, 20000").replace(
    "scene.add(g.scene);",
    "g.scene.traverse(o => { if (o.material && o.material.map) o.material.map.anisotropy = r.capabilities.getMaxAnisotropy(); }); scene.add(g.scene);")


def rendus(vues, fichiers):
    tmp = Path(tempfile.mkdtemp())
    try:
        (tmp / "rendu.html").write_text(RENDER_HTML, encoding="utf-8")
        (tmp / "rendu.js").write_text(m08.RENDER_JS, encoding="utf-8")
        for f in fichiers:
            shutil.copy(f, tmp / f.name)
        srv = subprocess.Popen([sys.executable, "-m", "http.server", "8766", "--bind", "127.0.0.1"], cwd=tmp,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(0.5)
            views, outs = [], []
            for name, eye, at, fov in vues:
                q = (f"w=1400&h=800&fov={fov}&files={','.join(f.name for f in fichiers)}"
                     f"&eye={','.join(f'{v:.2f}' for v in eye)}&at={','.join(f'{v:.2f}' for v in at)}")
                outs.append((tmp / f"{name}.png", FIG4 / f"route_{name}.png"))
                views.append({"url": f"http://127.0.0.1:8766/rendu.html?{q}", "out": str(outs[-1][0])})
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
            if dst.stat().st_size > 1.4e6:                      # plafond 1,5 Mo : palette 256 couleurs
                im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(dst, optimize=True)
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def vue_pont(ch, ref, mnt, rg, d, recul=14.0, lat=22.0, haut=2.5):
    """Œil de côté et un peu en avant du pont, du côté où le terrain est le plus bas."""
    pa, pb = d["pk"]
    c = (pa + pb) / 2
    A, _, _, _, _ = rg(np.array([c - 20, c, c + 20]))
    t = (A[2] - A[0])[:2]
    t /= np.linalg.norm(t)
    n = np.array([t[1], -t[0]])                                 # droite
    best = None
    for sgn in (1, -1):
        q = A[1, :2] + sgn * lat * n - recul * t
        zt = float(mnt.z(q[:1], q[1:])[0])
        if best is None or zt < best[1]:
            best = (q, zt)
    q, zt = best
    eye = np.array([[q[0], q[1], max(zt + 2.0, A[1, 2] + haut)]])
    at = A[1:2] - [0, 0, 1.2]
    return m08.to_gltf(eye, ref)[0], m08.to_gltf(at, ref)[0]


def main():
    t0 = time.time()
    ch = m08.chaussee()
    mnt = m08.MNT()
    deck = m08.tablier(ch, mnt)
    ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    calc = m08.repere(ch)
    if abs(calc["x0"] - ref["x0"]) + abs(calc["y0"] - ref["y0"]) + abs(calc["z0"] - ref["z0"]) > 0.01:
        print(f"attention : le PK 0 du CSV ({calc['x0']}, {calc['y0']}, {calc['z0']}) diffère de modele/repere.json ; "
              "on garde repere.json (celui du terrain)")
    rg = Rangs(ch)
    decks, prol = config_ouvrages(ch, deck)
    cfg_m = json.loads((REF / "marquage_route.json").read_text(encoding="utf-8"))
    print(f"chaussée : {len(ch['pk'])} rangs, PK {ch['pk'][0]:.0f} à {ch['pk'][-1]:.0f} ; {len(decks)} tabliers")

    # --- route habillée
    route = chaussee_texturee(ch, ref, rg)
    marq, stats_m = marquage(ch, ref, rg, cfg_m, decks, route)
    aspect, stats_a = aspect_chaussee(ch, ref, rg, route)
    blanc = cfg_m["geometrie"]["couleur_rgb"]["valeur"]

    # --- ouvrages
    meshes_ouv, coll = [], {"pierre": [], "beton": []}
    tableau = []
    for d in decks:
        pa, pb = d["pk"]
        cfg = d["cfg"]
        ep = {c: (cfg[c]["epaisseur_m"] if cfg[c]["type"] != "aucun" else CORNICHE) for c in ("gauche", "droite")}
        nom = f"PK{pa:.0f}"
        meshes_ouv.append(fusion(tablier_epais(rg, ref, mnt, d, ep), f"tablier_{nom}", "dalle"))
        ligne = {"pk": f"{pa:.0f}-{pb:.0f}", "longueur_m": round(pb - pa + 1), "route": cfg["route"]}
        for cote in ("gauche", "droite"):
            p = cfg[cote]
            ligne[cote] = f"{p['type']} {p.get('hauteur_m', '')} ({p['statut']})"
            if p["type"] == "aucun":
                continue
            # "pk_debut_m" / "pk_fin_m" : bornes du parapet relevées sur la vidéo de reconnaissances ; à défaut, le
            # tablier détecté et son prolongement
            s0 = float(p.get("pk_debut_m", pa - p.get("prolongement_avant_m", prol)))
            s1 = float(p.get("pk_fin_m", pb + p.get("prolongement_apres_m", prol)))
            # hors du tablier (prolongement de plus de 3 m, ou recul), le pied descend jusqu'au terrain
            hors = s0 < pa - 3 or s1 > pb + 3 or p.get("decalage_m")
            pcs, cb, _ = parapet(rg, ref, cote, s0, s1, p, mnt=mnt if hors else None)
            coll["beton" if p["type"] == "beton" else "pierre"].append(cb)
            corps = "beton" if p["type"] == "beton" else "pierre"
            # "peint_en_blanc" : béton peint (bloc du Lion d'Or, blanc sur la reconnaissance, gris sombre en jeu le 13/11/2026)
            meshes_ouv.append(fusion(pcs[corps], f"parapet_{nom}_{cote}", "blanc" if p.get("peint_en_blanc") else corps))
            if "blanc" in pcs:
                meshes_ouv.append(fusion(pcs["blanc"], f"parapet_{nom}_{cote}_des", "blanc"))
            if "chaperon" in pcs:
                meshes_ouv.append(fusion(pcs["chaperon"], f"parapet_{nom}_{cote}_chaperon", "chaperon"))
        tableau.append(ligne)
    # parapets hors tablier (relevé vidéo) : pied descendu jusqu'au terrain
    cfg_par = json.loads((REF / "ouvrages_parapets.json").read_text(encoding="utf-8"))
    hors = []
    for e in cfg_par.get("parapets_hors_tablier", []):
        for cote in ("gauche", "droite"):
            p = e[cote]
            if p.get("type", "aucun") == "aucun":
                continue
            s0, s1 = float(e["pk_debut_m"]), float(e["pk_fin_m"])
            pcs, cb, _ = parapet(rg, ref, cote, s0, s1, p, mnt=mnt)
            corps = "beton" if p["type"] == "beton" else "pierre"
            coll[corps].append(cb)
            if p.get("rendu") == "roche":            # paroi rocheuse : la collision reste, la forme vient de 16_paquet_unreal.py
                hors.append(f"{s0:.0f}-{s1:.0f} {cote} paroi rocheuse (collision seule)")
                continue
            nom = f"PK{s0:.0f}"
            meshes_ouv.append(fusion(pcs[corps], f"parapet_hors_tablier_{nom}_{cote}", "blanc" if p.get("peint_en_blanc") else corps))
            if "blanc" in pcs:
                meshes_ouv.append(fusion(pcs["blanc"], f"parapet_hors_tablier_{nom}_{cote}_des", "blanc"))
            if "chaperon" in pcs:
                meshes_ouv.append(fusion(pcs["chaperon"], f"parapet_hors_tablier_{nom}_{cote}_chaperon", "chaperon"))
            hors.append(f"{s0:.0f}-{s1:.0f} {cote} {p['type']} {p['hauteur_m']} m ({p.get('statut', '')})")
    gl, gl_coll, gl_bilan = glissieres(rg, ref, mnt, ch)
    for k, v in gl.items():
        if v:
            meshes_ouv.append(fusion(v, k, k))
    coll["metal_glissiere"] = gl_coll
    vm, info_murs = murs(ch, ref, mnt, rg)
    if vm:
        meshes_ouv.append(fusion(vm, "murs_soutenement", "pierre"))
        coll["pierre"] += vm
    print(f"murs de soutènement BD TOPO à moins de {MUR_DIST_MAX:.0f} m de l'axe : {len(info_murs)} {info_murs}")

    rapport = {"tabliers": tableau, "parapets_hors_tablier": hors, "glissieres": gl_bilan, "marquage": stats_m,
               "aspect_chaussee": stats_a}
    for version, px in VERSIONS.items():
        dossier = MOD if version == "complet" else MOD / "apercu"
        mats = {"enrobe": {"jpeg": tex_enrobe(px), "rough": 0.92}, "marquage": {"color": blanc, "rough": 0.6},
                "reprise": {"color": stats_a.get("couleurs", {}).get("reprise", [0.2, 0.2, 0.2]), "rough": 0.88},
                "fissure": {"color": stats_a.get("couleurs", {}).get("fissure", [0.06, 0.06, 0.06]), "rough": 0.7},
                "pierre": {"jpeg": tex_pierre(px // 2), "rough": 0.95}, "beton": {"jpeg": tex_beton(px // 2), "rough": 0.9},
                "dalle": {"jpeg": tex_beton(px // 2, seed=3), "rough": 0.9},
                "blanc": {"color": [0.60, 0.585, 0.55], "rough": 0.85}, "chaperon": {"color": [0.62, 0.61, 0.58], "rough": 0.9},
                "glissiere_lisse": {"color": [0.72, 0.74, 0.76], "rough": 0.45}, "glissiere_poteau": {"color": [0.55, 0.56, 0.58], "rough": 0.5}}
        ecrire_glb(dossier / "route_habillee.glb", [route, marq, *aspect], mats)
        ecrire_glb(dossier / "ouvrages.glb", meshes_ouv, mats)
        if version == "complet":
            mc = {"pierre": {"color": [0.6, 0.58, 0.54]}, "beton": {"color": [0.7, 0.7, 0.68]},
                  "metal_glissiere": {"color": [0.72, 0.74, 0.76]}}
            ecrire_glb(dossier / "ouvrages_collision.glb",
                       [fusion(v, f"collision_{k}", k) for k, v in coll.items() if v], mc)
        rapport[version] = controle(dossier, ch, ref)
    print(json.dumps(rapport, ensure_ascii=False, indent=1))

    # --- rendus : virage (marquage), pont de la D3D, plus long ouvrage de la D1, vue conducteur
    A = rg(ch["pk"])[0]
    Ag = m08.to_gltf(A, ref)
    es = np.flatnonzero((ch["zone"] == "es") & ((ch["pk"] < 3550) | (ch["pk"] > 3750)))
    h = np.unwrap(np.arctan2(np.gradient(A[:, 1]), np.gradient(A[:, 0])))
    k = np.abs(np.convolve(np.gradient(h), np.ones(15) / 15, "same"))
    loin = np.ones(len(A), bool)
    for d in decks:
        loin &= np.abs(ch["pk"] - (d["pk"][0] + d["pk"][1]) / 2) > 80
    es = es[loin[es]]
    v = es[np.argmax(k[es])]
    eye = Ag[v - 22] + np.array([0, 3.2, 0])
    vues = [("virage", eye, Ag[v + 6] - np.array([0, 0.5, 0]), 60)]
    d3d = min((d for d in decks if d["cfg"]["route"] == "D3D"), key=lambda d: abs(sum(d["pk"]) / 2 - 1661))
    d1 = max((d for d in decks if d["cfg"]["route"] == "D1"), key=lambda d: d["pk"][1] - d["pk"][0])
    for nom, d, kw in (("pont_d3d", d3d, {}), ("pont_d1", d1, {"recul": 30.0, "lat": 45.0, "haut": 8.0})):
        e_, a_ = vue_pont(ch, ref, mnt, rg, d, **kw)
        vues.append((nom, e_, a_, 55))
    i = int(np.searchsorted(ch["pk"], d3d["pk"][0])) - 30                 # vue conducteur avant le pont
    vues.append(("pont_d3d_conducteur", Ag[i] + m08.to_gltf(rg.point(np.array([ch["pk"][i]]), 1.6, 1.25), ref)[0] - Ag[i],
                 m08.to_gltf(rg.point(np.array([ch["pk"][i] + 35]), 1.0, 0.6), ref)[0], 60))
    fichiers = [MOD / "terrain.glb", MOD / "route_habillee.glb", MOD / "ouvrages.glb"]
    ok = rendus(vues, fichiers)
    print("rendus :", ok, {"virage_pk": round(float(ch["pk"][v])), "pont_d3d_pk": [round(x) for x in d3d["pk"]],
                            "pont_d1_pk": [round(x) for x in d1["pk"]]})
    print(f"durée : {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
