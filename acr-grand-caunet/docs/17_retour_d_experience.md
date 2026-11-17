# 17. Retour d'expérience : de l'étude de faisabilité à la dix-neuvième version

*17 novembre 2026. Document destiné au directeur de projet, et base du skill `projets/python/skill-speciale-rallye/`.*

**Sources.** Docs 01 à 16 du projet, `pc/LISEZMOI.md`, `pc/etape2_unreal/PROTOCOLE.md`, les commits de `projets/python` (du 10/11 à 20 h 59 au 17/11), les constantes datées et commentées des scripts, les retouches `pc/patches/0001` à `0006`, et les conversations tenues sur le PC : celles du 11/11 au 15/11 (dossier de Claude Code `…-projets-python`, deux conversations, 71 messages du directeur) et celles du 16 et du 17/11. Les échanges du 10/11 (étude de faisabilité, phases 2 à 4) ont eu lieu sur le serveur Linux et ne sont connus que par les docs 01 à 08 et les commits. *Première rédaction le 17/11 sans les conversations du 11 au 15/11, cherchées par erreur dans un seul dossier ; complétée le même jour après leur relecture.*

**En une phrase.** En sept jours, le projet est passé de « est-ce possible ? » à une spéciale complète, jouable et proche de la réalité, au prix d'une vingtaine d'aller-retours en jeu dont plus de la moitié auraient pu être évités en mesurant d'abord ce que fait le studio sur ses propres spéciales goudronnées, au lieu d'inventer une valeur puis de la corriger d'après l'essai.

---

## 1. Chronologie

| Date | Étape | Ce qui a été décidé ou appris |
|---|---|---|
| 10/11 soir | Étude de faisabilité (doc 01) | Premier verdict « pas encore possible », **faux** : la recherche n'avait pas trouvé BioBio ni ACR Extra Stages, apparus fin octobre. Corrigé le soir même sur l'indication du directeur. |
| 10/11 | Choix de l'ES, phase 2 (doc 02) | Le Grand Caunet, 6,702 km, asphalte. Tracé reconstitué sur la BD TOPO par plus court chemin entre les points officiels ; écart-type de 6,9 m aux 9 intermédiaires. Les coordonnées imprimées de la carte officielle sont indicatives (départ à 82 m de la route) : **ce sont les PK officiels qui font foi**. |
| 10/11 | Phase 3 (doc 03) | Axe, bords, largeur et dévers au mètre, depuis le LiDAR HD 0,5 m et l'ortho 20 cm. Ligne de départ reculée de 20 m sur la vidéo embarquée de 2025. |
| 10/11 | Archives de BioBio et du jeu (doc 04) | BioBio est un niveau simple, terrain en dalles, végétation et matériaux du jeu désignés par leur chemin. Décision : ne pas contacter son auteur, ne rien réutiliser de ses fichiers. |
| 10-11/11 nuit | Export Stage IR (doc 05), phase 4 (doc 07) | Format d'échange d'ACR Extra Stages produit sans l'avoir jamais exécuté. Lion d'Or refait trois fois (deux interprétations fausses des photos, puis nuage de points brut). Premier relevé vidéo (doc 08) : largeurs fausses là où un accotement plat a été compté en chaussée. |
| 11/11 matin | Kit PC, étape 1 en jeu | Prérequis installés (PowerShell 7, .NET 10, Rust, outils C++), une correction (`--locked` pour `retoc`). La route physique seule (acr-ref `stage-build`, remplacement de Hafren South 1/2) roule en jeu du premier coup : « le tracé semble bon ». L'option `-Textures` (matières galloises) est jugée « toujours dégueu de fou » : c'est le plafond de cette voie. |
| 11/11 | Préparation hors Unreal, puis Unreal 5.6.1 installé, essais E0-E4 | Avant l'installation, tout ce que le protocole voulait « lire dans Unreal » est lu dans les archives du jeu (3 erreurs du protocole évitées : `M_Simple` sans ses static switch, mauvais maillage de portique, Nanite supposé actif ; 3 468 arbres pointant vers des souches). Puis cuisson « avec versions » obligatoire (les groupes d'arbres cuits sans versions sont illisibles), import dans l'éditeur complet, factices aux dimensions réelles. **Première preuve en jeu à 16 h 26** : notre bannière cuite s'affiche sur le portique de Hafren North. |
| 11/11 après-midi | **Voie hybride** (PROTOCOLE § 0 quater) | Une étude du code d'acr-ref montre qu'il ne sait pas ajouter d'objets à un niveau, seulement réutiliser ceux de Hafren : on abandonne sa retouche. À la place, notre niveau Unreal remplace une cellule de World Partition de Hafren South ; la physique reste celle d'acr-ref. Vu en jeu sur 200 m (alignement exact), doublons retirés (retouche 0004), puis **toute la spéciale dans une seule cellule toujours chargée** (`1LS8FPM8JIMX697U3QIPKC01K`) : « sans bug et de manière fluide » à 22 h 22. C'est le choix structurant du projet. |
| 11/11 23 h 36 | Mode autonome | Le directeur autorise à « avancer vers le rendu final sans qu'on teste à nouveau ». À partir de là, plusieurs versions s'empilent souvent sans essai entre elles. |
| 12/11 | Sol du jeu, régularisation, mobilier (docs 09, 10, 11) | Nuit autonome : tracé régularisé, collision des troncs proches, sol aux matières du jeu (matériau de terrain de Bollène avec nos masques), 82 000 herbes, 98 000 buissons, glissières du jeu, trois versions gardées (`choisir_decor.ps1`). Matin : chaussée pliée aux ponts (bords lus dans le vide, 340 m repris). Après-midi : vidéo de reconnaissance (doc 12), où beaucoup d'objets de la vidéo de course étaient placés 20 à 60 m trop tôt. **Consigne du directeur** : la course est la référence, la reconnaissance affine le décor fixe, les objets du rallye restent. Soir : objets du rallye et barres rocheuses du lointain (doc 13), quatre versions sans essai. |
| 13/11 | Essais 2, 3, 4, 6 (doc 14 § 1-7) | Relief proche et lointain, parois, herbe, arbres sur la route, bords saccadés. Le directeur constate en jeu que les pneus restent « terre » : registre de BioBio dans `Paks`, table asphalte livrée à part, confirmée à 18 h 56. |
| 14/11 | Essais 7, 11, 12, 13 (doc 14 § 9-12) | Relief lointain « moins géométrique », route « trop lissée », zone de départ d'après 24 captures Street View fournies par le directeur, portiques verts. **Consigne** du directeur : confier les tâches simples à des agents sur un modèle moins coûteux. Les commissaires, d'abord déclarés impossibles, sont trouvés après que le directeur a demandé de regarder comment font les autres spéciales (doc 15). **Consigne permanente** : n'utiliser que les personnages du jeu, n'en créer aucun. |
| 15/11 | Essais 14, 15, 16 | Personnages cachés par l'étiquette `ServicePark`, mur invisible du Lion d'Or (murs de reprise), habillage de chaussée : le directeur demandait des feuilles, le studio met des décalques. Feux de détresse allumés sur trois monospaces garés (variante « feux allumés » par défaut). Parc d'assistance absent : enquête (doc 16), question au directeur restée ouverte jusqu'au 16/11. |
| 16/11 | Essai 17 | Trop de débris, pas assez de traces ; sous-virage signalé. |
| 17/11 | Essai 18, construction de la 19 | Enquête d'adhérence : **ligne idéale** recopiée de l'axe et **humidité de base 0,1** héritée du niveau gallois. Officiels animés, parc réduit posé sur le parking du départ. |

## 2. Les choix structurants, et pourquoi ils étaient bons

1. **Garder des données et un modèle indépendants du jeu** (`data/`, `modele/`, `export/`). Tout ce qui vient de l'IGN, du LiDAR et des vidéos est rejouable par `scripts/tout_lancer.py`. Le jeu n'est qu'une destination. Cela a permis de changer de voie de construction sans rien perdre.
2. **Valider la physique seule d'abord** (étape 1, voie ACR Extra Stages). Elle a marché du premier coup et n'a plus été remise en cause, ce qui a isolé tous les problèmes suivants dans le décor.
3. **La voie hybride.** Plutôt qu'un niveau à nous (classes souches C++ indispensables pour les acteurs de jeu, chemin non prouvé), le décor cuit par Unreal remplace une cellule de Hafren South, et la physique, le chronométrage, les notes et les déclencheurs restent ceux qu'acr-ref sait écrire. Les retouches de leur outil (`0004` visuels exclus, `0005` personnages, `0006` ligne idéale, humidité, officiels, parc) ont suffi pour tout le reste.
4. **Une seule cellule toujours chargée.** 585 000 objets, 2 Go de conteneur : le directeur a jugé le jeu fluide à chaque essai. Il n'a jamais fallu répartir le décor.
5. **N'utiliser que des éléments du jeu, désignés par leur chemin** (factices de même nom côté Unreal), avec des variantes de matériaux du jeu pour parents. Rien n'est copié, et le rendu prend l'éclairage, le vent et l'aspect du jeu. Exception assumée : nos propres pierres calcaires et poteau de béton (`scripts/pierres_calcaires.py`), parce que les éléments du jeu correspondants étaient d'une teinte non réglable.
6. **Contrôles hors jeu systématiques** : `relire_decor.py` (relecture du conteneur cuit avec les archives du jeu), contrôles de `stage-verify`, `07b` qui refuse d'écrire si un virage est dénaturé, aperçus `21_apercu_conducteur.py` et `23_apercu_lointain.py`. Aucune version n'a planté en jeu.
7. **Deux vidéos, deux rôles** (consigne du directeur du 12/11) : la reconnaissance fait foi pour le décor fixe (plus lisible, sans public), la course pour les objets du rallye. Le LiDAR l'emporte sur les deux pour les ponts et les ponceaux.
8. **Versions gardées avec leur route physique** (`Z:\acrxs\unreal\dist\sol_*`, `choisir_decor.ps1`) : retour arrière possible en une commande à chaque essai.

## 3. Les impasses, et pourquoi

| Impasse | Coût | Pourquoi c'était une impasse | Ce qui l'aurait évitée |
|---|---|---|---|
| Verdict de faisabilité négatif | 1 révision | Recherche web trop générale, réalisations de moins de deux semaines | Chercher d'abord sur GitHub et les forums de mods, par date |
| Lion d'Or interprété sur photos | 3 versions en une nuit | Photo aérienne et Street View ambigus sur un carrefour à niveaux | Lire directement le nuage de points LiDAR brut (parapets, panneaux, fossés s'y lisent) |
| Largeurs relevées sur la vidéo | 1 passe | Étalonnage d'une ligne d'image à ±15 % | Croiser ortho infrarouge + LiDAR ; la vidéo ne tranche qu'entre 5 et 9 m |
| `acr-additive relocate` pour renommer un niveau cuit | ½ journée | L'outil ne relit pas nos niveaux cuits avec versions | Construire directement au chemin de la cellule |
| Cuisson « sans versions » | 1 essai | Propriétés écrites par rang, différentes de celles du moteur du studio | Toujours `-Versionne` dès qu'il y a un niveau |
| Sol en photo aérienne | 1 essai | 20 cm par point : flou de près, ombres des houppiers | Matériau de terrain de Bollène + masques à nous dès le départ |
| Marquage hérité du décalque du jeu | 1 essai (lignes disparues) | Ce matériau de décalque ne s'affiche pas sur nos maillages | Garder `M_Simple` pour le marquage ; essayer un nouveau parent sur 200 m avant de le généraliser |
| Bande de terre mordant sur l'enrobé | 1 essai (bords en zigzag) | Variation tous les 25 cm, visible comme un tremblé | Bord net ; le liseré de pierraille se fait dans les masques du sol |
| « Pièces » et « fissures » posées sur la chaussée | 1 essai | Bandes unies visibles en rectangles gris | Les décalques du jeu (v16) ou les variantes `Patches_Enabled` |
| Parois rocheuses rendues en murs de pierre | 3 essais | Un mur dressé devant un terrain plus bas devient un « immense parapet » | Roche qui épouse le relief LiDAR, posée sur le terrain, jamais en porte-à-faux |
| Couleur de sommet des murs du jeu | 2 essais | Sens deviné (gris 135, puis presque blanc) : **blanc = mousse**, noir = pierre | Lire la couleur de sommet d'un mur du jeu dans les archives et la recopier |
| Herbes et feuilles du jeu rendues en noir | 2 essais | Matériaux à `UseRVTBaseColor` : couleur prise dans la texture virtuelle du niveau d'origine | Exporter chaque matériau d'herbe candidat et refuser ceux qui ont cet interrupteur |
| Arbre à perruque pour le chêne vert | 2 essais | Feuillage mauve en jeu ; choix sur le seul nom | Extraire l'image d'ensemble (`T_<Arbre>NNBillboard_B`) de chaque arbre avant de le choisir |
| Pierres et rochers du jeu | 2 essais | Texture beige rosé assombrie, non réglable | Nos pierres anguleuses dans notre roche claire |
| Table des variantes livrée dans le mod de la route | 1 essai sans effet | Le registre de BioBio est dans `Paks`, pas dans `~mods`, et mieux classé | Inventorier tout `Paks` (et pas seulement `~mods`) avant de livrer une table partagée |
| Météo galloise pour l'adhérence | 1 essai sans effet | Ce n'était pas la cause | Comparer d'abord la physique entière avec une spéciale goudronnée du jeu (§ 6) |
| Débris de chaussée au niveau du studio | 3 essais | Densité de Bollène appliquée telle quelle, plus 5 800 feuilles | Partir bas (2,5 paquets/km) et monter si le directeur le demande |
| Retouche d'acr-ref pour poser le décor | ½ heure d'étude | L'outil ne sait que réutiliser les objets existants de Hafren, en même nombre | Lire d'abord ce que l'outil sait écrire ; la cellule de World Partition était la bonne porte |
| « Pas de commissaires possibles » (14/11) | 1 version sans personnages | Conclusion tirée de la seule forme des personnages du jeu | Regarder d'abord comment le studio fait sur ses spéciales (demandé par le directeur, trouvé en une étude) |
| Contrôle « 10 sur 10 » des personnages | 1 essai (invisibles) | Le contrôle vérifiait le fichier, pas ce que le jeu affiche (étiquette `ServicePark`) | Comparer chaque réglage de nos acteurs à ceux d'acteurs visibles du jeu, pas seulement leur présence |
| Mur invisible du Lion d'Or diagnostiqué sans l'endroit exact | 2 messages du directeur (« non pas du tout ») | Cause supposée (collisions des parois) avant de savoir où il était | Demander l'endroit exact (capture, PK, côté) avant de diagnostiquer ; chercher ensuite dans les données de collision, pas sur la vidéo |
| Versions 8 à 10 empilées sans essai, relectures d'agents successives | 2 erreurs corrigées dans la version suivante (pont du PK 2602) | Deux relectures de la reconnaissance se contredisaient, sans essai entre elles | Une relecture complète, une fois, avec la règle « le LiDAR l'emporte » ; puis un essai |
| Voitures garées posées en série | 1 essai (noires) | Leurs matériaux refusent les instances | Acteurs individuels, variante « feux éteints », comme le studio |

## 4. Ce qui marche, et qu'il faut garder

- **La chaîne** : IGN (BD TOPO, BD Forêt, LiDAR HD MNT/MNS 0,5 m et 2 m, RGE ALTI 5 et 25 m, BD ORTHO et IRC 20 cm) → tracé → chaussée au mètre → régularisation → modèle 3D → export Stage IR → paquet Unreal → route physique acr-ref → relevé du placement → construction Unreal et cuisson → relecture → table asphalte → installation jeu fermé. `pc/scripts/7_tout_refaire.ps1` enchaîne tout en 80 à 90 minutes.
- **Le placement** : route physique d'abord, `relever_placement.py` ensuite, pose du décor en dernier. Décalage route / décor mesuré à 0,0 cm à chaque version depuis la 6.
- **Le calage des vidéos** : la reconnaissance par les virages (`19_calage_video.py`, 50 virages sur 50 retrouvés) ; la vidéo d'un essai en jeu par la barre de progression (`19b_calage_barre.py`, 7 m près, une colonne par 9,6 m en 1080p) ; puis 167 paires jeu / reconnaissance tous les 40 m (`20_planches_comparees.py`) relues par des agents. C'est ce qui a rendu chaque essai exploitable : 161 à 324 écarts localisés par essai, au lieu de quelques captures.
- **La règle de lecture d'une vidéo embarquée** : un objet est au PK de l'image où il sort du champ par le côté, pas de celle où on l'aperçoit (20 à 60 m d'écart). Le calage de la reconnaissance est en avance de 0 à 24 m selon l'endroit : il se corrige sur des repères sûrs (ponts LiDAR, débouchés IGN, `calage_reco_reperes.json`).
- **Les arbres** : un arbre par cime détectée au LiDAR, essence tirée de la BD Forêt, modèle du jeu choisi d'après sa forme mesurée (`profils_arbres.json`) pour ne rien faire dépasser sur la chaussée sous 4,5 m ; un arbre trop grand est réduit, pas retiré.
- **Les matières** réglées sur des valeurs mesurées : couleur moyenne des textures du jeu (`couleur_texture.py`), réglages lus sur les variantes de Bollène, Munster et Sisteron, consignés avec leur raison dans `data/reference/matieres_du_jeu.json`.
- **Les personnages du jeu déplacés**, jamais créés : 10 personnages du parc de Hafren (étiquette `ServicePark` neutralisée), puis les officiels animés des cellules de départ et d'arrivée, reportés à la même distance de leurs repères et du **bord** de notre route.

## 5. Les versions vues en jeu et ce que chaque essai a corrigé

La numérotation est celle du doc 14. Les versions 5, 8, 9 et 10 ont été installées mais jamais jugées seules ; la 19 est en construction.

| Essai | Version | Remarques du directeur | Corrections principales |
|---|---|---|---|
| 11/11 | étape 1 | La route physique roule | — |
| 11/11 | hybride 200 m, puis complet | Décor affiché, doublons de l'étape 1, puis tout affiché, fluide | Retouche 0004 (visuels exclus), une cellule toujours chargée |
| 12/11 matin | 1 (sol du jeu) | Sol, herbes, buissons, glissières affichés ; plis aux ponts, sol anthracite, massif bleu ardoise | Profil en travers aux ponts (07b étape 3 bis), carte de couleur du sol, éclaircissement lointain |
| 13/11 matin | 2 (vidéo 4 min 30) | Relief médiocre, parois en parapets, bords saccadés, arbres sur la route, herbe jaune et haute | Lissage de l'axe, roche épousant le talus, herbe verte 15-35 cm, fond pierreux clair, vue rasante du lointain |
| 13/11 | 3 | Net progrès, herbe bonne ; lignes blanches disparues, bords en zigzag, arbres qui débordent | Retour à `M_Simple`, bande de bord retirée, forme mesurée des arbres |
| 13/11 soir | 4 | « Beaucoup mieux » ; reliefs à mi-distance « tas de sable », parois, Lion d'Or | Relief au sol jusqu'à 450 m avec vrais arbres, chaussée des ouvrages lue au LiDAR, lignes du Lion d'Or ; pneus asphalte |
| 13/11 soir | 6 | Route « un peu trop bosselée », visuel à travailler | Altitude lissée à 5 cm du relevé ; herbes noires retirées, nos pierres, roche plus claire, haies, poteaux béton |
| 14/11 | 7 | Lointain trop géométrique, parois, touffes à plat sur talus, route trop lissée | 15 pins variés, frange jusqu'à 880 m, falaises recoupées ; route rendue aux 3/4 ; touffes couchées sur la pente ; zone de départ (Street View) |
| 14/11 midi | 11 | « Bonne voie » ; dalle et portique verts, barrière mal axée | Portiques enterrés, falaises au LiDAR 2 m jusqu'à 2 km, poteau de béton du projet |
| 14/11 17 h | 12 | Lointain nettement amélioré, fluide ; zone de départ, parapets, parois | Murs de pierre sèche → roche litée, tabliers sous la chaussée, véhicules et décor de course |
| 14/11 20 h | 13 | Zone de départ en aplats, parking en butte, voitures noires, pas de zone rouge, panneau de fin en hauteur, parois géométriques et « en suspension » (en travers, au-dessus du vide) | Déclencheurs rendus visibles, voitures en acteurs individuels, murs en matière du jeu, parking aplani, roche posée sur le terrain, personnages (0005) |
| 15/11 0 h 45 | 14 | Personnages absents ; mur invisible le long des piquets du Lion d'Or ; enrobé de la route barrée en contrebas ; parapets | Étiquette `ServicePark`, murs de reprise repoussés à plus de 15 m, piquets sans collision, route barrée raccordée, parapets |
| 15/11 | 15 | Demande d'habillage de chaussée, de parc, feux allumés | Décalques du jeu, feuilles, feux éteints (v16) |
| 15/11 soir | 16 | Trop de débris ; feux éteints confirmés | Densité au tiers (v17) |
| 16/11 | 17 | Encore trop de débris, pas assez de traces ; parc absent ; sous-virage | Feuilles retirées, 2,5 paquets/km, traces de pneus ; météo MonteCarlo (v18) |
| 17/11 | 18 | Effets au sol bons ; sous-virage persistant ; parc et officiels voulus ; bugs zone de départ | Ligne idéale, humidité 0, officiels animés, parc réduit, marges des arbres (v19) |

**Bilan** : 14 essais en jeu jugés, 19 versions construites, 80 à 90 minutes par construction complète. Les sujets qui ont coûté le plus d'essais : relief lointain (8), parois rocheuses (8), zone de départ (5), lissage de la route (5), sol (4), débris (3), adhérence (2).

## 6. Les réglages finalement calibrés

Les valeurs ci-dessous sont celles des scripts au 17/11 (dix-neuvième version). Le détail, avec leur raison, est dans les commentaires datés du code et dans `matieres_du_jeu.json` ; le skill les reprend dans `references/valeurs_calibrees.md`.

### 6.1 Route et physique

| Sujet | Valeur retenue | Essais | Où |
|---|---|---|---|
| Lissage en plan | axe d'ordre 3, longueur d'onde ~9 m (`LAMBDA_AXE` 8), fort (30 000) hors des vrais virages ; tolérance 20 à 50 cm selon la source, 0 au dessin à la main ; refus si un rayon change de plus de 10 % | 3 | `07b_regulariser_chaussee.py` |
| Profil en long | altitude lissée (`LAMBDA_Z` 4 000, ~25 m) à 5 cm au plus du LiDAR, puis **3/4 de l'écart rendu** pour les ondulations de plus de 6 m, écrêté à 1,5 cm : 0,08 g moyen, 0,42 g max à 90 km/h | 3 (trop bosselé, trop lisse, juste) | `07b`, `LAMBDA_GRAIN` |
| Dévers | lissé à 2 % du mesuré ; toit admis −4,5 % à +3 % ; saut ≤ 4 %/m | 1 | `07b` |
| Ouvrages | chaussée lue au MNS là où il voit le tablier ; tablier 10 cm sous la chaussée | 2 | `07_chaussee_precise.py`, `11` |
| Matière physique | `PM_SurfaceTarmacSmooth`, accotement terre dure sur 3 m | 0 | `09` |
| Table des variantes | Tarmac / TarmacSnow, météo MonteCarlo, longueur au menu, conteneur à part `zz_…_table_9_P` bâti sur la table du registre installé | 2 | `6_table_asphalte.ps1`, `pneus_asphalte.py` |
| **Ligne idéale** | courbure minimale entre bords, marge 1,2 m, écart ≤ 2,5 m, rappel vers l'axe 3e-4, couloir 1,5 à 3,4 m s'arrêtant à 20 cm du bord ; SkidIntensity selon le rayon (0,8 à 15 m → 0,2 en ligne droite) | 2 (découverte tardive) | `09`, `IDEALE` ; retouche 0006 |
| **Humidité de base** | 0 (Hafren : 0,1) | idem | `4_construire.ps1 -HumiditeNiveau` |
| Murs de reprise | bouts de porte biaisés reportés sur la normale : limite à plus de 15 m de la chaussée | 1 | `09`, `bords_normaux` |
| Portiques d'acr-ref | enterrés ; déclencheurs et zone rouge gardés (pas d'option de visuels avec notre décor) | 2 | `4_construire.ps1` |
| Piquets de rubalise | sans collision | 1 | `12` |

### 6.2 Relief lointain (« pas de pâte à modeler »)

| Sujet | Valeur retenue | Où |
|---|---|---|
| Altitude | MNT LiDAR 0,5 m jusqu'à 550-650 m, **MNT LiDAR 2 m jusqu'à 1 950-2 150 m**, RGE ALTI 5 m jusqu'à 4,5 km, 25 m jusqu'à 30 km ; courbure terrestre et réfraction (k = 0,13) | `13_paysage_lointain.py` (`LIDAR`, `LIDAR_2M`, `R_PROCHE`) |
| Maillage | pas de 5 m jusqu'à 400 m, 10 m jusqu'à 2 km, 20 m jusqu'à 4 km, puis 50/100/200 m ; demi-pas au-delà de 30°, quart de pas au-delà de 50°, jamais sous 2,5 m | `13` (`VERSIONS`, `RAIDE_*`) |
| Hauteur de la surface | **au sol jusqu'à 450 m**, montée à hauteur de cime entre 450 et 650 m | `13` (`CANOPEE`) |
| Arbres des versants | entiers, de 135 à 650 m par bandes (pas 4,4 / 5,5 / 7 m), frange par plaques jusqu'à 880 m, 15 modèles de pin, 65 % de pins, aucun au-delà de 40° ; buissons jusqu'à 380 m | `16`, `ARBRES_LOIN` |
| Images | « vue rasante » : couvert forestier en vert de pinède (62, 82, 52) moucheté de houppiers à trois échelles (amplitude 0,12), pistes et trouées effacées, garrigue (112, 122, 96), champs et rocher nu gardent la photo ; dalles à 50 cm/px à moins de 600 m | `16`, `RASANT` ; `13`, `TRES_PRES_M` |
| Éclairage | normales adoucies de 150 m (0 %) à 800 m (85 %) | `16`, `LOIN_APLAT_*` |
| Falaises (teinte) | pente LiDAR 2 m de 55 à 68°, RGE 5 m de 46 à 58° ; calcaire (218, 212, 198) à 86 %, élargi de 2 m, strates tous les 3,4 m | `16`, `FALAISE` |
| Falaises (roche) | faces de plus de 48° jusqu'à 2 km habillées de la roche du jeu, dépliage 17,5 m, extension aux faces de plus de 40°, recoupe de 2,5 m (+1 m par 400 m), bosselage (`ROMPRE`) | `16`, `FALAISE_ROCHE` |

### 6.3 Roche proche, sol, végétation

| Sujet | Valeur retenue | Où |
|---|---|---|
| Parois | trois genres (lité, blocs, éboulis) ; pas de 12,5 cm, bancs de 18 à 42 cm, blocs 0,5 à 1,5 m, avancée 0,35 m, jupe enterrée de 0,45 m, posées sur le terrain (zéro porte-à-faux), dépliage 2,5 m | `16`, `ROCHE` ; `parois_rocheuses.json` |
| Rocaille | pas de maillage de roche : sol peint en pierraille + nos pierres, 1,8 par m², disparition 160-240 m | `16`, `ROCAILLE` |
| Sol | matériau de terrain de Bollène ; couches : fond pierreux clair (Grèce, clarté 2,0), aiguilles 1,7, herbe verte d'Alsace 2,5, herbe sèche 1,35, terre 1,4, roche 2,5 ; carte de couleur à 118/255 de clarté moyenne ; liseré de pierraille de 2 à 40 cm, herbe verte pleine jusqu'à 2,2 m et effacée à 3,6 m ; roche sur les pentes de 30° (début) à 48° (85 %) | `matieres_du_jeu.json`, `15b_sols_du_jeu.py`, `16` |
| Herbes | 44 candidats par mètre sur 14 m, de 35 cm du bord ; vertes 14 à 32 cm (GreenGrass03, GreenGrassLong02) sur l'accotement, sèches basses ailleurs ; couchées sur la pente de 6° à 55°, raréfiées de 28° à 48° (35 % gardées) ; disparition 90-140 m | `16`, `HERBES` |
| Buissons | Willow 0,5 à 1,4 m pour les arbustes de plus de 0,55 m, Boxthorn au-delà de 1,3 m ; disparition 150-220 m | `16`, `BUISSONS` |
| Sous-bois de bord | de 1,7 à 9 m, bande d'herbe de 2,6 m d'abord ; haies au ras (trois rangs dès 0,9 m) seulement là où relevé ; peu de sous-bois sous un couvert de plus de 7 m | `16`, `SOUS_BOIS` ; `bords_vegetation.json` |
| Fourré | arbustes de 1,8 à 6,5 m là où le LiDAR voit un taillis de 2 à 7 m sans cime, de 12,5 à 135 m | `16`, `FOURRE` |
| Dégagement des arbres | rien sous 4,5 m au-dessus de la chaussée ; surplomb ≤ 3 m (pins de plus de 9 m) ; échelles 0,6 à 1,5 ; marges : bâti 2 m, constructions 2 m, murs 1 m, parc 11 m | `regles_arbres.py` |
| Essences (Provence) | pin d'Alep → `AleppoPine` ; chêne vert → `Boxthorn` (arbuste dense vert sombre) ; un tiers des grands chênes → `BlackmapleMonteCarlo` (jaune, novembre) ; **à éviter** : `Smoketree` (mauve), `SM_Dead_Leaves_01` et `BroomCreeper` (noirs), `SM_Ribwort_01`, `SM_WildGrass01` (noirs, `UseRVTBaseColor`) | `regles_arbres.py`, `16` |

### 6.4 Matières et objets

| Sujet | Valeur retenue | Où |
|---|---|---|
| Enrobé | hérite de `MI_BolleneAsphalt1`, `Base_Tint` (3,35 ; 3,2 ; 2,95), `ColorContrastMacro` 0,4, sommets (0, 0, 0, 0) | `matieres_du_jeu.json` |
| Marquage | `M_Simple` blanc, 12 cm ; axiale en traits rapprochés sous 140 m de rayon | `11_route_ouvrages.py` |
| Pierre des parapets | `MI_MonBolStoneWallsA`, clarté 2,0, teinte beige, **couleur de sommet noire** | `matieres_du_jeu.json`, `MURS_DU_JEU` |
| Béton | clarté 1,7, teinte (1 ; 0,97 ; 0,9) | idem |
| Roche | `MI_BolleneRockfacesParent`, clarté 2,4, saturation 0,45, teinte (1 ; 0,94 ; 0,82) | idem |
| Câbles | 3 par portée, 8 mm de rayon, flèche 0,8 m pour 60 m | `16`, `CABLES` |
| Poteaux | poteau de béton du projet, 8,2 m | `pierres_calcaires.py` |
| Glissières | `MetalGuardrailA`, modules de 4 m | `16`, `GLISSIERE` |
| Habillage de chaussée | décalques du jeu en acteurs ; **pas de feuilles mortes** ; litière 2,5 paquets/km ; une boîte par aire, une par débouché, chacun gardé 4 fois sur 10 ; traces de pneus en sortie des virages de moins de 40 m de rayon et plus de 60°, et dans les épingles (≈ 100 décalques en tout) | `16`, `DETAILS`, `FEUILLES` |
| Véhicules garés | acteurs individuels, variante « feux éteints » | `16`, `relire_decor.py` |
| Panneaux du rallye | lacet = cap de la route + 90°, à 2,5-4 m de l'axe | `mobilier.py` |
| Personnages | jamais à moins de 1 m du bord, regard vers l'axe 15 m en amont | `mobilier.py` |
| Officiels | cellules de départ et d'arrivée de Hafren (A0I1, 0QY7), reportés à la même distance du bord, posés au plus 25 cm au-dessus du sol | retouche 0006 |
| Parc d'assistance | acteurs à moins de 8 m du point de la voiture, posés sur le parking du Grand Caunet (emprise « parking » de `zone_depart.json`), sortie au PK −60 ; le reste enfoncé de 1 000 m | `09`, `PARC` ; retouche 0006 |

## 7. Ce qu'il faut retenir

1. **Mesurer le studio avant d'inventer.** Pour chaque famille (sol, herbe, roche, murs, décalques, ligne idéale, météo, humidité, personnages), lire d'abord les valeurs d'une spéciale goudronnée du jeu (Bollène, Sisteron, Munster) et les reprendre. Presque toutes les impasses du § 3 sont des valeurs devinées.
2. **Un essai en jeu ne sert qu'à ce qui ne se voit pas hors jeu** : rendu des matières, éclairage, ressenti de conduite. Formes, positions, densités, collisions et dépassements se contrôlent avec les aperçus et les relectures.
3. **Changer une seule chose risquée à la fois**, et sur 200 m d'abord (marquage en décalque, parents de matériaux jamais portés par le jeu).
4. **L'hôte gallois laisse des traces** à neutraliser une par une : humidité 0,1, météo Wales, ligne idéale recopiée de l'axe, étiquette `ServicePark`, portiques verts, murs de reprise à 20 m des portes, parc d'assistance à sa place galloise, menus « Hafren South ».
5. **Le LiDAR prime** pour les ouvrages, les talus et le relief ; la reconnaissance pour le décor fixe ; la course pour le décor du rallye ; Street View pour les abords du départ et de l'arrivée.
6. **Le relief lointain doit rester au sol avec de vrais arbres** jusqu'à ~450 m, et suivre le LiDAR à 2 m jusqu'à 2 km. Une photo aérienne posée sur une nappe à hauteur de cime donne le « tas de sable » ; une photo vue du ciel ne montre jamais une falaise.
7. **Tout ce que le directeur a jugé bon est désormais une constante** : le prochain projet doit partir de ces valeurs, pas de zéro.
8. **Avant de dire « impossible », regarder comment fait le studio.** Deux fois le projet a conclu trop vite : la faisabilité le 10/11 et les commissaires le 14/11. Les deux fois, la réponse existait déjà dans le jeu ou chez d'autres moddeurs.
9. **Demander l'endroit exact avant de diagnostiquer** (capture, PK, côté), et chercher la cause dans les données plutôt que sur la vidéo quand le défaut ne s'y voit pas.
10. **Une demande du directeur dit un résultat, pas forcément le moyen** : il demandait des feuilles sur l'asphalte, le studio habille ses routes de décalques. Montrer ce que fait le jeu avant d'appliquer le moyen demandé.
11. **L'autonomie sans essai a un prix.** Elle a permis d'avancer la nuit et pendant les limites d'usage, mais les versions empilées sans essai (quatre le 12/11, trois le 14/11) ont aussi empilé des erreurs, découvertes ensemble au premier essai. Un essai court entre deux grosses passes coûte moins cher.

## 8. Ce qu'il ne faut pas refaire

- Lancer une construction de 80 minutes pour une retouche de teinte : regrouper les corrections, et ne reconstruire Unreal que lorsque le paquet a changé (`--sortie paquet_unreal_cN` pendant qu'Unreal tourne).
- Supprimer un objet qu'on ne comprend pas (mur de l'épingle du km 4,08 retiré en v7, rétabli en v8).
- Livrer une table partagée sans avoir regardé tout le dossier `Paks`.
- Ouvrir le jeu pendant une construction (la route physique n'est alors pas reconstruite : v16).
- Faire confiance au code de retour de l'éditeur Unreal (−1073741819 à la fermeture sans conséquence) : c'est le rapport JSON qui fait foi.
- Réimporter dans Unreal sans supprimer les éléments existants : l'import ne les remplace pas.
- Passer des chemins avec des antislashs à l'éditeur.
- Comparer degrés et mètres (arbres sur les routes annexes jusqu'à la v12) : chaque nouvelle règle de placement mérite un contrôle chiffré dans `relire_decor.py`.

## 9. Coûts, et ce qui les aurait réduits

| Poste | Constat | Économie possible |
|---|---|---|
| Essais en jeu | 14 essais jugés, chacun suivi d'un relevé vidéo complet | Un seul essai « de réception » si les valeurs calibrées sont reprises d'emblée ; un second pour les retouches |
| Constructions | 19 versions × 80-90 min, souvent la nuit | Contrôles hors jeu avant chaque construction ; regrouper |
| Relevés vidéo | 5 relevés complets (course, reconnaissance, parois, objets, relectures v8 et v9) | Un relevé de la reconnaissance fait une fois, au bon calage, avec la règle « sortie du champ » et le schéma JSON final |
| Relief lointain | 8 itérations | Les réglages du § 6.2 d'emblée |
| Parois | 8 itérations | Roche épousant le LiDAR, relue sur planches tous les 6 m, dès la première version |
| Adhérence | 2 essais et une enquête | Comparaison systématique de la route physique avec Munster ou Bollène (`acr-ref export`) avant le premier essai |
| Jetons | Longues sorties de construction relues en entier, relevés d'images faits par le modèle principal ; au moins dix arrêts sur la limite de cinq heures entre le 11 et le 15/11, reprises par réveils programmés ; le 14/11 au matin, 48 % de la limite hebdomadaire consommés, et huit agents lancés dans la matinée. La session principale portait un historique de quatre jours, qui coûtait à chaque tour | Constructions en arrière-plan, journaux filtrés par motif (`7_tout_refaire.ps1` le fait), relevés confiés à des agents sur un modèle moins coûteux (adopté le 14/11), **sessions courtes avec une note de reprise** plutôt qu'une session de plusieurs jours |
| Création d'une spéciale | Copier le projet et retoucher à la main une quarantaine de valeurs codées en dur | `skill-speciale-rallye/scripts/creer_speciale.py` (17/11) : copie et remplacements vérifiés à partir de `speciale.json` |

## 10. Ce qui reste ouvert

- Ressenti d'adhérence après la ligne idéale et l'humidité 0 (dix-neuvième version, pas encore essayée) ; sinon comparer avec Bollène (même température de référence), puis le masque de débris de la matière asphalte.
- Troncs de pin rouge-orangé (le pin du jeu), voûte de branches au-dessus de la route, panneaux directionnels sans équivalent dans le jeu, écran bas sous les glissières.
- Une seule spéciale à la fois : elle remplace Hafren South 1/2. Deux spéciales simultanées demanderaient un second hôte.
- Les scripts sont propres au Grand Caunet en de nombreux endroits. Pour une nouvelle spéciale, `skill-speciale-rallye/scripts/creer_speciale.py` en fait une copie paramétrée et vérifiée ; elle n'a pas encore servi sur une vraie spéciale. L'inventaire et les généralisations facultatives sont dans `skill-speciale-rallye/references/generalisations.md`.
