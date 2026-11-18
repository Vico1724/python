# 21. Étude : Munster comme niveau hôte

Demande du directeur, 18 novembre 2026. Le niveau Munster du jeu (Rallye d'Alsace, asphalte) peut-il accueillir une spéciale de Provence, à la place de Hafren South ou en plus de lui ? À quel coût, et pour quel gain ?

Cette étude a été faite **en lecture seule**. Rien n'a été construit ni installé, le jeu n'a pas été ouvert, et aucun fichier existant n'a été modifié. Les extractions ont été faites avec `acr-ref` (build 25170642, mappings `Z:\acrxs\mappings\acr_25170642.usmap`) dans un dossier temporaire hors du projet.

Les marques ont le sens suivant :
- **[lu]** : fait lu dans les fichiers du jeu, dans le code ou dans nos documents ;
- **[supposé]** : déduction non vérifiée, à confirmer.

## 21.1 Réponse courte

**Recommandation : non, Munster ne doit pas remplacer Hafren South comme hôte. Il ne vaut pas non plus la peine d'en faire un second hôte, sauf dans un cas précis (§ 21.8).**

- **Aucun gain physique.** La chaussée utilise de toute façon notre matière d'asphalte. Tout ce que Munster « apporte » d'asphalte passe déjà par les tables, quel que soit le niveau hôte : surface, pneus, météo Alsace, `OptimalAirTemperature` 30 °C. L'humidité de base de Hafren est déjà remise à 0.
- **Coût élevé** : environ **10 à 13 jours** de travail, dont 2 à 3 en jeu. Il faudrait rendre acr-ref paramétrable par hôte et refaire tous les relevés.
- **Plus de risques que Hafren.** Le monde de Munster est trois fois plus découpé (512 cellules contre 163). Ses six variantes partagent la plupart des cellules. Surtout, il n'a **aucun équivalent de notre cellule de décor `1LS8…`**.
- **Pour le nombre de spéciales**, remplacer Munster en plus de Hafren ne donne qu'**une place de plus**, et fait perdre une spéciale du jeu. La voie « copie relocalisée de Hafren » de l'autre session vise N spéciales sans toucher aux spéciales du jeu. C'est elle qu'il faut pousser.

## 21.2 Identité de Munster

| Élément | Valeur | |
|---|---|---|
| Niveau | `acr/Content/Levels/AlsaceS2Munster.umap` (+ `.ubulk`, `_BuiltData`, textures d'occlusion) | [lu] |
| Spéciale (`DT_Tracks`) | ligne `Munster`, lieu Alsace | [lu] |
| BakedData | `/Game/Environments/AlsaceS2Munster/DataAssets/DA_AlsaceS2MunsterBakedData` | [lu] |
| Données physiques | 2 378 collisionneurs maillés, 8,21 M triangles (Hafren : 734 et 4,77 M) ; 10 680 formes simples, dont 10 159 troncs | [lu] |
| Matières | `PM_SurfaceTarmacSmooth` 492 collisionneurs / 3,21 M triangles ; herbe 405 / 4,80 M ; murs et roches | [lu] |
| Particularités | 3 collisionneurs appartiennent à un autre niveau, `/Game/Levels/AlsaceServicePark` ; les collisionneurs sont classés par calque (`DataLayerToMeshCollisionDataIndices`) | [lu] |
| Notes de copilote | `DT_PacenoteMunster{Full,Short1,Short2}{Forward,Reverse}` | [lu] |

**Les six variantes** (`DT_TracksVariants`, toutes asphalte 100 %, pneus `TarmacSnow`, météo `Alsace`, largeur moyenne 4,3 m) [lu] :

| Ligne | Nom au menu | Longueur | Altitudes | Départ |
|---|---|---|---|---|
| `AlsaceS2MunsterFullForward` | Vallée de Munster Montée | 10,3 km | 475–1 160 m | 466 m |
| `AlsaceS2MunsterFullReverse` | Vallée de Munster Descente | 10,3 km | 475–1 160 m | 1 040 m |
| `AlsaceS2MunsterShort1Forward` | Luttenbach près Munster | 7,0 km | 475–1 090 m | 466 m |
| `AlsaceS2MunsterShort1Reverse` | Forêt de Munster | 6,8 km | 475–1 090 m | 1 027 m |
| `AlsaceS2MunsterShort2Forward` | Sommet de Munster | 5,3 km | 883–1 160 m | 882 m |
| `AlsaceS2MunsterShort2Reverse` | Col du petit Ballon | 5,6 km | 883–1 160 m | 1 040 m |

Les calques de données s'appellent `DL_MunsterCut1…` et `DL_MunsterCut2…`, alors que les lignes disent `Short1` et `Short2`. Trois lignes « Short » écrivent même `GamplayActors`, sans « e » [lu]. Ce sont des noms de lignes de `DT_DataLayers`, pas des noms de calques, donc sans conséquence [supposé].

**Météo du niveau** (`BC_WeatherActor_C`) [lu] : `weather_data` ne garde que `global_day_duration` 0 et `global_gloominess` 0. **Il n'y a pas d'humidité de base**, alors que Hafren porte 0,1. La journée démarre à 13 h (`Timeline.StartTime` 46 800 s). La commande `--level-wetness` de `Weather.cs` cherche l'heure et l'humidité de Hafren, qui sont absentes ici. Elle échouerait sur Munster, et elle y serait inutile.

**`OptimalAirTemperature`** : 30 °C pour Munster [lu, `docs/18` § 18.6]. Notre spéciale l'a déjà depuis le build 23 (`docs/19`).

**Acteurs du niveau persistant propres à l'Alsace** [lu] : `BC_CrowdSystemManager_Alsace_C` (au lieu de `…_Wales_C`), 5 `BC_Marshal_C`, 5 `BC_Mechanic_C`, 5 `BC_HighResCrowd_C`, 6 tentes, 5 camions d'assistance, 2 ambulances et une voiture de sécurité. 530 acteurs portent l'étiquette `ServicePark` (479 chez Hafren).

## 21.3 Zone physique et relief

**`PhysicsWorldBounds` de Munster** [lu] : boîte centrée en UE (−305 127 ; −383 ; 82 315) cm, demi-côtés (302 295 ; 136 210 ; 39 728) cm. En mètres « physique » (x = UE X, z = UE Y, y = UE Z) :

| | Munster | Hafren d'origine | Hafren élargi (notre build) |
|---|---|---|---|
| x | −6 074 … −28 (6 046 m) | −2 048 … 802 (2 850 m) | −2 951 … 1 706 (4 657 m) |
| z | −1 366 … 1 358 (2 724 m) | −964 … 2 048 (3 012 m) | idem |
| y (altitude) | 426 … 1 220 (794 m) | 305 … 534 (229 m) | 305 … 685 |
| Surface | 16,5 km² | 8,6 km² | 14,0 km² |

Sources : Hafren d'après `StageBuild.cs` (`World.Host`) [lu], notre build d'après `construction/stage-grandcaunet.report.json` [lu].

Les collisionneurs de Munster débordent de la boîte : x de −8 500 à −33 m [lu]. Notre chaîne les remplace de toute façon.

**Le Grand Caunet contre ces boîtes** (calcul équivalent à `stage-fit` : 932 portes de `export/stage_ir/grand_caunet/stage.json`, meilleure rotation par pas de 1°) [lu] :

| Marge autour de l'axe | Munster (boîte d'origine) | Hafren d'origine | Hafren élargi |
|---|---|---|---|
| 0 m | tient, 589 m de jeu (θ = 35°) | ne tient pas (−37 m) | tient, 806 m |
| 130 m (notre couloir de collision) | tient, 329 m | ne tient pas | tient, 546 m |
| 400 m (marge de `stage-fit`) | **ne tient pas (−211 m)** | ne tient pas | tient, 6 m |

L'emprise de la route tournée est de 3 851 × 2 135 m. Son dénivelé est de 149 m, et celui de la collision de 202 m : la hauteur de Munster (794 m) est largement suffisante.

**Le point clé :** la boîte de Munster n'est pas un avantage. acr-ref **élargit déjà** la boîte de Hafren (`stage-build --bounds 1`, `Bounds.cs`, décision D8), et c'est ce que fait notre build. Munster est long et étroit : une spéciale de 7 à 9 km tient si elle est allongée (jusqu'à environ 5 km de long sur 2 km de large). Une spéciale ramassée ou en boucle y tiendra moins bien qu'à Hafren élargi. Il faudrait alors élargir la boîte de Munster de la même façon [supposé : `Bounds.cs` repère la boîte par sa classe, il devrait marcher tel quel].

**Relief :** le relief de Munster (vallée, 475 à 1 160 m) ne sert à rien. Notre terrain et notre route remplacent les collisionneurs, et le décor de l'hôte est caché. L'altitude de départ du menu (`ElevationAtStart`) est un champ de la table, que nous réglons de toute façon [lu].

## 21.4 World Partition

| | Munster | Hafren South |
|---|---|---|
| Grille | `MainGrid`, cases de 350 m, portée 640 m | idem |
| Niveaux de grille | 7 (0 à 6) | 6 (0 à 5) |
| Cellules | 513 (492 au niveau 0, 1+2+2 aux niveaux 2 à 4, 16 au niveau 6) | 164 (157, 1, 6) |
| Paquets de cellules `_Generated_` | 512 | 163 |
| Cellules sans calque, toujours actives à portée | 304 | 76 |
| Cellule « toujours chargée » (`bIsAlwaysLoaded`, aucun calque) | `261YU3VG2NL2GPV1VTDBGWS47` | `9B6YIZGWVTI51AYGOJFUCI75E` |
| HLOD | 254 | 87 |

**Partage entre variantes [lu].** Chez Hafren, chaque cellule de décor de rallye appartient à un seul sens. Chez Munster, la plupart des cellules portent plusieurs calques à la fois. Par exemple, 12 cellules portent `Cut2ForwardRallyProps + FullForwardRallyProps`, et 6 cellules portent les six calques « gameplay » à la fois. Activer une variante charge donc aussi une partie des objets des autres.

**Cellule candidate pour notre décor.** La `1LS8…` de Hafren est au niveau le plus haut de la grille (une case qui couvre tout le monde, donc toujours à portée), et elle ne porte que le calque `FullForwardRallyProps`. **Munster n'a pas de cellule équivalente** [lu]. Ses 16 cellules du niveau 6 sont :
- `D2JQMCALY1NBU69PBHEHCE3DW` : `FullForwardGameplayActors` seul. C'est probablement la cellule de jeu (équivalent de `22VG…`), qu'acr-ref réécrit, donc pas une cellule de décor [supposé].
- `5J8V1W0YFE41926LVQYQIXL2J` : `Cut2ForwardRallyProps` seul. C'est le seul candidat « décor seul ». L'utiliser obligerait notre ligne de variante à activer `Cut2ForwardRallyProps`, ce qui charge aussi les 12 + 10 + 7 + 4 + … cellules de décor de cette variante, à cacher ensuite [supposé].
- Les autres cellules portent des calques du sens retour ou plusieurs calques.

Une autre voie est possible : échanger une référence dans le hachage spatial, comme le fait déjà `Officials.cs` (retouche 0006). Les cellules du niveau 6 qui ne servent qu'au retour feraient de bonnes donneuses : `AE9Y…` (`FullReverseGameplayActors`), `69JP…` (`Cut1Reverse…`), `0N8A…` (`Cut2Reverse…`). Ce montage n'a jamais été essayé pour une cellule de décor [supposé].

**Décor de Munster à cacher :** 304 cellules sans calque, contre 76 chez Hafren, plus 498 `StaticMeshActor` et 254 HLOD dans le niveau persistant [lu]. La forêt vosgienne serait à masquer quatre fois plus largement qu'à Hafren. Les listes de `Scenery.cs` et de `4_construire.ps1` (`--scenery`, cellules gardées) sont à refaire entièrement.

## 21.5 Chemins et valeurs écrits en dur

### Dans acr-ref (`Z:\acrxs\acr-extrastages\tools\acr-ref`) [lu]

| Fichier | Ce qui dépend de Hafren | Travail pour un second hôte |
|---|---|---|
| `StageBuild.cs` (12 mentions) | boîte `World.Host` et zone sûre `Safe*` ; `GroundBase` 380, `HostFlatMin/Max` ; `HostTemplateCollider` 10 ; cellule de jeu `22VG…` ; `DT_PacenoteHafrenSouthForward` ; ligne de variante « Hafren South forward » | à sortir dans un profil d'hôte, et relevé complet de Munster (sol plat, collisionneur modèle) |
| `StageSelfTest.cs` (`HostPaths`) | BakedData, cellule de jeu, persistant, notes | profil, puis allers-retours octet pour octet sur les paquets de Munster (persistant de 330 Mo en JSON) |
| `StageVerify.cs` (13) | mêmes chemins ; tuiles `SM_WalesS4HafrenSouthTerrain*` ; contrôle de la ligne Hafren | profil, et règles de vérification propres à Munster |
| `Scenery.cs` | `PersistentLevel`, `Persistent`, listes d'acteurs et de HLOD cachés | à refaire pour 498 acteurs et 254 HLOD |
| `Officials.cs` (9) | cellules `A0I1…` et autres, `CellRel`, demi-largeur 1,9 m, niveau 5 de la grille, donneuses `7FF9`/`BGX4` | à refaire : niveau 6, nouvelles donneuses, nouveaux officiels de départ et d'arrivée |
| `Characters.cs` | table « nom d'éditeur → export » du persistant de Hafren (build du 14/11) | nouvelle table pour les 5 + 5 + 5 personnages de Munster |
| `ServicePark.cs` | 479 acteurs `ServicePark` à la place galloise | à refaire (530 acteurs, plus le niveau `AlsaceServicePark`) |
| `Weather.cs` | motif `global_day_time 1559.361` + `global_wetness 0.1` | sans objet sur Munster : à désactiver pour cet hôte |
| `Bounds.cs` | repère la boîte par sa classe | devrait marcher tel quel [supposé] |
| `TreeInstancer.cs`, `HismRewrite.cs` | forêts PCG du persistant de Hafren réutilisées | à relever sur Munster (122 acteurs `PCG_Ground` contre 6) |
| `BakedEdit.cs`, `ObjectColliders.cs` | conventions vérifiées sur la BakedData de Hafren (couleurs, propriétaires, index par calque) | à revérifier : Munster classe ses collisionneurs par calque |
| `RoadUv.cs`, `Pacenotes.cs` | références de mesure (UV de route, rayons médians) | commentaires et étalonnage seulement |
| `Program.cs` | texte d'aide | — |

À cela s'ajoutent les retouches qui touchent ces fichiers : `pc/patches/0001` (6 mentions), `0005` (4), `0006` (9) et `0008` (2) [lu]. Elles seraient à réécrire, ou à reporter sur le profil.

**Estimation acr-ref : 4 à 5 jours.** Il faut un type « profil d'hôte » qui regroupe chemins, cellules, boîte, sol, modèles et tables, Hafren restant le profil par défaut. Il faut aussi refaire les relevés de Munster et l'autotest.

### Dans nos scripts [lu]

| Fichier | Mentions | Nature |
|---|---|---|
| `pc/scripts/4_construire.ps1` | 16 | table `$hote` (BakedData, `22VG…`, notes, persistant), cellules gardées, aide |
| `pc/etape2_unreal/scripts_pc/chaine_decor.ps1` | 4 | cellule `1LS8…` par défaut, chemin `Levels/WalesS4HafrenSouth/_Generated_` |
| `pc/etape2_unreal/scripts_pc/cuire_et_empaqueter.ps1`, `choisir_decor.ps1` | 2 + 1 | chemin du niveau à cuire |
| `pc/etape2_unreal/outils/relever_jeu.py` | 7 | expression `NIVEAU`, matériaux de Hafren |
| `pc/etape2_unreal/outils/` (`decor_hybride`, `relire_decor`, `zones_decor`, `extraire_elements`) et `scripts_editeur/construire_niveau.py` | 1 à 2 chacun | chemin de la cellule hôte |
| `pc/scripts/6_table_asphalte.ps1`, `pneus_asphalte.py`, `rallye_grand_caunet.json` | 3 + 3 + 3 | ligne `WelesS4HafrenSouthFullForward`, niveau `WelesS4HafrenSouth` |
| `pc/scripts/5_installer.ps1`, `7_tout_refaire.ps1` | 1 + 2 | noms et contrôles |
| `scripts/09_export_stage_ir.py` | 5 | rubrique `characters.host`, étalonnages Munster/Hafren (commentaires) |
| `scripts/16_paquet_unreal.py`, `scripts/mobilier.py`, `pc/config/noms-grand-caunet.toml` | 3 + 1 + 1 | étalonnages, noms |

**Estimation scripts : 1,5 à 2 jours.** Il faut un paramètre « hôte » commun, lu par `commun.ps1`, puis mettre à jour les règles de `creer_speciale.py` du skill. Le projet Unreal doit aussi avoir une copie vide du chemin `Levels/AlsaceS2Munster/_Generated_/<cellule>`, comme il en a une pour Hafren.

## 21.6 Officiels, personnages, parc, portiques, murs de reprise

| Élément | Côté Munster | À refaire ? |
|---|---|---|
| Personnages du parc (méthode `Characters.cs`) | 5 commissaires, 5 mécaniciens, 5 spectateurs « haute résolution » dans le persistant [lu] | table de correspondance à refaire ; même méthode [supposé] |
| Officials de départ et d'arrivée (méthode B, `Officials.cs`) | dans des cellules du sens aller, non identifiées ici [supposé] | relevé des cellules, nouvelles donneuses au niveau 6 (§ 21.4) |
| Parc d'assistance (`ServicePark.cs`, `docs/16`) | 530 acteurs étiquetés, plus le niveau à part `AlsaceServicePark` cité par la BakedData [lu] | à refaire ; le niveau séparé est une inconnue [supposé] |
| Portiques, rubalises, décor de rallye | répartis dans des cellules partagées entre variantes (§ 21.4) [lu] | à cacher ou à garder cellule par cellule |
| Murs et points de reprise | notre chaîne les tire de nos portes (`respawn.method = gates`) | rien de propre à l'hôte [supposé] |
| Foule | `BC_CrowdSystemManager_Alsace_C` [lu] | foule « Alsace » au lieu de « Wales » : seul petit gain visuel possible [supposé] |

## 21.7 Comparaison avec la « copie relocalisée de Hafren »

La copie relocalisée de Hafren est décrite dans `acr-extrastages/docs/additive-plan.md`, voie (b). On copie le niveau, ses cellules et sa BakedData sous `/Game/AcrXs/Stages/<Id>/`, et on ajoute des lignes dans un registre unique.

| Critère | Munster en remplacement | Copie relocalisée de Hafren |
|---|---|---|
| Gain physique | **aucun** : même `PM_SurfaceTarmacSmooth` ; surface, pneus, météo et température passent par les tables ; humidité déjà à 0 [lu, `docs/18`] | aucun, et aucune perte |
| Spéciales du jeu touchées | une variante de Munster perdue (le modèle « Tarmac » d'`acr-additive`, `MenuLocations.cs`, est justement `AlsaceS2MunsterFullForward`) [lu] | **aucune** : 0 paquet du jeu remplacé [lu, plan] |
| Nombre de spéciales | 2 (Hafren + Munster) | N, sans limite trouvée [lu, plan] |
| Effort | 10 à 13 jours (§ 21.9) | celui de l'autre session ; toute notre chaîne Hafren (cellule `1LS8`, officiels, personnages, parc) se réutilise [supposé] |
| Taille par spéciale | 512 cellules à cacher ou à copier | 163 cellules |
| Risques | pas d'équivalent de `1LS8` ; cellules partagées entre variantes ; 4 fois plus de décor à cacher ; niveau `AlsaceServicePark` à part ; retouches à réécrire | essai en jeu de la voie additive encore à faire ; un seul registre propriétaire des tables |

Munster en copie relocalisée (Munster comme modèle de la voie additive) cumulerait les deux coûts : profil d'hôte plus clonage de 512 cellules. Sans gain physique, il n'y a pas de raison de le faire.

Les seuls avantages réels de Munster sont mineurs :
- une boîte physique déjà grande, mais acr-ref élargit celle de Hafren ;
- pas d'humidité de base, mais elle est déjà remise à 0 ;
- une foule et des ambiances alsaciennes, invisibles si l'on cache le décor.

## 21.8 Recommandation

1. **Non** pour remplacer Hafren par Munster comme hôte du Grand Caunet. Il n'y a ni gain physique ni gain de place, et le travail et le risque sont bien plus grands.
2. **Non** pour un second hôte Munster « en plus », tant que la copie relocalisée de Hafren n'a pas été essayée en jeu. C'est elle qui répond à la coexistence de plusieurs spéciales dans « Sainte Baume Rallye ».
3. **À reconsidérer seulement si** l'essai en jeu de la copie relocalisée échoue pour une raison propre à Hafren, et non à la relocalisation elle-même (registre, identifiants de paquets, chargement des cellules). Dans ce cas, commencer par rendre acr-ref paramétrable par hôte (§ 21.5). Ce travail servirait aussi à tout autre hôte. Avant Munster, regarder les hôtes du jeu déjà en asphalte et moins découpés : Bollène et Sisteron (Monte-Carlo) et Saverne (Alsace) ont aussi une BakedData [lu]. Leur découpage n'a pas été mesuré ici.

## 21.9 Coût estimé si l'on passait quand même à Munster

| Poste | Jours |
|---|---|
| Profil d'hôte dans acr-ref, autotest et vérification paramétrés | 2 |
| Relevés Munster : sol plat, collisionneur modèle, officiels, personnages, parc, décor à cacher, forêts PCG | 2 à 3 |
| Stratégie de cellule de décor (échange au niveau 6, ou calque `Cut2ForwardRallyProps`) | 1 à 2 |
| Nos scripts, retouches 0001/0005/0006/0008, règles de `creer_speciale.py` | 1,5 à 2 |
| Projet Unreal : cuisson sous le chemin de Munster | 0,5 |
| Essais en jeu et corrections | 2 à 3 |
| **Total** | **10 à 13** |

## 21.10 Ce qui ne se tranche qu'en jeu

- Si une cellule de décor « échangée » au niveau 6 se charge bien dans toute la spéciale, comme la `1LS8` de Hafren.
- Le coût en fluidité des 304 cellules sans calque et des 254 HLOD de Munster, même cachés.
- Le rôle du niveau `AlsaceServicePark` dans le chargement du parc.
- L'effet éventuel de l'hôte sur l'éclairage : `_BuiltData` et textures d'occlusion de Munster sous notre décor, ciel et heure de départ à 13 h.
- `OptimalAirTemperature` et `ElevationAtStart` : effet inconnu, mais indépendant de l'hôte (`docs/18` § 18.7).

## 21.11 Refaire les extractions

Depuis `Z:\acrxs`, avec `G` = dossier du jeu et `U` = `mappings\acr_25170642.usmap`, dans un dossier temporaire :

```
bin\acr-ref\acr-ref.exe list   --game G --usmap U --filter "(?i)munster" --out list.txt
bin\acr-ref\acr-ref.exe export acr/Content/Data/Database/Main/TrackSelection/DT_TracksVariants.uasset --game G --usmap U --out tv.json
bin\acr-ref\acr-ref.exe export acr/Content/Levels/AlsaceS2Munster.umap --game G --usmap U --out munster.json      (330 Mo)
bin\acr-ref\acr-ref.exe export acr/Content/Environments/AlsaceS2Munster/DataAssets/DA_AlsaceS2MunsterBakedData.uasset --game G --usmap U --out mbaked.json   (850 Mo)
bin\acr-ref\acr-ref.exe baked-summary mbaked.json --out mbaked_sum
```

La grille, les cellules et leurs calques sont dans les objets `WorldPartitionRuntimeSpatialHash`, `WorldPartitionRuntimeLevelStreamingCell` et `DataLayerInstanceWithAsset` du niveau. La boîte physique est le `Model` dont l'`Outer` est `PhysicsWorldBounds`, plus la `RelativeLocation` de son `BrushComponent`.
