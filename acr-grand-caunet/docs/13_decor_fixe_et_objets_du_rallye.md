# Décor fixe affiné et objets du rallye remis

*12 novembre 2026, au soir. Document destiné au directeur de projet et à la session qui reprendra le travail.*

**Consigne du directeur.** Les vidéos de course sont le rendu de référence. La vidéo des reconnaissances est un complément : elle sert à corriger les bordures de route et à mieux placer le décor fixe (arbres, poteaux, rochers, aspect de la route). Les objets dus à la spéciale elle-même (rubalises, panneaux de spéciale) doivent rester présents. Continuer le décor, barres rocheuses comprises.

## 1. La règle appliquée

| L'objet est… | La vidéo qui fait foi |
|---|---|
| permanent (mur, rocher, poteau, panneau routier, marquage, revêtement) | la reconnaissance, plus lisible |
| posé pour le rallye (rubalise, panneau de spéciale, horloge) | la course |
| différent d'une vidéo à l'autre | la course |

Un cas de la troisième ligne : le parapet du km 1,55. La reconnaissance y montre une brèche de 6 m fermée par des séparateurs plastique ; sur la vidéo de course, le parapet est intact. Il est donc rendu intact, de bout en bout.

## 2. Les objets du rallye

La vidéo de course a été relevée à nouveau, image par image, et chaque objet a été replacé d'après un repère fixe dont la position est connue par la reconnaissance (bout de glissière, pont, poteau, débouché de piste). L'ancien relevé était décalé de 52 m au pire.

| Objet | Nombre | Rendu par |
|---|---|---|
| Panneaux bleus « point radio » | 9 | le panneau du jeu, sur chevalet |
| Panneaux jaunes d'annonce de point radio | 8 | le panneau du jeu : sur mât quand il est cloué sur un tronc ou un poteau, sur chevalet quand il est posé bas |
| Panneaux « public interdit » | 10 | le panneau du jeu, sur piquet |
| Horloge de départ, panneau de fin de zone, annonce d'arrivée, arrivée | 4 | les objets du jeu |
| Cône | 1 | le cône du jeu |
| Rubalises | 16 tronçons, 286 m | un ruban rouge et blanc à nous, tendu entre des piquets |

Les rubalises sont aux endroits vus : départ (piste GC 107), débouchés de pistes des km 1,50 ; 1,87 ; 2,65 ; 2,99 ; 5,04, aire de Fontblanche (km 3,37 à 3,41), carrefour du Lion d'Or des deux côtés de la route suivie, talus du km 4,96, km 5,01 à 5,03, propriété du km 5,47, aire avant le pont du km 5,5, talus du km 5,64.

**Ce qui n'a pas d'équivalent et n'est pas rendu** : les chevalets « ATTENTION CELLULE » et les cellules de chronométrage, le fléchage jaune avant le Lion d'Or, le filet orange et la banderole à chevrons du Lion d'Or (la fermeture de la branche de droite y reste en rubalise), le public, les commissaires et leurs véhicules.

**À savoir.**
- Les rubalises réelles sont nouées à des arbres. Nos arbres ne sont pas à la place des vrais : chaque point d'attache reçoit donc un mince piquet de bois, pour que le ruban ne flotte pas en l'air.
- Les rubalises et les panneaux n'ont pas de collision : la voiture les traverse.
- L'ancien « panneau de secours » du km 3,08 était une annonce de point radio (km 3,09). L'ancien « panneau jaune » de l'épingle du km 2,2 est un panneau de chantier, non rendu.

## 3. Le décor fixe

| Sujet | Ce qui est fait |
|---|---|
| Barres rocheuses du massif | Là où le relief de l'IGN est très raide (plus de 40°), l'image du relief lointain prend une teinte de calcaire clair, avec des bancs horizontaux. 215 images sur 290 sont concernées. Les bandes tombent exactement sur les lignes de falaise de la photo aérienne. |
| Rochers au bord de la chaussée | 99 blocs du jeu sur 20 tronçons relevés, de 20 cm à 1,5 m de haut. 88 ont une collision. Un bloc ne mord jamais sur la chaussée. |
| Panneaux routiers | 9 triangles de danger du jeu (dont 3 vus de dos, pour l'autre sens), 3 balises de virage à chevrons, 1 plaque kilométrique. |
| Lisses en bois, barrière de piste | 5 tronçons : fond de l'aire du km 2,65, aire de Fontblanche, clôture du km 5,33, barrières des pistes des km 5,05 et 5,67. |
| Marquage au sol | Rives continues du km 6,52 à l'arrivée et à l'intérieur de l'épingle du km 4 ; rives rétablies aux ponts de pierre des km 4,3 à 4,5 ; axe continu dès le km 3,54. |
| Aspect de la chaussée | 30 pièces d'enrobé plus sombres et 31 fissures pontées au bitume, aux endroits et dans la voie relevés. Posées en bandes minces sous les lignes blanches. |

**À savoir.**
- **Falaises** : seule la couleur change, pas la forme du relief. Le maillage lointain est grossier (un point tous les 35 m environ) : une falaise y est une pente très raide, pas une paroi verticale.
- **Rochers** : leur nombre, leur taille et leur côté viennent du relevé ; la forme de chaque bloc est celle des rochers du jeu, et sa teinte peut différer du calcaire blanc local.
- **Chevrons des balises** : le jeu n'a qu'un dessin ; je n'ai pas pu vérifier de quel côté il pointe.
- **Triangles** : le jeu n'a pas « succession de virages, le premier à droite » ni « affaissement » ; ils sont rendus par le triangle de danger ordinaire. Du mât à deux triangles du km 3,75, seul « chaussée glissante » est rendu.
- **Aspect de la chaussée** : la position et la voie sont relevées ; la taille exacte de chaque pièce et le tracé de chaque fissure sont inventés. Le faïençage est rendu par deux ou trois fissures voisines. Aucun effet sur la physique.
- **Calage automatique de la vidéo de course** : essayé, il échoue (caméra grand angle, tableau de bord dans l'image). Le relevé à l'œil recalé sur les repères fixes le remplace.

## 4. Où c'est décrit

- Le relevé de la vidéo de course : `data/reference/releve_course/partie_1.json` et `partie_2.json` (122 observations, avec le repère fixe utilisé pour chacune).
- Les objets posés : `data/reference/mobilier_bord_de_route.json` (rubriques `objets`, `rochers`, `lisses`, `rubalises` ; chaque entrée dit si elle est permanente ou du rallye).
- L'aspect de la chaussée : `data/reference/aspect_chaussee.json`. Le marquage : `data/reference/marquage_route.json`.
- Le code : `scripts/mobilier.py`, `scripts/11_route_ouvrages.py` (aspect de la chaussée), `scripts/16_paquet_unreal.py` (falaises avec `--falaises 0` pour les retirer, rubalises, lisses).
- La version d'avant est gardée sur le PC sous `sol_jeu_releve_reco`, avec sa route physique.

**Rien de ceci n'a encore été vu en jeu.**
