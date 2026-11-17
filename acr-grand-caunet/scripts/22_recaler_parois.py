"""Recale le long de la route les parois rocheuses relevées sur la vidéo, d'après le relief du relevé laser.

Le relevé de la reconnaissance donne chaque paroi à ±10 m, et parfois plus tôt qu'elle n'est : une paroi aperçue devant la
voiture a été notée au PK de l'image. Constat du 13/11/2026 (aperçu hors jeu, scripts/21_apercu_conducteur.py) : la paroi
de 3 à 4 m relevée du PK 3455 au PK 3495 tombait sur un sol plat, le talus ne montant qu'à partir du PK 3478 ; même chose
pour le nez rocheux du PK 2920. Une paroi ne peut pas se dresser là où le terrain ne monte pas : le relief laser fait foi.

Pour chaque paroi, la « note » est la part de sa hauteur relevée que le terrain atteint dans les 4 m qui suivent le bord
de chaussée, en moyenne sur sa longueur. Une paroi mal notée sur place est glissée le long de la route (±30 m au plus),
là où sa note est la meilleure, si le gain est net et sans mordre sur ses voisines. Une paroi très mal notée sur place
(relevé manifestement trop tôt) est en outre allongée tant que le talus continue, jusqu'à doubler sa longueur.

Écrit dans data/reference/parois_rocheuses.json, pour chaque paroi déplacée : recalage_pk_m, allonge_m, note_recalage.
Les PK relevés ne sont pas modifiés. Usage : python scripts/22_recaler_parois.py [--essai]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
FICHIER = RACINE / "data" / "reference" / "parois_rocheuses.json"
REGLE = {"pas_m": 2.0, "au_bord_m": (1.0, 2.0, 3.0, 4.0), "glissement_max_m": 30, "cout_par_m": 0.004, "note_suffisante": 0.9,
         "gain_min": 0.1, "note_tres_basse": 0.5, "part_de_hauteur_pour_allonger": 0.8, "jeu_entre_voisines_m": 2.0}


def montee_des_talus():
    """PK, {côté : montée maximale du terrain au-dessus du bord de chaussée, entre 1 et 4 m du bord}."""
    import mobilier
    r = mobilier.Route()
    pk = np.arange(-20.0, 6740.0, REGLE["pas_m"])
    out = {}
    for cote in ("gauche", "droite"):
        m = np.zeros(len(pk))
        for i, s in enumerate(pk):
            v = []
            for d in REGLE["au_bord_m"]:
                x, y, zb, _ = r.point(s, cote, d)
                v.append(r.z_terrain(x, y, zb) - zb)
            m[i] = max(v)
        out[cote] = np.nan_to_num(m)
    return pk, out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--essai", action="store_true", help="affiche sans écrire")
    a = ap.parse_args()
    cfg = json.loads(FICHIER.read_text(encoding="utf-8"))
    pk, montee = montee_des_talus()
    parois = cfg["parois"]

    def note(e, dec, allonge=0.0):
        hm = sum(e["hauteur_m"]) / 2
        s = (pk >= e["pk_debut_m"] + dec) & (pk <= e["pk_fin_m"] + dec + allonge)
        return float(np.minimum(montee[e["cote"]][s], hm).mean() / hm) if s.any() else 0.0

    for e in parois:
        for k in ("recalage_pk_m", "allonge_m", "note_recalage"):
            e.pop(k, None)
    emprise = lambda e: (e["pk_debut_m"] + e.get("recalage_pk_m", 0), e["pk_fin_m"] + e.get("recalage_pk_m", 0) + e.get("allonge_m", 0))  # noqa: E731
    # les plus mal placées d'abord : elles prennent la place dont elles ont besoin, les autres s'en arrangent
    for e in sorted(parois, key=lambda e: note(e, 0)):
        n0 = note(e, 0)
        if n0 >= REGLE["note_suffisante"]:
            continue
        autres = [emprise(o) for o in parois if o is not e and o["cote"] == e["cote"]]
        libre = lambda d0, d1: all(d1 <= x0 - REGLE["jeu_entre_voisines_m"] or d0 >= x1 + REGLE["jeu_entre_voisines_m"]   # noqa: E731
                                   or (x0 == e["pk_fin_m"] and d1 <= x0) or (x1 == e["pk_debut_m"] and d0 >= x1) for x0, x1 in autres)
        decs = [d for d in range(-REGLE["glissement_max_m"], REGLE["glissement_max_m"] + 1, 2)
                if libre(e["pk_debut_m"] + d, e["pk_fin_m"] + d)]
        if not decs:
            continue
        v = [note(e, d) - REGLE["cout_par_m"] * abs(d) for d in decs]
        d = decs[int(np.argmax(v))]
        if d == 0 or note(e, d) - n0 < REGLE["gain_min"]:
            continue
        e["recalage_pk_m"] = d
        allonge = 0.0
        if n0 < REGLE["note_tres_basse"]:
            hm = sum(e["hauteur_m"]) / 2
            longueur = e["pk_fin_m"] - e["pk_debut_m"]
            while (allonge < longueur and libre(e["pk_debut_m"] + d, e["pk_fin_m"] + d + allonge + REGLE["pas_m"])
                   and np.interp(e["pk_fin_m"] + d + allonge + REGLE["pas_m"], pk, montee[e["cote"]]) >= REGLE["part_de_hauteur_pour_allonger"] * hm):
                allonge += REGLE["pas_m"]
            if allonge:
                e["allonge_m"] = allonge
        e["note_recalage"] = (f"relief laser : sur place le terrain n'atteint que {n0:.0%} de la hauteur relevée ; {note(e, d, allonge):.0%} "
                              f"une fois la paroi glissée de {d:+d} m" + (f" et allongée de {allonge:.0f} m" if allonge else ""))
    for e in parois:
        if "recalage_pk_m" in e:
            a0, a1 = emprise(e)
            print(f"  {e['pk_debut_m']:.0f}-{e['pk_fin_m']:.0f} {e['cote']} -> {a0:.0f}-{a1:.0f} : {e['note_recalage']}")
    print(f"{sum('recalage_pk_m' in e for e in parois)} parois recalées sur {len(parois)}")
    cfg["recalage"] = ("recalage_pk_m, allonge_m et note_recalage sont calculés par scripts/22_recaler_parois.py d'après le relief laser ; "
                       "les PK relevés (pk_debut_m, pk_fin_m) ne sont jamais modifiés")
    if not a.essai:
        FICHIER.write_text(json.dumps(cfg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("écrit :", FICHIER.relative_to(RACINE))


if __name__ == "__main__":
    main()
