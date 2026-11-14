"""Forme des arbres du jeu : rayon du feuillage à chaque hauteur, lu dans les archives installées sans rien modifier.

Pourquoi : à l'import, chaque arbre reçoit l'un des maillages de sa famille d'après sa seule hauteur. Or les quinze pins
d'Alep du jeu vont du pin parasol à tronc dégagé (SM_AleppoPine11 : rien sous 5 m, houppier de 5 m) au pin bas et
étalé, feuillu jusqu'au sol (SM_AleppoPine06 : 9 m de haut, 13 m de large). Vu en jeu le 13/11/2026 : des arbres
débordent sur la route. La règle de dégagement (scripts/regles_arbres.py) a besoin de la vraie forme de chaque maillage.

Mesure : sommets du maillage (acr-ref mesh-uv), centrés sur le pied du tronc ; pour chaque dixième de la hauteur, rayon
en dessous duquel se trouvent 98 % des sommets de la tranche.

Usage : python pc/etape2_unreal/outils/profils_arbres.py
Sortie : pc/etape2_unreal/releves/profils_arbres.json
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

import numpy as np

KIT = Path(__file__).resolve().parents[1]
FAMILLES = ["Foliage/Trees/AleppoPine", "Foliage/Trees/BlackpineMonteCarlo", "Foliage/Trees/Smoketree", "Foliage/Trees/Blackmaple",
            "Foliage/Trees/BlackmapleMonteCarlo", "Foliage/Trees/Cypress", "Foliage/Trees/Olivetree", "Foliage/Trees/Boxthorn",
            "Foliage/Trees/Fig"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--acr-ref", default=r"Z:\acrxs\bin\acr-ref\acr-ref.exe")
    ap.add_argument("--jeu", default=r"Z:\acrxs\construction\vanilla")
    ap.add_argument("--usmap", default=r"Z:\acrxs\mappings\acr_25170642.usmap")
    a = ap.parse_args()
    veg = json.loads((KIT / "releves" / "maillages_vegetation.json").read_text(encoding="utf-8"))["dossiers"]
    env = {**os.environ, "DOTNET_SYSTEM_GLOBALIZATION_INVARIANT": "1"}
    motif = re.compile(r"\s*v\s+(\d+)\s+\(\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)\)")
    out = {"source": "sommets des maillages du jeu (acr-ref mesh-uv), archives d'origine", "unite": "mètres, à l'échelle 1",
           "lecture": "rayons_m : pour chaque dixième de la hauteur, du pied à la cime, rayon contenant 98 % des sommets de la tranche, "
                      "compté depuis le pied du tronc", "familles": {}}
    for fam in FAMILLES:
        profils = {}
        for nom in sorted(veg.get("/Game/" + fam, {})):
            r = subprocess.run([a.acr_ref, "mesh-uv", f"acr/Content/{fam}/{nom}.uasset", "--limit", "400000", "--game", a.jeu, "--usmap", a.usmap],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
            V = {}
            for ligne in r.stdout.splitlines():
                m = motif.match(ligne)
                if m:
                    V[int(m.group(1))] = (float(m.group(2)), float(m.group(3)), float(m.group(4)))
            if len(V) < 50:
                print(f"  {nom} : illisible ({len(V)} sommets)")
                continue
            P = np.array(list(V.values()))
            P[:, 2] -= max(P[:, 2].min(), -0.6) if P[:, 2].min() < 0 else 0.0     # racines sous le sol ignorées
            h = float(P[:, 2].max())
            pied = P[P[:, 2] < 0.05 * h]
            rad = np.hypot(P[:, 0] - np.median(pied[:, 0]), P[:, 1] - np.median(pied[:, 1]))
            rayons = []
            for i in range(10):
                s = (P[:, 2] >= 0.1 * i * h) & (P[:, 2] < 0.1 * (i + 1) * h + (1e-6 if i == 9 else 0))
                rayons.append(round(float(np.quantile(rad[s], 0.98)), 2) if s.sum() > 3 else 0.0)
            profils[nom] = {"haut_m": round(h, 2), "rayons_m": rayons, "sommets": len(P)}
            print(f"  {nom:27s} {h:5.1f} m | " + " ".join(f"{x:4.1f}" for x in rayons))
        out["familles"][fam] = profils
    f = KIT / "releves" / "profils_arbres.json"
    f.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("écrit :", f.relative_to(KIT.parents[1]))


if __name__ == "__main__":
    main()
