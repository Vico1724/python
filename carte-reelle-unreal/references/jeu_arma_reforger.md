# Arma Reforger : livrer une carte réelle (Enfusion / Workbench, ce n'est pas Unreal)

Expérience vécue : carte « Hangar » / La Ciotat (terrain de 4 096 m), 11 au 17/11/2026, jeu 1.9.0.37. La chaîne de DONNÉES (contour, LiDAR, ortho, vecteurs, arbres) est celle des projets Unreal ; seul le compilateur final change : au lieu d'un niveau Unreal, on écrit des fichiers texte (couches) et des tuiles de terrain que le Workbench charge.
Balises : **[vu]** = constaté ; **[déduit]** ; **[NV]** = non vérifié.

## Table des matières
1. Chaîne Enfusion / Workbench
2. Formats rencontrés
3. Import du terrain
4. Prefabs du jeu utilisés, par catégorie
5. Génération des couches
6. Publication Workshop
7. Plantages rencontrés et causes
8. Pertes de retouches et parade

---

## 1. Chaîne Enfusion / Workbench

- **Outils** : Arma Reforger + Arma Reforger Tools (Steam, gratuits, 1.9.0.37) ; Workbench `ArmaReforgerWorkbenchSteamDiag.exe -addonsDir "<JEU>/addons" -gproj <projet>/addon.gproj -wbmodule=ResourceManager -plugin=<Plugin>`, piloté par `workbench.ps1` (`-Fin "LC_…: fin"`, `-Captures N -Sortie`). Plugins de projet en Enforce Script (`scripts/WorkbenchGame/LaCiotat/LC_ReliefPlugin.c`, `LC_RoutesPlugin.c`, `LC_MondePlugin.c`). **Lancé hors Steam, le Workbench ne trouve pas le jeu sans `-addonsDir`** (« Missing Addon »).
- **Générateur de base** : un générateur de carte Reforger public (MIT, testé 1.9.0.37) a servi de source de formats et d'identifiants ; non utilisé tel quel (il retombe sur un relief à 30 m en France). GameRealisticMap ne vise qu'Arma 3 : vérifier la plateforme cible avant de retenir un outil.
- **Repère** : x Est, z Nord, y altitude ; lacet = azimut de l'axe Z du modèle (0 = nord, 90 = est) ; terrain 2 048 × 2 048 faces de 2 m = 4 096 m, altitudes −6,6 à 266,6 m, 0 = mer (au sud) ; zone jouable centrée en (x 2 048 ; z 3 196), à 900 m du bord nord ; le terrain s'arrête à 2 km E/O et 900 m N (au-delà, le moteur affiche la mer) ; pas d'arbre réel au-delà de ~300 m de la zone (forêt tirée au sort jusqu'à 700 m).
- **Étapes** : `11_reforger.py` (projet complet : terrain, sols, couches) → `12_verifier_identifiants.py` → `terrain_reforger.py` + plugins (terrain, routes) → `captures_reforger.py` → `Workbench -packAddon` → fenêtre « Publish Project ». Constructions déterministes (hash de position, jamais de graine globale) pour pouvoir rejouer.
- **Un projet généré par script n'est pas validé tant qu'il n'a pas été ouvert dans le Workbench** : la génération seule ne garantit rien (état du 12/11 : « jamais ouvert »).
- **Ce que le jeu n'a pas** (1.9.0.37 : 698 modèles de végétation, 20 202 prefabs `.et`) : pin d'Alep, garrigue, figuier de Barbarie, tractopelle/pelle, piscine, bloc taillé, éboulis angulaire de 1 m, dalle de béton posée, poutrelle, front de taille en gradins ; végétation d'Europe centrale, rochers en granite seulement. Substituts signalés comme écarts (grue épave, granite recoloré en calcaire, piles de dalles).

## 2. Formats rencontrés

| Format | Rôle / contenu |
|---|---|
| `addon.gproj` | `GameProject { ID, GUID, TITLE, Dependencies {"58D0FB3206B6F859"} }` ; toute dépendance absente du PC = mod qui ne charge pas (« can't load world ») |
| `.ent` + `.ent.meta` | monde ; `.ent` vide normal ; **GUID du monde dans le `.meta`** |
| `*.layer` (texte, **LF, sans BOM**) | couches d'entités : `$grp Tree : "{GUID}chemin.et" { { coords x y z … } }`, angles `angles 0 a 0`, hauteur relative au sol (y = 0) pour la végétation, absolue pour véhicules/objets (`pose`) ; le Workbench réécrit les couches en groupes `$grp` à l'enregistrement |
| `.conf` mission | `SCR_MissionHeader { World, SystemsConfig "{8DDC2A311929D52F}…GameMasterSystems.conf", m_sName, m_sGameMode, m_iPlayerCount 16 }` + `.conf.meta` ; régler latitude, longitude et fuseau du lieu sinon 14 h tombe à la nuit |
| `.emat` + `.emat.meta` | matière **héritée** d'une matière du jeu, seules les couleurs changent (`MatPBR2Layers : "{GUID}Assets/…emat" { Color r g b 1 }`, valeurs > 1 acceptées pour éclaircir) ; 23 matières `LC_*` ; surcharge sur entité fille : `GenericEntity { ID "<ID fille>" components { … } }`, nom de slot = chemin lu dans le `.xob` |
| `.xob` | modèle : noms des slots de matière dans les premiers octets (`pak_reforger.py`) |
| `.et` prefab | `GUID` 16 hex + chemin ; **classe lue à la racine de la chaîne d'héritage** ; pose au sol si le prefab ou un parent porte le drapeau 0x80000 |
| `.asc` + `.zip` | relief 2049×2049, maille 2 m, 1re ligne = nord ; import « Invert Z axis » coché, « Resample » décoché ; vérifier la mer au sud |
| `Terrain.terr`, `Terrain_N.ttile` (HGHT 129×129 uint16, BERR, GCTD, LRS2, TMAT), `.bterr` | tuiles : entiers petit-boutistes, N = tz × tuilesParCôté + tx, lignes sud→nord, hauteur = entier × 0,03125 + zéro (−204,78125) ; 256 tuiles, blocs de 33 points ; tuile gabarit tirée d'un terrain d'exemple public |
| `surface_*.png`, `satellite_map.png` | masques de sol 8 bits (asphalte, terre, pinède, roche) et image aérienne 2 m/px (« Linear Color Space » désactivé) ; tuiles satellite : première ligne = sud |
| `resourceDatabase.rdb` | index des ressources du jeu (GUID ↔ chemin) ; son parseur échoue sur certains genres → les traiter en champ de bits |
| Terrain d'exemple et `ServerData.json`, `*_manifest.json` | structure d'un mod téléchargé du Workshop : lue, inutilisable pour installer à la main |

## 3. Import du terrain

- **À la main** (méthode d'origine) : Create New Terrain 2 048 × 2 048, 2 m, échelle de hauteur 0,03125 ; Import Height Map ; Import Satellite Map ; peinture Grass_01 en base puis `surface_asphalt`/`rock`/`pine_floor`/`dirt`.
- **Méthode finale, sans souris** : `terrain_reforger.py terrain <gabarit> <Worlds> <heightmap.asc>` (écrit les tuiles v9 : 9 réels par bloc BERR au lieu de 11) → `LC_ReliefPlugin` (le Workbench charge et réécrit) → `controle` (relief relu à 1,5 cm près) → `textures_terrain.py satellite` → `terrain_reforger.py sols` (masques + flou) → `LC_RoutesPlugin`. Le terrain ne s'écrit pas en couches : on remplace les hauteurs d'une tuile gabarit.
- **Matières de sol** : ≤ 5 par bloc ; **TMAT à 5 matériaux = « LoadQuadMaterials bad data » et plantage** → un seul matériau de base dans TMAT, LRS2 à 5 matériaux (rendu correct). Masques part : asphalte+bâti 13 %, roche 0,2 %, pinède 33 %, terre 24 %.
- **Routes** : un générateur de route ne fabrique la chaussée que lorsqu'il est créé ou modifié → `LC_RoutesPlugin` réécrit la largeur de chaque générateur ; **tous en `AdjustHeightMap 0`** (sinon les routes retaillent le terrain sculpté) ; « invalid segments » sur ~14 routes ; les générateurs écrits dans le texte d'une couche ne s'affichent pas.
- **Limites** : un seul terrain par monde ; imports très grands (32,5 km) en échec sur le suivi du studio en 2024 [`modding_par_jeu.md` §6].

## 4. Prefabs du jeu utilisés, par catégorie

**Jamais de GUID ni de chemin deviné** : lire l'index du jeu (`12_verifier_identifiants.py`, 0 défaut sur 189 références), **mesurer chaque modèle dans le Workbench** (boîte englobante → `tailles_*.csv`), choisir par dimensions et axe long, recolorer par `.emat` hérité. Les CSV `config/reforger_*.csv` portent les GUID vérifiés ; liste détaillée dans `catalogue_assets.md` §c.

| Catégorie | Prefabs (sous `Prefabs/…`) | Remarque |
|---|---|---|
| Pins | `Vegetation/Tree/t_pinus_sylvestris/*` (23 mesurés, 22 retenus, 2,2 à 28,9 m) | pin sylvestre à la place du pin d'Alep ; le choisir pour que la hauteur rendue = hauteur réelle |
| Arbustes, fouillis | `Vegetation/Bush/b_juniperus_communis_*` (genévrier `81EE8FAE7539DAA1`), `Calamagrostis_epigejos`, `c_branches_debris_*`, `GravelPile_01_*`, `Pallet_01`, `DebrisPile_*`, `TirePile_01_small` | pose `sol` (végétation) ou `absolue` (bazar) |
| Bâtiments | 37 maisons (`House_Village_E_1I01…`, `FarmHouse_E_1L01`, `Villa_E_2I01`, `House_Wooden_*`), 46 utilitaires (`ShedMetal_*`, `Warehouse_01`, `Garage_E_01`) | seulement 9 modèles pour 49 bâtiments BD TOPO : approximation ; hangar `Warehouse_01` (41×19 m) retourné de 180° (grande porte côté nord-est) ; `batiments_imposes.csv` impose modèle, rotation, décalage |
| Rochers | `Rocks/Granite/*` (blocs, éboulis, pierres, `GraniteCliff_01/02`) | recolorés en calcaire par `.emat` hérité ; sable posé sur des rochers : rejeté |
| Objets, engins | `Props/Industrial/CompressorTrailerWreck_01`, `ConcretePanel_01_stack`, `Lathe_01`, `BenchDrill_01_set`, `BenchIndustrial_01`, `Props/Wrecks/BoatWreck_01`, `GarbageStack_01`, `PlankPile_01`, `BrickPile_01` | pas de tractopelle : épave de compresseur jaune ; la grue épave a été rejetée |
| Véhicules | `Vehicles/Wheeled/S105/*`, `S1203_cargo_white`, `UAZ452_cargo_CIV_grey`, `Ural4320_transport_CIV`, `M151A2`, `ArsenalBox_US` | |
| Routes | `WEGenerators/Roads/Asphalt/RG_Road_Asphalt_E_01_Narrow`, `RG_Road_Concrete_USSR_01_narrow`, `RG_Road_Dirt_01`, `RG_Road_Forest_01`, `RG_TrailDirt_01`, `RG_TrailGravel_01` | largeur du modèle (8 m) ramenée à la largeur BD TOPO |
| Sols (`Terrains/Common/Surfaces/`) | `Grass_01`, `Asphalt_01`, `Rock_01`, `ForestPine_01_Base`, `Dirt_01`, `Dirt_02`, `Concrete_02`, `MountainGrass_02` | `Debris_Rock_01` (gris) rejeté → `Dirt_02` |
| Mode et apparition | `MP/Modes/Editor/GameMode_Editor_Full.et`, `MP/Spawning/SpawnPoint_US.et`, `Screenshot_Autotest` | voir §5 |
| Décalques, particules | `Decal_Puddle_01_*`, `Decal_Dirt_Patch_*`, `Coal_Dust.ptc`, `Dust_Motes_Long.ptc` | **sans effet visible** en jeu, retirés |

## 5. Génération des couches

- **Un script par couche** (`reforger_arbres/batiments/rochers/routes/fouillis/objets/murs/alentours/matieres.py`) : choix de modèle par taille mesurée, semis reproductible, matières héritées. Un bâtiment refusé fait échouer le script (pas de sortie partielle). Couches du projet : 13 fichiers (~8 Mo de texte), 5 117 arbres réels → 4 962 pins, 9 389 genévriers, 49 bâtiments, 68 tracés de routes ; 52 000 à 75 564 entités selon la passe.
- **Règles de pose** : enfoncement 3-12 cm (+10-18 % de la hauteur pour les rochers) ; inclinaison ≤ 25° ; arbres écartés de 3 m des murs ; hors du cœur : 6 m des routes, 3 m de l'existant, pente < 0,6 m ; rien ne doit flotter (« les herbes qui lévitent : jamais »).
- **Fichiers de configuration à colonne `raison`** (traçabilité : qui a demandé quoi, quand) : `zones/zone_N.csv` (objets à la pièce, **font foi dans leur emprise**), `batiments_imposes.csv`, `routes_imposees.csv`, `sols_imposes.csv`, `zones_degagees.csv` (38 lignes), `aplats.csv`, `eboulis_denses.csv`, `murs.csv`, `pistes.csv`, `alentours.csv` (8 hameaux et 5 lieux isolés, 477 entités, 75 prefabs, rendu non vérifié).
- **Zones pour sous-agents** : 5 zones, un sous-agent chacun avec son extrait d'ortho 20 cm quadrillé (10 px/m, maille 10 m) ; livrable `zone_N.csv` + rapport en 4 points (vu / déduit ; bâtiments à corriger ; rectangles à dégager ; ce que le jeu n'a pas). L'assembleur relit et installe.
- **Mode de jeu** : `GameMode_Editor_Full.et` + `SCR_AIWorld` et gestionnaires du parent copiés (MapEntity, CameraManager, météo, son, destruction, radio, musique) ; ajouter les `SystemsConfig` des en-têtes officiels ; positions de caméra de départ ; `ArsenalBox_US` + 2 `M151A2`. **Une carte seule ne se lance pas** : il faut une mission complète (points d'apparition, couches, configuration). Les scénarios officiels sont en `.ent` binaire (on n'y lit que des noms de classes).
- **Faction jouable** : `FactionManager_Editor` met US/USSR/FIA en `m_bIsPlayable 0` → surcharge à 1 sur l'ID `56E685E92F1B7E7A` ; un mod de soldats français redéfinit la faction US (dépendance à ajouter au `.gproj` ; tout joueur doit avoir les mêmes mods : risque majeur). Navmesh : « No navmesh file specified », l'IA ne bouge pas, **non résolu**.
- **Retouches à usage unique** (`aplanir.py`, `relief_jeu.py`, `bosses_carriere.py`, `terrasse_piscine.py`) : ne pas relancer sans lire `constats.md`.

## 6. Publication Workshop

- **Jouer dans le vrai jeu exige de publier** : aucune option du client ne charge un monde local ; un scénario local non publié n'apparaît pas dans le menu ; déposer le mod à la main dans `addons/` échoue (« Resource F07E3E0F99DD1F89 not found », exceptions `SCR_WorkshopAddonLineComponent.HandleDownloadChanges`, le jeu cherchant la ressource sur le Workshop). Le script d'installation locale a été retiré.
- **CLI** `-publishAddon -publishAddonDir … -publishAddonVersion … -publishAddonChangeNote … -publishAddonPreviewImage …` : refusée (« Game Identity is not linked with Bohemia Account ») ; compte lié à un compte Google sans mot de passe (`userService.noPassword`, message de jeu générique « vérifiez votre connexion internet ») ; puis `data.asset should have required property 'summary'` ; la CLI ne règle pas la visibilité (publication publique par défaut) → **première publication par la fenêtre Workbench > Publish Project** (Summary obligatoire, visibilité Private/Unlisted/Test, aperçu 1280×720 JPG ≤ 2 Mo). Réussie le 14/11 à 17 h 10 par le joueur en **non listé**, nom « Hangar », 1.0.0, `data.pak` ~130 Mo ; vérifier avant envoi qu'aucun nom d'utilisateur ni chemin absolu ne figure dans les fichiers.
- **Demander avant toute publication** (règle du joueur) ; la publication est un geste de compte, à lui.
- Après publication [vu 14/11] : le mod apparaît dans le Workshop du jeu et la partie se lance.

## 7. Plantages rencontrés et causes

| Symptôme | Cause | Parade |
|---|---|---|
| Workbench plante au retour du mode jeu (rapport envoyé à l'éditeur, avec des fichiers du PC) | plugin `WorldTestPlugin` | arrêter le Workbench avant ce retour ; fermer la fenêtre pour quitter |
| « Script Authorization Required » bloque | tout script de projet qui lit/écrit un fichier (`FileIO`) ou capture (`MakeScreenshot`) | écrire les tuiles hors Workbench, captures par `Screenshot_Autotest` ; `-scriptAuthorizeAll` **refusé par le garde-fou, ne jamais l'utiliser** |
| `LoadQuadMaterials bad data` | TMAT à 5 matériaux | un seul matériau de base |
| Chargement de la carte plante, scripts cassés | mod tiers de vision nocturne non compilable en 1.9 (`Variable name conflict 'a'`), ou dépendance absente (`NV-System`) | activer seul le mod carte |
| Couche mal formée refusée | mauvais indice d'accolade du premier script de routes | contrôle du format avant écriture |
| « Huge number of entities per scene tree leaf » à chaque image | cause non trouvée (ni le nombre d'objets, ni un modèle) ; disparue après réduction des pins lointains et resauvegarde [NV] | surveiller |
| Plantage à l'accès, rapport Windows `Access violation. Illegal read` en 1.9.0.37 (14/11 19 h 33) | **non établie** ; le joueur a confirmé ensuite que « ça marche » | conserver le rapport |
| « Game addon … not found » | client lancé depuis le mauvais dossier | `-WorkingDirectory` = dossier du jeu |
| Terrain/captures à l'envers | tuiles satellite : première ligne = sud ; lacet ; `Invert Z axis` | contrôle visuel de la mer au sud |
| Captures détournées | couche Game Master | l'outil écarte `jeu.layer` pendant les captures |

Outillage : le Python du PC était 32 bits sans bibliothèques (forêt non régénérable) ; `py -I -X utf8` + `sys.path.insert` avant les imports ; JSON avec BOM → `utf-8-sig` ; `Select-Object -First` coupe `workbench.ps1` en cours ; les scripts Enforce n'ont pas d'opérateur `%` ; heredoc Bash abîme les antislashs ; git sans identité : `git -c user.name=… -c user.email=…`.

## 8. Pertes de retouches et parade

- **Le joueur sculpte et déplace à la main** : les couches installées dans le projet du Workbench **font foi**, pas celles du dépôt. Régénérer écrase ses retouches.
- **Incidents** : 12/11 13 h 11 et 13/11 21 h 56 : monde enregistré vide (`default.layer` écrasé, 11 couches perdues) parce que le Workbench du joueur sauvegardait pendant que l'assistant copiait des couches → restauration depuis le dépôt (`git archive`, LF). 12/11 13 h 18 : `workbench.ps1` a fermé la session Workbench du joueur.
- **Parade** : (1) vérifier qu'aucun Workbench n'est ouvert avant toute opération, ne jamais fermer celui du joueur ; (2) copier d'abord les couches du projet installé vers le dépôt, puis seulement régénérer ; (3) ne plus régénérer objets, rochers, arbres après une retouche manuelle ; (4) ne **jamais** relancer `relief_jeu.py`, ni `terrasse_piscine.py`/`bosses_carriere.py` sans relancer `aplanir.py` ; (5) `recaler_au_sol.py` (idempotent, `--essai`) pour les entités laissées à l'ancienne altitude après sculpture (flottantes ou enterrées jusqu'à 3,8 m ; ne touche ni portes, fenêtres, bâtiments, murs) ; (6) sauvegarder avant toute opération lourde.
- **Non vérifié [NV]** : apparition en soldat, arsenal, tenue après une mise à jour du jeu, fluidité, navmesh, décalques de boue et poussière (invisibles), orientation de façade (+Z supposée), tailles d'objets estimées. Verdict du joueur le 12/11 : « pas super belle » ; la carte publiée « marche » le 14/11.
