"""Cale une vidéo du jeu sur la route d'après la barre de progression de l'écran, et mesure les secousses de la caméra.

Le calage par les virages (19_calage_video.py) dérive dans les lignes droites et ne sait pas que la voiture attend le
départ. La barre de progression du jeu, en haut de l'écran, donne directement la part de la spéciale parcourue.
Étalonnage fait le 13/11/2026 sur la vidéo du quatrième essai, contre le calage par les virages :
    PK = 31,5 + 6696,4 x part remplie de la barre
la barre allant, sur une image de 1920 px de large, de la colonne 612 à la colonne 1307, lignes 51 à 57.

Secousses : la caméra est fixée à la voiture, le capot ne bouge donc pas dans l'image ; quand la voiture tangue ou
saute, le paysage monte et descend. Le script mesure, d'une image à la suivante, le décalage vertical d'une bande du
paysage (au-dessus du capot, hors des affichages), puis en garde la part rapide (moins d'une demi-seconde) : c'est ce
que le pilote perçoit comme une route bosselée. Sert à situer les bosses signalées en jeu, à comparer au profil de la
route (data/processed/chaussee_precise.csv).

Écrit data/processed/calage_<nom>.json : table_t_s_pk_m (un point toutes les 0,2 s) et secousses (un point tous les
10 m : écart-type du décalage rapide, en millièmes de la hauteur d'image, et vitesse).

Usage : python -P scripts/19b_calage_barre.py <vidéo du jeu> <nom> [--a 31.5 --b 6696.4]
À lancer avec « python -P » depuis un dossier neutre si la vidéo est un fichier téléchargé.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

RACINE = Path(__file__).resolve().parents[1]
BARRE = {"x": (612.0, 1307.0), "y": (52.0, 57.0), "largeur_de_reference": 1920.0, "blanc": 228}


def part_remplie(im):
    f = im.shape[1] / BARRE["largeur_de_reference"]
    x0, x1 = int(round(BARRE["x"][0] * f)), int(round(BARRE["x"][1] * f))
    y0, y1 = int(round(BARRE["y"][0] * f)), int(round(BARRE["y"][1] * f))
    bande = im[y0:y1 + 1, x0:x1 + 1].min(axis=2).astype(np.float32).mean(axis=0)     # le plus sombre des trois canaux
    blanc = bande > BARRE["blanc"]
    # La partie parcourue du secteur EN COURS est blanche ; un secteur terminé prend la couleur de son temps (vert,
    # rouge) et n'est plus blanc ; les repères de secteur sont de fins traits blancs (3 à 4 px). Le front est donc la
    # fin de la dernière suite blanche plus longue qu'un repère. Sans suite (début d'un secteur) : 0, que la règle
    # « la barre ne recule pas » remplace ensuite par la dernière valeur lue.
    d = np.diff(np.r_[0, blanc.astype(np.int8), 0])
    debuts, fins = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    longues = [int(z) for a, z in zip(debuts, fins) if z - a >= 4.5 * f]
    return (max(longues) / len(blanc)) if longues else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video")
    ap.add_argument("nom")
    ap.add_argument("--a", type=float, default=31.5)
    ap.add_argument("--b", type=float, default=6696.4)
    ap.add_argument("--sans-secousses", action="store_true")
    a = ap.parse_args()
    cap = cv2.VideoCapture(a.video)
    ips = cap.get(cv2.CAP_PROP_FPS)
    n_im = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    pas_barre = max(1, int(round(0.2 * ips)))
    t_b, part, t_s, dy = [], [], [], []
    avant = None
    fen = None
    i = 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        t = i / ips
        if i % pas_barre == 0:
            t_b.append(t)
            part.append(part_remplie(im))
        if not a.sans_secousses:
            h, w = im.shape[:2]
            # bande du paysage : sous les affichages du haut, au-dessus du capot, hors des bords
            g = cv2.cvtColor(cv2.resize(im[int(0.24 * h):int(0.62 * h), int(0.22 * w):int(0.78 * w)], (256, 160), interpolation=cv2.INTER_AREA),
                             cv2.COLOR_BGR2GRAY).astype(np.float32)
            if fen is None:
                fen = cv2.createHanningWindow((256, 160), cv2.CV_32F)
            if avant is not None:
                (dx_, dy_), rep = cv2.phaseCorrelate(avant, g, fen)
                t_s.append(t)
                dy.append(dy_ / 160.0 * 0.38 * 1000.0 if rep > 0.03 else np.nan)     # en millièmes de la hauteur d'image
            avant = g
        i += 1
    t_b, part = np.array(t_b), np.array(part)
    # la barre ne recule pas ; une lecture fausse (nuage blanc derrière la barre) dépasse d'un coup : on l'écarte
    med = np.array([np.median(part[max(0, k - 5):k + 6]) for k in range(len(part))])
    part = np.where(np.abs(part - med) > 0.01, med, part)
    part = np.maximum.accumulate(part)
    # au passage d'un repère de secteur le front n'est pas lisible pendant une demi-seconde : la valeur reste figée,
    # puis saute. On relie les lectures qui avancent par une droite (vitesse constante sur le trou).
    avance = np.r_[True, np.diff(part) > 0]
    part = np.interp(t_b, t_b[avance], part[avance])
    pk = a.a + a.b * part
    # la barre avance par pixels (quelques mètres) : lissage sur 1,4 s, sans toucher à l'arrêt du départ
    k = np.ones(7) / 7
    pk_l = np.convolve(np.pad(pk, 3, mode="edge"), k, mode="valid")
    pk_l = np.maximum.accumulate(np.where(part <= 0, pk, pk_l))
    depart = float(t_b[np.argmax(part > 0)]) if (part > 0).any() else 0.0
    arrivee = float(t_b[np.argmax(part >= part.max())])
    out = {"video": Path(a.video).name, "duree_s": round(n_im / ips, 1), "images_par_s": round(ips, 3),
           "methode": f"barre de progression du jeu : PK = {a.a} + {a.b} x part remplie (scripts/19b_calage_barre.py)",
           "depart_t_s": round(depart, 1), "arrivee_t_s": round(arrivee, 1),
           "pk_au_debut_m": round(float(pk_l[0]), 1), "pk_a_la_fin_m": round(float(pk_l[-1]), 1),
           "table_t_s_pk_m": [[round(float(t), 2), round(float(p), 1)] for t, p in zip(t_b, pk_l)]}
    if not a.sans_secousses and len(dy) > 100:
        t_s, dy = np.array(t_s), np.array(dy)
        dy = np.where(np.isfinite(dy), dy, 0.0)
        n_l = max(3, int(round(0.5 * ips)) | 1)                      # part lente (virage, relief) retirée : moyenne sur 0,5 s
        lent = np.convolve(np.pad(dy, n_l // 2, mode="edge"), np.ones(n_l) / n_l, mode="valid")
        rapide = dy - lent
        pk_s = np.interp(t_s, t_b, pk_l)
        v = np.gradient(pk_s, t_s) * 3.6
        sec = []
        for p0 in np.arange(0.0, pk_l[-1], 10.0):
            sel = (pk_s >= p0) & (pk_s < p0 + 10.0) & (t_s > depart + 1.0)
            if sel.sum() >= 3:
                sec.append([float(p0 + 5.0), round(float(rapide[sel].std()), 2), round(float(np.median(v[sel])), 0)])
        out["secousses"] = {"unite": "écart-type du décalage vertical rapide d'une image à la suivante, en millièmes de la hauteur d'image",
                            "colonnes": ["pk_m", "secousse", "vitesse_kmh"], "table": sec}
    f = RACINE / "data" / "processed" / f"calage_{a.nom}.json"
    f.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(t_b)} lectures de la barre ; départ à t = {depart:.1f} s, arrivée à t = {arrivee:.1f} s ; PK {pk_l[0]:.0f} à {pk_l[-1]:.0f}")
    print("écrit :", f)


if __name__ == "__main__":
    main()
