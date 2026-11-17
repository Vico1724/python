# 02 - Ce qui vient du Grand Caunet, ce qui est neuf, ce qui est paramétré

Origine de toutes les copies : dossier `acr-grand-caunet/` du dépôt, branche `claude/epic-shannon-a8f6rp`, **commit `f93fded4d9e10cc2a6e50bb898c3fd38438ba12f`** (17/11/2026). Ce dossier n'est ni modifié ni lu par la montée : le projet est autonome (vérifié en le rendant inaccessible pendant une reconstruction complète, voir `ETAT.md`).

## 1. Recouvrement des tracés

Aucun tronçon commun (D3 pour la montée ; D3D puis D1 pour l'ES du Grand Caunet). Contact en un point : carrefour D3/D3D = PK 3746 de la montée = PK −183 du Grand Caunet. Il n'y avait donc ni chaussée, ni parois, ni glissières, ni mobilier relevés à reprendre : tout ce qui est propre au lieu a été recalculé (IGN), et ce qui ne se calcule pas (glissières, parapets, parois, mobilier, carrefours) reste **à relever** sur vidéo ou photos.

## 2. Données copiées (dans `data/reference/`)

| Fichier ici | Fichier d'origine | Nature |
|---|---|---|
| `matieres_du_jeu.json` | `acr-grand-caunet/data/reference/matieres_du_jeu.json` | matières physiques et matériaux lus dans le jeu (build 25170642) |
| `catalogue_jeu_25170642.txt.gz` | idem | catalogue des archives du jeu (noms seulement) |
| `acr_paks_build_25170642.csv` | idem | tailles d'archives, contrôle de version (0_controle) |
| `aspect_chaussee.json`, `marquage_route.json` | idem | aspect et marquage de l'enrobé (jugés en jeu sur le Grand Caunet) |
| `ressources_cc0.json` | idem | textures CC0 (Poly Haven) et crédits |
| `zone_depart.json` (objet « parking » seulement) | `acr-grand-caunet/data/reference/zone_depart.json` | emprise Lambert-93 du parking du Grand Caunet, aplani et utilisé comme parc d'assistance (au bout de la route modélisée) |
| `ouvrages_parapets.json` (rubrique `types`), `glissieres.json` (`geometrie`, `jeu`), `carrefours_annexes.json` (`balisage_par_defaut`) | fichiers de même nom | types, géométrie et noms des maillages du jeu ; **aucune position** reprise |

Kit PC (`pc/`) copié de `acr-grand-caunet/pc/` : `scripts/` (sauf ajouts ci-dessous), `patches/` (retouches d'ACR Extra Stages, inchangées), `etape2_unreal/{scripts_pc, scripts_editeur, outils, projet}`, `factices.json`, `elements_jeu_utiles.json`, `hauteurs_maillages.json` et, dans `etape2_unreal/releves/`, les seuls relevés **du jeu** (`acteurs`, `maillages_arbres`, `maillages_vegetation`, `materiaux_maitres`, `niveau_hote`, `profils_arbres`, `textures`, `variantes`). Le relevé de placement du Grand Caunet n'est **pas** copié : celui de la montée sera relevé après sa propre route physique.

Non copiés : vidéos, relevés vidéo et de reconnaissance, corrections de chaussée, parois, mobilier, aires et pistes, notes retouchées, calages en jeu (tout est propre au Grand Caunet), docs.

## 3. Scripts copiés et adaptés (`scripts/`)

Les 37 scripts de la chaîne (01 à 25 et modules) sont copiés. Principe : **les valeurs propres au lieu sont lues dans `epreuve.json`** (`acr_geo.param`), avec pour défaut la valeur d'origine ; rien n'est réécrit. Changements par rapport à l'origine (lignes de diff entre parenthèses) :

- `acr_geo.py` (35) : racine = dossier du projet ; `epreuve.json` ; `fichier_ref()` (lecture de `data/reference`) ; emprise et fichier officiel paramétrés ; `ouvrir_csv()` (.csv ou .csv.gz).
- `02_trace_es.py` (33) : routes, noms, calage **sans PK officiels** (origine = projection du départ).
- `06_figures.py` (20), `07_chaussee_precise.py` (28) : titres, légendes, étendue traitée, point de fin, extraits ; pas d'extrait au-delà de l'arrivée.
- `09_export_stage_ir.py` (50) : identifiant, lieu, temps intermédiaires, point d'arrêt, sortie du parc ; **contrôle du sens des notes par cap cumulé** (le contrôle d'origine se trompait sur les épingles de plus de 180°, absentes du Grand Caunet).
- `10_semis_arbres.py` (25) : extraits de contrôle tolérants à une formation absente ; arbustes toujours compressés.
- `11_route_ouvrages.py` (47) : ouvrages d'une seule route (`route_par_defaut`), vues de rendu paramétrées.
- `15_vues_decor.py` (14) : vues lues dans `epreuve.json`, temps vidéo facultatif.
- `16_paquet_unreal.py` (30) : nom du niveau (`MonteeCeyreste`), PK de contrôle, essai E3, relevé de placement propre.
- `regles_arbres.py` (37), `aplanissements.py`, `mobilier.py`, `pierres_calcaires.py`, `calage_reco.py`, 17 à 25 : lecture des relevés par `fichier_ref`, racine du projet.
- 08, 13, 14 : nom du générateur glTF seulement.

## 4. Kit PC adapté (`pc/`)

- `commun.ps1` : identifiant `ceyreste_rally_01_route_0`, conteneurs `zz_acrxs_ceyreste_P` et `zz_acrxs_ceyreste_table_9_P`, décor `zz_cey_cey_P`, noms affichés `pc/config/noms-ceyreste.toml`, **atelier propre** (`ACR_ATELIER`, sinon `<disque du jeu>\acrxs_ceyreste`), jeu par `ACR_JEU`.
- `4_construire.ps1`, `6_table_asphalte.ps1`, `0_controle.ps1`, `7_tout_refaire.ps1` : noms et chemins de la montée.
- `5_installer.ps1` : refuse d'installer si un conteneur du Grand Caunet est en place (renvoie à la bascule).
- **Neufs** : `bascule_vers_ceyreste.ps1`, `bascule_vers_grand_caunet.ps1` (voir `ETAT.md`, coexistence).
- `etape2_unreal/` : `repere_unreal.py` porte la racine, le lieu, le nom du niveau et le relevé de placement ; `chaine_decor.ps1`, `cuire_et_empaqueter.ps1`, `relire_decor.py`, `relever_placement.py`, `liste_factices.py`, `zones_decor.py`, `decor_hybride.py`, `construire_niveau.py` les utilisent ; préfixe de conteneur `zz_cey_`.

## 5. Neuf

`epreuve.json`, `data/reference/montee_ceyreste_officiel.json`, `lignes_es.json`, versions vides ou partielles des relevés de site, `pc/config/noms-ceyreste.toml`, les deux scripts de bascule, la documentation.

## 6. Écarts connus avec le Grand Caunet

- Pas de vidéo : lignes, largeurs, parois, glissières, parapets, carrefours et mobilier non relevés.
- Le point intermédiaire `INTER_JEU` (PK 1500) et la zone d'arrêt `ARRET` (PK 3700) n'existent pas sur l'épreuve réelle : ce sont des points techniques pour le format du jeu.
