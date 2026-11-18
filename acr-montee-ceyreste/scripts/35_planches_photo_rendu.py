"""Planches photo réelle (Panoramax 08/09/2025) | rendu texturé de l'étape 15 (figures/phase5/vue_<nom>.png), au même PK.

Cadrage voisin, pas identique : la photo est prise du toit d'un véhicule qui descend (voie opposée, ~2,5 m) ; le rendu
est à 1,1 m sur la voie de droite de la montée. Le rendu montre des arbres FIGURANTS (silhouettes calculées par 15), pas
ceux du jeu. Photo : Panoramax, Région Sud / Immergis, licence Etalab 2.0.
Usage : python scripts/35_planches_photo_rendu.py
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from acr_geo import FIG, param  # noqa: E402

s = importlib.util.spec_from_file_location("p26", ICI / "26_photos_rue.py")
P = importlib.util.module_from_spec(s); s.loader.exec_module(P)
FOV_H = 2 * math.degrees(math.atan(math.tan(math.radians(52.0) / 2) * 16 / 9))   # champ horizontal du rendu de 15


def main():
    Image.MAX_IMAGE_PIXELS = None
    L = {r["id"]: r for r in P.charger_liste()}
    ret = [i for i in json.loads((P.DOSSIER / "retenues.json").read_text()) if (P.DOSSIER / f"{i}.jpg").exists()]
    pk, x, y = P.axe()
    try:
        fnt = ImageFont.truetype("DejaVuSans.ttf", 16)
    except OSError:
        fnt = None
    dest = FIG / "affinage" / "photo_rendu"; dest.mkdir(parents=True, exist_ok=True)
    for nom, (p, visee) in param("vues_decor").items():
        if not isinstance(visee, (int, float)) or visee < 0:
            continue
        rendu = FIG / "phase5" / f"vue_{nom}.png"
        if not rendu.exists():
            continue
        i = min(ret, key=lambda k: abs(float(L[k]["pk_m"]) - p))
        r = L[i]
        _, _, cap = P.projeter(pk, x, y, float(r["x_l93"]), float(r["y_l93"]))
        eq = np.asarray(Image.open(P.DOSSIER / f"{i}.jpg").convert("RGB"))
        ph = Image.fromarray(P.vue_plane(eq, float(r["azimut_deg"]), cap, fov=FOV_H, largeur=960, hauteur=540, tangage=-3))
        rd = Image.open(rendu).convert("RGB").resize((960, 540))
        pl = Image.new("RGB", (1930, 600), (255, 255, 255))
        pl.paste(ph, (0, 30)); pl.paste(rd, (970, 30))
        d = ImageDraw.Draw(pl)
        d.text((6, 6), f"PHOTO RÉELLE - Panoramax {i[:8]}, PK {float(r['pk_m']):.0f}, 08/09/2025", fill=(0, 0, 0), font=fnt)
        d.text((976, 6), f"RENDU de contrôle (étape 15) - PK {p:.0f} - arbres figurants, hors jeu", fill=(0, 0, 0), font=fnt)
        d.text((6, 576), "Photo : Panoramax, Région Sud / Immergis, licence Etalab 2.0. Cadrages voisins : caméra photo "
               "plus haute, sur l'autre voie.", fill=(60, 60, 60), font=fnt)
        pl.save(dest / f"{nom}.jpg", quality=84)
        print("écrit", nom)


def avant_apres(nom, planche_avant):
    """Synthèse photo | rendu avant | rendu après, à partir d'une planche précédente (git show <commit>:...) et de la
    planche courante : python scripts/35_planches_photo_rendu.py --avant-apres NOM FICHIER_AVANT"""
    dest = FIG / "affinage" / "photo_rendu"
    av, ap = Image.open(planche_avant).convert("RGB"), Image.open(dest / f"{nom}.jpg").convert("RGB")
    ph, ra, rp = av.crop((0, 30, 960, 570)), av.crop((970, 30, 1930, 570)), ap.crop((970, 30, 1930, 570))
    pl = Image.new("RGB", (2900, 600), (255, 255, 255))
    for k, im in enumerate((ph, ra, rp)):
        pl.paste(im, (k * 970, 30))
    try:
        fnt = ImageFont.truetype("DejaVuSans.ttf", 16)
    except OSError:
        fnt = None
    d = ImageDraw.Draw(pl)
    for k, t in enumerate(("PHOTO RÉELLE (Panoramax f9160d60, 08/09/2025)", "RENDU AVANT (passe 2 : ni mur, ni clôture, ni panneau)",
                           "RENDU APRÈS (passe 3 : murs, muret + grillage occultant, EB20)")):
        d.text((k * 970 + 6, 6), t, fill=(0, 0, 0), font=fnt)
    d.text((6, 576), "Photo : Panoramax, Région Sud / Immergis, licence Etalab 2.0. Rendus de contrôle hors jeu (étape 15).",
           fill=(60, 60, 60), font=fnt)
    pl.save(dest / f"{nom}_avant_apres.jpg", quality=84)
    print("écrit", f"{nom}_avant_apres")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--avant-apres"]:
        avant_apres(sys.argv[2], sys.argv[3])
    else:
        main()
