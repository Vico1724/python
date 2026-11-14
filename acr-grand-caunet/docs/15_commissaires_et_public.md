# 15. Commissaires et public : comment le jeu les place, comment en mettre chez nous

Étude du 14/11/2026, en lecture seule. Rien n'a été modifié dans le jeu, dans `Z:\acrxs\acr-extrastages` ni dans le projet Unreal. Les deux scripts d'essai sont dans le dossier de travail de la session (voir l'annexe).

## En bref

- **Les commissaires et le public du jeu sont des acteurs posés dans les niveaux.** Le jeu ne les crée pas lui-même à partir d'une table. Ce sont des Blueprints (`BC_Marshal`, `BC_HighResCrowd`, `BC_CrowdSystemSpawnerBakedActor`…), posés un par un par le studio. Leur classe native est dans le module `/Script/acr` du jeu. Ils dépendent de gestionnaires communs (`MarshalsManager`, `BC_CrowdSystemManager_Wales`) placés dans le niveau persistant.
- **Notre cellule hôte `1LS8FPM8JIMX697U3QIPKC01K` n'en contient aucun** : 6 rubalises, 5 piquets, rien d'autre. Les commissaires et le public de Hafren South sont dans d'autres cellules du sens aller, que l'étape 1 empêche de charger.
- **Nos factices ne connaissent aucune de ces classes, et ne peuvent pas les connaître en l'état.** Un factice de Blueprint exige sa classe native ; notre projet n'a pas de module C++. Le 14/11, les 11 Blueprints de `BLUEPRINTS` ont tous été ignorés par `creer_factices.py`. `v_poser_classe` ne pose d'ailleurs que des classes du moteur (lumières, `Actor` vide). Poser un commissaire depuis `construire_niveau.py` demanderait donc des classes souches en C++ : risque élevé.
- **Méthode recommandée : déplacer des personnages qui existent déjà.** Le niveau persistant de Hafren South porte, au parc d'assistance (X ≈ 3,25 km, Y ≈ 1,16 km, hors de notre zone), **4 commissaires et 6 spectateurs**. Ils sont chargés en permanence, animés, entièrement habillés, et personne ne les voit sur notre spéciale. L'étape 1 réécrit déjà ce paquet. Les déplacer revient à réécrire sur place leur position et leur lacet, comme `acr-ref stage-build` le fait déjà pour le départ, les secteurs et l'arrivée. **Essai hors jeu : 10 sur 10 sont déplaçables de cette façon.**

## 1. Ce que fait le jeu

### 1.1 Les familles de personnages

| Famille | Classe posée (Blueprint) | Classe native (`/Script/acr`) | Où dans Hafren South | Animé par |
|---|---|---|---|---|
| Commissaire « décor » | `BC_Marshal_C` | `MarshalCharacter` → `HighResCrowdCharacter` → `CustomizableCrowdCharacter` → `CrowdCharacter` → `Actor` | 92 dans 26 cellules, 4 dans le niveau persistant (parc d'assistance) | un Blueprint d'animation choisi selon l'accessoire (`AB_MarshalStanding`, `AB_MarshalRadioNew`, `AB_MarshalCamera`…) |
| Officiels du départ et de l'arrivée | `BC_MarshalStartEndSequencePC_C`, `…Doc_C` (assis à une table) ; `BC_StopMarshalStartSequence_C`, `BC_StopMarshalEndSequence_C` (debout, bâton) | les mêmes, plus `GenericMarshalStartEndSequenceComponent`, `MarshalStartSequenceComponent`, `MarshalEndSequenceComponent` | cellules A0I1 (départ) et 0QY7 (arrivée), à 1 à 3 m des déclencheurs de départ et d'arrivée | `AB_MarshalStartEndSequence`, piloté par la séquence de départ ou d'arrivée |
| Spectateur haute définition | `BC_HighResCrowd_C`, `BC_HighResCrowd_Spline_C` (il marche le long d'un tracé) | `HighResCrowdCharacter` | 6 + 3, tous dans le niveau persistant (parc d'assistance) | comme les commissaires |
| Public de masse (lointain) | `BC_CrowdSystemSpawnerBakedActor_C` | `CrowdSystemSpawnerBakedActor` (système Mass) | 104 groupes dans 25 cellules | matériau (texture d'animation), données par personne fournies par le gestionnaire de foule |
| Accompagnants | `BC_CrowdManagedAmbientSound_C` (bruit de foule), `BC_CrowdEscapeReaction_C` (fuite quand la voiture arrive) | — | à côté des groupes de public | — |

### 1.2 Un commissaire, en détail

Exemple : `BC_Marshal16` (cellule 0QY7, photographe à genoux). L'acteur porte :

- des **noms** qui décrivent son apparence : `HeadType` « Head004 », `BodyType` « AutumnMale », `HatType` « Hat », `PropType` « Camera », `BodyCustomization` « PhotographerOrange », `ClothesCustomization` « Autumn_03 », `HatCustomization` « Grey », `MeshType` ;
- une **pose de tête** (`HeadPoseAsset` → `AS_Marshal_Head_004_PoseAsset`) ;
- un **jeu d'animations** (`AnimationSetConfig` : `DA_MarshalCameraAnimations`, condition « Kneeling ») ;
- quatre **sous-objets `CustomizableCrowdCharacterAccessory`** (corps « AutumnMale » et couleurs, cheveux « HatHair004 », casquette et couleur, appareil photo), sans transformation propre ;
- un **composant racine `BodySkeletalMesh`** (`CrowdSkeletalMeshComponent`, créé par la classe native). Il porte la position (`RelativeLocation`, `RelativeRotation`), la tête `SK_Marshal_Head_004`, ses 5 matériaux et la classe d'animation `AB_MarshalCamera_C` ;
- trois composants du Blueprint : `CrowdCharacterRespawnBox` (boîte de 53 × 53 × 218 cm), `Decal` (ombre au sol, `M_CrowdGroundAO`) et `CustomizableCrowdCharacterAnimation`.

Le corps, les vêtements, les cheveux et l'accessoire ne sont pas des composants posés. Ce sont des noms. Le jeu les résout au lancement à partir des données de `SetupDataAssetTag` « MarshalsSetup » (`DA_MarshalsSetup_*`, `DA_MarshalBody_*`, `DA_MarshalsAddMeshGroups_*`…), fournies par le gestionnaire de foule du niveau persistant. Le Blueprint tire en plus les cheveux au hasard au lancement (`AccessoriesGroups` → Hair, `bRandomizeAtBeginPlay`).

**Aucun lien avec le tracé ni avec une table de données.** Un `BC_Marshal_C` ne référence ni le tracé de la course, ni un déclencheur, ni une `DataTable`. Il est posé où le studio l'a posé, face à la route.

### 1.3 Les officiels du départ et de l'arrivée

Ils sont liés au déroulé de la course :

- `BC_StopMarshalStartSequence_C` (cellule A0I1, à 3 m du `BC_StartSequenceTrigger` de la cellule 22VG) porte deux `ChildActorComponent`, « Start » et « ComeCloser ». Chacun contient un `SplineEventTrigger`, posé 79 m et 35 m en arrière du commissaire : c'est lui qui fait signe d'avancer ;
- `BC_MarshalStartEndSequenceDoc_C` est assis à une table, à 2,6 m du point de départ de la voiture (`BC_CompleStartTargetPoint`). `BC_MarshalStartEndSequencePC_C` (arrivée) a une chaise, une table et un portable en `StaticMeshComponent` ;
- `BC_StopMarshalEndSequence_C` se tient à 3 m du `BC_EndSequenceTrigger` (zone d'arrêt, cellule 0QY7).

Rectification de `acr-stage-anatomy.md` : dans le sens aller, le départ est en (−853 ; 901) m et la zone d'arrêt en (295 ; −799) m. Le document d'ACR Extra Stages donne la seconde position pour le départ.

### 1.4 Le public de masse

Un `BC_CrowdSystemSpawnerBakedActor_C` est un groupe de spectateurs. Son `BakedSpawnData` est la liste des personnes : transformation relative à la racine du groupe, `RepresentationId` (« Nathan_Autumn »…), accessoires (parapluie, téléphone), couleurs, groupe d'animation, attributs. Le système Mass (`CrowdSystemMassSpawnExecutorComponent` du `BC_CrowdSystemManager_Wales`) dessine ces personnes avec les maillages `SM_*_Generated`, animés par leur matériau. C'est pour cela que ces maillages, posés seuls, prennent une allure imprévisible (constat du premier agent, `mobilier_bord_de_route.json`).

### 1.5 Où sont les gestionnaires

Dans le **niveau persistant** `WalesS4HafrenSouth` : `BC_CrowdSystemManager_Wales_C` (avec `CrowdSystemSetupProvider`, `CrowdSystemCustomizationDataComponent`, `CrowdSystemMassSpawnExecutorComponent`, `CrowdReplayComponent`), `MarshalsManager`, `CrowdReactionsManager`, `CrowdSplineFollowersManager`, `BC_CrowdSystemParticles_C`. On trouve les mêmes à Bollène et à Sisteron (gestionnaire `_Winter`). L'étape 1 ne les cache pas (`scenery.toml` : « Kept on purpose… managers »). Ils fonctionnent donc déjà dans notre spéciale.

### 1.6 Bollène, pour comparer

La spéciale de Bollène suit la même organisation, en plus dense : 252 `BC_Marshal_C` dans 83 cellules, 335 groupes de public, 25 `BC_GenericMarshalStartEndSequence_C`, 58 `BC_CrowdBarrier_C`. Elle a aussi son gestionnaire de foule dans le niveau persistant.

## 2. Preuves

| Constat | Source |
|---|---|
| Comptes par classe et par cellule (Hafren South, Bollène, niveaux persistants) | exports `Z:\acrxs\unreal\lu\niveau_hafren`, `niveau_bollene`, `niveaux_persistants` (faits par `relever_jeu.py` sur la vue d'origine), relus par `tally.py` et `positions.py` |
| Classe native `MarshalCharacter` et sa lignée de propriétés (1 + 37 + 34 + 18 propriétés propres, puis `Actor`) | `acr-ref schema --usmap Z:\acrxs\mappings\acr_25170642.usmap MarshalCharacter …` |
| Propriétés et composants des Blueprints | `Z:\acrxs\unreal\lu\exports\acr\Content\Data\{Marshals,Crowd,HighResCrowd}\…\BC_*.uasset.json` |
| Couches de données des cellules (BE01 = gameplay aller, E8A3 = accessoires aller, B42F et C2CD = retour) | objets `WorldPartitionRuntimeLevelStreamingCell` de l'export du niveau persistant |
| Cellules cachées par l'étape 1, gestionnaires et parc d'assistance gardés | `Z:\acrxs\acr-extrastages\config\scenery.toml`, `docs\decisions.md` (v1.6) |
| Factices Blueprint tous ignorés | `Z:\acrxs\unreal\acr\Saved\Logs\acr-backup-2026.11.14-07.52.19.log` : « factice Blueprint … ignoré : classe native … absente du projet » ; pas de dossier `Source`, `Binaries` ni `Content/Data` dans le projet |

### Cellules de Hafren South qui portent des commissaires (sens aller)

| Cellule | Couche | Contenu |
|---|---|---|
| `A0I1JHQ2458PSST2XD0UTWQ2I` | aller (BE01), chargée par la distance | départ : 5 `BC_Marshal_C`, l'officiel assis (Doc), le commissaire au bâton, 2 portiques, 2 `SplineEventTrigger` |
| `0QY7AIYF1F7BYQ1BH0V2NX22R` | aller | arrivée : 5 `BC_Marshal_C`, l'officiel au portable, le commissaire d'arrêt, 6 groupes de public, 7 bruits de foule, 1 portique |
| `7O80TL828EEN9GFVUZH00HQYQ` | aller | 3 `BC_Marshal_C` (radio, gilets orange), rien d'autre |
| `5OWDW4K89KK8XU0UCXUHKR78W`, `3QGF4ZWWA88EGPQ71ZPXHEPTY` | aller et retour | 13 et 7 `BC_Marshal_C`, 22 et 9 groupes de public |
| `CMMRC9I7LCHK2G94JP8IEPCS0`, `C3QS21PSH8A7XG8BQEKKHI66O` | aller | 6 et 5 `BC_Marshal_C`, objets physiques (`BC_PhysicsActor_C`) |
| niveau persistant | toujours chargé | parc d'assistance : 4 `BC_Marshal_C` (photographe qui parle, radio, tablette, gilet orange), 6 `BC_HighResCrowd_C` (tenues de printemps, l'un avec un appareil photo), 3 `BC_HighResCrowd_Spline_C` |

## 3. Notre cellule hôte

Export de la cellule d'origine (`…\_Generated_\1LS8FPM8JIMX697U3QIPKC01K.umap.json`, 38 objets) : 6 `BC_NarrowTapeActor_C`, 5 `TapePoleActor`, 2 `BC_TapeHandleActor_C` (rubalises de Hafren), un `SplineSpawnerRoot`, plus le monde et le niveau. **Aucun commissaire, aucun public.** Il n'y a donc rien à récupérer dans cette cellule. Comme notre décor la remplace entièrement, ces rubalises galloises n'existent déjà plus dans notre version.

Les commissaires de Hafren sont dans les cellules du tableau ci-dessus, placés pour le tracé gallois. Le départ de Hafren est à 2,4 km du nôtre (notre PK 0 est en UE (1155 ; 1407 ; 516) m, d'après `releves/placement_etape1.json`). L'étape 1 range ces cellules dans les couches du sens retour (`scenery.toml`), si bien qu'elles ne se chargent plus. Seuls restent chargés les 10 personnages du niveau persistant, au parc d'assistance, qui est en dehors de l'emprise de notre spéciale (X max 1,7 km).

## 4. Méthodes examinées

| | Méthode | Animé | Ce qu'il faut | Risque |
|---|---|---|---|---|
| **A** | **Déplacer les 10 personnages du niveau persistant** (réécriture sur place de leur position et de leur lacet par l'étape 1) | oui, exactement comme dans le jeu | une retouche `pc/patches/0005-…` de `acr-ref stage-build`, une liste de positions | **faible** |
| B | Comme A, avec en plus les officiels de départ et d'arrivée et les commissaires des cellules A0I1, 0QY7 et 7O80 | oui, et les séquences de départ et d'arrivée | garder ces cellules chargées, les rendre « toujours chargées », déplacer leurs acteurs, enfoncer ou cacher le reste (portiques, public, bruits) | moyen |
| C | Poser des `BC_Marshal` dans notre cellule depuis `construire_niveau.py` | si tout est juste | classes souches C++ (module `acr`, Visual Studio, à installer avec accord), factices Blueprint complets, apparence à recopier à la main | **élevé** |
| D | Statues : maillages squelettiques du jeu figés en `StaticMesh` | non | exporter les `SK_Marshal*`, les poser, les importer, les cuire dans notre paquet | faible techniquement, mais cela redistribue de la géométrie du jeu dans notre conteneur, et le résultat est immobile ; écarté |
| E | `SM_*_Generated` en instances simples | non, ou mal | — | écarté (premier agent) |

Pourquoi C est risqué. Dans notre paquet cuit, l'acteur serait de classe `/Game/Data/Marshals/Blueprints/BC_Marshal.BC_Marshal_C`. Au chargement, c'est la vraie classe du jeu qui est prise (le factice n'est pas empaqueté, comme pour les maillages). Mais il faudrait que les sous-objets de notre acteur correspondent à ceux de la vraie classe : le composant natif `BodySkeletalMesh` (`CrowdSkeletalMeshComponent`), les trois composants du Blueprint avec leurs noms exacts, les accessoires. Sinon, l'archétype n'est pas trouvé, au mieux l'acteur est vide, au pire le jeu plante. Notre cuisson est « avec versions » : les propriétés sont écrites par leur nom, ce qui épargne le piège de l'ordre des propriétés. Restent les classes natives, absentes. En outre, l'apparence (tête, matériaux, accessoires) est préparée dans l'éditeur du studio par le script de construction natif. Notre souche ne l'exécuterait pas : il faudrait recopier ces valeurs nous-mêmes.

## 5. Méthode proposée (A, puis B si le directeur veut les séquences)

### 5.1 Principe

Le niveau persistant `acr/Content/Levels/WalesS4HafrenSouth.umap` fait déjà partie du conteneur de l'étape 1 (`zz_acrxs_grandcaunet_P`), puisque `Scenery.Build` le réécrit. Pour chacun des 10 personnages, on remplace dans l'export de son composant racine `BodySkeletalMesh` :

- les trois doubles de `RelativeLocation` par la position voulue (UE, cm, repère du clone) ;
- le double « Yaw » de `RelativeRotation` par le cap voulu.

C'est exactement la technique de `StageBuild.cs` (lignes 700 à 720, `FindDoubles` puis `WriteDoubles`) pour le point de départ, les déclencheurs et les secteurs : même taille d'export, aucun en-tête modifié, aucune nouvelle classe ni importation. La boîte de réapparition et l'ombre au sol sont attachées à la racine : elles suivent. Les accessoires n'ont pas de position propre : le corps, les cheveux et l'objet sont accrochés au squelette au lancement.

**Essai hors jeu, fait** (`essai_deplacement.py`, sur `Z:\acrxs\construction\mod\…\WalesS4HafrenSouth.umap`, le niveau persistant produit par l'étape 1) : pour les 10 composants racines (exports n° 612 à 617 et 621 à 624, 105 octets chacun), la position apparaît **une seule fois** et la rotation **une seule fois** dans les octets. La condition de `FindDoubles` est donc remplie. Les 10 ont un lacet non nul, donc une rotation déjà écrite que l'on peut remplacer. Il ne faut pas en ajouter.

### 5.2 Répartition proposée

Il y a 10 personnages pour 16 souhaités dans `commissaires_et_public_non_poses` (méthode B pour en avoir plus) :

| Place (`mobilier_bord_de_route.json`) | Personnage du parc d'assistance |
|---|---|
| PK 1, droite, 2,5 m : officiel debout derrière le chevalet | `BC_Marshal113` (gilet orange, debout) |
| PK 27, droite, 1,5 m : 2 spectateurs | `BC_HighResCrowd`, `BC_HighResCrowd3` |
| PK −20, droite, 4 m : 2 officiels sous la tonnelle | non pourvu en A (ils sont assis ; à prendre en B, ou à remplacer par 1 debout) |
| PK 3650, Lion d'Or : 2 gilets jaunes + 1 chasuble orange | `BC_Marshal111` (radio), `BC_Marshal112` (tablette), `BC_Marshal110` (photographe orange, qui parle) |
| PK 6509, gauche, 3 m : commissaire en chasuble + 2 personnes en sombre | `BC_HighResCrowd4`, `BC_HighResCrowd6` (le commissaire : en B) |
| PK 6573, gauche, 3 m : 4 spectateurs sur le talus | `BC_HighResCrowd2` (appareil photo), `BC_HighResCrowd5` |
| PK 6736 : chronométreur | en B |

Les 3 `BC_HighResCrowd_Spline_C` marchent le long d'un tracé du parc d'assistance. On les laisse sur place.

### 5.3 Données

Positions calculées une seule fois, dans `scripts/mobilier.py`, à la manière des autres objets de bord de route :

- nouvelle fonction `personnages(route=None)`. Pour chaque entrée de `commissaires_et_public_non_poses.liste`, elle prend `route.point(pk, cote, decalage)` et `route.z_terrain(...)`, écarte les personnes d'une même entrée de 0,8 à 1,2 m le long de la route (`alea(pk, k)` pour un écart reproductible), puis oriente chacune vers l'axe de la chaussée. On ajoute à chaque entrée du JSON un champ `personnages` : une liste de noms d'acteurs du jeu (`"BC_Marshal113"`…), ou un nombre si l'on veut laisser la répartition au script ;
- **`scripts/09_export_stage_ir.py`** écrit une rubrique de `export/stage_ir/grand_caunet/stage.json`, lue par l'étape 1. Elle est dans le même repère que les `triggers` (mètres, X est, Y altitude, Z sud) :

  ```json
  "characters": {
    "source": "data/reference/mobilier_bord_de_route.json, commissaires_et_public_non_poses",
    "host": "WalesS4HafrenSouth persistent level",
    "items": [
      {"actor": "BC_Marshal113", "class": "BC_Marshal_C", "role": "officiel du départ", "pk_m": 1.0,
       "position": [x, y_sol, z], "forward": [fx, 0, fz]}
    ]
  }
  ```

  `forward` est la direction du regard. `actor` est l'étiquette relevée dans l'export ; la retouche la retrouve par le nom d'export complet (`BC_Marshal_C_UAID_…`), plus stable, recopié dans une table de la retouche ;
- **`scripts/16_paquet_unreal.py`** ne pose rien, mais recopie la même liste dans `paquet_unreal/manifeste.json`, rubrique `"personnages"`, avec `"pose_par": "étape 1 (acr-ref stage-build, niveau persistant)"`. Il peut ajouter un repère dans l'aperçu (`modele/apercu/…`), pour que la relecture du décor (`relire_decor.py`) puisse dire où ils seront. **`construire_niveau.py`, `liste_factices.py` et `creer_factices.py` ne changent pas** dans la méthode A.

### 5.4 La retouche de l'étape 1 (`pc/patches/0005-personnages.patch`)

Elle est appliquée par `pc/scripts/2_recuperer_acrxs.ps1` comme les quatre autres. Rien n'est modifié directement dans `Z:\acrxs\acr-extrastages`.

1. Nouvelle option de `stage-build`, `--characters 1`, ou lecture automatique de `stage.json → characters` quand la rubrique existe.
2. Juste après `Scenery.Build`, qui vient d'écrire le niveau persistant (ligne 189 de `StageBuild.cs`) : rouvrir ce paquet (`LegacyPackage`), trouver pour chaque nom d'export son `RootComponent`, puis remplacer :
   - la position, convertie par le même placement que les déclencheurs (`pl.ToUe(position)`) ;
   - le lacet, `atan2` de `forward` passé dans le repère UE.
   Enregistrer ensuite, et inscrire chaque déplacement dans la rubrique `actors` du rapport (`stage-grandcaunet.report.json`).
3. Contrôle dans `stage-check` : relire chaque racine et vérifier position et lacet, à 1 cm et 0,1° près.
4. `4_construire.ps1` : rien à ajouter si la lecture est automatique.

`relever_placement.py` n'est pas concerné : le placement ne change pas.

### 5.5 Ce qui sera animé

Tout : l'attitude au repos de chaque personnage (radio, tablette, photographe qui parle, spectateurs debout), les cheveux tirés au hasard au lancement, les réactions aux sorties de route si le jeu les déclenche pour ces classes. Ils n'arrêtent pas la voiture : la physique de l'étape 1 ne les connaît pas. Avec le jeu d'origine, c'est la boîte de réapparition (`CrowdCharacterRespawnBox`) qui gère le cas où une voiture les touche **[à voir en jeu]**.

## 6. Risques

| Risque | Gravité | Parade |
|---|---|---|
| Le personnage flotte ou s'enfonce : notre altitude (`mnt_couloir_1m.tif`) et le sol physique de l'étape 1 diffèrent de quelques centimètres | faible | prendre `max(terrain, bord de chaussée − 1 m)` comme le mobilier ; contrôler sur une capture ; corriger la hauteur entrée par entrée |
| Un gestionnaire (budget d'animation, distances d'affichage) se fonde sur l'emplacement d'origine | faible | aucun indice dans les propriétés relevées ; à voir en jeu |
| Le personnage regarde du mauvais côté (signe du lacet, repère gauche d'UE) | faible | même conversion que les déclencheurs ; vérifier le premier en jeu |
| La saison des tenues (automne et printemps gallois) ne correspond pas à notre rallye | esthétique | à accepter, ou en B prendre des commissaires d'autres cellules |
| Trop peu de personnages (10 pour 16) | — | méthode B |
| Méthode B : les `SplineEventTrigger` enfants du commissaire au bâton ne suivent pas, ou sont liés au tracé de Hafren | moyen | commencer par les officiels assis (Doc, PC), sans déclencheur ; déplacer les déclencheurs comme les acteurs de 22VG, par projection sur la ligne de course (`hostLine.Project` → `newLine.At`) |
| Méthode B : rendre une cellule « toujours chargée » (`bIsSpatiallyLoaded` à zéro) et l'ajouter à `keep` charge aussi ses portiques, son public et ses bruits aux places de Hafren | moyen | les déplacer aussi (les portiques peuvent aller au départ), ou les enfoncer de 1 000 m comme la racine des murs de réapparition en v1 |
| Méthode C (souches) : classe introuvable, factice incomplet, plantage au chargement | **élevé** | ne pas la choisir tant que A ou B suffisent |
| Une mise à jour du jeu change les noms d'export (`…_UAID_…`) | faible | la retouche échoue avec un message clair (`FindDoubles` lève une exception) ; refaire le relevé |

## 7. Étapes

L'essai hors jeu suffit pour la faisabilité ; le premier essai en jeu se fait avec le résultat de l'étape 4.

1. Ajouter `personnages()` à `scripts/mobilier.py`, et le champ `personnages` aux entrées de `commissaires_et_public_non_poses` (§ 5.2).
2. Faire écrire la rubrique `characters` à `09_export_stage_ir.py`, et la rubrique `personnages` du manifeste à `16_paquet_unreal.py`.
3. Écrire `pc/patches/0005-personnages.patch` (§ 5.4), puis refaire `2_recuperer_acrxs.ps1` et `4_construire.ps1 -CellulesDecor 1LS8FPM8JIMX697U3QIPKC01K -ExclureVisuels …`.
4. Contrôle hors jeu : `acr-ref export` du niveau persistant du conteneur produit. Les 10 racines doivent être aux positions voulues, et le reste du paquet identique octet pour octet, hors des 32 octets réécrits par personnage (3 doubles de position et 1 de lacet).
5. Installer, puis faire regarder par le directeur : départ (PK 0 à 30), Lion d'Or (PK 3650), arrivée (PK 6500 à 6600).
6. Seulement ensuite, et si demandé, la méthode B : d'abord la cellule `7O80TL828EEN9GFVUZH00HQYQ` (3 commissaires seuls, aucun autre acteur), puis les officiels de A0I1 et de 0QY7.

## Annexe : scripts d'essai (dossier de travail de la session)

`C:\Users\Clement\AppData\Local\Temp\claude\9a363c87dfa2c7c8\de0a3927-cc94-4a3e-b308-2623eef70d30\scratchpad\comm\` :

- `tally.py` : comptes des classes de personnages par niveau et par cellule ;
- `positions.py` : position et lacet de la racine de chaque commissaire, officiel, spectateur et groupe de public ;
- `essai_classes.py` : classes et assets exigés par un commissaire posé, et présence dans `factices.json` et dans le projet. Résultat : `BC_Marshal`, `BC_StopMarshalStartSequence`, `BC_CrowdSystemSpawnerBakedActor` sont absents des factices et du projet ; leurs composants sont de 4 à 6 classes natives de `/Script/acr` ;
- `essai_deplacement.py` (résultat dans `essai_deplacement.txt`) : les 10 personnages du niveau persistant sont déplaçables par réécriture sur place.
