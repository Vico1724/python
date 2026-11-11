r"""Voie hybride : écrit les zones où notre décor cuit par Unreal remplace les visuels d'essai de l'étape 1, pour
l'option --visuals-exclude ajoutée à l'outil d'ACR Extra Stages (pc/patches/0004-visuals-exclude.patch).

Deux familles de polygones, dans le repère du clone de Hafren (Unreal, cm) :
  "terrain" : l'emprise de nos dalles fines (sous-dalles de 100 m le long de la route). À l'intérieur, notre terrain
              est complet : la dalle de 500 m hors de la bande de route, la sous-dalle dans la bande.
  "autres"  : un couloir le long de notre route, entre les PK de l'étendue, élargi de MARGE_M de chaque côté : la
              chaussée, les piquets de bord et les pavés des obstacles de l'étape 1 n'y sont plus dessinés.
Hors de ces zones, l'étape 1 continue de dessiner sa route d'essai : on peut rouler jusqu'à notre décor.

EXÉCUTÉ sur le PC le 11/11/2026. Python ordinaire, sans dépendance.
Usage : python pc/etape2_unreal/outils/zones_decor.py [--etendue E4] [--sortie Z:\acrxs\unreal\hybride\zones_E4.json]
"""
import argparse
import csv
import json
import os
import sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RACINE = os.path.dirname(os.path.dirname(KIT))
sys.path.insert(0, os.path.join(KIT, "scripts_editeur"))
import repere_unreal as R  # noqa: E402

MARGE_M = 6.0          # de part et d'autre des bords de chaussée : piquets, parapets, glissières
RETRAIT_CM = 50.0      # les dalles sont rognées d'autant, pour ne pas mordre sur le terrain voisin de l'étape 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifeste", default=os.path.join(KIT, "echantillon", "manifeste.json"))
    ap.add_argument("--etendue", default="E4")
    ap.add_argument("--placement", default=os.path.join(KIT, "releves", "placement_etape1.json"))
    ap.add_argument("--sortie")
    a = ap.parse_args()
    man = json.load(open(a.manifeste, encoding="utf-8"))
    pl = json.load(open(a.placement, encoding="utf-8"))["placement"]
    org = json.load(open(os.path.join(RACINE, "export", "stage_ir", "grand_caunet", "stage.json"), encoding="utf-8"))["coordinates"]["origin"]
    rep = R.charger_repere()

    def l93(x, y):
        p = R.l93_vers_unreal_acrxs(x, y, 0.0, org, pl)
        return [round(p[0], 1), round(p[1], 1)]

    def propre(x_cm, y_cm):
        return l93(x_cm / 100.0 + rep["x0"], rep["y0"] - y_cm / 100.0)

    sortie = a.sortie or os.path.join(r"Z:\acrxs\unreal\hybride", f"zones_{a.etendue}.json")
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    if a.etendue == "complet":
        # toute la spéciale a son décor : plus aucun visuel d'essai n'est dessiné (les portiques restent, l'outil
        # ne les retire jamais)
        g = 1.0e8
        partout = [[[-g, -g], [g, -g], [g, g], [-g, g]]]
        with open(sortie, "w", encoding="utf-8") as f:
            json.dump({"description": "toute la spéciale : aucun visuel d'essai de l'étape 1, sauf les portiques",
                       "etendue": "complet", "terrain": partout, "autres": partout}, f)
        print(f"toute la spéciale -> {sortie}")
        return
    terrain = []
    for e in man["elements"]:
        if e["type"] == "StaticMesh" and e.get("acteur") and "TerrainFin" in e["nom"] and (a.etendue in e["essais"] or a.etendue == "complet"):
            p, b = e["acteur"]["position_cm"], e["bornes_locales_cm"]
            x0, x1 = p[0] + b["min"][0] + RETRAIT_CM, p[0] + b["max"][0] - RETRAIT_CM
            y0, y1 = p[1] + b["min"][1] + RETRAIT_CM, p[1] + b["max"][1] - RETRAIT_CM
            terrain.append([propre(x0, y0), propre(x1, y0), propre(x1, y1), propre(x0, y1)])
    pk = man["essais"].get(a.etendue, {}).get("pk_m")
    if not pk:
        raise SystemExit(f"l'étendue {a.etendue} n'a pas de plage de PK dans le manifeste")
    bords = []
    with open(os.path.join(RACINE, "data", "processed", "chaussee_precise.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if pk[0] <= float(r["pk_m"]) <= pk[1]:
                g, d = (float(r["x_gauche"]), float(r["y_gauche"])), (float(r["x_droite"]), float(r["y_droite"]))
                n = ((g[0] - d[0]) ** 2 + (g[1] - d[1]) ** 2) ** 0.5 or 1.0
                u = ((g[0] - d[0]) / n, (g[1] - d[1]) / n)
                bords.append(((g[0] + u[0] * MARGE_M, g[1] + u[1] * MARGE_M), (d[0] - u[0] * MARGE_M, d[1] - u[1] * MARGE_M)))
    pas = max(1, len(bords) // 100)                              # une centaine de quadrilatères suffit
    pts = bords[::pas] + ([bords[-1]] if (len(bords) - 1) % pas else [])
    autres = [[l93(*pts[i][0]), l93(*pts[i + 1][0]), l93(*pts[i + 1][1]), l93(*pts[i][1])] for i in range(len(pts) - 1)]
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump({"description": "zones où notre décor remplace les visuels de l'étape 1 (Unreal, cm, repère du clone)",
                   "etendue": a.etendue, "pk_m": pk, "terrain": terrain, "autres": autres}, f)
    print(f"{len(terrain)} dalles fines, couloir de {len(autres)} quadrilatères (PK {pk[0]:.0f} à {pk[1]:.0f}, ±{MARGE_M:.0f} m) -> {sortie}")


if __name__ == "__main__":
    main()
