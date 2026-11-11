# Étape 2 : le décor dans le jeu, avec Unreal Engine 5.6. Protocole d'essai

*11 novembre 2026. Ce document est destiné à une session Claude ouverte sur le PC du directeur, qui n'a pas notre contexte. Le directeur doit aussi pouvoir le lire.*

## 0. À lire d'abord

**Décision du directeur (11/11/2026).** Unreal Engine 5.6 est installé sur son PC. Il veut un rendu beau et réaliste, « à la manière de BioBio » : un terrain en dalles portant chacune sa photo aérienne, les arbres et objets du jeu, une route texturée.

**Règles :**
- Aucune archive d'origine du jeu n'est modifiée. Tout essai va dans `…\acr\Content\Paks\~mods\`, dans des fichiers `zz_gc_*_P.*` qu'on retire après l'essai.
- Le jeu tourne hors ligne, en Free Practice.
- Aucun fichier de BioBio n'est réutilisé, et on ne contacte pas son auteur.
- Lire la structure interne de BioBio sur le PC, avec FModel ou `acr-ref`, ferait gagner beaucoup de temps (E2), mais **seulement si le directeur l'autorise explicitement**. Par défaut, on ne le fait pas.
- On demande l'accord du directeur avant toute installation.

**Ce qui existe déjà**, et dont ce protocole se sert :
- **L'étape 1** (`pc/LISEZMOI.md`) : outils `retoc`, `acr-ref` et `acr-additive` construits dans `Z:\acrxs\bin`, fichier de correspondance `Z:\acrxs\mappings\acr_25170642.usmap`, mod d'essai de la physique.
- **Nos données :**
  - `modele/` : `terrain.glb` (26 dalles de 500 m, chacune avec son image JPEG), `route_habillee.glb`, `ouvrages.glb`, `annexes.glb`, `balisage.glb`, `repere.json` ;
  - bientôt `terrain_sol.glb`, `lointain.glb`, `textures_sol/` et `data/processed/textures_sol.json` ;
  - `data/processed/arbres.csv` : 41 584 arbres, avec position, hauteur, essence et maillage du jeu proposé ;
  - `export/stage_ir/` : sol physique, obstacles, notes du copilote.
- **Ce kit :**
  - `elements_jeu_utiles.json` : environ 1 960 éléments du jeu utiles, avec leur chemin, tirés du catalogue ;
  - `factices.json` : les éléments factices à créer ;
  - `scripts_editeur/` : Python de l'éditeur ;
  - `scripts_pc/cuire_et_empaqueter.ps1`.

  **Aucun de ces scripts n'a jamais été exécuté.**

**Étiquettes utilisées** (rigoureusement) :
- **[ACR-XS]** : prouvé, ou au moins construit et contrôlé, par le projet ACR Extra Stages (dépôt `nitnerolf420/acr-extrastages`, `docs/decisions.md`, `docs/load-proof.md`, `docs/acr-stage-anatomy.md`).
- **[BioBio]** : montré par la structure de BioBio, lue dans les sommaires de ses archives (`docs/04_integration_jeu.md`).
- **[UE courant]** : pratique courante du modding Unreal Engine 5, que je connais. Non vérifiée sur ce jeu.
- **[supposé]** : hypothèse.
- **[à vérifier : où]** : je ne suis pas sûr ; l'endroit à consulter sur le PC est indiqué (documentation Epic, en ligne ou dans l'éditeur).

## 1. L'idée générale

Le jeu affiche du contenu « cuit » : des fichiers déjà convertis pour Windows, dans des archives IoStore (`.utoc`, `.ucas`, `.pak`). L'éditeur Unreal sait cuire nos maillages, nos textures et nos variantes de matériaux. La difficulté est de faire désigner par nos éléments ceux du jeu, que nous ne possédons pas : pins d'Alep, matériaux maîtres, classes du jeu. La méthode courante **[UE courant]** est la suivante :
- créer dans notre projet des **éléments factices** qui portent **exactement le même chemin** que ceux du jeu (par exemple `/Game/Foliage/Trees/AleppoPine/SM_AleppoPine14`) ;
- s'en servir dans nos niveaux ;
- **ne pas les livrer**. À l'exécution, le jeu trouve à ce chemin son propre élément et l'utilise.

BioBio ne contient ni arbre, ni matériau maître, ni programme d'affichage (« shader ») **[BioBio]**, ce qui est cohérent avec cette méthode.

**Pourquoi seulement des variantes de matériaux du jeu.** Un matériau maître contient des programmes d'affichage compilés pour le moteur exact du jeu. Une **variante** (MaterialInstanceConstant) ne contient que des valeurs de paramètres : textures, nombres, couleurs. Elle réutilise les programmes déjà présents dans le jeu, **à condition de ne changer aucun paramètre « static switch »**, faute de quoi il faudrait de nouveaux programmes **[UE courant]**. Nous ne livrerons donc que des variantes, des textures et des maillages.

**Enchaînement des essais**, du plus simple au plus ambitieux. Chacun ne coûte que s'il le faut.

```
E0 installer, projet « acr », chaîne de cuisson ─► E1a texture remplacée ─► E1b maillage + variante de matériau
   │ E1 échoue (rien ne change, ou plantage)        │ E1 réussit
   └─► diagnostiquer (§ E1) ; si l'échec persiste : VOIE B (§ 7)
E2a niveau simple à nous + pin d'Alep du jeu, inscrit aux menus
   ├─ se charge ─► E2b acteurs de jeu par « classes souches » (voie A, BioBio)
   └─ ne se charge pas, ou E2b trop coûteux ─► voie HYBRIDE H : notre décor cuit, posé dans le clone de Hafren d'ACR Extra Stages
E3 une dalle de terrain avec sa photo (variante de M_Simple, puis d'un matériau de terrain du jeu)
E4 200 m complets (route, bords, 2 dalles, arbres, physique), puis toute la spéciale
```

## 2. E0 : installation, projet factice, chaîne de cuisson (½ à 1 journée, dont le téléchargement)

**But :** disposer d'un éditeur de la bonne version, d'un projet dont les chemins imitent ceux du jeu, et d'une commande qui produit un conteneur `zz_gc_*_P` ne contenant que nos éléments.

### Version d'Unreal Engine

- **Le jeu est en UE 5.6.1.** La preuve vient du fichier de correspondance produit par Dumper-7 chez ACR Extra Stages, nommé `5.6.1-0+UE5-acr.usmap` (`docs/decisions.md` D1) **[ACR-XS]**. Le suffixe `+UE5-acr` indique un moteur compilé par le studio depuis ses propres sources **[supposé : c'est la forme des numéros de version d'Unreal compilé depuis les sources]**.
- **Installer 5.6.1** par l'Epic Games Launcher (Unreal Engine > Bibliothèque > « + », choisir 5.6.1). Si le Launcher ne propose qu'un autre correctif 5.6.x, le prendre et noter son numéro. Les correctifs d'une même version mineure ne changent en principe pas le format des paquets **[UE courant ; à vérifier : notes de version 5.6.x sur dev.epicgames.com]**.
- **Ne pas prendre 5.5 ni 5.7** : le format des paquets diffère entre versions mineures **[UE courant]**.
- **Vérifier la version du jeu sur le PC :** clic droit sur `…\Assetto Corsa Rally\acr\Binaries\Win64\acr-Win64-Shipping.exe` > Propriétés > Détails, « Version du produit » **[à vérifier : le nom exact de l'exécutable]**. Noter le résultat.
- **Espace :** environ 60 Go pour l'éditeur **[ACR-XS, D5]**, plus 10 à 30 Go pour le projet et ses caches **[supposé]**. Visual Studio 2022, avec le module « Développement de jeux en C++ », n'est nécessaire qu'à partir de E2b (classes souches) **[à vérifier : page « Setting up Visual Studio » d'Epic pour 5.6]**.

### Le projet

1. Créer un projet **vide**, sans contenu de démarrage, **nommé exactement `acr`**, dans `Z:\acrxs\unreal\acr\`. Le nom du projet fixe la racine des chemins : notre `/Game/…` correspond alors à `acr/Content/…`, comme dans les archives du jeu **[UE courant]**. Avant de choisir, vérifier la racine de montage des archives du jeu : `retoc` affiche le point de montage d'un conteneur **[à vérifier : commande d'information de retoc, `retoc --help`]**. Le catalogue donne `acr/Content/…`.
2. Activer les extensions **Python Editor Script Plugin** et **Editor Scripting Utilities**. Vérifier que l'import glTF (Interchange) est actif **[à vérifier dans Édition > Extensions]**.
3. Créer nos dossiers : `/Game/GrandCaunet/` (Levels, Terrain, Route, Materiaux, Textures). Les factices vont à leurs chemins du jeu, par `scripts_editeur/creer_factices.py`.
4. Préparer la liste des factices (déjà faite) avec `python3 pc/etape2_unreal/outils/liste_factices.py`. Elle donne 60 éléments, tous vérifiés présents dans le catalogue : `M_Simple`, les 45 maillages d'arbres utilisés par `arbres.csv`, 3 matériaux à compléter et 11 classes Blueprint.

### La chaîne de cuisson

Le script `scripts_pc/cuire_et_empaqueter.ps1` enchaîne trois étapes :
1. Unreal cuit en fichiers séparés, avec `UnrealEditor-Cmd.exe acr.uproject -run=cook -targetplatform=Windows -unversioned …`.
2. Le script ne garde que nos chemins (option `-Inclure`) et **écarte tous les factices** (liste `factices.json`).
3. `retoc to-zen --version UE5_6` les empaquette en `zz_gc_<essai>_P.utoc/.ucas/.pak`. C'est exactement la commande d'ACR Extra Stages, sur des fichiers de même forme **[ACR-XS]**.

Points d'attention :
- `-unversioned` : le jeu est cuit « sans versions de propriétés » **[ACR-XS, anatomy]**, et il faut sans doute faire de même **[à vérifier : documentation « Cooking Content » d'Epic ; essayer sans cette option si E1 échoue]**.
- La compression Oodle est gérée par retoc, qui télécharge la bibliothèque lui-même **[ACR-XS]**.
- Autre voie possible : l'empaquetage d'Unreal (« Package Project ») avec IoStore et un découpage en « chunks » par Primary Asset Labels **[UE courant]**. Elle est moins sûre, parce qu'il faut empêcher les factices d'y entrer.
- **Où déposer l'archive :** dans `Paks\~mods\`. Un conteneur dont le nom finit par `_P` y remplace les paquets du jeu de même chemin. C'est **vérifié en jeu** (`docs/load-proof.md`) **[ACR-XS]**. BioBio dépose les siennes directement dans `Paks\`, sous le nom `pakchunk99-…_P` **[BioBio]** : c'est la solution de repli si `~mods` ne marchait pas.

## 3. E1 : preuve de chargement (1 à 2 heures)

**Préalable :** désinstaller le mod de l'étape 1 (`pc/scripts/6_desinstaller.ps1`), pour regarder Hafren South d'origine.

### E1a : une texture remplacée

**But :** établir que le jeu accepte une texture cuite par **notre** éditeur.

**Cible :** la bannière du portique de départ gallois, `/Game/Props/RallyProps/Gantries/T_RallyGantryWales_B` (catalogue). Elle est visible au départ de Hafren South et des autres spéciales galloises.

1. Lire ses réglages réels :

   ```
   Z:\acrxs\bin\acr-ref\acr-ref.exe export acr/Content/Props/RallyProps/Gantries/T_RallyGantryWales_B.uasset --game <vue d'origine> --usmap <usmap> --out Z:\acrxs\unreal\lu\T_RallyGantryWales_B.json
   ```

   Relever la taille, le format (DXT1 ou BC7…), le sRGB, le groupe de LOD et la case « VirtualTextureStreaming ». `acr-ref export` sait lire n'importe quel paquet **[ACR-XS]** ; la vue d'origine est celle de l'étape 1, `Z:\acrxs\construction\vanilla`.
2. Importer dans le projet, **au même chemin**, une image de même taille (par exemple le logo « Le Grand Caunet »), avec les mêmes réglages de compression.
3. Cuire et installer :

   ```
   pwsh -File scripts_pc\cuire_et_empaqueter.ps1 -Essai e1a -Inclure 'Props/RallyProps/Gantries/T_RallyGantryWales_B'
   ```

   Copier les trois fichiers dans `Paks\~mods\`.
4. En jeu : Pays de Galles, Hafren South, Free Practice. Regarder la bannière du portique.

**Conclusions :**
- **Notre image apparaît :** une texture cuite par notre éditeur est acceptée. Passer à E1b.
- **Rien ne change :**
  - le conteneur n'est pas monté, ou le chemin diffère. Vérifier le nom en `_P`, la présence des 3 fichiers, puis essayer dans `Paks\` (§ 2) ;
  - comparer le chemin interne avec la sortie de `retoc` (liste du conteneur).
- **Image brouillée, noire, ou plantage :** le format ne convient pas. Dans l'ordre :
  1. vérifier compression et taille ;
  2. recuire sans `-unversioned` ;
  3. comparer l'en-tête de notre paquet et l'original (`acr-ref legacy-dump`, `export-info`) **[ACR-XS : outils présents ; leur sortie exacte est à lire]** ;
  4. vérifier la version d'Unreal.
- **Échec persistant :** l'éditeur ne produit pas de contenu acceptable. Prendre la **voie B** (§ 7).

### E1b : un maillage et une variante d'un matériau du jeu

**But :** établir qu'un maillage cuit est affiché, et qu'une variante dont le parent est un **factice** se lie au **vrai** matériau du jeu.

1. Créer le factice `M_Simple` avec `creer_factices.py`. Les noms de ses paramètres, `Simple_BaseColor_Texture`, `Simple_OcclRoughMet_Texture` et `Simple_Normal_Texture`, viennent de la configuration d'ACR Extra Stages : ils y créent des variantes de `M_Simple` avec leurs textures (v1.8) **[ACR-XS : construites et contrôlées hors jeu ; les captures de leur README montrent des textures DiRT en jeu, sans consignation détaillée]**.
2. Créer `MI_GC_Essai` (parent `M_Simple`, une texture à nous) et un maillage simple, par exemple un panneau de 8 m.
3. Le placer **au chemin** `/Game/Props/RallyProps/Gantries/SM_RallyGantry8m`, en remplacement. Le portique gallois l'utilise probablement **[supposé : à confirmer par `acr-ref export` du Blueprint `BC_GantryWales`]**.
4. Cuire avec :

   ```
   -Inclure 'Props/RallyProps/Gantries/SM_RallyGantry8m','GrandCaunet/Materiaux','GrandCaunet/Textures'
   ```

   `M_Simple` est écarté automatiquement, comme tout factice.

**Ce qu'on doit voir :** notre panneau à la place du portique, éclairé et texturé.

**Conclusions :**
- **Réussi :** la méthode des factices marche pour les matériaux. Passer à E2 et E3.
- **Rose ou damier :** la variante ne trouve pas son parent ou ses programmes d'affichage. Vérifier qu'aucun « static switch » n'a été touché, et que le chemin du factice est exact. Relire les paramètres réels de `M_Simple` (`acr-ref export acr/Content/Materials/General/Masters/M_Simple.uasset`).
- **Gris uni :** le paramètre de texture est mal nommé.
- **Invisible :** essayer de cuire le maillage avec, puis sans Nanite **[UE courant]**.

## 4. E2 : un pin d'Alep du jeu dans un niveau à nous (½ journée pour E2a ; E2b de 2 à 5 jours)

### E2a : le niveau le plus simple que le jeu accepte

**But :**
1. le jeu charge-t-il un niveau **non découpé** à nous, inscrit dans ses menus ?
2. y remplace-t-il le pin factice par le vrai ?

BioBio est un niveau simple, sans World Partition **[BioBio]** : c'est donc possible pour lui.

1. Créer le niveau `/Game/GrandCaunet/Levels/GC_Essai` (Fichier > Nouveau niveau > « Empty Level », **pas** « Open World »). Y poser :
   - un sol (notre maillage, avec `MI_GC_Essai`) ;
   - un acteur de maillage portant le factice `/Game/Foliage/Trees/AleppoPine/SM_AleppoPine14` ;
   - un `PlayerStart` ;
   - une lumière directionnelle et un SkyLight, comme ciel de secours **[supposé]**.

   Dans les réglages du monde (World Settings), cocher « Force No Precomputed Lighting », pour ne dépendre d'aucun éclairage précalculé **[UE courant]**.
2. **Inscrire le niveau dans les menus** avec l'outil d'ACR Extra Stages **[ACR-XS : `acr-additive registry`, vérifié hors jeu]**. Écrire une fiche JSON (modèle : `mods/additive/stages-prototype/acrxstest.json` de leur dépôt) avec :
   - `"Id": "GcEssai"` ;
   - `"Level": "/Game/GrandCaunet/Levels/GC_Essai/GC_Essai"` **[à vérifier : forme exacte « paquet/objet » attendue]** ;
   - `"Location": {"Row": "Wales"}` ;
   - `"Track": {"Template": "WalesS4HafrenSouth", "Name": "GC ESSAI"}` ;
   - une variante avec `"Template": "WelesS4HafrenSouthFullForward"`.

   Puis :
   - extraire les tables `retoc to-legacy --filter Data/Database/Main/ <vue d'origine>\acr\Content\Paks <legacy>` (comme leur `mods/additive/build.ps1`, l. 177-200) ;
   - lancer `acr-additive registry --legacy <legacy> --out <mod> fiche.json` ;
   - lancer `retoc to-zen --version UE5_6 <mod> zz_gc_registre_P.utoc`.
3. **Écueil :** ce registre remplace les tables de menus en entier, tout comme celui de BioBio. **Pendant E2 à E4, BioBio doit être mis de côté** : déplacer ses deux archives `pakchunk99-*` hors de `Paks`, avec l'accord du directeur, et les remettre ensuite.
4. Cuire avec `-Inclure 'GrandCaunet' -Cartes '/Game/GrandCaunet/Levels/GC_Essai'`, installer les deux conteneurs, puis choisir « GC ESSAI » dans le menu.

**Ce qu'on peut voir :**
- **Le niveau se charge et le vrai pin d'Alep est là :** la voie A est ouverte. La voiture tombera sans doute, faute de physique : c'est attendu. Passer à E2b.
- **Le menu n'affiche pas l'entrée :** problème de registre. Relire les fiches et le journal d'`acr-additive`, et comparer avec leur prototype `AcrXsTest`.
- **Chargement interrompu, retour au menu, ou plantage :** lire le journal du jeu **[à vérifier : emplacement, probablement `%LOCALAPPDATA%\acr\Saved\Logs\`]**. Chercher les classes ou acteurs réclamés (« GameConfigurator », « TrackAvatar », « PlayerStartsManager »…). C'est l'indication de ce que E2b doit fournir.
- **Le pin est un cube :** le factice a été livré par erreur. Vérifier la liste du tri.

### E2b : les acteurs de jeu indispensables

D'après `docs/acr-stage-anatomy.md` § 4 **[ACR-XS, déduit de Hafren South]**, il faut dans le niveau :
- `BC_TrackAvatar_C`, avec son `BakedData` (la physique) ;
- `BC_PhysicsAvatar_C` et un `PhysicsWorldBounds` ;
- `GameConfigurator` et `BC_PlayerStartsManager_C` ;
- WorldSettings, avec `BC_GameMode_C` ;
- un ciel `BC_DMSky_*` et la météo ;
- par sens de parcours : `SplinesActor` (tracé central, idéal, bords, contour), déclencheurs de départ et d'arrivée, point de départ, `PacenoteSetupActor` (notes), 4 `RaceSector` et les murs de remise en piste.

Ces classes sont celles du jeu : `/Script/acr`, `/Script/dmphysics`, et des Blueprints `BC_*` sous `/Game/Data/...` (chemins dans `elements_jeu_utiles.json`, rubrique `acteurs_de_niveau`). Notre projet ne les possède pas. Deux façons de faire :

**1. Classes souches (voie A, celle que ACR Extra Stages appelle « A1 », non essayée par eux).**
- Écrire des classes C++ vides **de mêmes noms**, dans un module `acr` (le module principal du projet) et une extension `dmphysics`, ainsi que `dmenvironment` pour le ciel. Leurs propriétés doivent être déclarées **dans le même ordre** que dans le jeu.
- Créer ensuite les factices Blueprint aux chemins du jeu, sur ces parents (champ `parent` de `factices.json`).
- **Écueil majeur :** le jeu lit les propriétés « sans versions », par leur **numéro d'ordre** dans la classe. Une souche dont l'ordre diffère ferait lire des valeurs fausses **[UE courant]**.
  - L'ordre réel est donné par `acr-ref schema <Type>` (« usmap property indices (unversioned serialization order) ») **[ACR-XS : commande présente]**, ou par le kit C++ que génère Dumper-7.
  - Règle de prudence : ne régler sur ces acteurs que leur position, et les rares propriétés indispensables (`BakedData` du TrackAvatar, la table de notes du PacenoteSetupActor). Laisser tout le reste à sa valeur par défaut, qui n'est alors pas écrite.
- **Travail :** 2 à 5 jours. **Risque élevé.** C'est la voie la plus proche de BioBio, dont la notice parle de « modèles d'acteurs » et de fichiers qui « suivent la disposition de ceux du jeu » **[BioBio]**.

**2. Voie hybride H (repli recommandé si E2a échoue, ou si E2b s'enlise).**
- On garde la partie jeu que l'étape 1 sait déjà produire dans un clone de Hafren South : physique, tracé, chronométrage, notes, remise en piste, ciel, inscription aux menus. C'est la voie « ajout » d'ACR Extra Stages, `acr-additive relocate` **[ACR-XS]**.
- L'éditeur ne sert plus qu'à cuire des éléments **de classes du moteur** (StaticMesh, Texture2D, variantes de matériaux), sans aucune souche.
- On fait désigner nos éléments par les composants existants du clone :
  - les 87 `TrackTile` de Hafren (composants `Terrain_0` / `Road_0`) **[ACR-XS, anatomy]** désigneraient nos dalles et nos tronçons de route, à nos positions ;
  - les forêts du niveau, composants d'instances, recevraient nos arbres avec le maillage `SM_AleppoPine…`.
- **À écrire :** une petite retouche de leur outil, qui change l'élément désigné par un composant et sa position. Leur code fait déjà l'équivalent pour les forêts : `HismRewrite.cs` réécrit les instances, et `TreeInstancer.cs` change le maillage désigné pour le couvre-sol **[ACR-XS : déduit du code]**.
- **Travail :** 2 à 4 jours. **Risque moyen** : les cellules de Hafren se chargent selon la position, il faudra les maintenir chargées ; et le nombre d'instances est limité à la capacité des forêts de Hafren.

**Hauteurs des maillages d'arbres :** à relever une fois, pour l'échelle des arbres. Lancer `acr-ref export acr/Content/Foliage/Trees/AleppoPine/SM_AleppoPine14.uasset …` pour chacun des 45 maillages et lire les bornes, ou mesurer dans FModel **[UE courant]**. Écrire le résultat dans `pc/etape2_unreal/hauteurs_maillages.json` (`{"SM_AleppoPine14": 1450.0}`, en cm), que lit `poser_arbres.py`.

## 5. E3 : une dalle de terrain avec sa photo (½ à 2 jours)

**But :** afficher une dalle de 500 m de notre terrain avec son image aérienne, d'abord simplement, puis avec un matériau de terrain du jeu pour retrouver le relief fin et les reflets.

1. **E3a (sûr) :**
   - importer une dalle avec `scripts_editeur/importer_dalles.py`, qui lit `data/processed/textures_sol.json` s'il existe, sinon `modele/terrain.glb` ;
   - la poser dans `GC_Essai` (E2a), ou dans le clone de la voie H ;
   - elle reçoit une variante de `M_Simple` portant sa photo.

   **Le script contrôle le repère :** il compare les bornes importées aux bornes attendues (UE = 100 × (gX, gZ, gY)) et écrit « REPÈRE CONFORME » ou « REPÈRE DIFFÉRENT ». La conversion d'axes de l'importeur glTF d'Unreal **n'est pas connue avec certitude** **[à vérifier : documentation Interchange / glTF d'Epic]**. En cas d'écart, régler la transformation d'import, ou pivoter les acteurs, selon le verdict.
2. **E3b (beau) :** une variante d'un matériau de terrain du jeu. Candidats, avec leurs chemins dans `elements_jeu_utiles.json` :
   - `M_TerrainMaster_light`, le parent probable des 68 variantes de dalles de Bollène `MI_TerrainMatBlend1001…`. Chez Hafren, ce sont des mélanges de 9 matériaux pilotés par des masques par dalle `T_…_M1/_M2`, en **textures virtuelles** **[ACR-XS, visuals-plan]** ;
   - `M_RoadSurface_Layered` et `M_AsphaltMaster_Adv` pour la route ;
   - les variantes d'asphalte de Bollène et Sisteron, `MI_BolleneAsphaltRoadside…` ;
   - les textures de sol de Monte-Carlo : `T_Dried_Grass`, `T_Pine_Needles`, `T_Stones_On_Soil`, `T_Dirt_Ground`…

   **Nous n'avons que des noms.** Sur le PC :
   - `acr-ref export <variante>.uasset --out x.json` donne son **Parent**, ses `TextureParameterValues`, `ScalarParameterValues` et `StaticParameters` **[ACR-XS : outil présent ; noms de champs habituels de CUE4Parse, à vérifier dans la sortie]**. FModel les montre aussi **[UE courant]** ;
   - recréer le factice du parent avec **les mêmes noms de paramètres** (compléter `factices.json`) ;
   - faire des variantes de **variantes** du jeu quand c'est possible (le parent d'une variante peut être une variante) **[UE courant]** ;
   - si le parent échantillonne des textures virtuelles, activer leur prise en charge dans le projet et dans nos textures **[à vérifier : « Virtual Texturing » dans la documentation Epic]**.

**Ce qu'on doit voir :** la dalle à sa place, bien raccordée à la route (même sommets de bord, `modele/`), la photo nette à 2048 px pour 500 m.

**Conclusions :**
- **Photo rose ou délavée :** problème de sRGB ou de paramètre.
- **Le rendu à plat suffit :** généraliser E3a et garder E3b pour plus tard.
- **E3b réussit :** reprendre ce modèle pour toutes les dalles.

## 6. E4 : 200 m complets, puis toute la spéciale (2 à 5 jours, puis la généralisation)

**But :** les 200 premiers mètres jouables et beaux : route, bords et marquage, 2 dalles, arbres en instances, parapets, physique.

1. **Physique et partie jeu :** celles de l'étape 1, construites par leur outil `stage-build` (sol, obstacles, tracé, notes, chronométrage) **[ACR-XS]**.
   - Voie H : c'est le clone de Hafren lui-même.
   - Voie A : le `BakedData` du clone est déplacé à notre chemin par `acr-additive relocate` et désigné par notre `BC_TrackAvatar` souche. Les tracés et déclencheurs restent à refaire dans notre niveau : c'est le principal coût de la voie A.
2. **Accord du décor et de la physique.** Leur outil a choisi un placement (rotation θ et translation), écrit dans le rapport `…\construction\stage-grandcaunet.report.json`, rubrique `placement`. Notre décor doit être posé dans **le même** repère : mode « acrxs » de `repere_unreal.py`, option `--placement` de `poser_arbres.py`. La formule, recopiée de leur `StageBuild.Placement.ToPhysics` **[ACR-XS]**, est :

   ```
   physique = R_y(θ) · (ir − (cx, 0, cz)) + (tx, dy, tz)
   UE cm = 100 · (px, pz, py)
   ```
3. **Route :** `modele/route_habillee.glb` (enrobé, marquage), avec une variante d'un asphalte du jeu (E3b), sans collision Unreal. La physique vient du BakedData seul **[ACR-XS, D4 : vérifié en jeu]**. Marquer les acteurs « NoCollision ».
4. **Arbres :**

   ```
   poser_arbres.py --placement <rapport> --pk-min 0 --pk-max 200
   ```

   **Point de contrôle (mode propre)**, avec le repère du 11/11/2026 : le premier arbre de `arbres.csv`, un pin d'Alep en Lambert-93 (916 565,25 ; 6 243 787,75 ; sol 231,24 m), doit tomber en UE **(−44 324,0 ; −275 715,0 ; −16 731,0) cm**. Pour recalculer après un changement de repère : `python3 scripts_editeur/repere_unreal.py`.
5. **Ouvrages et balisage :** `modele/ouvrages.glb` (parapets), `modele/balisage.glb`. Les piquets et la rubalise du jeu existent aussi (rubrique `rubalise_piquets`).

**Ce qu'on doit voir :** sur 200 m, la voiture roule sur le bon sol (physique) exactement sous la route dessinée, les arbres sont aux bons endroits (comparer à l'orthophoto), la fréquence d'images est correcte.

**Contrôles visuels :**
- un décalage constant entre route dessinée et route physique : erreur de placement (θ ou translation) ;
- un miroir : erreur d'axe (glTF vers Unreal) ;
- des arbres au milieu de la route : cap ou échelle.

**Généralisation :**
- 26 dalles, ou celles de `terrain_sol.glb` ;
- toute la route, et l'anneau lointain `lointain.glb` ;
- les 41 584 arbres, en instances regroupées par maillage, ce qui fait 45 composants ;
- le ciel de Monte-Carlo (`BC_DMSky_Montecarlo_Bollene`) et sa météo (`DA_MonteCarloWeatherConfig`) ;
- Nanite pour le terrain si E1 l'a validé.

**Écueils de E1 à E4 [UE courant, sauf mention] :**
- **Version d'objet :** un paquet cuit par une autre version mineure est refusé ou plante. D'où la version 5.6.1 exacte.
- **Classes du jeu absentes du projet** (`/Script/acr`, `/Script/dmphysics`, Blueprints `BC_*`) : souches ou voie H (E2b). Les éléments de classes du moteur (StaticMesh, Texture2D, MaterialInstanceConstant) n'en ont pas besoin.
- **Programmes d'affichage :** seulement des variantes, sans changer de « static switch ». Aucun matériau maître n'est livré.
- **World Partition :** BioBio s'en passe **[BioBio]**. Hafren l'utilise **[ACR-XS]**. Commencer sans.
- **Nanite :** le jeu s'en sert **[ACR-XS, anatomy]**. Commencer sans, l'essayer ensuite.
- **Lumen et éclairage :** les réglages de rendu sont ceux du jeu ; le ciel et la lumière viennent des acteurs du niveau. Ne rien précalculer.
- **Collisions :** désactivées sur tout notre décor. La physique ne vient que du BakedData **[ACR-XS, vérifié en jeu]**. Le jeu sait aussi rassembler des collisions à l'exécution **[ACR-XS, anatomy § 3 : existe dans le binaire, interaction non étudiée]** : raison de plus pour tout mettre en « NoCollision ».
- **Registre des éléments du jeu :** nos éléments neufs n'y figurent pas. ACR Extra Stages s'en passe pour ses niveaux clonés **[ACR-XS : captures du README ; marqué non vérifié dans additive-plan § 6]**.

## 7. Voie B de repli : sans éditeur

Si l'éditeur ne produit rien d'acceptable (E1), on écrit nous-mêmes le contenu cuit, avec les outils d'ACR Extra Stages. Beaucoup existe déjà **[ACR-XS : déduit du code, construit hors jeu]** :

- **Terrain photographié : 1 à 2 jours.** Leur affichage v1.11 dessine déjà un sol découpé en tuiles, **une texture et une variante de `M_Simple` par tuile**. C'est notre besoin.
  - Il faut leur fournir `render/terrain.glb` (notre `modele/terrain.glb` y ressemble) et un manifeste `render/ground_bake/manifest.json` (format dans `docs/stage-ir.md`, « ground_bake ») avec nos photos en DDS BC1.
  - L'outil `texconv` de Microsoft (DirectXTex) fait la conversion **[supposé : outil officiel, non essayé]**.
  - Limite : un seul composant de maillage « procédural », sans niveaux de détail. La fréquence d'images est à surveiller.
- **Arbres du jeu : 2 à 3 jours.** On réécrit les forêts de Hafren (`HismRewrite`) en changeant leur maillage pour `SM_AleppoPine…`, sur le modèle de ce que leur code fait pour le couvre-sol. La limite est la capacité des forêts de Hafren.
- **Vrais maillages statiques cuits** (rendu de qualité, niveaux de détail) : plusieurs semaines. Il faut écrire les données de rendu d'un `UStaticMesh` 5.6 (tampons de sommets, LOD, éventuellement Nanite). Rien n'existe pour cela **[ACR-XS, D5 : « very hard / unproven »]**.

## 8. Les inconnues qui décident de tout

1. **Le jeu accepte-t-il du contenu cuit par un Unreal 5.6.1 du commerce ?** Lui sort d'un moteur compilé par le studio (« +UE5-acr »), et le contenu passe par retoc. Réponse : E1a.
2. **Une variante dont le parent est un factice se lie-t-elle au vrai matériau** et à ses programmes d'affichage ? Réponse : E1b.
3. **Un niveau simple à nous, inscrit aux menus, est-il chargé, et que lui faut-il au minimum ?** Réponse : E2a.
4. **Des acteurs de classes du jeu sont-ils possibles sans posséder ces classes ?** Il faudrait des souches au même ordre de propriétés. Sinon, voie hybride H. Réponse : E2b.
5. **Les paramètres réels des matériaux de terrain et d'asphalte** (textures virtuelles comprises), pour un rendu à la BioBio et non à plat. Réponse : E3b, après lecture sur le PC.

**Question à poser au directeur :** autorise-t-il à **lire** (sans rien en reprendre) la structure du niveau de BioBio installé, ses acteurs et leurs classes ? Cela répondrait directement aux inconnues 3 et 4.

## 9. Fichiers du kit

| Fichier | Rôle | État |
|---|---|---|
| `PROTOCOLE.md` | ce document | |
| `elements_jeu_utiles.json` | 27 rubriques : arbres par essence (pin d'Alep, arbre à perruque, érables pour les chênes, pins noirs, cyprès, oliviers…), herbes sèches, asphaltes et terrains de Monte-Carlo, matériaux maîtres, murs, ponts, rochers, glissières, panneaux français, rubalise, portiques, ciels et météo, surfaces physiques, acteurs de niveau, tables, niveaux | régénérable : `outils/extraire_elements.py` |
| `factices.json` | 60 factices, tous présents au catalogue | régénérable : `outils/liste_factices.py` |
| `scripts_editeur/repere_unreal.py` | conversions Lambert-93, glTF, Unreal, point de contrôle | testé en Python ordinaire, jamais dans Unreal |
| `scripts_editeur/creer_factices.py` | crée les factices | jamais exécuté |
| `scripts_editeur/importer_dalles.py` | importe les dalles, crée leurs variantes, contrôle le repère | jamais exécuté |
| `scripts_editeur/poser_arbres.py` | pose les arbres en instances | jamais exécuté ; création de composant à vérifier |
| `scripts_pc/cuire_et_empaqueter.ps1` | cuisson, tri des factices, retoc | jamais exécuté ; options de cuisson à vérifier |
