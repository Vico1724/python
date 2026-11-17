# Valeurs calibrées sur le Grand Caunet (état du 17/11/2026)

Ces valeurs sont celles des scripts de `projets/python/acr-grand-caunet/` à la dix-neuvième version. Elles sont à **reprendre telles quelles** pour une nouvelle spéciale goudronnée de Provence ; ailleurs en France, seules les teintes du sol, les essences et la saison sont à revoir, et toujours en mesurant une texture ou une spéciale du jeu, jamais au jugé.

Colonne « État » : **vu** = jugé bon par le directeur en jeu ; **19** = dans la dix-neuvième version, pas encore vue ; **lu** = relevé dans les fichiers du jeu, non jugeable à l'œil.

Contrôle rapide qu'une copie des scripts n'a pas dérivé : `grep -n "^NOM_DE_LA_CONSTANTE" scripts/<fichier>.py` et comparer à la colonne « Valeur ».

## 1. Route (`07_chaussee_precise.py`, `07b_regulariser_chaussee.py`, `11_route_ouvrages.py`)

| Constante | Valeur | Rôle | État | Essais pour y arriver |
|---|---|---|---|---|
| `TOLERANCE_M` | lidar+ortho 0,20 ; lidar 0,25 ; ortho 0,40 ; vidéo/interpolé 0,50 ; manuel 0 | déplacement admis par source | vu | 1 |
| `LAMBDA_AXE` / `LAMBDA_AXE_FORT` | 8 / 30 000 (léger dans les virages, fort ailleurs ; `CAP_VIRAGE_FRANC_DEG` 12, `FENETRE_CAP` 20, `MARGE_VIRAGE` 8) | ondulation de 15 cm tous les 25-30 m retirée des droites | vu | 3 |
| `ECART_RAYON_MAX`, `ECART_CAP_MAX_DEG`, `ECART_LONGUEUR_MAX_M` | 10 %, 2°, 3 m | refus d'écrire si un virage est dénaturé | vu | — |
| `LAMBDA_BORD` | 3 000 | demi-largeurs, raccord ~40 m | vu | 1 |
| `TOIT_ADMIS`, `SAUT_DEVERS_MAX` | (−4,5 % ; +3 %), 4 %/m | profils en travers douteux (bords lus dans le vide aux ponts) | vu | 1 |
| `LAMBDA_Z`, `TOL_Z_M` | 4 000 (~25 m), 0,05 m | altitude de l'axe | vu | 3 |
| `LAMBDA_GRAIN` + rendu | 1,0 ; 3/4 de l'écart rendu, écrêté à 1,5 cm | « ressenti de route non parfaite » : 0,08 g moyen, 0,42 g max à 90 km/h | vu (v8) | 3 (bosselé → trop lisse → juste) |
| `LAMBDA_DEVERS`, `TOL_DEVERS` | 1 000, 0,02 | dévers | vu | 1 |
| ouvrages | chaussée lue au MNS là où trois points en travers voient le tablier | palier faux de 0,3 à 1 m avant | vu (v5) | 1 |
| `DALLE_RETRAIT` | 0,10 m | tablier sous la chaussée (pas de défaut de sol aux ponts) | vu (v13) | 1 |
| `RAYON_T3_M` | 140 m | axiale en traits rapprochés sous ce rayon | vu | 1 |
| marquage | `M_Simple` blanc, 12 cm, 15 mm au-dessus | le décalque du jeu ne s'affiche pas sur nos maillages | vu | 1 (échec du décalque) |
| bord d'enrobé | net, sans bande de terre (`--bord-enrobe 0`) | la bande mordante faisait un zigzag | vu | 1 |

## 2. Physique (`09_export_stage_ir.py`, `pc/scripts/4_construire.ps1`, `6_table_asphalte.ps1`, retouche 0006)

| Réglage | Valeur | État | Essais |
|---|---|---|---|
| matière de chaussée | `PM_SurfaceTarmacSmooth` ; annexes enrobé `TSD+`, terre `DBK+` ; accotement terre dure sur 3 m | vu | 0 |
| table des variantes | Tarmac / TarmacSnow, `WeatherConfig` MonteCarlo, longueur au menu ; conteneur à part `zz_…_table_9_P` bâti sur la table **du registre installé** (seule notre ligne change) | vu (pneus), météo 18 | 2 |
| `IDEALE` | marge 1,2 m ; écart ≤ 2,5 m ; rappel 3e-4 ; pas 2 m ; couloir (1,5 ; 3,4) m, garde 0,2 m ; SkidIntensity par rayon 15/30/60/120/300/∞ m → 0,8/0,65/0,4/0,25/0,17/0,2, lissée sur 20 m | 19 | 2 (manque d'adhérence signalé aux 17 et 18) |
| repères Munster | écart à l'axe médian 0,47 m ; couloir 150 à 330 cm ; SkidIntensity médiane 0,2, 0,7 sous 30 m | lu | — |
| humidité de base | `--level-wetness 0` (Hafren : 0,1 ; Munster : aucune) | 19 | idem |
| portes | `PAS_PORTES` 10 m, `TOL_PORTES` 0,25 m ; bouts biaisés de plus de `BIAIS_MAX_DEG` 20° reportés sur la normale (limite de reprise à plus de 15 m de la chaussée) | vu (v15) | 1 (mur invisible) |
| obstacles | parapets, murs `PM_WallConcrete`/roche ; poteau cylindre `PM_WallConcrete` ; bois `PM_WallWoodPole` ; troncs `PM_WallWoodTreeTrunks` à moins de 6 m, 3 m de haut ; haie `PM_WallBush` ; piquets de rubalise **sans** collision ; rocher sous 35 cm sans collision | vu | 2 |
| notes | `SEUILS` 1:17°, 2:23°, 3:34°, 4:54°, 5:81°, 6:150° ; `LIEN` 40 m ; `AVANCE` 80 m ; retouches dans `notes_copilote_retouches.json` | brouillon jugé correct | — |
| portiques d'acr-ref | enterrés (hauteur négative), aucune option de visuels avec notre décor (sinon la zone rouge de départ disparaît) | vu (v14) | 2 |
| `PARC` | PK −47, 3 m à gauche, rayon 8 m (164 acteurs) ; reste du parc enfoncé de 1 000 m ; arbres écartés sur 11 m | 19 | — |
| officiels | cellules de départ A0I1 et d'arrivée 0QY7 ; même distance au repère et au **bord** de la route ; au plus 25 cm au-dessus du sol ; portiques « Rally Wales » enfoncés | 19 | — |
| personnages du parc | 4 commissaires + 6 spectateurs déplacés, étiquette `ServicePark` neutralisée ; jamais à moins de 1 m du bord, regard vers l'axe 15 m en amont | vu (v15) | 2 |

## 3. Relief lointain (`13_paysage_lointain.py`, `16_paquet_unreal.py`)

| Constante | Valeur | État | Essais |
|---|---|---|---|
| `R_PROCHE`, `R_MAX` | 4 500 m (RGE ALTI 5 m), 30 000 m (RGE ALTI 25 m) ; `K_REFRACTION` 0,13 | vu | — |
| `VERSIONS["complet"]` | pas 5 m → 400 m, 10 m → 2 km, 20 m → 4 km, 50 → 10 km, 100 → 20 km, 200 → 30 km ; textures 1024/1024/512 | vu (v12) | 2 |
| `CANOPEE` | (450, 650) m : au sol jusqu'à 450 m | vu (v5, « tas de sable » corrigé) | 2 |
| `LIDAR` | (550, 650) m : MNT 0,5 m | vu | 2 |
| `LIDAR_LOIN_M`, `LIDAR_2M` | 2 200 m ; (1 950, 2 150) m : MNT 2 m | vu (v12) | 2 |
| `RAIDE_DEG`, `RAIDE_FORT_DEG`, `RAIDE_BASE_M`, `RAIDE_PAS_MIN_M` | 30°, 50°, 4 m, 2,5 m | vu | 2 |
| `TRES_PRES_M` | 600 m (dalles à 50 cm/px) | vu | 1 |
| `ARBRES_LOIN` | de 135 à 650 m ; bandes (300 m, pas 4,4), (450, 5,5), (650, 7,0) ; frange jusqu'à 880 m au pas de 9 ; MNH ≥ 3 m ; 65 % de pins (15 modèles) ; aucun au-delà de 40° ; hauteur 4-20 m ; disparition 950-1 300 m ; buissons jusqu'à 380 m (pas 3,6, 0,6-2,4 m) | vu (v8-v12) | 3 |
| `RASANT` | sombre (0,50 ; 0,36) ; couvert (0,12 ; 0,42) ; rayons 14 / 7 m ; forêt (62, 82, 52) ; garrigue (112, 122, 96) ; référence 0,30 ; contraste 0,6 ; part de la photo 0,3 ; détail 0,7 ; nu clair (0,48 ; 0,72) à 0,75 ; houppiers 0,12 à 3,2 m, échelles (1 ; 0,5), (2,5 ; 0,35), (8 ; 0,25) | vu (v12) | 4 |
| `LOIN_APLAT_DE/A` | 150 → 800 m (normales adoucies jusqu'à 85 %) | vu | 2 |
| `FALAISE` | pente LiDAR 2 m (55 ; 68)°, RGE 5 m (46 ; 58)° ; fondu 150 m ; couleur (218, 212, 198) à 0,86 ; élargie de 2 m ; strates tous les 3,4 m à 0,20 | vu (v12) | 4 (pâle, enneigé, flou) |
| `FALAISE_ROCHE` | pente ≥ 48° jusqu'à 2 000 m ; dépliage 17,5 m ; bord ≥ 40°, 1 anneau ; coupe 2,5 m + 1 m par 400 m | vu (v12) | 3 (dômes lisses, dents de scie) |
| `ROMPRE` | 4 coupes ; bord 1,5 m ; ressaut 2,2-9 m ; grain 0,6-2,2 m ; part de face 0,35 | vu | 1 |

## 4. Roche proche et rocaille (`16_paquet_unreal.py`, `parois_rocheuses.json`)

| Constante | Valeur | État | Essais |
|---|---|---|---|
| `ROCHE` | pas 0,125 m ; biseau 7 m ; allonge 6 m ; portée 10 m ; enfoui 0,45 m ; épaisseur 0,16 ; pente (9 ; 24)° ; dépliage 2,5 m ; marge à la chaussée 0,3 m | vu (v14) | 8 |
| genres | lité : avance 0,35, bancs 0,18-0,42, blocs 0,5-1,5, lacunes 0,30 ; blocs : 0,5 / 0,6-1,1 / 1,2-2,4 / 0,2 ; éboulis : 0,45 / 0,3-0,45 / 0,6-1,3 / 0,08 | vu | — |
| règles | posée sur le terrain LiDAR, **zéro sommet en porte-à-faux** (contrôle), jamais dressée devant un terrain plus bas ; une pointe ne dépasse pas son voisinage ; mur de pierre sèche haut → paroi litée avec mur de collision invisible | vu | — |
| `ROCAILLE` | 1,8 pierre/m² ; disparition 160-240 m ; finesse 2,6 ; enfoncement 0,22 ; pierres A-D du projet de 0,14 à 0,90 m | vu (v7) | 2 |

## 5. Sol (`15b_sols_du_jeu.py`, `16_paquet_unreal.py`, `matieres_du_jeu.json` → `sol`)

| Réglage | Valeur | État |
|---|---|---|
| parent | `MI_MonteCarloS1BolleneTerrainFirstChild` ; cellules de 350 m alignées sur l'origine du monde ; masques 1 024 px (A : aiguilles, herbe haute, herbe sèche, terre ; B : cailloux) ; carte de couleur 4 096 px, côté = `UVDivideWP` × 70 m | lu, vu |
| couche 1, fond | `GreeceShared/GravelTextures/T_SoilAndGravel_00`, taille 3 m, clarté 2,0, saturation 0,55, teinte (1 ; 0,96 ; 0,86) | vu (v7) |
| couche 2, aiguilles | `GreeceShared/TerrainTextures/T_PineNeedles`, 2 m, 1,7 / 0,85, (1 ; 0,97 ; 0,92) | vu |
| couche 3, herbe verte | `AlsaceShared/TerrainTextures/T_AlsaceGreenGrass1`, 3 m, 2,5 / 1,15, (1 ; 1,04 ; 0,9) | vu |
| couche 4, herbe sèche | `GreeceShared/TerrainTextures/T_GrassDried_01`, 4 m, 1,35 / 0,8 | vu |
| couche 5, terre | texture de Bollène, 1,4 / 0,6, (1 ; 0,94 ; 0,84) | vu |
| couche 6, roche | `MonBolRockfaces/T_RockSurfaceSbcjgap0`, 4 m, 2,5 / 0,4, (1 ; 0,95 ; 0,84) | vu |
| `SOL_CARTE_CIBLE` | clarté moyenne 118/255 (Bollène : 86,5) | vu |
| accotement | liseré de pierraille de 0,02 à 0,40 m ; herbe verte pleine jusqu'à 2,2 m, effacée à 3,6 m | vu (v7) |
| `PENTE_ROCHE` | 30° → 48° (85 %) | vu |
| `NDVI_VIGOUREUX`, `CLARTE_CALCAIRE` | (0,30 ; 0,42), (90 ; 130) | vu |
| sommets du terrain sous la chaussée | abaissés à 15 cm sous l'enrobé s'ils sont à moins de 8 cm | vu |

## 6. Végétation (`10_semis_arbres.py`, `regles_arbres.py`, `16_paquet_unreal.py`)

| Constante | Valeur | État | Essais |
|---|---|---|---|
| semis | un arbre par cime LiDAR (MNS − MNT), `BANDE` 135 m, `H_ARBRE` 2 m, `H_ARBUSTE` 0,4 m, `MARGE_CHAUSSEE` 0,5 m, `MARGE_BATI` 2 m ; essence tirée de la BD Forêt | vu | — |
| attribution | maillage du jeu de taille voisine (`attribution.py`), échelles 0,6 à 1,5 (Boxthorn 0,3 à 1,5) | vu | 1 |
| dégagement | `DEGAGE_M` 4,5 (rien au-dessus de la chaussée sous 4,5 m), `SURPLOMB_MAX_M` 3, `SURPLOMB_PIN_M` 1 pour un pin de plus de `HAUT_PIN_M` 9 m ; à moins de `BANDE_M` 14 m, modèle choisi d'après sa forme mesurée (`profils_arbres.json`) ; un arbre trop grand est réduit, pas retiré | vu (v4) | 3 |
| marges | bâti 2 m, constructions 2 m, murs 1 m, parc 11 m, zones ouvertes 25 % gardés sur 16 m | 19 (constructions 2 m) | 2 |
| pistes IGN | route empierrée 3,6 m terre ; chemin 2,6 m ; sentier 1,1 m, dégagés | vu | — |
| `HERBES` | bande 14 m dès 0,35 m du bord ; 44 candidats/m ; disparition 90-140 m ; « vert » GreenGrass03 0,62, GreenGrassLong02 0,36 ; « sec » DryGrass05 0,44, DryGrass06 0,18, WildGrass03 0,14, GreenGrass03 0,12 ; nos pierres de 10 à 38 cm ; couchées de 6° à 55°, raréfiées de 28° à 48° (35 %) | vu (v8) | 4 |
| `BUISSONS` | Willow_03a dès 0,55 m ; Boxthorn au-delà de 1,3 m ; disparition 150-220 m | vu | 1 |
| `SOUS_BOIS` | 1,7 à 9 m, pas 1,1, 3 par pas, MNH ≥ 1,3 m ; bande d'herbe 2,6 m ; haie au ras en trois rangs ((0,9-1,3 m, pas 1, 1,2-1,9 m), (1,9-2,7 ; 1,3 ; 2,4-4,6), (3,4-4,8 ; 1,8 ; 3-6,5)) seulement là où relevé ; sous couvert > 7 m, 70 % gardés et buissons bas 1,2-2,8 m ; pins de bord à 2,2-4,2 m là où MNH > 8 m | vu (v7) | 3 |
| `FOURRE` | 12,5 à 135 m, pas 3,2 ; taillis MNH 2-7 m sans cime à 2,5 m ; sujets 1,8-6,5 m | vu (v7) | 1 |
| essences (Provence, novembre) | pin d'Alep → `AleppoPine` ; pin noir → `BlackpineMonteCarlo` ; chêne vert et sous-bois → `Boxthorn` ; un tiers des grands chênes → `BlackmapleMonteCarlo` (jaune) ; cyprès, olivier du jeu | vu (v6) | 2 |
| **interdits** | `Smoketree` (mauve), `SM_Dead_Leaves_01`, `BroomCreeper` (noirs), `SM_Ribwort_01`, `SM_WildGrass01` (`UseRVTBaseColor`) ; pierres et rochers du jeu (rosés) | vu | 5 |

## 7. Matières (`data/reference/matieres_du_jeu.json`, `MURS_DU_JEU`)

À copier tel quel. Résumé :

| Matériau | Parent | Réglages |
|---|---|---|
| `MI_GC_Enrobe` | `MI_BolleneAsphalt1` | `Base_Tint` (3,35 ; 3,2 ; 2,95), `ColorContrastMacro` 0,4 ; sommets (0, 0, 0, 0) ; plaqué en coordonnées monde |
| `MI_GC_Pierre` | `MI_MonBolStoneWallsA` | `Mat1_UVTiling` 2,9, clarté 2,0, teinte (1 ; 0,93 ; 0,8) ; **couleur de sommet (0, 0, 0, 255) : noir = pierre, blanc = mousse** ; dépliage 2/5 |
| `MI_GC_Roche` | `MI_BolleneRockfacesParent` | clarté 2,4, saturation 0,45, teinte (1 ; 0,94 ; 0,82) ; couleur de sommet bleu 255 (roche), rouge = usure |
| `MI_GC_Beton`, `Chaperon` | béton de Bollène | clarté 1,7, teinte (1 ; 0,97 ; 0,9) ; dépliage 2/3,144 |
| `MI_GC_Dalle` (tabliers) | idem | clarté 0,62, teinte 0,92 (gris de l'enrobé) |
| enduits | `MI_MonBolConcreteWallsA` | ocre (1 ; 0,8 ; 0,56) à 1,05 ; blanc (1 ; 0,92 ; 0,76) à 1,7 ; maison (1 ; 0,86 ; 0,66) à 1,45 ; clair (1 ; 0,93 ; 0,74) à 1,0 — **teintes propres au Grand Caunet, à remesurer sur Street View** |

## 8. Objets (`16_paquet_unreal.py`, `mobilier.py`, `pierres_calcaires.py`)

| Constante | Valeur | État |
|---|---|---|
| `GLISSIERE` | `MetalGuardrailA` Simple Begin/Center/End, module 4 m, enfoncé 5 cm ; lisse côté +Y | vu |
| poteaux | poteau de béton du projet, fût effilé de 8,2 m, traverse, isolateurs | vu (v12) |
| `CABLES` | portée ≤ 115 m ; flèche 0,8 m pour 60 m ; 12 segments ; rayon 8 mm ; (46, 46, 48) ; 3 par portée à ±1 m et au milieu | vu |
| `RUBALISE` | 0,90 m de haut, 7,5 cm, motif de 30 cm, flèche 1,2 %/m ; piquets de bois si appui « arbres » | vu |
| panneaux du rallye | lacet = cap + 90°, 2,5 à 4 m de l'axe ; face d'un panneau routier : +Y | lu, vu |
| véhicules garés | acteurs individuels (pas d'instances) ; variante « feux éteints » | vu (v16) |
| `DETAILS` (habillage) | litière 2,5 paquets/km (1-2 boîtes, écart ≥ 30 m, 85 % d'aiguilles sous les pins) ; aires 1/40 m, au plus 1, gardées 40 % ; débouchés 1 par débouché (routes empierrées IGN), gardés 40 %, ornières 1-2 ; épingles (R ≤ 22 m, ≥ 70°) gomme 1-2 ; traces de pneus en sortie des virages R ≤ 40 m et ≥ 60°, une paire au freinage des épingles | vu (v18 : « effets au sol bons ») |
| `FEUILLES` | `actif: False` | vu |

## 9. Ce qui n'est pas calibré et doit être relevé à chaque spéciale

- Position et genre de chaque paroi, parapet, mur, glissière, poteau, aire, haie au ras, rubalise et panneau : relevés vidéo (`releves_video.md`).
- Zone de départ et d'arrivée : Street View.
- Teintes des enduits et des bâtiments : mesurées sur Street View au soleil et à l'ombre.
- Palette d'essences si l'on quitte la Provence calcaire ; teinte du fond pierreux si le sol n'est pas calcaire.
- Saison : herbe verte (automne, hiver, printemps) ou sèche (été) ; feuillus jaunes seulement en automne.
