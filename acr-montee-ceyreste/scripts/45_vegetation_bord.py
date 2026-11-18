"""Végétation de bord de route et de jardin relevée sur les photos (sixième passe, 19/11/2026).

Demande de l'utilisateur (transmise par le coordinateur, mots exacts) : « il manque des murets, des éléments devant, des
arbres. Ça manque de végétation, de petits éléments ». Lit data/reference/vegetation_relevee.json (chaque zone cite ses
images Panoramax) et pose :
  - « herbes » : touffes d'herbe sèche (quatre plans croisés, texture ajourée calculée ici) sur l'accotement et au pied
    des murs, densité relevée à l'œil, tirage à graine fixe ; posées sur le MNT LiDAR ;
  - « massifs_mns » : massifs de feuillage (forme de 41_carrefour_depart.massif) là où le MNS - MNT du LiDAR est entre
    h_min et h_max dans la bande de recul relevée : la hauteur et l'emprise viennent du LiDAR, l'espèce de la photo.
Sorties : modele/vegetation_bord.glb (touffes et massifs : aperçu 15, export neutre 33), modele/abords.glb (massifs
et petits éléments : paquet Unreal, famille « abords », acteurs StaticMesh), data/processed/vegetation_bord_bilan.json.
Dans le paquet, l'herbe reste celle du jeu (16, herbes_du_bord) : les touffes de ce script n'y vont pas.
Usage : python scripts/45_vegetation_bord.py
"""
import importlib.util
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from acr_geo import OUT, RAW, REF, ROOT  # noqa: E402

MOD = ROOT / "modele"


def _charger(nom, f):
    s = importlib.util.spec_from_file_location(nom, ICI / f)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


m08 = _charger("m08", "08_modele_3d.py")
m11 = _charger("m11", "11_route_ouvrages.py")
m37 = _charger("m37", "37_clotures.py")
m41 = _charger("m41", "41_carrefour_depart.py")


def tex_herbe(px=256, seed=45):
    """Touffe d'herbe sèche : brins paille et vert gris, du pied (bas) vers le haut ; fond transparent."""
    import cv2
    rng = np.random.default_rng(seed)
    img = np.zeros((px, px, 3), np.uint8); a = np.zeros((px, px), np.uint8)
    for _ in range(110):
        x0 = rng.normal(px / 2, px / 7); h = rng.uniform(0.45, 0.97) * px
        x1 = x0 + rng.normal(0, px / 6) * h / px
        sec = rng.random() < 0.6
        c = np.array([168, 150, 100] if sec else [104, 118, 70]) * rng.uniform(0.75, 1.1)
        n = 6
        pts = np.column_stack([np.linspace(x0, x1, n) + np.linspace(0, 1, n) ** 2 * rng.normal(0, 6, 1),
                               px - 1 - np.linspace(0, h, n)]).astype(np.int32)
        cv2.polylines(img, [pts], False, tuple(int(v) for v in np.clip(c, 0, 255)), 2, cv2.LINE_AA)
        cv2.polylines(a, [pts], False, 255, 2)
    img = np.where(a[..., None] > 0, img, cv2.dilate(img, np.ones((5, 5), np.uint8)))
    b = io.BytesIO(); Image.fromarray(np.dstack([img, a])).save(b, format="PNG", optimize=True)
    return b.getvalue()


def touffe(c, z, h, larg, ang, ref):
    """Quatre plans verticaux croisés, pied 5 cm sous le sol."""
    pos, uv, tri, nrm = [], [], [], []
    for k in range(4):
        t = ang + k * np.pi / 4
        d = np.array([np.cos(t), np.sin(t)]) * larg / 2
        P = np.array([[*(c - d), z - 0.05], [*(c + d), z - 0.05], [*(c + d), z + h], [*(c - d), z + h]])
        o = len(pos) * 4
        pos.append(P); uv.append([[0, 1], [1, 1], [1, 0], [0, 0]])
        tri += [[o, o + 1, o + 2], [o, o + 2, o + 3]]
        n = np.array([-np.sin(t), np.cos(t), 0.0]); nrm.append(np.tile(n, (4, 1)))
    P = np.vstack(pos)
    G = m08.to_gltf(P, ref).astype(np.float32)
    N = np.vstack(nrm); N = np.column_stack([N[:, 0], N[:, 2], -N[:, 1]]).astype(np.float32)
    return {"pos": G, "nrm": N, "uv": np.asarray(uv, np.float32).reshape(-1, 2), "idx": np.asarray(tri, np.uint32)}


def main():
    import rasterio
    R = json.loads((REF / "vegetation_relevee.json").read_text(encoding="utf-8"))
    ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    ch = m08.chaussee()
    rg = m11.Rangs(ch)
    T = m37.Terrain()
    with rasterio.open(RAW / "mns_lidarhd_50cm.tif") as s:
        mns, inv = s.read(1), ~s.transform

    def z_mns(x, y):
        cc, rr = inv * (np.asarray(x, float), np.asarray(y, float))
        return mns[np.clip(np.floor(rr).astype(int), 0, mns.shape[0] - 1), np.clip(np.floor(cc).astype(int), 0, mns.shape[1] - 1)].astype(float)

    # pas de massif sur un toit : emprises BD TOPO (couloir) élargies de 0,8 m
    import shapely
    m31 = _charger("m31", "31_bati.py")
    bati = shapely.union_all([P.buffer(0.8) for _, P in m31.lire(OUT / "couloir" / "batiment.geojson")])
    bilan = {"herbes": [], "massifs": [], "massifs_ecartes_sur_bati": 0}
    touffes, massifs = [], {}
    rng = np.random.default_rng(4501)
    for z in R["herbes"]:
        a, b = z["pk"]
        larg = z["largeur_m"]
        n = int(z["densite_m2"] * (b - a) * larg)
        s = rng.uniform(a, b, n)
        o = rng.uniform(0.15, 0.15 + larg, n)
        _, G, D, hG, hD = rg(s)
        A = rg(s)[0]
        sg = 1.0 if z["cote"] == "droite" else -1.0
        E = D if z["cote"] == "droite" else G
        h_ = hD if z["cote"] == "droite" else hG
        u = (E[:, :2] - A[:, :2]) / np.maximum(h_, 1e-6)[:, None]       # vers l'extérieur
        Q = E[:, :2] + u * o[:, None]
        zz = T.z(Q[:, 0], Q[:, 1])
        k = 0
        for j in range(n):
            if not np.isfinite(zz[j]):
                continue
            h = rng.uniform(*z["hauteur_m"])
            touffes.append(touffe(Q[j], float(zz[j]), h, h * rng.uniform(0.9, 1.4), rng.uniform(0, np.pi), ref)); k += 1
        bilan["herbes"].append({"pk": z["pk"], "cote": z["cote"], "touffes": k})
        del sg
    for z in R["massifs_mns"]:
        a, b = z["pk"]
        k = 0
        for s0 in np.arange(a, b, 2.0):
            s0 = s0 + rng.uniform(-0.4, 0.4)
            A, G, D, hG, hD = rg(np.array([s0]))
            E = D[0] if z["cote"] == "droite" else G[0]
            h_ = (hD if z["cote"] == "droite" else hG)[0]
            u = (E[:2] - A[0, :2]) / max(h_, 1e-6)
            for o in np.arange(z["recul_m"][0], z["recul_m"][1] + 1e-6, 2.0):
                Q = E[:2] + u * (o + rng.uniform(-0.35, 0.35)) + np.array([-u[1], u[0]]) * rng.uniform(-0.4, 0.4)
                if shapely.contains_xy(bati, Q[0], Q[1]):
                    bilan["massifs_ecartes_sur_bati"] += 1
                    continue
                zg = float(T.z(*Q)); h = float(z_mns(*Q)) - zg
                if not (z["h_min"] <= h <= z["h_max"]):
                    continue
                r = rng.uniform(0.75, 1.3) * (1.0 if z["espece"] != "bambou" else 0.8)
                massifs.setdefault(z["espece"], []).extend(
                    m41.massif(Q, zg, r, r * rng.uniform(0.75, 1.1), h * rng.uniform(0.9, 1.0), ref, int(rng.integers(1e6))))
                k += 1
        bilan["massifs"].append({"pk": z["pk"], "cote": z["cote"], "espece": z["espece"], "massifs": k})
    # petits éléments relevés (bacs à déchets) : cuve, couvercle débordant, deux roues
    petits = []
    for e in R.get("petits_elements", []):
        A, G, D, hG, hD = rg(np.array([float(e["pk"])]))
        E = D[0] if e["cote"] == "droite" else G[0]
        h_ = (hD if e["cote"] == "droite" else hG)[0]
        u = (E[:2] - A[0, :2]) / max(h_, 1e-6); t = np.array([u[1], -u[0]])
        c = E[:2] + u * e["recul_m"]; z = float(T.z(*c))
        mat = "bac_{:02x}{:02x}{:02x}".format(*e["couleur"])
        Q = np.array([c - t * 0.29, c + t * 0.29])
        petits.append((m37.ruban(Q, np.tile(u, (2, 1)), -0.36, 0.36, np.full(2, z - 0.02), np.full(2, z + 0.98), ref, 1.0), mat))
        petits.append((m37.ruban(np.array([c - t * 0.31, c + t * 0.31]), np.tile(u, (2, 1)), -0.39, 0.38, np.full(2, z + 0.98), np.full(2, z + 1.05), ref, 1.0), mat))
        for sgn in (-1, 1):
            w = c + t * sgn * 0.25 - u * 0.33
            petits.append((m37.ruban(np.array([w - t * 0.03, w + t * 0.03]), np.tile(u, (2, 1)), -0.1, 0.1, np.full(2, z - 0.02), np.full(2, z + 0.18), ref, 1.0), "roue_noire"))
        bilan.setdefault("petits_elements", []).append({"genre": e["genre"], "pk": e["pk"], "cote": e["cote"]})
    M41 = m41.matieres_depart()
    mats = {"herbe_seche": {"img": tex_herbe(), "mime": "image/png", "alpha": True, "double": True, "rough": 0.95},
            "feuillage_haie": M41["feuillage_haie"],
            "feuillage_bambou": {"img": _jpeg(m41.tex_fleurs((112, 120, 64), (150, 146, 84), 0.05, 23)), "mime": "image/jpeg", "rough": 0.9}}
    meshes_m = [m11.fusion(p, f"jardins_{e}", f"feuillage_{e}") for e, p in massifs.items() if p]
    for k, (pm, mat) in enumerate(petits):
        meshes_m.append(dict(pm, name=f"petit_{k}_{mat}", mat=mat))
        if mat not in mats:
            col = (30, 30, 30) if mat == "roue_noire" else tuple(int(mat[-6:][i:i + 2], 16) for i in (0, 2, 4))
            mats[mat] = {"img": m37._jpeg(m37.tex_unie(col)), "mime": "image/jpeg", "rough": 0.6}
    for me in meshes_m:
        me["idx"] = me["idx"].reshape(-1, 3)
    meshes = list(meshes_m)
    if touffes:
        mt = m11.fusion(touffes, "herbes_bord", "herbe_seche"); mt["idx"] = mt["idx"].reshape(-1, 3)
        meshes.append(mt)
    used = {m["mat"] for m in meshes}
    m37.ecrire_glb(MOD / "vegetation_bord.glb", meshes, {k: v for k, v in mats.items() if k in used})
    m37.ecrire_glb(MOD / "abords.glb", meshes_m, {k: v for k, v in mats.items() if k in {m["mat"] for m in meshes_m}})
    bilan["touffes"] = int(sum(x["touffes"] for x in bilan["herbes"]))
    bilan["massifs_total"] = int(sum(x["massifs"] for x in bilan["massifs"]))
    (OUT / "vegetation_bord_bilan.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(bilan, ensure_ascii=False))


def _jpeg(im):
    b = io.BytesIO(); im.convert("RGB").save(b, "JPEG", quality=88); return b.getvalue()


if __name__ == "__main__":
    main()
