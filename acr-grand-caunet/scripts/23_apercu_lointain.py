"""Aperçu hors jeu du PAYSAGE vu de la route : relief lointain avec ses images, terrain proche, arbres en silhouettes.

Complète scripts/21_apercu_conducteur.py (formes proches, en aplats). Ici le but est de juger, sans le jeu, ce que le
conducteur voit au loin : netteté et teinte des images du relief lointain, raccords entre dalles, crêtes, part du
relief que les arbres laissent voir. Ce n'est pas le rendu du jeu : pas de matières du jeu, pas d'ombres portées, des
arbres réduits à des houppiers en nuages de points ; l'éclairage est un soleil simple.

Rendu par nuage de points : chaque triangle est échantillonné en proportion de sa surface à l'écran, puis trié par
profondeur. Ne dépend que de numpy et de PIL.

Usage : python scripts/23_apercu_lointain.py <PK> [<PK> ...] [--paquet paquet_unreal] [--sans-arbres] [--champ 62]
"""
import argparse
import csv
import importlib.util
import io
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

CIEL = np.array([176, 196, 216], np.float32)
SOLEIL = np.array([0.74, 0.42, 0.52])            # vers le soleil, repère glTF du projet (X est, Y haut, Z sud) : matin, sud-est
SOLEIL = SOLEIL / np.linalg.norm(SOLEIL)
TEINTES = {"terrain": (112, 104, 78), "chaussee": (118, 116, 114), "mur": (176, 168, 152)}
HOUPPIERS = {"pin": ((62, 88, 50), 0.30, 0.20, 0.78), "feuillu": ((84, 98, 52), 0.26, 0.30, 0.62), "arbuste": ((92, 100, 60), 0.45, 0.42, 0.5)}


class Ecran:
    def __init__(self, oeil, vers, W, H, champ_deg):
        self.oeil, self.W, self.H = oeil, W, H
        haut = np.array([0.0, 1.0, 0.0])
        self.base = np.stack([np.cross(vers, haut), haut, vers])          # droite, haut, avant
        self.f = (W / 2) / np.tan(np.radians(champ_deg) / 2)
        self.z = np.full(W * H, np.inf, np.float32)
        self.im = np.tile(CIEL, (W * H, 1))

    def camera(self, p):
        return (p - self.oeil) @ self.base.T

    def pose(self, c, rvb):
        """Points en repère caméra (n, 3) et leurs couleurs : dépose ceux qui sont devant ce qui est déjà là."""
        ok = c[:, 2] > 0.6
        c, rvb = c[ok], rvb[ok]
        px = (self.W / 2 + self.f * c[:, 0] / c[:, 2]).astype(np.int64)
        py = (self.H * 0.47 - self.f * c[:, 1] / c[:, 2]).astype(np.int64)
        ok = (px >= 0) & (px < self.W) & (py >= 0) & (py < self.H)
        pix, z, rvb = py[ok] * self.W + px[ok], c[ok, 2].astype(np.float32), rvb[ok]
        np.minimum.at(self.z, pix, z)
        g = z <= self.z[pix]
        d = np.linalg.norm(c[ok][g], axis=1)[:, None]
        brume = 1.0 - np.exp(-d / 14000.0)                                 # voile atmosphérique
        self.im[pix[g]] = rvb[g] * (1 - brume) + CIEL * brume

    def triangles(self, pos, tri, couleur, uv=None, image=None, lumiere=None, portee=None):
        """Échantillonne chaque triangle selon sa surface à l'écran. couleur : (3,) ou par triangle (n, 3)."""
        c = self.camera(pos)
        t = c[tri]                                                         # (n, 3, 3)
        devant = (t[:, :, 2] > 0.6).all(1)
        if portee is not None:
            devant &= t[:, :, 2].min(1) < portee
        if not devant.any():
            return
        tri, t = tri[devant], t[devant]
        coul = np.broadcast_to(np.asarray(couleur, np.float32), (len(devant), 3))[devant] if np.ndim(couleur) == 2 else None
        px = self.W / 2 + self.f * t[:, :, 0] / t[:, :, 2]
        py = self.H * 0.47 - self.f * t[:, :, 1] / t[:, :, 2]
        vu = (px.max(1) >= 0) & (px.min(1) < self.W) & (py.max(1) >= 0) & (py.min(1) < self.H)
        aire = 0.5 * np.abs((px[:, 1] - px[:, 0]) * (py[:, 2] - py[:, 0]) - (px[:, 2] - px[:, 0]) * (py[:, 1] - py[:, 0]))
        vu &= aire > 0.02
        if not vu.any():
            return
        n = np.clip(np.ceil(aire * 1.6) + 1, 1, 60000)
        n = (2 ** np.ceil(np.log2(n))).astype(int)
        nrm = np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
        nrm[nrm[:, 1] < 0] *= -1.0
        lum = (0.50 + 0.62 * np.clip(nrm @ SOLEIL, 0.0, 1.0)) if lumiere is None else lumiere
        rng = np.random.default_rng(7)
        for k in np.unique(n[vu]):
            s = np.flatnonzero(vu & (n == k))
            for a0 in range(0, len(s), max(1, 3_000_000 // int(k))):
                ss = s[a0:a0 + max(1, 3_000_000 // int(k))]
                a, b = rng.random((len(ss), int(k))), rng.random((len(ss), int(k)))
                pli = a + b > 1
                a, b = np.where(pli, 1 - a, a), np.where(pli, 1 - b, b)
                w = np.stack([1 - a - b, a, b], 2)                         # (m, k, 3)
                p = np.einsum("mkv,mvc->mkc", w, t[ss]).reshape(-1, 3)
                if image is not None:
                    q = np.einsum("mkv,mvc->mkc", w, uv[tri[ss]]).reshape(-1, 2)
                    ih, iw = image.shape[:2]
                    rvb = image[np.clip((q[:, 1] * ih).astype(int), 0, ih - 1), np.clip((q[:, 0] * iw).astype(int), 0, iw - 1)].astype(np.float32)
                elif coul is not None:
                    rvb = np.repeat(coul[ss], int(k), axis=0)
                else:
                    rvb = np.tile(np.asarray(couleur, np.float32), (len(p), 1))
                l = lum if np.ndim(lum) == 0 else np.repeat(lum[ss], int(k))[:, None]
                self.pose(p, rvb * l)

    def houppiers(self, base, hauteur, genre, portee):
        """Arbres en nuages de points : un ellipsoïde par houppier, un trait pour le tronc."""
        teinte, r_h, r_v, h_c = HOUPPIERS[genre]
        c0 = self.camera(base + np.array([0.0, 1.0, 0.0]) * (hauteur * h_c)[:, None])
        ok = (c0[:, 2] > 2.0) & (c0[:, 2] < portee) & (np.abs(c0[:, 0]) < c0[:, 2] * self.W / self.f * 0.6)
        base, hauteur, c0 = base[ok], hauteur[ok], c0[ok]
        if not len(base):
            return
        rayon_px = self.f * hauteur * r_h / c0[:, 2]
        n = np.clip(np.ceil(4.5 * rayon_px ** 2 * (r_v / r_h)) + 2, 2, 20000)
        n = (2 ** np.ceil(np.log2(n))).astype(int)
        rng = np.random.default_rng(11)
        ton = 0.82 + 0.36 * rng.random(len(base))
        for k in np.unique(n):
            s = np.flatnonzero(n == k)
            for a0 in range(0, len(s), max(1, 2_000_000 // int(k))):
                ss = s[a0:a0 + max(1, 2_000_000 // int(k))]
                d = rng.normal(size=(len(ss), int(k), 3))
                d /= np.linalg.norm(d, axis=2, keepdims=True)
                d *= rng.random((len(ss), int(k), 1)) ** 0.33              # dans le volume, plus dense vers la surface
                h = hauteur[ss][:, None, None]
                centre = base[ss][:, None, :] + np.array([0.0, 1.0, 0.0]) * h * h_c
                p = centre + d * np.array([r_h, r_v, r_h]) * h
                lum = 0.42 + 0.34 * np.clip(d @ SOLEIL, -0.2, 1.0) + 0.24 * np.clip(d[:, :, 1] + 0.3, 0.0, 1.0)
                rvb = np.asarray(teinte, np.float32) * (lum * ton[ss][:, None])[:, :, None]
                self.pose(self.camera(p.reshape(-1, 3)), rvb.reshape(-1, 3))
                if genre != "arbuste":                                      # tronc, pour les arbres proches
                    pres = c0[ss][:, 2] < 90.0
                    if pres.any():
                        u = rng.random((int(pres.sum()), 160, 1))
                        tp = base[ss][pres][:, None, :] + np.array([0.0, 1.0, 0.0]) * u * (hauteur[ss][pres][:, None, None] * h_c)
                        tp = tp + rng.normal(scale=0.07, size=tp.shape) * np.array([1.0, 0.0, 1.0])
                        self.pose(self.camera(tp.reshape(-1, 3)), np.tile(np.array([98, 86, 72], np.float32), (tp.shape[0] * 160, 1)))

    def image(self):
        z = self.z.reshape(self.H, self.W)
        im = self.im.reshape(self.H, self.W, 3).copy()
        for _ in range(3):                                                 # bouche les trous d'échantillonnage (pas le ciel)
            vide = ~np.isfinite(z)
            zp = np.pad(z, 1, constant_values=np.inf)
            ip = np.pad(im, ((1, 1), (1, 1), (0, 0)), mode="edge")
            vois_z = np.stack([zp[1 + dy:1 + dy + self.H, 1 + dx:1 + dx + self.W] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)])
            vois_i = np.stack([ip[1 + dy:1 + dy + self.H, 1 + dx:1 + dx + self.W] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)])
            pleins = np.isfinite(vois_z)
            a_boucher = vide & (pleins.sum(0) >= 5)
            if not a_boucher.any():
                break
            k = np.where(pleins, vois_z, np.inf).argmin(0)
            yy, xx = np.nonzero(a_boucher)
            im[yy, xx] = vois_i[k[yy, xx], yy, xx]
            z[yy, xx] = vois_z[k[yy, xx], yy, xx]
        return Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))


def arbres_du_paquet(paquet):
    """{genre : (bases glTF (n, 3), hauteurs)} lus dans les tables d'instances du paquet."""
    out = {"pin": [], "feuillu": [], "arbuste": []}
    for dossier in ("arbres", "versants", "arbustes", "mobilier"):
        for f in sorted((paquet / "instances" / dossier).glob("*.csv")):
            nom = f.stem.lower()
            if dossier == "mobilier" and "pine" not in nom and "tree" not in nom and "maple" not in nom:
                continue
            genre = "arbuste" if dossier == "arbustes" else "pin" if ("pine" in nom or "cypress" in nom) else "feuillu"
            with open(f, encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    h = float(r.get("hauteur_voulue_m") or r.get("hauteur_m") or 0) or (1.2 if genre == "arbuste" else 7.0)
                    out[genre].append((float(r["x_cm"]) / 100, float(r["z_cm"]) / 100, float(r["y_cm"]) / 100, h))
    return {g: (np.array(v)[:, :3], np.array(v)[:, 3]) for g, v in out.items() if v}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pk", nargs="+", type=float)
    ap.add_argument("--paquet", default=str(RACINE / "paquet_unreal"))
    ap.add_argument("--sortie", default=str(RACINE / "figures" / "apercu_lointain"))
    ap.add_argument("--champ", type=float, default=62.0)
    ap.add_argument("--sans-arbres", action="store_true")
    ap.add_argument("--lacet", type=float, default=0.0, help="degrés ajoutés à la direction de la route (positif : vers la gauche)")
    ap.add_argument("--suffixe", default="")
    ap.add_argument("--direct", action="store_true", help="images lointaines retraitées ici (vue_rasante, teinte_falaises) au lieu de celles du paquet")
    a = ap.parse_args()
    paquet = Path(a.paquet)
    ref = json.loads((s16.MOD / "repere.json").read_text(encoding="utf-8"))
    with open(s16.OUT / "chaussee_precise.csv", encoding="utf-8") as f:
        r = list(csv.DictReader(f))
    pk = np.array([float(x["pk_m"]) for x in r])
    A = s16.m08.to_gltf(np.array([[float(x["x_axe"]), float(x["y_axe"]), float(x["z_axe"])] for x in r]), ref).astype(float)
    proche = [(np.asarray(m["pos"], float), np.asarray(m["idx"]).reshape(-1, 3), t)
              for fichier, t in (("terrain_sol.glb", "terrain"), ("route.glb", "chaussee"), ("ouvrages.glb", "mur"))
              for m in s16.lire_glb(s16.MOD / fichier)]
    loin = s16.lire_glb(s16.MOD / "lointain.glb")
    arbres = {} if a.sans_arbres else arbres_du_paquet(paquet)
    pentes = s16.Pentes() if a.direct else None
    sortie = Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    for p in a.pk:
        i = int(np.argmin(np.abs(pk - p)))
        j = min(i + 8, len(pk) - 1)
        vers = (A[j] - A[i]) * np.array([1.0, 0.0, 1.0])
        vers /= max(np.linalg.norm(vers), 1e-9)
        ca, sa = np.cos(np.radians(a.lacet)), np.sin(np.radians(a.lacet))
        vers = np.array([vers[0] * ca + vers[2] * sa, 0.0, -vers[0] * sa + vers[2] * ca])
        oeil = A[i] + np.array([0.0, 1.2, 0.0]) + np.cross(vers, [0.0, 1.0, 0.0]) * 0.9
        e = Ecran(oeil, vers, 1280, 640, a.champ)
        for m in loin:
            g = m["pos"]
            d = np.hypot(g[:, 0] - oeil[0], g[:, 2] - oeil[2])
            if d.min() > 16000 or ((g - oeil) @ vers).max() < 0:
                continue
            _, taille, kx, ky = m["nom"].split("_")
            suf = f"{(int(kx) - s16.LOIN0[0]) // 1000}_{(int(ky) - s16.LOIN0[1]) // 1000}"
            fi = paquet / "textures" / "lointain" / f"T_FarRing{'' if taille == '1km' else 'L'}_{suf}.jpg"
            if a.direct:                                                   # sans passer par le paquet : pour régler le traitement
                im = Image.open(io.BytesIO(m["mat"]["image"])).convert("RGB")
                if d.min() > 2500 and im.width > 512:
                    im = im.reduce(im.width // 512)
                im = s16.vue_rasante(im, float(np.ptp(g[:, 0])) / im.width)
                im, _ = s16.teinte_falaises(im, m, ref, pentes)
            else:
                im = Image.open(fi if fi.exists() else io.BytesIO(m["mat"]["image"])).convert("RGB")
            if d.min() > 2500 and im.width > 512:                          # loin : inutile de garder toute l'image
                im = im.reduce(im.width // 512)
            # éclairage : normales ramenées vers la verticale comme dans le paquet (--lointain-aplat 0,85 au-delà de 800 m)
            e.triangles(g, m["idx"], None, uv=m["uv"], image=np.asarray(im), lumiere=None)
        for pos, tri, t in proche:
            pres = np.hypot(pos[:, 0] - oeil[0], pos[:, 2] - oeil[2]) < 700
            tt = tri[pres[tri].any(1)]
            if len(tt):
                e.triangles(pos, tt, TEINTES[t])
        for genre, (base, h) in arbres.items():
            e.houppiers(base, h, genre, 260.0 if genre == "arbuste" else 1500.0)
        im = e.image()
        ImageDraw.Draw(im).text((8, 6), f"PK {p:.0f} - aperçu du paysage hors jeu (images du relief lointain, arbres en silhouettes)", fill=(20, 20, 20))
        nom = f"pk_{int(round(p)):04d}{a.suffixe}.jpg"
        im.save(sortie / nom, quality=88)
        print("écrit :", nom)


if __name__ == "__main__":
    main()
