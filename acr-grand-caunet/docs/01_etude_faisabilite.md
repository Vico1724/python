# Étude de faisabilité : ES « Le Grand Caunet » dans Assetto Corsa Rally

*Situation au 10 novembre 2026, révisée le même jour (voir l'encadré du § 1). Document destiné au directeur de projet.*

Légende de fiabilité :
- **[confirmé]** : vérifié sur la page source complète ;
- **[confirmé, extrait]** : vu seulement dans un extrait de moteur de recherche, la page étant inaccessible ;
- **[probable]** : indice concordant, sans preuve directe ;
- **[inconnu]** : aucune source trouvée.

---

## 1. Verdict

**Oui, on peut mettre une spéciale personnalisée dans Assetto Corsa Rally (ACR), par une voie non officielle et encore expérimentale.**

- **Officiellement**, le jeu ne permet de modifier que les livrées (la décoration des voitures). Aucun éditeur de spéciales n'est annoncé.
- **Non officiellement**, deux réalisations apparues entre fin octobre et début novembre 2026 prouvent que c'est faisable :
  - une spéciale **originale** de 8,7 km, « Chile BioBio » (Sando Rally), construite à partir de données cartographiques publiques comme les nôtres [S14] ;
  - un projet libre, **ACR Extra Stages**, qui documente la méthode pas à pas et dont le code est réutilisable [S15].
- **Les limites connues** : jeu hors ligne seulement (Free Practice pour BioBio), reconstruction à prévoir après chaque mise à jour du jeu, rendu visuel encore en chantier dans le projet libre, et un PC Windows avec le jeu obligatoire pour construire et tester.

> **Correction.** La première version de cette étude concluait « pas encore possible ». C'était faux : elle s'appuyait sur une recherche qui n'avait pas trouvé ces deux réalisations, toutes récentes. Le directeur avait raison.

## 2. État du modding d'ACR au 10/11/2026

| Fait | Date | Fiabilité | Source |
|---|---|---|---|
| Le jeu est en accès anticipé. Dernière version : **0.6**. Aucune annonce officielle depuis. | 10/09/2026 | [confirmé] | Flux officiel des actualités Steam [S1] |
| La 0.6 a fait passer le jeu du moteur **Unreal Engine 5.4 à 5.6**. | Déclaration du 11/09/2026 | [confirmé] | Déclaration officielle de Supernova reproduite par Traxion [S2] |
| Seul contenu modifiable officiellement : les **livrées**. La documentation est fournie dans le dossier du jeu `acr/Content/LiveryTemplates/`. C'est présenté comme « une première étape vers le support du modding, que nous prévoyons d'étendre ». | 10/09/2026 | [confirmé] | Notes de version 0.6 [S1][S3] |
| Supernova dit développer une **chaîne de modding officielle** conçue pour rester stable lors des mises à jour du moteur. **Aucune date, aucun outil, aucun éditeur de spéciales** n'est annoncé. | 11/09/2026 | [confirmé] | [S2] |
| Il n'y a ni Steam Workshop (le système de partage de mods intégré à Steam), ni kit de développement (SDK). | — | [confirmé] : aucune mention dans les annonces officielles | [S1] |
| D'après un article OverTake, le modding complet ne viendrait « pas avant la version 1.0 ». | Q&R communautaire, date non vérifiée | [confirmé, extrait] (page refusée, erreur 403) | [S4] |
| Des mods non officiels existent : livrées, copilotes, applications. Ils fonctionnent en remplaçant des fichiers du jeu (archives `.pak/.ucas/.utoc`), qu'on ouvre et reconstruit avec FModel, UnrealPak et FMOD Bank Tools. | 11/09/2026 | [confirmé] | [S2] |
| La 0.6 a cassé tous les mods non officiels antérieurs. Le développeur précise qu'il n'a ajouté **ni protection anti-mod ni DRM** (verrou anti-copie). | 11/09/2026 | [confirmé] | [S2] |
| Les archives du jeu ne sont pas chiffrées, ce qui permet de les ouvrir avec FModel. | Message de forum | [confirmé, extrait] (page refusée, erreur 403) | [S5] |
| **Une spéciale originale non officielle existe** : « Chile BioBio » v0.3.0 de Sando Rally (Diego Sandoval), 8,7 km de terre plus le sens inverse. Faite pour la 0.6, « à partir de données publiques de carte, d'altitude et d'occupation du sol ». Copilote avec éditeur de notes, point stop. **Free Practice uniquement.** Installation par un petit programme Windows, archive de 3,8 Go. | Novembre 2026 | [confirmé] | [S14] |
| La méthode de fabrication de BioBio n'est pas publiée. | — | [inconnu] | [S14] |
| Sando Rally avait aussi publié un outil convertissant des spéciales de WRC Generations ; l'auteur l'a **retiré** parce que des spéciales converties étaient partagées en ligne. | Novembre 2026 | [confirmé] | [S16] |
| **ACR Extra Stages** : projet libre (licences MIT et Apache) qui convertit 106 spéciales de DiRT Rally 2.0 à partir de la copie du joueur. Elles apparaissent dans les menus du jeu, avec notes du copilote, carte et profil. Version 0.1.0-beta.1, **non publiée**, tests en jeu « encore en cours » ; hors ligne uniquement ; Windows uniquement ; les spéciales de plus de 9 km ne tiennent pas. | Dernier dépôt le 31/10/2026 | [confirmé] : dépôt lu | [S15] |
| ACR Extra Stages documente l'anatomie d'une spéciale du jeu et un **format d'échange** (« Stage IR ») entre les données d'origine et la construction du mod. | 31/10/2026 | [confirmé] : documentation lue | [S15] |
| Le site AC Rally Central écrivait encore que la plupart des moddeurs « attendent avec impatience le modding de tracés pour ACR ». | 2026 | [confirmé] | [S6] |
| Un serveur Discord communautaire, « RallyForge », travaille sur des méthodes Unreal 5.4 pour les spéciales et les voitures. Aucun résultat public n'est connu. | — | [confirmé, extrait] (Nexus refusé, erreur 403) | [S7] |
| Les spéciales officielles sont **scannées au laser** par un partenaire externe. | 2025 | [confirmé, extrait] | [S8] |
| Points inconnus : la position de l'éditeur sur ces spéciales non officielles, et les clauses du contrat de licence (CLUF) sur les mods. | — | [inconnu] | — |

## 3. Contraintes identifiées

**Techniques** (d'après la documentation d'ACR Extra Stages [S15])
- La méthode qui fonctionne ne crée pas un niveau neuf. Elle **copie une spéciale existante du jeu** (une spéciale galloise, Hafren South) et y remplace :
  1. la collision, c'est-à-dire la surface invisible sur laquelle roule la voiture et qui porte l'adhérence ;
  2. les courbes qui décrivent la route, les lignes de départ et d'arrivée, les notes du copilote ;
  3. les lignes des tables du jeu qui font apparaître la spéciale dans les menus.
- Les fichiers produits se déposent dans un dossier `~mods` du jeu, sans toucher aux fichiers d'origine.
- Les surfaces doivent être choisies parmi celles que le jeu connaît déjà. Un asphalte lisse existe (`PM_SurfaceTarmacSmooth`).
- La spéciale hôte limite la longueur à 9 km. **Nos 6,702 km tiennent.**
- **Le rendu visuel est le point faible** : dans ce projet, deux tiers des spéciales converties ont des textures de sol de remplacement, et la création de vrais décors texturés passe par une voie que ses auteurs jugent non prouvée.
- Le jeu repose sur des scans laser de grande précision. Une route reconstruite à partir de données publiques sera moins fidèle que les spéciales officielles.

**Casse à chaque mise à jour**
- Le développeur l'écrit lui-même : les archives sont liées à la version du moteur. Chaque mise à jour majeure peut rendre un mod inutilisable [S2]. Une intégration non officielle serait donc à refaire régulièrement.

**Juridiques**
- Je n'ai pas trouvé le contrat de licence (CLUF). Diffuser publiquement un mod non officiel reste à valider.
- Les données géographiques utilisées (IGN : LiDAR HD, BD ORTHO, BD TOPO, BD Forêt) sont sous Licence Ouverte Etalab 2.0 : réutilisation libre, y compris dans un mod diffusé, à condition de citer la source (« IGN »). La carte de l'organisateur (ASA Marseille) n'est pas redistribuée : seules ses coordonnées et distances sont reprises.

**Ce que notre serveur Linux ne peut pas faire**
- Lancer le jeu et tester en conduite : il faut le PC Windows du directeur, avec le jeu et un volant.
- Ouvrir les archives du jeu avec FModel, qui ne fonctionne que sous Windows. De plus, le jeu n'est pas installé sur le serveur.
- Construire le mod final : les outils d'ACR Extra Stages lisent les fichiers du jeu installé et ne sont prévus que pour Windows.
- Le serveur peut en revanche traiter toutes les données géographiques et produire le modèle 3D.

## 4. Stratégie recommandée

*Recommandation, non un fait.*

1. **Viser directement Assetto Corsa Rally**, par la méthode de la spéciale hôte.
2. Continuer à produire une spéciale **« neutre »** : axe, bords de chaussée, relief, modèle 3D, dans des formats ouverts (GeoTIFF, GeoJSON, glTF). C'est ce qui est fait depuis la phase 2, et c'est ce qui protège le travail si une mise à jour du jeu casse la méthode.
3. Ajouter un **exporteur vers le format d'échange « Stage IR »** d'ACR Extra Stages : un fichier `stage.json` (axe, portes avec bords gauche et droit, départ, intermédiaires, arrivée, notes du copilote) et des maillages glTF (collision par type de surface, objets, rendu). Ce format est conçu pour des spéciales de DiRT Rally 2.0 ; il faudra vérifier, côté construction, ce qui dépend de ce jeu.
4. Construire et tester sur le PC Windows du directeur, d'abord en version minimale (la route seule, sans décor), puis en enrichissant.
5. Garder **Assetto Corsa 1 avec CSP** comme solution de repli si la méthode casse.
6. Écrire à Sando Rally : son approche est la plus proche de la nôtre, mais sa licence interdit de réutiliser son travail sans accord.

| Cible | Maturité | Outillage | Effort | Ce que le directeur fait sur son PC |
|---|---|---|---|---|
| **AC Rally**, méthode de la spéciale hôte | Expérimentale mais prouvée : une spéciale originale publiée [S14], un outil libre en bêta [S15] | .NET, PowerShell 7, retoc, Dumper-7 (Windows) | Élevé ; rendu visuel incertain ; à reconstruire après chaque mise à jour | Installer le jeu et les outils, lancer la construction, **tester en conduite** |
| **Assetto Corsa 1 + CSP** (repli) | Élevée : de nombreuses spéciales communautaires de qualité [S6] | Blender, exporteur kn5 ou ksEditor, Content Manager, CSP | Moyen | Installer AC, CSP et Content Manager, copier la spéciale, rouler |
| **Richard Burns Rally / RallySimFans** | Élevée, communauté rallye historique | Exporteur Blender pour RBR [S9], plugin RSF [S10] | Moyen à élevé | Installer RSF, copier la spéciale, rouler |
| **BeamNG.drive** | Moyenne : mode rallye récent, création de boucles peu documentée [S11] | World Editor, MapNG [S12] | Moyen | Installer BeamNG, copier le niveau, rouler |

**Décision du directeur (10/11/2026) : procéder comme « Chile BioBio »**, pour un rendu à la fois réaliste et jouable. Le directeur possède le jeu sur PC.

Ce que la page de BioBio dit de sa fabrication [S14] :
- la route vient d'OpenStreetMap, le relief d'un modèle mondial à 30 m (Copernicus), la végétation d'une carte mondiale d'occupation du sol (ESA WorldCover) ;
- les textures sont des photographies libres (Poly Haven, licence CC0) ;
- les éléments du jeu (probablement arbres, objets, matériaux : la page ne les détaille pas) sont **référencés par leur nom et leur chemin, jamais redistribués**.

Ce que cela change pour nous :
- nos données sont nettement plus fines : relief laser à 0,5 m au lieu de 30 m, forêt cartographiée par essence, hauteur des arbres mesurée, photo aérienne à 20 cm ;
- le décor réaliste passe par la réutilisation des arbres et matériaux du jeu, référencés par leur chemin ; il faudra donc en dresser la liste à partir du jeu installé sur le PC du directeur ;
- **la façon dont BioBio est assemblé et chargé par le jeu n'est pas publiée.** Deux voies sont possibles : la spéciale hôte décrite par ACR Extra Stages, ou un niveau neuf construit dans Unreal Engine 5.6. Je ne sais pas laquelle BioBio utilise. La liste des fichiers qu'il installe, et une question à son auteur, le diront (voir `guide_pc_directeur.md`).

## 5. Chaîne d'outils retenue

| Logiciel | Rôle | Gratuit | Où il tourne |
|---|---|---|---|
| Python + rasterio, shapely, pyproj (bibliothèques GDAL/PROJ) | Téléchargement IGN, cartographie, traitement du relief | Oui | Serveur Linux (en ligne de commande) |
| QGIS | Consultation des cartes et contrôle visuel par le directeur (facultatif) | Oui | PC |
| Python (scripts du projet) | Automatisation : axe de la route, profil, contrôles | Oui | Serveur Linux |
| Blender | Modèle 3D de la route et du décor ; export glTF | Oui | Serveur Linux (sans écran) et PC |
| LidarToolbox (AC Rally Central) | Conversion de données laser en terrain [S6] | — | PC Windows |
| Content Manager + CSP, ksEditor | Repli Assetto Corsa 1 | Oui | PC Windows |
| Outils d'ACR Extra Stages [S15] | Construction du mod ACR à partir du format d'échange | Oui (MIT/Apache) | PC Windows |
| Dumper-7 | Produit le fichier de correspondance (.usmap) nécessaire pour lire les fichiers du jeu [S15] | Oui | PC Windows, jeu lancé |
| retoc | Conversion et empaquetage des archives ACR [S13][S15] | Oui | PC Windows (Linux non testé ici) |
| FModel | Consultation des archives ACR | Oui | PC Windows |
| Unreal Engine 5.6 | Seulement si l'on veut de vrais décors texturés par la voie « éditeur », non prouvée | Oui (licence Epic) | PC Windows |

Source de relief retenue : le LiDAR HD de l'IGN (relevé laser aérien, maille de 0,5 m), disponible sur toute la spéciale et déjà téléchargé en phase 2. Licence Ouverte Etalab 2.0.

## 6. Plan de développement

| Phase | Contenu | Livrable | Automatisable sur le serveur |
|---|---|---|---|
| 0 | Faisabilité | Ce document | — |
| 1 | Choix de la spéciale : **fait**. ES 7/10 « Le Grand Caunet », 6,702 km, asphalte, Sainte-Baume Rallye 2026. | Fichier `data/reference/es_grand_caunet_2026_officiel.json` (15 points officiels) | Oui |
| 2 | Données géographiques : **fait** (voir `02_phase2_donnees_geographiques.md`) | Tracé calé sur les points officiels, relief LiDAR 0,5 m, photos aériennes 20 cm, profil en long, inventaire du décor | Oui (entièrement scripté) |
| 3 | Axe routier et profil fins | Axe et bords de chaussée redessinés sur le LiDAR et la photo 20 cm, dévers, largeurs réelles, lignes de départ/arrivée verrouillées | Largement ; contrôle visuel humain |
| 4 | Terrain 3D | Maillage du terrain autour de la route | Oui |
| 5 | Route, bas-côtés, objets | Chaussée, accotements, glissières, panneaux ; **premier essai en jeu avec la route seule** | Partiellement (Blender scripté) |
| 6 | Végétation et décor | Arbres, bâtiments, textures | Partiellement ; finition manuelle |
| 7 | Export et intégration | Export au format d'échange « Stage IR », puis construction du mod ACR par la méthode de la spéciale hôte | Export oui ; **construction et test en jeu sur le PC du directeur** |
| 8 | Notes du copilote, chrono, tests | Notes de copilote, départ/arrivée/intermédiaires, retours de conduite | Notes générées à partir du tracé ; validation humaine |

## 7. Risques et décisions à prendre

**Risques**
- La méthode est non officielle : une mise à jour du jeu (la 0.7 est attendue) peut la casser, et il faudra reconstruire [S2][S15].
- Le rendu visuel par cette méthode n'est pas acquis : la route peut être pilotable bien avant d'être belle [S15].
- ACR Extra Stages est une bêta non publiée, conçue pour DiRT Rally 2.0 ; l'adapter à nos données demandera du développement et des essais sur le PC du directeur.
- Hors Free Practice et hors ligne, rien n'est prouvé.
- La précision des données publiques est inférieure au scan laser du jeu.
- Clauses du CLUF du jeu sur les mods inconnues ; aucune position de l'éditeur sur ces spéciales.

**Décisions attendues du directeur**
1. Cible validée le 10/11/2026 : Assetto Corsa Rally, à la manière de BioBio ; PC Windows avec le jeu disponible.
2. Tester « Chile BioBio » et transmettre la liste des fichiers installés (voir `guide_pc_directeur.md`) [S14].
3. Écrire à l'auteur de BioBio pour connaître sa méthode d'assemblage (facultatif, mais utile).
4. Choisir le niveau de détail visé pour le décor, qui est le poste le plus long.
5. Décider si la spéciale sera diffusée publiquement, ce qui impose une vérification juridique.

## 8. Sources

- [S1] Actualités officielles Steam d'ACR (API Steam, consultée le 10/11/2026) : https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=3917090 (version lisible : https://store.steampowered.com/news/app/3917090)
- [S2] Traxion, « Why Assetto Corsa Rally's V0.6 update was more important than first thought », avec la déclaration de Supernova du 11/09/2026 : https://traxion.gg/why-assetto-corsa-rallys-v0-6-update-was-more-important-than-first-thought/
- [S3] 505 Games, notes de version 0.6 : https://support.505games.com/support/solutions/articles/150000233496-assetto-corsa-rally-early-access-update-0-6
- [S4] OverTake, modding « pas avant la 1.0 » (non vérifié en page entière) : https://www.overtake.gg/news/native-vr-implementation-a-top-priority-for-ac-rally-modding-to-come-not-before-version-1-0.4297/
- [S5] OverTake, informations de modding (non vérifié en page entière) : https://www.overtake.gg/threads/final-game-cars-list-modding-infos-i-gathered.290925/
- [S6] AC Rally Central : https://acrallycentral.com/
- [S7] RallyForge sur Nexus Mods (non vérifié en page entière) : https://www.nexusmods.com/assettocorsarally/images/1
- [S8] PC Gamer, spéciales scannées au laser et UE5 : https://www.pcgamer.com/games/racing/assetto-corsa-rally-features-fully-laser-scanned-courses-unreal-engine-5-visuals-and-its-out-in-early-access-on-november-13/
- [S9] Exporteur Blender pour RBR : https://richardburnsrally.github.io/blender-track-exporter/features.html
- [S10] RallySimFans : https://rallysimfans.hu/rbr/download.php
- [S11] BeamNG, mode rallye et notes de copilote : https://www.beamng.com/resources/rally-mode-smart-co-driver-stages-with-pacenotes.21824/updates
- [S12] MapNG : https://mapng.com — documentation terrain BeamNG : https://docs.beamng.com/modding/levels/level_creation/section2/
- [S13] retoc : https://github.com/trumank/retoc
- [S14] Sando Rally, « Original Stages for Assetto Corsa Rally » (page lue le 10/11/2026) : https://sandorally.com/original-stages
- [S15] ACR Extra Stages (dépôt lu le 10/11/2026 : README, `docs/stage-ir.md`, `docs/acr-stage-anatomy.md`, `docs/decisions.md`) : https://github.com/nitnerolf420/acr-extrastages
- [S16] Sando Rally, arrêt de l'outil d'export : https://sandorally.com/stage-export-tool-discontinued
- Pack d'outils de modding ACR sur Nexus : https://www.nexusmods.com/assettocorsarally/mods/3
- Exporteur Blender kn5 : https://awesome.ecosyste.ms/projects/github.com%2Fmoppius%2Fblender-assetto-corsa-tools
