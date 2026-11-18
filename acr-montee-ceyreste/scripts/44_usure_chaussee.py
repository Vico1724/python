"""Usure de la chaussée relevée par tronçon de 50 m (sixième passe, 19/11/2026) : maillages minces posés sur l'enrobé.

Demande de l'utilisateur (transmise par le coordinateur, mots exacts) : « Ça manque […] de marquage au sol, de routes
abîmées ». Lit data/reference/chaussee_releve_50m.json (relevé tronçon par tronçon, 43_chaussee_releve.py ; chaque
élément cite ses images Panoramax) et pose, à son PK et dans sa voie :
  - faïençage (réseau de fissures), fissures longitudinales et transversales, joints pontés au bitume ;
  - pièces d'enrobé plus sombres (« reprise »), raccords d'enrobé ;
  - traces noires de pneus ; terre rouge, gravillons, aiguilles, bord effrité sur les bords.
Chaque famille a une texture calculée ici (RGBA, transparence progressive : glTF « BLEND »), dépliée en mètres le long de la route,
avec un décalage tiré à graine fixe par élément (deux éléments voisins ne montrent pas le même motif). Bandes à 5 à 9 mm
au-dessus du ruban de 11 (le marquage est à 15 mm et passe dessus).

Sorties : modele/usure_chaussee.glb (aperçu de l'étape 15 et export neutre 33), data/processed/usure_bilan.json.
Dans le paquet Unreal, l'usure est faite par des décalques du jeu (16_paquet_unreal.py, details_de_chaussee, 3 ter) : des
aplats de couleur unie posés sur l'enrobé avaient été refusés en jeu au Grand Caunet (aspect_chaussee.json).
Usage : python scripts/44_usure_chaussee.py
"""
import importlib.util
import io
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from acr_geo import OUT, REF, ROOT  # noqa: E402

MOD = ROOT / "modele"


def _charger(nom, f):
    s = importlib.util.spec_from_file_location(nom, ICI / f)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


m08 = _charger("m08", "08_modele_3d.py")
m11 = _charger("m11", "11_route_ouvrages.py")
m37 = _charger("m37", "37_clotures.py")

PX_M = 128          # pixels par mètre des textures
# famille : (largeur de la bande, m, ou None = largeur de la voie ; longueur d'une répétition, m ; hauteur, m)
FAMILLES = {
    "faiencage": (None, 4.0, 0.006), "fissure_longitudinale": (0.7, 6.0, 0.007), "fissure_transversale": (None, 1.0, 0.007),
    "joint_ponte": (0.4, 6.0, 0.008), "reprise": (None, 6.0, 0.005), "raccord": (None, 1.0, 0.007),
    "traces_pneus": (None, 8.0, 0.009), "terre": (1.1, 5.0, 0.008), "gravillons": (0.9, 4.0, 0.008),
    "aiguilles": (1.0, 4.0, 0.008), "bord_effrite": (0.7, 4.0, 0.008),
}


def _bruit(h, w, rng, ech):
    b = rng.random((max(2, h // ech + 2), max(2, w // ech + 2))).astype(np.float32)
    return cv2.resize(b, (w + 2 * ech, h + 2 * ech), interpolation=cv2.INTER_CUBIC)[ech:ech + h, ech:ech + w]


def _png(rgba):
    b = io.BytesIO(); Image.fromarray(rgba).save(b, format="PNG", optimize=True); return b.getvalue()


def _fissure(img, a, rng, x0, y0, x1, y1, ep, couleur, ramifier=2):
    """Trait brisé d'un point à un autre (fissure), avec ramifications."""
    n = max(4, int(np.hypot(x1 - x0, y1 - y0) / 10))
    t = np.linspace(0, 1, n)
    xs = x0 + (x1 - x0) * t + np.cumsum(rng.normal(0, 3.0, n)); ys = y0 + (y1 - y0) * t + np.cumsum(rng.normal(0, 3.0, n))
    pts = np.column_stack([xs, ys]).astype(np.int32)
    cv2.polylines(img, [pts], False, couleur, ep, cv2.LINE_AA)
    cv2.polylines(a, [pts], False, 235, ep + 1, cv2.LINE_AA)
    for _ in range(ramifier):
        k = rng.integers(1, n - 1)
        ang = rng.uniform(0, 2 * np.pi); L = rng.uniform(15, 60)
        _fissure(img, a, rng, xs[k], ys[k], xs[k] + L * np.cos(ang), ys[k] + L * np.sin(ang), max(1, ep - 1), couleur, 0)


def textures():
    """Une image RGBA par famille ; v (vertical de l'image) le long de la route, répétable en v."""
    rng = np.random.default_rng(44)
    T = {}
    noir = (50, 48, 46)
    # faïençage : réseau de mailles de 10 à 30 cm (cellules de Voronoï déformées), plus dense au centre de la bande
    W, H = 256, int(4.0 * PX_M)
    img = np.zeros((H, W, 3), np.uint8); a = np.zeros((H, W), np.uint8)
    sub = cv2.Subdiv2D((0, -H, W, 3 * H))
    graines = np.column_stack([rng.uniform(0, W, 170), rng.uniform(0, H, 170)])
    for g in np.vstack([graines, graines + [0, H], graines - [0, H]]):
        sub.insert((float(g[0]), float(g[1])))
    facettes, _ = sub.getVoronoiFacetList([])
    for f in facettes:
        pts = np.asarray(f, np.float32)
        pts += rng.normal(0, 1.5, pts.shape)
        cv2.polylines(img, [pts.astype(np.int32)], True, noir, 2, cv2.LINE_AA)
        cv2.polylines(a, [pts.astype(np.int32)], True, 200, 2, cv2.LINE_AA)
    garde = _bruit(H, W, rng, 60) > 0.35                    # plaques saines entre les zones faïencées
    a[~garde] = 0
    T["faiencage"] = (img, a)
    # fissure longitudinale : un trait brisé le long, ramifié
    W, H = 96, int(6.0 * PX_M)
    img = np.zeros((H, W, 3), np.uint8); a = np.zeros((H, W), np.uint8)
    _fissure(img, a, rng, W / 2, -10, W / 2, H + 10, 3, noir, 6)
    T["fissure_longitudinale"] = (img, a)
    # joint ponté : bande de bitume noir brillant de 3 à 5 cm, bords flous
    img = np.zeros((H, W, 3), np.uint8) + np.array([18, 18, 19], np.uint8); a = np.zeros((H, W), np.uint8)
    x = W / 2 + np.cumsum(rng.normal(0, 0.8, H)); x -= np.linspace(0, x[-1] - x[0], H)
    for y in range(H):
        e = 2.5 + 1.5 * rng.random()
        a[y, int(x[y] - e):int(x[y] + e)] = 255
    T["joint_ponte"] = (img, a)
    # fissure transversale : trait en travers (u), une répétition = 1 m
    W, H = 512, PX_M
    img = np.zeros((H, W, 3), np.uint8); a = np.zeros((H, W), np.uint8)
    _fissure(img, a, rng, -5, H / 2, W + 5, H / 2, 3, noir, 4)
    T["fissure_transversale"] = (img, a)
    T["raccord"] = T["fissure_transversale"]
    # reprise : enrobé plus sombre à grain, bords irréguliers (en u)
    W, H = 256, int(6.0 * PX_M)
    gr = (_bruit(H, W, rng, 2) * 22 + _bruit(H, W, rng, 24) * 10 + 62).clip(0, 255)
    img = np.stack([gr, gr, gr * 1.03], -1).clip(0, 255).astype(np.uint8)
    u = np.abs(np.linspace(-1, 1, W))[None, :]
    a = ((1 - u) * 1.0 + _bruit(H, W, rng, 18) * 0.25 > 0.14).astype(np.uint8) * 235
    T["reprise"] = (img, a)
    # traces de pneus : deux paires de bandes sombres (voie de 1,5 m, pneus de 20 cm), effacées par endroits
    W, H = 256, int(8.0 * PX_M)
    img = np.zeros((H, W, 3), np.uint8) + np.array([22, 21, 21], np.uint8); a = np.zeros((H, W), np.uint8)
    vv = np.arange(H)
    for c0 in (0.22, 0.72):
        for d in (-0.13, 0.13):
            c = (c0 + d) * W + 5 * np.sin(vv / H * 2 * np.pi + rng.uniform(0, 6))
            for y in range(H):
                a[y, int(c[y] - 0.012 * W):int(c[y] + 0.012 * W) + 1] = 170
    f_ = _bruit(H, W, rng, 90) + 0.15 * _bruit(H, W, rng, 8)
    a = (a * np.clip((f_ - 0.3) * 2.0, 0, 1)).astype(np.uint8)
    T["traces_pneus"] = (img, a)
    # terre rouge : taches qui s'éclaircissent vers la chaussée (u = 0 au bord)
    W, H = 160, int(5.0 * PX_M)
    n = _bruit(H, W, rng, 14) * 0.6 + _bruit(H, W, rng, 3) * 0.4
    fond = np.array([132, 92, 70], np.float32)
    img = (fond[None, None, :] * (0.75 + 0.5 * n[..., None])).clip(0, 255).astype(np.uint8)
    u = np.linspace(0, 1, W)[None, :]
    a = (np.clip((n * 1.1 - u * 1.0 - 0.05) * 2.2, 0, 0.9) * 255).astype(np.uint8)
    T["terre"] = (img, a)
    # gravillons : grains clairs de 5 à 15 mm, plus denses au bord
    img = np.zeros((H, W, 3), np.uint8); a = np.zeros((H, W), np.uint8)
    for _ in range(2600):
        x = int(abs(rng.normal(0, 0.45)) * W); y = int(rng.uniform(0, H))
        if x >= W:
            continue
        r = int(rng.uniform(1, 2.5)); c = int(rng.uniform(150, 215))
        cv2.circle(img, (x, y), r, (c, c - 6, c - 18), -1); cv2.circle(a, (x, y), r, 255, -1)
    T["gravillons"] = (img, a)
    # aiguilles de pin : traits bruns de 6 à 10 cm
    img = np.zeros((H, W, 3), np.uint8); a = np.zeros((H, W), np.uint8)
    for _ in range(1500):
        x = abs(rng.normal(0, 0.5)) * W; y = rng.uniform(0, H)
        if x >= W:
            continue
        ang = rng.uniform(0, np.pi); L = rng.uniform(8, 13)
        c = tuple(int(v) for v in np.array([120, 74, 40]) * rng.uniform(0.75, 1.15))
        p0 = (int(x - L / 2 * np.cos(ang)), int(y - L / 2 * np.sin(ang))); p1 = (int(x + L / 2 * np.cos(ang)), int(y + L / 2 * np.sin(ang)))
        cv2.line(img, p0, p1, c, 1, cv2.LINE_AA); cv2.line(a, p0, p1, 255, 1)
    T["aiguilles"] = (img, a)
    # bord effrité : enrobé arraché (trous clairs de grave) au bord
    W, H = 96, int(4.0 * PX_M)
    n = _bruit(H, W, rng, 10)
    u = np.linspace(0, 1, W)[None, :]
    a = (n - u * 1.1 > 0.0).astype(np.uint8) * 255
    gr = (_bruit(H, W, rng, 2) * 40 + 140)
    img = np.stack([gr, gr * 0.95, gr * 0.86], -1).clip(0, 255).astype(np.uint8)
    T["bord_effrite"] = (img, a)
    out = {}
    for k, (img, a) in T.items():
        # couleur prolongée sous les parties découpées (pas de liseré au filtrage)
        flou = cv2.dilate(img, np.ones((5, 5), np.uint8)) if a.mean() < 128 else img
        img2 = np.where(a[..., None] > 0, img, flou)
        out[k] = np.dstack([img2, a])
    return out


def main():
    R = json.loads((REF / "chaussee_releve_50m.json").read_text(encoding="utf-8"))
    ch = m08.chaussee()
    ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    rg = m11.Rangs(ch)
    ruban = m11.chaussee_texturee(ch, ref, rg)
    T = textures()
    parts = {k: [] for k in FAMILLES}
    rng = np.random.default_rng(4401)
    bilan = {}
    for t in R["troncons"]:
        for e in t["elements"]:
            g, (a, b), voie = e["genre"], e["pk"], e["voie"]
            larg_f, rep, dz = FAMILLES[g]
            a, b = max(a, ch["pk"][0] + 1), min(b, ch["pk"][-1] - 1)
            transv = g in ("fissure_transversale", "raccord") or (g == "joint_ponte" and b - a < 3)
            if transv:
                c = (a + b) / 2; a, b = c - 0.5, c + 0.5
            if b - a < 0.3:
                continue
            S = np.unique(np.concatenate([[a], np.arange(np.floor(a) + 1, b, 0.5), [b]]))
            _, _, _, hG, hD = rg(S)
            m = 0.15
            if voie == "toute" or transv:
                o0, o1 = -(hG - m), hD - m
            elif voie == "droite":
                o0, o1 = (np.full_like(S, 0.1), hD - m) if larg_f is None else (hD / 2 - larg_f / 2, hD / 2 + larg_f / 2)
            elif voie == "gauche":
                o0, o1 = (-(hG - m), np.full_like(S, -0.1)) if larg_f is None else (-hG / 2 - larg_f / 2, -hG / 2 + larg_f / 2)
            elif voie == "axe":
                w = larg_f or 1.8
                o0, o1 = np.full_like(S, -w / 2), np.full_like(S, w / 2)
            elif voie == "bord_droit":            # u = 0 au bord
                w = larg_f or 1.0
                o0, o1 = hD - 0.02, hD - w
            else:
                w = larg_f or 1.0
                o0, o1 = -(hG - 0.02), -(hG - w)
            o0 = np.broadcast_to(o0, S.shape).astype(float); o1 = np.broadcast_to(o1, S.shape).astype(float)
            # serpente un peu (fissures et traces ne filent pas droit)
            if g in ("fissure_longitudinale", "joint_ponte", "traces_pneus") and not transv:
                dec = 0.25 * np.sin(S / rng.uniform(5, 9) + rng.uniform(0, 6.3)); o0 = o0 + dec; o1 = o1 + dec
            P = np.empty((2 * len(S), 3))
            P[0::2] = rg.point(S, o0, dz)
            P[1::2] = rg.point(S, o1, dz)
            i = np.arange(len(S) - 1)
            tri = np.concatenate([np.column_stack([2 * i, 2 * i + 1, 2 * i + 3]), np.column_stack([2 * i, 2 * i + 3, 2 * i + 2])])
            pos = m08.to_gltf(P, ref).astype(np.float64)
            ecart = m11.hauteur_sur_ruban(ruban["pos"].astype(np.float64), ruban["idx"], pos, np.repeat(S, 2), ch["pk"]) - dz
            pos[:, 1] -= np.nan_to_num(ecart)
            tri = m11.oriente(pos, tri, np.array([0.0, 1.0, 0.0]))
            # dépliage : u en travers (0 -> 1), v le long en répétitions de « rep » m, décalé et parfois retourné
            if transv:
                uu = np.column_stack([np.zeros(len(S)), np.ones(len(S))]).ravel()
                vv = np.repeat((S - a) / (b - a), 2) * 0.98 + 0.01
                uv = np.column_stack([vv, uu])                   # texture couchée : le trait suit la largeur
            else:
                sens = 1.0 if rng.random() < 0.5 else -1.0
                vv = np.repeat(sens * (S - a) / rep + rng.uniform(0, 1), 2)
                uu = np.tile([0.0, 1.0], len(S))
                if g == "faiencage":                      # en mètres dans les deux sens (texture de 2 m de large), sans étirer
                    uu = np.column_stack([np.zeros(len(S)), np.abs(o1 - o0) / 2.0]).ravel() + rng.uniform(0, 1)
                elif rng.random() < 0.5 and voie not in ("bord_droit", "bord_gauche"):
                    uu = 1.0 - uu
                uv = np.column_stack([uu, vv])
            parts[g].append({"pos": pos.astype(np.float32), "nrm": np.tile([0, 1, 0], (len(P), 1)).astype(np.float32),
                             "uv": uv.astype(np.float32), "idx": tri.astype(np.uint32)})
            bilan.setdefault(g, {"elements": 0, "longueur_m": 0.0})
            bilan[g]["elements"] += 1; bilan[g]["longueur_m"] += round(float(b - a), 1)
    # enrobé récent sombre entre les deux raccords relevés (PK 1855 -> 2700) : nappe pleine largeur à 3 mm, texture
    # d'enrobé plus sombre et plus fine (aperçu et export neutre ; dans le paquet, l'enrobé reste celui du jeu)
    rac = sorted(e["pk"] for t in R["troncons"] for e in t["elements"] if e["genre"] == "raccord")
    if len(rac) >= 2:
        a, b = (rac[0][0] + rac[0][1]) / 2, (rac[1][0] + rac[1][1]) / 2
        S = np.unique(np.concatenate([[a], np.arange(np.floor(a) + 1, b), [b]]))
        _, _, _, hG, hD = rg(S)
        P = np.empty((2 * len(S), 3)); P[0::2] = rg.point(S, -hG, 0.003); P[1::2] = rg.point(S, hD, 0.003)
        i = np.arange(len(S) - 1)
        tri = np.concatenate([np.column_stack([2 * i, 2 * i + 1, 2 * i + 3]), np.column_stack([2 * i, 2 * i + 3, 2 * i + 2])])
        pos = m08.to_gltf(P, ref).astype(np.float64)
        ecart = m11.hauteur_sur_ruban(ruban["pos"].astype(np.float64), ruban["idx"], pos, np.repeat(S, 2), ch["pk"]) - 0.003
        pos[:, 1] -= np.nan_to_num(ecart)
        tri = m11.oriente(pos, tri, np.array([0.0, 1.0, 0.0]))
        uv = np.column_stack([np.column_stack([-hG, hD]).ravel() / m11.S_ENROBE, np.repeat(S, 2) / m11.S_ENROBE])
        parts["enrobe_recent"] = [{"pos": pos.astype(np.float32), "nrm": np.tile([0, 1, 0], (len(P), 1)).astype(np.float32),
                                   "uv": uv.astype(np.float32), "idx": tri.astype(np.uint32)}]
        bilan["enrobe_recent"] = {"elements": 1, "longueur_m": round(float(b - a), 1)}
    meshes, mats = [], {}
    for g, p in parts.items():
        if g == "enrobe_recent":
            meshes.append(m11.fusion(p, "enrobe_recent", "enrobe_recent"))
            ima = np.asarray(Image.open(io.BytesIO(m11.tex_enrobe(512))).convert("RGB")).astype(np.float32)
            ima = (ima * 0.62).clip(0, 255).astype(np.uint8)             # récent : sombre (photos du PK 1855-2700)
            b_ = io.BytesIO(); Image.fromarray(ima).save(b_, format="JPEG", quality=85)
            mats["enrobe_recent"] = {"img": b_.getvalue(), "mime": "image/jpeg", "rough": 0.9}
            continue
        if not p:
            continue
        meshes.append(m11.fusion(p, f"usure_{g}", f"usure_{g}"))
        mats[f"usure_{g}"] = {"img": _png(T[g]), "mime": "image/png", "alpha": "BLEND",
                              "rough": 0.45 if g == "joint_ponte" else 0.92}
    for me in meshes:
        me["idx"] = me["idx"].reshape(-1, 3)
    m37.ecrire_glb(MOD / "usure_chaussee.glb", meshes, mats)
    bilan = {"note": "Usure de la chaussée posée par 44_usure_chaussee.py d'après data/reference/chaussee_releve_50m.json",
             "par_famille": bilan, "elements": sum(v["elements"] for v in bilan.values()),
             "fichier": "modele/usure_chaussee.glb", "taille_ko": round((MOD / "usure_chaussee.glb").stat().st_size / 1024)}
    (OUT / "usure_bilan.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(bilan, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
