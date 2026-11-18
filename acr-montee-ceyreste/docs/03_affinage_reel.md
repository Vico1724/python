# 03 - Affinage d'après le réel (18/11/2026)

*Demande de l'utilisateur (18/11/2026, mots exacts) : « affine quand meme les eleemnt la carte la route les sols les murret lais maison si ya avec les elements relel verifie le tracer de al route, verifei les panneau aussi pour renforcer l'imretion le paysage au alentours » ; et « il faudra pense au villange de ceyreste en bas aussi ».*

**Rien de ce travail n'a été vu en jeu ni dans Unreal.** « Vérifié » ci-dessous veut dire : sortie regardée (figure, planche, aperçu hors jeu).

## 1. Tracé et largeur

Script `scripts/27_verif_trace.py` ; figures `figures/affinage/verif_trace.png`, `verif_largeur_bandes_1..4.jpg`, `verif_largeur_planche.jpg`, `verif_axe_zooms.jpg`, `verif_epingles.jpg` ; chiffres `data/processed/verif_trace.json`, mesures à l'œil `data/reference/verif_largeur_ortho_mesures.json`.

### Axe

| Comparaison (PK 0 → 3020, un point tous les 5 m) | médiane | 95 % | max | part > 0,5 m |
|---|---|---|---|---|
| axe retenu ↔ axe BD TOPO | 0,74 m | 2,35 m | 4,42 m (PK 2187) | 63 % |
| axe retenu ↔ axe OpenStreetMap (Overpass, 18/11/2026) | 0,49 m | 1,71 m | 2,96 m | 50 % |
| BD TOPO ↔ OSM (pour mémoire) | 0,83 m | 2,66 m | 4,07 m | 66 % |
| **axe retenu ↔ ligne axiale peinte, lue sur l'ortho 20 cm (21 points)** | **0,25 m** | — | **1,0 m (PK 451)** | **1 point sur 21** |

Les deux vecteurs s'écartent autant l'un de l'autre que de notre axe : ils ne font pas foi au mètre (BD TOPO : précision planimétrique annoncée 2,5 m). La seule référence au décimètre est la ligne peinte, visible sur l'ortho là où il n'y a pas d'arbre au-dessus : l'axe calculé par 07 la suit à 0,25 m près en médiane. **Seul écart > 0,5 m : PK 444-468** (débouché, bords interpolés) : l'axe passait 1,0 à 1,2 m à gauche de la ligne peinte (mesuré deux fois : à l'œil et par la détection automatique). **Corrigé** par une entrée de `data/reference/chaussee_corrections.json` (bord gauche ramené à 7,7 m du bord droit ; le mur de pierre du bord droit, vu sur Panoramax, fixe ce bord).

Recherche automatique de la ligne axiale sur tout le parcours : trop peu de points sous les pins (8 % des stations) et quelques confusions avec une rive dans les épingles ; non retenue comme preuve, seulement comme indice.

### Largeur

La médiane de 7,44 m était soupçonnée d'être surestimée d'environ 1 m. Mesures à l'œil sur des bandes d'ortho redressées et graduées tous les 0,5 m (lecture ±0,25 m) :

| | n | médiane | étendue |
|---|---|---|---|
| distance entre lignes de rive | 20 | **6,93 m** | 5,8 - 7,6 m (9,0 m dans l'épingle du PK 2226) |
| enrobé complet (les deux bords visibles) | 9 | 8,4 m | 6,6 - 9,5 m (caniveaux et accotements revêtus compris) |
| largeur 07 aux mêmes points | 22 | 7,6 m | 5,0 - 9,5 m |
| BD TOPO « largeur de chaussée » | — | 7 m sur 3 746 m, 5,5 m sur les 150 m de l'approche | |

Conclusion : **la surestimation d'1 m n'est pas confirmée.** Là où l'enrobé est visible, 07 mesure l'enrobé : lignes de rive (≈ 6,9 m, cohérent avec les 7 m de la BD TOPO) plus 0,2 à 0,5 m d'accotement revêtu de chaque côté. Les bords « 1 à 2 m au-delà de l'enrobé » vus sur les anciennes planches sont dans les débouchés (PK 444-468, corrigé) ; dans les épingles (PK 880-905, 1510-1525) la largeur de 07 (7,6 à 9,1 m) est conforme à l'enrobé visible. En revanche l'erreur inverse existe : **sous les pins, 07 sous-estimait la chaussée** (4,8 à 5,6 m aux PK 1028-1073 et 1798-2004, alors que l'ortho y montre les rives à 5,8-6,6 m l'une de l'autre et Panoramax deux voies normales). Corrigé par une largeur minimale de 6,4 m (entrée « minimum », symétrique, de `chaussee_corrections.json`) : 849 stations relevées, les autres ne bougent pas.

| Largeur retenue (PK 0 → 3020) | médiane | 5 % | 95 % |
|---|---|---|---|
| avant | 7,44 m | 5,38 m | 9,40 m |
| après | 7,44 m | 6,37 m | 9,28 m |

Méthode : pas de changement de 07 lui-même ; les corrections passent par son fichier de corrections, comme au Grand Caunet. Contrôles de 07b après correction : tous passés.

## 2. Relevé du bord de route (imagerie de rue)

- **Panoramax** (méta-catalogue `api.panoramax.xyz`, sans clé) : 864 images à moins de 25 m de l'axe. 793 sont des images **360°** de la **Région Sud (Immergis), 08/09/2025, licence Etalab 2.0**, une seule collection, prises en descendant, **sans trou de plus de 30 m entre PK −142 et 3766** ; 71 viennent d'un contributeur individuel (2019, CC-BY-SA 4.0), non utilisées. Liste : `data/reference/photos_rue_panoramax.csv` (identifiant, position, PK, date, licence, URL). Images (247, une tous les 15 m, 2,1 Go) dans `data/raw/panoramax/` (non versionné). **Mapillary** : jeton obligatoire, non utilisé.
- **Dépouillement** : `scripts/26_photos_rue.py planches` fait 31 planches de 8 bandes de 200° centrées sur le sens de la montée ; elles ont été lues **par moi**, planche par planche (pas de sous-agent : l'outil de sous-agents n'était pas disponible dans cette session), puis 22 objets douteux ont été agrandis à fort grossissement pour lire les panneaux. Relevé brut, objet par objet, avec images et description : `data/reference/releve_panoramax_2025.json`.
- **Recalage** : `scripts/29_releve_panoramax.py` cherche la signature de chaque objet dans le LiDAR HD le long du bord de chaussée et verse le résultat dans les fichiers lus par la chaîne. Bilan : `data/processed/releve_panoramax_bilan.json`, figure `figures/affinage/releve_panoramax.png`.

| Type | relevés | bornes au mètre (LiDAR) | approximatifs (photo, ±10 m) |
|---|---|---|---|
| glissières (simples) | 6 (442 m) | 0 | 6 |
| murs, murets, parapets de bord de route | 32 | 13 | 19 |
| têtes de ponceaux | 3 (+1 « rien à gauche ») | 1 | 2 |
| parois et talus rocheux | 25 | 22 | 3 |
| objets ponctuels (panneaux, balises, bornes, poteaux, mobilier) | 20 | 0 | 20 |
| **total** | **87** | **36 (41 %)** | **51 (59 %)** |

Ce que le LiDAR voit et ne voit pas : le MNS 0,5 m de l'IGN **ne contient ni les glissières ni les parapets minces** (vérifié au PK 1150 : le mur-parapet de 0,75 m vu en photo n'a aucune trace dans le MNS, seule la chute du terrain derrière lui apparaît) ; il voit les talus, les parois et les murs de soutènement (montée du MNT). D'où : bornes au mètre pour 22 parois sur 25 et pour les murs de soutènement, bornes photo pour les glissières et les parapets. La BD TOPO (`construction_lineaire`) n'a que 6 murs de soutènement près de l'axe, à ±2-3 m ; posés jusqu'ici en voiles génériques, ils sont **remplacés par le relevé** (`epreuve.json` : `murs_bd_topo_remplaces_par_releve`).

Principaux objets (détail dans les fichiers) :
- **Glissières** : G 500-580 (au-dessus du vallon), G 822-925 (extérieur de l'épingle du 893), G 1597-1606 (courte), G 2320-2455, D 2655-2705, G 2935-3000 (épingle du 2950).
- **Murs et parapets** : murets de pierre sèche du bas (PK −120 à 210, oliveraies), bordure maçonnée D 287-350, mur à chaperon D 440-470, murs-parapets de moellons à chaperon G 705-740, G 768-826, G 925-968 (chaperon de pierres de chant), D 1120-1335 (quatre pièces, extrémités blanches), G 1605-1655, G 2458-2520 ; parapet de béton à bandes blanches G 2520-2565 ; murs de soutènement D 2105-2160, D 2869-2897 ; murs des propriétés du hameau au-delà de l'arrivée (3100-3270, 3386-3562).
- **Ponceaux** : PK ≈ 2016, têtes de béton basses (0,55 m) des deux côtés, vues (remplacent la valeur supposée de 0,70 m) ; PK ≈ 2910, tête de béton à droite.
- **Parois** : talus taillés de calcaire lité presque partout d'un côté ; grandes parois massives G 1115-1444 (jusqu'à 5 m), D 570-720 ; talus de blocs blancs D 752-801.
- **Panneaux** (nomenclature française) : EB20 sortie d'agglomération « CEYRESTE » D PK ≈ −34 ; A15b (animaux sauvages) + panonceau « 4,6 km » et A1c (succession de virages, le 1er à droite) + « 3 km », D PK ≈ 86, sur poteau béton ; balises J4 (chevrons blancs sur bleu) G PK ≈ 902 et 913 derrière la glissière ; borne de point de repère **« D3 ▸ 7 » (PR 7)** G PK ≈ 2111 et plaquette probable du PR 8 G PK ≈ 3112 (1 000 m d'écart : cohérent avec le calage des PK) ; B1 sens interdit sur les voies latérales ; trois panneaux vus de dos (pour les descendants, non lisibles) ; deux panneaux d'information non lus. Aucune limitation de vitesse vue dans le sens de la montée. Le PR 6 (attendu vers le PK 1110) n'a pas été trouvé.
- **Marquage** : axiale discontinue partout, traits ≈ 3 m et intervalles 1 à 1,5 m sur l'ortho (type T3) ; rives discontinues des deux côtés. `marquage_route.json` : les tronçons repris du Grand Caunet (PK de la D1, carrefour du Lion d'Or) étaient faux ici, remplacés. Enrobé plus sombre et récent de ≈ 1855 à ≈ 2700, gris fissuré ailleurs (non rendu : `aspect_chaussee.json` reste celui du Grand Caunet, aucune pièce posée).
- **Bas-côtés** : terre rouge (terra rossa) nue, souvent en bourrelet, herbe sèche clairsemée, cunettes de béton à l'intérieur de quelques courbes (380-480, 310-350).

Posé dans le paquet : glissières, murs, parapets, têtes de ponceaux, parois, 7 objets ponctuels (A15b et A1c par les triangles génériques du jeu — **substituts signalés**, aucun A15b ni A1c dans le jeu —, 2 balises J4, 2 bornes de PR, 2 poteaux bois). **Non posés** (listés dans `mobilier_bord_de_route.json`, `non_poses`) : EB20, panneaux de dos ou non lus, abri de bus du Plan de Masse, poteaux d'incendie, bacs à déchets, barrière en tube, bloc béton blanc ; clôtures, grillages, portails, haies taillées, garde-corps ; poteaux et lignes électriques (vus en nombre, non comptés poteau par poteau).

**Contrôle de mes lectures** : 20 agrandissements des images HD (12 288 px) ; 2 lectures de planche corrigées (le « petit poteau blanc » du PK 1745 est une marque de sentier sur un tronc ; la balise J4 notée vers le PK 2975 n'y est pas, retirée), 2 précisées (le « panneau jaune » du PK −30 est un panneau temporaire et cache l'EB20 voisin ; le « petit panneau jaune » du PK 2108 est la borne du PR 7), 2 recherches vaines (PR 6), les autres confirmées.

### Ambiance du jour de course (complément de l'utilisateur, 18/11/2026)

Une description générale de l'épreuve (rédigée par un autre assistant, à vérifier) mentionne : public derrière des rubalises sur les talus au-dessus des épingles, commissaires, redescente en convoi vers un « parc de départ ». **Rien de cela n'est posé** : aucune photo d'édition passée n'a été dépouillée, donc aucune position. La chaîne sait poser des rubalises (`mobilier_bord_de_route.json`, `rubalises`) et des objets du rallye ; les commissaires et le public ne sont pas posables (maillages animés du jeu, voir le Grand Caunet). Proposition, à valider : rubalises au bord extérieur des épingles des PK 893, 1517, 2150 et 2950, marquées « déduit d'une description générale ».

## 3. Maisons et bâti

Dans le couloir modélisé (300 m), 656 bâtiments BD TOPO, dont 36 à moins de 25 m de l'axe, presque tous dans l'approche (PK −150 à 0) et au hameau du Grand Caunet (au-delà de l'arrivée estimée). Photos : maisons de crépi beige à toits de tuiles rondes, murs de clôture enduits ou en moellons, portails métalliques. **Aucune maison n'est posée** : la chaîne ne sait poser des volumes simples (`12_carrefours_annexes.py`, `_batiment`) que dans `zone_depart.json`, et l'utilisateur a refusé les volumes unis (« Minecraft ») sur le projet de référence. Ce qui est fait : les murs de clôture et de soutènement vus au bord de la route sont posés (§ 2). À décider : volumes simples avec toit à deux pans pour les ~36 maisons à moins de 25 m, ou assets du jeu.

## 4. Sols et paysage

- **Essences** : PK 60-235, Panoramax montre des oliveraies derrière les murets de pierre sèche et de grands chênes verts ; la BD Forêt n'y a rien et la BD TOPO y voit des haies et une vigne, si bien que le semis y mettait surtout des pins. Nouvelle zone relevée `data/reference/zones_essences_relevees.json` (olivier 55 %, chêne vert 30 %, pin d'Alep 15 %, bande de 45 m), lue par `10_semis_arbres.py`. Ailleurs la pinède d'Alep dense avec chênes verts et kermès du semis est conforme aux photos.
- **Accotements** : la règle « herbe verte rase de 2 à 3,6 m » venait de la reconnaissance du Grand Caunet ; ici la bande prend 60 % de terre et 30 % d'herbe sèche (`epreuve.json` : `accotement`, lu par `15b_sols_du_jeu.py`, donc seulement pour le sol « façon jeu »). Réserve : images de septembre ; en avril (date de l'épreuve), l'herbe peut être plus verte.
- **Lointain** : la colline boisée en face (Grand Caunet, Saint-Pons) et les crêtes calcaires sont rendues par le lointain existant (MNT 2 m et RGE ALTI) ; la mer n'est visible sur aucune planche de la montée. Pas de changement.

## 5. Village de Ceyreste (préparation, rien n'est construit)

Script `scripts/28_village.py` ; figure `figures/affinage/village_ceyreste.png` ; données `data/processed/village/` (itinéraire, bâtiments par option, `chiffrage.json`).

- Salle polyvalente : chemin des Peupliers (OSM, nœud 4374868094), 1,1 km au sud-ouest de la mairie ; mairie : BD TOPO. Itinéraire salle → mairie → début de l'axe modélisé (PK −150), D3 préférée : **2 870 m** (1 137 m jusqu'à la mairie, puis 1 733 m par le boulevard Alphonse-David et la D3).
- **Option A, village en décor lointain vu depuis le départ** : 976 bâtiments BD TOPO à moins de 1,5 km du départ, à plus de 150 m de l'axe, en vue directe (MNT 2 m) depuis au moins un des PK −149, 0, 150, 300 ; 74 000 m² d'emprise. Volumes simples (murs enduits, toits de tuiles à deux pans, hauteur BD TOPO / LiDAR) : environ 60 000 triangles, quelques Mo ; emprise jouable inchangée ; travail estimé à une journée (un script de plus, sur le modèle de `_batiment`, et une vue de contrôle).
- **Option B, village parcourable avec parc d'assistance** : 2 870 m de route en plus (+74 % du linéaire modélisé), 961 bâtiments à moins de 40 m de l'itinéraire ou au cœur du village (61 500 m²), relief et orthophoto à télécharger à l'ouest de x = 914 500 (le relevé LiDAR 0,5 m actuel s'arrête là), chaussée au mètre des rues étroites, une vingtaine de rues latérales à fermer, parc d'assistance derrière la mairie ou à la salle polyvalente ; plusieurs jours de chaîne plus des essais en jeu ; paquet plus lourd d'environ 30 à 40 %. Elle répond au « parc de départ » où les voitures redescendent entre les montées (description de l'épreuve rapportée par l'utilisateur) et rouvre la décision n° 3 (parc d'assistance).

## 6. Régénération et contrôles

Chaîne relancée de l'étape 07 à 16 (`--sol photo`), sans retéléchargement : code 0, export sans erreur (532 portes, 27 notes sur 27, 3 025,37 m), paquet sans erreur (468 maillages, 243 457 instances, 20 parois rocheuses sur 1 187 m). Planches photo réelle / aperçu avant / aperçu après : `figures/affinage/comparaison/comparaison_pk_0519.jpg`, `_0807`, `_1147`, `_1286`, `_2012` (scripts/30_planches_comparaison.py). Détail et réserves : `docs/ETAT.md` § « Affinage du 18/11/2026 ».

Nouveaux scripts (hors chaîne 01-16, à relancer à la main) : `26_photos_rue.py` (inventaire, téléchargement, planches Panoramax), `27_verif_trace.py` (contrôle de l'axe et de la largeur), `28_village.py`, `29_releve_panoramax.py` (recalage LiDAR et remplissage des relevés), `30_planches_comparaison.py`. Ordre pour refaire : 26 inventaire → 26 telecharger → 26 planches → (lecture) → 29 → `tout_lancer.py --depuis 7` → 27 → 30.

## 7. Sources ajoutées

- Panoramax, collection Région Sud / Immergis du 08/09/2025, Licence Ouverte Etalab 2.0 — https://api.panoramax.xyz/api
- OpenStreetMap (axe de la D3, salle polyvalente), ODbL — via Overpass et Nominatim, 18/11/2026.
- Lus pour le tracé (complément de l'utilisateur) : la fiche Agenda Auto Moto (déjà citée) redit 3 km entre Ceyreste et le Grand Caunet ; la déclaration de manifestation (declaration-manifestations.gouv.fr, dossier 98930) a répondu « 503 » et n'a pas pu être lue ; l'article de La Provence (10 ans) n'a pas pu être chargé ; Climbfinder « col du Grand Caunet » part de La Ciotat (11,7 km, 423 m) et ne recoupe pas la montée ; aucune autre source ne situe l'arrivée. **3,0 km et l'arrivée estimée sont gardés.**

## 8. Deuxième passe (18/11/2026, après-midi) : décor qui continue, bâti, chaussée, OpenStreetMap, export neutre

Demandes de l'utilisateur (mots exacts, transmises par le coordinateur) :
- « queque screen coté ceyreste aussi stp pense a bien contnuer le decore les arbre aussi a palcer les torn 'abre tout ce genre de chsoes » ;
- « pour tout les objet on reste sur batimetn et tout ca peut etre le top mais si possible de les avoir meme dans la carte unreal c'est encore mieux » ;
- « dans le sens ou au moins si on veut reuse cette carte dans un autre jeu on a tout les mdoel » ;
- « Pense bien à intégrer tout ce qui va être barrière, etc., des troncs, aussi sur la route, des fois il y a des traces de pneus, etc., tout ça, il faut l'intégrer, parce que ça montre, c'est aussi ça l'essence de cette route » ;
- « Tous les panneaux et tout, il faut bien tout le temps penser à tout. C'est pour ça que la script OpenStreetMap est très important. »

Les choix ci-dessous sont des **choix par défaut, non confirmés par l'utilisateur** (décisions 7 à 9 de `ETAT.md`).

### Bâti (`scripts/31_bati.py`)

- **Maisons du bord de route** : 35 posées (36 à moins de 25 m ; une emprise cadastrale mordait sur la chaussée et n'est pas posée). Murs extrudés et toit à deux pans (pente 30 %, débord 0,3 m), en crépi beige et tuiles canal (matières `enduit_maison` et `tuile`). C'est la fonction des bâtiments de la zone de départ du Grand Caunet. Hauteur : faîtage relu sur le LiDAR (MNS − MNT). Au PK 3293, une haie couvrait le toit : la hauteur y vient de la BD TOPO + 1 m.
- **Collision** : façades des 21 maisons à moins de 15 m de la chaussée (`bati_bord_collision.glb`, lu par 09 comme obstacle `PM_WallConcrete`).
- **Les 10 plus visibles depuis la route**, à remplacer en premier par des assets : PK −122 G, −106 D, −53 D, −52 G, 33 D, 2854 D, 2910 D, 3181 D, 3226 D, 3293 D. Les identifiants BD TOPO sont dans `data/processed/bati_bilan.json`.
- **Village (option A)** : 936 bâtiments en volumes simples (`village.glb`, sans collision). Emprise jouable inchangée.
- **Dans le paquet Unreal** : familles `batiments` (14 maillages, 1 616 triangles) et `village` (12 maillages, 45 710 triangles). Ce sont des acteurs StaticMesh nommés `SM_MonteeCeyresteBuilding_<Matière>_<tronçon>` et `SM_MonteeCeyresteVillage_…`, avec un matériau par type (`MI_GC_Enduit_maison`, `MI_GC_Tuile`), des UV en mètres (une répétition tous les 2 m) et des normales par face. Le pivot est au centre de la base. Les noms ne changent pas d'une génération à l'autre tant que le découpage en tronçons de 200 m ne change pas.
- **Non fait** : clôtures et portails des propriétés (pas de maillage ; listés dans les descriptions du relevé), teintes de façade mesurées sur les photos (beige uniforme supposé).

### Végétation (contrôle `scripts/32_verif_vegetation.py`)

Contrôle sur onze secteurs, comparé aux photos (planche d'abords, 8 vues latérales) et au MNH du LiDAR : `data/processed/verif_vegetation_secteurs.json`.
- **Densité et hauteur** : de 32 à 60 arbres pour 100 m à moins de 20 m de l'axe ; couvert LiDAR > 2 m de 51 à 74 % ; hauteur médiane de 9 à 15 m en pinède. Cohérent avec les photos : pinède d'Alep claire sur sous-bois dense de chênes kermès et verts.
- **Essences** : pin d'Alep de 74 à 94 % en pinède ; oliveraies du bas (relevé de la première passe) ; cyprès près des maisons (10 % dans l'approche, 6 % au PK 2150-2350). Aucune règle n'a été changée dans cette passe : rien ne diverge assez des photos.
- **Arbres isolés au bord de la route** : déjà placés à l'apex LiDAR (méthode du semis : un tronc par maximum local du MNH, reporté au bord + 0,8 m quand il surplombe la chaussée). 81 surplombs sont reportés ainsi.
- **Troncs, souches, branches au sol** : les photos montrent très peu de bois au sol en bord de route (débroussaillement DFCI). Aucun tronc couché, aucune pile de bois ni souche nette n'a été relevé aux points examinés. **Rien n'est posé** : le jeu a des maillages (`Props/Nature/WoodLog`, `TreeStump*`, `DeadBranches*`, `Foliage/GroundCover/Greece/BranchDebri`), mais aucune position réelle ne les justifie.
- **Garrigue** : romarin, ciste, genêt et kermès n'ont pas d'équivalent dans le jeu (le catalogue n'a que `BroomCreeper`, rendu noir en jeu). La garrigue reste rendue par `Willow` et `Boxthorn`, comme avant.

### Surface de la chaussée

- **Relevé** sur 24 vues plongeantes de la chaussée : `data/reference/chaussee_surface_releve.json` et `aspect_chaussee.json`. Les 62 éléments de `aspect_chaussee.json` repris par erreur du Grand Caunet sont retirés.
- **Permanent** :
  - passage à un enrobé récent sombre du PK ≈ 1855 à ≈ 2700 ;
  - faïençage fort aux PK 456 et 2857 ;
  - fissures dans les épingles 883-902 et 1501-1517 ;
  - voie de droite reprise au PK 1301.
- **Variable** :
  - arcs noirs de dérapage dans les épingles 1517 et 2150 ;
  - traces serpentines et « donuts » au carrefour du PK 2622 ;
  - aiguilles et terre rouge le long des glissières et des pieds de talus.
- **Réserve** : les photos datent du 08/09/2025, un jour ordinaire, pas un jour de course.
- **Dans le paquet** : la gomme et les traces de pneus ne sont plus posées que dans les virages où les photos en montrent (épingles 1517 et 2150), plus les traces hors virage relevées (PK 2622, 1965, 2860). Avant, toutes les épingles et tous les virages serrés en avaient. Les décalques n'ont ni collision ni effet sur l'adhérence : le sol physique reste celui de la route.
- **Pièces et fissures** : relevées mais non rendues, car les bandes de couleur unie avaient été refusées en jeu au Grand Caunet.
- **Aucune inscription peinte vue sur la chaussée.**

### Panneaux : passe dans le sens de la descente

`scripts/26_photos_rue.py planches --descente` produit 16 planches tournées vers le bas (une image sur deux) : les panneaux destinés aux descendants s'y lisent de face. Trouvés en plus :
- B13 « 19 t » au PK 5 ;
- B14 « 50 » au PK ≈ −20 ;
- borne PR 5 au PK 110 ;
- **A14 + panonceau jaune temporaire « CHAUSSÉE DÉFORMÉE »** au PK 1300 : c'est le triangle vu de dos en montée ;
- AB3a sur la voie latérale du PK 2938 ;
- une rangée de **8 séparateurs en plastique rouges et blancs** devant le mur-parapet du PK 1620-1645. Au premier passage, je les avais pris pour des bandes peintes.

Lecture corrigée au PK 86 d'après la photo HD et OSM : le second panneau est un **A1d** (premier virage à gauche, panonceau 3 km), pas un A1c ; il est posé en triangle générique. La planche 16 (PK 3663-3756, après l'arrivée) n'a pas été lue.

### OpenStreetMap (`scripts/34_osm.py`)

- Overpass a été injoignable toute la journée (délais et coupures sur quatre miroirs). Le script se replie sur l'API OSM v0.6 (`/map`, par dalles) et met le résultat en cache : 7 974 éléments, dont 1 519 dans le couloir ou l'approche du village. Bilan par clé : `data/processed/osm_bilan.json`.
- Recoupement en trois colonnes (`data/processed/osm_croisement.csv`) : 10 objets vus dans OSM et sur photo, 36 dans OSM seul (dont 24 poteaux), 25 sur photo seule. Ce recoupement est automatique, sur le PK seul à ±20 m et un type compatible : il est indicatif.
- **Posé d'après OSM seul** : 12 poteaux électriques à moins de 10 m de l'axe, marqués « OSM seul », confiance faible.
- **Listé, non posé** : chaînes et barrières d'accès des pistes (PK 899, 2095, 3057 ; pas de maillage du jeu).
- La colonne BD TOPO / LiDAR n'est remplie que pour les objets en long (murs, parois : première passe), pas pour les objets ponctuels.
- **Clés absentes de `carte-reelle-unreal/scripts/04_vecteurs.py`** (le script du skill n'a pas été modifié ; la liste est à vérifier contre son code) : `traffic_sign`, `traffic_calming`, `crossing`, `highway=give_way|stop|milestone|street_lamp`, `barrier=*` (seulement une partie), `power=pole|minor_line`, `man_made`, `natural=tree|tree_row|cliff|rock|scree`, `roof:shape`, `roof:material`, `building:levels`, `tracktype`, `access`.

### Grille « ne rien oublier »

| Famille | Sources consultées | Relevé | Posé | Manque, et pourquoi |
|---|---|---|---|---|
| Signalisation verticale | Panoramax montée + descente, OSM | 17 panneaux et balises (A15b, A1d, A14+panonceau, J4 ×2, PR 5, 7, 8, EB20, B13, B14, B1, AB3a, 2 panneaux d'information, 1 de dos) | 7 (triangles génériques du jeu, J4, bornes) | EB20, B13, B14, B1, AB3a, panneaux d'information : aucun maillage du jeu ; texte de 2 panneaux d'information non lu |
| Signalisation horizontale | ortho, Panoramax | axiale T3, rives T2, cédez-le-passage peint des voies latérales | axiale et rives | lignes des voies latérales, îlot rouge du Plan de Masse |
| Retenue | Panoramax, LiDAR | 6 glissières, 32 murs et parapets, 3 têtes de ponceaux, 8 séparateurs en plastique | tout | état (rouille, tags) non rendu |
| Clôtures et accès | Panoramax, OSM | grillages, portails, chaînes DFCI (OSM : 3 chaînes, 6 portails) | rien | pas de maillage ; listés |
| Réseaux aériens | Panoramax, OSM | 26 poteaux (OSM), lignes vues | 14 poteaux en bois (2 photo, 12 OSM) | câbles non tirés, matière (bois ou béton) non vérifiée poteau par poteau |
| Mobilier | Panoramax, OSM | abri de bus, bacs, poteau d'incendie, barrière en tube, bloc blanc | rien | pas de maillage du jeu |
| Bâti | BD TOPO, LiDAR, Panoramax | 35 maisons au bord, 936 au village | tout, en volumes simples | façades et menuiseries |
| Végétation remarquable | LiDAR, Panoramax | oliveraies, cyprès, arbres en surplomb | par le semis | troncs couchés et souches : aucun vu |
| Surface de chaussée | Panoramax, ortho | 2 changements d'enrobé, 13 zones de fissures, 5 zones de traces, 5 bords souillés | traces (décalques) | pièces et fissures (refusées en jeu au Grand Caunet) |
| Bas-côtés | Panoramax | terre rouge, herbe sèche, cunettes | règle de sol (sol « façon jeu ») | cunettes en béton |
| Ouvrages hydrauliques | BD TOPO, LiDAR, Panoramax | 2 ponceaux | têtes en béton | regards et grilles non relevés |
| Éléments de course | recherche web | rien de situé | rien | aucune photo ni vidéo d'édition passée trouvée (deux recherches) |

### Vues produites (rendu de contrôle de l'étape 15, hors jeu) et ce qu'elles montrent

- **Vues** : `figures/phase5/vue_*.png`, 21 au total.
  - Depuis le village : `village_d3_vers_depart`, `village_mairie_vers_nord`.
  - Ligne de départ : `ligne_depart_montee`, `ligne_depart_vers_village`.
  - Approche : `approche_oliveraies_100`, `approche_oliveraies_170`.
  - Plus haut : `premieres_epingles_700`, `mur_parapet_1140`, `glissiere_2330`, `hameau_2840`.
  - Vues rapprochées : `chaussee_epingle_1517`, `glissiere_rapprochee_505`, `carrefour_2622_traces`.
  - Aérienne oblique : `aerien_bas_du_trace_village`.
- **Planches photo réelle / rendu** : `figures/affinage/photo_rendu/*.jpg` (15 vues) ; **planches photo / aperçu des formes avant / après** : `figures/affinage/comparaison/*.jpg` (12).
- **Regardées. Défauts propres au rendu, à ne pas lire comme l'aspect en jeu :**
  - arbres figurants (silhouettes calculées par 15, pas les arbres du jeu) : l'oliveraie y paraît en pins sombres ;
  - enrobé uniformément sombre, alors que l'enrobé réel est gris clair sauf de 1855 à 2700 ; les décalques (traces, terre) n'apparaissent pas dans ce rendu, ils n'existent que dans le paquet Unreal ;
  - accotements peints par la photo aérienne étirée ;
  - au village, le terrain est le lointain grossier (5 à 25 m), en pointes : `village_d3_vers_depart` et surtout `village_mairie_vers_nord` sont à prendre comme un contrôle de l'implantation des volumes, pas comme une vue du village ;
  - les murets bas du PK 95 sortent plus hauts et plus clairs que sur la photo (chaperon de béton gris).
- **Écarts réels vus sur les planches** : à corriger au prochain passage, non corrigés ici :
  - pas d'herbe sèche ni de terre rouge dans le rendu de l'accotement (le sol « façon jeu » les porte, le rendu photo non) ;
  - glissière du PK 503 de même hauteur que sur la photo, mais d'un blanc uniforme.


## 9. Troisième passe (18/11/2026, soir) : murs, murets, clôtures et ce qui borde la route

*Demande de l'utilisateur (mots exacts) : « Le tacer a l'air fidel il lanque les murret cloture et tout quand même ». Puis (transmis par le coordinateur) : « En decore ok mais les zone visible doivent etre vraiment bien faite ».*

**Rien n'a été vu en jeu ni dans Unreal.** « Vérifié » = sortie regardée (planche, rendu de contrôle de l'étape 15, hors jeu).

### Pourquoi le départ était vide

Constat de l'utilisateur sur `figures/affinage/photo_rendu/depart_plan_de_masse.jpg` : la photo montre un haut mur de pierre à droite, un muret de pierre surmonté d'un grillage vert occultant à gauche, le panneau « CEYRESTE », le rendu rien de tout cela. Trois causes, toutes dans le relevé et sa transcription, aucune dans la plage de PK traitée (la chaîne va bien du PK −149 au PK 3746) :

1. **Bornes fausses de 30 à 40 m dans l'approche.** Le grand mur de droite était noté PK −82 à −50 ; il y en a deux : le mur en gradins (−74 à −50, rendu) et, après la voie latérale, un mur de pierre de 1,8 m de −43 à −17 (relu sur l'agrandissement de l'image `f9160d60`, cap D50), **absent** du relevé. Le muret de gauche était noté −65 à −45 (rendu −67 à −36, 0,5 m de haut) : il va de −64 à −27.
2. **Clôtures non modélisées.** Le relevé les mentionnait dans ses descriptions (« grillage brise-vue non rendu », « grillage derrière ») mais la chaîne ne savait poser ni grillage, ni toile, ni portail, ni haie ; le muret seul (0,5 m) se confondait avec le talus.
3. **Panneau d'agglomération non posé** (aucun maillage du jeu ; il est maintenant posé en géométrie générée).

Les deux premières passes lisaient des bandes de 200° à 4 px par degré centrées sur la montée, une image tous les 15 m, en notant surtout les ouvrages. La troisième passe relit **toutes** les images à 6 px par degré, sur 220°, graduées tous les 30° (« G90 » = perpendiculaire à gauche), en tenant un registre par tronçon de 50 m et par côté. 15 images supplémentaires ont été téléchargées dans l'approche (PK −160 à 70) pour y descendre à un pas de 6 à 10 m.

### Méthode

- `scripts/36_releve_clotures.py planches` : 53 planches de 5 bandes (262 images, PK −142 à 3756, aucun écart de plus de 25 m entre deux images ; images prises à plus de 6 m de l'axe écartées), `data/raw/panoramax/planches_clotures/` (non versionné). **Lues par moi, planche par planche** (pas d'outil de sous-agents dans cette session), plus 2 agrandissements (`zoom`) au départ. Relevé brut : `data/reference/releve_clotures_2025.json` (81 éléments en long ou ponctuels d'enceinte, 5 objets ponctuels du départ ; chaque élément cite ses images).
- `lidar` : signatures par mètre et par côté (`data/processed/clotures_lidar.csv` : marche du MNT, objet mince surélevé MNS − MNT).
- `cadastre` : limites parcellaires (PCI Etalab, `cadastre.data.gouv.fr`, commune 13023, téléchargé le 18/11/2026, `data/raw/cadastre/`, non versionné) ; recul de la première limite rencontrée au bord de chaussée, tous les mètres (`data/processed/clotures_cadastre.json`).
- `verser` : un élément vu sur photo est calé **au mètre** si le cadastre (clôtures, murs de propriété) ou la marche du MNT (murs, restanques) le confirme sur au moins 60 % (50 %) de sa longueur, à ±1,5 m (±2,5 m si l'élément a été noté « cadastre ») du recul lu sur la photo ; sinon il garde la position photo (±5 m en long, ±1 m en travers). **Une clôture n'est posée que si une photo la montre.** Sortie : `data/reference/clotures_murets.json` (tracé L93 de chaque élément), registre `data/processed/clotures_registre.json`. Corrections des passes 1-2 (bornes et doublons) dans `ouvrages_parapets.json` et `releve_panoramax_2025.json` (clé `corrections_ouvrages` du relevé brut, rejouable).
- `scripts/37_clotures.py` : géométrie (voir plus bas). `scripts/38_visibilite.py` : ce que voit le pilote. `scripts/39_panneaux_neutres.py` : panneaux de l'export neutre.
- OSM (`barrier=*`, 27 objets dans le couloir) : 3 chaînes de pistes (PK 899, 2104, 3057), un portillon (2095), des portails ; recoupés : la barrière tubulaire du PK 2093-2097 est vue sur photo et posée ; les chaînes ne se voient pas sur les photos (non posées).
- BD TOPO `construction_lineaire` : déjà remplacée par le relevé (passe 1).

### Ce qui a été relevé (troisième passe)

| Type | gauche | droite | total |
|---|---|---|---|
| mur ou muret de pierre sèche (soutènement, restanque, muret) | 23 m | 606 m | 629 m |
| mur maçonné enduit | 8 m | 68 m | 76 m |
| muret + grillage simple | 136 m | 266 m | 402 m |
| muret + grillage occultant (toile verte ou bâche grise) | 70 m | — | 70 m |
| grillage simple seul | 94 m | 333 m | 427 m |
| grillage occultant seul | — | 39 m | 39 m |
| haie taillée | 20 m | 45 m | 65 m |
| portails (8) et piliers (13) | 6 m | 24 m | 30 m |
| barrière tubulaire de piste, bloc de béton, caniveau, boîtes aux lettres | 74 m | 4 m | 78 m + 1 |
| **total en long** | **431 m** | **1 385 m** | **1 815 m** |

Calé au mètre : **878 m sur 1 815 (48 %)** (20 éléments par le cadastre, 10 par le LiDAR) ; le reste à la position photo.

**Avant / après (en long, sans les glissières ni les parois rocheuses ; un muret surmonté d'un grillage compte dans les deux colonnes)** :

| | murs et murets (pierre, béton, enduit) | clôtures (grillages, toiles), haies, portails |
|---|---|---|
| avant (passes 1-2) | G 628 m, D 674 m : **1 302 m** | **0** |
| après | G 698 m, D 1 503 m : **2 201 m** | G 326 m, D 707 m : **1 033 m** |

Les murets des passes 1-2 remplacés par un élément composé ou raccourcis (−278 m) sont décomptés ; s'y ajoutent 78 m de caniveau, barrière de piste et bloc de béton, et une batterie de boîtes aux lettres.

### Registre des tronçons examinés (156 tronçons de 50 m × côté, tous avec au moins une image ; « rien » = examiné, sans mur ni clôture au bord)

| PK | gauche | droite |
|---|---|---|
| -150 à -100 | haie, mur (p1-2), pilier, portail | rien |
| -100 à -50 | mur (p1-2), mur enduit, muret+occultant | mur (p1-2) |
| -50 à 0 | grillage, mur (p1-2), muret+occultant | pierre sèche |
| 0 à 50 | grillage, mur (p1-2), muret+grillage, pilier, portail | muret+grillage, pierre sèche |
| 50 à 100 | muret+grillage | muret+grillage |
| 100 à 150 | muret+grillage | muret+grillage, pilier, portail |
| 150 à 200 | mur (p1-2), muret+grillage | grillage occultant, mur (p1-2), muret+grillage |
| 200 à 250 | mur (p1-2) | grillage, mur (p1-2), mur enduit, talus roch. |
| 250 à 300 | rien | grillage, mur enduit, muret+grillage, talus roch. |
| 300 à 350 | rien | muret+grillage |
| 350 à 400 | rien | grillage, muret+grillage, talus roch. |
| 400 à 450 | rien | grillage, mur (p1-2), talus roch. |
| 450 à 500 | rien | mur (p1-2), pierre sèche, pilier, portail, talus roch. |
| 500 à 550 | glissière | talus roch. |
| 550 à 600 | glissière | pierre sèche, talus roch. |
| 600 à 650 | rien | pierre sèche, talus roch. |
| 650 à 700 | rien | pierre sèche, talus roch. |
| 700 à 750 | mur (p1-2) | talus roch. |
| 750 à 800 | mur (p1-2) | talus roch. |
| 800 à 850 | glissière, mur (p1-2) | talus roch. |
| 850 à 900 | glissière | rien |
| 900 à 950 | glissière, mur (p1-2) | rien |
| 950 à 1000 | mur (p1-2), talus roch. | rien |
| 1000 à 1050 | talus roch. | rien |
| 1050 à 1100 | talus roch. | rien |
| 1100 à 1150 | talus roch. | mur (p1-2) |
| 1150 à 1200 | talus roch. | mur (p1-2) |
| 1200 à 1250 | talus roch. | mur (p1-2) |
| 1250 à 1300 | talus roch. | mur (p1-2) |
| 1300 à 1350 | talus roch. | mur (p1-2) |
| 1350 à 1400 | talus roch. | rien |
| 1400 à 1450 | talus roch. | rien |
| 1450 à 1500 | bloc béton | pierre sèche |
| 1500 à 1550 | rien | pierre sèche, talus roch. |
| 1550 à 1600 | glissière | talus roch. |
| 1600 à 1650 | glissière, mur (p1-2) | talus roch. |
| 1650 à 1700 | mur (p1-2) | talus roch. |
| 1700 à 1750 | talus roch. | talus roch. |
| 1750 à 1800 | talus roch. | rien |
| 1800 à 1850 | rien | rien |
| 1850 à 1900 | talus roch. | rien |
| 1900 à 1950 | talus roch. | rien |
| 1950 à 2000 | talus roch. | rien |
| 2000 à 2050 | pilier, talus roch. | haie |
| 2050 à 2100 | rien | barrière, grillage, pierre sèche, pilier |
| 2100 à 2150 | rien | mur (p1-2), pierre sèche |
| 2150 à 2200 | rien | mur (p1-2), pierre sèche, talus roch. |
| 2200 à 2250 | rien | pierre sèche, talus roch. |
| 2250 à 2300 | rien | grillage, pierre sèche, talus roch. |
| 2300 à 2350 | glissière | grillage, pierre sèche, talus roch. |
| 2350 à 2400 | glissière | grillage, pierre sèche |
| 2400 à 2450 | glissière | pierre sèche |
| 2450 à 2500 | glissière, mur (p1-2) | pierre sèche |
| 2500 à 2550 | mur (p1-2) | pierre sèche, talus roch. |
| 2550 à 2600 | mur (p1-2) | talus roch. |
| 2600 à 2650 | rien | pierre sèche, talus roch. |
| 2650 à 2700 | rien | glissière, pierre sèche |
| 2700 à 2750 | rien | boîtes aux lettres, glissière |
| 2750 à 2800 | rien | rien |
| 2800 à 2850 | rien | pierre sèche, pilier, portail |
| 2850 à 2900 | rien | grillage occultant, mur (p1-2), pierre sèche |
| 2900 à 2950 | glissière, mur (p1-2) | mur (p1-2), talus roch. |
| 2950 à 3000 | glissière | talus roch. |
| 3000 à 3050 | rien | grillage, talus roch. |
| 3050 à 3100 | rien | grillage |
| 3100 à 3150 | rien | grillage, mur (p1-2), mur enduit, portail |
| 3150 à 3200 | rien | grillage, mur (p1-2), pilier, portail |
| 3200 à 3250 | mur (p1-2), pierre sèche | mur (p1-2), mur enduit, muret+grillage |
| 3250 à 3300 | mur (p1-2) | haie, mur enduit, pierre sèche, portail, talus roch. |
| 3300 à 3350 | rien | talus roch. |
| 3350 à 3400 | rien | mur (p1-2), pierre sèche, talus roch. |
| 3400 à 3450 | rien | mur (p1-2), pierre sèche, talus roch. |
| 3450 à 3500 | rien | mur (p1-2), talus roch. |
| 3500 à 3550 | grillage | mur (p1-2), pierre sèche |
| 3550 à 3600 | grillage | mur (p1-2), pierre sèche, portail |
| 3600 à 3650 | grillage, mur (p1-2) | rien |
| 3650 à 3700 | caniveau, mur (p1-2) | rien |
| 3700 à 3750 | caniveau, muret+occultant | rien |

Aucun tronçon sans image. Les 2 tronçons « mur (p1-2) » de gauche entre −50 et 50 sont la bordure de béton basse (passe 1, bornes corrigées −27 à 22).

### Posé dans la carte (`scripts/37_clotures.py`)

- **Formes paramétriques** suivant le terrain (MNT LiDAR 0,5 m), pied enterré de 0,3 m : pierre sèche avec couronnement de pierres plates ; mur enduit avec chaperon ; muret (pierre, béton ou enduit) + poteaux tous les 2,5 m + grillage simple torsion ajouré (texture à transparence) ; idem + toile brise-vue ; grillage seul ; haie taillée ; portail plein ou ajouré ; pilier à chapeau ; barrière tubulaire ; bloc de béton ; boîtes aux lettres ; caniveau. UV en mètres. Un mur de soutènement est posé au **pied** de la montée du terrain (le MNT lisse la marche d'un mur en talus : posé au milieu de la pente, le mur disparaissait dans le terrain, vu sur le rendu du départ) et son dessus dépasse le terrain arrière de 0,15 m.
- **Matières** : pierre `old_stone_wall` et enduit `white_plaster_rough_01` (Poly Haven, CC0, catalogue du skill), teintées d'après les photos ; grillage, toiles, haie, portails : textures calculées. Dans le paquet Unreal : la pierre sèche prend **la pierre du jeu** (`MI_MonBolStoneWallsA`, comme les parapets : `MI_GC_Pierre_seche`), le grillage **la matière du grillage du jeu** (`MI_ChainlinkFenceA1`, masquée : `MI_GC_Grillage`), les enduits la matière de béton du jeu (comme le bâti). Les maillages de clôture du jeu (`SM_ChainlinkFenceA1..11`, `SM_FenceModular*`, portails `SM_FarmGateA`, `SM_FraChaGateA/B`, haie `SM_CypressHedge01`) existent mais leurs dimensions ne sont pas relevées : **géométrie générée** à la place.
- **Collision** : 79 éléments à moins de 15 m de la chaussée (`modele/clotures_collision.glb` : pierre → `PM_WallRock`, béton → `PM_WallConcrete`, clôtures et portails → `PM_WallBasic`, haies → `PM_WallBush`), lue par 09.
- Passes 1-2 : les murs de pierre sèche vus sans chaperon de béton (9 tronçons) ont maintenant un couronnement de pierre (`"couronnement": "pierre"` dans `ouvrages_parapets.json`) ; la pierre de l'aperçu et de l'export neutre est `old_stone_wall` au lieu de la pierre calculée. **Murets du PK 95** (signalés trop hauts et trop clairs) : le muret de 0,6 m à chaperon de béton clair du PK 55-165 est remplacé par un muret de pierre sèche de 0,6 m sans chaperon surmonté de son grillage (vérifié sur `approche_oliveraies_100`).
- **Départ** : EB20 « CEYRESTE » sur portique vert, panneau jaune temporaire, mât de plaques de rue, panneau d'affichage du parking (PK −97) : mât + plaque générés (faces redessinées : texte lu sur les photos, aucun logo).

### Panneaux exacts pour l'export neutre (`scripts/39_panneaux_neutres.py`)

12 panneaux (EB20, B14 50, B13 19 t, A15b + panonceau 4,6 km, A1d + panonceau 3 km, PR 5, J4 ×2, A14 + panonceau jaune « CHAUSSÉE DÉFORMÉE », PR 7, AB3a, PR 8) : `modele/panneaux_neutres.glb` (un maillage par mât, plaque et panonceau, UV 0-1 sur la face), placements dans `data/processed/panneaux_neutres.json`. Faces A15b et A1d : **Wikimedia Commons, auteur Roulex_45, CC BY-SA 3.0** (téléchargées). Les autres : **redessinées simplement** — Wikimedia a répondu « 429 trop de requêtes » au téléchargement. Le paquet ACR garde ses substituts du jeu.

### Ce que voit le pilote (`scripts/38_visibilite.py`)

Œil à 1,1 m, un point tous les 10 m du PK −149 au PK 3746, voie de droite en montée et autre voie en descente (convoi), ±70°. Relief : MNT LiDAR ; végétation et bâti (MNS − MNT) : arrêtent le rayon après 20 m traversés à moins de 4 m du sol. Résultat : `data/processed/visibilite.json`, `figures/affinage/visibilite.png` (regardée).

| | premier plan (< 30 m) | plan moyen (30-150 m) | lointain | jamais vu |
|---|---|---|---|---|
| bâtiments (971 posés) | 30 | 5 | 798 | 138 |
| éléments de clôture (81) | 81 | 0 | 0 | 0 |
| terrain (ha, cellules de 20 m à < 400 m) | 16 | 26 | 40 | 210 |

Traitement selon ce classement : **toits** de tous les bâtiments relus sur le LiDAR (croupes si le faîtage descend aux deux bouts : 3 maisons du bord de route et 64 du village en quatre pans, le reste à deux pans), **clôtures, portails, piliers et haies** des 30 maisons de premier plan posés quand une photo les montre. **Non fait** : façades avec ouvertures (portes, fenêtres, volets), génoises, teintes d'enduit par maison, garages et terrasses : les 30 bâtiments de premier plan restent des volumes à toit juste mais **façades nues** (liste dans `visibilite.json`, niveau `premier_plan`). Correction du terrain « en pointes » du village (lointain 5 à 25 m) et contrôle de la silhouette (clocher) : **non faits**.

## 10. Quatrième passe (19/11/2026) : façades des bâtiments vus de près, village lointain

*Demande de l'utilisateur (mots exacts) : « En decore ok mais les zone visible doivent etre vraiment bien faite ».*

**Rien n'a été vu en jeu ni dans Unreal.** « Vérifié » = sortie regardée (planche photo / rendu de contrôle de l'étape 15, hors jeu). Pas d'outil de sous-agents dans cette session : toutes les images ont été lues par l'agent.

### Méthode (`scripts/40_facades.py`, `scripts/facades.py`)

- `images` : pour chaque bâtiment de premier plan et de plan moyen (`visibilite.json`), score de chaque panorama 2025 (793 référencés) par façade : angle d'incidence, distance, rayons vers 5 points de la façade non arrêtés par le MNS ; 8 images au plus, téléchargées en HD (12 288 × 6 144 ; 74 téléchargées en plus, non versionnées).
- `vues` : vue rectifiée vers le bâtiment avec l'emprise BD TOPO projetée, façades nommées `F0`, `F1`… (côtés de l'emprise, anneau trigonométrique depuis le sommet sud-ouest), graduées tous les mètres (rouge le long, cyan en hauteur depuis le pied = MNT le plus bas du contour). Correction de la convergence des méridiens (1,92°) entre azimut Panoramax et quadrillage Lambert-93 ; caméra à 2,6 m au-dessus de la chaussée la plus proche (le MNT au point GPS tombait parfois sur un mur). `zoom` : vue serrée d'une façade pour y lire les ouvertures ; `profil` : MNS − MNT le long de chaque façade ; `teinte` : couleur médiane d'un rectangle de façade (avec la chaussée de la même image au soleil et à l'ombre comme référence de gris ; correction écartée quand la chaussée sort colorée) ; `ortho` : teinte médiane du toit sur l'ortho 20 cm.
- **Teintes** : l'exposition des panoramas n'est pas calibrée ; on garde le rapport des canaux mesuré et l'on fixe la clarté d'après une classe lue sur la photo (`facades.rgb_releve`). Toits : ortho, saturation relevée de 60 % (voile et compression la désaturent).
- **Relevé** : un fichier par bâtiment, `data/reference/facades/<cleabs>.json` (identifiant BD TOPO stable, images citées par élément, volumes, toit, enduit, ouvertures, éléments, notes). `31_bati.py` le lit et régénère la géométrie ; collision inchangée (façades de `_batiment`).
- **Géométrie** (`facades.Batisseur`) : emprise découpée en volumes (bandes perpendiculaires à une façade, ou « reste ») ; toit deux pans, croupes, appentis ou plat ; débord, sous-face (enduit, tuile, blanc, bois), rives, faîtières ; génoise de 1 à 3 rangs ; au premier plan, baies percées avec tableaux de 18 cm, vitrage sombre, cadre et meneau, appui saillant, encadrement ; volets battants (vantaux plaqués au mur ou fermés dans la baie, plein ou persiennes), volets roulants (tablier à la fraction relevée) ; soubassement ; auvents, terrasses couvertes, cheminées, conduits, coffrets ; abri ouvert (abribus : piédroits, bandeau, banc, intérieur) ; ruine de pierre sèche (murs de 0,5 m, arases irrégulières). Plan moyen : mêmes ouvertures en aplat. Matières par type, UV en mètres (2 m par répétition) ; textures calculées.

### Résultat par bâtiment (dans l'ordre : zone de départ, puis durée de visibilité)

| Bâtiment | PK | Vu | Posé |
|---|---|---|---|
| 487997256 | −106 D | F2, F3 | 2 volumes à croupes (7 m et 4,3 m d'égout ; LiDAR invalide : maison plus récente), enduit blanc, 2 fenêtres d'étage à volets roulants anthracite, 1 baie, conduit inox |
| 257167825 | −108 G | non | toit (ortho) ; cabanon caché derrière le mur et les oliviers |
| 487997246 | −120 D | non | toit (ortho) ; caché par les lauriers-roses |
| 257167737 | 5 D | F11 (haut) | égout 4,6 m, génoise, enduit blanc, auvent de tuiles |
| 257167771 | −149 G | toit, pignon | enduit beige, toit (ortho) ; façades derrière le mur et le portail bleu |
| 257167973, 974 | −149 D | non | toits (ortho) |
| 257167740 | −18 D | F9 | génoise 2 rangs, enduit blanc, baie à 4 persiennes bleu pâle fermées, cheminée |
| 257167865 | −84 D | F3 (pignon) | remise de 2,4 m d'égout (LiDAR pris sur des arbres), enduit de ciment gris, aveugle |
| 257167736, 168051, 167866, 167861 | −4, −11, −84, −61 | non | toits (ortho) |
| 257168011 | −122 G | F0 (pignon) | cabanon, marquise de tuiles, porte derrière le portail |
| 257167862 | −52 G | F0 (haut) | génoise 2 rangs, enduit crème, fenêtre à cadre blanc, 2 souches |
| 334468838 | −53 D | F6 | cube à étage à croupes + corps bas (LiDAR invalide : maison de 2023), enduit saumon mesuré, 2 fenêtres anthracite à volets roulants |
| 257168030 | 33 D | 4 faces | abribus « LE PLAN DE MASSE » : ouvert au sud, appentis de tuiles, bandeau de bois, banc, conteneur à verre et armoire électrique |
| 257172633 | 3293 D | non | caché par la haie de cyprès ; tuile par défaut (ortho couverte) |
| 276329369 | 2854 D | F2 | bâtisse de moellons enduits à pierre vue, égout 5,6 m, volet plein vert fermé, petit châssis blanc, soubassement de pierre |
| 257172615, 616 | 3308, 3312 D | non | toits (ortho) |
| 257172596 | 2061 G | oui | cabane de planches brunes, appentis de tôle ondulée |
| 257172642 | 3181 D | oui | ruine de pierre sèche sans toit (corps de 3,6 m, enclos de 2,1 m) |
| 356341071 | 3131 D | toit | toit (ortho) ; derrière le mur et le portail |
| 257172553, 551, 552 | 2910-2917 D | toit | toits (ortho) ; derrière la haie de lierre |
| 257172627 | 3226 D | F9 (partie) | génoise 2 rangs, enduit blanc, auvent sur poteaux |
| 257172626, 651 | 3224, 3760 | non | toits (ortho, ou défaut) |
| plan moyen : 257167851, 867, 824, 257172617, 628 | | non | toits (ortho, sauf 628 : défaut) |

Total : **12 bâtiments avec façade relevée, 23 cachés**, **10 ouvertures, 6 volets, 9 éléments**. Vus mais **non posés** (position incertaine ou hors du modèle) : fenêtre à barreaux et tags de la cabane du PK 2061 (emprise BD TOPO décalée de 2-3 m), portes de garage du PK 3226 (±1 m), panneau d'affichage et mosaïque de l'abribus, antennes de télévision, coffret et câbles sur le poteau du PK 2854, claustra du PK 5. Génoise peinte du PK −18 rendue par la génoise de tuiles générique. Abords (végétation de jardin, terrasses, piscines) : **non posés** au-delà des clôtures de la passe 3.

### Village lointain

- **Terrain « en pointes » : cause et correction.** Le maillage lointain (13) passe de 5 à 10 m de pas à partir de 400 m, et au-delà de 450 m ajoute 0,9 × MNH (« hauteur de végétation » du LiDAR HD) pour figurer les cimes. Ce MNH est MNS − MNT : **il contient les bâtiments** (médiane 4 m, 9e décile 6,4 m aux centres des bâtiments du village). Chaque sommet tombé sur un toit ou un arbre de jardin montait de 4 à 10 m, d'où les pointes entre et sous les volumes posés sur le MNT. Correction (`13_paysage_lointain.zone_village`) : dans l'emprise bâtie (tous les bâtiments BD TOPO du village, enveloppe à 40 m, fondu sur 40 m), la surface reste au sol. Ni la triangulation ni l'échelle verticale n'étaient en cause. Vérifié : `figures/phase5/vue_village_mairie_vers_nord.png` (relief lisse, volumes du village dégagés), `vue_aerien_bas_du_trace_village.png`. Reste : la photo aérienne des toits est peinte sur le sol du village (texture du lointain).
- **Silhouette** (`40_facades.py silhouette`, `figures/affinage/silhouette/village_depuis_pk-0140.jpg`, `-0050`, `+0020`) : depuis ces trois points réels, regard vers l'église (1,7-1,8 km), la photo montre la route, les murs et la végétation proches ; le village est caché (PK −140, −50) ou réduit à quelques toits bas dans la plaine sous les collines (PK 20) ; **le clocher n'est visible sur aucune des trois photos**. Le rendu montre le même relief d'horizon et, au PK 20, les toits du village au même endroit, un peu plus dégagés (végétation figurante moins dense que la réelle). Au PK 20, une maison du bord (PK −4 à −11) sort plus dégagée sur le rendu que sur la photo, où des oliviers la cachent. Au PK −140, le rendu de contrôle ne montre pas la route (caméra au bord du modèle, PK −149) : à reprendre.
- **Teintes des toits** : 4 teintes mesurées sur l'ortho (`31_bati.teintes_toits_village`, 572 toits sur 936 dans l'ortho, les autres en teinte médiane) au lieu de la tuile rouge orangé uniforme : `tuile_706058`, `a07868`, `b89078`, `c8b098`. Façades du village : enduit beige inchangé (l'ortho ne les montre pas).

### Vérification par l'image

Planches photo réelle / rendu, même position, cap, tangage et champ (sténopé 1 600 × 900 des deux côtés) : `figures/affinage/facades/pk*_<cleabs>_0.jpg` (13 bâtiments vus) et `depart_synthese_4_directions.jpg` (PK 1, montée, droite, descente, gauche). Regardées. Reconnaissables : abribus, maisons des PK −106, −53, −122, 2854, ruine du PK 3181. Moins bien : PK −52 (le mur couvert de vigne vierge est uni dans le rendu), PK −18 et 5 (cachés par les arbres figurants dans le rendu comme dans la réalité), cabane du PK 2061 (tôle rendue claire et lisse). Le rendu de contrôle ne montre que la texture du modèle : dans Unreal, les enduits relevés héritent du béton du jeu (teinte non vérifiée en jeu).

### Paquet et export neutre

Familles inchangées (`batiments`, `village`) ; 78 + 22 maillages ; nouveaux matériaux nommés par teinte (`MI_GC_Enduit_<rrggbb>`, `MI_GC_Tuile_<rrggbb>`…) ou par type (`MI_GC_Volet_persienne_bleu_pale`, `MI_GC_Verre`, `MI_GC_Genoise`…) : noms stables tant que le relevé ne change pas. 16 : `enduit_releve` et `teinte_enduit_du_jeu` (règle des enduits de `matieres_du_jeu.json`). Bâtiments et village du paquet : 3,1 Mo de maillages + 0,8 Mo de textures nouvelles ; `modele/bati_bord.glb` 0,20 → 0,78 Mo (2 718 triangles, 1 628 avant). Export neutre : CONFORME.

## 11. Cinquième passe (19/11/2026) : carrefour du départ, panneaux, poteaux, jardins ; contrôle des maisons

*Demande de l'utilisateur (mots exacts) : « les zones visibles doivent être vraiment bien faites » ; puis, sur les planches de la quatrième passe : « il y a encore des maisons buggées, des trucs pas très bien modélisés, pas très bien intégrés, des textures encore trop répétitives, des maisons un peu plus grandes que la normale peut-être par moment, ou il manque des murets, des éléments devant, des arbres. Ça manque un peu de végétation, de petits éléments, de panneaux, de marquage au sol, de routes abîmées. »*

**Rien n'a été vu en jeu ni dans Unreal.** « Vérifié » = regardé sur une planche photo / rendu de contrôle (étape 15, hors jeu).

### Ce que montrait la planche du départ

`figures/affinage/facades/depart_synthese_4_directions.jpg` (PK 1, montée, droite, descente, gauche) : la photo montre une voie latérale (Voie Romaine) parallèle à la D3 avec son arrêt de bus, séparée par un îlot d'enrobé rouge, un trottoir rouge au pied du mur de pierre, un îlot court dans la bouche de la Voie Romaine, des panneaux, des poteaux et des lignes ; le rendu montrait à la place un talus de terrain et le mur de pierre posé **à 4,5 m du bord, au milieu de la voie latérale** (relevé de la troisième passe : « cadastre non concordant », gardé à la position photo). Cause du talus : le MNT 0,5 m lisse en pente la marche de 4 m du mur (voie 213-216 m, jardins 216-219 m) et la grille de 1 m de 08 l'étale encore.

### Méthode

- Relevé versionné `data/reference/depart_carrefour.json` (repère local, origine L93 915000 / 6239000) : pied du mur (marche du MNT tous les 2 m, 31 points), contours des îlots, de la voie et du parvis (ortho 20 cm), marquage, panneaux, poteaux, lignes, coffrets, potelets, végétation ; chaque objet cite ses images.
- Positions : visées croisées depuis 2 ou 3 panoramas (azimuts des pixels) et « sol des pixels » ; outil `41_carrefour_depart.py sol IMAGE CAP TANGAGE CHAMP u,v …`. Contrôle : `41_carrefour_depart.py controle IMAGE CAP TANGAGE CHAMP` projette tout le relevé sur la vue (contours, mâts, plaques, pied et hauteurs +1/+2/+3 m du mur) : 89d3561a (cap 40 et 108), f72ed2c1, f58e2a31, bfbe2896 regardées ; écarts de 0,2 à 0,5 m sur les contours proches, de 1 à 2 m sur les objets à plus de 20 m. Hauteur du mur : 2,5 m (lignes graduées sur 89d3561a droite).
- Géométrie : `scripts/41_carrefour_depart.py` (dans la chaîne après 37) ; surfaces découpées dans les triangles du terrain de 08 (comme 12), 3 cm au-dessus, plafonnées au niveau de la plateforme au pied du mur ; trottoir, îlots et parvis surélevés de 12-14 cm avec bordure de béton ; marquage peint à 1,2 cm ; texte « BUS » vectorisé (contours de lettres, sans transparence) ; plaques de panneaux en forme (disque, triangle, flèche) sans transparence, dos gris ; fûts et crosses ; câbles en chaînette ; massifs de feuillage bosselés.
- Terrain : `aplanissements.plateformes()` (surface du second degré ajustée au MNT sur la voie, le trottoir et les îlots ; points du talus écartés ; écart au MNT gardé −0,12 à +0,08 m) ; `08_modele_3d.py` retire ses nœuds à moins de 0,6 m du pied du mur et ajoute trois lignes de points (devant, 0,1 m derrière, 0,55 m derrière) : la marche tient dans l'épaisseur du mur. `10_semis_arbres.py` ne sème plus sur la plateforme.
- Mur : `releve_clotures_2025.json` (mur_D_-15, placement `trace_releve`) reprend le pied du relevé ; `36_releve_clotures.py verser` sait maintenant prendre un tracé relevé (`trace_releve`, `trace_l93_releve`), et ses corrections des passes 1-2 ne se répètent plus à chaque relance (statut de `ouvrages_parapets.json` qui s'allongeait).

### Posé (compté, `data/processed/depart_bilan.json`)

| Famille | Posé |
|---|---|
| Surfaces | voie latérale et bouche de la Voie Romaine 312 m² (enrobé neuf) ; trottoir 120 m², îlot long 40 m², îlot court 2,5 m², parvis de l'abribus 51 m² (enrobé rouge, bordures) ; sol de roulage 525 m² (TSD+ dans 09) |
| Marquage | liserés blancs des deux îlots, « BUS », zigzag jaune et tirets jaunes de l'arrêt, cédez-le-passage de la voie latérale et de la Voie Romaine, passage piéton (≈ 19 m² peints) |
| Panneaux (9) | mât de jalonnement (cartouche « D 3 », flèches « SIGNES », « CAUNET », « Circuit du Castellet », petite plaque blanche non lue) ; B1 au bout nord de l'îlot ; B1 + panonceau « SAUF … BUS » à l'entrée ; C13a sur poteau de bois ; AB3a ; C20a ; B21 sur l'îlot court ; B14 « 50 » et B13 « 19 t » face aux descendants (ils remplacent B14_m20 et B13_5 de 39, lus de loin aux PK −20 et 5) |
| Réseaux | 6 poteaux : béton à transformateur (remplace le poteau de bois OSM du PK 35,7), béton à lanterne (abribus), béton à lanterne couvert de lierre (PK −22), bois du mur (porte le C13a), bois de l'entrée, bois à jambe de force (Voie Romaine) ; 5 portées, 71 m de lignes |
| Petits éléments | 2 coffrets encastrés au pied du mur, boîte aux lettres jaune, potelet vert, poteau tordu de l'îlot court |
| Jardins | 82 massifs de haie (hauteur MNS − MNT, 1,8 à 4,2 m derrière le pied, plafonnés à 3,4 m), bougainvillier, laurier-rose de l'abribus, 21 m de muret blanc à grillage au-dessus du mur |
| Autres | EB20 et panneau jaune temporaire remis **en travers** de la route (ils étaient parallèles) ; EB10 « CEYRESTE » au dos de l'EB20 (43f093e4) ; face du panneau jaune redessinée (« CARREFOUR MODIFIÉ », flèches, sens interdit « SAUF BUS », lu sur b0467d52) ; UV des plaques de 37 corrigées (elles montraient une bande retournée de l'image) |

### Panneaux vérifiés du PK −150 au PK 100, dans les deux sens

Balayage de 24 vues (12 en montée, 12 en descente) et zooms ; détail dans `depart_carrefour.json`, clé `verification_panneaux_pk_-150_100`. Tous les panneaux vus sont posés, sauf : plaque jaune à pictogramme au-dessus de l'EB10 et deux plaques d'information dessous (logo et texte non reproduits), petit panneau de stationnement interdit sur le mur à vigne vierge, dos de plaque non lu vers le PK −97. **Aucune balise J5 n'est visible** : le disque blanc vu de dos sur l'îlot est le dos du B1 nord. OSM met un STOP au débouché de la voie latérale (node/4343358548) : la photo montre un cédez-le-passage (AB3a et tirets), c'est la photo qui est retenue. Les A15b et A1d du PK 86 sont fixés sur un poteau de béton (OSM node/13248624887, posé comme poteau de bois : matière non corrigée).

### Vu, non posé

Voir `depart_carrefour.json`, clé `vu_non_pose` : poteaux du PK −140 et lanterne sur poteau de bois du PK ≈ 42 (vus de loin, non positionnés) ; fil du transformateur vers l'ouest (poteau d'arrivée hors images) ; jambes de force du grillage du champ (espacement non relevé) ; texte de la petite plaque du mât et mot du milieu du panonceau (illisibles).

### Vérification par l'image (planche refaite et regardée)

`figures/affinage/facades/depart_synthese_4_directions.jpg` (40_facades.py depart4 compose maintenant la synthèse lui-même) :
- **montée** : îlot rouge et liserés, voie latérale, mât de jalonnement, AB3a, B14 de dos, abribus, poteaux à lanterne : le carrefour se reconnaît ;
- **droite** : trottoir rouge à bordure jusqu'au pied du mur, mur de 2,5 m, coffrets, C13a sur le poteau de bois, potelet, « BUS » et zigzag, muret blanc et haies au-dessus ; **le talus a disparu** ;
- **descente** : B14 « 50 », poteau à lanterne, trottoir, grillage du champ continu jusqu'au loin ;
- **gauche** : le grillage du champ n'entre pas dans le champ du rendu, alors que la photo le montre à ≈ 4,6 m. Le LiDAR met la bordure de béton et le grillage à 0,5 m du bord de la chaussée (marche de 0,6 m vers le champ), soit à ≈ 2,1 m de la position de la caméra : la pose de la caméra (position GPS du panorama) est en cause, pas le grillage, que la vue de descente montre continu. Non corrigé.
- Écarts restants vus : haies des jardins plus sombres et plus régulières que les vraies (massifs simples), bougainvillier en masse magenta ; rouge des surfaces plus vif qu'en photo malgré une teinte éteinte (éclairage du rendu).

Planches de la quatrième passe reprises et regardées : `pk-0052_G_257167862_0.jpg` (le mur à vigne vierge couvre maintenant le bas de la maison comme sur la photo ; nouveau mur `mur_enduit_G_-60` tracé sur l'arête du MNS et l'ombre de l'ortho), `pk+3226_D_257172627_0.jpg` (porte de garage blanche sous l'auvent ; **la maison est bien plus visible dans le rendu que sur la photo : le grand arbre et la haie devant ne sont pas posés**), `pk+2061_G_257172596_0.jpg` (fenêtre à barreaux sur le long pan, près du coin des tags, comme sur la photo). Le rendu du PK −140 (silhouette) reste sans route : la caméra est au bout du modèle (PK −149), la route au-delà est l'approche du village, hors emprise jouable (décision 7).

### Contrôle des maisons de premier plan (`scripts/42_controle_bati.py`, `data/processed/controle_bati.json`)

Mesures sur le maillage posé (`bati_bord.glb`, sommets attribués au bâtiment le plus proche) : faîtage (toit seul) au-dessus du pied, contre le 95e centile du MNS ; égout contre le MNS médian d'une bande intérieure ; emprise des murs contre la BD TOPO ; faces retournées (aucune trouvée). **Correction faite** : sur terrain en pente, la hauteur LiDAR mesurée au-dessus du terrain local et reportée depuis le terrain médian mettait le faîtage jusqu'à 1,6 m au-dessus du MNS ; le faîtage est maintenant plafonné au 90e centile du MNS absolu (`12_carrefours_annexes._batiment`, lu par 31) : 7 maisons du bord et 147 du village abaissées. Maison du PK −52 : pente de toit 0,30 → 0,17 (faîtage +1,7 → +0,1 m sur le LiDAR). Textures des façades désormais tirées d'une graine fixe (`facades.py` utilisait `hash()`, qui change d'un processus à l'autre).

| Bâtiment | PK | Faîtage modèle − LiDAR | Emprise murs / BD TOPO | État |
|---|---|---|---|---|
| 257167771 | −149 G | −0,2 m | 1,26 | hauteur conforme ; emprise : mesure gonflée par les éléments posés devant (à revoir) |
| 257167973 | −149 D | +0,1 m | 1,23 | hauteur conforme ; emprise : idem |
| 257167974 | −149 D | +1,5 m | — | **écart non corrigé** : annexe accolée au 973 (mesure peut-être prise sur le toit voisin) |
| 257168011 | −122 G | −1,0 m | 1,00 | conforme (plus bas que le LiDAR, arbres au-dessus) |
| 487997246 | −120 D | −8,1 m | 1,04 | non vérifiable (lauriers-roses au-dessus du toit) |
| 257167825 | −108 G | −0,1 m | 1,07 | conforme |
| 487997256 | −106 D | (LiDAR invalide) | 1,00 | non vérifiable au LiDAR (maison plus récente) ; hauteurs photo |
| 257167865 | −84 D | (LiDAR sur arbres) | — | non vérifiable au LiDAR ; hauteurs photo |
| 257167866 | −84 D | −0,1 m | — | conforme |
| 257167861 | −61 G | +1,0 m | — | conforme (à la limite) |
| 334468838 | −53 D | (LiDAR invalide) | 1,11 | non vérifiable au LiDAR (maison de 2023) ; hauteurs photo |
| 257167862 | −52 G | +0,1 m | 1,03 | **corrigé** (était +1,7 m) |
| 257167740 | −18 D | −0,9 m | 1,15 | conforme |
| 257168051 | −11 D | +1,2 m | — | **écart non corrigé** (petite annexe ; cause non isolée) |
| 257167736 | −4 D | +0,6 m | — | conforme |
| 257167737 | 5 D | −0,3 m | 1,12 | conforme |
| 257168030 | 33 D | +0,3 m | 1,70 | conforme (emprise : banc, conteneur et armoire comptés) |
| 257172596 | 2061 G | (LiDAR invalide) | 1,00 | non vérifiable au LiDAR (pins) ; hauteurs photo |
| 276329369 | 2854 D | −5,8 m | 1,00 | conforme (pins au-dessus d'un angle) |
| 257172553 | 2910 D | −0,2 m | 0,85 | conforme |
| 257172552 | 2915 D | +0,3 m | 0,79 | conforme |
| 257172551 | 2917 D | −14,4 m | 0,88 | non vérifiable (arbres) |
| 356341071 | 3131 D | 0,0 m | 1,00 | conforme |
| 257172642 | 3181 D | −2,7 m | 1,16 | conforme (ruine ; pins au-dessus) |
| 257172626 | 3224 D | +1,1 m | — | **écart non corrigé** (abri de 6 m² accolé au 627 ; mesure peut-être prise sur le toit voisin) |
| 257172627 | 3226 D | −0,2 m | 1,29 | conforme (emprise : poteaux de l'auvent comptés) |
| 257172633 | 3293 D | −9,3 m | 1,00 | non vérifiable (cyprès sur le toit) |
| 257172615 | 3308 D | +0,7 m | — | conforme |
| 257172616 | 3312 D | 0,0 m | — | conforme |
| 257172651 | 3760 G | −2,2 m | 1,00 | conforme |

« — » : trop peu de faces de mur mesurables. Aucune maison n'est **plus large** que la BD TOPO au-delà de ce qu'expliquent les éléments posés devant (auvent, abri, conteneur). L'assise (pied contre le MNT) n'a pas de résultat sûr : le test automatique compte comme « flottantes » les façades d'étage posées sur un corps bas ; elle n'a été regardée que sur les planches (aucune maison flottante vue au départ ni aux PK −52, 2061, 3226).

### Demandes du retour du 19/11 non traitées dans cette passe

- **Textures répétitives** : seul un décalage d'UV par élément (graine fixe) est fait pour les murs, clôtures et murets de 37 ; la répétition à l'intérieur d'un long mur, des enduits, des tuiles et du sol n'est pas traitée. Dans Unreal, la pierre et les enduits prennent les matériaux du jeu (échelle des textures de 16 inchangée).
- **Végétation proche** : hors du départ, pas de nouvelle végétation de jardin (le grand arbre et la haie du PK 3226 manquent) ; densité des arbres contrôlée par `32_verif_vegetation.py` (32 à 60 arbres pour 100 m à moins de 20 m, couvert LiDAR > 2 m de 51 à 74 % : inchangé).
- **Chaussée** : marquage et usure non repris hors du carrefour du départ (les pièces et fissures relevées en § 8 ne sont toujours pas rendues).

### Chaîne et contrôles

`tout_lancer.py --depuis 8 --sans-telechargement -- --sol photo` (code 0), puis 31, 37, 41, 09, 16 relancés après les corrections. Export Stage IR : **0 erreur**, 532 portes, 27 notes sur 27 dans le bon sens, 3 025,37 m, 7 740 obstacles, 0 retiré sur la chaussée ; sol de la voie latérale et des surfaces rouges en TSD+ (2 062 triangles). Paquet : **0 erreur**, 696 maillages (51 de la famille `depart`, 82 `batiments`, 82 `clotures`), 243 414 instances (−66 : plus de semis sur la plateforme). Export neutre : **CONFORME**, 26 glb, 230,5 Mo (non versionné), `depart.glb` et `depart_collision.glb` inclus.

## 12. Sixième passe (19/11/2026) : chaussée relevée par tronçon de 50 m, textures, végétation, maisons, panneaux du haut

*Demande de l'utilisateur (transmise par le coordinateur, mots exacts) : « il y a encore des maisons buggées, des trucs pas très bien modélisés, pas très bien intégrés, des textures encore trop répétitives, des maisons un peu plus grandes que la normale par moment, il manque des murets, des éléments devant, des arbres. Ça manque de végétation, de petits éléments, de panneaux, de marquage au sol, de routes abîmées. » et « les zones visibles doivent être vraiment bien faites ».*

**Rien n'a été vu en jeu ni dans Unreal.** « Vérifié » = regardé sur une planche (photo / rendu de contrôle de l'étape 15, ou vue graduée de Panoramax). Pas d'outil de sous-agents : toutes les images ont été lues par l'agent.

### Chaussée : relevé par tronçon de 50 m (`scripts/43_chaussee_releve.py`, `data/reference/chaussee_releve_50m.json`)

- **Méthode** : pour chacune des 200 images HD du 08/09/2025 entre le PK 100 et le PK 3775 (2 à 10 par tronçon de 50 m, aucun tronçon sans image), vue sténopé tournée vers la descente (tangage −9°, champ 75°), graduée : PK de l'axe tous les 5 m (étiquette tous les 10 m), bords de chaussée de 07 en pointillé. 23 planches de 9 vues (`data/raw/panoramax/chaussee/planche_<PK>.jpg`, non versionnées), toutes lues. Outils annexes : `zoom` (vue graduée serrée) et `bandes` (bande redressée en plan, 50 m × 11 m, image amont choisie par blocs de 4 m pour éviter le capot ; décalages de 0,5 à 1 m aux coutures, à cause du GPS).
- **Relevé** : 73 tronçons (PK 100 à 3750), chacun avec son enrobé, ses images et ses éléments ; **121 éléments**, chacun avec PK, voie (droite = voie montante, gauche, axe, toute, bords) et images : 34 fissures longitudinales, 30 zones de faïençage, 3 fissures transversales, 3 joints pontés au bitume, 4 pièces d'enrobé (reprises), 2 raccords d'enrobé (PK 1855 et 2700, déjà connus), 15 zones de traces de pneus (dont les longues traces noires des PK 2445-2465, 2625-2665, 3045-3075, 3125-3180, 3210-3230), 20 bandes de terre rouge, 5 d'aiguilles, 3 de gravillons, 2 bords effrités. Contrôle : `43_chaussee_releve.py bilan` (aucun tronçon manquant, toutes les images citées existent ; `data/processed/chaussee_releve_bilan.json`).
- **Erreur évitée** : à la première lecture, des « tirets jaunes » le long de l'axe semblaient un marquage provisoire ; c'étaient les bords de chaussée de 07 dessinés en jaune par l'outil (vérifié sur `zoom_ff83d182`). Rien de jaune n'est posé.
- **Marquage** (`marquage_route.json`) : axiale T3 (3 m / 1,33 m) confirmée (bande redressée du PK 2000-2050 : rapport trait / intervalle ≈ 2 ; orthophoto au PK 1050 : traits de 2,5 m, intervalles de 1,6 m) ; rives T2 (intervalles de 2,8 à 4,2 m mesurés sur l'orthophoto) ; **aucune portion continue de l'axiale vue** sur les 73 tronçons. Ajouts : rive gauche **continue** du PK 3685 au bout (zone d'arrêt, le long du caniveau à grille : e48878e8, 1eeb4efc, 2f96ea55) ; **rectangles blancs peints sur les deux rives au droit des bornes PR 6 (PK 1113, e34f1aff) et PR 8 (PK 3104, 2540de5a)** ; ligne de cédez-le-passage (tirets de 0,5 m) au débouché de la voie latérale du PK 2934-2944 (a0adfc0d, 0e847466 ; ±2 m). **Retirée** : la « zone hachurée du carrefour du Lion d'Or » (PK 3636-3652), reprise du Grand Caunet (ses coordonnées tombent à 2,7 km au nord du PK 3636 de Ceyreste) ; aucune zone hachurée sur les images 3293697d et 11ee1c29.
- **Borne PR 6** trouvée au PK 1113 à gauche (plaquette « D3 6 » lue sur un zoom de e34f1aff), absente des relevés précédents ; posée (mobilier du jeu et export neutre).

### Chaussée : rendu de l'usure (`scripts/44_usure_chaussee.py`, nouvelle étape après 41)

- **Aperçu et export neutre** (`modele/usure_chaussee.glb`, non versionné, régénéré par la chaîne) : bandes minces sur l'enrobé (5 à 9 mm au-dessus du ruban de 11, sous le marquage à 15 mm), une texture calculée par famille, en **transparence progressive** (glTF BLEND : une découpe nette à 0,5 rendait le faïençage en taches noires sur la planche du PK 450), dépliée en mètres dans les deux sens pour le faïençage et les traces (dépliée à la largeur de la voie, la maille était étirée 3,5 fois en travers : barres horizontales sur la première planche), décalage et sens tirés par élément. Nappe de l'**enrobé récent sombre** entre les raccords relevés (PK 1855-2700). Enrobé ancien de 11 éclairci (base 0,36 → 0,44 : il est gris clair sur toutes les photos).
- **Paquet Unreal** : **décalques du jeu** (16, `details_de_chaussee`, partie « 3 ter », tirage à graine propre) : `MI_AsphaltDecalCracks_01/_02` sur le faïençage (un tous les 3,2 m), `MI_AsphaltDecalCracksLong_01` le long des fissures et joints (tous les 7 m) et en travers pour les fissures transversales, `MI_AsphaltTransitionDecal` aux deux raccords, `MI_AsphaltTiresMarksDecal` le long des traces relevées, terre, gravillons et aiguilles du jeu sur les bords relevés. **Gabarits et couleurs de décalque des fissures et du raccord SUPPOSÉS** (l'usage par le studio n'a pas été relevé) : à regarder en jeu. Pièces d'enrobé (« reprise ») **non posées dans le paquet** : aucun décalque de pièce sûr dans le catalogue (seul `MI_AsphaltPatchSquared_Yellow_01`, de nature inconnue). L'enrobé récent du PK 1855-2700 n'a pas d'équivalent dans le paquet (la route du jeu garde son asphalte ; seuls les raccords sont marqués).

### Textures répétitives (`scripts/variation.py`)

- **Teinte par sommet** (glTF `COLOR_0`, multipliée par la texture) : bruit de valeur lisse à deux échelles (de 1 à 18 m selon la matière), calculé sur la position du sommet, pour la pierre, les enduits, le béton, les tuiles, les génoises, les haies et feuillages, l'enrobé et les bordures. Écrit par les écrivains glb de 11 et 37, donc pour 11, 12, 31 (bâti et village), 37, 41, 44, 45. Un long mur de pierre ou une façade change lentement de teinte (jusqu'à −16 % pour la pierre, −7 % pour l'enduit, −13 % pour les tuiles), sans couture, et deux éléments voisins diffèrent. **Aperçu et export neutre seulement** : le paquet Unreal ne lit pas `COLOR_0` (les matières du jeu se servent de la couleur de sommet pour autre chose ; non essayé).
- **Départ** (`41_carrefour_depart.py`) : massifs de haie à bosses lisses (somme de quelques ondes, maillage 20 × 10) au lieu d'un bruit par sommet qui faisait des « dents » régulières ; rayons, hauteurs et pas tirés dans des plages plus larges ; feuillage de haie plus clair (92, 116, 62 → 106, 128, 70) ; bougainvillier moins chargé de fleurs (densité 0,8 % → 0,35 %, magenta adouci) ; enrobé rouge des îlots désaturé (106, 60, 55 → 112, 80, 74).
- **Non fait** : échelle des textures dans le paquet (les murs prennent la pierre et le béton du jeu, échelle de 16 inchangée) ; textures du sol (14) : non retouchées.

### Végétation (`scripts/45_vegetation_bord.py`, `data/reference/vegetation_relevee.json`, nouvelle étape après 44)

- **Herbes** : 11 zones relevées (accotements et pieds de murs : PK 100-350, 1985-2110, 2240-2300, 2830-2850, 3360-3400, 3600-3750), chacune avec ses images ; touffes d'herbe sèche (4 plans croisés, texture ajourée calculée), densité relevée à l'œil, ramenée à 2-3 au m² et 0,2-0,5 m après la planche de la zone d'arrêt (la bande d'herbe y sortait comme une haie de paille) : **4 014 touffes**. Aperçu et export neutre ; dans le paquet, l'herbe reste celle du jeu (`herbes_du_bord` de 16).
- **Massifs** : 3 zones (arbustes devant la maison du PK 3226, buissons du hameau au PK 2838-2870, arbustes derrière le muret du PK 110-200) ; massifs posés là où le MNS − MNT du LiDAR est entre 1,2-1,5 m et 3,2 m dans la bande de recul relevée, jamais sur une emprise bâtie : **16 massifs**. Première version : 244 massifs jusqu'à 7 m, avec les bambous du PK 3236-3300 ; sur la planche `pk3226_maison`, ils sortaient en grandes masses vertes lisses qui cachaient la maison : au-dessus de 3,2 m, une forme bosselée simple ne ressemble plus à un arbuste ; bambous et arbres de jardin laissés au semis (vu, non posé : `vegetation_relevee.json`, clé `vu_non_pose`). Paquet : nouvelle famille **`abords`** (`SM_MonteeCeyresteRoadside_*`, `/Game/Environments/MonteeCeyreste/Roadside/Meshes`), avec les petits éléments.
- **Grand arbre du PK 3226** : zone d'essences relevée (`zones_essences_relevees.json`, PK 3212-3238, bande 16 m : chêne pubescent 75 %, cyprès 25 %) ; le semis y mettait des oliviers et des pins sur les apex LiDAR.
- Densité des arbres : `32_verif_vegetation.py` relancé (voir « Chaîne et contrôles »).

### Maisons (`scripts/42_controle_bati.py` refait)

- **Les trois « écarts non corrigés » de la cinquième passe étaient des erreurs de mesure** : le faîtage d'une annexe accolée était lu sur le débord de toit du voisin (tolérance de 1,8 m autour de l'emprise). Le contrôle lit maintenant la **tuile propre du bâtiment** (teinte relevée, 31) dans l'emprise élargie de 0,45 m, ou à défaut écarte les sommets à moins de 0,45 m d'un autre bâtiment : 257167974 +1,5 → −0,8 m, 257168051 +1,2 → −0,3 m, 257172626 +1,1 → 0,0 m. Aucune géométrie n'avait à changer.
- **Emprises « gonflées » du PK −149** : l'enveloppe convexe des murs d'une maison en L était comparée à l'aire du L ; comparée maintenant à l'enveloppe convexe de l'emprise BD TOPO, et seuls les murs à moins de 0,3 m du contour comptent (les éléments posés devant sont écartés) : 257167771 et 257167973 conformes. Aucune maison n'est plus large que la BD TOPO.
- **Test d'assise remplacé** : tous les 0,5 m du contour, le plus bas des **pieds de mur** (arête basse de chaque triangle de mur, matières de mur seules) à moins de 0,35 m, contre le MNT ; points sous une baie ou une porte écartés (l'ancien test comptait les tableaux de fenêtres et les rives de toit comme des pieds flottants). Résultat : **aucun pied flottant** sur les 30 maisons. Le pied des volumes relevés et des volumes simples est en outre pris sur le MNT tous les 0,4 m du contour (et non aux seuls sommets) et jamais au-dessus du pied du bâtiment entier (`facades.py`, `12_carrefours_annexes.py`).
- Reste : égout de l'annexe 257167974 (PK −149, sous les lianes) à +1,2 m du LiDAR (égout minimal de 2,2 m au-dessus du terrain médian, sur 1,6 m de pente) ; maisons non vérifiables au LiDAR (arbres, maisons récentes) inchangées.

### Panneaux et petits éléments du PK 100 à l'arrivée

- Recoupés : `mobilier_bord_de_route.json`, `39_panneaux_neutres.py`, `osm_croisement.csv` (34) et les 23 planches de la chaussée ; zooms de contrôle sur dcde5896, 3293697d, 6f422c65, 7c7c6c0c, 53a09c49.
- **Posés** : borne PR 6 (PK 1113 G) ; A15b + A1c face aux descendants au PK 3672 G (zone d'arrêt ; A1c = image miroir de l'A1d) ; AB3a du débouché du PK 3198 D (face à la voie latérale) ; 3 bacs à déchets (jaune et marron au PK 1527 D, jaune sur palette au PK 2625 D : forme simple, famille `abords`).
- **Corrigé dans l'export neutre (39)** : toutes les plaques étaient posées parallèles à la route, face tournée vers la chaussée ; les panneaux de police regardent maintenant les usagers (montée, descente ou voie latérale, clé `SENS`), les plaques de PR restent de côté. EB20 retiré de 39 (37 le pose déjà en travers, avec l'EB10 au dos : doublon).
- **Vus, non posés** : dos de deux mâts de jalonnement (PK ≈ 3605 G et 3640 D, faces non visibles depuis la route : texte inconnu) ; poteau d'incendie rouge du PK ≈ 2722 (non retrouvé sur le zoom) ; taches sombres du PK 2020-2030 (nature incertaine) ; poteaux OSM seuls au-delà de ceux de la deuxième passe.

### Grillage du champ à gauche du départ

Vérifié sur l'orthophoto 20 cm (`figures/affinage/sixieme_passe/grillage_depart_ortho.jpg`, tracé posé en magenta, bords de 07 en cyan, positions des panoramas en jaune) : le grillage `grillage_G_-27` suit la limite du champ, à 0,25-0,45 m du bord de la chaussée, comme le LiDAR. Les panoramas sont pris dans la voie de gauche, à 1,5-2 m du bord : la distance de ≈ 4,6 m lue sur la photo de la cinquième passe était une erreur d'estimation de la vue, pas du grillage. **Rien à corriger.**

### Vérification par l'image (planches regardées, `figures/affinage/sixieme_passe/`)

13 planches photo / rendu (même position, cap, tangage et champ ; rendu de contrôle de l'étape 15, arbres figurants) : `pk0450_faiencage`, `pk0893_epingle`, `pk1301_reprise`, `pk1517_epingle`, `pk2061_cabane`, `pk2150_epingle`, `pk2622_traces`, `pk2854_hameau`, `pk2903_hameau`, `pk2938_voie_laterale`, `pk3104_pr8`, `pk3226_maison`, `pk3709_arret` ; plus `grillage_depart_ortho.jpg`. Commande : `python scripts/43_chaussee_releve.py rendus`.
- **Vu et corrigé en cours de passe** : faïençage en taches noires puis en barres étirées (PK 450) → transparence progressive et dépliage en mètres ; traces de pneus en rayures denses sur toute la chaussée (PK 1517) → deux paires de traces fines par élément ; massifs de 7 m en masses vertes lisses (PK 3226) → limités à 3,2 m ; herbe en haie de paille (PK 3709) → densité et hauteur réduites.
- **Ce que montrent les planches finales** : faïençage aux PK 450 et 2903 aux places de la photo (plus contrasté que la photo) ; rectangles blancs du PR 8 et sa plaque (PK 3104) comme sur la photo ; rive continue et herbe le long du caniveau, A15b/A1c visibles (PK 3709) ; traces aux PK 1517 et 2622.
- **Écarts restants vus, non corrigés** : bande sombre continue au bord de l'enrobé du PK 2622 (sans doute le bord du ruban de 08 ; présent sans l'usure) ; mur enduit du PK 3232-3252 à dessus en marches (37) et maison du PK 3226 plus visible que sur la photo ; haie de lierre du PK 2880-2920 en aplat vert sombre (37) ; arbres figurants plus sombres et plus serrés que les vrais.

### Chaîne et contrôles

`tout_lancer.py --depuis 11 --sans-telechargement -- --sol photo` (code 0, 11 → 16 avec 44 et 45), puis 44, 45, 16 et 33 relancés après les corrections vues sur les planches. Export Stage IR : **0 erreur**, 532 portes, 27 notes sur 27 dans le bon sens, 3 025,37 m, 7 856 obstacles, 0 intrusion de plus de 30 cm. Paquet : **0 erreur**, 704 maillages (8 de la nouvelle famille `abords`), 243 415 instances, **475 décalques** dont 96 + 97 de fissures, 113 de fissures longues, 2 de raccord, 45 de traces de pneus, 72 de terre (11 groupes, tous présents au catalogue ; le raccord est dans `AlsaceS4Saverne`). Export neutre : **CONFORME**, 28 glb, 238,6 Mo (non versionné), `usure_chaussee.glb` et `vegetation_bord.glb` inclus. `32_verif_vegetation.py` : 32 à 60,5 arbres pour 100 m à moins de 20 m, couvert LiDAR > 2 m de 51 à 74 % (inchangé). `42_controle_bati.py` : 15 conformes, 12 non vérifiables (arbres ou maisons récentes) ou plus bas que le LiDAR, 1 égout à +1,2 m (annexe sous les lianes du PK −149), 0 pied flottant.
