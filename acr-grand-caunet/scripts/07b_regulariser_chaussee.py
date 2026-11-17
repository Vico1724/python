"""Régularise l'axe et les bords de la chaussée (data/processed/chaussee_precise.csv) : retire les petites
irrégularités dues aux mesures et aux coutures entre sources, SANS changer la forme de la route.

Ce que le diagnostic (scripts/17_diagnostic_trace.py) a montré le 12/11/2026 :
  - le cap de l'axe oscille d'environ 1 degré en permanence, celui des bords de 1,8 degré ;
  - des cassures de 5 à 24 degrés se trouvent aux limites des sections dont la largeur a été corrigée d'après les
    vidéos : la correction y commence et s'y arrête d'un mètre au suivant, ce qui décroche le bord, et l'axe avec lui ;
  - les sections dessinées à la main (approche, carrefour du Lion d'Or) ont aussi des cassures, mais voulues.

Principe (rien n'est redessiné, tout part des points mesurés) :
  1. AXE. Lissage de Whittaker d'ordre 3 sur x(s) et y(s) : il pénalise la VARIATION de courbure, pas la courbure ;
     un arc de cercle ou une droite le traversent presque inchangés. Il est réglé LÉGER (LAMBDA_AXE : longueurs
     d'onde de moins d'une dizaine de mètres). Autour d'une cassure artificielle seulement, le poids des points est
     abaissé, pour que le raccord se fasse sur une quinzaine de mètres au lieu d'un.
     Chaque point a une tolérance de déplacement selon sa source (TOLERANCE_M) ; tant qu'un point la dépasse, son
     poids est augmenté et le lissage refait. Les points « manuel » ne bougent pas.
  2. BORDS. Les demi-largeurs gauche et droite, mesurées perpendiculairement à l'axe régularisé, sont lissées à
     l'ordre 2 : un changement de largeur réel reste, un saut d'un mètre au suivant devient un raccord progressif.
  3. ALTITUDES. Chaque point déplacé garde l'altitude du profil en travers mesuré.
  3 bis. PROFIL EN TRAVERS. Là où l'altitude d'un bord a été lue hors de la chaussée (vide d'un pont, talus), les
     bords sont reconstruits d'après l'inclinaison et le toit des profils sains voisins. L'axe n'est pas touché.
  3 ter. PROFIL EN LONG ET DÉVERS (14/11/2026, après l'essai « route par moments trop bosselée »). L'altitude de l'axe
     est lissée à l'ordre 3 (bosses et creux de moins de 25 m de long retirés, 5 cm de déplacement au plus) ; le dévers
     de chaque demi-chaussée est débarrassé de ses valeurs aberrantes puis lissé à l'ordre 2 (2 % au plus). Les
     sections dessinées à la main gardent leur tracé mais reçoivent ces altitudes lissées.
  4. CONTRÔLES, écrits dans data/processed/regularisation_chaussee.json. Si l'un échoue, rien n'est écrit :
       - déplacement de chaque point sous sa tolérance ;
       - même enchaînement de virages (nombre, sens, position), lu à l'échelle de 25 m ;
       - même changement de cap dans chaque virage (à ECART_CAP_MAX_DEG près) ;
       - même rayon au sommet de chaque virage (à ECART_RAYON_MAX près), mesuré à l'échelle de 15 m, hors des
         abords d'une cassure artificielle, où le rayon d'origine n'a pas de sens ;
       - longueur de l'ES inchangée (à ECART_LONGUEUR_MAX_M près).

Le fichier d'origine est conservé dans data/processed/chaussee_precise_brut.csv ; ce script repart toujours de lui
s'il existe, il peut donc être relancé sans cumuler les lissages.

Usage : python scripts/07b_regulariser_chaussee.py [--essai]   (--essai : calcule et contrôle sans rien écrire)
"""
import argparse
import csv
import json
import shutil
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.signal import savgol_filter
from scipy.sparse.linalg import spsolve

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "data" / "processed" / "chaussee_precise.csv"
BRUT = RACINE / "data" / "processed" / "chaussee_precise_brut.csv"

# déplacement latéral maximal admis, en mètres, selon la source de la mesure
TOLERANCE_M = {"lidar+ortho": 0.20, "lidar": 0.25, "ortho": 0.40, "video": 0.50, "interpole": 0.50, "manuel": 0.0}
LAMBDA_AXE = 8.0          # lissage d'ordre 3 de l'axe : coupe sous 2 pi lambda^(1/6), soit environ 9 m de longueur d'onde.
                          # Essais du 12/11/2026 : 3e4 aplatissait les virages (refusé par les contrôles) ; 25 agrandissait leur
                          # rayon de 2,5 % en médiane ; 8 le laisse à moins de 1 % près, en retirant un tiers du bruit de cap.
# Vu en jeu le 13/11/2026 : bords d'asphalte et lignes blanches saccadés, alors que la route réelle est lisse. Mesuré :
# sur les lignes droites (PK 1050 à 1130 par exemple), l'axe relevé serpente de 15 cm environ avec une période de 25 à
# 30 m : une suite de petits « virages » de sens alternés, de 100 m de rayon, qui n'existent pas. Ce qui distingue un
# vrai virage de ce serpentement est le CHANGEMENT DE CAP : un vrai virage tourne la route d'au moins une douzaine de
# degrés, le serpentement oscille de quelques degrés sans la tourner. Le lissage est donc modulé par le changement de
# cap sur 40 m, lu sur un axe très lissé : léger (LAMBDA_AXE) dans les vrais virages, fort (LAMBDA_AXE_FORT, coupe sous
# 35 m environ) ailleurs. La tolérance de déplacement de chaque point reste celle d'avant : c'est elle qui garantit
# que la route ne bouge pas de plus de 20 à 25 cm.
LAMBDA_AXE_FORT = 30000.0
LAMBDA_PRE = 30000.0                         # pré-lissage qui sert seulement à lire le changement de cap
FENETRE_CAP = 20                             # demi-fenêtre, en mètres, du changement de cap
CAP_DROIT_DEG, CAP_VIRAGE_DEG = 5.0, 12.0    # changement de cap sur 40 m : en dessous lissage fort, au-dessus léger
MARGE_VIRAGE = 8                             # mètres avant et après un virage où le lissage reste celui du virage
CAP_VIRAGE_FRANC_DEG = 12.0                  # contrôles : un « virage » qui tourne moins que cela est une ondulation
LAMBDA_BORD = 3000.0      # lissage d'ordre 2 des demi-largeurs : raccord d'une quarantaine de mètres (60 jusqu'au 12/11/2026)
SEUIL_CASSURE_AXE_DEG = 5.0
SEUIL_CASSURE_BORD_DEG = 9.0
DEMI_RACCORD = 8          # points de part et d'autre d'une cassure où le poids est abaissé
POIDS_RACCORD = 0.02
ECART_RAYON_MAX = 0.10
ECART_CAP_MAX_DEG = 2.0
ECART_LONGUEUR_MAX_M = 3.0
TOIT_ADMIS = (-0.045, 0.030)      # demi-somme des dévers gauche et droit : toit de 4,5 % au plus, V de 3 % au plus
SAUT_DEVERS_MAX = 0.04            # variation de dévers d'un mètre au suivant
ELARGIR_PROFIL = 3                # points repris de part et d'autre d'un profil douteux
# profil en long et dévers (étape 3 ter)
LAMBDA_Z = 4000.0                 # ordre 3 : coupe sous 2 pi lambda^(1/6), soit 25 m de longueur d'onde environ
TOL_Z_M = 0.05                    # l'axe lissé reste à 5 cm au plus de l'altitude mesurée (précision du relevé laser)
LAMBDA_DEVERS = 1000.0            # ordre 2 : coupe sous 2 pi lambda^(1/4), soit 35 m environ (300 laissait des vrilles de 2 %/m)
TOL_DEVERS = 0.02                 # le dévers lissé reste à 2 % au plus du dévers mesuré (6 cm au bord)
FENETRE_DEVERS, ECART_DEVERS = 21, 0.03    # dévers aberrant : à plus de 3 % de la médiane sur 21 m
# relief réel rendu à la route lissée (fonction grain) : part de l'écart mesuré, plafonds en altitude et en dévers
GRAIN_PART, GRAIN_MAX_M, GRAIN_DEVERS_MAX = 0.75, 0.015, 0.006
LAMBDA_GRAIN = 1.0                # ordre 2 : ne rend que les ondulations de plus de 6 m de long environ


def whittaker(y, poids, lam, ordre):
    """lam : un nombre, ou un tableau de len(y) valeurs (lissage modulé le long de la route)."""
    n = len(y)
    d = sparse.eye(n, format="csc")
    for _ in range(ordre):
        d = d[1:] - d[:-1]
    if np.ndim(lam):
        lam = np.asarray(lam, float)
        k = ordre // 2
        return spsolve((sparse.diags(poids) + d.T @ sparse.diags(lam[k:k + n - ordre]) @ d).tocsc(), poids * y)
    return spsolve((sparse.diags(poids) + lam * (d.T @ d)).tocsc(), poids * y)


def lisser_borne(y, tol, lam, ordre, fixe, poids0, tours=60):
    """Whittaker dont aucun point ne s'écarte de sa valeur de plus de tol ; les points fixes ne bougent pas."""
    poids = np.where(fixe, 1.0e6, poids0).astype(float)
    z = y
    for _ in range(tours):
        z = whittaker(y, poids, lam, ordre)
        trop = (np.abs(z - y) > tol) & ~fixe
        if not trop.any():
            break
        poids[trop] *= 3.0
    return np.where(fixe, y, z)


def reperes(p):
    d = np.gradient(p, axis=0)
    t = d / np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-9)[:, None]
    return t, np.c_[-t[:, 1], t[:, 0]]                       # tangente, normale à gauche


def ecart_de_cap(p):
    """Écart, en degrés, entre le cap d'un segment et le cap lissé sur 21 m : une cassure y fait un pic."""
    d = np.diff(p, axis=0)
    cap = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    return np.degrees(cap - savgol_filter(cap, 21, 2))


def courbure(p, fenetre):
    d = np.gradient(p, axis=0)
    cap = savgol_filter(np.unwrap(np.arctan2(d[:, 1], d[:, 0])), fenetre | 1, 2)
    return np.gradient(cap) / np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-6), cap


def virages(p):
    """Enchaînement des virages à l'échelle de 25 m : [(i0, i1, sens)] pour chaque passage continu sous 150 m de rayon."""
    k, _ = courbure(p, 25)
    dans = np.abs(k) > 1.0 / 150.0
    out, i = [], 0
    while i < len(k):
        if dans[i]:
            j = i
            while j + 1 < len(k) and dans[j + 1] and np.sign(k[j + 1]) == np.sign(k[i]):
                j += 1
            if j - i >= 12:
                out.append((i, j, 1 if k[i] > 0 else -1, float(1.0 / np.abs(k[i:j + 1]).max())))
            i = j + 1
        else:
            i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--essai", action="store_true")
    ap.add_argument("--neuf", action="store_true", help="chaussee_precise.csv vient d'être recalculé par l'étape 07 : repartir de lui")
    a = ap.parse_args()
    source = SORTIE if a.neuf else (BRUT if BRUT.exists() else SORTIE)
    with open(source, encoding="utf-8") as f:
        lignes = list(csv.DictReader(f))
        champs = list(lignes[0].keys())
    col = lambda k: np.array([float(x[k]) for x in lignes])
    pk = col("pk_m")
    n = len(pk)
    axe, g, d = np.c_[col("x_axe"), col("y_axe")], np.c_[col("x_gauche"), col("y_gauche")], np.c_[col("x_droite"), col("y_droite")]
    za, zg, zd = col("z_axe"), col("z_gauche"), col("z_droite")
    src = [x["source"] for x in lignes]
    tol = np.array([TOLERANCE_M.get(s, 0.25) for s in src])
    fixe = np.array([s == "manuel" for s in src])

    # cassures artificielles : pics de cap sur l'axe ou sur un bord, hors des sections dessinées à la main
    pics = (np.abs(ecart_de_cap(axe)) > SEUIL_CASSURE_AXE_DEG) | (np.abs(ecart_de_cap(g)) > SEUIL_CASSURE_BORD_DEG) | \
           (np.abs(ecart_de_cap(d)) > SEUIL_CASSURE_BORD_DEG)
    pics = np.r_[pics, False] & ~fixe
    pres = np.zeros(n, bool)
    for i in np.where(pics)[0]:
        pres[max(0, i - DEMI_RACCORD): i + DEMI_RACCORD + 1] = True
    pres &= ~fixe
    poids0 = np.where(pres, POIDS_RACCORD, 1.0)
    groupes = []
    for i in np.where(pics)[0]:
        if groupes and i - groupes[-1][1] <= 2 * DEMI_RACCORD:
            groupes[-1][1] = i
        else:
            groupes.append([i, i])

    # 1. axe : lissage léger dans les vrais virages, fort ailleurs
    un = np.ones(n)
    pre = np.c_[whittaker(axe[:, 0], un, LAMBDA_PRE, 3), whittaker(axe[:, 1], un, LAMBDA_PRE, 3)]
    _, cap_pre = courbure(pre, 15)
    w = FENETRE_CAP
    tourne = np.abs(np.degrees(cap_pre[np.minimum(np.arange(n) + w, n - 1)] - cap_pre[np.maximum(np.arange(n) - w, 0)]))
    u = np.clip((tourne - CAP_DROIT_DEG) / (CAP_VIRAGE_DEG - CAP_DROIT_DEG), 0.0, 1.0)                    # 1 : vrai virage
    u = np.maximum.reduce([np.roll(u, j) for j in range(-MARGE_VIRAGE, MARGE_VIRAGE + 1)])
    u = savgol_filter(u, 21, 1)
    lam_axe = np.exp(np.log(LAMBDA_AXE_FORT) + u * u * (3 - 2 * u) * (np.log(LAMBDA_AXE) - np.log(LAMBDA_AXE_FORT)))
    ax = np.c_[lisser_borne(axe[:, 0], tol / np.sqrt(2), lam_axe, 3, fixe, poids0),
               lisser_borne(axe[:, 1], tol / np.sqrt(2), lam_axe, 3, fixe, poids0)]
    t0, n0 = reperes(axe)
    t1, n1 = reperes(ax)

    # 2. demi-largeurs sur la normale de l'axe régularisé ; la composante le long de l'axe des bords est gardée
    og, od = np.einsum("ij,ij->i", g - ax, n1), -np.einsum("ij,ij->i", d - ax, n1)
    og1 = lisser_borne(og, tol, LAMBDA_BORD, 2, fixe, poids0)
    od1 = lisser_borne(od, tol, LAMBDA_BORD, 2, fixe, poids0)
    g1 = ax + n1 * og1[:, None] + t1 * np.einsum("ij,ij->i", g - ax, t1)[:, None]
    d1 = ax - n1 * od1[:, None] + t1 * np.einsum("ij,ij->i", d - ax, t1)[:, None]
    g1[fixe], d1[fixe], ax[fixe] = g[fixe], d[fixe], axe[fixe]

    # 3. altitudes sur le profil en travers d'origine (gauche - axe - droite), prolongé linéairement
    lg0, ld0 = np.einsum("ij,ij->i", g - axe, n0), np.einsum("ij,ij->i", d - axe, n0)
    pente_g, pente_d = (zg - za) / np.maximum(lg0, 0.5), (zd - za) / np.minimum(ld0, -0.5)

    def z_sur_profil(q):
        lat = np.einsum("ij,ij->i", q - axe, n0)
        return za + np.where(lat >= 0, pente_g, pente_d) * lat

    za1, zg1, zd1 = z_sur_profil(ax), z_sur_profil(g1), z_sur_profil(d1)
    za1[fixe], zg1[fixe], zd1[fixe] = za[fixe], zg[fixe], zd[fixe]

    # 3 bis. profil en travers : là où l'altitude d'un bord a été lue hors de la chaussée (dans le vide d'un pont, sur
    # un talus), le profil mesuré forme un toit ou un V impossible pour une chaussée. Vu en jeu le 12/11/2026 : arête
    # en travers au km 6,1, marche au km 5,0, plis au km 4,0, parapets ondulés. Une chaussée est un plan incliné
    # (dévers), au plus un toit de 2,5 % : on décompose chaque profil en inclinaison d'ensemble et en toit ; là où le
    # toit sort de l'intervalle admis ou saute d'un mètre au suivant, l'altitude des bords est reconstruite en
    # raccordant inclinaison et toit entre les profils sains voisins. L'axe n'est pas touché, ni les profils sains.
    lg1, ld1 = np.maximum(np.hypot(*(g1 - ax).T), 0.5), np.maximum(np.hypot(*(d1 - ax).T), 0.5)
    dev_g, dev_d = (zg1 - za1) / lg1, (zd1 - za1) / ld1
    incl, toit = (dev_g - dev_d) / 2.0, (dev_g + dev_d) / 2.0
    saut = np.maximum(np.abs(np.r_[0.0, np.diff(dev_g)]), np.abs(np.r_[0.0, np.diff(dev_d)]))
    douteux = (toit < TOIT_ADMIS[0]) | (toit > TOIT_ADMIS[1]) | (saut > SAUT_DEVERS_MAX)
    douteux = np.convolve(douteux.astype(float), np.ones(2 * ELARGIR_PROFIL + 1), "same") > 0
    douteux &= ~fixe
    rang = np.arange(n)
    sains = ~douteux
    incl2, toit2 = np.interp(rang, rang[sains], incl[sains]), np.interp(rang, rang[sains], toit[sains])
    zg2 = np.where(douteux, za1 + (incl2 + toit2) * lg1, zg1)
    zd2 = np.where(douteux, za1 + (-incl2 + toit2) * ld1, zd1)
    i_d = np.flatnonzero(douteux)
    troncons = [(int(t[0]), int(t[-1])) for t in np.split(i_d, np.flatnonzero(np.diff(i_d) > 1) + 1)] if len(i_d) else []
    profil = {"toit_admis_pct": [x * 100 for x in TOIT_ADMIS], "saut_de_devers_max_pct_par_m": SAUT_DEVERS_MAX * 100,
              "metres_repris": int(douteux.sum()),
              "troncons": [{"pk_debut": round(float(pk[i])), "pk_fin": round(float(pk[j])),
                            "correction_max_gauche_m": round(float(np.abs(zg2 - zg1)[i:j + 1].max()), 2),
                            "correction_max_droite_m": round(float(np.abs(zd2 - zd1)[i:j + 1].max()), 2)} for i, j in troncons],
              "devers_extreme_avant_pct": round(float(max(np.abs(dev_g).max(), np.abs(dev_d).max()) * 100), 1),
              "devers_extreme_apres_pct": round(float(max(np.abs((zg2 - za1) / lg1).max(), np.abs((zd2 - za1) / ld1).max()) * 100), 1)}
    zg1, zd1 = zg2, zd2

    # 3 ter. PROFIL EN LONG ET DÉVERS. Essai en jeu du 13/11/2026 au soir (sixième version) : « à certains moments la
    # route est un peu trop bosselée ». Mesuré sur le profil : l'axe porte des bosses et des creux de 2 à 4 cm sur 4 à
    # 8 m (PK 1655, 2600, 3073, 5578...), soit 1 à 2 g à 90 km/h, qu'une chaussée réelle n'a pas : c'est le grain du
    # relevé laser et des raccords entre sources, qu'un simple lissage sur 7 m (étape 07) laissait passer. Le dévers
    # saute aussi par endroits (bout du pont du PK 4470 : de +8 % à -2 % en 4 m, puis retour). Les sections dessinées
    # à la main (approche, Lion d'Or) gardaient en plus des altitudes au centimètre, jamais lissées.
    #   - axe : lissage d'ordre 3 (il pénalise la variation de courbure : une bosse ou un creux réels de plus de
    #     25 m de long le traversent), chaque point restant à moins de TOL_Z_M de l'altitude mesurée ;
    #   - dévers de chaque demi-chaussée : valeurs aberrantes écartées (écart à la médiane sur 21 m), puis lissage
    #     d'ordre 2, chaque point restant à moins de TOL_DEVERS de sa valeur ; les bords sont reposés sur l'axe lissé.
    def mediane_glissante(v, w):
        return np.median(np.lib.stride_tricks.sliding_window_view(np.pad(v, w // 2, mode="edge"), w), axis=1)

    def agitation(z_):                                   # accélération verticale à 90 km/h, en g (écart-type, maximum)
        acc = np.gradient(np.gradient(z_, pk), pk) * 25.0 ** 2 / 9.81
        return round(float(acc.std()), 3), round(float(np.abs(acc).max()), 2), f"maximum au PK {pk[int(np.argmax(np.abs(acc)))]:.0f}"

    def lisser_en_long(y, tol_, lam, ordre):
        # sur une grille régulière d'un mètre : le fichier a un point hors grille (ligne d'arrivée, PK 6735,8), et un
        # lissage fait point par point y créait une marche
        grille = np.arange(pk[0], pk[-1] + 0.5, 1.0)
        yl = lisser_borne(np.interp(grille, pk, y), tol_, lam, ordre, np.zeros(len(grille), bool), np.ones(len(grille)))
        return np.interp(pk, grille, yl)

    def grain(mesure, lisse, plafond):
        """Part du relief mesuré rendue à la valeur lissée. Essai en jeu du 14/11/2026 (septième version) : « n'as-tu pas
        trop lissé la route ? Garder un ressenti réel de route non parfaite, mais enlever les bosses non réelles et trop
        fortes ». Le lissage seul laissait une chaussée parfaite (0,04 g). On lui rend GRAIN_PART de l'écart mesuré
        (ondulations de plus de 6 m de long : en dessous, c'est le bruit du relevé), écrêté en douceur à `plafond` : une
        ondulation d'un centimètre revient à peu près entière, une bosse de 4 cm est ramenée à 1,5 cm."""
        r = lisser_en_long(mesure - lisse, 1.0, LAMBDA_GRAIN, 2)
        return lisse + plafond * np.tanh(GRAIN_PART * r / plafond)

    za_l = lisser_en_long(za1, TOL_Z_M, LAMBDA_Z, 3)
    za_l = grain(za1, za_l, GRAIN_MAX_M)
    sg, sd = (zg1 - za1) / lg1, (zd1 - za1) / ld1
    faux = (np.abs(sg - mediane_glissante(sg, FENETRE_DEVERS)) > ECART_DEVERS) | (np.abs(sd - mediane_glissante(sd, FENETRE_DEVERS)) > ECART_DEVERS)
    faux = np.convolve(faux.astype(float), np.ones(5), "same") > 0
    bons = ~faux
    sg_i, sd_i = np.interp(rang, rang[bons], sg[bons]), np.interp(rang, rang[bons], sd[bons])
    sg_l = grain(sg_i, lisser_en_long(sg_i, TOL_DEVERS, LAMBDA_DEVERS, 2), GRAIN_DEVERS_MAX)
    sd_l = grain(sd_i, lisser_en_long(sd_i, TOL_DEVERS, LAMBDA_DEVERS, 2), GRAIN_DEVERS_MAX)
    zg_l, zd_l = za_l + sg_l * lg1, za_l + sd_l * ld1
    i_f = np.flatnonzero(faux)
    en_long = {"lambda_axe": LAMBDA_Z, "tolerance_axe_m": TOL_Z_M, "lambda_devers": LAMBDA_DEVERS, "tolerance_devers_pct": TOL_DEVERS * 100,
               "deplacement_axe_m": {"moyen": round(float(np.abs(za_l - za1).mean()), 4), "max": round(float(np.abs(za_l - za1).max()), 3)},
               "deplacement_bords_m": {"moyen": round(float(np.r_[np.abs(zg_l - zg1), np.abs(zd_l - zd1)].mean()), 4),
                                       "max": round(float(max(np.abs(zg_l - zg1).max(), np.abs(zd_l - zd1).max())), 3)},
               "acceleration_verticale_a_90_kmh_g": {"axe_avant": agitation(za1), "axe_apres": agitation(za_l),
                                                     "bord_gauche_avant": agitation(zg1), "bord_gauche_apres": agitation(zg_l),
                                                     "bord_droit_avant": agitation(zd1), "bord_droit_apres": agitation(zd_l)},
               "devers_aberrants": {"metres": int(faux.sum()),
                                    "troncons": [[round(float(pk[t[0]])), round(float(pk[t[-1]]))]
                                                 for t in np.split(i_f, np.flatnonzero(np.diff(i_f) > 1) + 1)] if len(i_f) else []}}
    za1, zg1, zd1 = za_l, zg_l, zd_l

    # 4. contrôles
    dep = {"axe": np.hypot(*(ax - axe).T), "gauche": np.hypot(*(g1 - g).T), "droite": np.hypot(*(d1 - d).T)}
    par_source = {}
    for s in sorted(set(src)):
        m = np.array([x == s for x in src])
        par_source[s] = {"points": int(m.sum()), **{k: {"moyen_m": round(float(v[m].mean()), 3), "max_m": round(float(v[m].max()), 3)} for k, v in dep.items()}}

    def cap_stats(p):
        e = np.abs(ecart_de_cap(p))[~fixe[:-1]]
        return {"cassures_sup_5_deg": int((e > 5).sum()), "ecart_type_deg": round(float(e.std()), 2), "max_deg": round(float(e.max()), 2)}

    va, vb = virages(axe), virages(ax)
    k0, cap0 = courbure(axe, 15)
    k1, cap1 = courbure(ax, 15)
    _, capl0 = courbure(axe, 25)
    _, capl1 = courbure(ax, 25)
    echecs, tableau, hors_controle = [], [], 0
    # Enchaînement : tout virage net (moins de 80 m de rayon à l'échelle de 25 m) doit se retrouver de l'autre côté,
    # de même sens, à moins de 10 m. Les courbes très ouvertes, au seuil de détection, ne sont pas comptées : elles
    # apparaissent ou disparaissent pour un écart de courbure infime.
    def tourne_de(c, capl):
        return abs(float(np.degrees(capl[min(n - 1, c[1] + 6)] - capl[max(0, c[0] - 6)])))

    def nets(v, capl):
        # depuis le 13/11/2026 : un virage net tourne aussi la route d'au moins CAP_VIRAGE_FRANC_DEG ; en dessous,
        # c'est une ondulation de l'axe relevé, que le lissage a justement pour but de retirer
        return [c for c in v if c[3] < 80.0 and tourne_de(c, capl) >= CAP_VIRAGE_FRANC_DEG]

    def retrouve(c, autres):
        # même sens, et les deux intervalles se recouvrent à 10 m près : deux virages de même sens qui se rejoignent
        # en un seul, ou l'inverse, ne sont pas un changement d'enchaînement
        return any(s == c[2] and i <= c[1] + 10 and j >= c[0] - 10 for i, j, s, r in autres)

    perdus = [round(float(pk[(c[0] + c[1]) // 2])) for c in nets(va, capl0) if not retrouve(c, vb)]
    nouveaux = [round(float(pk[(c[0] + c[1]) // 2])) for c in nets(vb, capl1) if not retrouve(c, va)]
    if perdus or nouveaux:
        echecs.append(f"enchaînement des virages changé : virages nets perdus aux PK {perdus}, apparus aux PK {nouveaux}")
    for (i0, j0, s0, _) in vb:
        a0, a1 = max(0, i0 - 6), min(n - 1, j0 + 6)
        dcap0, dcap1 = np.degrees(capl0[a1] - capl0[a0]), np.degrees(capl1[a1] - capl1[a0])
        # rayon du cœur du virage : courbure MOYENNE sur les points où elle dépasse 70 % de son maximum (lu sur
        # l'axe régularisé). Une moyenne n'est pas tirée vers le haut par le bruit, contrairement à un maximum.
        coeur = np.where(np.abs(k1[i0:j0 + 1]) >= 0.7 * np.abs(k1[i0:j0 + 1]).max())[0] + i0
        r0, r1 = 1.0 / max(abs(k0[coeur].mean()), 1e-6), 1.0 / max(abs(k1[coeur].mean()), 1e-6)
        artefact = bool(pres[a0:a1 + 1].any())
        tableau.append({"pk": round(float(pk[(i0 + j0) // 2])), "sens": "gauche" if s0 > 0 else "droite", "cap_avant_deg": round(float(dcap0), 1),
                        "cap_apres_deg": round(float(dcap1), 1), "rayon_avant_m": round(float(r0), 1), "rayon_apres_m": round(float(r1), 1),
                        "ecart_rayon_pct": round(float((r1 - r0) / r0 * 100), 1), "pres_d_une_cassure": artefact})
        if abs(dcap1 - dcap0) > ECART_CAP_MAX_DEG and not artefact:
            echecs.append(f"virage du PK {tableau[-1]['pk']} : cap changé de {dcap1 - dcap0:+.1f} deg")
        franc = abs(dcap0) >= CAP_VIRAGE_FRANC_DEG
        tableau[-1]["franc"] = bool(franc)
        if artefact or not franc:
            hors_controle += 1
        elif abs(r1 - r0) / r0 > ECART_RAYON_MAX:
            echecs.append(f"virage du PK {tableau[-1]['pk']} : rayon {r0:.1f} -> {r1:.1f} m")
    for k, v in dep.items():
        marge = 0.02 if k == "axe" else 0.30                 # les bords cumulent le déplacement de l'axe et le leur
        if (v > tol + marge).any():
            echecs.append(f"{k} : déplacement au-delà de la tolérance en {int((v > tol + marge).sum())} points")
    es = np.array([x["zone"] == "es" for x in lignes])
    long0, long1 = float(np.hypot(*np.diff(axe[es], axis=0).T).sum()), float(np.hypot(*np.diff(ax[es], axis=0).T).sum())
    if abs(long1 - long0) > ECART_LONGUEUR_MAX_M:
        echecs.append(f"longueur de l'ES changée de {long1 - long0:+.2f} m")
    largeur1 = np.hypot(*(g1 - d1).T)
    ecarts = [abs(t["ecart_rayon_pct"]) for t in tableau if not t["pres_d_une_cassure"] and t["franc"]]
    bilan = {
        "source": source.name, "points": n, "tolerances_m": TOLERANCE_M, "lambda_axe": LAMBDA_AXE, "lambda_bord": LAMBDA_BORD,
        "cassures_artificielles": [{"pk_debut": round(float(pk[i])), "pk_fin": round(float(pk[j])), "source": src[i]} for i, j in groupes],
        "deplacement_par_source": par_source, "deplacement_max_m": {k: round(float(v.max()), 3) for k, v in dep.items()},
        "cap_avant_hors_manuel": {k: cap_stats(p) for k, p in (("axe", axe), ("gauche", g), ("droite", d))},
        "cap_apres_hors_manuel": {k: cap_stats(p) for k, p in (("axe", ax), ("gauche", g1), ("droite", d1))},
        "virages": {"nombre_avant": len(va), "nombre_apres": len(vb), "nets_avant": len(nets(va, capl0)), "nets_apres": len(nets(vb, capl1)),
                    "controles_sur_le_rayon": len(ecarts), "pres_d_une_cassure": hors_controle,
                    "ecart_de_rayon_median_pct": round(float(np.median(ecarts)), 2) if ecarts else None,
                    "ecart_de_rayon_max_pct": round(float(max(ecarts)), 2) if ecarts else None, "detail": tableau},
        "longueur_es_m": {"avant": round(long0, 2), "apres": round(long1, 2)},
        "largeur_m": {"mediane_avant": round(float(np.median(col("largeur_m"))), 2), "mediane_apres": round(float(np.median(largeur1)), 2),
                      "saut_max_avant": round(float(np.abs(np.diff(col("largeur_m")))[~fixe[:-1]].max()), 2),
                      "saut_max_apres": round(float(np.abs(np.diff(largeur1))[~fixe[:-1]].max()), 2)},
        "profil_en_travers": profil,
        "profil_en_long": en_long,
        "echecs": echecs,
    }
    print(f"{n} points lus dans {source.name} ; {len(groupes)} cassures artificielles :", [(c["pk_debut"], c["pk_fin"]) for c in bilan["cassures_artificielles"]])
    print("déplacement max (m) :", bilan["deplacement_max_m"], "| axe, moyen/max par source :", {s: (v["axe"]["moyen_m"], v["axe"]["max_m"]) for s, v in par_source.items()})
    print("cap avant :", bilan["cap_avant_hors_manuel"]); print("cap après :", bilan["cap_apres_hors_manuel"])
    print("virages :", {k: v for k, v in bilan["virages"].items() if k != "detail"})
    print("  près d'une cassure :", [(t["pk"], t["rayon_avant_m"], t["rayon_apres_m"]) for t in tableau if t["pres_d_une_cassure"]][:12])
    print("longueur ES :", bilan["longueur_es_m"], "| largeur :", bilan["largeur_m"])
    print(f"profil en travers : {profil['metres_repris']} m repris en {len(profil['troncons'])} tronçons ; dévers extrême "
          f"{profil['devers_extreme_avant_pct']} % -> {profil['devers_extreme_apres_pct']} %")
    print("  ", [(t["pk_debut"], t["pk_fin"], max(t["correction_max_gauche_m"], t["correction_max_droite_m"])) for t in profil["troncons"]])
    print(f"profil en long : axe déplacé de {en_long['deplacement_axe_m']['moyen'] * 100:.1f} cm en moyenne, {en_long['deplacement_axe_m']['max'] * 100:.1f} cm au plus ; "
          f"bords {en_long['deplacement_bords_m']['max'] * 100:.1f} cm au plus ; dévers aberrants sur {en_long['devers_aberrants']['metres']} m "
          f"{en_long['devers_aberrants']['troncons'][:14]}")
    print("  accélération verticale à 90 km/h, en g (écart-type, maximum) :", en_long["acceleration_verticale_a_90_kmh_g"])
    print("CONTRÔLES :", "tous passés" if not echecs else echecs[:10])
    if a.essai:
        return
    (RACINE / "data" / "processed" / "regularisation_chaussee.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if echecs:
        raise SystemExit("contrôles en échec : chaussee_precise.csv n'est pas modifié")
    if a.neuf or not BRUT.exists():
        shutil.copyfile(SORTIE, BRUT)
    # Décimales écrites : fixées ici. Jusqu'au 13/11/2026 elles étaient lues sur la première ligne du fichier, dont
    # l'abscisse finissait par hasard à une décimale : tout l'axe était écrit au décimètre, d'où une ligne centrale en
    # dents de scie de 5 cm (vu en jeu).
    deci = {k: 3 if k[:2] in ("x_", "y_", "z_") else 2 if k == "largeur_m" else 1 for k in champs}
    brut_dev = np.where(np.abs(zd - zg) > 1e-3, (zd - zg) / np.maximum(col("largeur_m"), 0.1) * 100, np.nan)
    signe = np.sign(np.nanmedian(col("devers_pct") / brut_dev))
    for i, x in enumerate(lignes):
        if fixe[i]:                # section dessinée à la main : le tracé ne bouge pas, mais ses altitudes sont lissées
            nv = {"z_axe": za1[i], "z_gauche": zg1[i], "z_droite": zd1[i],
                  "devers_pct": signe * (zd1[i] - zg1[i]) / max(largeur1[i], 0.1) * 100}
        else:
            nv = {"x_axe": ax[i, 0], "y_axe": ax[i, 1], "z_axe": za1[i], "x_gauche": g1[i, 0], "y_gauche": g1[i, 1], "z_gauche": zg1[i],
                  "x_droite": d1[i, 0], "y_droite": d1[i, 1], "z_droite": zd1[i], "largeur_m": largeur1[i],
                  "devers_pct": signe * (zd1[i] - zg1[i]) / max(largeur1[i], 0.1) * 100}
        for k, v in nv.items():
            x[k] = f"{v:.{deci[k]}f}"
    with open(SORTIE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=champs, lineterminator="\n")
        w.writeheader()
        w.writerows(lignes)
    print(f"écrit : {SORTIE.relative_to(RACINE).as_posix()} (origine gardée dans {BRUT.name})")


if __name__ == "__main__":
    main()
