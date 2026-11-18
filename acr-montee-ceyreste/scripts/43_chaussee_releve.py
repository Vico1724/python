"""Relevé de la chaussée par tronçon de 50 m (sixième passe, 19/11/2026) : marquage et usure, d'après Panoramax.

Demande de l'utilisateur (transmise par le coordinateur, mots exacts) : « Ça manque […] de marquage au sol, de routes
abîmées ». Le relevé de la deuxième passe (aspect_chaussee.json, chaussee_surface_releve.json) ne portait que sur 24 vues
plongeantes ; celui-ci couvre chaque tronçon de 50 m du PK 100 à la zone d'arrêt (PK 3770), avec toutes les images HD
téléchargées (2 à 10 par tronçon).

Source : Panoramax, Région Sud / Immergis, 08/09/2025, 360°, licence Etalab 2.0 (data/reference/photos_rue_panoramax.csv) ;
images non versionnées (data/raw/panoramax/).

Usage :
  python scripts/43_chaussee_releve.py planches [PK0 PK1]   vues plongeantes de la chaussée (vers la descente et vers la
                    montée), graduées : PK de l'axe tous les 5 m (étiquette tous les 10 m), bords de chaussée de 07 en
                    pointillé ; 9 vues par planche, data/raw/panoramax/chaussee/planche_<PK>.jpg (non versionnées)
  python scripts/43_chaussee_releve.py zoom ID CAP TANGAGE CHAMP [LARGEUR]   une vue graduée (cap Lambert-93)
  python scripts/43_chaussee_releve.py bilan               relit data/reference/chaussee_releve_50m.json, contrôle que
                    chaque tronçon est renseigné et que chaque élément cite une image existante ; écrit
                    data/processed/chaussee_releve_bilan.json
Le relevé lui-même (data/reference/chaussee_releve_50m.json) est écrit à la main, planche par planche ; il est lu par
11_route_ouvrages.py (marquage, usure rendue en maillages minces texturés) et 16_paquet_unreal.py (décalques du jeu).
"""
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from acr_geo import OUT, RAW, REF  # noqa: E402

import importlib.util  # noqa: E402


def _charger(nom, f):
    s = importlib.util.spec_from_file_location(nom, ICI / f)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


F40 = _charger("f40", "40_facades.py")
DOSSIER = RAW / "panoramax"
SORTIE = DOSSIER / "chaussee"
RELEVE = REF / "chaussee_releve_50m.json"
Image.MAX_IMAGE_PIXELS = None
try:
    FNT = ImageFont.truetype("DejaVuSans.ttf", 13)
    FNTG = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
except OSError:
    FNT = FNTG = None


def chaussee():
    with open(OUT / "chaussee_precise.csv", encoding="utf-8") as f:
        R = list(csv.DictReader(f))
    g = lambda k: np.array([float(r[k]) for r in R])  # noqa: E731
    return {"pk": g("pk_m"), "A": np.c_[g("x_axe"), g("y_axe"), g("z_axe")],
            "G": np.c_[g("x_gauche"), g("y_gauche"), g("z_gauche")], "D": np.c_[g("x_droite"), g("y_droite"), g("z_droite")]}


def projeter(P, c, zc, cap, tang, fov_h, W, H):
    """Points Lambert-93 (n, 3) -> pixels (u, v) de la vue sténopé (cap L93, tangage, champ horizontal) ; nan derrière."""
    f = (W / 2) / math.tan(math.radians(fov_h) / 2)
    d = np.asarray(P, float) - np.array([c[0], c[1], zc])
    a = math.radians(cap)
    x = d[:, 0] * math.cos(a) - d[:, 1] * math.sin(a)          # à droite
    y = d[:, 0] * math.sin(a) + d[:, 1] * math.cos(a)          # devant
    t = math.radians(tang)
    fw = y * math.cos(t) + d[:, 2] * math.sin(t)
    up = -y * math.sin(t) + d[:, 2] * math.cos(t)
    u = np.where(fw > 0.5, W / 2 + f * x / np.maximum(fw, 1e-6), np.nan)
    v = np.where(fw > 0.5, H / 2 - f * up / np.maximum(fw, 1e-6), np.nan)
    return u, v


def vue_graduee(r, ch, cap, tang, fov_h, W, H, eq=None):
    """Vue sténopé d'un panorama, graduée : PK de l'axe (croix tous les 5 m, étiquette tous les 10 m), bords de 07."""
    if eq is None:
        eq = np.asarray(Image.open(DOSSIER / f"{r['id']}.jpg").convert("RGB"))
    c = np.array([float(r["x_l93"]), float(r["y_l93"])])
    gam = F40.convergence(*c)
    zc = F40.z_camera(r, None) if False else _zc(r, ch)
    im = Image.fromarray(F40.vue_pinhole(eq, float(r["azimut_deg"]), cap - gam, tang, fov_h, W, H))
    d = ImageDraw.Draw(im)
    dist = np.hypot(ch["A"][:, 0] - c[0], ch["A"][:, 1] - c[1])
    sel = dist < 45
    for cle, coul in (("G", (255, 210, 0)), ("D", (255, 210, 0))):
        u, v = projeter(ch[cle][sel], c, zc, cap, tang, fov_h, W, H)
        for k in range(0, len(u), 2):
            if np.isfinite(u[k]) and 0 <= u[k] < W and 0 <= v[k] < H:
                d.point((u[k], v[k]), fill=coul)
                d.point((u[k] + 1, v[k]), fill=coul)
    pkr = ch["pk"]
    for s in np.arange(math.ceil(pkr[sel].min() / 5) * 5, pkr[sel].max(), 5.0):
        i = int(np.argmin(np.abs(pkr - s)))
        if dist[i] > 40:
            continue
        u, v = projeter(ch["A"][i:i + 1], c, zc, cap, tang, fov_h, W, H)
        if not (np.isfinite(u[0]) and 0 <= u[0] < W and 0 <= v[0] < H):
            continue
        d.line((u[0] - 5, v[0], u[0] + 5, v[0]), fill=(0, 255, 255), width=2)
        if int(round(s)) % 10 == 0:
            d.text((u[0] + 6, v[0] - 14), f"{s:.0f}", fill=(0, 255, 255), font=FNT, stroke_width=2, stroke_fill=(0, 0, 0))
    return im


_ZC = {}


def _zc(r, ch):
    c = np.array([float(r["x_l93"]), float(r["y_l93"])])
    d = np.hypot(ch["A"][:, 0] - c[0], ch["A"][:, 1] - c[1])
    i = int(np.argmin(d))
    return float(ch["A"][i, 2]) + F40.H_CAMERA if d[i] < 8 else float(ch["A"][i, 2]) + F40.H_CAMERA


def images_hd(pk0, pk1):
    L = [r for r in F40.photos() if r["date"].startswith("2025") and pk0 <= float(r["pk_m"]) <= pk1
         and (DOSSIER / f"{r['id']}.jpg").exists()]
    return sorted(L, key=lambda r: float(r["pk_m"]))


def cap_route(ch, r, vers_descente=True):
    """Cap Lambert-93 de la route au droit de l'image, vers la descente (PK décroissants) ou la montée."""
    c = np.array([float(r["x_l93"]), float(r["y_l93"])])
    i = int(np.argmin(np.hypot(ch["A"][:, 0] - c[0], ch["A"][:, 1] - c[1])))
    j = max(i - 12, 0) if vers_descente else min(i + 12, len(ch["pk"]) - 1)
    v = ch["A"][j, :2] - c
    return math.degrees(math.atan2(v[0], v[1]))


def cmd_planches(pk0=100.0, pk1=3775.0, W=760, H=400, par=9, sens=(True,)):
    ch = chaussee()
    SORTIE.mkdir(parents=True, exist_ok=True)
    L = images_hd(pk0, pk1)
    vues = []
    for r in L:
        eq = np.asarray(Image.open(DOSSIER / f"{r['id']}.jpg").convert("RGB"))
        for desc in sens:
            cap = cap_route(ch, r, desc)
            im = vue_graduee(r, ch, cap, -9.0, 75.0, W, H, eq)
            dd = ImageDraw.Draw(im)
            dd.rectangle((0, 0, W, 20), fill=(0, 0, 0))
            dd.text((4, 2), f"{r['id'][:8]}  PK {float(r['pk_m']):.0f}  vers la {'descente' if desc else 'montée'}  cap {cap:.0f}",
                    fill=(255, 255, 255), font=FNTG)
            vues.append((float(r["pk_m"]), im))
        print(r["id"][:8], r["pk_m"], flush=True)
    # 9 vues par planche, rangées par PK
    for k in range(0, len(vues), par):
        lot = vues[k:k + par]
        pl = Image.new("RGB", (3 * W + 8, 3 * H + 8), (255, 255, 255))
        for j, (_, im) in enumerate(lot):
            pl.paste(im, ((j % 3) * (W + 4), (j // 3) * (H + 4)))
        nom = SORTIE / f"planche_{int(lot[0][0]):+05d}.jpg"
        pl.save(nom, quality=80)
        print("écrit", nom)


def cmd_bandes(pk0=100.0, pk1=3750.0, px=0.025, demi=5.5, par=5):
    """Bandes redressées (vue en plan) de la chaussée, 50 m par bande : chaque point du sol (station s, décalage o) est
    pris sur le panorama le plus proche situé à 4-18 m (capot et lointain écartés). Surface de 07 (axe et bords, pente
    en travers linéaire). Graduée : un trait tous les 5 m, PK tous les 10 m ; montée vers la droite, gauche en haut."""
    ch = chaussee()
    pk = ch["pk"]
    Ls = [r for r in images_hd(pk0 - 30, pk1 + 30)]
    C = np.array([[float(r["x_l93"]), float(r["y_l93"])] for r in Ls])
    eqs = {}

    def eq(i):
        if i not in eqs:
            if len(eqs) > 12:
                eqs.pop(next(iter(eqs)))
            eqs[i] = np.asarray(Image.open(DOSSIER / f"{Ls[i]['id']}.jpg").convert("RGB"))
        return eqs[i]

    gams = [F40.convergence(*c) for c in C]
    zcs = [_zc(r, ch) for r in Ls]
    SORTIE.mkdir(parents=True, exist_ok=True)
    bandes = []
    for k0 in np.arange(pk0, pk1, 50.0):
        S = np.arange(k0, k0 + 50.0, px)
        O = np.arange(demi, -demi, -px)                       # gauche (o > 0) en haut
        ip = lambda Q: np.column_stack([np.interp(S, pk, Q[:, j]) for j in range(3)])  # noqa: E731
        a, g, d = ip(ch["A"]), ip(ch["G"]), ip(ch["D"])
        t = np.gradient(a[:, :2], axis=0); t /= np.linalg.norm(t, axis=1)[:, None]
        n = np.column_stack([-t[:, 1], t[:, 0]])
        hG = np.einsum("ij,ij->i", g[:, :2] - a[:, :2], n); hD = -np.einsum("ij,ij->i", d[:, :2] - a[:, :2], n)
        img = np.full((len(O), len(S), 3), 255, np.uint8)
        X = a[None, :, 0] + n[None, :, 0] * O[:, None]
        Y = a[None, :, 1] + n[None, :, 1] * O[:, None]
        zg = a[None, :, 2] + (g[None, :, 2] - a[None, :, 2]) * np.clip(O[:, None] / np.maximum(hG[None, :], 0.5), 0, 9)
        zd = a[None, :, 2] + (d[None, :, 2] - a[None, :, 2]) * np.clip(-O[:, None] / np.maximum(hD[None, :], 0.5), 0, 9)
        Z = np.where(O[:, None] >= 0, zg, zd)
        # image retenue par colonne : la plus proche du point de l'axe à 4-18 m, de préférence en aval (vue sans capot)
        # par blocs de 4 m : l'image prise en amont (PK de la caméra de s + 6 à s + 24 m, regard vers la descente : le
        # capot cache les 5 premiers mètres), la plus proche ; sinon la plus proche en aval
        pkc = np.array([float(r["pk_m"]) for r in Ls])
        best = np.zeros(len(S), int); ok = np.zeros(len(S), bool)
        for b0 in np.arange(k0, k0 + 50.0, 4.0):
            cols = (S >= b0) & (S < b0 + 4.0)
            m = b0 + 2.0
            ecart = pkc - m
            cand = np.flatnonzero((ecart >= 6.0) & (ecart <= 24.0))
            if not len(cand):
                cand = np.flatnonzero((ecart <= -6.0) & (ecart >= -24.0))
            if len(cand):
                best[cols] = cand[np.argmin(np.abs(ecart[cand]))]; ok[cols] = True
        utilisees = []
        for i in np.unique(best[ok]):
            cols = np.flatnonzero(ok & (best == i))
            e = eq(i); He, We = e.shape[:2]
            dx = X[:, cols] - C[i, 0]; dy = Y[:, cols] - C[i, 1]; dz = Z[:, cols] - zcs[i]
            az = np.degrees(np.arctan2(dx, dy)) - gams[i] - float(Ls[i]["azimut_deg"])
            el = np.arctan2(dz, np.hypot(dx, dy))
            u = np.mod((az / 360.0 + 0.5) * We, We).astype(np.int32)
            v = np.clip((0.5 - el / math.pi) * He, 0, He - 1).astype(np.int32)
            img[:, cols] = e[v, u]
            utilisees.append(Ls[i]["id"][:8])
        im = Image.fromarray(img)
        dr = ImageDraw.Draw(im)
        H = len(O)
        for sk in np.arange(math.ceil(k0 / 5) * 5, k0 + 50, 5.0):
            x = int((sk - k0) / px)
            dr.line((x, 0, x, 14), fill=(0, 255, 255), width=2); dr.line((x, H - 14, x, H), fill=(0, 255, 255), width=2)
            if int(round(sk)) % 10 == 0:
                dr.text((x + 3, 1), f"{sk:.0f}", fill=(0, 255, 255), font=FNT, stroke_width=2, stroke_fill=(0, 0, 0))
        # bords de 07 (pointillé magenta) et axe (petits points)
        for hh in (hG, -hD):
            yy = ((demi - hh) / px).astype(int)
            for x in range(0, len(S), 40):
                if 0 <= yy[x] < H:
                    dr.point((x, yy[x]), fill=(255, 0, 255)); dr.point((x + 1, yy[x]), fill=(255, 0, 255))
        dr.text((4, H - 30), f"PK {k0:.0f}-{k0 + 50:.0f}  gauche en haut, montée vers la droite ; images : {' '.join(utilisees)}",
                fill=(255, 255, 255), font=FNT, stroke_width=2, stroke_fill=(0, 0, 0))
        bandes.append((k0, im))
        print(f"PK {k0:.0f}", utilisees, flush=True)
    for k in range(0, len(bandes), par):
        lot = bandes[k:k + par]
        W = lot[0][1].size[0]; Hh = lot[0][1].size[1]
        pl = Image.new("RGB", (W, par * (Hh + 6)), (255, 255, 255))
        for j, (_, im) in enumerate(lot):
            pl.paste(im, (0, j * (Hh + 6)))
        nom = SORTIE / f"bandes_{int(lot[0][0]):+05d}.jpg"
        pl.save(nom, quality=82)
        print("écrit", nom)


# Planches photo réelle / rendu de contrôle (15_vues_decor.py) de la sixième passe : (image, vers la descente ?, tangage,
# champ horizontal, légende) ; le cap suit la route au droit de l'image
PLANCHES = {
    "pk0450_faiencage": ("3a0d33e4", True, -8.0, 75.0, "faïençage des deux voies, PK 440-470"),
    "pk0893_epingle": ("a7c86442", True, -6.0, 75.0, "épingle du PK 893, glissière et balises"),
    "pk1301_reprise": ("4f05c439", True, -6.0, 75.0, "voie montante reprise, A14 « chaussée déformée »"),
    "pk1517_epingle": ("fa96e3fc", True, -8.0, 80.0, "épingle du PK 1517, traces de dérapage"),
    "pk2061_cabane": ("df39fc97", True, -4.0, 75.0, "cabane du PK 2061, enrobé récent"),
    "pk2150_epingle": ("f807be2e", True, -6.0, 75.0, "épingle du PK 2150, enrobé récent"),
    "pk2622_traces": ("fa486745", True, -6.0, 75.0, "traces de pneus du carrefour du PK 2622"),
    "pk2854_hameau": ("0119a756", True, -4.0, 80.0, "hameau, maison du PK 2854, faïençage"),
    "pk2903_hameau": ("c270e1ae", True, -4.0, 80.0, "hameau, haie et murs du PK 2880-2920"),
    "pk2938_voie_laterale": ("f71b87e9", True, -4.0, 80.0, "voie latérale du PK 2938, faïençage"),
    "pk3104_pr8": ("2540de5a", True, -6.0, 75.0, "rectangles du PR 8, traces"),
    "pk3226_maison": ("a133f64e", True, -3.0, 80.0, "maison du PK 3226, mur enduit"),
    "pk3709_arret": ("e48878e8", True, -4.0, 75.0, "zone d'arrêt, rive continue et caniveau"),
}


def cmd_planches_rendu(noms=()):
    ch = chaussee()
    L = {r["id"][:8]: r for r in F40.photos()}
    specs = {}
    for nom, (pref, desc, tang, fov, leg) in PLANCHES.items():
        if noms and nom not in noms:
            continue
        r = L[pref]
        specs[nom] = (pref, cap_route(ch, r, desc), tang, fov, leg)
    F40.planches_libres(specs, ICI.parent / "figures" / "affinage" / "sixieme_passe")


def cmd_zoom(pref, cap, tang, fov, W=1400):
    ch = chaussee()
    r = next(x for x in F40.photos() if x["id"].startswith(pref))
    im = vue_graduee(r, ch, float(cap), float(tang), float(fov), W, int(W * 0.62))
    SORTIE.mkdir(parents=True, exist_ok=True)
    nom = SORTIE / f"zoom_{pref[:8]}_{float(cap):.0f}_{float(tang):.0f}.jpg"
    im.save(nom, quality=85)
    print("écrit", nom)


def cmd_bilan():
    R = json.loads(RELEVE.read_text(encoding="utf-8"))
    ids = {r["id"][:8] for r in F40.photos()}
    manque, sans_image, compte = [], [], {}
    pk = {t["pk"][0] for t in R["troncons"]}
    for a in range(100, 3750, 50):
        if a not in pk:
            manque.append(a)
    for t in R["troncons"]:
        for im in t.get("images", []):
            if im[:8] not in ids:
                sans_image.append((t["pk"], im))
        for e in t.get("elements", []):
            compte[e["genre"]] = compte.get(e["genre"], 0) + 1
            if not e.get("images") or any(i[:8] not in ids for i in e["images"]):
                sans_image.append((t["pk"], e["genre"]))
    for e in R.get("marquage", []):
        compte["marquage:" + e["genre"]] = compte.get("marquage:" + e["genre"], 0) + 1
        if not e.get("images") or any(i[:8] not in ids for i in e["images"]):
            sans_image.append((e.get("pk"), e["genre"]))
    b = {"troncons": len(R["troncons"]), "troncons_manquants": manque, "elements_par_genre": compte,
         "elements_sans_image_valide": sans_image}
    (OUT / "chaussee_releve_bilan.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(b, ensure_ascii=False, indent=1))
    if manque or sans_image:
        sys.exit(1)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(0)
    if a[0] == "planches":
        n = [x for x in a[1:] if not x.startswith("--")]
        cmd_planches(*(map(float, n[0:2]) if len(n) >= 2 else ()), sens=(True, False) if "--deux" in a else (True,))
    elif a[0] == "bandes":
        cmd_bandes(*(map(float, a[1:3]) if len(a) >= 3 else ()))
    elif a[0] == "rendus":
        cmd_planches_rendu(set(a[1:]))
    elif a[0] == "zoom":
        cmd_zoom(a[1], *a[2:5], *(int(x) for x in a[5:6]))
    elif a[0] == "bilan":
        cmd_bilan()
