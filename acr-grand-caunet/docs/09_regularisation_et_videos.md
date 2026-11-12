# Régularisation du tracé et comparaison aux vidéos embarquées

*12 novembre 2026. Document destiné au directeur de projet et à la session qui reprendra le travail.*

**Demande du directeur.** Retirer les petites irrégularités du tracé qui viennent des données (IGN, relevé laser), sans simplifier ni dénaturer la route réelle ; croiser les sources avant toute modification ; en cas de doute, garder l'existant.

## 1. Ce qui a été trouvé

Mesuré par `scripts/17_diagnostic_trace.py` sur `data/processed/chaussee_precise.csv`, un point par mètre :

| | Axe | Bord gauche | Bord droit |
|---|---|---|---|
| Bruit de cap (écart-type) | 0,72° | 1,24° | 1,18° |
| Cassures de plus de 5° (hors sections dessinées à la main) | 14 | 110 | 85 |
| Plus forte cassure | 12,5° | 23,8° | 17,7° |

- **Les cassures sont des coutures, pas des formes de la route.** Elles se trouvent aux limites des sections dont la largeur avait été corrigée d'après les vidéos (`docs/08_releve_video.md`). La correction y commençait et s'y arrêtait d'un mètre au suivant, ce qui décrochait le bord, et l'axe avec lui puisqu'il passe au milieu. Douze endroits : PK 736, 1 568, 1 646, 1 927, 1 979, 2 454 à 2 462, 2 775 à 2 787, 3 105 à 3 107, 3 974, 4 037, 5 632 à 5 635, 6 099.
- **Les sections dessinées à la main** (approche, carrefour du Lion d'Or) ont aussi des cassures. Elles sont voulues : elles ne sont pas touchées.
- **Le reste est du bruit de mesure** : le cap oscille en permanence d'un degré environ, deux fois plus sur les bords que sur l'axe. Ce sont les bords qui dessinent la chaussée et le marquage, donc c'est ce bruit-là qui se voyait.

## 2. Ce qui a été fait

`scripts/07b_regulariser_chaussee.py`, étape 70 de `scripts/tout_lancer.py`, juste après le calcul de la chaussée. Le fichier d'origine est gardé dans `data/processed/chaussee_precise_brut.csv`.

1. **L'axe** est lissé en pénalisant la variation de courbure, pas la courbure : une droite ou un arc de cercle traversent le lissage presque inchangés, les zigzags sont retirés. Le réglage est volontairement léger (longueurs d'onde de moins de 9 m).
2. **Autour des douze coutures seulement**, le raccord est étalé sur une quinzaine de mètres.
3. **Les demi-largeurs** gauche et droite sont lissées séparément : un élargissement réel reste, un saut d'un mètre au suivant devient progressif.
4. **Chaque point a une tolérance de déplacement** selon la fiabilité de sa mesure : 20 cm si le laser et l'image concordent, 25 cm pour le laser seul, 40 cm pour l'image seule, 50 cm pour les valeurs interpolées ou tirées de la vidéo, zéro pour le dessin à la main.
5. **Les altitudes** suivent le profil en travers mesuré.

**Le script refuse d'écrire si un contrôle échoue.** Il l'a fait deux fois pendant la mise au point : un premier réglage aplatissait des virages (rayons triplés par endroits), un deuxième agrandissait les rayons de 2,5 % en médiane. Le réglage retenu est le plus léger des trois essayés.

## 3. Résultat

| | Avant | Après |
|---|---|---|
| Cassures de plus de 5° sur l'axe | 14 | 0 |
| Cassures de plus de 5° sur le bord gauche / droit | 110 / 85 | 0 / 1 |
| Bruit de cap de l'axe | 0,72° | 0,5° environ |
| Plus grand saut de largeur d'un mètre au suivant | 0,41 m | 0,25 m |
| Longueur de l'ES | 6 732,27 m | 6 731,56 m |

- **Déplacement de l'axe** : 1 à 2 cm en moyenne, 26 cm au plus (aux coutures).
- **Virages** : sur 79 virages contrôlés, le rayon du cœur du virage change de 1,0 % en médiane et de 6,8 % au plus. Douze autres virages touchent une couture : leur rayon d'origine n'avait pas de sens, ils sont listés à part.
- **Enchaînement** : tous les virages nets (moins de 80 m de rayon) se retrouvent, au même endroit et dans le même sens.

Le détail, virage par virage, est dans `data/processed/regularisation_chaussee.json`.

## 4. Comparaison aux vidéos embarquées

`scripts/18_comparaison_video.py` mesure, dans chaque vidéo, de combien le paysage glisse d'une image à la suivante : c'est la rotation de la voiture. La suite des changements de direction vus à l'image est alignée sur celle du tracé, sans supposer la vitesse.

| Vidéo | Changements de direction vus | Appariés aux 52 du tracé | Écart d'angle médian |
|---|---|---|---|
| M3 E30, 2023 | 44 | 42 | 9,8° |
| VMRS, 2025 | 45 | 44 | 21,4° |
| Clio Rally5, 2025 | 57 | 52 | 25,2° |

- **Les 52 changements de direction du tracé se retrouvent tous dans au moins une vidéo**, dans le même ordre et le même sens.
- **Aucune vidéo ne montre un virage à l'envers**, et aucun virage du tracé n'est contredit par toutes les vidéos à la fois.
- **La mesure d'angle n'est pas assez précise pour corriger un rayon** : une dizaine de degrés sur la meilleure vidéo, davantage sur les deux autres. Une glissade ou un contre-braquage font tourner la caméra sans que la route tourne, et la vitesse n'est pas connue.

Cette comparaison confirme l'enchaînement et le sens des virages, comme l'avait fait le relevé image par image du 11 novembre. Elle ne donne aucune raison de modifier un virage, et aucun ne l'a été d'après elle. Le détail est dans `data/processed/comparaison_video.json`.

## 5. Ce qui reste incertain

- **Trois tronçons n'ont jamais pu être mesurés** et restent interpolés : PK 451 à 473, 4 097 à 4 117, 6 450 à 6 470. La régularisation ne les améliore pas : elle n'invente pas de mesure.
- **Le rayon des épingles** repose sur le relevé laser seul. Aucune autre source ne permet de le vérifier à mieux qu'un ou deux mètres.
- **La largeur** reste la donnée la moins sûre du tracé.
- **Rien de cela n'a encore été vu en jeu** au moment où ce document est écrit.

## 6. Ce qui a changé en aval

Tout ce qui dépend de la chaussée a été recalculé : modèle 3D, route et ouvrages, export physique, paquet Unreal, échantillon. Deux ajouts ont été faits dans le même passage :

- **Dégagement des arbres** (`scripts/16_paquet_unreal.py`) : un arbre est retiré si son tronc est à moins de 2,5 m du bord de chaussée, ou à moins d'un quart du diamètre de son houppier ; un buisson, à moins de son demi-diamètre plus 0,5 m. En jeu, des branches barraient la route au km 0,1.
- **Collision des troncs** (`scripts/09_export_stage_ir.py`) : 1 023 arbres situés entre ce dégagement et 6 m du bord reçoivent un cylindre de 3 m de haut dans la physique, avec la surface « tronc d'arbre » du jeu. Avant, la voiture traversait les arbres.
