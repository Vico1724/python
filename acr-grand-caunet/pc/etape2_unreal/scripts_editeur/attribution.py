"""Choix du maillage du jeu et de l'échelle pour chaque arbre, arbuste ou couvre-sol, d'après les dimensions réelles
des maillages relevées dans le jeu (releves/maillages_vegetation.json, écrit par outils/relever_jeu.py).

Pourquoi : les scripts 10 et 16 attribuent à chaque plante un maillage tiré au hasard dans le dossier de son essence,
sans connaître la taille des maillages (le catalogue ne donne que des noms). Or le jeu range dans le même dossier
des arbres de 16 m, des plants de 3 m et des souches : SM_AleppoPine12 mesure 0,25 m, SM_AleppoPine13 0,55 m,
SM_Blackmaple04 0,87 m, SM_Boxthorn04 0,27 m. Et les couvre-sols (GroundCover/BroomCreeper) sont des plaques d'un
mètre de large et de 0,2 à 12 cm d'épaisseur : une échelle calculée sur leur hauteur les grossirait 27 fois.

Règle :
  dossier de plaques (tous les maillages font moins de PLAT_CM de haut) : maillage au hasard, échelle = diamètre voulu
      / largeur du maillage (1 si le diamètre est inconnu) ;
  sinon : on écarte les maillages de moins de HAUT_MIN_CM ; on tire au hasard parmi ceux dont l'échelle hauteur voulue
      / hauteur du maillage est entre ECH_MIN et ECH_MAX ; s'il n'y en a pas, parmi ceux dont l'échelle est à moins
      d'un facteur TOLERANCE de la meilleure.
Le tirage dépend seulement de la clé donnée (nom du groupe et numéro de la plante) : il est reproductible.

Python pur, sans dépendance : utilisable dans l'éditeur Unreal (construire_niveau.py) comme en ligne de commande.
En ligne de commande, écrit le bilan releves/arbres_bilan.json pour arbres.csv et arbustes.csv.gz :
    python pc/etape2_unreal/scripts_editeur/attribution.py
"""
import json
import math
import os
import random
import zlib

PLAT_CM = 30.0
HAUT_MIN_CM = 150.0
ECH_MIN, ECH_MAX = 0.6, 1.5
TOLERANCE = 1.25


def charger(kit):
    """{"/Game/Foliage/Trees/AleppoPine": [{"nom", "haut_cm", "largeur_cm"}, ...]} ou None si le relevé manque."""
    f = os.path.join(kit, "releves", "maillages_vegetation.json")
    if not os.path.exists(f):
        return None
    with open(f, encoding="utf-8") as h:
        d = json.load(h)["dossiers"]
    return {dossier: [{"nom": n, "haut_cm": v[0], "largeur_cm": v[1]} for n, v in sorted(m.items())] for dossier, m in d.items()}


def choisir(maillages, hauteur_m, diametre_m, cle):
    """(nom du maillage, échelle) pour une plante de hauteur et de diamètre voulus, parmi les maillages d'un dossier."""
    rng = random.Random(zlib.crc32(str(cle).encode("utf-8")))
    if max(m["haut_cm"] for m in maillages) < PLAT_CM:                       # plaques de couvre-sol
        m = rng.choice(maillages)
        e = diametre_m * 100.0 / m["largeur_cm"] if diametre_m and m["largeur_cm"] > 1 else 1.0
        return m["nom"], e
    cand = [m for m in maillages if m["haut_cm"] >= HAUT_MIN_CM] or [m for m in maillages if m["haut_cm"] >= PLAT_CM]
    ech = [(hauteur_m * 100.0 / m["haut_cm"], m) for m in cand]
    bons = [x for x in ech if ECH_MIN <= x[0] <= ECH_MAX]
    if not bons:
        meilleur = min(abs(math.log(e)) for e, _ in ech)
        bons = [x for x in ech if abs(math.log(x[0])) <= meilleur + math.log(TOLERANCE)]
    e, m = rng.choice(bons)
    return m["nom"], e


def _bilan():
    import collections
    import csv
    import gzip
    import statistics
    kit = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    racine = os.path.dirname(os.path.dirname(kit))
    veg = charger(kit)
    if veg is None:
        raise SystemExit("releves/maillages_vegetation.json absent : lancer outils/relever_jeu.py")
    natif = {d + "/" + m["nom"]: m for d, ms in veg.items() for m in ms}
    out = {"regle": {"plaque_si_moins_de_cm": PLAT_CM, "hauteur_minimale_cm": HAUT_MIN_CM, "echelle_visee": [ECH_MIN, ECH_MAX],
                     "tolerance": TOLERANCE}}
    sources = (("arbres", open(os.path.join(racine, "data", "processed", "arbres.csv"), encoding="utf-8"), "diametre_houppier_m"),
               ("arbustes", gzip.open(os.path.join(racine, "data", "processed", "arbustes.csv.gz"), "rt", encoding="utf-8"), "diametre_m"))
    for nom, f, col_d in sources:
        par_dossier = collections.defaultdict(lambda: {"avant": [], "apres": [], "maillages": collections.Counter()})
        for i, r in enumerate(csv.DictReader(f)):
            dossier = "/Game/" + r["famille_jeu"]
            h, d = float(r["hauteur_m"]), float(r[col_d]) if r.get(col_d) else None
            b = par_dossier[dossier]
            m0 = natif[dossier + "/" + r["element_jeu_propose"]]
            b["avant"].append(h * 100.0 / m0["haut_cm"] if m0["haut_cm"] >= 1 else float("inf"))
            n, e = choisir(veg[dossier], h, d, f"GC_{nom.capitalize()}_{r['element_jeu_propose']}:{i}")
            b["apres"].append(e)
            b["maillages"][n] += 1
        f.close()

        def resume(v):
            fini = [x for x in v if math.isfinite(x)]
            if not fini:
                return {"sans_objet": "maillage d'origine en plaque : pas d'échelle en hauteur"}
            return {"mediane": round(statistics.median(fini), 2), "min": round(min(fini), 2), "max": round(max(fini), 2),
                    "hors_de_0,5_a_2": sum(1 for x in v if not 0.5 <= x <= 2)}

        out[nom] = {d: {"nombre": len(b["apres"]), "echelle_avant": resume(b["avant"]), "echelle_apres": resume(b["apres"]),
                        "par_maillage": dict(sorted(b["maillages"].items()))} for d, b in sorted(par_dossier.items())}
        tot = sum(len(b["apres"]) for b in par_dossier.values())
        av = sum(1 for b in par_dossier.values() for x in b["avant"] if not 0.5 <= x <= 2)
        ap = sum(1 for b in par_dossier.values() for x in b["apres"] if not 0.5 <= x <= 2)
        print(f"{nom} : {tot} ; échelle hors de 0,5 à 2 : {av} avant, {ap} après")
        for d, b in sorted(par_dossier.items()):
            e = sorted(b["apres"])
            print(f"    {d.rsplit('/', 1)[1]:22} {len(e):6d}  échelle {e[0]:.2f} / {e[len(e) // 2]:.2f} / {e[-1]:.2f}  sur {len(b['maillages'])} maillages")
    with open(os.path.join(kit, "releves", "arbres_bilan.json"), "w", encoding="utf-8") as h:
        json.dump(out, h, ensure_ascii=False, indent=1)
        h.write("\n")


if __name__ == "__main__":
    _bilan()
