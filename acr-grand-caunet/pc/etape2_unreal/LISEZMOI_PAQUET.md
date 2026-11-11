# Le paquet d'import Unreal de la spéciale « GrandCaunet »

*11 novembre 2026. Pour la session Claude du PC du directeur, et pour le directeur.*

> **Mise à jour du 11/11/2026, après relevé dans le jeu sur le PC.** Deux points de ce guide sont dépassés, et `construire_niveau.py` a été corrigé en conséquence (`PROTOCOLE.md`, § 0 bis) :
>
> - **Parent des matériaux (§ sur les variantes, et « reste à faire » n° 3).** Les trois noms de paramètres sont confirmés. Mais avec `M_Simple` pour parent, les textures ne s'afficheraient pas : ses static switch de texture sont inactifs par défaut. Avec `--parent jeu`, le script prend à sa place la variante du jeu `MI_SisteronConcrete01`, et donne un relief plat aux variantes qui n'en règlent pas. Le manifeste continue de nommer `M_Simple`.
> - **Échelle des instances (et « reste à faire » n° 4).** Les dimensions des maillages sont relevées. Le script ne garde plus le maillage nommé par le manifeste : il en rechoisit un à la taille de chaque plante dans le même dossier (`scripts_editeur/attribution.py`), parce que ces dossiers contiennent aussi des souches et que les couvre-sols sont des plaques de quelques centimètres d'épaisseur.

## 1. Ce que c'est

Le décor de la spéciale a été préparé hors d'Unreal : découpé, nommé, converti et vérifié. Dans l'éditeur, il ne reste qu'à lancer un script, `scripts_editeur/construire_niveau.py`, qui lit un manifeste et fait tout le reste. Ce script n'a jamais tourné dans Unreal : ses appels incertains sont listés dans `A_VERIFIER.md`.

Il existe deux paquets :

| Paquet | Où | Contenu | Taille |
|---|---|---|---|
| **Échantillon** | `pc/etape2_unreal/echantillon/` (versionné, prêt tout de suite) | Essais E3 et E4 : 200 m autour du pont de pierre du PK 1653 (PK 1 600 à 1 800). On y trouve la route et son marquage, le pont, ses parapets et sa glissière, 2 dalles de 500 m et 5 sous-dalles fines, 14 morceaux d'anneau lointain allégé, 8 304 arbres et arbustes, ainsi que les mires d'axes et de relief. | 12 Mo |
| **Complet** | `paquet_unreal/` (non versionné, à produire sur le PC, § 4) | Toute la spéciale : 26 dalles, 126 sous-dalles, 38 tronçons de route et 38 de marquage, 58 groupes d'ouvrages, 8 de carrefours, 3 de balisage, 290 morceaux d'anneau lointain, 164 186 instances. | 420 Mo |

Chaque paquet contient :
- `manifeste.json` : un élément par maillage, texture, variante de matériau ou groupe d'instances. Pour chacun, il donne le fichier source, le chemin dans le projet, les réglages d'import, le matériau, la position de l'acteur et les essais concernés.
- `maillages/` : un glb par maillage.
- `textures/` : les images.
- `instances/` : une table CSV par maillage du jeu.

## 2. Conventions

**Noms.** Ils imitent BioBio, avec `GrandCaunet` comme nom de spéciale. Les indices des dalles sont comptés depuis le coin Lambert-93 (913 500 ; 6 240 500), par pas de 500 m pour les dalles et de 100 m pour les sous-dalles.

| Élément | Maillage | Texture | Relief | Variante de matériau |
|---|---|---|---|---|
| Dalle de 500 m | `SM_GrandCaunetTerrain_5_3` | `T_Terrain_5y3` | `T_TerrainN_5y3` | `MI_Terrain_5y3` |
| Sous-dalle de 100 m (bande route) | `SM_GrandCaunetTerrainFin_27_15` | `T_TerrainFin_27y15` | `T_TerrainFinN_27y15` | `MI_TerrainFin_27y15` |
| Anneau lointain (1 km ; « L » : 5 km) | `SM_GrandCaunetFarRing_36_32`, `SM_GrandCaunetFarRingL_…` | `T_FarRing_36_32` | | `MI_FarRing_36_32` |
| Route, marquage, par tronçon de 200 m de PK | `SM_GrandCaunetRoad_09`, `SM_GrandCaunetRoadMarking_09` | `T_GC_Enrobe`, `T_GC_Marquage` | | `MI_GC_Enrobe`, `MI_GC_Marquage` |
| Ouvrages, par tronçon et par matériau | `SM_GrandCaunetBridge_Pierre_09`, `…_Glissiere_lisse_09` | `T_GC_Pierre`… | | `MI_GC_Pierre`… |
| Carrefours, balisage | `SM_GrandCaunetJunction_…`, `SM_GrandCaunetTape_…` | | | |

Le tronçon `k` couvre les PK `200·k − 200` à `200·k`. Le tronçon 09 va donc du PK 1 600 au PK 1 800.

**Chemins dans le projet `acr`.**
- Décor : `/Game/Environments/GrandCaunet/{Terrain,Road,Bridges,Junctions,Props,FarRing,Shared}/{Meshes,Textures,Materials}`.
- Niveaux : `/Game/Levels/GrandCaunet`, `GrandCaunet_E3` et `GrandCaunet_E4`.
- Éléments propres à l'éditeur, **à ne jamais livrer** : `/Game/GC_EditeurSeulement/` (matériau de secours, mires).

**Repère.** Unreal : X = est, Y = sud, Z = haut, en centimètres, avec pour origine l'axe de la chaussée au PK 0.
- Depuis Lambert-93 : `UE = 100 · (x − 917 008,49 ; 6 241 030,6 − y ; z − 398,55)`.
- Depuis les glb du modèle (`modele/`, X est, Y haut, Z sud) : `UE = 100 · (gX, gZ, gY)`.

Points de contrôle :

| Point | Lambert-93 (m) | Unreal (cm) |
|---|---|---|
| Départ, PK 0 | (917 008,49 ; 6 241 030,60 ; 398,55) | (0 ; 0 ; 0) |
| Arrivée, PK 6 736 | (914 282,52 ; 6 243 375,66 ; 344,71) | (−272 597 ; −234 506 ; −5 384) |

**Pivots.** Chaque maillage est recentré sur son pivot : centre de son emprise en plan, à son altitude la plus basse, arrondi au centimètre. L'acteur se pose à `acteur.position_cm`, sans rotation ni échelle.
- Les grandes coordonnées (jusqu'à 33 km) sont portées par l'acteur, en double précision en UE 5. Les sommets restent petits, donc précis en simple précision.
- Contrôle : après la découpe, les sommets partagés par deux dalles voisines coïncident à 0,001 cm près.

**Format des maillages.** Ce sont des glb (glTF binaire), lus par l'importeur Interchange d'Unreal 5.6.
- Chacun contient un seul maillage, une seule section de matériau au nom de sa variante, des normales et des UV. Ni matériau texturé ni image n'y sont intégrés.
- Les UV des dalles vont de 0 à 1. Les UV répétées (enrobé, pierre) ont été ramenées près de 0 : dans le modèle d'origine, celles des carrefours dépassaient 10⁶, ce qui fait trembler les textures en simple précision.
- FBX n'a pas été retenu : l'écrire de façon fiable exige le SDK d'Autodesk. OBJ ne porte pas de noms de section fiables.

**Axes de l'importeur.** Le paquet suppose qu'Unreal convertit un glb par `UE = 100 · (gX, gZ, gY)`. Ce n'est pas vérifié. La première commande (`--mire`) importe trois barres de 4, 2 et 1 m, tracées le long des axes X, Y et Z du fichier, et en déduit la conversion réelle.
- Si elle diffère, le script s'arrête et donne la commande de correction : `python pc\etape2_unreal\outils\reaxer_paquet.py <paquet>\manifeste.json --axes <valeur>`. Elle réécrit les glb du paquet sans les données sources, en Python seul ; on peut aussi refaire le paquet avec `scripts/16_paquet_unreal.py --axes <valeur>`.
- Seuls les sommets des glb changent ; le reste du manifeste ne bouge pas.

**Textures.**
- Toutes ont des dimensions en puissances de 2. Les images de dalle de 2 660 px ont été ramenées à 2 048 px (26 cm par pixel ; option `--px-dalle 4096` pour les agrandir).
- Couleur : JPEG de qualité 95, en sRGB, compression `TC_Default`, adressage `Clamp` pour le terrain, `Wrap` pour les matières répétées. Les sous-dalles à 5 cm sont recopiées sans recompression.
- Relief : PNG sans perte, linéaire (sRGB décoché), compression `TC_Normalmap`, **convention DirectX, canal vert déjà inversé**. Il ne faut donc pas cocher « Flip Green Channel ».
- Contrôle à l'œil : ouvrir `T_GC_MireRelief`, un dôme. Sa moitié haute doit être violacée et sa moitié basse verdâtre. Posé sur un plan éclairé, il doit paraître bombé ; s'il paraît creusé de haut en bas, la convention est inversée.

**Matériaux.** Chaque variante désigne deux parents :
- le parent du jeu pressenti, `M_Simple`, avec les paramètres `Simple_BaseColor_Texture`, `Simple_OcclRoughMet_Texture` et `Simple_Normal_Texture` (noms repris d'ACR Extra Stages, **à confirmer**), plus un alternatif pour l'essai E3b (`M_TerrainMaster_light`, `M_AsphaltMaster_Adv`) ;
- un parent de secours, `M_GC_Secours`, créé par le script, avec les paramètres `Couleur`, `ORM` et `Relief`.

Par défaut, le script utilise le secours, pour voir le décor dans l'éditeur. Avec `--parent jeu`, il prend le factice `M_Simple` créé par `creer_factices.py`. **Pour cuire vers le jeu, toujours `--parent jeu`** : le secours est un matériau maître de notre éditeur et ne doit pas partir dans le jeu.

**Instances.** Une table CSV par maillage du jeu, avec les colonnes suivantes :
- `x_cm`, `y_cm`, `z_cm` : position dans le repère ci-dessus ; l'altitude est celle du maillage de terrain importé ;
- `lacet_deg` : tirage à graine fixe ;
- `hauteur_voulue_m`, `pk_m`, essence.

Le maillage du jeu est celui de `arbres.csv` (tirage à graine fixe de l'étape 10). Tous sont présents au catalogue du jeu. Aucune instance n'est sur la chaussée.

L'échelle vaut `hauteur_voulue_m × 100 / hauteur native`. La hauteur native de chaque maillage du jeu est inconnue ici : la relever une fois (`PROTOCOLE.md` E2) dans `pc/etape2_unreal/hauteurs_maillages.json`. Sans ce fichier, l'échelle vaut 1. Les rubalises (`BC_NarrowTapeActor`, un Blueprint du jeu) ne sont pas en instances ; nos propres rubalises sont fournies en maillage (`SM_GrandCaunetTape_*`).

**Collision.** Aucune. La physique vient du BakedData d'ACR Extra Stages. Nanite est désactivé au départ.

## 3. Lancer l'import

Dans l'éditeur du projet `acr`, console Python (`py`), les factices étant créés au préalable (`creer_factices.py`) :

```
py "Z:\<dépôt>\pc\etape2_unreal\scripts_editeur\construire_niveau.py" --etendue E3 --mire
py "Z:\<dépôt>\pc\etape2_unreal\scripts_editeur\construire_niveau.py" --etendue E4
py "Z:\<dépôt>\pc\etape2_unreal\scripts_editeur\construire_niveau.py" --manifeste "Z:\<dépôt>\paquet_unreal\manifeste.json" --etendue complet
```

Options :
- `--parent jeu` : pour cuire vers le jeu ;
- `--placement <rapport stage-build>` : pour poser le décor dans le repère physique d'ACR Extra Stages ;
- `--sans-instances` ;
- `--sans-eclairage` : sans le soleil, le ciel et la brume de contrôle ;
- `--seulement-assets`.

Le rapport est écrit dans `<projet>\Saved\GrandCaunet\construire_niveau_<étendue>.json`. Il compte notamment les verdicts « REPÈRE CONFORME » ou « REPÈRE DIFFÉRENT », issus de la comparaison des bornes de chaque maillage importé avec le manifeste.

Avant d'aller sur le PC, la logique a été vérifiée ici avec un faux module `unreal` :

```
python3 pc/etape2_unreal/outils/essai_construire.py [paquet_unreal/manifeste.json]
```

## 4. Produire le paquet complet sur le PC

Les données brutes ne sont pas versionnées : il faut rejouer la chaîne une fois. Il faut Python 3.11 ou plus récent ; Node.js n'est pas nécessaire (les rendus de contrôle sont alors sautés).

```
cd Z:\<dépôt>
python -m pip install -r requirements.txt
python scripts\tout_lancer.py              # 01 -> 16, ~1 h la première fois (~600 Mo téléchargés)
python scripts\tout_lancer.py --seulement 16 -- --axes X,Z,Y   # refaire le paquet seul, axes au besoin
```

Le paquet arrive dans `paquet_unreal\`. `python scripts\16_paquet_unreal.py --echantillon` refait l'échantillon. Sous l'option `--pk-min A --pk-max B`, seuls les éléments de cette plage sont écrits.

## 5. Ce qui reste à décider ou à faire dans l'éditeur

1. **Vérifier les appels du script** (`A_VERIFIER.md`). Le plus incertain est l'ajout d'un composant d'instances à un acteur.
2. **La correspondance d'axes** de l'importeur glb (mire), et la convention du relief (dôme).
3. **Le vrai parent des matériaux** et les noms de ses paramètres (`acr-ref export`, `PROTOCOLE.md` E1b et E3b). Il faudra ensuite compléter `factices.json`, ou corriger `PARAM_SIMPLE` dans `scripts/16_paquet_unreal.py` et refaire le paquet.
4. **Les hauteurs natives** des maillages d'arbres du jeu (`hauteurs_maillages.json`).
5. **Le ciel, la météo et les acteurs de jeu** (E2), qui ne sont pas dans ce paquet.
6. **Faut-il Nanite, ou des niveaux de détail ?** L'anneau lointain complet compte 1,5 million de triangles et le terrain 0,73 million : à juger à la fréquence d'images.
7. **Ne jamais inclure `GC_EditeurSeulement`** dans la cuisson.
