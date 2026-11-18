# 19. Un rallye propre au Grand Caunet

Demande du directeur, 17 novembre 2026 : que la spéciale apparaisse dans son propre rallye et non plus dans le rallye du pays de Galles. Fait le même jour, au build 22.

## 19.1 Comment le jeu range les spéciales

Les menus du jeu lisent quatre tables, dans `Data/Database/Main/TrackSelection` :

| Table | Une ligne = | Champs utiles |
|---|---|---|
| `DT_TracksLocations` | un **lieu**, c'est-à-dire le « rallye » des menus | nom, histoire, logo, fond, pays, discipline, liste des spéciales, variante par défaut, difficulté, surfaces |
| `DT_TracksLocationsLogos` / `…Backgrounds` | l'image du logo ou du fond d'un lieu | chemin de la texture |
| `DT_Tracks` | une **spéciale** | nom, carte, images, niveau à charger (`Asset` → `DT_Levels`), lieu, variantes, modes de jeu, tirage du temps, `OptimalAirTemperature` |
| `DT_TracksVariants` | un **parcours** (sens, longueur) | nom, spéciale de rattachement, surface, pneus, météo, secteurs… |

Notre spéciale est construite par-dessus la variante `WelesS4HafrenSouthFullForward`. Elle appartenait donc à la spéciale Hafren Sud, elle-même rangée dans le lieu « Wales ». Le mod BioBio, installé chez le directeur, livre déjà ces tables avec un lieu « Chile » de son cru (son mod « registre », `pakchunk99-SandoRegistry_2_P`). C'est la preuve que le jeu accepte un lieu ajouté.

## 19.2 Ce qui est fait

Le petit conteneur des tables (`zz_acrxs_grandcaunet_table_9_P`, fait par `pc\scripts\6_table_asphalte.ps1`) livre désormais cinq tables au lieu d'une. Elles partent de celles du registre, pour que BioBio continue de marcher. Une nouvelle commande, `acr-ref rally-tables` (retouche `pc\patches\0007-rallye.patch`, fichier `Rally.cs`), y apporte les changements décrits dans `pc\scripts\rallye_grand_caunet.json` :

- **Lieu `GrandCaunet`**, copié de la ligne Chili de BioBio :
  - nom « Sainte Baume Rallye », le rallye dont l'ES du Grand Caunet fait partie, avec un texte de présentation en français ;
  - pays **France**, surface **Tarmac** ;
  - une seule spéciale, la nôtre, qui est aussi la variante par défaut ;
  - logo et fond propres.
- **Spéciale `GrandCaunet`**, copiée de la ligne BioBio :
  - nom « Le Grand Caunet » ;
  - niveau `WelesS4HafrenSouth`, c'est-à-dire celui que nos conteneurs remplacent ;
  - une variante, la nôtre ;
  - mode Essai libre ;
  - tirage du temps « Alsace », comme la météo de la variante depuis le build 23 (« Montecarlo » au build 22) ;
  - `OptimalAirTemperature` à 30 °C, comme Munster, depuis le build 23 (5 °C au build 22, valeur d'Hafren Sud ; voir `docs/18`, § 18.6).
- **Hafren Sud** ne garde que sa variante inverse.
- **Notre variante** est rattachée à la spéciale `GrandCaunet`.

**Depuis le build 24**, le logo est la plaque officielle du Sainte-Baume Rallye 2026 fournie par le directeur, sans le rond du numéro (`logo_sainte_baume.py`, `docs/14` § 18.3). Au build 22, le logo était une plaque au format du jeu, faite avec les logos du roadbook du rallye (`Roadbook SBRC 2026.pdf`, demande du directeur du 17/11). Ces logos sont pris dans le bandeau d'en-tête des pages, dont l'image et le masque sont recomposés dans `pc\etape2_unreal\ui\source\bandeau_roadbook_sbr2026.png` : titre « SAINTE BAUME RALLYE », ASA Marseille Provence Métropole, Ligue PACA, FFSA. Une bande « ES LE GRAND CAUNET » complète la plaque. Le roadbook ne contient pas d'autre logo du rallye, seulement des pictogrammes et des cartes. Le fond est la photographie aérienne IGN de l'épingle du PK 4 080. Les deux images sont faites par `pc\etape2_unreal\outils\images_rallye.py`. Ils sont importés dans `/Game/Environments/GrandCaunet/UI` par `scripts_editeur\importer_ui.py`, avec les réglages des images des lieux du jeu (groupe UI, compression `TC_EditorIcon`). Ils sont ensuite cuits avec le décor, dans `zz_gc_gc_P`.

## 19.3 Comment les lignes sont écrites

Une ligne de table se lit ainsi : le nom de la ligne, un en-tête de 2 octets qui dit quels champs suivent, puis les valeurs.
- Un renvoi vers une ligne d'une autre table occupe 18 octets : l'en-tête `00 05`, le nom de la table et le nom de la ligne.
- Une liste commence par son nombre d'éléments.
- Un texte libre s'écrit `0, -1, 1` suivi de la chaîne. Un texte du jeu renvoie à sa table de traduction.

La commande copie la ligne modèle, remplace les noms, les textes et la température, et retire les éléments de liste en trop. Chaque remplacement vérifie le nombre d'occurrences trouvées, sinon la commande s'arrête. Les noms nouveaux sont ajoutés au paquet par `LegacyPackage.AddExportName`.

**Relecture** (fin de `6_table_asphalte.ps1`) : les tables sont relues telles que le jeu les chargera, notre conteneur par-dessus le registre. Le script vérifie :
- que chaque table gagne exactement la ligne `GrandCaunet` ;
- qu'aucune autre ligne ne change, sauf Hafren Sud (qui perd notre variante) et le renvoi de notre variante ;
- que le lieu a la bonne spéciale et le bon pays.

Résultat du 17/11 : conforme.

## 19.4 Limites et suites possibles

- **Mode Essai libre seulement**, comme BioBio. Les autres modes (rallye, championnat) demandent des week-ends de rallye (`DT_RallyWeekendCalendarPreset`) propres au lieu. Les week-ends « Rally Wales » du jeu citent toujours notre variante. Ils n'ont pas été modifiés.
- **Carte et images de la spéciale** : la carte, l'image de la spéciale et l'image du salon sont encore celles d'Hafren Sud (`HafrenSouthTrack`, `HafrenSouthBackground`), comme avant. Faire les nôtres demande d'autres textures (même méthode que le logo).
- **Plaque de rallye sur la voiture** (`DT_StickersTrackLogos`) : pas de ligne pour notre lieu. Le jeu prend sans doute sa ligne « Default », comme pour BioBio. Une plaque Grand Caunet est possible avec la même méthode.
- **Le registre de BioBio** : nos tables partent des siennes. S'il est mis à jour ou retiré, il faut refaire le build. Sans lui, `6_table_asphalte.ps1 -SansRallye` revient à l'ancien classement, faute de lignes modèles.
- **À voir à l'essai** :
  - le menu Essai libre doit montrer un lieu « Sainte Baume Rallye » avec drapeau français, logo et fond, et la spéciale « Le Grand Caunet » dedans ;
  - le pays de Galles ne doit plus proposer que Hafren Sud inverse ;
  - le drapeau du chronomètre doit être français.
