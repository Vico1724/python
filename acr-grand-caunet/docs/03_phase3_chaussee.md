# Phase 3 : axe précis et bords de la chaussée

*Première version, 10 novembre 2026. Document destiné au directeur de projet.*

## 1. Résultat

La chaussée est maintenant décrite **tous les mètres** entre le départ et l'arrivée : position de l'axe, des deux bords, altitude, largeur et dévers (l'inclinaison latérale de la route). C'est la base du futur modèle 3D.

- L'axe de la carte IGN, qui servait de guide, était décalé de **0,7 m en médiane et jusqu'à 4,4 m** (au PK 830) par rapport à la route réelle.
- Sur les portions dégagées, les bords tombent sur le bord visible de l'asphalte à environ 0,5 m près.
- **Un cinquième du linéaire (20,7 %) n'a pas pu être mesuré** et a été interpolé entre ses voisins. Sous les arbres, la précision peut tomber à 1 ou 2 m.

![Extraits de contrôle](../figures/phase3/planche_extraits.png)

## 2. Méthode

Tous les mètres, un profil de 30 m de large est relevé en travers de la route dans deux sources indépendantes :

1. **Le relevé laser** (sol nu, 0,5 m) : la chaussée est une bande lisse et presque plate ; son bord est l'endroit où le terrain casse (fossé, talus, bourrelet).
2. **La photo aérienne**, en couleurs et en infrarouge (20 cm) : l'asphalte ne contient pas de chlorophylle et se distingue nettement de la végétation. Cette lecture n'est faite que là où rien ne couvre la route, ni arbre ni ombre.

Quand la photo voit le bord, elle fait foi : le relevé laser englobe parfois un accotement plat. Ailleurs, le laser décide seul. Les bords sont ensuite filtrés le long du parcours, et l'axe est le milieu des deux bords.

| Origine du bord | Part du linéaire |
|---|---:|
| Laser seul | 66,1 % |
| Interpolé (ni laser ni photo ne tranchent) | 20,7 % |
| Laser et photo concordants | 8,4 % |
| Photo seule | 4,9 % |

## 3. Chiffres

| | |
|---|---:|
| Longueur départ-arrivée sur le nouvel axe | 6 715 m |
| Largeur médiane | 6,40 m |
| Largeur, 90 % des cas | 5,15 à 8,37 m |
| Dévers, 98 % des cas | entre −9 % et +9 % |
| Décalage avec l'axe IGN : médiane, 95 %, maximum | 0,67 m, 2,19 m, 4,39 m |

**Sur la longueur.** Le nouvel axe mesure 13 m de plus que les 6 702 m officiels (0,2 %). L'axe IGN, fait de segments droits, coupait légèrement les courbes. Les lignes de départ et d'arrivée restant connues à 30 m près, cet écart n'apprend rien de plus pour l'instant.

**Sur le dévers.** Il penche vers l'intérieur des virages et augmente quand le virage se resserre (6,5 à 7 % sous 60 m de rayon). C'est le comportement attendu d'une route, et un bon signe pour la mesure.

![Largeur et décalage](../figures/phase3/largeur_decalage.png)

## 4. Limites

- **La largeur est bruitée.** Elle varie de 4 à 9,5 m alors que la route réelle varie sans doute bien moins : une partie de ces variations vient d'accotements plats comptés dans la chaussée. La largeur médiane de 6,40 m est fiable ; les valeurs locales le sont moins.
- **Sous couvert dense**, rien ne permet de vérifier : la photo ne voit pas la route.
- **Quatre tronçons indécidables**, interpolés sur plus de 20 m : PK 414 à 434, 470 à 508, 4 707 à 4 753 et 4 928 à 4 965. Autour des PK 470 à 510 et 660 à 700, la largeur atteint le plafond de 9,5 m : probablement des refuges ou des surlargeurs revêtues. À confirmer sur vidéo embarquée.
- **Dix autres tronçons interpolés** correspondent à des ponts et à des débouchés de pistes, dont le carrefour du Lion d'Or (PK 3 618 à 3 665), où la forme exacte du virage reste à dessiner.
- **Un ponceau mal placé dans la base IGN** creusait la route de 1,5 m au PK 3 452. Il est comblé automatiquement ; le script signale ce type de creux.
- **Seule la partie chronométrée est traitée.** L'approche avant le départ et la zone jusqu'au point stop restent à faire : le jeu en a besoin.
- Les virages et les notes du copilote n'ont pas encore été recalculés sur ce nouvel axe.

## 5. Fichiers

| Fichier | Contenu |
|---|---|
| `data/processed/chaussee_precise.csv` | Un point par mètre : axe, bord gauche, bord droit (position et altitude), largeur, dévers, origine de la mesure |
| `data/processed/chaussee_precise.geojson` | Les trois lignes, lisibles dans QGIS ou sur geojson.io |
| `data/processed/chaussee_precise_qualite.json` | Chiffres de qualité et liste des tronçons interpolés |
| `figures/phase3/` | Planches de contrôle sur photo aérienne, courbes de largeur et de décalage |
| `scripts/07_chaussee_precise.py` | Le calcul, rejouable en 15 secondes |

## 6. Suite

1. Prolonger la chaussée avant le départ et jusqu'au point stop.
2. Verrouiller les lignes et lever les tronçons douteux sur les vidéos embarquées.
3. Recalculer les virages et produire une première version des notes du copilote.
4. Construire le premier modèle 3D : la route et le terrain du couloir, habillés par la photo aérienne.
