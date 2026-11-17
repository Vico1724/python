"""Diagnostic de régularité du tracé : mesure, sur l'axe et les bords de data/processed/chaussee_precise.csv, les
petites irrégularités qui ne peuvent pas être celles d'une route réelle, et les localise.

Une route est dessinée par des droites, des arcs et des raccordements progressifs : sa courbure varie lentement. Le
bruit de mesure (LiDAR sous les arbres, bords pris sur une rupture de terrain, interpolations) se voit au contraire
comme des zigzags de courte longueur d'onde : la courbure change de signe plusieurs fois sur quelques dizaines de
mètres, sans que le cap général change. Ce script ne modifie rien.

Mesures, par fenêtre glissante de 50 m :
  - ondulation : écart latéral (m) entre l'axe et sa version lissée sur LONGUEUR_LISSAGE_M ; écart-type et maximum ;
  - alternances : nombre de changements de signe de la courbure, hors des passages où elle est presque nulle ;
  - largeur : écart-type de la largeur, et saut maximal d'un mètre au suivant.
Sorties : data/processed/diagnostic_trace.json (bilan et zones classées) et figures/phase6/diagnostic_trace.png.

Usage : python scripts/17_diagnostic_trace.py [--csv autre.csv] [--sans-figure]
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.signal import savgol_filter

RACINE = Path(__file__).resolve().parents[1]
LONGUEUR_LISSAGE_M = 31          # fenêtre de référence : plus courte que le plus petit virage réel (épingle : ~40 m d'arc)
FENETRE_M = 50
SEUIL_COURBURE = 1.0 / 400.0     # sous R = 400 m, un changement de signe n'est pas compté (droite)


def charger(chemin):
    with open(chemin, encoding="utf-8") as f:
        r = list(csv.DictReader(f))
    col = lambda k: np.array([float(x[k]) for x in r])
    return {"pk": col("pk_m"), "axe": np.c_[col("x_axe"), col("y_axe")], "g": np.c_[col("x_gauche"), col("y_gauche")],
            "d": np.c_[col("x_droite"), col("y_droite")], "largeur": col("largeur_m"), "source": [x["source"] for x in r],
            "zone": [x["zone"] for x in r]}


def courbure(p, lissage=9):
    """Courbure signée (1/m, positive à gauche) d'une polyligne au pas d'environ 1 m, cap lissé sur `lissage` points."""
    d = np.gradient(p, axis=0)
    cap = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    cap = savgol_filter(cap, lissage, 2)
    ds = np.hypot(d[:, 0], d[:, 1])
    return np.gradient(cap) / np.maximum(ds, 1e-6), cap


def ecart_lateral(p, ref):
    d = np.gradient(ref, axis=0)
    n = np.c_[-d[:, 1], d[:, 0]] / np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-9)[:, None]
    return np.einsum("ij,ij->i", p - ref, n)


def analyser(c):
    lisse = np.c_[savgol_filter(c["axe"][:, 0], LONGUEUR_LISSAGE_M, 3), savgol_filter(c["axe"][:, 1], LONGUEUR_LISSAGE_M, 3)]
    e = ecart_lateral(c["axe"], lisse)
    k, cap = courbure(c["axe"])
    signe = np.where(np.abs(k) > SEUIL_COURBURE, np.sign(k), 0)
    n = len(e)
    zones = []
    for i in range(0, n - FENETRE_M, FENETRE_M // 2):
        j = i + FENETRE_M
        s = signe[i:j]
        s = s[s != 0]
        alt = int(np.sum(s[1:] != s[:-1])) if len(s) > 1 else 0
        src = c["source"][i:j]
        zones.append({"pk_debut": float(c["pk"][i]), "pk_fin": float(c["pk"][j - 1]),
                      "ondulation_ecart_type_m": round(float(e[i:j].std()), 3), "ondulation_max_m": round(float(np.abs(e[i:j]).max()), 3),
                      "alternances_de_courbure": alt, "rayon_min_m": round(float(1.0 / max(np.abs(k[i:j]).max(), 1e-6)), 1),
                      "changement_de_cap_deg": round(float(np.degrees(cap[j - 1] - cap[i])), 1),
                      "largeur_ecart_type_m": round(float(c["largeur"][i:j].std()), 2),
                      "largeur_saut_max_m": round(float(np.abs(np.diff(c["largeur"][i:j])).max()), 2),
                      "sources": {x: src.count(x) for x in sorted(set(src))}})
    return e, k, zones


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(RACINE / "data" / "processed" / "chaussee_precise.csv"))
    ap.add_argument("--sans-figure", action="store_true")
    ap.add_argument("--sortie", default=str(RACINE / "data" / "processed" / "diagnostic_trace.json"))
    a = ap.parse_args()
    c = charger(a.csv)
    e, k, zones = analyser(c)
    pires = sorted(zones, key=lambda z: -(z["ondulation_ecart_type_m"] * (1 + z["alternances_de_courbure"])))
    par_source = {}
    for s in sorted(set(c["source"])):
        m = np.array([x == s for x in c["source"]])
        par_source[s] = {"points": int(m.sum()), "ondulation_ecart_type_m": round(float(e[m].std()), 3),
                         "ondulation_p95_m": round(float(np.percentile(np.abs(e[m]), 95)), 3)}
    bilan = {"fichier": Path(a.csv).name, "points": len(e), "longueur_lissage_m": LONGUEUR_LISSAGE_M,
             "ondulation_axe": {"ecart_type_m": round(float(e.std()), 3), "p95_m": round(float(np.percentile(np.abs(e), 95)), 3),
                                "max_m": round(float(np.abs(e).max()), 3)},
             "alternances_de_courbure_par_km": round(sum(z["alternances_de_courbure"] for z in zones[::2]) / (len(e) / 1000.0), 1),
             "largeur": {"saut_p95_m": round(float(np.percentile(np.abs(np.diff(c["largeur"])), 95)), 2),
                         "saut_max_m": round(float(np.abs(np.diff(c["largeur"])).max()), 2)},
             "par_source": par_source, "zones_les_plus_irregulieres": pires[:25]}
    Path(a.sortie).write_text(json.dumps(bilan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{bilan['points']} points ; ondulation de l'axe : écart-type {bilan['ondulation_axe']['ecart_type_m']} m, "
          f"p95 {bilan['ondulation_axe']['p95_m']} m, max {bilan['ondulation_axe']['max_m']} m ; "
          f"{bilan['alternances_de_courbure_par_km']} alternances de courbure par km")
    print("par source :", {s: (v["points"], v["ondulation_ecart_type_m"]) for s, v in par_source.items()})
    print("largeur : saut d'un mètre au suivant, p95", bilan["largeur"]["saut_p95_m"], "m, max", bilan["largeur"]["saut_max_m"], "m")
    print("zones les plus irrégulières (PK, ondulation, alternances, rayon min, sources) :")
    for z in pires[:12]:
        print(f"  {z['pk_debut']:6.0f}-{z['pk_fin']:6.0f}  {z['ondulation_ecart_type_m']:.2f} m (max {z['ondulation_max_m']:.2f})  "
              f"{z['alternances_de_courbure']} alt.  R {z['rayon_min_m']:6.1f} m  {z['sources']}")
    if not a.sans_figure:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(3, 1, figsize=(16, 9), sharex=True)
        ax[0].plot(c["pk"], e, lw=0.6); ax[0].set_ylabel("écart latéral à l'axe lissé (m)"); ax[0].axhline(0, color="k", lw=0.3)
        ax[1].plot(c["pk"], k * 1000, lw=0.6); ax[1].set_ylabel("courbure (1/km)"); ax[1].axhline(0, color="k", lw=0.3)
        ax[2].plot(c["pk"], c["largeur"], lw=0.6); ax[2].set_ylabel("largeur (m)"); ax[2].set_xlabel("PK (m)")
        fig.suptitle(f"Régularité du tracé : {Path(a.csv).name}")
        out = RACINE / "figures" / "phase6" / "diagnostic_trace.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=110, bbox_inches="tight")
        print("figure :", out.relative_to(RACINE).as_posix())


if __name__ == "__main__":
    main()
