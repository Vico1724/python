"""Régularise l'axe et les bords de la chaussée (data/processed/chaussee_precise.csv) : retire les petites
irrégularités dues aux mesures et aux coutures entre sources, SANS changer la forme de la route.

Ce que le diagnostic (scripts/17_diagnostic_trace.py) a montré le 12/11/2026 :
  - le cap de l'axe oscille d'environ 1 degré en permanence, celui des bords de 1,8 degré ;
  - des cassures de 5 à 24 degrés se trouvent aux limites des sections dont la largeur a été corrigée d'après les
    vidéos : la correction y commence et s'y arrête d'un mètre au suivant, ce qui décroche le bord et l'axe ;
  - les sections dessinées à la main (approche, carrefour du Lion d'Or) ont aussi des cassures, mais voulues.

Principe (rien n'est redessiné, tout part des points mesurés) :
  1. AXE. Lissage de Whittaker d'ordre 3 sur x(s) et y(s) : il pénalise la VARIATION de courbure, pas la courbure.
     Un arc de cercle ou une droite le traversent donc presque inchangés ; ce sont les zigzags qui sont retirés.
     Chaque point a une tolérance de déplacement selon sa source (TOLERANCE_M) ; tant qu'un point la dépasse, son
     poids est augmenté et le lissage refait. Les points « manuel » sont tenus fixes.
  2. BORDS. Les demi-largeurs gauche et droite, mesurées perpendiculairement à l'axe régularisé, sont lissées à
     l'ordre 2 : un changement de largeur réel reste, un saut d'un mètre au suivant devient un raccord progressif.
     Mêmes tolérances, mêmes points fixes.
  3. ALTITUDES. Chaque point déplacé garde l'altitude du profil en travers mesuré (interpolation ou prolongement
     linéaire le long de la section gauche - axe - droite).
  4. CONTRÔLES, écrits dans data/processed/regularisation_chaussee.json : déplacements par source, cassures avant et
     après, rayon minimal de chaque virage avant et après (écart toléré : ECART_RAYON_MAX), longueur de l'ES.
     Si un contrôle échoue, le fichier n'est PAS remplacé.

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
from scipy.sparse.linalg import spsolve

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "data" / "processed" / "chaussee_precise.csv"
BRUT = RACINE / "data" / "processed" / "chaussee_precise_brut.csv"

# déplacement latéral maximal admis, en mètres, selon la source de la mesure
TOLERANCE_M = {"lidar+ortho": 0.20, "lidar": 0.25, "ortho": 0.40, "video": 0.50, "interpole": 0.50, "manuel": 0.0}
LAMBDA_AXE = 150.0        # lissage d'ordre 3 de l'axe (pas d'environ 1 m) : coupe sous 14 m de longueur d'onde environ
                          # (2 pi lambda^(1/6)) ; 3e4 coupait sous 35 m et aplatissait les virages : refusé par les contrôles
LAMBDA_BORD = 60.0        # lissage d'ordre 2 des demi-largeurs : raccord d'une dizaine de mètres
ECART_RAYON_MAX = 0.05    # un virage ne doit pas voir son rayon minimal changer de plus de 5 %
FENETRE_RAYON_M = 15      # le rayon d'un virage est mesuré sur un cap lissé à cette échelle


def whittaker(y, poids, lam, ordre):
    n = len(y)
    d = sparse.eye(n, format="csc")
    for _ in range(ordre):
        d = d[1:] - d[:-1]
    w = sparse.diags(poids)
    return spsolve((w + lam * (d.T @ d)).tocsc(), poids * y)


def lisser_borne(y, tol, lam, ordre, fixe, tours=40):
    """Lissage de Whittaker dont aucun point ne s'écarte de sa valeur de plus de tol ; les points fixes ne bougent pas."""
    poids = np.where(fixe, 1.0e6, 1.0)
    z = y
    for _ in range(tours):
        z = whittaker(y, poids, lam, ordre)
        trop = (np.abs(z - y) > tol) & ~fixe
        if not trop.any():
            break
        poids[trop] *= 3.0
    return np.where(fixe, y, z)


def normales(p):
    d = np.gradient(p, axis=0)
    t = d / np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-9)[:, None]
    return t, np.c_[-t[:, 1], t[:, 0]]                       # tangente, normale à gauche


def cap_lisse(p, fenetre):
    from scipy.signal import savgol_filter
    d = np.gradient(p, axis=0)
    return savgol_filter(np.unwrap(np.arctan2(d[:, 1], d[:, 0])), fenetre | 1, 2), np.hypot(d[:, 0], d[:, 1])


def virages(p):
    """Structure du tracé : [(i0, i1, sens)], un virage = un passage continu sous 120 m de rayon, le cap étant lissé
    sur FENETRE_RAYON_M ; seule la partie centrale (courbure au-dessus de 70 % du maximum) est rendue."""
    cap, ds = cap_lisse(p, FENETRE_RAYON_M)
    k = np.gradient(cap) / np.maximum(ds, 1e-6)
    dans = np.abs(k) > 1.0 / 120.0
    out, i = [], 0
    while i < len(k):
        if dans[i]:
            j = i
            while j + 1 < len(k) and dans[j + 1] and np.sign(k[j + 1]) == np.sign(k[i]):
                j += 1
            if j - i >= 10:
                fort = np.where(np.abs(k[i:j + 1]) >= 0.7 * np.abs(k[i:j + 1]).max())[0]
                if fort[-1] - fort[0] >= 6:
                    out.append((i + int(fort[0]), i + int(fort[-1]), "gauche" if k[i] > 0 else "droite"))
            i = j + 1
        else:
            i += 1
    return out


def rayon_ajuste(p):
    """Rayon du cercle ajusté aux points (moindres carrés) : insensible au bruit point à point."""
    q = p - p.mean(axis=0)
    a = np.c_[q, np.ones(len(q))]
    s, *_ = np.linalg.lstsq(a, -(q ** 2).sum(axis=1), rcond=None)
    return float(np.sqrt(max(s[0] ** 2 / 4 + s[1] ** 2 / 4 - s[2], 1e-6)))


def cassures(p, seuil_deg):
    from scipy.signal import savgol_filter
    d = np.diff(p, axis=0)
    cap = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    e = np.degrees(cap - savgol_filter(cap, 21, 2))
    return int((np.abs(e) > seuil_deg).sum()), float(np.abs(e).std()), float(np.abs(e).max())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--essai", action="store_true")
    a = ap.parse_args()
    source = BRUT if BRUT.exists() else SORTIE
    with open(source, encoding="utf-8") as f:
        lignes = list(csv.DictReader(f))
        champs = list(lignes[0].keys())
    col = lambda k: np.array([float(x[k]) for x in lignes])
    pk = col("pk_m")
    axe, g, d = np.c_[col("x_axe"), col("y_axe")], np.c_[col("x_gauche"), col("y_gauche")], np.c_[col("x_droite"), col("y_droite")]
    za, zg, zd = col("z_axe"), col("z_gauche"), col("z_droite")
    src = [x["source"] for x in lignes]
    tol = np.array([TOLERANCE_M.get(s, 0.25) for s in src])
    fixe = np.array([s == "manuel" for s in src])
    # les points fixes tiennent aussi leurs voisins immédiats, pour que le raccord se fasse hors de la section manuelle
    fixe_large = fixe.copy()

    # 1. axe
    ax = np.c_[lisser_borne(axe[:, 0], tol / np.sqrt(2), LAMBDA_AXE, 3, fixe_large), lisser_borne(axe[:, 1], tol / np.sqrt(2), LAMBDA_AXE, 3, fixe_large)]
    t0, n0 = normales(axe)
    t1, n1 = normales(ax)
    dep_axe = np.einsum("ij,ij->i", ax - axe, n0)                                 # déplacement latéral de l'axe, + à gauche

    # 2. demi-largeurs, mesurées sur la normale de l'axe régularisé
    og = np.einsum("ij,ij->i", g - ax, n1)
    od = -np.einsum("ij,ij->i", d - ax, n1)
    og1 = lisser_borne(og, tol, LAMBDA_BORD, 2, fixe)
    od1 = lisser_borne(od, tol, LAMBDA_BORD, 2, fixe)
    # la composante le long de l'axe des bords d'origine est gardée telle quelle (sections pas tout à fait perpendiculaires)
    lg = np.einsum("ij,ij->i", g - ax, t1)
    ld = np.einsum("ij,ij->i", d - ax, t1)
    g1 = ax + n1 * og1[:, None] + t1 * lg[:, None]
    d1 = ax - n1 * od1[:, None] + t1 * ld[:, None]
    g1[fixe], d1[fixe], ax[fixe] = g[fixe], d[fixe], axe[fixe]

    # 3. altitudes le long du profil en travers d'origine
    def z_sur_profil(lat):
        """Altitude à la distance latérale lat de l'axe d'origine (+ à gauche), sur le profil gauche - axe - droite."""
        lg0 = np.einsum("ij,ij->i", g - axe, n0)
        ld0 = np.einsum("ij,ij->i", d - axe, n0)                                  # négatif
        pente_g = (zg - za) / np.maximum(lg0, 0.5)
        pente_d = (zd - za) / np.minimum(ld0, -0.5)
        return za + np.where(lat >= 0, pente_g, pente_d) * lat

    za1 = z_sur_profil(dep_axe)
    zg1 = z_sur_profil(np.einsum("ij,ij->i", g1 - axe, n0))
    zd1 = z_sur_profil(np.einsum("ij,ij->i", d1 - axe, n0))
    za1[fixe], zg1[fixe], zd1[fixe] = za[fixe], zg[fixe], zd[fixe]

    # 4. contrôles
    dep = {"axe": np.hypot(*(ax - axe).T), "gauche": np.hypot(*(g1 - g).T), "droite": np.hypot(*(d1 - d).T)}
    par_source = {}
    for s in sorted(set(src)):
        m = np.array([x == s for x in src])
        par_source[s] = {"points": int(m.sum()), **{k: {"moyen_m": round(float(v[m].mean()), 3), "max_m": round(float(v[m].max()), 3)} for k, v in dep.items()}}
    # virages : la structure est lue sur l'axe régularisé, puis le MÊME intervalle de points sert à ajuster un cercle
    # sur l'axe d'origine et sur l'axe régularisé ; l'écart de rayon mesure donc ce que la régularisation a changé
    vb = virages(ax)
    va = virages(axe)
    appar = []
    for i0, i1, s in vb:
        r0, r1 = rayon_ajuste(axe[i0:i1 + 1]), rayon_ajuste(ax[i0:i1 + 1])
        appar.append((float(pk[(i0 + i1) // 2]), r0, r1, (r1 - r0) / r0))
    pires = sorted(appar, key=lambda x: -abs(x[3]))[:8]
    es = (pk >= 0) & (pk <= pk[np.array([x["zone"] == "es" for x in lignes])].max())
    long0 = float(np.hypot(*np.diff(axe[es], axis=0).T).sum())
    long1 = float(np.hypot(*np.diff(ax[es], axis=0).T).sum())
    largeur1 = np.hypot(*(g1 - d1).T)
    bilan = {
        "source": source.name, "points": len(pk), "tolerances_m": TOLERANCE_M, "lambda_axe": LAMBDA_AXE, "lambda_bord": LAMBDA_BORD,
        "deplacement_par_source": par_source,
        "deplacement_max_m": {k: round(float(v.max()), 3) for k, v in dep.items()},
        "cap_avant": {k: dict(zip(("cassures_sup_5_deg", "ecart_type_deg", "max_deg"), [round(x, 2) for x in cassures(p, 5)])) for k, p in (("axe", axe), ("gauche", g), ("droite", d))},
        "cap_apres": {k: dict(zip(("cassures_sup_5_deg", "ecart_type_deg", "max_deg"), [round(x, 2) for x in cassures(p, 5)])) for k, p in (("axe", ax), ("gauche", g1), ("droite", d1))},
        "virages": {"avant": len(va), "apres": len(vb), "apparies": len(appar),
                    "ecart_de_rayon_median_pct": round(float(np.median([abs(x[3]) for x in appar]) * 100), 2),
                    "ecart_de_rayon_max_pct": round(float(max(abs(x[3]) for x in appar) * 100), 2),
                    "les_plus_modifies": [{"pk": round(p), "rayon_avant_m": round(r0, 1), "rayon_apres_m": round(r1, 1), "ecart_pct": round(e * 100, 1)} for p, r0, r1, e in pires]},
        "longueur_es_m": {"avant": round(long0, 2), "apres": round(long1, 2)},
        "largeur_m": {"mediane_avant": round(float(np.median(col("largeur_m"))), 2), "mediane_apres": round(float(np.median(largeur1)), 2),
                      "saut_max_avant": round(float(np.abs(np.diff(col("largeur_m"))).max()), 2), "saut_max_apres": round(float(np.abs(np.diff(largeur1)).max()), 2)},
    }
    echecs = []
    for k, v in dep.items():
        if (v > tol + (0.02 if k == "axe" else 0.30)).any():      # les bords cumulent le déplacement de l'axe et le leur
            echecs.append(f"{k} : déplacement au-delà de la tolérance en {int((v > tol + (0.02 if k == 'axe' else 0.30)).sum())} points")
    if bilan["virages"]["ecart_de_rayon_max_pct"] > ECART_RAYON_MAX * 100:
        echecs.append(f"rayon d'un virage modifié de {bilan['virages']['ecart_de_rayon_max_pct']} % (> {ECART_RAYON_MAX * 100:.0f} %)")
    sens_avant = [s for _, _, s in virages(np.c_[whittaker(axe[:, 0], np.ones(len(pk)), 30.0, 3), whittaker(axe[:, 1], np.ones(len(pk)), 30.0, 3)])]
    if [s for _, _, s in vb] != sens_avant:
        echecs.append(f"enchaînement des virages changé : {len(sens_avant)} virages avant, {len(vb)} après, ou sens différent")
    if abs(long1 - long0) > 1.0:
        echecs.append(f"longueur de l'ES changée de {long1 - long0:+.2f} m")
    bilan["echecs"] = echecs
    print(f"{len(pk)} points lus dans {source.name}")
    print("déplacement max (m) :", bilan["deplacement_max_m"], "| par source (axe moyen/max) :", {s: (v["axe"]["moyen_m"], v["axe"]["max_m"]) for s, v in par_source.items()})
    print("cap avant :", bilan["cap_avant"]); print("cap après :", bilan["cap_apres"])
    print("virages :", {k: v for k, v in bilan["virages"].items() if k != "les_plus_modifies"}); print("  les plus modifiés :", bilan["virages"]["les_plus_modifies"][:4])
    print("longueur ES :", bilan["longueur_es_m"], "| largeur :", bilan["largeur_m"])
    print("CONTRÔLES :", "tous passés" if not echecs else echecs)
    if a.essai:
        return
    (RACINE / "data" / "processed" / "regularisation_chaussee.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if echecs:
        raise SystemExit("contrôles en échec : chaussee_precise.csv n'est pas modifié")
    if not BRUT.exists():
        shutil.copyfile(SORTIE, BRUT)
    deci = {k: len(lignes[0][k].split(".")[1]) if "." in lignes[0][k] else 0 for k in champs}
    signe = np.sign(np.nanmedian(col("devers_pct") / np.where(np.abs(zd - zg) > 1e-3, (zd - zg) / np.maximum(col("largeur_m"), 0.1) * 100, np.nan)))
    for i, x in enumerate(lignes):
        if fixe[i]:
            continue
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
