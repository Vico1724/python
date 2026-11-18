---
name: speciale-rallye
description: Fabrique d'un trait une version essayable, dans Assetto Corsa Rally, d'une épreuve spéciale goudronnée réelle en France (route physique + décor Unreal), à partir du roadbook ou de la carte officielle et de vidéos embarquées (course, reconnaissance), en reprenant les valeurs calibrées sur le projet acr-grand-caunet. À utiliser quand le directeur demande « crée-moi la spéciale X du rallye Y », fournit un roadbook, une carte d'ES ou des caméras embarquées, ou veut refaire une ES dans le jeu.
---

# Spéciale de rallye pour Assetto Corsa Rally

> **Brouillon du 17/11/2026, pas encore installé.** Les scripts appelés ici sont ceux de `projets/python/acr-grand-caunet/`, encore propres au Grand Caunet par endroits : avant le premier usage, faire les généralisations de [`references/generalisations.md`](references/generalisations.md) (ou, à défaut, la procédure « copie du projet » du § 2).

Travail en français, phrases complètes, pour le directeur de projet.

## 0. Ce que le skill produit, et ce qu'il ne fait pas

**Produit** : une spéciale jouable en Essais libres, à la place de Hafren South 1/2 (Pays de Galles), avec :
- la route physique au mètre (axe, bords, dévers, ouvrages), en asphalte avec les pneus asphalte, la ligne idéale et une humidité nulle ;
- le chronométrage, les intermédiaires, le point stop, les notes du copilote ;
- le décor cuit par Unreal 5.6.1 : sol aux matières du jeu, herbes, buissons, arbres relevés au LiDAR, relief lointain jusqu'à 30 km, falaises, parois rocheuses, parapets, glissières, poteaux et câbles, panneaux et rubalises du rallye, habillage de chaussée ;
- en option : commissaires et public du jeu, officiels animés du départ et de l'arrivée, parc d'assistance réduit.

**Ne fait pas** : une spéciale sur terre (les réglages sont calibrés pour l'asphalte provençal ; une ES de terre ou de montagne enneigée est un nouveau projet de calibration), une spéciale de plus de 9 km, deux spéciales installées en même temps (une seule remplace Hafren South), un mod partageable en ligne.

**Budget visé** : une session, deux constructions au plus (une complète, une de retouche), **un seul essai en jeu**. Tout ce qui se vérifie hors jeu est vérifié hors jeu.

## 1. Entrées à demander une fois, au début

Poser les questions manquantes en une seule fois (AskUserQuestion), puis ne plus interrompre.

| Entrée | Obligatoire | Forme | Sert à |
|---|---|---|---|
| Nom du rallye, nom et numéro de l'ES, année | oui | texte | identifiant, menus |
| Roadbook ou carte officielle de l'ES | oui | PDF ou image | points CH, départ, intermédiaires, arrivée, stop avec leurs PK |
| Vidéo embarquée de **reconnaissance** | fortement conseillée | mp4, 1080p | décor fixe, bords, parois, ouvrages (fait foi) |
| Vidéo embarquée de **course** | fortement conseillée | mp4 | objets du rallye (panneaux, rubalises, horloge, public), lignes de départ et d'arrivée |
| Saison visée | non (défaut : celle de la vidéo de course) | mois | herbe verte ou sèche, feuillus roussis |
| Options | non | personnages / officiels / parc d'assistance (défaut : officiels oui, personnages oui, parc non) | `4_construire.ps1` |
| Captures Street View | non | le skill peut aller les chercher (§ 4, étape 4) | abords du départ et de l'arrivée |

Écrire ces réponses dans `speciales/<id>/speciale.json` (gabarit : [`references/gabarit_speciale.json`](references/gabarit_speciale.json)). Ce fichier est la seule source des noms, PK et options pour toutes les étapes.

## 2. Préalables (contrôle, pas d'installation sans accord)

1. **Machine** : PC Windows du directeur, jeu en version **25170642** (`pc/scripts/0_controle.ps1`). Si la version a changé : refaire le fichier de correspondance (`3_usmap.ps1`), relire `Z:\acrxs\acr-extrastages\docs\updating-after-a-patch.md`, et prévenir que les valeurs relevées dans le jeu sont à revérifier.
2. **Outils déjà construits** : `Z:\acrxs\bin\{acr-ref,retoc,acr-additive}` avec les retouches `pc/patches/0001` à `0006`, Unreal 5.6.1 et le projet factice `Z:\acrxs\unreal\acr\`. S'ils manquent : `1_prerequis.ps1`, `2_recuperer_acrxs.ps1` (accord du directeur avant toute installation).
3. **Jeu fermé, Steam hors ligne.** Aucune construction pendant que le jeu tourne (la route physique serait sautée).
4. **Mods tiers** : inventorier `Paks` **et** `Paks\~mods` (un registre installé dans `Paks` masque toute table de menus livrée ailleurs).
5. **Couverture LiDAR HD** de la zone (Géoplateforme) : sans elle, le relief proche et les falaises perdent l'essentiel de leur qualité ; le dire au directeur avant de continuer.
6. **Scripts généralisés ?** Si les généralisations ne sont pas faites, copier `acr-grand-caunet` dans `projets/python/acr-<id>/` et remplacer les éléments codés en dur listés dans `references/generalisations.md` § 1 (ne jamais modifier le projet du Grand Caunet lui-même).

## 3. Règles d'économie (à tenir pendant toute la session)

- Les étapes de calcul sont des **scripts** : ne pas réécrire leur logique dans la conversation, ne pas relire leur sortie en entier. Lancer en arrière-plan ce qui dépasse 2 minutes (construction complète : 80 à 90 minutes) et filtrer les journaux par motif (`FAIL`, `Traceback`, bilans), comme le fait `7_tout_refaire.ps1`.
- Les relevés d'images (vidéos, Street View, planches) vont à des **agents sur un modèle moins coûteux**, avec un schéma JSON imposé ([`references/releves_video.md`](references/releves_video.md)) ; le modèle principal ne lit que leurs JSON.
- **Ne jamais inventer une valeur** de matière, de densité ou de réglage physique : prendre celle de [`references/valeurs_calibrees.md`](references/valeurs_calibrees.md) ; à défaut, la lire sur une spéciale goudronnée du jeu (Bollène, Sisteron, Munster) avec `acr-ref export`.
- Tout ce qui se contrôle hors jeu (formes, positions, dépassements, collisions, couverture des matières, relecture du conteneur) est contrôlé **avant** l'essai.
- Une nouveauté risquée (parent de matériau jamais porté par le jeu, nouveau type de maillage) s'essaie d'abord sur 200 m (`--etendue E4`), pas sur la spéciale entière.

## 4. Déroulé complet

Les numéros d'étape de `scripts/tout_lancer.py` sont entre crochets.

### Étape 1 : identification et points officiels
- Lire le roadbook : CH, départ, intermédiaires, arrivée, point stop, avec PK et coordonnées. **Les PK font foi, pas les coordonnées imprimées** (au Grand Caunet, départ imprimé à 82 m de la route).
- Écrire `data/reference/es_<id>_officiel.json` (format de `es_grand_caunet_2026_officiel.json`) et remplir `speciale.json` : routes empruntées (numéros BD TOPO), emprise, intermédiaires retenus pour le chrono (deux, vers le tiers et les deux tiers), longueur.

### Étape 2 : données IGN et tracé [1, 2, 3, 4, 5, 6]
- `python scripts/tout_lancer.py --jusqua 6` (accès à `data.geopf.fr`).
- **Contrôle** : écart-type des PK mesurés aux intermédiaires officiels < 15 m (Grand Caunet : 6,9 m). Au-delà, revoir l'accrochage des points avant toute suite.

### Étape 3 : lignes de départ et d'arrivée
- Sur la vidéo de course : image où le panneau de départ (puis d'arrivée) sort du champ ; `data/reference/lignes_es.json`. Le PK 0 est la ligne de départ réelle.

### Étape 4 : Street View (facultatif mais conseillé)
- Avec le navigateur intégré (skill `built-in-browser`), ouvrir Google Maps en Street View aux coordonnées du départ, de l'arrivée, du point stop et de chaque carrefour de la spéciale ; une capture tous les 10 à 20 m sur 200 m avant le départ et 100 m autour de l'arrivée ; ailleurs, seulement là où un relevé vidéo est douteux.
- Captures gardées hors dépôt (`speciales/<id>/streetview/`, nom = PK et cap), **jamais intégrées au mod** : ce sont des références de forme et de teinte.
- Un agent en tire `data/reference/zone_depart.json` (bâtiments, murs, aires, barrières, parkings, avec position, dimensions, matière et teinte mesurée), au schéma du Grand Caunet.

### Étape 5 : relevé des vidéos (agents)
- Caler la reconnaissance : `python -P scripts/19_calage_video.py <video> --nom reco` depuis un dossier neutre ; contrôle : tous les changements de direction retrouvés, écart d'angle médian < 8°. Corriger le calage sur des repères sûrs (ponts vus au LiDAR, débouchés de pistes IGN) dans `calage_reco_reperes.json`.
- Planches d'images tous les 6 m, relevées par des agents selon `references/releves_video.md` : parapets et ouvrages, glissières, murs, parois rocheuses (genre lité / blocs / éboulis), poteaux, aires et pistes, bords de végétation (haies au ras, bords ouverts), marquage, rubalises et panneaux du rallye (vidéo de course, recalés sur un repère fixe de la reconnaissance).
- Règles : un objet est au PK de l'image où il **sort du champ** par le côté ; le LiDAR l'emporte pour les ponts et ponceaux ; permanent → reconnaissance, posé pour le rallye → course.

### Étape 6 : chaussée au mètre [7, 70]
- `07_chaussee_precise.py` puis `07b_regulariser_chaussee.py` (réglages calibrés tels quels).
- Carrefours complexes : lire le nuage de points LiDAR brut, pas les photos ; corrections dans `chaussee_corrections.json`.
- **Contrôles** : `17_diagnostic_trace.py` (aucune cassure > 5° sur l'axe), à-coups à 90 km/h ≈ 0,08 g moyen et < 0,5 g max ; aucun rayon modifié de plus de 10 % (07b refuse sinon) ; largeurs 5,5 à 7,5 m hors carrefours.

### Étape 7 : modèle, décor et export [8 11 12 10 9 13, puis 11 14 150 16]
- Reprendre **sans les modifier** les valeurs calibrées (`valeurs_calibrees.md`) et `data/reference/matieres_du_jeu.json` (copié du Grand Caunet : il est générique pour la Provence).
- Adapter seulement la palette d'essences si la région change (`regles_arbres.py`, `10_semis_arbres.py`) en choisissant chaque arbre du jeu sur son image d'ensemble (`couleur_texture.py --apercus`), jamais sur son nom.
- **Contrôles hors jeu avant toute construction** :
  - `21_apercu_conducteur.py` et `23_apercu_lointain.py` à dix PK répartis (départ, arrivée, chaque falaise visible, chaque carrefour) ; comparer à la reconnaissance ;
  - aucune paroi en porte-à-faux, aucun arbre dans le bâti ou à moins de 1 m d'un mur, aucun houppier au-dessus de la chaussée sous 4,5 m, aucun objet perché ou enterré de plus de 0,5 m (contrôle de placement) ;
  - export : sol sous toutes les portes, aucun obstacle sur la chaussée, limites de reprise à plus de 15 m de la chaussée.

### Étape 8 : construction complète (arrière-plan, ~90 min)
- `pwsh -File pc/scripts/7_tout_refaire.ps1 -Journal <journal>` : données, route physique (`-Noms -Ciel -Asphalte` et les options de personnages, officiels et parc retenues), relevé du placement, chaîne Unreal (`chaine_decor.ps1`), cuisson, relecture.
- **Critères d'acceptation** : aucune ligne `FAIL` de `stage-verify` ; table relue (Tarmac, TarmacSnow, météo MonteCarlo, longueur, autres lignes identiques au registre) ; `relire_decor.py` « RELECTURE CONFORME » ; décalage route / décor de 0,0 cm. Le code de sortie de l'éditeur Unreal ne compte pas : c'est son rapport JSON qui fait foi.

### Étape 9 : comparaison physique avec une spéciale du jeu (une fois)
- `acr-ref export` de la route physique et de Munster ou Bollène : matière, couleurs physiques, rugosité, ligne idéale (écart à l'axe médian ~0,4 m, SkidIntensity médiane ~0,2), humidité de base 0, ligne de table. Tout écart se corrige avant l'essai.

### Étape 10 : installation et essai unique
- Accord du directeur, jeu fermé : `5_installer.ps1` (et la table asphalte) ; garder la version précédente (`choisir_decor.ps1`).
- Donner au directeur la liste de contrôle de [`references/essai_en_jeu.md`](references/essai_en_jeu.md) et lui demander une vidéo de l'essai entier.

### Étape 11 : après l'essai (si nécessaire)
- Caler la vidéo par la barre de progression (`19b_calage_barre.py`), paires jeu / reconnaissance tous les 40 m (`20_planches_comparees.py`), relevé par agents, corrections regroupées, **une** construction de retouche. Consigner toute valeur nouvellement jugée bonne dans `valeurs_calibrees.md` avec sa date.

## 5. Valeurs calibrées (résumé)

Le détail, avec la raison et le nombre d'essais qu'a coûté chaque valeur, est dans [`references/valeurs_calibrees.md`](references/valeurs_calibrees.md). L'essentiel :

- **Route** : lissage en plan léger dans les virages, fort ailleurs ; altitude à 5 cm du LiDAR puis 3/4 des ondulations de plus de 6 m rendues (écrêtées à 1,5 cm) ; dévers à 2 % du mesuré ; tablier 10 cm sous la chaussée.
- **Physique** : `PM_SurfaceTarmacSmooth` ; ligne idéale à courbure minimale (marge 1,2 m, couloir 1,5 à 3,4 m, SkidIntensity selon le rayon) ; humidité de base 0 ; table Tarmac / TarmacSnow / MonteCarlo dans un conteneur à part ; portiques d'acr-ref enterrés, déclencheurs gardés.
- **Relief lointain** : au sol jusqu'à 450 m avec arbres entiers jusqu'à 650 m et frange jusqu'à 880 m ; LiDAR 0,5 m jusqu'à 600 m, LiDAR 2 m jusqu'à 2 km, RGE ALTI ensuite jusqu'à 30 km ; images en « vue rasante » ; falaises en roche du jeu jusqu'à 2 km.
- **Roche** : posée sur le relief LiDAR, jamais dressée devant un terrain plus bas ; bancs de 18 à 42 cm ; rocaille = sol peint + nos pierres.
- **Sol et herbe** : matériau de terrain de Bollène avec le fond pierreux clair ; herbe verte rase sur 2,2 m d'accotement ; touffes couchées sur la pente.
- **Habillage** : pas de feuilles mortes ; 2,5 paquets de débris par km ; traces de pneus dans les virages serrés.
- **Matières** : `matieres_du_jeu.json` tel quel ; couleur de sommet noire pour la pierre des murs ; marquage en `M_Simple`.
- **À ne jamais employer** : arbre à perruque, feuilles mortes et plantes rampantes du jeu, herbes à `UseRVTBaseColor`, pierres et rochers du jeu, décalque de marquage du jeu sur nos maillages, bande de terre mordant l'enrobé.

## 6. Pièges connus

Liste à relire avant chaque construction : [`references/pieges.md`](references/pieges.md) (hôte gallois, Unreal, cuisson, tables, vidéos, placement).

## 7. Ce qui est propre au Grand Caunet, et les généralisations à faire

Inventaire fichier par fichier et proposition de paramétrage : [`references/generalisations.md`](references/generalisations.md). En résumé :

- **Identité** : `STAGE_ID`, `NOM`, noms de conteneurs `zz_acrxs_grandcaunet_*`, chemins Unreal `/Game/Environments/GrandCaunet`, préfixe `MI_GC_*`, dossier `export/stage_ir/grand_caunet`.
- **Géographie** : emprise `BBOX_LONLAT`, routes `STAGE_ROADS`, origines de grilles Lambert-93 (`GRILLE0`, `LOIN0`, `ORIGINE_LOCALE`), fenêtre de la zone de départ (`ZD_*`), points officiels.
- **PK** : intermédiaires `SPLITS`, parc au PK −47, arrivée au PK 6736 dans un contrôle, PK des essais E3/E4, carrefour du Lion d'Or et constructions de la zone de départ écrits dans `12_carrefours_annexes.py`.
- **Hôte et jeu** : Hafren South (chemins, cellule de décor `1LS8…`, cellules d'officiels `A0I1…` et `0QY7…`, ligne `WelesS4HafrenSouthFullForward`), version 25170642, chemins `Z:\`.
- **Proposé** : un `speciale.json` par spéciale lu par `acr_geo.py` et les `.ps1`, un `hote.json` pour Hafren South, les objets de carrefour et de zone de départ sortis du code vers les données, un `--speciale <dossier>` pour `tout_lancer.py` et `7_tout_refaire.ps1`.
