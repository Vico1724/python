"""Réattribue à chaque arbre de data/processed/arbres.csv un maillage du jeu de la BONNE TAILLE, et calcule son échelle.

Pourquoi : scripts/10_semis_arbres.py a choisi le maillage au hasard dans la famille de l'essence, sans connaître la
hauteur des maillages (le catalogue ne donne que des noms). Les hauteurs réelles, relevées sur le PC le 11/11/2026
(releves/maillages_arbres.json), montrent que certains « arbres » du jeu sont des souches ou des jeunes plants :
SM_AleppoPine12 mesure 0,25 m, SM_AleppoPine13 0,55 m, SM_Blackmaple04 0,87 m. 3 468 de nos arbres les désignaient,
avec une échelle allant jusqu'à 97 ; 48 % des arbres avaient une échelle hors de 0,5 à 2.

Règle : dans la famille de l'arbre (colonne famille_jeu, inchangée), on garde les maillages d'au moins HAUT_MIN m, et
on tire au hasard (graine fixe) parmi ceux dont l'échelle hauteur mesurée / hauteur du maillage reste entre ECH_MIN et
ECH_MAX ; s'il n'y en a aucun, on prend le maillage d'échelle la plus proche de 1. L'échelle est écrite telle quelle :
c'est poser_arbres.py qui l'applique.

EXÉCUTÉ sur le PC le 11/11/2026. Python ordinaire, sans dépendance.
Usage : python pc/etape2_unreal/outils/reattribuer_arbres.py
Écrit : pc/etape2_unreal/arbres_jeu.csv.gz (colonnes de arbres.csv + element_jeu, echelle), lu par poser_arbres.py et
        liste_factices.py à la place de arbres.csv quand il existe ; et un bilan dans releves/arbres_bilan.json.
"""
import collections
import csv
import gzip
import json
import math
import random
import statistics
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
RACINE = Path(__file__).resolve().parents[3]
HAUT_MIN = 1.5            # m : en dessous, ce n'est pas un arbre (souche, plant)
ECH_MIN, ECH_MAX = 0.6, 1.5


def main():
    m = json.loads((KIT / "releves" / "maillages_arbres.json").read_text(encoding="utf-8"))["maillages"]
    familles = collections.defaultdict(list)                       # "Foliage/Trees/AleppoPine" -> [(nom, hauteur m)]
    for nom, d in m.items():
        fam = d["objet"][len("/Game/"):].rsplit("/", 1)[0]
        if d["haut_cm"] >= HAUT_MIN * 100:
            familles[fam].append((nom, d["haut_cm"] / 100))
    rng = random.Random(20261111)
    lignes = list(csv.DictReader(open(RACINE / "data" / "processed" / "arbres.csv", encoding="utf-8")))
    avant, apres, repli, usage = [], [], 0, collections.Counter()
    for r in lignes:
        h = float(r["hauteur_m"])
        avant.append(h * 100 / m[r["element_jeu_propose"]]["haut_cm"])
        cand = familles[r["famille_jeu"]]
        if not cand:
            raise SystemExit(f"aucun maillage d'au moins {HAUT_MIN} m dans {r['famille_jeu']}")
        bons = [(n, hm) for n, hm in cand if ECH_MIN <= h / hm <= ECH_MAX]
        if bons:
            n, hm = rng.choice(bons)
        else:
            repli += 1
            n, hm = min(cand, key=lambda c: abs(math.log(h / c[1])))
        r["element_jeu"] = n
        r["echelle"] = f"{h / hm:.3f}"
        apres.append(h / hm)
        usage[n] += 1
    sortie = KIT / "arbres_jeu.csv.gz"
    with gzip.open(sortie, "wt", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)

    def bilan(e):
        return {"mediane": round(statistics.median(e), 2), "min": round(min(e), 2), "max": round(max(e), 2),
                "hors_de_0,5_a_2": sum(1 for x in e if x < 0.5 or x > 2), "hors_de_0,6_a_1,5": sum(1 for x in e if x < ECH_MIN or x > ECH_MAX)}

    b = {"arbres": len(lignes), "regle": {"hauteur_minimale_du_maillage_m": HAUT_MIN, "echelle_visee": [ECH_MIN, ECH_MAX]},
         "echelle_avant": bilan(avant), "echelle_apres": bilan(apres), "arbres_sans_maillage_dans_la_plage": repli,
         "maillages_ecartes": sorted(n for n, d in m.items() if d["haut_cm"] < HAUT_MIN * 100),
         "arbres_par_maillage": dict(sorted(usage.items()))}
    (KIT / "releves" / "arbres_bilan.json").write_text(json.dumps(b, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(lignes)} arbres -> {sortie.relative_to(RACINE).as_posix()} ({sortie.stat().st_size // 1024} Ko), {len(usage)} maillages")
    print("échelle avant :", b["echelle_avant"])
    print("échelle après :", b["echelle_apres"], "; hors plage (maillage le plus proche pris) :", repli)


if __name__ == "__main__":
    main()
