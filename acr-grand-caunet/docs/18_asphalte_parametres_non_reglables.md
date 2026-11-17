# 18. L'asphalte dans le jeu : ce qui agit sur l'adhérence sans être réglable

Document établi le 17 novembre 2026, à la demande du directeur. Il recense tout ce qui, dans les données d'Assetto Corsa Rally, agit sur l'adhérence d'une spéciale asphalte, sans figurer parmi les réglages du joueur (voiture, pneus choisis, options météo). Il ne couvre que ce qui a été lu dans les fichiers du jeu. Ce qui reste caché dans le code du moteur (`acr.exe`, module physique `dmphysics`) est signalé comme tel.

Sources : les fichiers du jeu, lus avec `acr-ref export` (CUE4Parse, correspondances `acr_25170642.usmap`), et les tables livrées par le mod « registre » installé chez le directeur. Les extractions JSON sont refaites par la commande donnée en fin de document (section 18.9).

## 18.1 La chaîne de l'adhérence, en bref

L'adhérence d'un pneu sur notre route dépend de six étages. Le joueur ne règle directement que le premier et une partie du cinquième :

| Étage | Qui le fixe | Où |
|---|---|---|
| 1. Voiture, pneus choisis, réglages | le joueur | menus |
| 2. Matière physique de la chaussée | la spéciale (nous) | collisionneurs de la route → `PM_SurfaceTarmacSmooth` |
| 3. Niveau d'adhérence de la piste (« grip level ») et son évolution | le jeu, d'après l'option « Adhérence de départ » | `DA_PhysMaterialsMappingCommon`, `BC_DynamicSurfaceManager` |
| 4. Trajectoire (ligne idéale, gomme, « billes ») | la spéciale (nous) | `IdealSpline` du niveau, `DA_PhysicsGlobalSettings` |
| 5. Météo : température de l'air, humidité, neige, gel | la configuration météo de la variante, le lieu, l'heure et l'option du joueur | `DT_TracksVariants → WeatherConfig`, `Data/Weather/…` |
| 6. Usure des pneus, classement de la surface | la variante | `DT_TracksVariants` |

Les sections qui suivent détaillent les étages 2 à 6.

## 18.2 La matière physique de la chaussée

Le jeu n'a **qu'une seule matière d'asphalte** : `PM_SurfaceTarmacSmooth`. Toutes les spéciales asphalte (Munster, Saverne, Bollène, Sisteron) l'utilisent, et notre route aussi. On ne peut donc pas donner à notre chaussée un asphalte plus « accrocheur » que celui du jeu. Les autres matières roulables sont le béton (`PM_SurfaceConcrete`), les pavés, le vibreur (`PM_SurfaceKerb`), l'herbe, le gravier, le sable et la neige.

Paramètres propres à `PM_SurfaceTarmacSmooth` (les valeurs sur sol sec ne sont pas écrites dans le fichier : ce sont celles par défaut de la classe, dans le code du moteur) :

| Paramètre | Valeur | Effet probable |
|---|---|---|
| `FrictionSnow` | 0,7 | frottement sous la neige |
| `FrictionReductionConstantWet` / `…Snow` | 0,0007 / 0,0005 | perte de frottement avec l'eau ou la neige |
| `SlidingSpeedOptimalDry` / `Wet` / `Snow` | 1,0 / 3,0 / 12,5 m/s | vitesse de glissement où le pneu accroche le mieux : sur sec, il faut très peu glisser |
| `RollingCoefficientSnow` | 0,004 | résistance au roulement dans la neige |
| `DebrisSinHeight` / `DebrisSinLength` | 2 mm / 3,5 m | **ondulation simulée** de la chaussée, ajoutée par le moteur à la géométrie |
| `BulldozingHeightSnow`, etc. | 0,045 m… | effet « chasse-neige » des roues |
| Saleté (`DA_AsphaltDirtProperties`) | poussière seulement, accumulation sèche ×0,05 | encrassement de la voiture, visuel |

**Les « couleurs physiques » de la chaussée.** La matière lit quatre valeurs sur chaque sommet de la route (`MeshVertexDataMapping`). Les trois premières sont des constantes nulles. La quatrième est lue dans le canal d'UV 5 (1 − U, et 1 si le canal manque). Le moteur s'en sert sans doute pour un niveau de débris ou de saleté, que `FC_TarmacGripDebrisCurve` traduit en perte d'adhérence (section 18.3). Notre route donne la même valeur que Munster sur chaque collisionneur (`docs/14`, § 16.1). Ce n'est donc pas une source d'écart.

**Ce qui dépend de nous :** que la chaussée porte cette matière et pas une autre (relu PASS : `PM_SurfaceTarmacSmooth`, et seulement 8 m² de gravier qui affleure, sur 50 800 m²). Il faut aussi éviter de la recouvrir d'une autre matière par endroits. L'herbe ou le gravier qui débordent sur la chaussée font perdre de l'adhérence localement.

## 18.3 Le niveau d'adhérence de la piste et son évolution

C'est le réglage le plus puissant, et il n'est **pas** dans la spéciale. Chaque surface a cinq niveaux d'adhérence (`DT_TrackGrips`). Pour l'asphalte (`DA_PhysMaterialsMappingCommon → DynamicSurfacesProperties → ST_TARMAC`) :

| Niveau | Adhérence de base | Hors trajectoire, on tombe à | Gravier, pour comparer |
|---|---|---|---|
| Optimal | 100 % | Fast (92 %) | 100 % |
| Fast | 92 % | Green (88 %) | 96 % |
| Green | 88 % | Slow (86 %) | 92 % |
| Slow | 86 % | Dirty (85 %) | 90 % |
| Dirty | 85 % | Dirty (85 %) | 88 % |

Lecture : sur asphalte, **passer d'« Optimal » à « Green » coûte 12 % d'adhérence partout**. Sortir de la trajectoire coûte un niveau de plus (8 % depuis Optimal). Sur gravier, l'écart est plus faible (8 %). C'est l'explication la plus probable du sous-virage ressenti aux essais.

Autres paramètres de l'asphalte dans la même table :
- `GripImprovement` 0,01 : vitesse d'amélioration de l'adhérence au fil des passages.
- `DustCleanLevel` Green : la poussière est balayée à partir de ce niveau.
- `TyreMarksMinLevel` Green : niveau à partir duquel les traces de gomme apparaissent.
- `IrregularityHighGripLevel` Fast.
- `GripDebrisCurve` : la courbe `FC_TarmacGripDebrisCurve` (0,86 → 0 ; 0,90 → 0,3 ; 0,95 → 0,6 ; 0,98 → 0,9 ; 1,0 → 1), qui relie l'adhérence aux débris.
- Pluie sur la trajectoire : `MaxOnTrajectoryWetnessDelta` 0,6. La trajectoire sèche plus vite (`OnTrajectoryWetSpeedReduction` : −0,25 en Optimal, −0,15 en Fast). `OnTrajectoryWetCarReduction` vaut 10.
- Gel sur la trajectoire : `MaxOnTrajectoryFreezeDelta` 0,6, `OnTrajectoryFreezeSpeedReduction` (+0,25 en Optimal), `OnTrajectoryFreezeCarReduction` 50.

**Évolution pendant la spéciale** (`BC_DynamicSurfaceManager → SurfaceEvolution`) :
- `DefaultGripLevel` vaut Optimal. C'est le niveau du gestionnaire quand rien d'autre ne le fixe.
- Coefficients d'amélioration par niveau : Dirty 1,5 ; Slow 0,8 ; Green 0,9 ; Optimal 0. Une piste sale s'améliore vite, une piste optimale ne bouge plus.
- `FreezeLevelExp` 0,8 et `RainSnowThreshold` 0,1.

**Qui fixe le niveau de départ :** l'option du joueur « Adhérence de départ » (`DA_StartingGripOption` → `WeatherOptions.StartingGripLevel`). Elle n'est pas enregistrée avec la spéciale. Les week-ends de rallye du jeu (`DT_RallyWeekendCalendarPreset`) l'imposent à **Optimal** pour chaque spéciale. En essai libre, c'est la valeur choisie dans le menu qui compte. **Une spéciale ne peut pas imposer son niveau d'adhérence en essai libre.** Il faut le régler dans le menu, sur Optimale.

L'IA a sa propre table (`DT_AITrackGripAttributes`) : de −1 % de temps en Optimal à +12 % en Dirty. Elle confirme la hiérarchie des niveaux.

## 18.4 La trajectoire : ligne idéale, gomme et billes

Réglages globaux (`DA_PhysicsGlobalSettings`, les mêmes pour toutes les spéciales) :

| Paramètre | Valeur | Rôle |
|---|---|---|
| `IdealLineWidth` | 2,0 (m) | largeur de référence de la ligne idéale |
| `IdealLineTransitionWidthPercentage` | 0,5 | fondu entre trajectoire et hors-trajectoire |
| `MarblesGrooveK` | 0,08 | bonus d'adhérence de la trajectoire gommée |
| `MarblesMuK` | 0,017 | perte d'adhérence due aux « billes » (gomme et gravillons rejetés hors trajectoire) |
| `MarblesAccumulationGain` / `DissipationGain` | 0,00065 / 0,00007 | vitesse d'accumulation et de disparition des billes |
| `MarblesPickupAccumulationSpeed` | 0,06 | billes ramassées par le pneu |
| `DirtTrackBaseAccumulationLevel` | 0,015 | saleté de base de la piste |
| `RutMode` | RaycastMod | ornières : déformation lue par rayon |
| `TiresConsumptionRate`, `FuelConsumptionRate` | 0 | pas d'usure accélérée |

**La partie qui dépend de la spéciale est la ligne idéale du niveau** (`IdealSpline` : position, largeur de couloir de chaque côté, intensité de gomme `SkidIntensity`). Le moteur décide « sur la trajectoire » ou « hors trajectoire » d'après elle, et on a vu en 18.3 que sortir de la trajectoire coûte un niveau d'adhérence. Historique chez nous :
- jusqu'au build 18 : la ligne recopiait l'axe, avec un couloir de 1,5 m et une gomme nulle ;
- build 19 : trajectoire calculée, couloir de 1,5 à 3,4 m, gomme comme Munster ;
- build 20 : couloir sur toute la largeur de la chaussée (1,5 à 6 m) et gomme de 0,5 à 1 (`scripts/09_export_stage_ir.py`, `IDEALE`).

On reste dans ce que le moteur accepte : un couloir plus large que la chaussée ne donne rien de plus.

## 18.5 La météo : température, humidité, gel, neige

La météo d'une variante vient de sa colonne `WeatherConfig` dans `DT_TracksVariants` : une ligne de `WeatherTrackConfigs` (MonteCarlo, Alsace, Wales, Livigno ou Greece), qui pointe vers `DA_<lieu>WeatherConfig`. Chaque configuration fixe :
- **les plages de température** par heure et par temps (`Data/Weather/Temperatures/Ranges/<lieu>`) ;
- l'écart de température selon le temps (`DA_WeatherTemperaturesVariation` : de −5 à −1 °C sous la pluie, de −5 à +5 °C par temps clair selon l'heure) ;
- la variation au fil du jour (`DA_DayTemperatureVariations` : ×0,7 la nuit, ×1,1 à 14 h) ;
- **l'altitude** (`CF_ElevationTemperatureVariation` : −6,5 °C par kilomètre, autorisé dans toutes les configurations) ;
- l'humidité sous la pluie (`CF_RainWetnessRate`) et le séchage selon la température (`CF_TemperatureWetnessDryingRate` : nul à 0 °C, 0,0001 à 15 °C, 0,0003 à 30 °C). **Une route mouillée sèche trois fois plus vite à 30 °C qu'à 15 °C, et pas du tout à 0 °C** ;
- la neige (accumulation, fonte selon la température et la pluie), avec `bSnowAllowed` vrai partout sauf en Grèce.

Plages de température par temps clair, en °C :

| Heure | Monte-Carlo | Alsace | pays de Galles | Livigno |
|---|---|---|---|---|
| 0 h | −10 à 5 | 5 à 15 | 2 à 10 | −20 à 0 |
| 8 h | −5 à 10 | 10 à 20 | 2 à 10 | −5 à 8 |
| 12 h | −5 à 20 | 15 à 25 | 5 à 15 | 0 à 15 |
| 14 h | −5 à 25 | 15 à 25 | 5 à 18 | 0 à 15 |
| 18 h | −8 à 15 | 10 à 20 | 4 à 15 | −10 à 8 |

Le tirage du temps (`DT_WeatherTypesDistributions`), en poids :

| Lieu | Clair + nuages | Pluie + orage | Brouillard | Neige |
|---|---|---|---|---|
| Monte-Carlo | 45 | 10 | 12,5 | **35** |
| Alsace | 60 | 35 | 5 | 3,5 |
| Grèce | 60 | 35 | 5 | 0 |
| pays de Galles | 30 | 50 | 20 | 17,5 |

**Notre cas :** depuis le build 18, notre variante utilise la configuration **MonteCarlo** (`pneus_asphalte.py --meteo MonteCarlo`), à la place de celle du pays de Galles qui donnait 4 °C. Le Rallye Monte-Carlo se court en janvier, et sa configuration est une **météo d'hiver**. Par temps clair, il peut faire −10 °C la nuit et rester sous zéro jusqu'en fin de matinée. Le gel fait alors perdre de l'adhérence sur la trajectoire (section 18.3). Si la météo est aléatoire, la neige est tirée 35 fois sur 100. La configuration **Alsace** correspond à un rallye d'été sur asphalte : 10 à 25 °C le jour, presque pas de neige. Elle est plus proche d'un Grand Caunet en saison douce.

**Altitude :** notre départ est à environ 470 m, comme Hafren Sud (`ElevationAtStart` 478 m). Cela fait environ −3 °C par rapport au niveau de la mer, et ne change rien par rapport à l'hôte. Le jeu ne dit pas s'il prend l'altitude du monde ou celle de la table (point ouvert).

**Humidité du niveau :** l'acteur météo du niveau hôte portait une humidité de base de 0,1. Nous la remettons à 0 depuis le build 19 (`--level-wetness 0`, relu PASS).

## 18.6 La variante et la spéciale : ce que les tables imposent

**`DT_TracksVariants`** (notre ligne : `WelesS4HafrenSouthFullForward`, réécrite par `pneus_asphalte.py`) :

| Champ | Hafren Sud d'origine | Notre ligne | Bollène, pour comparer | Effet |
|---|---|---|---|---|
| `SurfaceTypes` / `Sectors[].SurfaceType` | Gravel | Tarmac | Tarmac | type de pneus proposé, réglage de la voiture par défaut, IA |
| `CarSetupDefaultSurfaceType` | Gravel | Tarmac | Tarmac | réglage de départ de la voiture |
| `TireCompounds` | GravelOnly | TarmacSnow | TarmacSnow | gommes proposées au joueur (Soft, Medium, Hard, Wet, Winter, Snow) |
| `WeatherConfig` | Wales | MonteCarlo | MonteCarlo | météo (section 18.5) |
| `DegradationLevel` et celui des secteurs | Medium | Medium | Medium | usure des pneus |
| `Length` | 4,8 km | 6,737 km | 18,2 km | affichage |
| `ElevationAtStart`, `Elevation` | 478 m ; 345–410 | inchangés | 698 m | affichage, peut-être température (non vérifié) |
| `AverageRoadWidness` | 4,5 m | inchangé (réel 6,4 m) | 7,1 m | affichage, peut-être IA |
| `CarsData` | données IA d'Hafren Sud | inchangé | — | temps de l'IA seulement |

**`DT_Tracks`** (la spéciale, au-dessus des variantes) porte deux champs que nous ne pouvions pas changer tant que notre variante restait rangée sous Hafren Sud :
- `OptimalAirTemperature` : 30 °C pour Munster, Saverne et la Grèce ; 5 °C pour Hafren, Bollène et Sisteron ; −5 °C pour Livigno. La valeur suit la saison du rallye. Le nom laisse penser à une température de référence (pneus ou piste). Son usage n'est pas lisible dans les données (point ouvert).
- `WeatherTypesDistribution` : la table de tirage du temps (section 18.5). Hafren Sud tire le temps comme au pays de Galles : 50 % de pluie et d'orage.

**Avec un rallye propre au Grand Caunet** (demande du 17/11, section 18.8), notre spéciale a sa propre ligne dans `DT_Tracks`, et ces deux champs deviennent les nôtres.

## 18.7 Bilan : ce qui peut encore jouer, par ordre d'importance

1. **L'option « Adhérence de départ » sur Optimale** : jusqu'à 12 % d'adhérence. C'est un réglage du joueur, la spéciale ne peut pas l'imposer en essai libre.
2. **La configuration météo** : MonteCarlo peut donner du gel et de la neige. Alsace serait la plus favorable à l'asphalte sec. Ce choix est à nous (`pneus_asphalte.py --meteo`, et `WeatherTypesDistribution` de notre spéciale).
3. **Le temps choisi et l'heure** : temps clair, en milieu de journée.
4. **La ligne idéale** : faite (builds 19 et 20).
5. **`OptimalAirTemperature`** : 5 °C hérités d'Hafren Sud, effet inconnu. À essayer à 30 °C comme Munster, une fois notre spéciale séparée.
6. **La matière de la chaussée** : la seule possible. Aucun écart avec Munster, sauf une rugosité plus faible (4 mm contre 10). Pour mémoire, le moteur ajoute de lui-même une ondulation de 2 mm.

Points qui restent cachés dans le code du moteur : les valeurs de frottement sur sec, l'usage d'`OptimalAirTemperature` et de `ElevationAtStart`, et le sens exact de la quatrième « couleur physique ». Seul un essai comparatif en jeu peut les trancher, par exemple la même voiture à la même heure, avec `OptimalAirTemperature` à 5 puis à 30 °C.

## 18.8 Rapport avec le rallye propre au Grand Caunet

Le jeu range chaque spéciale (`DT_Tracks`) dans un lieu (`DT_TracksLocations`), et c'est le lieu qui forme le « rallye » au menu. Notre variante appartenait à Hafren Sud, donc au pays de Galles. Le rallye propre est décrit dans `docs/19_rallye_propre.md`. Côté adhérence, il permet de choisir `OptimalAirTemperature`, la distribution du temps et la surface affichée du lieu (Tarmac).

## 18.9 Refaire les extractions

```
acr-ref export-many --game Z:\acrxs\construction\vanilla --usmap Z:\acrxs\mappings\acr_25170642.usmap ^
  --filter "Data/Database/Main/(Common|TrackSelection|Options)/|PhysicsGlobalSettings|BC_DynamicSurfaceManager|DA_StartingGripOption|PhysicalMaterials/(DA_|FC_|PM_Surface)|Data/Weather/|Data/Vehicles/Common/DA_.*Dirt" ^
  --out <dossier>
```

Pour les tables telles que le jeu du directeur les charge (avec le mod « registre »), mettre `--game` sur le dossier du jeu. Attention, `acr-ref` ne lit pas le dossier `~mods`.
