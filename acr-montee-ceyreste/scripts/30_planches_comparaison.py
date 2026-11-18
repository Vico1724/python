"""Planches de comparaison à cadrage voisin : photo réelle (Panoramax) | aperçu des formes AVANT l'affinage | APRÈS.

Pour chaque PK demandé : l'image Panoramax la plus proche (360°, 08/09/2025) est redressée en vue plane dans le sens de
la montée (champ 75°, comme l'aperçu) ; l'aperçu « vue du conducteur » de scripts/21_apercu_conducteur.py est rendu au
PK de la prise de vue, une fois avec le modèle de la génération précédente (fichiers versionnés du commit --avant, sans
parois rocheuses : aucun relevé n'existait) et une fois avec le modèle courant.

Limites : la caméra Panoramax est sur le toit d'un véhicule qui DESCEND (voie opposée, ~2,5 m de haut) ; l'aperçu est à
1,15 m sur la voie de droite de la montée. Les cadrages sont voisins, pas identiques. L'aperçu ne montre ni matières ni
végétation.

Les extraits de photos sont sous licence Etalab 2.0 (Licence Ouverte), producteur Région Sud / Immergis, via Panoramax :
la mention figure sur chaque planche.
Usage : python scripts/30_planches_comparaison.py 520 800 1150 1300 2016 [--avant 19e1108]
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from acr_geo import FIG, ROOT  # noqa: E402


def charger(nom, fichier):
    spec = importlib.util.spec_from_file_location(nom, ICI / fichier)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def apercu(a21, pk, ref):
    sc, ch = a21.scene(ref)
    i = int(np.argmin(np.abs(ch["pk"] - pk)))
    j = min(i + 6, len(ch["pk"]) - 1)
    A = a21.s16.m08.to_gltf(ch["A"][[i, j]], ref).astype(float)
    vers = (A[1] - A[0]) * np.array([1.0, 0.0, 1.0]); vers /= max(np.linalg.norm(vers), 1e-9)
    oeil = A[0] + np.array([0.0, 1.15, 0.0]) + np.cross(vers, [0.0, 1.0, 0.0]) * 0.9
    return a21.rendre(sc, oeil, vers, 90.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pk", nargs="+", type=float)
    ap.add_argument("--avant", default="19e1108", help="commit de la génération précédente (fichiers versionnés de modele/)")
    a = ap.parse_args()
    P26 = charger("p26", "26_photos_rue.py")
    L = {r["id"]: r for r in P26.charger_liste()}
    ret = [i for i in json.loads((P26.DOSSIER / "retenues.json").read_text()) if (P26.DOSSIER / f"{i}.jpg").exists()]
    pk_ax, x_ax, y_ax = P26.axe()
    vues = []
    for pk in a.pk:
        i = min(ret, key=lambda k: abs(float(L[k]["pk_m"]) - pk))
        vues.append((float(L[i]["pk_m"]), i))
    # --- APRÈS : modèle courant
    a21 = charger("a21", "21_apercu_conducteur.py")
    ref = json.loads((a21.s16.MOD / "repere.json").read_text(encoding="utf-8"))
    apres = {p: apercu(a21, p, ref) for p, _ in vues}
    # --- AVANT : fichiers versionnés du commit --avant, terrain courant (non versionné, inchangé hors chaussée)
    tmp = Path(tempfile.mkdtemp())
    for f in ("route.glb", "route_habillee.glb", "ouvrages.glb", "annexes.glb", "balisage.glb", "repere.json"):
        try:
            data = subprocess.run(["git", "show", f"{a.avant}:acr-montee-ceyreste/modele/{f}"], cwd=ROOT, check=True,
                                  capture_output=True).stdout
            (tmp / f).write_bytes(data)
        except subprocess.CalledProcessError:
            shutil.copy(a21.s16.MOD / f, tmp / f)
    shutil.copy(a21.s16.MOD / "terrain_sol.glb", tmp / "terrain_sol.glb")
    a21b = charger("a21b", "21_apercu_conducteur.py")
    a21b.s16.MOD = tmp
    a21b.s16.parois_rocheuses = lambda *x, **k: 0          # aucun relevé de parois avant l'affinage
    refb = json.loads((tmp / "repere.json").read_text(encoding="utf-8"))
    avant = {p: apercu(a21b, p, refb) for p, _ in vues}
    shutil.rmtree(tmp, ignore_errors=True)
    # --- photo redressée et planche
    Image.MAX_IMAGE_PIXELS = None
    dest = FIG / "affinage" / "comparaison"; dest.mkdir(parents=True, exist_ok=True)
    for p, i in vues:
        r = L[i]
        _, _, cap = P26.projeter(pk_ax, x_ax, y_ax, float(r["x_l93"]), float(r["y_l93"]))
        eq = np.asarray(Image.open(P26.DOSSIER / f"{i}.jpg").convert("RGB"))
        ph = Image.fromarray(P26.vue_plane(eq, float(r["azimut_deg"]), cap, fov=75.0, largeur=1100, hauteur=560, tangage=-4))
        W, H = 1100, 560
        pl = Image.new("RGB", (W, 3 * H + 3 * 26 + 22), (255, 255, 255))
        d = ImageDraw.Draw(pl)
        try:
            from PIL import ImageFont
            fnt = ImageFont.truetype("DejaVuSans.ttf", 15)
        except OSError:
            fnt = None
        for k, (titre, im) in enumerate((("PHOTO RÉELLE - Panoramax, image " + i[:8] + f", PK {p:.0f}, 08/09/2025", ph),
                                          (f"AVANT l'affinage (génération {a.avant}) - aperçu des formes, PK {p:.0f}", avant[p]),
                                          (f"APRÈS l'affinage (18/11/2026) - aperçu des formes, PK {p:.0f}", apres[p]))):
            y = k * (H + 26)
            d.text((6, y + 5), titre, fill=(0, 0, 0), font=fnt)
            pl.paste(im.resize((W, H)), (0, y + 26))
        d.text((6, 3 * (H + 26) + 4), "Photo : Panoramax, Région Sud / Immergis, licence Etalab 2.0 (Licence Ouverte). "
               "Aperçu : ni matières ni végétation ; caméra photo plus haute, sur l'autre voie.", fill=(60, 60, 60), font=fnt)
        out = dest / f"comparaison_pk_{int(round(p)):04d}.jpg"
        pl.save(out, quality=85)
        print("écrit :", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
