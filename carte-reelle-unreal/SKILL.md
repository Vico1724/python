---
name: carte-reelle-unreal
description: Recréer fidèlement une zone géographique réelle (route, spéciale de rallye, quartier, site, hangar, ville) sous forme de carte de jeu Unreal Engine, à partir de données ouvertes (IGN Géoplateforme, LiDAR HD, BD ORTHO, BD TOPO, OpenStreetMap, Panoramax, photos, vidéos), puis la livrer comme mod dans un jeu (Assetto Corsa Rally, Bodycam, Arma Reforger, Sparking Zero ou un autre). Utiliser ce skill dès que l'utilisateur veut une carte, une map, un circuit, une spéciale, un terrain ou un décor de jeu tiré d'un lieu réel, veut télécharger relief, orthophoto ou bâtiments d'une zone pour un moteur de jeu, veut importer une heightmap réelle dans Unreal, cherche des assets ou des photos de référence pour un lieu, ou veut savoir comment faire entrer une carte personnalisée dans un jeu, même s'il ne prononce pas les mots « Unreal », « IGN » ou « mod ».
---

# Carte réelle vers jeu Unreal

Ce skill condense deux projets menés jusqu'au jeu : une spéciale de rallye de 6,7 km (Assetto Corsa Rally) et un site avec hangar, carrière et falaises (Bodycam, puis Arma Reforger). Il fournit une chaîne de scripts qui tourne sur n'importe quelle zone, et les règles qui ont évité, ou auraient évité, le plus de travail refait.

La carte se fabrique en trois couches. Garder cette séparation est ce qui permet de changer de zone ou de jeu sans tout refaire :

1. **Paquet neutre** : relief, orthophoto, vecteurs, arbres, photos de rue, lointain. Produit par les scripts, sans Unreal, indépendant du jeu.
2. **Niveau Unreal** : le paquet importé par script dans l'éditeur, habillé avec des assets.
3. **Adaptateur de jeu** : ce que le jeu exige (matériaux et acteurs du jeu, cuisson, paquetage, installation).

## Avant de construire : trois vérifications

Ces trois points ont chacun coûté des jours quand ils ont été sautés.

1. **Le jeu charge-t-il une carte ajoutée aujourd'hui ?** Faire entrer d'abord la carte d'exemple du kit, ou un niveau presque vide, dans la version actuelle du jeu. Une mise à jour (anti-triche, signature des paquets, menu) peut fermer la porte du jour au lendemain. Lire `references/modding_par_jeu.md`, puis la fiche du jeu si elle existe.
2. **Qu'est-ce qui tourne où ?** La collecte et le paquet neutre tournent n'importe où (Python, réseau). L'éditeur Unreal, la cuisson, l'installation et l'essai en jeu n'existent que sur le PC de l'utilisateur. Dire tôt ce qui lui reviendra.
3. **Quel est le critère de réussite ?** Demander la zone exacte (contour, tracé ou adresse), ce qui doit être reconnaissable, et les photos ou vidéos dont l'utilisateur dispose. Noter ses mots exacts dans un fichier de demandes (voir `references/fidelite_au_reel.md`).

Ce skill n'aide jamais à contourner un anti-triche, une signature de paquets ou une protection, et ne modifie pas un jeu pour le multijoueur compétitif en ligne. Si la seule voie d'entrée passe par là, le dire et proposer une autre cible (solo, serveur privé qui l'autorise, autre jeu).

## Étape 1 : le paquet neutre

Écrire un `zone.json` (gabarits : `assets/zone_exemple.json` pour une emprise compacte, `assets/zone_exemple_couloir.json` pour un couloir le long d'un tracé), puis lancer la chaîne :

```bash
pip install -r scripts/requirements.txt
python scripts/tout_lancer.py --zone zone.json --sortie paquet/
python scripts/controle_paquet.py --sortie paquet/
```

Chaque script est relançable seul, garde ses téléchargements en cache et n'imprime que quelques lignes ; le détail est dans les fichiers qu'il écrit. Lire ces fichiers par extraits ciblés, jamais en entier. Formats, arguments, durées et limites : `references/chaine_scripts.md`.

| Script | Produit |
|---|---|
| `01_emprise.py` | emprise en Lambert-93, repère local métrique, `repere.json` |
| `02_relief.py` | MNT, heightmap 16 bits à une taille valide pour un Landscape, échelles à saisir |
| `03_ortho.py` | orthophoto assemblée, plus une version basse résolution |
| `04_vecteurs.py` | routes (largeur), bâtiments (hauteur), végétation, eau, murs : BD TOPO et OSM |
| `05_vegetation.py` | un arbre par arbre réel quand le LiDAR HD couvre la zone, sinon semis |
| `06_photos_rue.py` | liste des images Panoramax de la zone, vignettes sur option |
| `07_lointain.py` | maillage basse résolution du relief autour de la zone |
| `08_paquet_unreal.py` | paquet assemblé, `manifeste.json`, notice d'import |
| `telecharger_assets_cc0.py` | assets libres de `assets/assets_cc0.csv` (Poly Haven, ambientCG), avec crédits |
| `controle_paquet.py` | verdict CONFORME ou NON CONFORME avec les écarts |

Ne pas passer à Unreal tant que le contrôle n'est pas conforme. Hors de France, fournir ses propres rasters (`--mnt`, `--ortho`) ; les sources par pays sont dans `references/sources_geodonnees.md`.

## Étape 2 : relever ce que les données ne disent pas

Le LiDAR et les vecteurs donnent la géométrie. Ce qui rend un lieu reconnaissable (panneaux, murets, glissières, façades, essences, revêtement, enseignes) vient des images. Pour chaque secteur, tenir un tableau « secteur, photos, vue de capture, écart constaté ».

- Sources d'images et d'assets libres, licences, requêtes : `references/photos_et_banques_assets.md`.
- Hiérarchie des sources, relevé depuis photo et vidéo, protocole d'essai : `references/fidelite_au_reel.md`.

Confier la description des images à un petit modèle qui rend un tableau structuré (objet, position, côté, confiance), et ne garder que le tableau.

## Étape 3 : le niveau Unreal

Sur le PC, dans un projet Unreal de la même version de moteur que le jeu cible :

1. Lancer `scripts/unreal/importer_paquet.py` dans l'éditeur (une copie est dans le paquet). Il lit `manifeste.json`, importe les maillages, pose le décor et les arbres en instances d'après une table `type → asset` (`assets/table_assets_exemple.csv`, formes de base par défaut) à remplir avec les assets du jeu ou d'une banque. Il ne crée pas le Landscape, faute d'API Python stable : il écrit la consigne exacte (fichier de heightmap, position, échelles X/Y/Z) à saisir dans l'outil d'import, et pose en attendant le terrain en maillage. Ce script n'a jamais tourné dans Unreal (seul son mode `--essai` a été exécuté) : le lancer d'abord sur une petite zone, vérifier l'échelle Z et l'orientation du nord, et corriger ce que la version du moteur exige.
2. Choisir les assets dans cet ordre : assets du jeu cible (cohérents, légers, déjà chez le joueur), puis assets scannés libres, et seulement en dernier un objet fabriqué en code. Mesurer chaque asset avant de le poser ; son nom ne prouve rien. Noter licence et crédit dès le téléchargement.
3. Garder la construction reproductible : un script reconstruit le niveau depuis les données. Les retouches manuelles de l'utilisateur vivent dans une copie que le script ne réécrit jamais.

Valeurs, tailles de Landscape, World Partition, collisions, végétation, lumière, automatisation : `references/unreal_monde_reel.md`.

## Étape 4 : livrer dans le jeu

Lire la fiche du jeu avant d'écrire la moindre ligne propre au jeu :

| Jeu | Fiche |
|---|---|
| Assetto Corsa Rally | `references/jeu_assetto_corsa_rally.md` |
| Bodycam | `references/jeu_bodycam.md` |
| Arma Reforger (Enfusion, pas Unreal : seul le paquet neutre sert) | `references/jeu_arma_reforger.md` |
| Sparking Zero, autre jeu, jeu inconnu | `references/modding_par_jeu.md` |

Règles communes : cuire avec exactement la version de moteur du jeu ; lire les valeurs (matières, physique des surfaces, météo, densités) sur un niveau existant du jeu plutôt que de les deviner ; sauvegarder les fichiers d'origine et prévoir le retour arrière avant d'installer.

## Étape 5 : contrôler, essayer, corriger

1. Avant chaque essai, lancer les contrôles chiffrés : tirs de rayons contre les collisions fantômes, objets flottants ou enterrés, relief relu, niveau cuit relu. Un contrôle doit porter sur ce que le joueur verra, pas sur la présence d'un fichier.
2. Une version par essai, chaque version gardée et réinstallable.
3. Demander au joueur des captures avec position et direction. Ne rien diagnostiquer sans elles.
4. Regrouper les corrections avant une reconstruction longue. Essayer un nouveau type d'objet sur un tronçon court avant de le généraliser.
5. N'écrire « fait », « installé » ou « vérifié » que pour ce qui a été vu en jeu ou sur capture. Dire le reste tel qu'il est : construit, non essayé.

Avant de commencer une étape, lire la section correspondante de `references/pieges_et_correctifs.md` ; ses quinze règles de tête valent pour toute la chaîne.

## Dépenser peu

Détail dans `references/economie_tokens.md`. L'essentiel :

- Un petit modèle lit, cherche et décrit les images ; un modèle moyen fait le travail courant ; le grand modèle tranche les problèmes durs.
- Les scripts font le travail répétitif et rendent un résumé court. Aucun gros fichier ne passe par le contexte.
- Un seul constructeur lourd à la fois, des sous-agents bornés, un seuil d'arrêt unique fixé par l'utilisateur.
- Tenir un fichier d'état et un fichier de reprise, pour repartir dans une conversation neuve sans relire l'ancienne.

## Assets

`references/catalogue_assets.md` recense les assets des deux projets : ceux qui se retéléchargent par script (CC0), ceux soumis à conditions, et ceux des jeux, cités par nom. Les assets extraits d'un jeu ne se redistribuent pas : le mod les référence par leur chemin, le joueur les possède déjà.
