# Ce qui est propre au Grand Caunet, et les généralisations à faire

*Inventaire du 17/11/2026 sur `projets/python/acr-grand-caunet/` (dix-neuvième version). Rien n'a été modifié : c'est la liste des travaux à faire avant que le skill fonctionne sans copie manuelle du projet.*

## 1. Inventaire du codé en dur

### 1.1 Identité de la spéciale

| Élément | Où | Valeur actuelle |
|---|---|---|
| Identifiant de l'export | `scripts/09_export_stage_ir.py` `STAGE_ID`, `pc/scripts/commun.ps1` `$IdSpeciale` | `grand_caunet_rally_01_route_0` |
| Nom affiché | `09` `NOM` | « Le Grand Caunet » |
| Dossier d'export | `09` `DOSSIER` ; lu en dur par `16_paquet_unreal.py:625`, `regles_arbres.py:390`, `pc/etape2_unreal/outils/{decor_hybride,relever_placement,zones_decor}.py` | `export/stage_ir/grand_caunet` |
| Conteneurs | `commun.ps1` `$NomConteneur`, `6_table_asphalte.ps1:38`, `chaine_decor.ps1` (`-Essai gc`) | `zz_acrxs_grandcaunet_P`, `zz_acrxs_grandcaunet_table_9_P`, `zz_gc_gc_P` |
| Rapports d'acr-ref | `4_construire.ps1:119,134`, `relever_placement.py:40` | `stage-grandcaunet.report.json`, `notes-grandcaunet.md` |
| Chemins Unreal | `16` `NOM` (`/Game/Environments/GrandCaunet`, `/Game/Levels/GrandCaunet`), `pierres_calcaires.py:28,50` (`SM_GrandCaunet*`), `construire_niveau.py` (dossiers d'acteurs `GrandCaunet/…`, `Saved/GrandCaunet`), `relire_decor.py:222`, `liste_factices.py:178`, `chaine_decor.ps1` (`-Inclure 'Environments/GrandCaunet'`) | `GrandCaunet` |
| Préfixe des matériaux | `matieres_du_jeu.json`, `16`, `construire_niveau.py` | `MI_GC_*` (sans gêne tant qu'une seule spéciale est installée) |
| Titres et générateurs | `02:203-225`, `07:602-694`, `08:131`, `11:159`, `13:434`, `16:299` | textes « ES Le Grand Caunet 2026 », « acr-grand-caunet » |

### 1.2 Géographie

| Élément | Où | Valeur actuelle |
|---|---|---|
| Emprise de téléchargement | `scripts/acr_geo.py:33` `BBOX_LONLAT` | (5,610 ; 43,225 ; 5,685 ; 43,268) |
| Points officiels | `acr_geo.py:27` `OFFICIAL` | `es_grand_caunet_2026_officiel.json` |
| Routes de la spéciale | `02_trace_es.py:27` `STAGE_ROADS` | {D3D, D1, D3} |
| Limite entre deux routes | `11_route_ouvrages.py:534` (`pk_limite_D3D_D1_m`), `:1016` (pont « D3D » du PK 1661 pris comme modèle) | D3D / D1 |
| Origines de grilles (Lambert-93) | `16` `GRILLE0` (913 500 ; 6 240 500), `LOIN0` (880 000 ; 6 210 000) ; `14_textures_sol.py:88` `ORIGINE_LOCALE` (900 000 ; 6 240 000) | à déduire de l'emprise |
| Zone de départ | `15b_sols_du_jeu.py:67-73` (`ZD_FENETRE_L93`, `ZD_VOIES_L93`, ornières, frange) ; `12_carrefours_annexes.py` section « constructions de la zone de départ » (`ZD_*`, enduits `:580-582`) ; `aplanissements.py:26` (`NOTES` = « parking du Grand Caunet ») | coordonnées et noms du Grand Caunet |
| Carrefour du Lion d'Or | `12_carrefours_annexes.py` (`PROLONGEMENTS["Lion d'Or"]` `:1125`, `depart_l93` `:1129`, `RELEVE_PONCEAU`), `07_chaussee_precise.py:967` (repère de figure), `25_recaler_objets_reco.py:15,55,111` (PK 3600-3712 exclus du recalage) | propre à ce carrefour |
| Repères de figures | `07:965-978` (`(5500, 5540)`, « approche : parking » au PK −90) | figures seulement |

### 1.3 PK

| Élément | Où | Valeur actuelle |
|---|---|---|
| Intermédiaires chronométrés | `09` `SPLITS` | (« INTER2 », « INTER6 ») |
| Parc d'assistance | `09` `PARC` | PK −47, 3 m à gauche |
| Contrôle départ / arrivée | `16:242` | « arrivée (PK 6736) » |
| Essais réduits | `16` `PK_E3` 1653, `PK_E4` (1600 ; 1800), figure des détails de chaussée (2100 ; 2400) | pont du PK 1653 |
| Longueur au menu | `6_table_asphalte.ps1:23` `-LongueurKm` | 6,738 |

### 1.4 Hôte gallois et jeu

| Élément | Où | Valeur actuelle |
|---|---|---|
| Fichiers de l'hôte | `4_construire.ps1:89-97` (BakedData, cellule `22VG0QIP9ATUQI633K86KWPFP`, table de notes, niveau persistant) | Hafren South 1/2 |
| Cellule de décor toujours chargée | `7_tout_refaire.ps1:40`, `chaine_decor.ps1:23` | `1LS8FPM8JIMX697U3QIPKC01K` |
| Cellules des officiels | `7_tout_refaire.ps1:40` | `A0I1JHQ2458PSST2XD0UTWQ2I`, `0QY7AIYF1F7BYQ1BH0V2NX22R` |
| Ligne de la table des variantes | `6_table_asphalte.ps1:23` | `WelesS4HafrenSouthFullForward` |
| Météo | `pneus_asphalte.py --meteo` | MonteCarlo |
| Version du jeu | `commun.ps1:17`, `0_controle.ps1`, catalogue `catalogue_jeu_25170642.txt.gz`, `acr_paks_build_25170642.csv` | 25170642 |
| Chemins | `commun.ps1` (jeu sur `Z:\Steamlibrary\…`, travail `Z:\acrxs`), `relever_placement.py:40`, `chaine_decor.ps1` (`C:\Program Files\Epic Games\UE_5.6`) | PC du directeur |

### 1.5 Données de référence propres à la spéciale (normal : à refaire à chaque fois)

`data/reference/` : `es_*_officiel.json`, `lignes_es.json`, `chaussee_corrections.json`, `carrefours_annexes.json`, `marquage_route.json`, `ouvrages_parapets.json`, `glissieres.json`, `mobilier_bord_de_route.json`, `parois_rocheuses.json`, `aires_et_pistes.json`, `bords_vegetation.json`, `zone_depart.json`, `aspect_chaussee.json`, `notes_copilote_retouches.json`, `calage_reco_reperes.json`, et les dossiers `releve_*`.

Génériques, à **copier** tels quels : `matieres_du_jeu.json`, `ressources_cc0.json`, `catalogue_jeu_25170642.txt.gz`, `acr_paks_build_25170642.csv`, `pc/etape2_unreal/{elements_jeu_utiles,factices,hauteurs_maillages}.json`, `pc/etape2_unreal/releves/*` (relevés du jeu), `pc/patches/*`.

## 2. Généralisations proposées (non faites)

Par ordre d'utilité. Chacune garde le Grand Caunet reconstructible à l'identique : c'est le test d'acceptation (même `stage.json`, même manifeste, même bilan de `relire_decor.py`).

1. **Un fichier `speciale.json` par spéciale** (gabarit : `gabarit_speciale.json`), lu par un module unique (`scripts/speciale.py`) qu'importent `acr_geo.py` et tous les scripts : identifiant, nom, rallye, année, routes, points officiels, intermédiaires, longueur, emprise (calculée depuis le tracé + 30 km si absente), origines de grilles (arrondies au kilomètre sous l'emprise), options. Remplace `STAGE_ID`, `NOM`, `DOSSIER`, `BBOX_LONLAT`, `OFFICIAL`, `STAGE_ROADS`, `SPLITS`, `PARC`, `GRILLE0`, `LOIN0`, `ORIGINE_LOCALE`, `PK_E3`, `PK_E4`.
2. **Une arborescence par spéciale** : `speciales/<id>/{data,modele,export,paquet_unreal,figures}` ; `ROOT` des scripts pointe vers elle (`--speciale <dossier>` sur `tout_lancer.py`, variable d'environnement pour les scripts appelés seuls). Les fichiers génériques du § 1.5 restent dans le dépôt commun.
3. **Les `.ps1` paramétrés** : `commun.ps1` lit `speciale.json` (identifiant, conteneurs, longueur au menu) et un `hote.json` (§ 4) ; `7_tout_refaire.ps1 -Speciale <dossier>` ; les options de personnages, d'officiels et de parc viennent de `speciale.json`.
4. **Un fichier `hote.json`** pour Hafren South : chemins de BakedData, cellule physique, table de notes, niveau persistant, cellule de décor toujours chargée, cellules des officiels, ligne de table, humidité de base d'origine. Préparer ainsi un second hôte permettrait d'installer deux spéciales en même temps.
5. **Sortir les objets du code vers les données** : la zone de départ (`12` section ZD, `15b` `ZD_*`, `aplanissements.NOTES`) vers `zone_depart.json` ; les prolongements de carrefour (`PROLONGEMENTS`, `RELEVE_PONCEAU`) vers `carrefours_annexes.json` ; l'exclusion du Lion d'Or de `25_recaler_objets_reco.py` vers un champ `"recaler": false` par objet.
6. **Noms Unreal et conteneurs dérivés de l'identifiant** : `NOM` de `16`, `pierres_calcaires.DOSSIER_UE`, `construire_niveau.py`, `relire_decor.py`, `liste_factices.py`, `chaine_decor.ps1` ; préfixe des matériaux `MI_<court>_*`.
7. **Contrôles lus dans les données** : l'arrivée de `16:242` lue dans `lignes_es.json` ; figures de contrôle à des PK pris dans les virages réels.
8. **Repli sans LiDAR HD** : `03` et `13` testent la couverture ; à défaut, RGE ALTI 1 m et un avertissement (le relief lointain et les parois perdront en qualité, à dire au directeur).
9. **Palette régionale** : sortir de `10_semis_arbres.py` (`JEU`, `SUBSTITUT_CHENE_VERT`) et de `regles_arbres.py` (`FAMILLE_*`) une table `essences_jeu.json` (essence BD Forêt → famille du jeu, échelles, interdits), avec la palette provençale actuelle par défaut.
10. **Saison** : un champ `saison` qui règle les parts « vert » / « sec » de `HERBES`, la couche d'herbe du sol et la part de `BlackmapleMonteCarlo`.
11. **Lecture du roadbook** : un petit script `00_points_officiels.py` qui transforme un tableau saisi (nom, PK, latitude, longitude) en `es_<id>_officiel.json`, la lecture du PDF restant faite par le modèle.
12. **Calage des vidéos et planches** : chemins de vidéos dans `speciale.json` ; `24_planches_parois.py` généralisé à tous les types d'objets (une planche tous les 6 m sur un intervalle de PK), pour que les agents de relevé aient toujours la même entrée.
13. **Contrôle « hors jeu » unique** : un `controle_hors_jeu.py` qui enchaîne `17_diagnostic_trace.py`, les aperçus 21 et 23 aux PK de `speciale.json`, le contrôle de placement et un bilan court (OK / à voir), pour que le skill n'ait qu'une sortie à lire.
14. **Version du jeu** : `25170642` en paramètre de `commun.ps1` et dans le nom des catalogues ; contrôle qui refuse de construire si le jeu a changé sans nouveau fichier de correspondance.

## 3. Ce qui ne demande pas de généralisation

- Les retouches d'acr-ref (`0001` à `0006`) : déjà paramétrées par options (`--keep-variants`, `--visuals-exclude`, `--level-wetness`, `--officials`, `--service-park`, `ideal_line` lu dans `stage.json`).
- Le redressement des bouts de porte (`09`, `bords_normaux`) : automatique, il ne cite pas le Lion d'Or.
- La ligne idéale, le lissage de la route, le relief lointain, la roche, le sol, la végétation et l'habillage : génériques, réglés par les constantes de `valeurs_calibrees.md`.
- `matieres_du_jeu.json` : générique pour la Provence calcaire, sauf les enduits de la zone de départ.

## 4. Gabarit de `hote.json` proposé (Hafren South 1/2)

```json
{
  "nom": "Hafren South 1/2",
  "variante_table": "WelesS4HafrenSouthFullForward",
  "baked": "acr/Content/Environments/WalesS4HafrenSouth/DataAssets/DA_WalesS4HafrenSouthBakedData",
  "cellule_physique": "acr/Content/Levels/WalesS4HafrenSouth/_Generated_/22VG0QIP9ATUQI633K86KWPFP",
  "notes": "acr/Content/Data/Pacenote/Tables/DT_PacenoteHafrenSouthForward",
  "niveau": "acr/Content/Levels/WalesS4HafrenSouth",
  "cellule_decor": "1LS8FPM8JIMX697U3QIPKC01K",
  "cellules_officiels": {"depart": "A0I1JHQ2458PSST2XD0UTWQ2I", "arrivee": "0QY7AIYF1F7BYQ1BH0V2NX22R"},
  "humidite_origine": 0.1,
  "longueur_max_km": 9.0,
  "version_jeu": "25170642"
}
```
