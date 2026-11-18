# Modding par jeu : par quelle voie une carte Unreal entre dans un jeu

Relevé du 17 novembre 2026 (recherche web + pages GitHub/Steam, lecture seule, rien téléchargé ni exécuté).
Légende : **[V]** = lu à la source citée à cette date ; **[C]** = communauté / presse / extrait de recherche, non recoupé ;
**[NV]** = non vérifié (non trouvé, page inaccessible, ou de mémoire). Une page GitHub sans date de release lisible = état « actif » **[NV]** sur la fraîcheur.
Les scènes bougent chaque semaine : rouvrir la source avant d'agir, ne pas se fier à ce fichier pour une version précise.

## Table des matières
1. Méthode pour un jeu inconnu
2. Boîte à outils Unreal générique
3. Assetto Corsa Rally (ACR)
4. Bodycam
5. Dragon Ball: Sparking! Zero
6. Autres familles (tableau)
7. Du niveau Unreal « neutre » au jeu cible
8. Points non vérifiés (récapitulatif)

---

## 1. Méthode pour un jeu inconnu

Répondre dans l'ordre ; s'arrêter dès qu'une voie officielle existe.

### 1.1 Kit officiel ? (5 minutes)
- Chercher : « <jeu> SDK », « <jeu> modkit », « <jeu> Workshop », « <jeu> mod.io », page Steam (onglet Workshop), Epic Games Store (outils « DevKit »), wiki du jeu.
- Une annonce du studio vaut plus que tout : lire les notes de version Steam via l'API publique
  `https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=<ID>&count=10&maxlength=3000` (texte brut des annonces). **[V]** (marche en novembre 2026)
- Si kit officiel : c'est la voie. Le reste de la méthode ne sert qu'à comprendre ses limites (taille, matériaux autorisés, version moteur imposée par le kit).
- Sinon : voie communautaire, fragile, à refaire à chaque mise à jour du jeu (cf. ACR 0.6 et Bodycam 0.9 ci-dessous).

### 1.2 Moteur et version exacte
- Propriétés de l'exécutable (`<Jeu>-Win64-Shipping.exe` > Détails) : « Version du produit » donne souvent `5.x.y-CL+++UE5+Release-5.x`. Sinon chaîne `++UE5+Release-` dans l'exe (`strings`).
- Fichiers : `Engine/Binaries/ThirdParty`, `<Jeu>/Config/DefaultEngine.ini` (rarement lisible), taille/présence de `Engine/Content/…`.
- Bases communautaires : SteamDB (technologie, dépôts), PCGamingWiki, notes de version du studio, fiches Nexus/GitHub des mods (« Unreal 5.1.1 », « 5.5 pas 5.6 »).
- La version **mineure** compte (5.5 vs 5.6 : sérialisation et formats IoStore différents). En cas de doute : cuire un niveau vide à la version supposée et tenter de le charger.
- Exemples relevés : Bodycam UE 5.5 **[V]** ; ACR UE 5.6 depuis la 0.6 **[V]** ; Sparking Zero UE 5.1.1 **[C]**.

### 1.3 Archives et chiffrement
- Dossier `<Jeu>/Content/Paks/`. Présence de `.pak` seuls (UE4 / début UE5) ou de triplets `.pak` + `.utoc` + `.ucas` (**IoStore**, format Zen ; UE5 courant). Un jeu peut mélanger : les `.pak` « legacy » d'un mod sont acceptés à côté d'un IoStore, c'est ce qu'exploitent la plupart des chaînes de mods.
- Chiffrement : la liste des fichiers s'ouvre-t-elle sans clé (FModel / `repak list`) ? Si non, le jeu est chiffré en AES-256 ; la clé n'est pas à « casser » : on n'utilise que ce que la communauté du jeu publie pour le solo. Ne jamais recopier une clé dans ce dépôt.
- Fichiers `.sig` à côté des paks = signature de pak activée : un pak non signé peut être refusé ou faire planter. Ne pas contourner (cf. § 1.6 et Bodycam).
- **Mappings `.usmap`** : requis pour lire/écrire les assets à propriétés « non versionnées » (UE5 cuit sans tables de propriétés). Se génèrent avec le dumper d'UE4SS ou Dumper-7 sur le jeu **lancé en solo**, ou se téléchargent s'ils sont publiés par la communauté du jeu.

### 1.4 Chargeur de mods, dossier `~mods`, ordre de chargement
- Dossier `Content/Paks/~mods/` (créé à la main) : chargé après les paks du jeu. Sinon, dans `Paks/` directement avec un nom qui trie après le jeu.
- Ordre : les paks sont montés par priorité ; **suffixe `_P`** (patch) = priorité supérieure ; plus le nom trie tard (`zz…_P`), plus il écrase. Deux mods qui remplacent le même fichier : le dernier gagne (pas de fusion) — un mod qui remplace une table de menu en entier écrase celle d'un autre mod.
- Chargeurs : UE4SS (DLL injectée, scripts Lua / LogicMods Blueprint) ; Reloaded-II ; mod managers du jeu. Une DLL injectée est précisément ce qu'un anti-triche (EAC, BattlEye) bloque : voir § 1.6.
- Certains jeux ignorent silencieusement un pak non signé / non reconnu : tester avec un mod minimal (une texture remplacée) avant d'investir.

### 1.5 Niveau ajouté ou niveau remplacé ? Comment le menu référence les cartes
1. Lister (FModel) les `DataTable` / `DataAsset` du menu : `DT_Levels`, `DT_Maps`, `DA_Map*`, `UI/MetaData`, `DT_UI_*Maps`, registre de pistes, etc.
2. Trois cas : (a) **ajout** d'une ligne dans une table de menu (mod de carte « propre ») ; (b) **remplacement** d'un niveau existant (même chemin `/Game/Maps/X.umap`, simple mais détruit la carte d'origine) ; (c) liste **côté serveur** (matchmaking, jeu en ligne) : une carte locale n'y apparaîtra jamais.
3. Une table remplacée l'est en entier : l'ajout de lignes se fait en repartant de la table **exacte** de la version courante du jeu (re-extraire après chaque mise à jour).
4. Un niveau peut se charger par commande console / `OpenLevel` / argument de lancement, mais cela ne prouve rien pour le menu.

### 1.6 Règles et sécurité (non négociables)
- Lire CLUF / conditions d'utilisation et la FAQ du studio. Certains éditeurs bannissent (Bandai Namco pour Sparking Zero, § 5).
- **Jeu multijoueur compétitif en ligne : ne rien modifier.** Rester en solo, en parties privées/hôte, ou sur serveurs qui l'autorisent. Pas de DLL injectée sous anti-triche, **aucun contournement d'EAC/BattlEye/signature de pak/DRM**, aucun déchiffrement hors de ce que la communauté du jeu documente publiquement pour le solo.
- Ne **pas redistribuer** de contenu du jeu : paks dérivés = usage personnel (ACR Extra Stages le dit explicitement). Livrer des outils et des scripts, pas des assets du jeu.
- Avant toute écriture : copier `Paks/` (ou au minimum les fichiers touchés) dans `Paks/_backup/<date>/` ; noter la version/build du jeu (`buildid` Steam) ; retour arrière = supprimer le dossier `~mods` ou les `z*_P.pak`, puis « Vérifier l'intégrité » Steam.
- Se méfier du bruit de recherche : beaucoup de dépôts « <jeu> mod/trainer/overlay » sont des triches ou des logiciels malveillants. N'exécuter que des outils dont on a lu la source ou la page officielle ; exécutables non signés = avertir l'utilisateur.

---

## 2. Boîte à outils Unreal générique

Dates de release non récupérables (API GitHub refusée, pages sans date) : « actif » = le dépôt est public, non archivé, avec des milliers de commits au relevé du 17/11/2026 **[V]** ; fraîcheur exacte **[NV]**.

| Outil | Rôle | URL | État 2026 |
|---|---|---|---|
| FModel | Explorer les paks/IoStore, exporter assets en JSON/glTF/textures, repérer les chemins à référencer | https://github.com/4sval/FModel | UE4 et UE5, « activement maintenu », 1 798 commits [V] |
| CUE4Parse | Bibliothèque C# de lecture d'archives/assets (base de FModel), pour scripter | https://github.com/FabianFG/CUE4Parse | UE4/5, Apache-2.0, 3 118 commits [V] |
| UE4SS (RE-UE4SS) | Chargeur Lua/Blueprint injecté + dumpers (SDK, `.usmap`) | https://github.com/UE4SS-RE/RE-UE4SS | « de 4.7 à 5.8 », 2 244 commits ; les builds « stables » traînent : Bodycam 5.5 a exigé une version expérimentale [V/C]. Interdit sous anti-triche |
| Dumper-7 | Générateur de SDK C++ (injecté dans le jeu en solo) ; utilisé pour obtenir un `.usmap` | https://github.com/Encryqed/Dumper-7 | « tout UE4 et UE5 », 902 commits [V] ; la page lue ne mentionne pas la sortie `.usmap` [NV] (ACR Extra Stages la cite comme alternative [V]) |
| retoc | Lire/écrire l'IoStore (`.utoc/.ucas`), convertir Zen <-> legacy (`to-legacy`, `to-zen --version UE5_x`), `unpack`, `pack-raw`, `info`, `list`, `verify` | https://github.com/trumank/retoc | « UE 5.3+ bien supporté », avant 5.3 dépendances parfois manquantes [V] ; 372 commits ; aucune release listée sur la page [NV] |
| repak | Lire/écrire des `.pak` (CLI Rust : list, unpack, pack, get ; AES et compressions) | https://github.com/trumank/repak | 213 commits, public [V] |
| UnrealPak | Outil officiel de l'éditeur (`Engine/Binaries/Win64/UnrealPak.exe`) : lister/extraire/créer des paks | fourni avec Unreal Engine (Epic Games Launcher) | stable ; utilisé en lecture seule pour extraire des tables (cf. veille Bodycam) [V local] |
| UnrealReZen / ZenTools | Réinjecter des assets legacy dans un IoStore existant (UnrealReZen) ; extraction (ZenTools GUI) | https://github.com/Amrsatrio/UnrealReZen | dépôt cité par les guides Sparking Zero ; page non relue à jour [C/NV]. Souvent remplacé par retoc |
| UAssetAPI / UAssetGUI | Lire/modifier `.uasset/.uexp` à la main ; supporte `.usmap` (chargement par chemin dès v1.1.1) | https://github.com/atenfyr/UAssetGUI (API : https://github.com/atenfyr/UAssetAPI) | « mature, stable », MIT, build expérimental à chaque commit [V] ; UAssetAPI [NV, non relu] |
| kismet-analyzer | Analyse/modification du bytecode Kismet (graphes de flux) d'assets cuits | https://github.com/trumank/kismet-analyzer | MIT, 110 commits, pas de release, activité inconnue [V/NV] |
| umodel (UE Viewer) | Visionneuse/export de meshes, textures, animations | https://github.com/gildor2/UEViewer | README : « moteurs 1 à 4 » ; UE5 **non confirmé** [NV]. Préférer FModel en UE5 |
| Projet Unreal « factice » | Projet à la **même version moteur** que le jeu, avec des assets fantômes (même chemin `/Game/...`, même type, contenu vide) pour référencer les assets du jeu sans les redistribuer | à construire ; modèle : kit Bodycam https://github.com/Lovac/bodycam-map-kit (`BodycamNativeStubs`) | voie validée pour Bodycam [V] ; « non prouvée » pour ACR selon ACR Extra Stages (cf. note projet) [C] |
| Cuisson | `UnrealEditor-Cmd.exe <proj>.uproject -run=cook -targetplatform=Windows -iterate` (ou UAT `BuildCookRun -cook -stage -pak -iostore`) | documentation Unreal Engine (dev.epicgames.com/documentation) | standard |
| Pak / IoStore final | `-pak` (paks) ; `-iostore` ou `retoc to-zen` pour le Zen ; nommer `zz<Nom>_P.pak` | idem | selon le jeu |

### Règle d'or
Cuire avec **exactement** la même version de moteur (mineure comprise : 5.5 n'est pas 5.6) et les mêmes réglages de sérialisation que le jeu : paks vs IoStore, propriétés non versionnées (`-unversioned`, besoin du `.usmap`), compression Oodle, version de pak (11 pour Bodycam [V local]), plateforme Windows. Une erreur se manifeste par : mod ignoré en silence, matériaux gris, crash au chargement du niveau. Après chaque mise à jour du jeu : ré-extraire, vérifier la version moteur, recuire (cf. « updating-after-a-patch » d'ACR Extra Stages).

Oodle : bibliothèque propriétaire, non redistribuable ; les outils la récupèrent depuis l'installation du jeu / l'éditeur.

---

## 3. Assetto Corsa Rally (Supernova / 505 Games)

- **Moteur** : UE 5.4 puis **UE 5.6 depuis la v0.6** (déclaration Supernova du 11/09/2026) [V : https://traxion.gg/why-assetto-corsa-rallys-v0-6-update-was-more-important-than-first-thought/]. Catalogue du projet : build 25170642 (47 246 éléments) [V local, note du 10/11/2026].
- **Officiel** : seule la **livrée (livery)** est supportée (0.6, doc dans `acr\Content\LiveryTemplates`) ; cartes/spéciales « non confirmées » ; Supernova « construit un support officiel » et affirme « aucune détection de mod ni DRM ajoutés en 0.6 » [V/C : https://support.505games.com/support/solutions/articles/150000233496-assetto-corsa-rally-early-access-update-0-6 (404 au relevé, contenu via recherche) ; https://boxthislap.org/assetto-corsa-rally-takes-first-step-toward-mod-support/ (bloqué, non lu)].
- **Les mods pak ont cassé avec la 0.6** : refaire l'extraction, régénérer les mappings, utiliser des outils compatibles 5.6 [V traxion].
- **ACR Extra Stages** : https://github.com/cherrymcgerry/acr-extrastages (forks : nitnerolf420/acr-extrastages, fbenniks/acr-extrastages). Convertit des spéciales **de votre propre DiRT Rally 2.0** en spéciales ACR ; v0.1.0-beta.1 (pré-release du 23 oct., zip pas encore publié au moment de la lecture : compiler depuis les sources) [V]. Sortie : paks `zz_acrxs_*` dans `acr\Content\Paks\~mods\` + un registre de menu ; crée le fichier de mappings au premier lancement (ACR démarre brièvement) ou accepte un `.usmap` Dumper-7. 106 spéciales sur 13 lieux (30 par défaut ; les 50 autres > 9 km non constructibles). ~0,7 Go par spéciale, ~15 Go d'espace de travail ; jeu et sources sur le même volume NTFS (liens physiques). **Solo hors ligne uniquement, ne pas redistribuer** [V]. N'est **pas** un outil de création depuis zéro [V]. IoStore/retoc non mentionnés sur la page [V].
- **BioBio / SandoChlBio** (autre pipeline, auteur tiers) : niveau simple (pas de Landscape/World Partition), terrain en dalles de maillages 44x44, 1 texture + 1 matériau par dalle, `DA_..BakedData` (physique de roulage), `DT_Pacenote..`, registre qui **remplace entièrement** 6 tables de menu (`DT_Levels`, `DT_Tracks`, `DT_TracksLocations`, `DT_TracksVariants`…) ; arbres/herbe/panneaux appelés par chemin dans le jeu ; matériaux = variantes de matériaux du jeu (pas de shader maître) ; la notice cite retoc [V local, analyse du 10/11/2026 sur les sommaires d'archives]. Un exporteur « WRC Generations vers ACR Sando Rally » existe sur Patreon (page non lisible, 403) [C/NV : https://www.patreon.com/AlbertPalahi/posts/wrc-generations-175220013].
- **acr-ref** : introuvable sur le web (aucun dépôt de ce nom trouvé) **[NV]**. Ne pas citer sans confirmation ; chercher à la place les docs de `acr-extrastages` (`docs/updating-after-a-patch.md`, `CONTRIBUTING.md`).
- **Chargement d'une spéciale personnalisée** : paks dans `~mods` ; niveau + `BakedData` + table de notes + lignes de registre (`DT_Levels`/`DT_Tracks`…) ; surfaces de roulage `PM_Surface*` du jeu ; apparition en « Free Practice » (à valider) [C/V local].
- **Limites** : mises à jour Early Access fréquentes = reconstruire ; registre en remplacement total donc incompatible entre mods (fusionner les lignes) ; usage en ligne/classements non documenté **[NV]** : rester hors ligne ; format exact de `BakedData` et des notes : seulement partiellement documenté **[NV]**.

---

## 4. Bodycam (Reissad Studio)

- **Moteur** : UE 5.5 (migration depuis 5.2 annoncée aux notes v0.7.0 du 25/11/2025) [V local]. Les outils communautaires exigent « 5.5, pas 5.6 » [V : https://github.com/Lovac/bodycam-map-importer]. Moteur de la v0.9 non annoncé ; rien n'indique un changement **[NV]**.
- **Versions** : v0.9 « The Dead & Damned » sortie le **13/11/2026** (build Steam 26647288 ; l'ancien kit visait 25505592) ; v0.9.1 le 16/11/2026 (correctifs EAC, plantage, Zombie Asylum) [V : API Steam appid 2406770, relevé 17/11/2026].
- **Kit officiel / Workshop** : **aucun** (réponse de l'équipe contenu du studio, 08/11/2025 : « pas de Workshop ni de support de mods ») [V : https://steamcommunity.com/app/2406770/discussions/0/666096879248883626/]. Rien dans les notes v0.8, v0.9, v0.9.1 [V]. « Creative 2.0 » = UEFN de Fortnite, pas Bodycam ; il existe une île officielle « Bodycam FPS » dans Fortnite (code 9784-3946-5466) [C : https://fchq.io/map/9784-3946-5466/bodycam-fps].
- **Anti-triche** : **Easy Anti-Cheat actif depuis la v0.9**, « intégré aux parties multijoueur P2P PC », décrit comme première brique [V : annonces Steam 13/11 et 16/11/2026]. Aucun lancement officiel sans EAC documenté (une seule option de lancement) [C]. Ne pas utiliser les « EAC bypass » des forums de triche.
- **Voie communautaire pré-v0.9** : Bodycam Map Importer v0.2.1 (6/11/2026, MIT) + Map Kit (UE 5.5 + Git Bash + Python/Pillow, projet `BodycamSandbox.uproject`, `Scripts/newmap.sh`) par un auteur tiers : https://github.com/Lovac/bodycam-map-importer , https://github.com/Lovac/bodycam-map-kit , exemple https://github.com/Lovac/prison-v2p-project [V]. Sortie : plusieurs `.pak` (`z<Nom>_9_P.pak`, `zzMapCards_19_P.pak`) dans `Bodycam\Content\Paks`, carte visible dans Play > Custom ; 7 modes (Hardpoint, TDM, DM, Versus, Gun Game, Body Bomb, Wingman) ; niveau avec `PlayerStart` tagués 1/2, 1 DirectionalLight, 1 SkyLight ; assets dans `Content/Sandbox/<Nom>/` ou chemins du jeu ; « quelques centaines de mètres » ; **parties privées avec bots uniquement** [V]. Landscape, foliage, Nanite, World Partition : non documentés **[NV]**.
- **Blocage v0.9 (essais locaux du 14/11/2026)** : (A) l'installeur 0.2.1 refuse (empreintes des 16 tables de menu changées ; corrigé dans une copie d'essai, sans effet) ; (B) le jeu v0.9 **n'affiche pas les cartes** des paks ajoutés : les 99 `.sig` du jeu suggèrent des paks signés, les nôtres n'en ont pas (hypothèse ~60 %, non tranchée) ; aucun journal du jeu [V local : `bodycam/veille_kit/ANALYSE_BLOCAGE.md`, `INSTALLEUR_V09_ESSAI.md`]. Issue ouverte : https://github.com/Lovac/bodycam-map-importer/issues/1 (sans réponse au 17/11).
- **BC_MOD** (autre mod joueur, v1.0.2 du 16/11/2026, https://bcmod.dev/) : lanceur propre + DLL non signées, contenu CS2 ; il ne lit pas le Map Kit et son mécanisme probable passe par-dessus EAC : **exclu** [V local, `BCMOD_1.0.2.md`].
- **Verdict** : aucune voie autorisée confirmée pour une carte personnalisée dans Bodycam v0.9. Pistes légitimes : contacter le studio, l'auteur de l'importateur, tester l'hébergement privé hors EAC **seulement s'il est officiellement permis**. Ne pas contourner la signature ni l'anti-triche.
- Plan B : porter la même carte vers Fortnite/UEFN (§ 6) ou Arma Reforger.

---

## 5. Dragon Ball: Sparking! Zero (Bandai Namco)

- **Moteur** : UE **5.1.1**, projet `SparkingZERO` [C : document communautaire « Sparking Zero Modding Resources » https://docs.google.com/document/u/0/d/1E8UiWe4X1pbWrJhG0eq3sEkZ7fvxKp4uc4XCByuL2gc/mobilebasic , daté d'environ 2024]. La clé AES y est publiée pour le solo ; ne pas la recopier. Jeu toujours suivi par le studio en octobre 2026 (annonces Steam du 02/10 et 09/10/2026) [V : API Steam appid 1790600].
- **Scène** : Nexus Mods (https://www.nexusmods.com/dragonballsparkingzero) et GameBanana ; pages Nexus renvoyant 403 à la lecture, infos via extraits [C].
- **Prérequis** : « UTOC Signature Bypass Patch » (https://www.nexusmods.com/dragonballsparkingzero/mods/18) pour que `.pak/.utoc/.ucas` ajoutés soient chargés [C]. C'est un patch documenté publiquement pour le solo, à n'employer que dans ce cadre ; mods dans `SparkingZERO/Content/Paks/~mods` [C]. Chargeurs/outils : Unverum, Reloaded-II (+ Ryo Framework pour l'audio), UE4SS, Dumper-7, UnrealReZen/ZenTools, repak, USMZero (vidéos d'arènes) [C].
- **Ce qui se modde** [C] : personnages, costumes, audio, configuration, **arènes** (mods « Let's Fight Somewhere Else (LFSE) » https://www.nexusmods.com/dragonballsparkingzero/mods/29 : ajoute des emplacements d'arène au sélecteur ; un mod de 50 emplacements avec « mapdata » propres ; suppression des murs invisibles ; cartes à images PNG/MP4).
- **Ajouter une arène** [C : guide « Sparking Zero Stage Modding Guide » sur Scribd, https://www.scribd.com/document/835854692/Sparking-Zero-Stage-Guide , non relu en détail] : Unreal Engine 5.1 personnalisé + projet UE dédié + modèle « StageLocatorTemplate » ; import des modèles (Blender), limites d'arène, points d'apparition des personnages, éclairage, foliage, objets destructibles ; empaquetage repak ; vignette/vidéo via USMZero ; référencement au sélecteur via LFSE. **Remplacer** une arène existante = même chemin d'asset que l'arène d'origine.
- **Risque en ligne** : Bandai Namco a averti (octobre 2024) que tout mod utilisé en **Custom Battles en ligne** expose à un bannissement ; supprimer les Custom Battles modifiés [C : https://www.gamesradar.com/games/fighting/dragon-ball-sparking-zero-publisher-warns-players-to-delete-modded-custom-battles-immediately-to-avoid-a-ban]. Politique 2026 non vérifiée **[NV]**. Règle : solo hors ligne, désinstaller les mods avant tout jeu en ligne.
- Les guides ont ~2 ans ; vérifier les versions du jeu (le jeu a reçu des mises à jour depuis) **[NV]**.

---

## 6. Autres familles

| Jeu | Voie d'entrée d'une carte | Format de terrain / limites | Doc |
|---|---|---|---|
| Fortnite (UEFN + Verse) | Éditeur officiel UEFN (UE5 modifié), publication d'une île ; **carte réelle possible** (Landscape, World Partition) | Budget de publication **300 MiB** (affiché en MiB, ex-« thermomètre ») ; streaming (World Partition) indispensable pour les grandes îles ; collisions de Landscape lourdes ; limite de taille d'île non précisée par la page [V]. Mémoire revue à la hausse en v43.00 selon un créateur (rapport forum, nov. 2026) [C] | https://dev.epicgames.com/documentation/en-us/uefn/memory-management-in-unreal-editor-for-fortnite |
| ARK: Survival Ascended | ARK DevKit (éditeur UE5 sur Epic Games Store, contenu complet du jeu), mods multiplateformes via CurseForge ; cartes entières possibles [V/C] | Téléchargement énorme (~1,3 To cité par une source tierce **[NV]**) ; un « ASA World Creator » en jeu évoqué pour 2026 **[NV]** | https://store.epicgames.com/p/ark-survival-ascended--devkit ; https://www.gamedeveloper.com/press-release/studio-wildcard-releases-major-update-to-ark-development-kit |
| Squad | SDK officiel (Epic Launcher) : « Modding Hub » > Custom Map, cuisson, « Upload to Steam Workshop » [C, guides 2017-2020] ; passage à UE5 fin 2025, couches reconstruites [C : changelog Workshop] | Version du SDK actuel et limites de taille **[NV]** | https://squad.fandom.com/wiki/Squad_Wiki ; https://www.moddb.com/games/squad/news/squad-modding-sdk-released-on-epic-launcher |
| Ready or Not | Pas de SDK officiel confirmé (VOID : « objectif ultime »), cartes communautaires via UE4SS/paks ; mod.io pour équipement seulement [C, 2024] | UE 5.3.2 cité par une page de mod **[NV]** ; vérifier la scène en 2026 **[NV]** | https://voidinteractive.net/?p=1877 |
| Pavlov (PC VR / Shack) | Modkit officiel + mod.io (carte Unique Id) ; Shack passé à UE5 (anciennes cartes incompatibles) [C] | Modkit UE **5.1.1** ; installer Starter Content, Engine Source, Android (Shack), Linux [C] | https://pavlovwiki.com/index.php/Getting_Started |
| Contractors / Contractors Showdown | mod.io / SDK : **non trouvé** | **[NV]** | chercher la page officielle mod.io du jeu |
| Assetto Corsa EVO | SDK officiel depuis la 0.7 : **voitures seulement** (solo) ; liens multijoueur/livrées en 0.8 ; **outils de pistes non publiés** au relevé [C] | Pas de format de piste public | https://boxthislap.org/assetto-corsa-evo-mods/ ; https://boxthislap.org/assetto-corsa-evo-0-7-official-modding-tools-are-finally-here/ |
| Assetto Corsa (1) | Dossier `content/tracks/<piste>/` : modèle `.kn5` (export Blender / 3ds Max / KsEditor), `models.ini`, `ui/`, `data/surfaces.ini`, lignes AI/`fast_lane.ai`, cuisson avec KsEditor ; mods piste très courants | `.kn5` : pas de terrain/landscape, maillages découpés ; limites de taille/mémoire : **[NV]** ; outils « RTB / Blender » (Race Track Builder, RTB) cités par la demande, non vérifiés **[NV]** | https://github.com/2m/actools (AcTools / Content Manager, cité par recherche) [C] |
| BeamNG.drive | Niveau dans `levels/` via World Editor ; import de heightmap PNG/TER, terrain `.ter` ; Workshop/repository | Import de heightmap parfois capricieux (terrain plat, crash) ; 4K difficile, un 8192 signalé fonctionnel en 0.32.5 [C]. Aucune limite officielle lue | https://www.beamng.com/threads/mapng.107522/ (MapNG) ; docs BeamNG **[NV]** |
| Arma Reforger (Enfusion Workbench) | Outil officiel Workbench, mods publiés au Workshop Bohemia | Heightmap `.asc` ou **PNG 16 bits** ; taille = Terrain Grid Size x Grid Cell Size ; **un seul terrain par monde** ; imports très grands (32,5 x 32,5 km) en échec sur le suivi BI en 2024 [C] ; satmap, prefabs de décor | https://community.bistudio.com/wiki/Arma_Reforger:World_Editor:_Terrain_Creation_Tool (403 à la lecture, extrait de recherche) |
| GTA V / FiveM | Cartes = YMAP/YTYP/YDR (CodeWalker, outils communautaires) ; chargement côté serveur FiveM ; solo : mod loaders | Terrain GTA non remplaçable proprement ; **GTA Online : ne rien modifier** ; format et limites : **[NV]** | https://docs.fivem.net/ **[NV]** |
| Cities: Skylines II | Éditeur de carte intégré, import de heightmap | Une source tierce : **4096x4096, PNG/TIFF 16 bits**, fichier `.png.cid` associé dans `LocalLow` [C, https://github.com/gregspruce/CS2_MapCreator] ; à confirmer **[NV]** | docs Paradox **[NV]** |
| Microsoft Flight Simulator 2020/2024 | SDK officiel + Developer Mode (scenery editor), publication Marketplace | Rien trouvé dans ce relevé : formats (BGL/glTF, tuiles photogrammétriques) et limites **[NV]** | https://docs.flightsimulator.com/ **[NV]** |

---

## 7. Du niveau Unreal « neutre » au jeu cible

### 7.1 Ce qui reste commun
- **Terrain** : MNT (relief) -> heightmap 16 bits / dalles de maillage ; orthophoto -> texture(s) de sol ; masques (route, bâti, forêt, eau).
- **Maillages** : route (ruban), bâtiments, murs, ponts, rochers ; export glTF/GLB (ou FBX) avec échelle en mètres, Z-up documenté.
- **Textures** : atlas/UDIM selon le jeu ; respecter les limites de VRAM du jeu (ACR : ~0,7 Go par spéciale convertie [V]).
- **Placements** : positions/rotations/échelles d'arbres, poteaux, panneaux, murets (par essence/type) en coordonnées locales (m) avec CRS d'origine conservé.

### 7.2 Ce qui doit être refait par jeu
- **Matériaux** : ceux du jeu (variantes de matériaux existants, paramètre de texture avec texture par défaut du même type, sinon gris : Bodycam [V]) ; pas de shader maître possible dans ACR/BioBio [V local].
- **Acteurs de jeu** : points d'apparition (`PlayerStart` tagués : Bodycam), lignes de départ/arrivée et chronos, zones (HardPointZone), volumes de limites, notes de copilote, tables de menu, vignettes.
- **Navigation** : NavMesh pour bots (Bodycam, cuisson via script du kit) ; ligne AI (AC1 `fast_lane.ai`).
- **Météo / lumière** : DirectionalLight/SkyLight imposés (Bodycam), ciel et heure par table du jeu.
- **Physique des surfaces** : matériaux physiques du jeu (`PM_SurfaceTarmacSmooth`, gravier, herbe… dans ACR), `surfaces.ini` (AC1), `BakedData` (ACR). C'est la partie la plus propre à chaque jeu.
- **Référencement** : chemins `/Game/...` des assets du jeu via projet factice à la bonne version moteur.

### 7.3 Architecture recommandée
1. **Représentation intermédiaire indépendante du jeu** : un dossier `scene/` contenant
   - `terrain/` : `heightmap_16bit.png` + `terrain.json` (origine, CRS, taille de pixel, altitude min/max) ; dalles si besoin ;
   - `meshes/*.glb` (route, bâti, murs) ;
   - `placements.json` (ou CSV) : `{type_semantique, essence, x, y, z, yaw, echelle, hauteur_mesuree}` en mètres locaux ;
   - `zones.json` : départ, arrivée, limites, points d'apparition candidats, axe de route avec dévers.
2. **Un adaptateur par jeu** (`adapters/<jeu>/`) : table de correspondance `type_semantique -> asset du jeu` (ex. `pin_alep -> /Game/Foliage/Trees/AleppoPine`), génération du niveau/pak, des acteurs de jeu, des lignes de registre, des tests de chargement.
3. **Contrôle de version** : un fichier `jeu.json` par jeu (moteur, build Steam, format d'archive, date de relevé) vérifié au lancement ; échec explicite si le build change.
4. **Étapes standard** : valider la scène neutre -> choisir l'adaptateur (§ 1) -> cuire à la version moteur du jeu (§ 2) -> installer dans `~mods` avec sauvegarde -> tester en solo / hors ligne -> noter les écarts dans `references/`.
5. **Taille** : prévoir un facteur de découpe (tuiles, LOD) ; viser la plus petite emprise exigée (Bodycam : quelques centaines de mètres ; ACR : < 9 km ; UEFN : 300 MiB).

---

## 8. Points non vérifiés (récapitulatif)
- Dates et numéros de release des outils du § 2 (API GitHub refusée) ; état d'UAssetAPI et UnrealReZen non relu.
- `acr-ref` : aucun dépôt trouvé. Format de `BakedData` et des notes ACR ; chargement en Free Practice ; usage en ligne.
- Moteur de la Bodycam v0.9 ; cause exacte du blocage v0.9 (signatures de paks ou autre) ; Landscape/foliage dans le Map Kit ; mode privé hors EAC.
- Sparking Zero : versions actuelles du jeu et des outils, politique de bannissement 2026, contenu précis du guide d'arènes (Scribd).
- Tableau § 6 : Squad (SDK UE5 actuel), Ready or Not, Contractors, AC1 (RTB/limites), BeamNG, GTA/FiveM, Cities: Skylines II, Microsoft Flight Simulator, tailles maximales.
- Pages bloquées à la lecture (403/404) : Nexus Mods, BI wiki, 505 support, boxthislap, Patreon, API GitHub.
