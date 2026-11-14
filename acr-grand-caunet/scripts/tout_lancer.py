"""Rejoue toute la chaîne, de la collecte des données au paquet Unreal (étapes 01 à 16), sous Windows comme sous
Linux : même liste et même ordre que tout_lancer.sh.

Prérequis : Python 3.11 ou plus récent, « pip install -r requirements.txt », accès à data.geopf.fr (IGN) et, pour
l'étape 14, à polyhaven.com (textures CC0, une seule fois). Node.js et Playwright sont FACULTATIFS : sans eux, les
rendus de contrôle (08, 11, 12, 15) sont sautés avec un message, le reste est produit normalement.
Durée : environ une heure la première fois (téléchargements, ~600 Mo dans data/raw), puis 25 à 35 minutes.
Mémoire : l'étape 14 lance 4 processus de 2 à 3 Go chacun.

Exemples (depuis la racine du dépôt) :
  python scripts/tout_lancer.py                        toute la chaîne
  python scripts/tout_lancer.py --depuis 13            de l'étape 13 à la fin
  python scripts/tout_lancer.py --seulement 16         le paquet Unreal seul (données déjà produites)
  python scripts/tout_lancer.py --sans-telechargement  saute 01, 03 et 06 (collectes et fonds de carte) : les
                                                       données brutes doivent déjà être dans data/raw
  python scripts/tout_lancer.py --sans-rendus          saute 15 (vues de contrôle avec le décor)
  python scripts/tout_lancer.py --liste                affiche les étapes
Les arguments placés après « -- » sont passés à l'étape 16 (par exemple : -- --axes X,Z,Y).
"""
import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent

# (numéro, script, rôle, télécharge)
ETAPES = [
    (1, "01_collecte_vecteurs.py", "routes, bâtiments, végétation (BD TOPO, BD Forêt)", True),
    (2, "02_trace_es.py", "tracé de l'ES et contrôle des PK officiels", False),
    (3, "03_collecte_rasters.py", "relief LiDAR HD 0,5 m et orthophotos 20 cm", True),
    (4, "04_profil_virages.py", "profil en long, pentes, virages, ponts", False),
    (5, "05_couloir_vecteurs.py", "décor dans le couloir et carrefours", False),
    (6, "06_figures.py", "cartes et graphiques de contrôle (fonds IGN téléchargés)", True),
    (7, "07_chaussee_precise.py", "axe précis et bords de chaussée, tous les mètres", False),
    (70, "07b_regulariser_chaussee.py", "régularisation de l'axe et des bords (bruit de mesure, coutures entre sources)", False),
    (8, "08_modele_3d.py", "modèle 3D : route et terrain texturé", False),
    (11, "11_route_ouvrages.py", "route texturée, marquage, tabliers et parapets", False),
    (12, "12_carrefours_annexes.py", "carrefours : voies fermées, îlot, balisage", False),
    (10, "10_semis_arbres.py", "semis des arbres et arbustes", False),
    (9, "09_export_stage_ir.py", "export « Stage IR » (ACR Extra Stages)", False),
    (13, "13_paysage_lointain.py", "paysage lointain jusqu'à l'horizon", False),
    (14, "14_textures_sol.py", "images de sol par dalle et relief fin", False),
    (15, "15_vues_decor.py", "vues conducteur de contrôle", False),
    (150, "15b_sols_du_jeu.py", "matières de sol du jeu : proportions par point, pour les masques du terrain", False),
    (16, "16_paquet_unreal.py", "paquet prêt à importer dans Unreal (paquet_unreal/)", False),
]
MODULES = ["numpy", "scipy", "requests", "pyproj", "shapely", "rasterio", "matplotlib", "PIL", "skimage", "cv2"]


def verifier_environnement():
    if sys.version_info < (3, 11):
        raise SystemExit(f"Python 3.11 ou plus récent requis (trouvé {sys.version.split()[0]})")
    manque = [m for m in MODULES if importlib.util.find_spec(m) is None]
    if manque:
        raise SystemExit(f"modules absents : {', '.join(manque)} ; lancer : python -m pip install -r requirements.txt")
    if not (shutil.which("node") and shutil.which("npm")):
        print("Node.js absent : les rendus de contrôle seront sautés (facultatif).")


def main():
    ap = argparse.ArgumentParser(description="Rejoue la chaîne 01 -> 16.")
    ap.add_argument("--depuis", type=int, help="numéro de la première étape à lancer (ordre de la liste)")
    ap.add_argument("--jusqua", type=int, help="numéro de la dernière étape à lancer")
    ap.add_argument("--seulement", type=int, nargs="+", help="numéros des seules étapes à lancer")
    ap.add_argument("--sans-telechargement", action="store_true")
    ap.add_argument("--sans-rendus", action="store_true")
    ap.add_argument("--liste", action="store_true")
    argv = sys.argv[1:]
    extra = []
    if "--" in argv:
        k = argv.index("--")
        argv, extra = argv[:k], argv[k + 1:]
    a = ap.parse_args(argv)
    if a.liste:
        for n, s, role, dl in ETAPES:
            print(f"{n:>2}  {s:<26} {role}{'  [télécharge]' if dl else ''}")
        return
    verifier_environnement()
    ordre = [n for n, *_ in ETAPES]
    choix = []
    for n, s, role, dl in ETAPES:
        if a.seulement and n not in a.seulement:
            continue
        if a.depuis is not None and ordre.index(n) < ordre.index(a.depuis):
            continue
        if a.jusqua is not None and ordre.index(n) > ordre.index(a.jusqua):
            continue
        if a.sans_telechargement and dl:
            print(f"(sauté : {s}, téléchargement)")
            continue
        if a.sans_rendus and n == 15:
            print(f"(sauté : {s}, rendus)")
            continue
        choix.append((n, s, role))
    t0 = time.time()
    for n, s, role in choix:
        print(f"\n=== {s} : {role}", flush=True)
        t = time.time()
        cmd = [sys.executable, str(ICI / s)] + (extra if n == 16 else [])
        if n == 70 and any(m == 7 for m, *_ in choix):
            cmd.append("--neuf")          # l'étape 07 vient de recalculer la chaussée : la régularisation repart d'elle
        # PYTHONUTF8 : sous Windows, fichiers et sorties redirigées en UTF-8 (sinon cp1252 et erreurs sur « ≈ », « → »)
        r = subprocess.run(cmd, cwd=ICI, env={**os.environ, "PYTHONUTF8": "1"})
        if r.returncode != 0:
            raise SystemExit(f"échec de {s} (code {r.returncode}) après {time.time() - t:.0f} s ; reprendre avec "
                             f"--depuis {n}")
        print(f"=== {s} : terminé en {time.time() - t:.0f} s", flush=True)
    print(f"\nchaîne terminée : {len(choix)} étapes en {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
