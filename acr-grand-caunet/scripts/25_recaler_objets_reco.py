"""Recale sur leur PK réel les objets relevés sur la vidéo de reconnaissance, ou posés par rapport à eux.

Constat du 13/11/2026 (docs/14, section 6) : le calage de la reconnaissance est en avance de 0 à 24 m selon l'endroit
(vingt repères connus par ailleurs : data/reference/calage_reco_reperes.json, scripts/calage_reco.py). Les parois
rocheuses ont été corrigées à leur relecture ; le reste du relevé (glissières, murets et parapets hors pont, poteaux,
panneaux, rochers, lisses, aires et pistes) était resté au PK lu sur la vidéo. Les objets du rallye relevés sur la
vidéo de course ont été posés par rapport à ces repères fixes : ils portent le même écart et bougent avec eux.

Ce script réécrit les PK dans les fichiers de référence, une seule fois par objet :
  - chaque PK devient calage_reco.corrige(PK), arrondi au demi-mètre ;
  - la valeur lue sur la vidéo est gardée à côté (pk_releve_m, pk_releve_debut_m, pk_releve_fin_m, points_releves) ;
  - l'objet reçoit un champ « calage » qui dit ce qui a été fait, et qui empêche de le corriger deux fois.

Laissés en place :
  - le carrefour du Lion d'Or (PK 3600 à 3712) : ses objets sont posés d'après le plan du carrefour, repris à part ;
  - les objets déjà déplacés à la main sur un repère (ponceau du PK 3472, piste du PK 3005) ;
  - les parapets des ponts (liste « ouvrages »), rattachés aux tabliers du relevé laser.

Usage : python scripts/25_recaler_objets_reco.py [--essai]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calage_reco  # noqa: E402

REF = Path(__file__).resolve().parents[1] / "data" / "reference"
CARREFOUR = (3600.0, 3712.0)
DEJA = ("déplacé le 13/11/2026", "glissée de")


def neuf(pk):
    return round(float(calage_reco.corrige(pk)) * 2) / 2


def sens(d):
    return f"{d:+.1f} m".replace(".", ",")


def traiter(e, cles, bilan, texte=None):
    """cles : [(clé du PK, clé où garder la valeur lue)]. Renvoie le plus grand déplacement, en mètres."""
    if "calage" in e:
        bilan["déjà faits"] += 1
        return 0.0
    pks = [e[k] for k, _ in cles]
    milieu = (min(pks) + max(pks)) / 2
    texte = json.dumps(e, ensure_ascii=False) if texte is None else texte
    if any(m in texte for m in DEJA):
        e["calage"] = "laissé en place : déjà déplacé à la main sur un repère connu"
        bilan["déjà déplacés à la main"] += 1
        return 0.0
    if CARREFOUR[0] <= milieu <= CARREFOUR[1]:
        e["calage"] = "laissé en place : carrefour du Lion d'Or, posé d'après le plan du carrefour"
        bilan["carrefour"] += 1
        return 0.0
    d = [neuf(p) - p for p in pks]
    if max(abs(x) for x in d) < 0.25:
        e["calage"] = "vérifié le 13/11/2026 : écart nul à cet endroit"
        bilan["écart nul"] += 1
        return 0.0
    for (k, garde), p, x in zip(cles, pks, d):
        e[garde] = p
        e[k] = p + x
    e["calage"] = (f"PK corrigé de {sens(d[0])}" + (f" à {sens(d[-1])}" if len(d) > 1 and abs(d[-1] - d[0]) >= 0.5 else "")
                   + " le 13/11/2026 (scripts/calage_reco.py) ; valeur lue sur la vidéo gardée à côté")
    bilan["corrigés"] += 1
    return max(abs(x) for x in d)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--essai", action="store_true", help="compte sans écrire")
    a = ap.parse_args()
    PLAGE = [("pk_debut_m", "pk_releve_debut_m"), ("pk_fin_m", "pk_releve_fin_m")]
    POINT = [("pk_m", "pk_releve_m")]
    total = {}

    def fichier(nom, travail):
        f = REF / nom
        o = json.loads(f.read_text(encoding="utf-8"))
        bilan = {k: 0 for k in ("corrigés", "écart nul", "carrefour", "déjà déplacés à la main", "déjà faits")}
        plus = travail(o, bilan)
        total[nom] = bilan
        print(f"{nom} : " + ", ".join(f"{v} {k}" for k, v in bilan.items() if v) + f" ; plus grand déplacement {plus:.1f} m")
        if not a.essai:
            f.write_text(json.dumps(o, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def parapets(o, b):
        return max([traiter(e, PLAGE, b) for e in o["parapets_hors_tablier"]] + [0.0])

    def glissieres(o, b):
        return max([traiter(e, PLAGE, b) for e in o["troncons"]] + [0.0])

    def aires(o, b):
        return max([traiter(e, PLAGE, b) for e in o["emprises"]] + [0.0])

    def mobilier(o, b):
        m = [0.0]
        for ligne in o["lignes_electriques"]:
            m += [traiter(p, POINT, b, texte="") for p in ligne["poteaux"]]
        m += [traiter(e, POINT, b) for e in o["objets"]]
        m += [traiter(e, PLAGE, b) for e in o["rochers"] + o["lisses"]]
        for e in o["rubalises"]:
            if "calage" in e:
                b["déjà faits"] += 1
                continue
            pks = [p[0] for p in e["points"]]
            if CARREFOUR[0] <= (min(pks) + max(pks)) / 2 <= CARREFOUR[1]:
                e["calage"] = "laissé en place : carrefour du Lion d'Or, posé d'après le plan du carrefour"
                b["carrefour"] += 1
                continue
            d = [neuf(p) - p for p in pks]
            if max(abs(x) for x in d) < 0.25:
                e["calage"] = "vérifié le 13/11/2026 : écart nul à cet endroit"
                b["écart nul"] += 1
                continue
            e["points_releves"] = [list(p) for p in e["points"]]
            e["points"] = [[p[0] + x] + list(p[1:]) for p, x in zip(e["points"], d)]
            e["calage"] = f"PK corrigés de {sens(d[0])} le 13/11/2026 (scripts/calage_reco.py) ; points lus gardés à côté"
            b["corrigés"] += 1
            m.append(max(abs(x) for x in d))
        return max(m)

    fichier("ouvrages_parapets.json", parapets)
    fichier("glissieres.json", glissieres)
    fichier("aires_et_pistes.json", aires)
    fichier("mobilier_bord_de_route.json", mobilier)
    print("essai : rien n'est écrit" if a.essai else "écrit")


if __name__ == "__main__":
    main()
