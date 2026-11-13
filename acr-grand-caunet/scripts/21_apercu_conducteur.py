"""Aperçu « vue du conducteur » hors jeu : terrain, chaussée, bande de bord et parois rocheuses, en aplats ombrés.

Ne montre ni les matières du jeu ni la végétation : sert à contrôler les FORMES et leurs raccords (une paroi qui flotte,
une bande qui dépasse, un mur au mauvais endroit) sans attendre un essai en jeu. Petit rendu par tampon de profondeur,
écrit pour ne dépendre que de numpy et de PIL.

Usage : python scripts/21_apercu_conducteur.py <PK> [<PK> ...] [--sortie figures/apercu_conducteur] [--portee 90]
"""
import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
_spec = importlib.util.spec_from_file_location("s16", Path(__file__).with_name("16_paquet_unreal.py"))
s16 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s16)

TEINTES = {"terrain": (128, 122, 96), "chaussee": (92, 92, 96), "bord": (150, 132, 104), "roche": (205, 198, 182), "mur": (170, 160, 148)}


class Recolte:
    """Faux paquet : garde les maillages que lui donnent les fonctions de 16_paquet_unreal.py."""
    vus, echantillon = set(), False

    def __init__(self):
        self.m = []

    def texture(self, nom, *a, **k):
        self.vus.add(nom)

    def materiau(self, *a, **k):
        pass

    def maillage(self, nom, fam, dest, pos, nrm, uv, tri, *a, **k):
        self.m.append((np.asarray(pos, float), np.asarray(tri)))


def scene(ref):
    """[(positions glTF, triangles, teinte)] : terrain, chaussée, ouvrages, bande de bord, parois rocheuses."""
    out = []
    for fichier, teinte in (("terrain_sol.glb", "terrain"), ("route.glb", "chaussee"), ("ouvrages.glb", "mur")):
        for m in s16.lire_glb(s16.MOD / fichier):
            out.append((np.asarray(m["pos"], float), np.asarray(m["idx"]).reshape(-1, 3), teinte))
    with open(s16.OUT / "chaussee_precise.csv", encoding="utf-8") as f:
        r = list(csv.DictReader(f))
    c = lambda *k: np.array([[float(x[a]) for a in k] for x in r])                      # noqa: E731
    ch = {"pk": c("pk_m")[:, 0], "A": c("x_axe", "y_axe", "z_axe"), "G": c("x_gauche", "y_gauche", "z_gauche"),
          "D": c("x_droite", "y_droite", "z_droite")}
    p, _, t = s16.bande_de_bord(ch, ref)
    out.append((np.asarray(p, float), t, "bord"))
    rec = Recolte()
    s16.parois_rocheuses(rec, ref, s16.Sol())
    out += [(p_, t_, "roche") for p_, t_ in rec.m]
    return out, ch


def rendre(sc, oeil, vers, portee, W=1100, H=560, champ_deg=75.0):
    """Image vue de `oeil` (glTF, m) en regardant vers `vers` (vecteur horizontal unitaire)."""
    haut = np.array([0.0, 1.0, 0.0])
    droite = np.cross(vers, haut)
    f = (W / 2) / np.tan(np.radians(champ_deg) / 2)
    img = np.full((H, W, 3), (168, 186, 204), np.float32)
    zb = np.full((H, W), 1e9)
    soleil = np.array([0.45, 0.75, 0.35])
    soleil /= np.linalg.norm(soleil)
    for pos, tri, teinte in sc:
        pres = np.linalg.norm(pos[:, [0, 2]] - oeil[[0, 2]], axis=1) < portee
        tri = tri[pres[tri].any(1)]
        if not len(tri):
            continue
        v = pos - oeil
        cam = np.column_stack([v @ droite, v @ haut, v @ vers])
        coul = np.array(TEINTES[teinte], np.float32)
        for t in tri:
            q = cam[t]
            if (q[:, 2] < 0.4).any():
                continue
            px, py = W / 2 + f * q[:, 0] / q[:, 2], H * 0.42 - f * q[:, 1] / q[:, 2]
            xa, xb = int(max(0, np.floor(px.min()))), int(min(W - 1, np.ceil(px.max())))
            ya, yb = int(max(0, np.floor(py.min()))), int(min(H - 1, np.ceil(py.max())))
            if xa > xb or ya > yb:
                continue
            d = (py[1] - py[2]) * (px[0] - px[2]) + (px[2] - px[1]) * (py[0] - py[2])
            if abs(d) < 1e-9:
                continue
            X, Y = np.meshgrid(np.arange(xa, xb + 1), np.arange(ya, yb + 1))
            a = ((py[1] - py[2]) * (X - px[2]) + (px[2] - px[1]) * (Y - py[2])) / d
            b = ((py[2] - py[0]) * (X - px[2]) + (px[0] - px[2]) * (Y - py[2])) / d
            g = 1 - a - b
            m = (a >= 0) & (b >= 0) & (g >= 0)
            z = 1.0 / (a / q[0, 2] + b / q[1, 2] + g / q[2, 2] + 1e-12)
            m &= z < zb[ya:yb + 1, xa:xb + 1]
            if not m.any():
                continue
            n = np.cross(pos[t[1]] - pos[t[0]], pos[t[2]] - pos[t[0]])
            n /= max(np.linalg.norm(n), 1e-9)
            if n @ (pos[t[0]] - oeil) > 0:
                n = -n
            lum = 0.38 + 0.62 * max(float(n @ soleil), 0.0)
            brume = np.clip(z[m] / (portee * 1.6), 0, 0.5)[:, None]
            img[ya:yb + 1, xa:xb + 1][m] = (1 - brume) * coul * lum + brume * np.array([168, 186, 204])
            zb[ya:yb + 1, xa:xb + 1][m] = z[m]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pk", nargs="+", type=float)
    ap.add_argument("--sortie", default=str(RACINE / "figures" / "apercu_conducteur"))
    ap.add_argument("--portee", type=float, default=90.0)
    a = ap.parse_args()
    ref = json.loads((s16.MOD / "repere.json").read_text(encoding="utf-8"))
    sc, ch = scene(ref)
    sortie = Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    for pk in a.pk:
        i = int(np.argmin(np.abs(ch["pk"] - pk)))
        j = min(i + 6, len(ch["pk"]) - 1)
        A = s16.m08.to_gltf(ch["A"][[i, j]], ref).astype(float)
        vers = (A[1] - A[0]) * np.array([1.0, 0.0, 1.0])
        vers /= max(np.linalg.norm(vers), 1e-9)
        oeil = A[0] + np.array([0.0, 1.15, 0.0]) + np.cross(vers, [0.0, 1.0, 0.0]) * 0.9        # voie de droite, yeux à 1,15 m
        im = rendre(sc, oeil, vers, a.portee)
        ImageDraw.Draw(im).text((8, 6), f"PK {pk:.0f} - aperçu des formes (ni matières ni végétation)", fill=(20, 20, 20))
        im.save(sortie / f"pk_{int(round(pk)):04d}.jpg", quality=88)
        print("écrit :", (sortie / f"pk_{int(round(pk)):04d}.jpg").name)


if __name__ == "__main__":
    main()
