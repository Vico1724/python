"""Façades des bâtiments vus de près (quatrième passe du 18-19/11/2026) : relevé sur les panoramas Panoramax et outils.

Demande de l'utilisateur (mots exacts) : « En decore ok mais les zone visible doivent etre vraiment bien faite ». Les 30
bâtiments de premier plan et les 5 de plan moyen (data/processed/visibilite.json, scripts/38_visibilite.py) avaient un
toit relu sur le LiDAR mais des façades nues. Ce script prépare et contrôle le relevé de leurs façades ; la géométrie
est faite par scripts/facades.py, appelé par 31_bati.py.

Source des images : Panoramax, Région Sud / Immergis, 08/09/2025, 360°, licence Etalab 2.0 (data/reference/
photos_rue_panoramax.csv). Les images ne sont pas versionnées (data/raw/panoramax/, 12 288 x 6 144 px).

Usage :
  python scripts/40_facades.py images [CLEABS...]   choisit pour chaque bâtiment les panoramas qui montrent le mieux ses
                                                     façades, télécharge ceux qui manquent (HD)
  python scripts/40_facades.py vues [CLEABS...]      vues rectifiées vers chaque bâtiment (data/raw/panoramax/facades/),
                                                     emprise projetée, façades nommées F0, F1… et graduées tous les mètres
  python scripts/40_facades.py zoom CLEABS IMAGE FACE [LARGEUR]  vue de face d'une façade, graduée (pour lire les ouvertures)
  python scripts/40_facades.py teinte CLEABS IMAGE FACE X0 X1 Z0 Z1   couleur médiane (sRGB 0-255) d'un rectangle de façade
                                                     (x le long de la façade depuis son coin gauche vu de dehors, z depuis
                                                     le pied), et celle de la chaussée au soleil et à l'ombre de la même image
  python scripts/40_facades.py planches [CLEABS...]  planches photo réelle / rendu (même point de vue, même direction)

Repères : façade Fk = k-ième côté de l'emprise BD TOPO simplifiée (anneau dans le sens trigonométrique, en partant du
sommet le plus au sud-ouest), x = 0 à son coin gauche vu de l'extérieur. Caps : les azimuts Panoramax sont comptés du
nord géographique ; le nord du quadrillage Lambert-93 en diffère ici de 1,92° (convergence des méridiens), corrigée.
Hauteur de la caméra : 2,6 m au-dessus de la chaussée (véhicule de prise de vue ; contrôlé sur les vues : les pieds de
façade projetés tombent sur le pied réel à quelques pixels près, voir les vues).
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import shapely
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from acr_geo import FIG, OUT, RAW, REF, ROOT, l93, wgs, _session  # noqa: E402
from facades import faces  # noqa: E402

import importlib.util  # noqa: E402


def _charger(nom, f):
    s = importlib.util.spec_from_file_location(nom, ICI / f)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


P26 = _charger("p26", "26_photos_rue.py")
DOSSIER = RAW / "panoramax"
SORTIE = DOSSIER / "facades"
RELEVES = REF / "facades"
H_CAMERA = 2.6
Image.MAX_IMAGE_PIXELS = None
try:
    FNT = ImageFont.truetype("DejaVuSans.ttf", 15)
    FNTG = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
except OSError:
    FNT = FNTG = None


def convergence(x, y):
    """Cap Lambert-93 du nord géographique (degrés, négatif ici) : cap_vrai = cap_l93 - convergence."""
    lo, la = wgs(x, y)
    x2, y2 = l93(lo, la + 1e-4)
    return math.degrees(math.atan2(x2 - x, y2 - y))


class Relief:
    def __init__(self):
        m31 = _charger("m31", "31_bati.py")
        self.r = m31.Relief()

    def z(self, x, y):
        return self.r.z(np.atleast_1d(x), np.atleast_1d(y))

    def s(self, x, y):
        return self.r._z(self.r.mns, np.atleast_1d(x), np.atleast_1d(y))


_AXE = None


def z_camera(r, rel, h_cam=H_CAMERA):
    """Altitude de la caméra : chaussée la plus proche (axe de chaussee_precise.csv, à moins de 8 m) + h_cam ; sinon MNT.
    Le MNT 0,5 m pris au point GPS tombe parfois sur le haut d'un mur de soutènement ou d'un talus (2 à 3 m trop haut)."""
    global _AXE
    if _AXE is None:
        with open(OUT / "chaussee_precise.csv", encoding="utf-8") as f:
            R = list(csv.DictReader(f))
        _AXE = np.array([[float(x["x_axe"]), float(x["y_axe"]), float(x["z_axe"])] for x in R])
    c = np.array([float(r["x_l93"]), float(r["y_l93"])])
    d = np.hypot(_AXE[:, 0] - c[0], _AXE[:, 1] - c[1])
    i = int(np.argmin(d))
    if d[i] < 8.0:
        return float(_AXE[i, 2]) + h_cam
    return float(rel.z(*c)[0]) + h_cam


def batiments_cibles():
    """Bâtiments de premier plan et de plan moyen, triés : zone de départ (PK -150 à 150) puis durée de visibilité."""
    v = json.loads((OUT / "visibilite.json").read_text(encoding="utf-8"))
    bb = {b["cleabs"]: b for b in json.loads((OUT / "bati_bilan.json").read_text(encoding="utf-8"))["batiments"]}
    L = [dict(b, **{k: bb[b["cleabs"]].get(k) for k in ("distance_chaussee_m", "hauteur_faitage_m", "egout_m",
                                                          "z_terrain_m", "forme_toit", "surface_m2")})
         for b in v["batiments"] if b["niveau"] in ("premier_plan", "plan_moyen")]
    L.sort(key=lambda b: (b["niveau"] != "premier_plan", not (-150 <= b["pk_m"] <= 150), -b["vu_sur_m"]))
    return L


def emprises():
    m31 = _charger("m31", "31_bati.py")
    return {str(p.get("cleabs")): (p, P) for p, P in m31.lire(OUT / "couloir" / "batiment.geojson")}


def photos():
    return [r for r in P26.charger_liste() if r["date"].startswith("2025") and str(r["fov_deg"]) == "360"]


def score_images(b, P, F, L, rel, zmax):
    """Pour chaque façade, images où elle est vue de face ou de biais, à 4-70 m, sans relief ni végétation devant
    (rayon vers 5 points de la façade à mi-hauteur, MNS - MNT)."""
    res = {}
    for r in L:
        c = np.array([float(r["x_l93"]), float(r["y_l93"])])
        d0 = P.distance(shapely.Point(c))
        if d0 > 75 or d0 < 2:
            continue
        zc = float(rel.z(*c)[0]) + H_CAMERA
        for f in F:
            m = (f["a"] + f["b"]) / 2
            dv = c - m
            d = float(np.linalg.norm(dv))
            cosi = float(dv @ f["normale"]) / d
            if cosi < 0.2 or d > 75 or f["long_m"] < 1.5:
                continue
            # visibilité : part des 5 points non masqués
            vu = 0
            for s in np.linspace(0.1, 0.9, 5):
                p = f["a"] + (f["b"] - f["a"]) * s + f["normale"] * 0.3
                zp = float(rel.z(*p)[0]) + 1.6
                k = max(int(np.linalg.norm(p - c) / 0.5), 2)
                t = np.linspace(0.05, 1 - 2.0 / max(np.linalg.norm(p - c), 2.5), k)   # 2 m avant la façade (débord du toit)
                X, Y = c[0] + (p[0] - c[0]) * t, c[1] + (p[1] - c[1]) * t
                Z = zc + (zp - zc) * t
                h = rel.s(X, Y)
                bloque = (h > Z + 0.2).sum()
                vu += bloque <= 2
            sc = (0.15 + vu) / 5.15 * cosi * min(1.0, 18.0 / max(d, 6.0)) * min(1.0, f["long_m"] / 4)
            res.setdefault(f["nom"], []).append((round(float(sc), 3), r["id"], round(d, 1), round(math.degrees(math.acos(min(cosi, 1))), 0), int(vu)))
    for k in res:
        res[k].sort(reverse=True)
    return res


def telecharger(i, url):
    dst = DOSSIER / f"{i}.jpg"
    if dst.exists():
        return dst
    for essai in range(4):
        try:
            rr = _session.get(url, timeout=180); rr.raise_for_status()
            dst.write_bytes(rr.content)
            return dst
        except Exception as e:  # noqa: BLE001
            print("  reprise", i, e, flush=True)
            import time; time.sleep(3 * (essai + 1))
    return None


def cmd_images(cibles):
    L = photos()
    E = emprises()
    rel = Relief()
    SORTIE.mkdir(parents=True, exist_ok=True)
    choix = json.loads((SORTIE / "choix_images.json").read_text()) if (SORTIE / "choix_images.json").exists() else {}
    Lid = {r["id"]: r for r in L}
    for b in batiments_cibles():
        if cibles and b["cleabs"] not in cibles:
            continue
        p, P = E[b["cleabs"]]
        F = faces(P)
        sc = score_images(b, P, F, L, rel, None)
        ids = []
        for f in F:
            for s in sc.get(f["nom"], [])[:3]:
                if s[1] not in ids:
                    ids.append(s[1])
        ids = ids[:8]
        choix[b["cleabs"]] = {"pk_m": b["pk_m"], "cote": b["cote"], "niveau": b["niveau"],
                              "faces": [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in f.items()} for f in F],
                              "scores": {k: v[:4] for k, v in sc.items()}, "images": ids}
        print(b["cleabs"], b["pk_m"], b["cote"], "faces vues :", {k: len(v) for k, v in sc.items()}, "images :", len(ids), flush=True)
        for i in ids:
            telecharger(i, Lid[i]["url_hd"])
    (SORTIE / "choix_images.json").write_text(json.dumps(choix, indent=1), encoding="utf-8")


# --- projection dans une vue plane (même géométrie que 26_photos_rue.vue_plane) ---------------------------------------
class Vue:
    def __init__(self, r, rel, cap_l93, fov, largeur, hauteur, tangage, cor_cap=0.0, h_cam=H_CAMERA, cor_tang=0.0):
        self.r = r
        self.c = np.array([float(r["x_l93"]), float(r["y_l93"])])
        self.zc = z_camera(r, rel, h_cam)
        self.gam = convergence(*self.c)
        self.cap_l93, self.fov, self.W, self.H, self.tang = cap_l93, fov, largeur, hauteur, tangage
        self.cap_vrai = cap_l93 - self.gam + cor_cap          # cap géographique demandé à l'image
        self.cor_tang = cor_tang                              # assiette de la caméra (image non mise à niveau)
        self.f = (largeur / 2) / math.tan(math.radians(fov) / 2)

    def image(self):
        eq = np.asarray(Image.open(DOSSIER / f"{self.r['id']}.jpg").convert("RGB"))
        return Image.fromarray(P26.vue_plane(eq, float(self.r["azimut_deg"]), self.cap_vrai, fov=self.fov,
                                             largeur=self.W, hauteur=self.H, tangage=self.tang + self.cor_tang))

    def proj(self, X):
        """Points Lambert-93 (n, 3) -> pixels (n, 2) ; nan derrière."""
        X = np.atleast_2d(X)
        d = X[:, :2] - self.c
        az = np.degrees(np.arctan2(d[:, 0], d[:, 1]))
        a = np.radians((az - self.cap_l93 + 540) % 360 - 180)
        el = np.arctan2(X[:, 2] - self.zc, np.hypot(d[:, 0], d[:, 1]))
        u = self.f * np.tan(a)
        v = -self.f * np.tan(el - math.radians(self.tang)) / np.cos(a)
        out = np.column_stack([u + self.W / 2, v + self.H / 2])
        out[np.abs(a) > math.radians(85)] = np.nan
        return out


def dessiner_emprise(im, V, F, z_pied, z_egout, z_faitage=None, faces_sel=None, graduer=True):
    d = ImageDraw.Draw(im)
    for f in F:
        if faces_sel and f["nom"] not in faces_sel:
            continue
        a, b = np.asarray(f["a"]), np.asarray(f["b"])
        n = np.asarray(f["normale"])
        visible = (V.c - (a + b) / 2) @ n > 0
        col = (255, 230, 0) if visible else (120, 120, 255)
        pts = V.proj(np.array([[*a, z_pied], [*b, z_pied], [*b, z_egout], [*a, z_egout]]))
        if np.isnan(pts).any():
            continue
        q = [tuple(p) for p in pts]
        d.line(q + [q[0]], fill=col, width=1 if not visible else 2)
        if visible and graduer:
            L = float(np.linalg.norm(b - a))
            for s in np.arange(0, L + 1e-6, 1.0):
                p = a + (b - a) * s / L
                q0, q1 = V.proj(np.array([[*p, z_pied], [*p, z_pied + (0.6 if s % 5 else 1.2)]]))
                d.line([tuple(q0), tuple(q1)], fill=(255, 60, 60), width=2)
            for zz in np.arange(z_pied, z_egout + 1e-6, 1.0):
                q0, q1 = V.proj(np.array([[*a, zz], [*(a + (b - a) * 0.35 / L), zz]]))
                d.line([tuple(q0), tuple(q1)], fill=(0, 255, 255), width=2)
            m = V.proj(np.array([[*((a + b) / 2), z_pied + 0.3]]))[0]
            d.text((m[0] - 10, m[1] + 4), f"{f['nom']} {f['orientation']}", fill=(255, 255, 0), font=FNTG,
                   stroke_width=2, stroke_fill=(0, 0, 0))


def pieds(P, rel):
    R = np.asarray(P.exterior.coords)[:-1]
    return float(rel.z(R[:, 0], R[:, 1]).min())


def vue_vers(r, rel, P, z0, z1, largeur=1600, marge=12.0, cor_cap=0.0, h_cam=H_CAMERA, fov_min=28.0, cor_tang=0.0):
    c = np.array([float(r["x_l93"]), float(r["y_l93"])])
    R = np.asarray(P.exterior.coords)[:-1]
    az = np.degrees(np.arctan2(R[:, 0] - c[0], R[:, 1] - c[1]))
    m = math.degrees(math.atan2(np.sin(np.radians(az)).mean(), np.cos(np.radians(az)).mean()))
    rel_az = (az - m + 540) % 360 - 180
    span = rel_az.max() - rel_az.min()
    fov = float(np.clip(span + 2 * marge, fov_min, 120.0))
    cap = m + (rel_az.max() + rel_az.min()) / 2
    zc = z_camera(r, rel, h_cam)
    dist = np.hypot(R[:, 0] - c[0], R[:, 1] - c[1])
    el = np.degrees(np.arctan2(np.r_[np.full(len(R), z0), np.full(len(R), z1)] - zc, np.r_[dist, dist]))
    tang = float((el.max() + el.min()) / 2)
    hauteur = int(np.clip(largeur * (el.max() - el.min() + 2 * marge) / fov, largeur * 0.45, largeur * 0.8))
    return Vue(r, rel, cap, fov, largeur, hauteur, tang, cor_cap, h_cam, cor_tang)


def releve(cle):
    f = RELEVES / f"{cle}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def cmd_vues(cibles):
    choix = json.loads((SORTIE / "choix_images.json").read_text())
    Lid = {r["id"]: r for r in photos()}
    E = emprises()
    rel = Relief()
    bb = {b["cleabs"]: b for b in json.loads((OUT / "bati_bilan.json").read_text(encoding="utf-8"))["batiments"]}
    for cle, c in choix.items():
        if cibles and cle not in cibles:
            continue
        p, P = E[cle]
        F = faces(P)
        z0 = pieds(P, rel)
        b = bb[cle]
        zt = b["z_terrain_m"]
        z_eg, z_ft = zt + b["egout_m"], zt + b["hauteur_faitage_m"]
        dd = SORTIE / cle; dd.mkdir(parents=True, exist_ok=True)
        cor = {i["id"]: i.get("correction_cap_deg", 0.0) for i in releve(cle).get("images", [])}
        tuiles = []
        for i in c["images"]:
            if not (DOSSIER / f"{i}.jpg").exists():
                continue
            V = vue_vers(Lid[i], rel, P, z0, z_ft + 1.5, cor_cap=cor.get(i, 0.0))
            im = V.image()
            brut = im.copy()
            brut.save(dd / f"{i[:8]}_brut.jpg", quality=92)
            dessiner_emprise(im, V, F, z0, z_eg)
            dw = ImageDraw.Draw(im)
            dw.text((6, 4), f"{cle[-9:]}  image {i[:8]}  PK {float(Lid[i]['pk_m']):.0f}  cap {V.cap_l93:.0f}  fov {V.fov:.0f}  "
                    f"d={P.distance(shapely.Point(V.c)):.0f} m", fill=(255, 255, 0), font=FNTG, stroke_width=2, stroke_fill=(0, 0, 0))
            im.save(dd / f"{i[:8]}_grille.jpg", quality=90)
            tuiles.append(im)
        # planche de contact
        if tuiles:
            w = 800
            ts = [t.resize((w, int(t.size[1] * w / t.size[0]))) for t in tuiles]
            hmax = max(t.size[1] for t in ts)
            nc = 2
            nl = (len(ts) + nc - 1) // nc
            pl = Image.new("RGB", (nc * w + 6, nl * (hmax + 4)), (0, 0, 0))
            for k, t in enumerate(ts):
                pl.paste(t, ((k % nc) * (w + 6), (k // nc) * (hmax + 4)))
            pl.save(dd / "planche.jpg", quality=86)
        print(cle, len(tuiles), "vues", flush=True)


def cmd_zoom(cle, i, face, largeur=1600, marge=4.0):
    """Vue serrée sur une façade (graduée), pour lire la position des ouvertures."""
    Lid = {r["id"]: r for r in photos()}
    E = emprises()
    rel = Relief()
    p, P = E[cle]
    F = {f["nom"]: f for f in faces(P)}
    f = F[face]
    bb = {b["cleabs"]: b for b in json.loads((OUT / "bati_bilan.json").read_text(encoding="utf-8"))["batiments"]}[cle]
    z0 = pieds(P, rel)
    z_eg = bb["z_terrain_m"] + bb["egout_m"]
    z_ft = bb["z_terrain_m"] + bb["hauteur_faitage_m"]
    if os.environ.get("ZOOM_HAUT"):                    # hauteur de cadrage forcée (bâtiment plus récent que le LiDAR)
        z_ft = z0 + float(os.environ["ZOOM_HAUT"])
    cor = {x["id"]: x.get("correction_cap_deg", 0.0) for x in releve(cle).get("images", [])}
    Pf = Polygon([f["a"], f["b"], np.asarray(f["b"]) + 0.01 * np.asarray(f["normale"]), np.asarray(f["a"]) + 0.01 * np.asarray(f["normale"])])
    V = vue_vers(Lid[i], rel, Pf, z0, z_ft + 1.0, largeur=largeur, marge=marge, cor_cap=cor.get(i, 0.0), fov_min=12.0)
    im = V.image()
    im.save(SORTIE / cle / f"{i[:8]}_{face}_zoom_brut.jpg", quality=92)
    dessiner_emprise(im, V, [f], z0, z_eg)
    ImageDraw.Draw(im).text((6, 4), f"{cle[-9:]} {face} image {i[:8]} fov {V.fov:.0f}", fill=(255, 255, 0), font=FNTG,
                            stroke_width=2, stroke_fill=(0, 0, 0))
    out = SORTIE / cle / f"{i[:8]}_{face}_zoom.jpg"
    im.save(out, quality=92)
    print(out)


def cmd_teinte(cle, i, face, x0, x1, z0r, z1r):
    """Couleur médiane d'un rectangle de façade, et chaussée au soleil / à l'ombre de la même image."""
    Lid = {r["id"]: r for r in photos()}
    E = emprises()
    rel = Relief()
    p, P = E[cle]
    f = {f["nom"]: f for f in faces(P)}[face]
    zp = pieds(P, rel)
    a, b = np.asarray(f["a"]), np.asarray(f["b"])
    L = np.linalg.norm(b - a)
    t = (b - a) / L
    cor = {x["id"]: x.get("correction_cap_deg", 0.0) for x in releve(cle).get("images", [])}
    Pf = Polygon([a + t * x0, a + t * x1, a + t * x1 + 0.01 * f["normale"], a + t * x0 + 0.01 * f["normale"]])
    V = vue_vers(Lid[i], rel, Pf, zp + z0r, zp + z1r, largeur=800, marge=1.0, cor_cap=cor.get(i, 0.0), fov_min=3.0)
    im = np.asarray(V.image()).astype(float)
    pts = V.proj(np.array([[*(a + t * x0), zp + z0r], [*(a + t * x1), zp + z1r]]))
    u0, u1 = sorted([int(pts[0, 0]), int(pts[1, 0])]); v0, v1 = sorted([int(pts[0, 1]), int(pts[1, 1])])
    u0, v0 = max(u0, 0), max(v0, 0)
    zone = im[v0:v1, u0:u1].reshape(-1, 3)
    med = np.median(zone, 0) if len(zone) else np.array([np.nan] * 3)
    # correction de l'éclairage : la chaussée (enrobé gris, à peu près neutre) de la même image, à l'ombre et au soleil,
    # sert de référence de gris ; la façade est ramenée au neutre de la chaussée sous le même éclairage (ombre ou soleil,
    # choisi d'après la clarté de la façade par rapport aux deux). Le rapport des canaux corrigé garde la teinte propre
    # de l'enduit, débarrassée du bleu du ciel à l'ombre ou du jaune du soleil bas.
    ref = chaussee_ref(Lid[i], rel)
    lin = lambda c: np.where(np.asarray(c) / 255 <= 0.04045, np.asarray(c) / 255 / 12.92, ((np.asarray(c) / 255 + 0.055) / 1.055) ** 2.4)  # noqa: E731
    srgb = lambda l: np.where(l <= 0.0031308, l * 12.92, 1.055 * np.clip(l, 0, None) ** (1 / 2.4) - 0.055) * 255  # noqa: E731
    out = {"rgb": [int(x) for x in med], "pixels": len(zone), "chaussee": ref}
    if ref:
        cle_r = "ombre" if ("ombre" in ref and ("soleil" not in ref or abs(np.mean(med) - np.mean(ref["ombre"]) * 1.8) <
                                                 abs(np.mean(med) - np.mean(ref["soleil"]) * 1.8))) else "soleil"
        g = lin(ref[cle_r])
        out["eclairage"] = cle_r
        if 0.75 < g[2] / max(g[0], 1e-6) < 1.35:      # référence plausible (gris) ; sinon pas de correction
            cor = lin(med) / (g / g.mean())
            out["rgb_corrige"] = [int(round(float(x))) for x in srgb(cor)]
        else:
            out["rgb_corrige"] = None
            out["note"] = "référence de chaussée trop colorée (reflet, végétation) : non corrigé"
    print(json.dumps(out))
    return med


def chaussee_ref(r, rel):
    """Couleurs médianes de la chaussée à 3-15 m de la caméra, à l'ombre et au soleil (sRGB 0-255) ; marquage écarté."""
    pk, x, y = P26.axe()
    c = np.array([float(r["x_l93"]), float(r["y_l93"])])
    d = np.hypot(x - c[0], y - c[1])
    sel = (d > 3) & (d < 15)
    if sel.sum() < 3:
        return None
    eq = Image.open(DOSSIER / f"{r['id']}.jpg")
    W, H = eq.size
    gam = convergence(*c)
    zc = float(rel.z(*c)[0]) + H_CAMERA
    vals = []
    for xx, yy in zip(x[sel], y[sel]):
        for o in (-1.0, 0.0, 1.0):                     # trois points en travers (évite la ligne axiale au centre)
            t = np.array([yy - c[1], -(xx - c[0])]); t = t / max(np.linalg.norm(t), 1e-6)
            px_, py_ = xx + t[0] * o * 1.6, yy + t[1] * o * 1.6
            az = math.degrees(math.atan2(px_ - c[0], py_ - c[1])) - gam
            el = math.atan2(float(rel.z(px_, py_)[0]) - zc, math.hypot(px_ - c[0], py_ - c[1]))
            u = int(((az - float(r["azimut_deg"])) / 360 + 0.5) % 1.0 * W)
            v = int((0.5 - el / math.pi) * H)
            a = np.asarray(eq.crop((u - 6, v - 6, u + 6, v + 6)).convert("RGB")).reshape(-1, 3).astype(float)
            vals.append(np.median(a, 0))
    V = np.array(vals)
    V = V[V.mean(1) < 200]                              # marquage blanc écarté
    if len(V) < 4:
        return None
    lum = V.mean(1)
    seuil = (lum.min() + lum.max()) / 2 if lum.max() > 1.5 * lum.min() else None
    out = {}
    if seuil is None:
        out["soleil" if lum.mean() > 90 else "ombre"] = [int(v) for v in np.median(V, 0)]
    else:
        out["ombre"] = [int(v) for v in np.median(V[lum < seuil], 0)]
        out["soleil"] = [int(v) for v in np.median(V[lum >= seuil], 0)]
    return out


def teinte_ortho(P):
    """Couleur médiane du toit sur l'ortho IGN 20 cm (emprise rétrécie de 0,6 m), sRGB 0-255."""
    import rasterio
    from rasterio.mask import mask
    with rasterio.open(RAW / "ortho_20cm.tif") as s:
        g = P.buffer(-0.6)
        if g.is_empty:
            g = P
        a, _ = mask(s, [g.__geo_interface__], crop=True, filled=False)
    a = a[:3].reshape(3, -1)
    ok = ~np.ma.getmaskarray(a).any(0)
    v = np.asarray(a)[:, ok].T.astype(float)
    if len(v) < 10:
        return None
    # écarte la végétation qui déborde (vert dominant) et les ombres franches
    lum = v.mean(1)
    garde = (v[:, 1] < v[:, 0] * 1.02) & (lum > np.percentile(lum, 20))
    return [int(x) for x in np.median(v[garde] if garde.sum() > 10 else v, 0)]


def vue_pinhole(eq, cap_image, cap_vue, tang, fov_h, W, H):
    """Vue perspective exacte (sténopé, tangage compris) d'un panorama équirectangulaire ; caps géographiques."""
    He, We = eq.shape[:2]
    f = (W / 2) / math.tan(math.radians(fov_h) / 2)
    u, v = np.meshgrid(np.arange(W) - W / 2 + 0.5, np.arange(H) - H / 2 + 0.5)
    t = math.radians(tang)
    dy = f * math.cos(t) - (-v) * math.sin(t)          # avant
    dz = f * math.sin(t) + (-v) * math.cos(t)          # haut
    dx = u
    az = np.degrees(np.arctan2(dx, dy)) + (cap_vue - cap_image)
    el = np.arctan2(dz, np.hypot(dx, dy))
    px = np.mod((az / 360.0 + 0.5) * We, We).astype(np.int32)
    py = np.clip((0.5 - el / math.pi) * He, 0, He - 1).astype(np.int32)
    return eq[py, px]


def cmd_planches(cibles):
    """Planche photo réelle | rendu de contrôle (15_vues_decor.py) depuis la position de la caméra Panoramax, même cap,
    même tangage, même champ (sténopé 1600 x 900 des deux côtés)."""
    import subprocess
    import tempfile
    Lid = {r["id"]: r for r in photos()}
    E = emprises()
    rel = Relief()
    bb = {b["cleabs"]: b for b in json.loads((OUT / "bati_bilan.json").read_text(encoding="utf-8"))["batiments"]}
    dest = FIG / "affinage" / "facades"; dest.mkdir(parents=True, exist_ok=True)
    W, H = 1600, 900
    vues, meta = {}, {}
    for fr in sorted(RELEVES.glob("*.json")):
        R = json.loads(fr.read_text(encoding="utf-8"))
        cle = R["cleabs"]
        if cibles and cle not in cibles:
            continue
        p, P = E[cle]
        z0 = pieds(P, rel)
        b = bb[cle]
        zt = b["z_terrain_m"]
        hmax = max([v["egout_z"] for v in R.get("volumes", [])] + [b["hauteur_faitage_m"] + zt - z0 - 1.0]) + 3.0
        for k, im in enumerate(R.get("planches") or [R["images"][0]]):
            i = next(k for k in Lid if k.startswith(im["id"][:8])); r = Lid[i]
            V = vue_vers(r, rel, P, z0, z0 + hmax, largeur=W, marge=im.get("marge", 14.0), cor_cap=im.get("correction_cap_deg", 0.0))
            fov_h = max(V.fov, 40.0)
            fov_v = 2 * math.degrees(math.atan(math.tan(math.radians(fov_h) / 2) * H / W))
            cap, tg = V.cap_l93 + im.get("decalage_cap_deg", 0.0), V.tang
            e = [float(V.c[0]), float(V.c[1]), V.zc]
            dvec = [math.sin(math.radians(cap)) * math.cos(math.radians(tg)), math.cos(math.radians(cap)) * math.cos(math.radians(tg)),
                    math.sin(math.radians(tg))]
            nom = f"pk{int(round(R['pk_m'])):+05d}_{R['cote'][0].upper()}_{cle[-9:]}_{k}"
            vues[nom] = {"oeil_l93": e, "vise_l93": [e[j] + 100 * dvec[j] for j in range(3)], "fov": fov_v}
            meta[nom] = (R, i, r, V, cap, tg, fov_h)
    if not vues:
        return
    tmp = Path(tempfile.mkdtemp())
    (tmp / "vues.json").write_text(json.dumps(vues), encoding="utf-8")
    subprocess.run([sys.executable, str(ICI / "15_vues_decor.py"), "--fichier", str(tmp / "vues.json"), "--sortie", str(tmp)],
                   check=True)
    for nom, (R, i, r, V, cap, tg, fov_h) in meta.items():
        eq = np.asarray(Image.open(DOSSIER / f"{i}.jpg").convert("RGB"))
        ph = Image.fromarray(vue_pinhole(eq, float(r["azimut_deg"]), cap - V.gam + 0.0, tg, fov_h, W, H))
        rd = Image.open(tmp / f"vue_{nom}.png").convert("RGB").resize((W, H))
        pl = Image.new("RGB", (W, 2 * H + 70), (255, 255, 255))
        pl.paste(ph, (0, 26)); pl.paste(rd, (0, H + 44))
        d = ImageDraw.Draw(pl)
        d.text((6, 4), f"PHOTO RÉELLE - Panoramax {i[:8]}, PK {float(r['pk_m']):.0f}, 08/09/2025 - bâtiment {R['cleabs'][-9:]} "
               f"(PK {R['pk_m']}, {R['cote']})", fill=(0, 0, 0), font=FNTG)
        d.text((6, H + 24), "RENDU de contrôle (étape 15), même position, cap et champ - arbres figurants, hors jeu", fill=(0, 0, 0), font=FNTG)
        d.text((6, 2 * H + 48), "Photo : Panoramax, Région Sud / Immergis, licence Etalab 2.0 (floutage automatique de Panoramax).",
               fill=(60, 60, 60), font=FNT)
        pl = pl.resize((1200, int(pl.size[1] * 1200 / W)), Image.LANCZOS)
        pl.save(dest / f"{nom}.jpg", quality=82)
        print("écrit", dest / f"{nom}.jpg")


def planches_libres(specs, dest, titre_rendu="RENDU de contrôle (étape 15), même position, cap et champ - arbres figurants, hors jeu"):
    """specs : {nom: (id_image, cap_l93, tangage, fov_h, legende)} -> planches photo | rendu dans dest."""
    import subprocess
    import tempfile
    Lid = {r["id"]: r for r in photos()}
    rel = Relief()
    W, H = 1600, 900
    vues, meta = {}, {}
    for nom, (pref, cap, tg, fov_h, leg) in specs.items():
        i = next(k for k in Lid if k.startswith(pref)); r = Lid[i]
        c = np.array([float(r["x_l93"]), float(r["y_l93"])])
        zc = z_camera(r, rel)
        fov_v = 2 * math.degrees(math.atan(math.tan(math.radians(fov_h) / 2) * H / W))
        dvec = [math.sin(math.radians(cap)) * math.cos(math.radians(tg)), math.cos(math.radians(cap)) * math.cos(math.radians(tg)),
                math.sin(math.radians(tg))]
        e = [float(c[0]), float(c[1]), zc]
        vues[nom] = {"oeil_l93": e, "vise_l93": [e[j] + 100 * dvec[j] for j in range(3)], "fov": fov_v}
        meta[nom] = (i, r, cap, tg, fov_h, leg, convergence(*c))
    tmp = Path(tempfile.mkdtemp())
    (tmp / "vues.json").write_text(json.dumps(vues), encoding="utf-8")
    subprocess.run([sys.executable, str(ICI / "15_vues_decor.py"), "--fichier", str(tmp / "vues.json"), "--sortie", str(tmp)], check=True,
                   stdout=subprocess.DEVNULL)
    dest.mkdir(parents=True, exist_ok=True)
    for nom, (i, r, cap, tg, fov_h, leg, gam) in meta.items():
        eq = np.asarray(Image.open(DOSSIER / f"{i}.jpg").convert("RGB"))
        ph = Image.fromarray(vue_pinhole(eq, float(r["azimut_deg"]), cap - gam, tg, fov_h, W, H))
        rd = Image.open(tmp / f"vue_{nom}.png").convert("RGB").resize((W, H))
        pl = Image.new("RGB", (W, 2 * H + 70), (255, 255, 255))
        pl.paste(ph, (0, 26)); pl.paste(rd, (0, H + 44))
        d = ImageDraw.Draw(pl)
        d.text((6, 4), f"PHOTO RÉELLE - Panoramax {i[:8]}, PK {float(r['pk_m']):.0f}, 08/09/2025 - {leg}", fill=(0, 0, 0), font=FNTG)
        d.text((6, H + 24), titre_rendu, fill=(0, 0, 0), font=FNTG)
        d.text((6, 2 * H + 48), "Photo : Panoramax, Région Sud / Immergis, licence Etalab 2.0 (floutage automatique de Panoramax).",
               fill=(60, 60, 60), font=FNT)
        pl = pl.resize((1200, int(pl.size[1] * 1200 / W)), Image.LANCZOS)
        pl.save(dest / f"{nom}.jpg", quality=82)
        print("écrit", dest / f"{nom}.jpg")


EGLISE_L93 = (913941.0, 6238453.0)   # église de Ceyreste (BD TOPO BATIMENT0000000257165905, nature « Eglise »)


def cmd_silhouette():
    """Village vu de la route : trois points réels (PK -140, -50, 20), regard vers l'église, comparé au rendu."""
    Lid = {r["id"]: r for r in photos()}
    specs = {}
    for pk_v in (-140, -50, 20):
        r = min(Lid.values(), key=lambda r: abs(float(r["pk_m"]) - pk_v))
        c = np.array([float(r["x_l93"]), float(r["y_l93"])])
        cap = math.degrees(math.atan2(EGLISE_L93[0] - c[0], EGLISE_L93[1] - c[1]))
        specs[f"village_depuis_pk{pk_v:+05d}"] = (r["id"][:8], cap, -1.0, 60.0, f"vers l'église de Ceyreste (cap {cap:.0f}°, {np.hypot(*(c - EGLISE_L93)):.0f} m)")
    planches_libres(specs, FIG / "affinage" / "silhouette")


def cmd_depart_4():
    """Zone de départ (PK 0) dans quatre directions : montée, droite, descente, gauche."""
    Lid = {r["id"]: r for r in photos()}
    pk, x, y = P26.axe()
    r = min(Lid.values(), key=lambda r: abs(float(r["pk_m"]) - 0.0))
    _, _, cap = P26.projeter(pk, x, y, float(r["x_l93"]), float(r["y_l93"]))
    specs = {f"depart_{n}": (r["id"][:8], cap + d, 0.0, 80.0, f"zone de départ, {n}") for n, d in
             (("montee", 0), ("droite", 90), ("descente", 180), ("gauche", 270))}
    planches_libres(specs, FIG / "affinage" / "facades")


def cmd_profil(cle):
    """Hauteur du bâti au-dessus du MNT (MNS - MNT LiDAR 0,5 m) par bandes de 1 m le long de chaque façade (pour
    découper l'emprise en volumes de hauteurs différentes) ; z = altitude du MNT au pied, par mètre."""
    E = emprises()
    rel = Relief()
    p, P = E[cle]
    for f in faces(P):
        a, b, n = np.asarray(f["a"]), np.asarray(f["b"]), np.asarray(f["normale"])
        L = f["long_m"]
        t = (b - a) / L
        hs, zs = [], []
        for x in np.arange(0.5, L, 1.0):
            pts = np.array([a + t * x - n * d for d in np.arange(0.75, 6.0, 0.5)])
            ok = np.array([P.buffer(-0.4).contains(shapely.Point(q)) for q in pts])
            pts = pts[ok] if ok.any() else pts[:1]
            h = rel.s(pts[:, 0], pts[:, 1]) - rel.z(pts[:, 0], pts[:, 1])
            hs.append(round(float(np.percentile(h, 90)), 1))
            q = a + t * x + n * 0.6
            zs.append(round(float(rel.z(*q)[0]), 1))
        print(f["nom"], f["orientation"], L, "h:", hs, "z pied:", zs)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(0)
    if a[0] == "images":
        cmd_images(set(a[1:]))
    elif a[0] == "vues":
        cmd_vues(set(a[1:]))
    if len(a) > 2 and a[0] in ("zoom", "teinte"):
        a[2] = next(r["id"] for r in photos() if r["id"].startswith(a[2].replace(".jpg", "")))
    if a[0] == "zoom":
        cmd_zoom(a[1], a[2], a[3], int(a[4]) if len(a) > 4 else 1600)
    if a[0] == "teinte":
        cmd_teinte(a[1], a[2], a[3], *map(float, a[4:8]))
    elif a[0] == "planches":
        cmd_planches(set(a[1:]))
    elif a[0] == "silhouette":
        cmd_silhouette()
    elif a[0] == "depart4":
        cmd_depart_4()
    elif a[0] == "ortho":
        E = emprises()
        for c in a[1:]:
            print(c, teinte_ortho(E[c][1]))
    elif a[0] == "profil":
        cmd_profil(a[1])
    elif a[0] == "liste":
        for b in batiments_cibles():
            print(b["cleabs"], b["niveau"], b["pk_m"], b["cote"], b["vu_sur_m"], b["distance_chaussee_m"])
