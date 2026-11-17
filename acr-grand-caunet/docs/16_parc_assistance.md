# 16. Le parc d'assistance : pourquoi il n'apparaît pas, comment en avoir un

> **Mise à jour du 17/11/2026.** L'essai de la dix-septième version a tranché : cas (b), l'écran du parc s'affiche mais le parc est resté au pays de Galles. À la demande du directeur (« très réduit et sommaire, sur la route avant la spéciale si besoin »), la dix-neuvième version pose la seule tente de la voiture et son mobilier (164 acteurs à moins de 8 m) au PK −47, à l'entrée du parking ; le reste est enfoncé. Voir `docs/14`, section 16.3 (retouche 0006, `ServicePark.cs`).

*15 novembre 2026. Étude en lecture seule, faite pendant que le directeur jouait. Rien n'a été modifié dans le jeu, dans `Z:\acrxs\acr-extrastages`, dans le projet Unreal ni dans les scripts du décor. Aucune construction et aucune installation n'ont été lancées. Les scripts d'essai sont dans le dossier de travail de la session (annexe).*

**Constat du directeur.** « Quand je charge la carte, je n'ai aucun parc d'assistance chargé. » Ses vidéos d'essai (13, 14 et 15/11) sont toutes en **Essais libres** : le bandeau du chronomètre affiche « FP ».

## En bref

- **Notre paquet ne retire pas le parc de Hafren.** Dans le niveau persistant de la quinzième version, 459 des 479 acteurs étiquetés `ServicePark` sont identiques à ceux du jeu : tentes, camions, mécaniciens, sol du parc, éclairages, point où la voiture est exposée. Seuls changent 7 bosquets et 6 éoliennes, cachés par l'étape 1, et les 10 personnages déplacés par la retouche 0005. S'y ajoute une cellule de végétation propre au parc, qui ne se charge plus.
- **Le jeu ne montre jamais le parc pendant une spéciale, même sur ses propres spéciales.** Il le fait apparaître seulement sur l'écran « Parc d'assistance », avant la session, et le cache dès qu'on part vers le départ. Dans le jeu d'origine aussi, le parc ne se voit donc pas depuis la route.
- **Cet écran existe en Essais libres, en Contre-la-montre et en Spéciale seule, quelle que soit la spéciale.** En Week-end de rallye, il dépend de chaque étape du programme. Les trois programmes gallois du jeu mettent « pas de parc » devant Hafren Sud aller, c'est-à-dire devant la variante que nous remplaçons. Aucune table ne dit qu'une spéciale « a » ou « n'a pas » de parc.
- **Le parc reste à sa place galloise.** Dans notre monde, cela le met 2,1 km à l'est-sud-est de notre départ. Il flotte de 55 à 105 m au-dessus d'un versant boisé de notre paysage lointain, sans les collines ni les forêts galloises qui l'entouraient.
- **Cause.** Elle ne peut pas être établie sans regarder l'écran d'avant la session. Deux explications restent :
  - (a) l'écran du parc est sauté : Week-end de rallye avec « pas de parc », ou « Recommencer », qui le saute toujours ;
  - (b) l'écran s'affiche avec le parc gallois hors de notre décor, si bien qu'il ne ressemble pas à un parc « chargé » chez nous.

  Un essai de cinq minutes tranche (§ 4).
- **Correction : rien de mis en œuvre.** Déplacer tout le parc près de notre départ est faisable techniquement : les 478 acteurs concernés se réécrivent sur place, essai fait sur une copie. Mais ce n'est pas sûr :
  - aucune zone plate et dégagée assez grande (93 × 125 m) n'existe dans notre décor détaillé près du départ ;
  - le parc se retrouverait dans le monde physique, ce que ne fait aucun des quatre niveaux du jeu examinés ;
  - les volumes sonores et l'ambiance du parc resteraient actifs près de notre départ pendant la spéciale ;
  - et la cause n'est pas encore confirmée.

  La méthode est décrite au § 5.

## 1. Ce que fait le jeu

### 1.1 Quand l'écran « Parc d'assistance » s'affiche

Le déroulé d'une épreuve est décrit par des machines à états (FSM) du jeu. Elles ont été relues dans les paquets d'origine, et les fonctions natives qu'elles appellent ont été désassemblées dans `acr.exe`.

| Étape | Source | Ce qu'elle fait |
|---|---|---|
| `FSM_PreGameGM`, état `Start` | `Data/Fsm/Templates/Race/FSM_PreGameGM` | si `ShouldSkipServicePark`, saute le parc |
| `ShouldSkipServicePark` | bytecode de `FSM_GameGM` | vrai seulement si la dernière étape terminée est `FSM.Flow.QuickRestart` : **« Recommencer » saute le parc** |
| `PerformanceRaceEventBranch` | même FSM | la branche « Performance » (mode de mesure de performances, chaîne `forcePerformanceFlow`) saute le parc ; en jeu normal, branche « Standard » |
| `HasRaceEventServicePark` | fonction native `RaceEventUtilsFunctionLibrary`, code en `0x14636EC60` | prend le composant de réglages de l'épreuve (`RaceEventRaceSettingsComponent`). **S'il n'est pas un `RaceEventRaceSettingsRallyWeekendComponent`, la réponse est « oui ».** Sinon, la réponse est « oui » seulement si la zone d'avant-course de l'étape en cours est de type `SERVICE_PARK` |
| `FSM_RacePCServer` | même chose côté joueur | `HasRaceEventServicePark` mène à `ServicePark` (sinon `StraightToRace`) |
| `FSM_ServiceParkClient` | écran du parc | état `EventInfo` prévu pour Spéciale seule, Contre-la-montre, **Essais libres** et Week-end |

Le composant des Essais libres (`RaceEventRaceSettingsFreePracticeComponent`) dérive de `RaceEventRaceSettingsRallyComponent`, pas du composant de week-end. **En Essais libres, il y a donc toujours un écran « Parc d'assistance » au chargement**, sauf après « Recommencer ».

En Week-end de rallye, la zone d'avant-course est un champ de chaque étape du programme (`DT_RallyWeekendCalendarPreset`, colonne `PreRaceZone` ; `DT_PreRaceZoneConfigurations` : `ServiceParkDefault`, `NoZone`…). Relevé des programmes du jeu :

| Programme | Hafren Sud aller (notre variante) | Hafren Nord |
|---|---|---|
| Rally Wales court, moyen et long (`WalesWeekendShort`, `Medium`, `Long`) | **`NoZone`** dans les 6 entrées où elle figure | `ServiceParkDefault` partout |

Le jeu alterne ainsi : parc, pas de parc, parc. Dans les trois programmes gallois, notre variante tombe toujours sur « pas de parc ». Le joueur peut modifier ce choix dans l'éditeur de programme (`EditServicePark`).

**Rien d'autre ne dit qu'une spéciale a un parc.** `DT_TracksVariants`, la table des variantes, n'a aucune colonne pour le parc : ses colonnes vont de `Name` à `bIsCircuit` et ont toutes été relues. `DT_Tracks` non plus. Le `GameConfigurator` du niveau ne porte que les couches de données des deux variantes (FullForward, FullReverse). Aucune couche de données n'est propre au parc.

### 1.2 Ce qui s'affiche, et quand

- À l'entrée dans l'écran du parc, `FSM_ServiceParkClient` (état `Init`) lance `FsmActionSetActorVisibility` avec l'étiquette `ServicePark`, et la voiture est posée au point `ServiceParkTargetPoint2` (étiquette `ServiceParkTarget`). La caméra tourne autour d'elle (`GarageOrbitCamera`).
- À la sortie (état `Uninit`), la même action est lancée avec `bTargetVisibility = false`.
- La fonction native qui fait ce travail (`0x146360A30`, appelée par `SetupServiceParkActors`) parcourt tous les acteurs du monde. Pour chaque acteur qui porte l'étiquette, elle fait `SetActorHiddenInGame(non visible)`.

**Pendant la spéciale, tous les acteurs étiquetés `ServicePark` sont donc cachés par le jeu**, sur toutes les spéciales. C'est ce qui avait caché les 10 personnages de la quatorzième version (doc 15, retouche 0005).

### 1.3 Le parc de Hafren Sud

Il est entièrement dans le niveau persistant, donc toujours chargé, sauf une cellule de végétation. Il est identique à celui de Hafren Nord : mêmes acteurs, mêmes identifiants. Bollène et Sisteron portent chacun un parc de 286 acteurs.

| Mesure | Valeur |
|---|---|
| Acteurs étiquetés `ServicePark` | 479 : 315 `StaticMeshActor`, 69 décalques, 7 camions d'assistance, 6 tentes de parc, 6 tonnelles, 6 fourgons, 6 mécaniciens, 2 mécaniciens qui marchent, 10 spectateurs et commissaires, 3 spectateurs qui marchent, le copilote, 13 éclairages, 3 volumes sonores, 1 son d'ambiance, 1 volume d'occultation de la pluie, des outils, des pneus… |
| Boîte englobante des 479 acteurs (positions, m, repère UE) | X −2 730 à 4 523, Y −669 à 3 142, Z 484 à 1 015 : **7,3 × 3,8 km**, élargie par 8 « tampons » PCG d'arbres (1,4 à 6,3 km) et 6 éoliennes (110 à 940 m) |
| **Cœur du parc** (455 acteurs à moins de 60 m du point de la voiture) | X 3 218 à 3 295, Y 1 114 à 1 208 : **77 × 94 m** entre les positions des acteurs ; 440 objets posés au sol entre −1,4 et +0,9 m de hauteur : le sol du parc est plat |
| Avec 8 m de marge pour la taille des objets | **93 × 125 m**, environ 1,2 ha |
| Le seul emplacement de la voiture (20 m autour) | 293 acteurs, 38 × 34 m |
| Hors du cœur | 3 volumes sonores (centre à 195 m), zone de ravitaillement (3 acteurs, à 400 m), pylône radio (490 m), sol du parc `SM_WalesServiceParkTerrain` (origine à 110 m) |
| Point de la voiture `ServiceParkTargetPoint2` | UE (3 244,8 ; 1 163,4 ; 543,0) m |

**Le parc est hors du monde physique, dans le jeu d'origine aussi.** La boîte `PhysicsWorldBounds` de Hafren Sud va de −2 048 à 802 m en X ; le parc est à 3 245 m. Il en va de même à Bollène (Y 3 922 contre 2 856 au plus), à Sisteron (X −8 284 contre −3 512) et à Hafren Nord (X −2 106 contre −1 195, Y −2 465 contre −2 053). C'est apparemment voulu : la voiture exposée au parc n'est pas dans la physique de la spéciale.

## 2. Ce que notre paquet change au parc

Le niveau persistant de la quinzième version a été relu dans la vue « jeu + notre conteneur » (`Z:\acrxs\construction\controle\full`). Ses 2 982 objets ont été comparés propriété par propriété au niveau d'origine.

| Élément | Changé ? | Par quoi |
|---|---|---|
| 459 acteurs étiquetés (tentes, camions, mécaniciens, sol, décalques, éclairages, cibles, sons) et leurs composants | **non**, identiques | — |
| 7 « tampons » PCG d'arbres étiquetés `ServicePark` (épicéas, hêtres) | cachés (`bHidden`, composants invisibles) | étape 1, `scenery.toml` → `hide_meshes` (`SM_SpruceWales`, `SM_BeechBare`) |
| 6 éoliennes étiquetées | composants invisibles | étape 1, `hide_actor_classes` (`BC_MyhTurbineA_C`) |
| 10 commissaires et spectateurs | déplacés sur la spéciale, étiquette neutralisée (`ServicePark_0`) | retouche 0005 |
| Cellule `CYMJW2T8N84BTLQFTQK5I4245` (4 `InstancedFoliageActor` étiquetés `ServicePark` : végétation du parc) | ne se charge plus | étape 1 : cellule sans couche, rangée dans la couche « accessoires retour » |
| Collines, forêts et fonds gallois autour du parc (4 dalles de terrain, 87 HLOD, fonds `SM_S4HafrensSouthBG`) | cachés | étape 1 (décor gallois caché) |
| Boîte du monde physique | agrandie à X −2 951 à 1 705 m | `--bounds 1` ; le parc reste dehors, comme dans le jeu |
| Retarget des visuels | non utilisé | voie hybride : pas de `--visuals` |
| Notre conteneur de décor `zz_gc_gc_P` | ne contient que la cellule `1LS8…` et nos assets ; aucun niveau persistant, rien du parc | liste de ses 2 312 fichiers |

À l'écran du parc, le jeu remet visibles les 7 tampons (`SetActorHiddenInGame(false)`). Leurs composants restent invisibles, et les éoliennes aussi.

**Conclusion de cette partie.** Le parc et le point où la voiture est exposée sont intacts. Les retouches cachent seulement des éléments décoratifs et l'environnement gallois autour.

## 3. Où le parc se trouve dans notre monde

Le placement de l'étape 1 a été inversé : rotation de 35°, origine au PK 0, `pc/etape2_unreal/releves/placement_etape1.json`. Contrôle : le PK 0 retombe exactement sur UE (1 154,97 ; 1 407,46 ; 516,17).

| Grandeur | Valeur |
|---|---|
| Point de la voiture au parc, en Lambert-93 | (918 860 ; 6 240 032), altitude 425 m dans notre repère |
| Distance au départ (PK 0) | **2,1 km** vers l'est-sud-est (1 852 m à l'est, 999 m au sud) |
| Terrain réel sous le parc (MNT LiDAR 2 m) | 321 à 372 m, versant boisé à 60-73 % (MNS − MNT > 2 m) |
| Hauteur du sol du parc au-dessus de notre terrain | **53 à 104 m** |
| Notre décor à cet endroit | anneau lointain seulement (dalles `SM_GrandCaunetFarRing_38_30` et `Cliff_38_30`, 1 km de côté) |

À l'écran du parc, notre version devrait donc montrer la voiture dans sa tente galloise, sur le sol gallois du parc. Ce sol flotte en l'air au-dessus de nos collines lointaines, sans forêt galloise autour et sans herbe de parc. Faire descendre le parc sur place est impossible : le terrain dessous est une pente boisée de 50 m de dénivelé.

## 4. La cause : ce qui est établi, ce qui reste à voir en jeu

**Établi.**

- Le jeu ne montre le parc que sur l'écran d'avant la session, jamais sur la spéciale.
- Notre paquet ne retire ni le parc ni le point où la voiture est exposée.
- En Essais libres, l'écran du parc est prévu à chaque chargement.

**Non établi hors jeu** : ce que le directeur voit au moment du chargement. Deux explications restent.

| | Explication | Ce que verrait le directeur |
|---|---|---|
| a | L'écran du parc est sauté : Week-end de rallye (Hafren Sud aller est en « pas de parc » dans les programmes du jeu), ou relance par « Recommencer » | la voiture directement sur la ligne de départ, sans menu « Parc d'assistance » |
| b | L'écran du parc s'affiche, mais le parc est à sa place galloise, hors de notre décor | menu « Parc d'assistance » ; voiture dans une tente sur un plateau gallois en l'air, nos collines lointaines autour |

S'il n'y a ni (a) ni (b), c'est-à-dire si le menu s'affiche avec la voiture seule sans aucune tente, rien dans les données ne l'explique. Il faudrait alors chercher dans le chargement de la voiture au parc (`GarageComponent`).

**Essai à faire (5 minutes, sans rien installer de plus).**

1. Essais libres, notre spéciale, chargement depuis le menu principal, sans « Recommencer ». Noter le premier écran après le chargement : menu « Parc d'assistance » (boutons démarrer la session, assistance de la voiture, infos de l'épreuve) ou ligne de départ ? S'il y a un menu, faire une capture et tourner la caméra autour de la voiture.
2. Même chose sur Hafren Nord (Cwmbiga), que notre mod ne touche pas : c'est la référence du parc gallois.
3. Même chose sur Hafren Sud **retour** (« Severn - Afon Bidno »). Elle utilise notre niveau persistant retouché, mais ses propres cellules galloises : si le parc y est normal, notre niveau persistant n'y est pour rien.

## 5. Avoir un parc près de notre départ : méthode décrite, non mise en œuvre

### 5.1 Principe

C'est la technique des retouches existantes (doc 15, `Characters.cs`) :

- **déplacement rigide** de tout le cœur du parc : une translation et une rotation autour de la verticale ;
- **réécriture sur place**, dans le composant racine de chaque acteur, des 3 doubles de `RelativeLocation` et du double « Yaw » de `RelativeRotation`. La rotation d'ensemble s'ajoute au lacet de chaque acteur, parce que le lacet d'un rotateur UE est la rotation la plus externe ;
- mêmes tailles d'export, aucune nouvelle classe, aucun nouvel élément.

Pendant la spéciale, le jeu continuerait de cacher le parc : rien ne changerait sur la route. Seul l'écran d'avant la session montrerait la voiture dans sa tente, devant notre décor.

**Essai de faisabilité, fait sur une copie** : `sonde_parc`, sur le niveau persistant d'origine extrait par l'étape 1 (`Z:\acrxs\construction\legacy-vanilla`).

- **478 acteurs étiquetés sur 478 trouvés une fois exactement** : tous ceux qui ont une racine, c'est-à-dire tous sauf `PCGWorldActor`. Leur position et leur rotation figurent chacune une fois exactement dans les octets de leur racine. La condition de `FindDoubles` est remplie partout.
- Aucune racine n'est attachée à un autre acteur.
- Toutes portent une rotation écrite, qu'on peut remplacer sans en ajouter une.

### 5.2 Retouche `0006-parc-assistance.patch` telle qu'elle serait écrite

1. Option `stage-build --service-park <x,y,z,lacet>`, lue dans une rubrique `service_park` de `stage.json` (repère des déclencheurs). `4_construire.ps1 -ParcAssistance`, activé par `7_tout_refaire.ps1`.
2. Après la retouche 0005, sélectionner les acteurs étiquetés `ServicePark` à moins de 100 m de `ServiceParkTargetPoint2`. Ils sont 456, dont 443 à déplacer : on retire les 10 personnages, déjà désétiquetés, et 3 acteurs de cette zone qui doivent rester en place (exclusion PCG, son d'ambiance, occultation de la pluie : voir le point 3). Leur appliquer le déplacement rigide qui amène ce point à la place voulue.
3. Laisser sur place :
   - `PCGWorldActor`, `BC_PCG_Exclusion_C` et les tampons PCG ;
   - les éoliennes et le pylône ;
   - la zone de ravitaillement (type de zone propre aux week-ends) ;
   - **les 3 volumes sonores, le son d'ambiance et le volume d'occultation de la pluie**. Cacher un acteur ne coupe pas ses sons ni ses volumes : déplacés près du départ, ils joueraient l'ambiance et la réverbération du parc pendant la spéciale.
4. Sol gallois du parc (`SM_WalesServiceParkTerrain`) : l'enfoncer de 1 000 m, comme la racine des murs de réapparition en v1. Le parc se poserait alors sur notre terrain.
5. Contrôle dans `stage-check` : relire chaque racine (nouvelle position et nouveau lacet présents une fois, ancienne position absente), en-tête et taille du paquet identiques, octets changés seulement dans les racines déplacées (32 octets au plus par racine).

### 5.3 Pourquoi elle n'est pas faite

| Point | Constat | Gravité |
|---|---|---|
| Place | Il faut une zone plate (moins de 3 m de dénivelé) et dégagée de **93 × 125 m**. Le parking du Grand Caunet (PK −68 à −26, ≈ 1 000 m², 45 × 32 m, arboré) ne suffit pas, même pour la seule tente de la voiture (38 × 34 m). Une recherche a été faite sur le MNT et le MNS LiDAR 2 m : 1,5 km autour du PK 0, 20 à 250 m de l'axe, orientation par pas de 15°. Meilleure zone : **le champ au sud-est du carrefour avec la D3, centre (917 308 ; 6 240 816), orientation 150°, dénivelé 2,8 m, 10-16 % de couvert (une haie au coin nord-ouest), à 365 m du PK 0 et 155 m de l'axe**. Elle n'est couverte que par l'anneau lointain (dalle `FarRing_37_30`, quelques dizaines de triangles par km²) : le sol du parc ne coïnciderait pas avec notre terrain, et il faudrait une dalle de sol à nous dans le décor. Le paquet du décor est le domaine d'un autre agent | **bloquant** sans travail sur le décor |
| Monde physique | La zone retenue est dans notre boîte physique (UE X ≈ 1 524 m, limite 1 705 m). Dans les 4 niveaux du jeu examinés, le parc est toujours hors de la boîte. Ce que fait la voiture exposée au parc dans le monde physique n'a jamais été essayé : elle reste figée, tombe, ou entre en collision | moyenne |
| Sons | Volumes sonores et son d'ambiance laissés en Galles (§ 5.2) : le parc déplacé serait plus silencieux que l'original | esthétique |
| Végétation du parc | La cellule `CYMJW…` ne peut pas suivre : c'est une cellule spatiale, pas un acteur du niveau persistant | esthétique |
| Cause | Si l'explication (a) est la bonne, le déplacement ne change rien à ce que voit le directeur | **à trancher d'abord (§ 4)** |

### 5.4 Ordre proposé

1. Faire l'essai du § 4.
2. Si c'est (a) : rien à corriger dans le mod. En Week-end, choisir « parc d'assistance » devant notre spéciale dans l'éditeur de programme ; éviter « Recommencer » si l'on veut voir le parc.
3. Si c'est (b) et que le directeur veut le parc chez nous :
   - demander à l'agent du décor une dalle de sol plate et dégagée au champ de la D3 (ou à une place que le directeur choisira) ;
   - écrire la retouche 0006 du § 5.2 ;
   - faire un premier essai en jeu limité à l'écran du parc : voiture posée, caméra, tentes ;
   - puis rouler une spéciale complète, pour vérifier qu'aucun son du parc ne s'entend au départ.

## Annexe : preuves et scripts

Dossier de travail : `C:\Users\Clement\AppData\Local\Temp\claude\9a363c87dfa2c7c8\de0a3927-cc94-4a3e-b308-2623eef70d30\scratchpad\parc\`.

| Fichier | Contenu |
|---|---|
| `a4.py` | 479 acteurs étiquetés du niveau d'origine : comptes par classe, boîte englobante, recoupement avec les 107 acteurs cachés par l'étape 1 |
| `a7.py` | comparaison propriété par propriété du niveau persistant de la quinzième version (`ex/persistant_v15.json`, vue `controle\full`) avec celui d'origine |
| `a9.py`, `b6.py` | cellules proches du parc et leurs couches avant et après ; position du parc et boîte physique de Bollène, Sisteron et Hafren Nord |
| `ex/DT_*.json`, `ex/FSM_*.json`, `fsm.py` | tables (`DT_Tracks`, `DT_RaceEventTypes`, `DT_PreRaceZone*`, `DT_RallyWeekendCalendarPreset`) et machines à états relues |
| `kismet/`, `kx/`, `kis.py` | relecture du bytecode des FSM (CUE4Parse avec `ReadScriptData`, compilé hors ligne depuis le cache NuGet local) |
| `dis/`, `natif.py` | désassemblage de `HasRaceEventServicePark`, `SetupServiceParkActors` et `OnServiceParkStateChanged` dans `acr.exe` (Iced, cache NuGet local) |
| `b1.py`, `b3.py`, `park_pts.npy` | emprise du parc par rayon autour de la voiture |
| `b4.py`, `zones.json`, `ortho_depart.jpg` | recherche de zones plates et dégagées près du départ (rouge : champ de la D3 ; magenta : écarté, sur la D3 et le mas) |
| `b8.py` | position du parc dans notre monde et terrain dessous |
| `sonde_parc/`, `parc_racines.json` | essai de faisabilité de la réécriture sur place (478 sur 478) |
