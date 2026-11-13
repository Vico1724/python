"""Paires d'images au même PK : une vidéo du jeu à gauche, la vidéo de reconnaissance à droite.

Sert à relever, tout le long de la spéciale, ce qui sépare le rendu du jeu de la réalité. Les deux vidéos doivent avoir
été calées sur la route par scripts/19_calage_video.py (data/processed/calage_<nom>.json).

Usage : python -P scripts/20_planches_comparees.py <vidéo du jeu> <nom de son calage> <vidéo de reconnaissance>
                                                   [--pas 40] [--avance-jeu-m 0] [--sortie figures/compare_<nom>]
Les images vont dans figures/compare_<nom>/pk_XXXX.jpg (hors dépôt). À lancer avec « python -P » depuis un dossier
neutre : les vidéos sont des fichiers téléchargés.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

RACINE = Path(__file__).resolve().parents[1]


def table(nom):
    c = json.loads((RACINE / "data" / "processed" / f"calage_{nom}.json").read_text(encoding="utf-8"))
    t = np.array(c["table_t_s_pk_m"], float)
    return t[:, 0], np.maximum.accumulate(t[:, 1])


def image(cap, t, largeur):
    cap.set(cv2.CAP_PROP_POS_MSEC, 1000.0 * t)
    ok, im = cap.read()
    if not ok:
        return None
    h = int(round(im.shape[0] * largeur / im.shape[1]))
    return cv2.resize(im, (largeur, h), interpolation=cv2.INTER_AREA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jeu")
    ap.add_argument("nom")
    ap.add_argument("reco")
    ap.add_argument("--pas", type=float, default=40.0)
    ap.add_argument("--largeur", type=int, default=960)
    ap.add_argument("--avance-jeu-m", type=float, default=0.0, help="correction ajoutée au PK de la vidéo du jeu")
    ap.add_argument("--sortie")
    a = ap.parse_args()
    tj, pj = table(a.nom)
    tr, pr = table("reco")
    pj = pj + a.avance_jeu_m
    sortie = Path(a.sortie) if a.sortie else RACINE / "figures" / f"compare_{a.nom}"
    sortie.mkdir(parents=True, exist_ok=True)
    cj, cr = cv2.VideoCapture(a.jeu), cv2.VideoCapture(a.reco)
    n = 0
    for pk in np.arange(max(pj[0], pr[0], 20.0) // a.pas * a.pas + a.pas, min(pj[-1], pr[-1]), a.pas):
        ij, ir = image(cj, float(np.interp(pk, pj, tj)), a.largeur), image(cr, float(np.interp(pk, pr, tr)), a.largeur)
        if ij is None or ir is None:
            continue
        h = max(ij.shape[0], ir.shape[0])
        planche = np.zeros((h + 34, 2 * a.largeur + 8, 3), np.uint8)
        planche[34:34 + ij.shape[0], :a.largeur] = ij
        planche[34:34 + ir.shape[0], a.largeur + 8:] = ir
        cv2.putText(planche, f"PK {pk:.0f}  -  JEU (t = {np.interp(pk, pj, tj):.1f} s)", (8, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.putText(planche, f"RECONNAISSANCE (t = {np.interp(pk, pr, tr):.1f} s)", (a.largeur + 16, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.imwrite(str(sortie / f"pk_{int(round(pk)):04d}.jpg"), planche, [cv2.IMWRITE_JPEG_QUALITY, 82])
        n += 1
    print(f"{n} paires dans {sortie}")


if __name__ == "__main__":
    main()
