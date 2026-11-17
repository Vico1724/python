# Assetto Corsa Rally (ACR) : livrer une spéciale réelle comme mod

Source : projet « Le Grand Caunet » (spéciale asphalte de 6,7 km, Bouches-du-Rhône), 10 au 17/11/2026, 19 à 21 versions construites, 14 essais en jeu jugés. Complète `modding_par_jeu.md` §3 (état des outils et du jeu).
Balises : **[vu]** = jugé bon en jeu par le joueur ; **[19+]** = présent dans les versions 19 à 21, jamais vues en jeu (ce sont des paris) ; **[lu]** = relevé dans les fichiers du jeu, non jugeable à l'œil ; **[déduit]** = inférence ; **[non vérifié]**.
Conventions : `<ATELIER>` = dossier de travail Windows (même disque que le jeu), `<JEU>` = dossier d'installation, « le joueur » = la personne qui juge. Jeu : early access, Unreal 5.6.1 (moteur compilé par le studio, `+UE5-acr`), build Steam 25170642 ; le jeu n'écrit pas de journal par défaut.

## Table des matières
1. Voie de livraison
2. Outils et rôle
3. Suite d'étapes et durées
4. Valeurs calibrées propres au jeu
5. Assets du jeu réutilisés
6. Traces du niveau hôte à neutraliser
7. Contrôles de relecture hors jeu
8. Installation et retour arrière
9. Pièges propres au jeu
10. Jamais validé en jeu

---

## 1. Voie de livraison

- **On ne peut pas ajouter une spéciale ; on remplace une variante du jeu.** Hôte retenu : « Hafren South 1/2 » (aller, Pays de Galles). Conséquences : une seule spéciale installée à la fois ; spéciale ≤ 9 km (au-delà, non constructible) ; sens retour 2/2 injouable ; les menus affichent « Hafren South » (sauf option `-Noms`) ; hors ligne, Essais libres, Steam hors ligne.
- **Trois conteneurs retirables** dans `<JEU>\acr\Content\Paks\~mods\` : `zz_acrxs_<id>_P` (route physique : sol, obstacles, chrono, notes, ligne idéale, personnages), `zz_acrxs_<id>_table_9_P` (table des variantes), `zz_gc_gc_P` (décor Unreal, ~2 Go). Un `_P` de `~mods` remplace les paquets de même chemin [vu 11/11, preuve par une bannière affichée].
- **Voie « hybride » du décor** : un niveau Unreal ordinaire, cuit, remplace le contenu d'UNE cellule World Partition de l'hôte (cellule `1LS8FPM8JIMX697U3QIPKC01K` : toujours chargée, sans `bIsSpatiallyLoaded` ; 75 des 163 cellules ne portent que terrain et végétation). Le jeu accepte un niveau ordinaire à la place d'une cellule malgré le nom de monde différent. Physique, chrono, notes et déclencheurs restent ceux d'`acr-ref`. Raison du choix : `acr-ref` ne sait que réutiliser les objets existants de l'hôte à capacité constante ; une demi-heure d'étude pour le retoucher a été perdue (P14).
- **Cuire exactement en 5.6.1** (le commerce suffit) : 5.5 et 5.7 écrivent des paquets de format différent. Cuire **avec versions de propriétés** (`-Versionne`) dès qu'il y a un niveau ; sans versions, les groupes d'arbres sont illisibles en jeu. Le jeu accepte [vu 11/11].
- **Rien du jeu n'est livré** : les éléments du jeu sont référencés par chemin via des **factices** (même chemin, même type, contenu vide, jamais livrés ; 168 entrées : 112 StaticMesh, 22 MaterialInstance, 15 Texture2D, 11 Blueprint ignorés, 8 Material). `cuire_et_empaqueter.ps1` les écarte (`factices.json`) et `relire_decor.py` le contrôle. Licence du jeu (CLUF) non trouvée : diffusion publique **à valider** ; la table `…_table_9_P` embarque la table d'un registre tiers : **non redistribuable**.
- **Jamais de fichier d'un mod tiers** (leurs structures ont été comprises par les sommaires d'archives, noms seulement). Une seule exception, autorisée par le joueur et documentée : la table du registre sert de base à notre table.
- Voies de repli **non essayées** : écriture directe du contenu cuit sans éditeur (`ground_bake`, `HismRewrite`) ; acteurs de classes natives créés depuis l'éditeur (risque élevé : classes souches C++, ordre des propriétés).

## 2. Outils et rôle

Tous construits sur le PC du joueur, aucun redistribué avec le jeu. Prérequis Windows : PowerShell 7.2+, Git (`core.autocrlf=false`), .NET 10 SDK, Rust (`rustup default stable`, `retoc` s'installe avec `--locked`), outils C++ Microsoft (un redémarrage peut être exigé), winget, ~10 Go libres sur le disque du jeu (liens physiques, NTFS) + ~10 Go sur C:, UE 5.6.1 (~60 Go).

| Outil | Rôle | Réserve |
|---|---|---|
| `acr-ref` (clone d'ACR Extra Stages à commit fixe `1324f07d…`, 31/10/2026, MIT/Apache-2.0, + nos retouches 0001-0006) | `stage-build` (route physique, chrono, notes, obstacles, retouche du niveau persistant), `stage-verify`, `stage-check`, `export` (lit tout paquet, sert à comparer avec une spéciale du jeu), `raw`, `schema` | `modding_par_jeu.md` n'a trouvé aucun dépôt de ce nom : c'est un exécutable construit par `2_recuperer_acrxs.ps1` [déduit] |
| `acr-additive` | `registry` (fiche → tables de menus) ; `relocate` | `relocate` inutilisable pour nos niveaux cuits (P15) |
| `acr-mappings` | produit le `.usmap` : lance le jeu par Steam, lit la mémoire en lecture seule, referme (30-60 s) | à refaire à chaque mise à jour ; secours Dumper-7 (hasardeux) |
| `retoc` | `to-zen --version UE5_6` (conteneur `.utoc/.ucas/.pak`), `to-legacy --filter` (extraction) ; télécharge Oodle seul | |
| Unreal 5.6.1 | cuisson uniquement ; projet vide nommé **exactement `acr`** (racine des chemins `acr/Content/…`) ; plugins Python Editor Script + Editor Scripting Utilities | éditeur complet requis pour `construire_niveau.py` (sans interface, les sous-systèmes manquent) |
| `lire_utoc.py` (à nous) | lit le sommaire (noms) d'une `.utoc` UE5 | |

Retouches d'`acr-ref` (`pc/patches/`, appliquées dans l'ordre ; **tester l'application sur un clone neuf**, elle doit redonner exactement nos fichiers) : 0001 `--keep-variants 1` (ne livre pas `DT_TracksVariants`) ; 0002 objets facultatifs ; 0003 identifiant libre (inutilisé) ; 0004 `--visuals-exclude <json>` ; 0005 `--characters 1` (déplace les 10 personnages) ; 0006 ligne idéale, officiels, parc réduit, `--level-wetness`.

## 3. Suite d'étapes et durées

| # | Étape | Durée mesurée | Sortie / contrôle |
|---|---|---|---|
| 0 | Faisabilité et voie (GitHub, forums de mods, triés par date) | 1 soirée | verdict initial faux, corrigé le soir même (P01) |
| 1-6 | Points officiels (15), vecteurs IGN, tracé, rasters IGN, profil, couloir ; **lignes de départ/arrivée relevées sur vidéo AVANT tout calcul** (PK 0 reculé de 20 m) | secondes à minutes ; ~250 Mo puis ~600 Mo | écart-type PK 6,9 m (13 max) ; seuil proposé < 15 m |
| 7-9 | Chaussée au mètre (profils ±15 m, pas 0,25 m), régularisation (refuse d'écrire si un virage est dénaturé), diagnostic de trace | 15 s ; secondes | cassures > 5° : 0 visé sur l'axe |
| 10 | Modèle 3D neutre (glTF) : terrain en dalles de 500 m, route, ouvrages, carrefours | 08 : 40 s | `repere.json` |
| 11 | Semis d'arbres cime par cime (MNS−MNT), graine fixe | quelques minutes | 41 579 arbres, 122 753 arbustes |
| 12 | Export physique « Stage IR » | 7 s | portes ≤ 10 m, `controle_<id>.json` |
| 13-14 | Paysage lointain (jusqu'à 30 km) ; sols « sous les arbres » et masques du jeu | ~10 min (13+14) | 4 processus de 2-3 Go |
| 16 | **Paquet Unreal** (maillages recentrés, textures, variantes, instances CSV, `manifeste.json`) | 2 min | ~420 Mo ; 553 maillages, 585 907 objets (v9) |
| 17 | Outils Windows (clone, build, `.usmap`) | 10-20 min, une fois | |
| 18-19 | **Route physique** puis relevé du placement | quelques minutes ; secondes | `stage-verify` sans FAIL ; décalage visé 0,0 cm |
| 20 | **Décor Unreal** : factices → import → niveau → cuisson versionnée → relecture | import 1 h la 1re fois, 30 min tout réimporter, 3 min niveau seul ; cuisson 11 min ; chaîne 55-75 min | « RELECTURE CONFORME » |
| 21 | Tout d'un trait (`7_tout_refaire.ps1`) | **80-90 min** (83, 82, 83) | |
| 22-23 | Installation ; essai en jeu | secondes ; 5-10 min de conduite | vidéo de TOUT le parcours |
| 24 | Exploitation d'un essai (calage vidéo, paires jeu/reconnaissance tous les 40 m, relevé, regroupement par cause) | demi-journée par cycle [déduit des dates] | 42 à 324 constats par essai |

- Premier bout de chaîne sur le PC (11/11) : kit écrit sur Linux sans Windows, étape physique seule **roule en jeu du premier coup** ; bannière vue en jeu à 16 h 26 ; paquet complet `tout_lancer.py --sans-rendus` en 44 min (téléchargements compris).
- **Après un changement de tracé, ordre impératif** : (1) régénérer données et modèle ; (2) reconstruire la route physique puis `relever_placement.py` ; (3) paquet ; (4) vider `Content\Environments\<Nom>\{Road,Bridges,Junctions,Props,Terrain,Shared}` et le niveau de la cellule (l'import ne remplace pas : P134) ; (5) `construire_niveau.py` ; (6) cuisson ; (7) installer les deux conteneurs ensemble. Raison : `acr-ref` recalcule le placement d'après l'emprise de la route (6,8 cm de décalage observés).
- Budget visé pour une nouvelle spéciale : une session, deux constructions (une complète, une de retouche), **un seul essai en jeu** ; réalité : 19-21 versions, 14 essais, dont plus de la moitié évitables. `creer_speciale.py` est cité dans la doc mais **n'existe pas** dans le dépôt lu ; ~40 valeurs du projet sont codées en dur pour le lieu.

## 4. Valeurs calibrées propres au jeu

### 4.1 Physique, roulage, menus

| Réglage | Valeur | Statut / raison |
|---|---|---|
| Sol physique par code | `TSD+` = `PM_SurfaceTarmacSmooth` (chaussée, enrobé annexe) ; `DBK+` = `PM_SurfaceGravelHard` (accotement 3 m, îlots) ; `GRS+` = `PM_SurfaceGrass` (couloir 130 m de chaque côté) | [vu] ; hors couloir on tombe (P163) |
| Obstacles | pierre `PM_WallRock` ; béton `PM_WallConcrete` ; barrière plastique `PM_WallPlasticBarrier` ; piquet `PM_WallPlasticPole` (non inscrit, remplacé par `PM_WallBasic` [déduit du code]) ; glissière `PM_WallMetalGuardrail` ; poteau bois `PM_WallWoodPole` ; poteau béton = cylindre 30 cm ; tronc `PM_WallWoodTreeTrunks` (≤ 6 m du bord, 3 m de haut, enfoui 0,3 m, 1 023 troncs) ; haie `PM_WallBush` ; rocher < 35 cm sans collision, sinon cylindre `PM_WallRock` ; piquets de rubalise sans collision ; murs invisibles sous les parois rocheuses | [vu] ; sans collision d'arbres la voiture les traverse (P153) |
| Portes de chrono | pas 10 m (plus serré aux ponts), tolérance 0,25 m ; 932 à 1 096 portes ; 2 intermédiaires aux tiers (PK 2 677 et 5 043) ; longueur compétitive 6 737,44 m ; point stop ~580 m après l'arrivée | [vu] |
| Notes du copilote | seuils 1:17°, 2:23°, 3:34°, 4:54°, 5:81°, 6:150° ; fenêtre 20 m ; fusion 10 m ; 55 virages calculés → 51 annoncés après 16 retouches issues de la vidéo | brouillon jugé correct ; le constructeur ne produit que virages, « ne pas couper », distances, arrivée : 24 dangers gardés dans `stage.json` mais **non annoncés** (P160) |
| **Table des variantes** | surface Tarmac ; pneus TarmacSnow ; météo `MonteCarlo` ; longueur 6,738 ; ligne `WelesS4HafrenSouthFullForward` ; Gravel→Tarmac ×5, GravelOnly→TarmacSnow ×1 ; 47 autres lignes identiques | pneus [vu] ; la table doit être bâtie SUR celle du registre installé et livrée en conteneur `_9_P` (P150) |
| **Humidité de base** | `--level-wetness 0` (hôte : 0,1 ; Munster : aucune) | [19+] ; l'hôte hérité mouille la route |
| **Météo** | `--meteo MonteCarlo` (ligne Wales : 4 °C) ; température de référence `DT_Tracks` 5 °C (Bollène 5, Munster 30) ; changer la température affichée à la main n'a presque aucun effet | v18 ; comparer avec Bollène (même référence), pas Munster |
| **Adhérence de départ** (option du JOUEUR, non sauvegardée par le mod) | Optimale = 1,0 ; Fast 0,92 ; Green 0,88 ; Slow 0,86 ; Dirty 0,85 ; hors trajectoire −1 niveau ; +13 % Optimale vs Green ; `MarblesGrooveK` 0,08 | demander au joueur de la régler (Optimale) avant l'essai |
| **Ligne idéale** | calculée (courbure minimale), marge au bord 1,2 m, écart ≤ 2,5 m, rappel 3e-4, pas 2 m, couloir 1,5 à 6,0 m, 932 points ; `SkidIntensity` par rayon 15/30/60/120/300/∞ m → 1/0,95/0,85/0,7/0,55/0,5 lissée sur 20 m | v19 (valeurs Munster) « un peu mieux » ; **v20-21 jamais vues**. Repères Munster : écart médian à l'axe 0,47 m, couloir 150-330 cm, gomme médiane 0,2 |
| Zone physique | `--bounds 1` si la route dépasse la boîte de l'hôte (de ~45 m en plan, 11 m en hauteur) | `PhysicsWorldBounds` X −2 048…802 m |
| Décalage de placement | 0,0 cm depuis la v6 (rotation 35° de l'hôte, PK 0 → UE (1 154,97 ; 1 407,46 ; 516,17) m) | `relever_placement.py` |

### 4.2 Rendu (matériaux, sol, végétation, relief)

- **Hériter des matériaux du jeu** (variantes seulement, aucun nouveau shader, aucun changement de static switch) : mesurer la couleur moyenne des textures du jeu (`couleur_texture.py`, DXT1/DXT5) et en tirer les teintes. Essayer tout nouveau parent de matériau **sur 200 m** (`--etendue E4`, 2 min) avant la spéciale entière.
- Enrobé `MI_GC_Enrobe` ← `MI_BolleneAsphalt1`, `Base_Tint` (3,35 ; 3,2 ; 2,95), `ColorContrastMacro` 0,4, sommets (0,0,0,0), plaqué en monde. Pierre ← `MI_MonBolStoneWallsA` : clarté 2,0, **sommet (0,0,0,255) : blanc = mousse, noir = pierre**. Roche ← `MI_BolleneRockfacesParent` : clarté 2,4, saturation 0,45. Béton : clarté 1,7. Enduits ← `MI_MonBolConcreteWallsA`, teintes mesurées sur Street View.
- **Couleur de sommet** : Unreal met du blanc opaque par défaut, que le matériau du jeu lit comme masque plein ; les sols et routes du jeu valent (0,0,0,0) : l'écrire.
- Marquage : `M_Simple` blanc, 12 cm de large, 15 mm au-dessus de la chaussée ; rives discontinues 3 m/3,5 m, axe 3 m/10 m, traits rapprochés si R < 140 m ; **le décalque du jeu `MI_RoadmarkingsTileableTrack0116` a fait disparaître les lignes (essai abandonné, noté dans `essais_abandonnes`)**. Bord d'enrobé net (`--bord-enrobe 0`).
- Sol : parent `MI_MonteCarloS1BolleneTerrainFirstChild`, 6 matières (fond `T_SoilAndGravel_00` clarté 2,0 ; aiguilles ; herbe verte ; herbe sèche ; terre ; roche), masques 1 024 px **par carré de 350 m** (un maillage ne dépasse pas son carré), carte de couleur 4 096 px visant 118/255 de clarté (Bollène 86,5, trop sombre). La photo aérienne ne sert qu'à teinter de loin (elle montre le dessus des arbres).
- Dalles de terrain 500 m, maillage 1 m jusqu'à 15 m, 2 m jusqu'à 40 m, 4 m au-delà ; textures en puissances de 2 (2 660 → 2 048 px), JPEG q95, relief PNG sans perte `TC_Normalmap` (convention DirectX, ne PAS cocher Flip Green), `Clamp` pour le terrain, `Wrap` pour les répétées. Repère Unreal : X est, Y sud, Z haut, cm, origine = axe au PK 0 ; glTF → UE `100·(gX, gZ, gY)` (vérifié par une mire de 3 barres de 4, 2, 1 m). Origine locale soustraite avant float32 ; UV ramenées près de 0 (Lambert-93 > 10⁶ noircit les maillages).
- Moteur du jeu : **Nanite désactivé** (`r.Nanite.ProjectEnabled=False`), textures virtuelles actives, Lumen/ombres virtuelles/RT coupés, aucun éclairage statique : recopier `DefaultEngine_extrait.ini`, ne cuire aucun maillage Nanite.
- Route : grain rendu = 3/4 de l'écart pour les ondulations > 6 m, écrêté à 1,5 cm → 0,08 g moyen, 0,42 g max à 90 km/h (ni 1-2 g brut, ni 0,04 g sur-lissé) ; altitude ≤ 5 cm du relevé, dévers à 2 % ; `DALLE_RETRAIT` 0,10 m (tablier sous la chaussée).
- Arbres : rien sous 4,5 m au-dessus de la chaussée, surplomb ≤ 3 m (≤ 1 m pour un pin > 9 m), **réduire, jamais retirer**, même règle dans la physique ; largeur/hauteur AleppoPine 0,80, BlackpineMonteCarlo 0,61, Cypress 0,54, Olivetree 1,26, autres feuillus 0,92 ; échelles 0,6-1,5. Herbes : bande 14 m dès 0,35 m du bord, 12 touffes/m, disparition 90-140 m, **sans ombre**, hauteur 14-35 cm, couchées sur pente 6-55°. Buissons : disparition 150-220 m. Relief lointain : au sol avec arbres entiers jusqu'à 450 m, à hauteur de cime 450-650 m, MNT LiDAR 2 m jusqu'à 2 km, RGE ALTI ensuite jusqu'à 30 km ; falaises par pente LiDAR > 46-48° habillées de roche du jeu.
- Habillage de chaussée par décalques, **partir bas** : litière 2,5 paquets/km, un décalque par débouché (gardé 4 fois sur 10), traces de pneus en sortie des virages R ≤ 40 m et ≥ 60° ; bilan v18 : 102 décalques (au lieu de 151 + 5 837 feuilles, jugés trop denses en 3 essais).
- Décor : une seule grosse cellule toujours chargée a tenu (585 000 objets, 2 Go de conteneur), fluide à tous les essais.

## 5. Assets du jeu réutilisés

Cités par nom, jamais copiés. Détail et noms de matériaux : `catalogue_assets.md` §c. Ici : ce qui a marché et ce qui est à éviter.

| Catégorie | À utiliser | À éviter (raison vue en jeu) |
|---|---|---|
| Arbres `/Game/Foliage/Trees/…` | `AleppoPine/SM_AleppoPine01…15` (pin d'Alep ; 15 formes, du parasol à tronc nu à 9 m × 13 m), `BlackpineMonteCarlo`, `Boxthorn/SM_Boxthorn01…05` (chêne vert, sous-bois, vert sombre dense), `BlackmapleMonteCarlo` (un tiers des grands chênes, jaune en novembre), `Blackmaple/SM_Blackmaple01…06`, `Cypress*`, `Olivetree` (pâle) | `Smoketree` (mauve) ; `SM_AleppoPine12/13` et `SM_Blackmaple04` (souches/plants de 0,25 à 0,87 m, 3 468 arbres y pointaient). **Extraire l'image `T_<Arbre>NNBillboard_B` de chaque candidat avant de choisir, jamais sur le nom** |
| Herbes et buissons `/Game/Foliage/GroundCover/…` | `DryGrass04/05/06`, `WildGrass/SM_WildGrass03/05`, `GreenGrass03`, `GreenGrassLong02`, `Willow/SM_Willow_01/_03a/_03b/_04a` | **noirs en jeu** (matériau `UseRVTBaseColor`, couleur lue dans une texture virtuelle du niveau d'origine) : `SM_Ribwort_01`, `SM_WildGrass01`, `SM_Dead_Leaves_01`, `BroomCreeper` (sauf les plus bas buissons), `FallenLeaf_*`. Exporter le matériau de chaque herbe candidate et refuser celles qui ont cet interrupteur |
| Glissières | `Props/Guardrails/MetalGuardrailA/SM_MetalGuardrailASimpleBegin/SimpleCenter/SimpleEnd` (module 4 m, enfoncé 5 cm, lisse côté +Y) | |
| Panneaux et rallye `Props/RallyProps/…` | `Signs/SM_RaceRadioWarningA/B`, `SM_RaceRadioPointA`, `SM_RaceMedicWarningA`, `SM_RacePreFlyingFinish`, `SM_RaceFlyingFinish`, `SM_RaceStart`, `SM_NopublicSign`, `SM_RaceControlZoneEnd` ; `RaceTimer`, `TrafficConeA`, `TapePlasticPoleA`, `PlasticBarrierA/SM_PlasticBarrierAFix` ; `FranceTrafficSigns/SM_TrafficSignFra{DangerA,CrossRoadsA,SlipperyRoadA,NarrowRoadA,RightTurnA1,CurveMarkerD}`, `MileMarkerA`. Orientation : lacet = cap + 90° (+180° si vu de dos), à 2,5-4 m de l'axe, face d'un panneau routier +Y, mât 50 cm sous l'origine | Pas de panneau « affaissement » ni « succession de virages » dans le jeu. Panneau cloué sur un tronc : planter un pin derrière |
| Portiques | `RallyProps/Gantries/SM_RallyGantry6m` (6 m, pas 8) ; bannière `T_RallyGantryWales_B` | les portiques verts que dessine `acr-ref` : les enterrer (copie de config à hauteur négative) |
| Poteaux | bois : `MonPylonC/SM_MonPylonC11`, `AlsaceProps/FraMunPylonA` ; `MonPylonB11/B15` | béton du jeu rejeté (« jumelés en A », caissons bleu-noir) → poteau à nous (fût effilé 8,2 m) |
| Véhicules `Props/NonDrivableVehicles/…` | `VanA/SM_VanCrew`, `SecurityCarA`, `HatchbackA`, `MpvA`, `SedanB`, `StationWagonA`, `SuvA` ; variante `MI_<X>MiscAllLightsOff` (feux éteints) | pose **en acteurs individuels** : en instances leurs matériaux sont remplacés par celui par défaut (voitures noires) ; feux de détresse allumés par défaut |
| Personnages (déplacés, **jamais créés**) | Blueprints `BC_Marshal_C`, `BC_HighResCrowd_C` (+`_Spline_C`), `BC_MarshalStartEndSequencePC_C`, `BC_StopMarshalStartSequence_C`, `BC_StopMarshalEndSequence_C`, gestionnaires `MarshalsManager`, `BC_CrowdSystemManager_Wales_C` | `BC_TiresRack_C` (pneus flottants dans le parc) |
| Sols, murs, roche | voir §4.2 et `catalogue_assets.md` | rochers du jeu `Props/Nature/*` et `GreElaSmallStones` : beige rosé assombri, non réglable → pierres anguleuses fabriquées (enveloppes convexes, graine fixe) |
| Décalques `AlsaceShared/DecalMaterialInstances` (filles de `M_MasterDecals_WorldSpace`) | `MI_AsphaltDirtDecalDirtDebree`, `MI_AsphaltDirtDecalGravel`, `MI_DirtDecal_MontecarloDirtOnAsphalt`, `MI_DirtDecal_MontecarloDirtTracks01`, `MI_AsphaltDecal_LightRubber`, `MI_AsphaltTiresMarksDecal`, `RallyShared/…/MI_PineNeedles` ; acteurs `DecalActor`, échelle 1, taille = moitiés | |

Références du jeu à lire avant de poser une valeur (ne jamais inventer une valeur de matière, densité ou physique) : Bollène (orientation des panneaux, densité de décalques, masque de sol, adhérence), Sisteron, Munster/Saverne (physique, ligne idéale).

## 6. Traces du niveau hôte à neutraliser

Une spéciale remplacée garde la vie de l'hôte ; l'étape 1 (`scenery.toml`, `sky.toml`) en cache une partie :
- **Visuels d'essai de l'hôte** (route de gravier, pavés, piquets magenta, terrain gallois) : `--visuals-exclude <zones.json>` (0004). **Ne pas passer `--visuals`** avec notre décor : la zone rouge de départ (boîte du déclencheur du jeu, que le constructeur déplace bien) disparaîtrait aussi. Deux panneaux de départ et deux cônes du jeu restent posés.
- **Végétation et objets galloise** : `hide_meshes` `SM_SpruceWales`, `SM_BeechBare` ; `hide_actor_classes` `BC_MyhTurbineA_C` ; 7 « tampons » d'arbres PCG et 6 éoliennes cachés. Gestionnaires gardés : `BC_CrowdSystemManager_Wales_C`, `MarshalsManager`, `CrowdReactionsManager`, `CrowdSplineFollowersManager`.
- **Étiquette `ServicePark`** : 479 acteurs (459 gardés intacts) que le jeu **cache pendant toute spéciale** (`FsmActionSetActorVisibility`). La retouche 0005 la neutralise pour les personnages (sinon aucun visible alors que le contrôle de fichier était vert, P08). Le parc d'assistance n'apparaît que sur l'écran « Parc d'assistance » avant la session (sauté par « Recommencer » et si la zone d'avant-course est `NoZone`, cas des 3 programmes gallois pour Hafren Sud aller) et reste à sa place galloise (2,1 km de notre départ, 53-104 m plus haut). Solution v18 : parc réduit (tente de la voiture + 164 acteurs à < 8 m du point de la voiture, posés dans l'emprise du parking au pôle d'inaccessibilité, garde 1 m au mobilier, 3,5 m aux voitures ; 295 autres enfoncés de 1 000 m ; arbres écartés sur 11 m ; sortie PK −60). Compte du parc : 164 (doc 14) ou 169 (valeurs calibrées).
- **Officiels animés** (cellules `A0I1JHQ2458PSST2XD0UTWQ2I` départ, `0QY7AIYF1F7BYQ1BH0V2NX22R` arrivée) : un World Partition cuit charge par cases de 350 m (`MainGrid`, portée 640 m) ; A0I1 est à 2,1 km de notre départ, notre arrivée est hors du monde gallois → réécrire la référence de chaque cellule (hachage spatial, entier de 4 octets) vers une cellule de la case unique du niveau 5 qui ne se charge jamais dans le sens aller (donneuses `3H10…`, `7FF9…`) [19+].
- **Portiques « Rally Wales »** des cellules d'officiels : enfoncés de 1 000 m. **Murs de reprise** que `acr-ref` trace 20 m au-delà du bout de chaque porte : `bords_normaux` (`BIAIS_MAX_DEG` 20°) → limite à > 15 m de la chaussée, sinon mur invisible [vu v15].
- Hôte : matériau de gravier gallois rejeté ; météo Wales 4 °C et humidité 0,1 voir §4.1 ; ciel `BC_DMSky_Montecarlo_Bollene` ; table de menus : le jeu garde UNE table, celle du conteneur le mieux classé (inventorier `Paks` ET `~mods`).

## 7. Contrôles de relecture hors jeu

À passer avant tout essai (un essai coûte 2-3 h ; un contrôle doit porter sur ce que le joueur VOIT, pas sur la présence d'un fichier) :
- `4_construire.ps1` : lignes `PASS`/`FAIL` de `stage-verify` (attendu : tout PASS ; officiels « referenced in the top grid level » ; parc réduit ; ligne idéale 932 points) ; `stage-check` (raycasts, splines, 1 cm / 0,1° pour les personnages) ; rapport `stage-<id>.report.json`.
- Table relue dans une vue « jeu + mods de `Paks` + notre conteneur » : Tarmac / TarmacSnow / MonteCarlo / 6,738 ; 47 lignes identiques ; message « notre conteneur passe devant ».
- `relire_decor.py` : conteneur = notre dossier + cellule hôte et **aucun factice** ; niveau (maillages, instances, éléments du jeu désignés) ; variantes de sol → parent Bollène ; masques ; couleurs de sommet ; herbes (disparition, sans ombre) ; véhicules (feux éteints) ; la référence de cellule des officiels ; sortie « RELECTURE CONFORME ». Il additionne les instances quand deux composants visent le même maillage (P23).
- `relever_placement.py` (cible 0,0 cm) ; `controle_<id>.json` (sol sous toutes les portes, aucun trou le long de l'axe, bord droit à droite, virages du bon côté, aucun obstacle sur la chaussée) ; contrôle de placement (objets perchés/enterrés > 0,5 m, arbustes à < 1 m d'un mur, roche sans sommet en porte-à-faux) ; aperçus maison (`21_apercu_conducteur.py`, `23_apercu_lointain.py`) : jamais le rendu du jeu (ni matières ni éclairage).
- Chaque nouvelle règle de placement reçoit un contrôle chiffré dans `relire_decor.py` (degrés comparés à des mètres, arbustes dans les bâtiments : P17). Logique de l'import testée sans éditeur par un faux module `unreal` : ne prouve pas l'API.
- Lire les archives AVANT d'écrire du code ni d'installer l'éditeur (`relever_jeu.py`, 1 min) : paramètres de matériaux (static switch !), hauteurs de maillages, classes d'acteurs, niveau hôte (3 erreurs de protocole et 3 468 arbres sur souches évitables, P18).

## 8. Installation et retour arrière

1. Jeu fermé, Steam hors ligne, ne JAMAIS ouvrir le jeu pendant une construction (la route physique n'est alors pas reconstruite : « ROUTE PHYSIQUE NON CONSTRUITE »). `0_controle.ps1` : build, tailles d'archives `acr_paks_build_25170642.csv`, disque.
2. `5_installer.ps1` (route physique seule : consigne l'état de `Paks`, confirmation, copie 3 fichiers) ou `choisir_decor.ps1 -Decor <version>` (installe route physique + table + décor d'une version gardée ; sans `-Decor` : liste et dit laquelle est installée). Toujours installer les deux conteneurs ensemble.
3. En jeu : Pays de Galles → Hafren South → variante 1/2 → Essais libres ; option « Adhérence de départ » = Optimale ; pour voir le parc : depuis le menu principal, sans « Recommencer ».
4. **Retour arrière** : `6_desinstaller.ps1` (supprime nos fichiers, et `~mods` s'il était créé et vide) ou « Vérifier l'intégrité des fichiers » Steam. Aucune archive d'origine n'est modifiée.
5. Versions gardées avec leur route physique dans `<ATELIER>\unreal\dist\` (25 au 17/11) : `sol_jeu` (courante), `sol_jeu_vu_le_<date>` (vue en jeu), `sol_jeu_cycle<n>_du_<date>` (jamais vue). Retour à une version vue = une commande, sans reconstruction.
6. Après toute mise à jour du jeu : refaire le `.usmap`, reconstruire, relire les valeurs lues ; build différent de 25170642 → prévenir.
7. Protocole d'essai du joueur : vidéo de TOUT le parcours (départ arrêté compris), captures avec PK et côté pour tout défaut, mêmes voiture et réglages que sur Bollène/Munster pour comparer ; 12 questions oui/non/PK/captures (chargement et sens, pneus, météo, zone rouge, officiels, chrono, notes, adhérence, murs invisibles/trous, relief lointain/parois, sol/herbe/débris, objets flottants, départ et arrivée, fluidité). Calage vidéo du jeu : barre de progression `PK = 31,5 + 6 696,4 × part` (1 colonne = 9,6 m, 7 m près), pas les virages (échoue sur la course : P62).

## 9. Pièges propres au jeu

Symptôme → cause → correctif / parade.
- **Table de menus livrée sans effet** → un registre tiers dans `Paks` (pas `~mods`) livre la même table et le moteur classe un conteneur `_<n>_P` d'après n (100×(n+1) ; sans nombre le nôtre valait 1, le registre 2) [déduit d'un commentaire sur `FPakPlatformFile`, non rouvert] → conteneur `zz_<id>_table_9_P` bâti sur la table installée ; à refaire si le registre change (P12, P150).
- **Spéciale classée « terre », pneus terre** → la ligne de table de l'hôte dit Gravel/GravelOnly (P150).
- **Sous-virage, manque de grip** → (a) ligne idéale recopiée de l'axe (couloir fixe 150 cm, SkidIntensity 0), (b) humidité de base 0,1 héritée, (c) météo Wales, (d) option joueur non réglée ; la météo seule n'était pas la cause principale → comparer d'abord la physique ENTIÈRE à une spéciale asphalte du jeu avec `acr-ref export` (P13, P151). Piste non vérifiée : masque de débris (canal UV 5, `FC_TarmacGripDebrisCurve`) absent de notre collision.
- **Variante de `M_Simple` restant unie** → static switch `Simple_Use_*_Texture` inactifs par défaut → parent = une variante du jeu qui les a déjà (`MI_SisteronConcrete01`), jamais le maître ; régler couleur, normale, ORM (P133).
- **Matériaux noirs** : herbes à `UseRVTBaseColor` (P87) ; voitures en instances (P94) ; branche fermée noire par UV en Lambert-93 (P99) ; blanc opaque par défaut des sommets (P139).
- **Mur invisible** → murs de reprise obliques (§6, P152) ; toujours demander capture + PK + côté AVANT de diagnostiquer (P07).
- **Personnages / parc / officiels invisibles** → étiquette `ServicePark` et cases du World Partition (§6, P154-155).
- **Import qui ne remplace pas** (14 morceaux d'anneau allégés et 23 textures basse résolution restés, rapport « REPÈRE DIFFÉRENT ») → supprimer les dossiers avant de réimporter (P134).
- **Éditeur qui rend −1073741819 à la fermeture** avec tout enregistré → sans effet ; le rapport JSON `Saved\<Nom>\construire_niveau_<étendue>.json` fait foi (P131). `construire_niveau.py` doit tourner dans l'éditeur complet : `UnrealEditor.exe <proj>.uproject -ExecutePythonScript="… --quitter" -unattended -nosplash` (P130). Chemins avec `/`, jamais `\` (P135).
- **Cubes factices de 1 m** → bornes et tri calculés trop tôt, pins de 15 m éliminés → le factice reçoit les dimensions du vrai maillage (P136).
- **Renommer un niveau cuit** impossible (`relocate` perd la référence au matériau) → construire directement au chemin final (P15).
- **Tirages au sort après un filtre** → une correction locale change toute la spéciale (sous-bois différent du PK 174 au PK 7 214) → graines tirées AVANT tout filtre ou une graine par entité ; règle limitée à la zone (P16). Comparaison au code d'avant : 73 512 sujets identiques.
- **Géométrie ambiguë** (carrefour à niveaux refait 3 fois) → LiDAR brut d'abord, photos ensuite (P03) ; le LiDAR l'emporte sur la vidéo pour ponts, ponceaux, talus (P39, P69).
- **Outillage** : fins de ligne des patches (P171) ; dossier de travail sur un autre disque que le jeu (liens physiques impossibles : P170) ; `python -P` depuis un dossier neutre quand le dossier courant contient des fichiers téléchargés (P175) ; `PYTHONUTF8=1` sous Windows (P176) ; journaux filtrés par motifs plutôt que relus en entier (P174).
- **Méthode** : ne pas empiler des versions sans essai (v8-v10 : erreurs découvertes toutes ensemble) ; ne pas reconstruire 80 min pour une teinte (regrouper les corrections ; fabriquer le paquet suivant pendant que l'éditeur importe, `16 --sortie paquet_unreal_cN`) ; ne pas supprimer un objet « incompris » avant d'avoir relu la vidéo (P06) ; mesurer ce que fait le studio sur ses spéciales asphalte avant d'inventer une valeur (P04) ; sessions courtes avec note de reprise, relevés d'images confiés à des agents moins coûteux avec un schéma JSON imposé (P22, P72).

## 10. Jamais validé en jeu

- **Versions 20 et 21 entières** : ligne idéale plus marquée (couloir complet + gomme de route roulée), officiels chargés partout (méthode B), parc au milieu du parking, arbres du build 18 hors zone de départ. Toute valeur marquée [19+] est un pari : humidité de base 0, météo `MonteCarlo` (v18 seulement), ligne idéale calculée (v19 « un peu mieux » aux valeurs Munster), parc réduit, officiels animés.
- Adhérence : option du joueur « Optimale » **à essayer** ; masque de débris ; comparaison chiffrée avec Bollène après v19.
- Sortie de route au-delà de 130 m (remise en piste sur notre route : jamais consignée comme résolue) ; physique du parc dans la boîte du monde (jamais essayé) ; bords de route fondus (`MI_BolleneAsphalt1SideFirstChildOuter/Inner`, non essayé) ; pièces/fissures d'asphalte par héritage d'une variante qui les a (`MI_MunsterAsphalt1patches`, piste non menée).
- Registre de menus `zz_gc_registre_P` (jamais installé) ; ajout par `acr-additive registry` + `retoc to-zen` (essai E2a, jamais installé) ; usage en ligne ou classements : **[non vérifié]**, rester hors ligne.
- Vu et jugé bon : tracé, fluidité de la cellule unique, route physique d'emblée, bannière, voie hybride, personnages visibles (v15), murs de reprise (v15), pneus asphalte. Retours reçus : « le tracé semble bon », « sans bug et de manière fluide », « beaucoup mieux » ; défauts jugés : « tas de sable avec une photo de dessus » (relief lointain), « immenses parapets » (parois), « comme si l'asphalte n'avait pas assez de grip ».
- Le format exact de `BakedData` et des notes n'est que partiellement documenté [non vérifié] ; le chargement d'une spéciale personnalisée dans d'autres modes que Essais libres est [non vérifié].
