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
