# Étude de faisabilité : ES « Le Grand Caunet » dans Assetto Corsa Rally

*Situation au 10 novembre 2026. Document destiné au directeur de projet.*

Légende de fiabilité :
- **[confirmé]** : vérifié sur la page source complète ;
- **[confirmé, extrait]** : vu seulement dans un extrait de moteur de recherche, la page étant inaccessible ;
- **[probable]** : indice concordant, sans preuve directe ;
- **[inconnu]** : aucune source trouvée.

---

## 1. Verdict

**Il n'est pas encore possible d'intégrer proprement une spéciale personnalisée dans Assetto Corsa Rally (ACR).** Aujourd'hui, le jeu ne permet officiellement de modifier que les livrées (la décoration des voitures). Personne n'a publié de spéciale ajoutée par la communauté qui fonctionne.

Ce qui est possible dès maintenant :
- produire toutes les données de la spéciale (tracé, relief, modèle 3D) dans des formats indépendants du jeu ;
- les tester dans **Assetto Corsa (2014)**, où la création de spéciales est maîtrisée depuis des années.

Le portage vers ACR se fera quand l'éditeur ouvrira le modding des spéciales.

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
| **Aucune spéciale personnalisée fonctionnelle** n'est publiée. Le site de référence AC Rally Central écrit que la plupart des moddeurs « attendent avec impatience le modding de tracés pour ACR ». | 2026 | [confirmé] | [S6] |
| Un serveur Discord communautaire, « RallyForge », travaille sur des méthodes Unreal 5.4 pour les spéciales et les voitures. Aucun résultat public n'est connu. | — | [confirmé, extrait] (Nexus refusé, erreur 403) | [S7] |
| Les spéciales officielles sont **scannées au laser** par un partenaire externe. | 2025 | [confirmé, extrait] | [S8] |
| Points inconnus : la manière dont le jeu décrit une spéciale en interne (relief, route, nature des surfaces), l'emplacement des notes du copilote et du chronométrage, et les clauses du contrat de licence (CLUF) sur les mods. | — | [inconnu] | — |

## 3. Contraintes identifiées

**Techniques**
- Pour forcer une spéciale dans ACR, il faudrait :
  1. reconstruire un niveau dans Unreal Engine 5.6 ;
  2. le « cuire », c'est-à-dire le convertir dans le format compilé du jeu ;
  3. remplacer une spéciale existante.

  Rien n'est documenté pour les surfaces (adhérence asphalte), les notes du copilote ou le chronomètre. Une voiture pourrait rouler sur notre route sans adhérence correcte, sans copilote et sans temps.
- Le jeu repose sur des scans laser de grande précision. Une route reconstruite à partir de données publiques sera moins fidèle que les spéciales officielles.

**Casse à chaque mise à jour**
- Le développeur l'écrit lui-même : les archives sont liées à la version du moteur. Chaque mise à jour majeure peut rendre un mod inutilisable [S2]. Une intégration non officielle serait donc à refaire régulièrement.

**Juridiques**
- Je n'ai pas trouvé le contrat de licence (CLUF). Diffuser publiquement un mod non officiel reste à valider.
- Les données géographiques utilisées (IGN : LiDAR HD, BD ORTHO, BD TOPO, BD Forêt) sont sous Licence Ouverte Etalab 2.0 : réutilisation libre, y compris dans un mod diffusé, à condition de citer la source (« IGN »). La carte de l'organisateur (ASA Marseille) n'est pas redistribuée : seules ses coordonnées et distances sont reprises.

**Ce que notre serveur Linux ne peut pas faire**
- Lancer le jeu et tester en conduite : il faut le PC Windows du directeur, avec le jeu et un volant.
- Ouvrir les archives du jeu avec FModel, qui ne fonctionne que sous Windows. De plus, le jeu n'est pas installé sur le serveur.
- Cuire un niveau compatible ACR : sans les fichiers du jeu, impossible de vérifier la compatibilité.
- Le serveur peut en revanche traiter toutes les données géographiques et produire le modèle 3D.

## 4. Stratégie recommandée

*Recommandation, non un fait.*

1. Produire une spéciale **« neutre »** : axe de la route, profil en long, terrain, modèle 3D de la route et des abords, dans des formats ouverts (GeoTIFF, GeoJSON, .blend, FBX). Ces fichiers sont réutilisables par n'importe quel jeu.
2. Cible de test immédiate : **Assetto Corsa 1 avec l'extension CSP**. Le mode « Rally Stage » de CSP gère :
   - le départ arrêté (voiture immobilisée 2 à 3 m avant la ligne, frein à main tiré) ;
   - un chronométrage propre au rallye, avec temps intermédiaires ;
   - un copilote via l'application « Rally Copilot ».

   Source : [S6], page complète vérifiée.
3. **Porter vers ACR** dès l'ouverture officielle du modding des spéciales. Tenter une injection non officielle seulement à titre d'essai et sans promesse de résultat.

| Cible | Maturité | Outillage | Effort | Ce que le directeur fait sur son PC |
|---|---|---|---|---|
| **AC Rally** (injection expérimentale UE 5.6) | Très faible : aucun précédent publié [S6] | Unreal 5.6, FModel, UnrealPak/retoc (Windows) | Très élevé, résultat incertain, à refaire à chaque mise à jour | Installer les outils, extraire les fichiers du jeu, tester |
| **Assetto Corsa 1 + CSP** | Élevée : de nombreuses spéciales communautaires de qualité [S6] | Blender, exporteur kn5 ou ksEditor, Content Manager, CSP | Moyen | Installer AC, CSP et Content Manager, copier la spéciale, rouler |
| **Richard Burns Rally / RallySimFans** | Élevée, communauté rallye historique | Exporteur Blender pour RBR [S9], plugin RSF [S10] | Moyen à élevé | Installer RSF, copier la spéciale, rouler |
| **BeamNG.drive** | Moyenne : mode rallye récent, création de boucles peu documentée [S11] | World Editor, MapNG [S12] | Moyen | Installer BeamNG, copier le niveau, rouler |

## 5. Chaîne d'outils retenue

| Logiciel | Rôle | Gratuit | Où il tourne |
|---|---|---|---|
| Python + rasterio, shapely, pyproj (bibliothèques GDAL/PROJ) | Téléchargement IGN, cartographie, traitement du relief | Oui | Serveur Linux (en ligne de commande) |
| QGIS | Consultation des cartes et contrôle visuel par le directeur (facultatif) | Oui | PC |
| Python (scripts du projet) | Automatisation : axe de la route, profil, contrôles | Oui | Serveur Linux |
| Blender (+ exporteur kn5) | Modèle 3D de la route et du décor ; export vers AC | Oui | Serveur Linux (sans écran) et PC |
| LidarToolbox (AC Rally Central) | Conversion de données laser en terrain [S6] | — | PC Windows |
| Content Manager + CSP | Lancer et tester la spéciale dans AC | Oui | PC Windows |
| ksEditor (Kunos) | Finalisation kn5, si nécessaire | Oui | PC Windows |
| FModel, UnrealPak | Lecture et reconstruction des archives ACR (expérimental) | Oui | PC Windows |
| retoc | Conversion des archives ACR en ligne de commande [S13] | Oui | Linux possible (non testé ici) |
| Unreal Engine 5.6 | Futur portage ACR | Oui (licence Epic) | PC Windows recommandé |

Source de relief retenue : le LiDAR HD de l'IGN (relevé laser aérien, maille de 0,5 m), disponible sur toute la spéciale et déjà téléchargé en phase 2. Licence Ouverte Etalab 2.0.

## 6. Plan de développement

| Phase | Contenu | Livrable | Automatisable sur le serveur |
|---|---|---|---|
| 0 | Faisabilité | Ce document | — |
| 1 | Choix de la spéciale : **fait**. ES 7/10 « Le Grand Caunet », 6,702 km, asphalte, Sainte-Baume Rallye 2026. | Fichier `data/reference/es_grand_caunet_2026_officiel.json` (15 points officiels) | Oui |
| 2 | Données géographiques : **fait** (voir `02_phase2_donnees_geographiques.md`) | Tracé calé sur les points officiels, relief LiDAR 0,5 m, photos aériennes 20 cm, profil en long, inventaire du décor | Oui (entièrement scripté) |
| 3 | Axe routier et profil fins | Axe et bords de chaussée redessinés sur le LiDAR et la photo 20 cm, dévers, largeurs réelles, lignes de départ/arrivée verrouillées | Largement ; contrôle visuel humain |
| 4 | Terrain 3D | Maillage du terrain autour de la route | Oui |
| 5 | Route, bas-côtés, objets | Chaussée, accotements, glissières, panneaux | Partiellement (Blender scripté) |
| 6 | Végétation et décor | Arbres, bâtiments, textures | Partiellement ; finition manuelle |
| 7 | Export et intégration | Spéciale AC installable ; dossier prêt pour ACR | Export oui ; **test en jeu sur le PC du directeur** |
| 8 | Notes du copilote, chrono, tests | Notes de copilote, départ/arrivée/intermédiaires, retours de conduite | Notes générées à partir du tracé ; validation humaine |

## 7. Risques et décisions à prendre

**Risques**
- ACR pourrait ne jamais ouvrir le modding des spéciales, ou le faire tard (après la 1.0) [S2][S4].
- Une injection non officielle serait cassée à chaque mise à jour [S2].
- La précision des données publiques est inférieure au scan laser du jeu.
- Clauses du CLUF du jeu sur les mods inconnues.

**Décisions attendues du directeur**
1. Valider Assetto Corsa 1 + CSP comme cible de test immédiate (recommandé).
2. Décider si l'on tente ou non un essai d'injection non officielle dans ACR, en sachant que le résultat est incertain.
3. Confirmer la disponibilité de son PC Windows (jeu, volant) pour les tests.
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
- Pack d'outils de modding ACR sur Nexus : https://www.nexusmods.com/assettocorsarally/mods/3
- Exporteur Blender kn5 : https://awesome.ecosyste.ms/projects/github.com%2Fmoppius%2Fblender-assetto-corsa-tools
