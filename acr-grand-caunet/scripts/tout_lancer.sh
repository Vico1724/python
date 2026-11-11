#!/usr/bin/env bash
# Rejoue les phases 2 et 3 (quelques minutes, ~250 Mo téléchargés dans data/raw).
# Prérequis : Python 3.11+, `pip install -r requirements.txt`, accès à data.geopf.fr.
set -euo pipefail
cd "$(dirname "$0")"
python3 01_collecte_vecteurs.py     # routes, bâtiments, végétation... (BD TOPO, BD Forêt)
python3 02_trace_es.py              # tracé de l'ES + contrôle des PK officiels
python3 03_collecte_rasters.py      # relief LiDAR HD 0,5 m + orthophoto 20 cm
python3 04_profil_virages.py        # profil en long, pentes, virages, ponts
python3 05_couloir_vecteurs.py      # décor dans le couloir + carrefours
python3 06_figures.py               # cartes et graphiques de contrôle
python3 07_chaussee_precise.py      # phase 3 : axe précis et bords de chaussée, tous les mètres
python3 08_modele_3d.py             # modèle 3D glTF : route + terrain texturé (+ rendus si Chromium/Playwright)
python3 11_route_ouvrages.py        # route texturée, marquage, tabliers et parapets des ponts
python3 12_carrefours_annexes.py    # carrefours : voies fermées en enrobé, îlot, balisage de fermeture
python3 09_export_stage_ir.py       # export « Stage IR » v2 (ACR Extra Stages) : stage.json + collision.glb
python3 10_semis_arbres.py          # semis des arbres et arbustes : position, hauteur, essence, élément du jeu
python3 13_paysage_lointain.py      # paysage lointain jusqu'à l'horizon (anneau autour du couloir)
python3 14_textures_sol.py          # images de sol par dalle, sans les arbres, et relief fin près de la route
python3 15_vues_decor.py            # vues conducteur de contrôle avec le décor complet
