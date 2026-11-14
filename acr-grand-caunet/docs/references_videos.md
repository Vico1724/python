# Vidéos embarquées de l'ES « Le Grand Caunet »

*Recensement du 10 novembre 2026.*

Les tracés 2025 et 2026 sont identiques (confirmé par le directeur). Les éditions antérieures empruntent les mêmes routes, avec des lignes de départ ou d'arrivée placées un peu différemment : elles servent pour la route et le décor, pas pour les lignes.

**Trois vidéos ont été fournies par le directeur le 10/11/2026 et analysées image par image** : les n° 1, 2 et 5. Les autres n'ont pas été visionnées (YouTube refuse la lecture depuis le serveur du projet) ; pour elles, le caractère d'embarquée complète reste déduit du titre et de la durée.

| N° | Année | Vidéo | Chaîne | Durée | Équipage, voiture, ES | Remarque |
|---|---|---|---|---|---|---|
| 1 | 2025 | [Rallye Sainte Baume 2025 - Grand Caunet - Clio RALLY5](https://www.youtube.com/watch?v=T2S-saD3Ai8) | Petroni Racing Team | 4:22 | Petroni / Brunie, Clio Rally5, ES 1 ou 4 | Meilleure candidate pour les lignes 2025 |
| 2 | 2025 | [Rallye de St Baume 2025 - VMRS - ES1 - Le Grand Caunet](https://www.youtube.com/watch?v=HIdtgQkVgi8) | Les Charrettes | 5:41 | Régularité (VMRS), ES 1 | Rythme lent : pratique pour relever le décor |
| 3 | 2025 | [Rallye de St Baume 2025 - VMRS - ES4 - Le Grand Caunet](https://www.youtube.com/watch?v=sAEJzMoTtK0) | Les Charrettes | 5:56 | Régularité (VMRS), ES 4 | Second passage du même équipage |
| 4 | 2024 | [Rallye de St Baume 2024 - VMRS - ES2 - Le Grand Caunet](https://www.youtube.com/watch?v=KbXOe1jGCBU) | Les Charrettes | 5:42 | Régularité (VMRS), ES 2 | |
| 5 | 2023 | [ONBOARD M3 E30 - Tom Pieri, ES5 LE GRAND CAUNET](https://www.youtube.com/watch?v=PpoBLygRGFs) | Tom Pieri | 3:50 | Tom Pieri, BMW M3 E30, ES 5 | Embarquée confirmée par la description ; version 6,89 km ; à vitesse de course |
| 6 | 2022 | [FIA Motorsport Games 22 / ES12 / Le Grand Caunet](https://www.youtube.com/watch?v=p2by7e1AiDQ) | Tom Rensonnet | 4:03 | Rensonnet / Dumont, ES 12 | Version 6,89 km |
| 7 | 2022 | [LE GRAND CAUNET: RallyCircuit 2022 ES4/7 R5 GT Turbo](https://www.youtube.com/watch?v=350aIR3Xk4I) | Papyto Racing | 5:13 | R5 GT Turbo, ES 4 et 7 | Peut contenir deux passages partiels |
| 8 | 2020 | [ES7 Le Grand Caunet 2020](https://www.youtube.com/watch?v=LGz8pRZWl3o) | Show Racing | 4:55 | Pilote inconnu, ES 7 | Sans description ; embarquée non confirmée |

En secours, plus anciennes : [2009, 205 Maxi, chaîne ASA Marseille](https://www.youtube.com/watch?v=ZXLXX9uZDKc) ; [2010, 206 XS](https://www.youtube.com/watch?v=Es1qtt7bgA0) ; [2014](https://www.youtube.com/watch?v=XC1GeN1vfxE).

## Ce que montrent les trois vidéos reçues

| Vidéo | Constat |
|---|---|
| N° 1 (2025, Clio Rally5) | **Tournée de nuit** (second passage, ES 4). Inutilisable pour le décor. |
| N° 2 (2025, régularité, ES 1) | De jour, à allure modérée : **la référence du projet** pour les lignes et le décor. |
| N° 5 (2023, BMW M3) | Version de 6,89 km, pas encore analysée en détail. |

### Ligne d'arrivée : confirmée

Sur la vidéo n° 2, on passe un petit pont à parapets de béton et un croisement de pistes (voiture et commissaires à gauche), puis un panneau bleu, un panneau jaune d'annonce, une courbe à gauche, une courbe à droite, et enfin **le panneau rouge d'arrivée et la cellule de chronométrage à la sortie de la courbe à droite, au début de la ligne droite**. C'est, à une quinzaine de mètres près, la position que donnaient les distances officielles ; les coordonnées imprimées sur la carte de l'organisateur étaient 31 m trop loin.

### Ligne de départ : fixée 20 m avant la position calculée

Sur la vidéo n° 2, la cellule de départ se trouve à hauteur de véhicules de secours garés sur la gauche, juste avant une courbe à gauche et une entrée de piste barrée sur la droite. **Le directeur la place à la graduation −20** de l'image `figures/phase3/lignes_depart_ortho.jpg` (graduations de l'ancien repère). Ma propre lecture hésitait entre −75 et −40, faute de savoir laquelle des deux entrées de piste apparaît à l'image.

La décision est enregistrée dans `data/reference/lignes_es.json` et appliquée à toute la chaîne : **le PK 0 du projet est désormais cette ligne, et l'arrivée est au PK 6 722** sur l'axe IGN (6 736 m sur l'axe précis de la chaussée).

Ce que cela implique : entre les deux lignes, la route mesure 20 à 34 m de plus que les 6 702 m officiels, soit 0,3 à 0,5 %. C'est de l'ordre de l'écart entre une distance relevée au compteur et une distance mesurée sur carte. Les deux lignes restent des repères déplaçables dans le modèle.

### Décor relevé sur la vidéo n° 2

- Chaussée à deux voies, **ligne axiale discontinue et lignes de rive** blanches, usées par endroits.
- **Parapets de pierre maçonnée** sur plusieurs ponts de la D3D ; **parapets de béton** bas sur les ponceaux de la D1.
- Talus rocheux taillés côté amont, pins et chênes en bord immédiat de route sur la D3D ; paysage plus ouvert, garrigue et lignes électriques sur poteaux bois le long de la D1.
- Balises de virage à chevrons, quelques panneaux routiers, peu de glissières.
