# Relevé vidéo de l'ES « Le Grand Caunet »

*Compte rendu du 11 novembre 2026. Le détail chiffré se trouve dans `data/reference/releve_video.json`.*

## Ce qui a été fait

J'ai revu en entier les trois vidéos embarquées fournies. La principale est celle de la voiture de régularité de 2025 (v2), tournée de jour et à allure modérée. J'ai aussi utilisé la BMW M3 de 2023 (v5), filmée à vitesse de course, et la Clio de nuit (v1). Aucune image n'a été copiée dans le dépôt.

Pour savoir où se trouve la voiture à chaque seconde, j'ai mesuré dans l'image combien la caméra tourne, j'ai comparé ces rotations aux virages de notre tracé, puis j'ai calé le résultat sur 19 repères reconnus à l'image : départ, arrivée, ponts, croisements de pistes, épingles et Lion d'Or. Pour le vérifier, j'ai retiré chaque repère à tour de rôle et je l'ai fait prédire par les autres : l'écart moyen est de 13 m, au plus 25 m. Trois ponceaux et un parapet non utilisés pour le calage tombent à moins de 16 m de leur place dans le relevé laser. Un objet de la vidéo se localise donc à une dizaine de mètres près, contre 150 m auparavant, sauf sur le premier kilomètre et demi, où la précision est d'une vingtaine de mètres.

Pour les largeurs, j'ai étalonné une ligne fixe de l'image, environ 4 m devant la voiture, sur 37 lignes droites de largeur connue par le laser. La mesure est approximative, à environ 15 % près, et ne vaut pas dans les virages serrés. Elle suffit pour trancher entre 5 m et 9 m, pas entre 6,3 m et 6,6 m.

## Ce qui confirme la reconstitution

Le tracé est le bon : les 55 virages du brouillon se retrouvent à l'image dans l'ordre, aucun dans le mauvais sens, et les ponts sont au bon endroit à quelques mètres près. La route a partout deux voies, axiale discontinue et rives, sauf sur l'approche du pont 4360, sans axiale. Le rétrécissement relevé au laser avant la première épingle (PK 2092 à 2178) est réel : la route y fait environ 5 m, entre une glissière, un parapet et le rocher. Les sections larges de l'épingle de la D1 et de l'entrée du pont 2777 sont également plausibles.

## Ce qui la contredit, et de combien

Les erreurs de largeur suivent deux schémas, qui expliquent la plupart des cas.

Les **largeurs trop grandes, de 8,3 à 9,5 m,** apparaissent presque toujours là où un accotement plat en terre ou en herbe longe l'enrobé. La reconstitution l'a compté comme chaussée. En réalité, la route y mesure de 6 à 7 m et l'excédent se trouve presque toujours du côté droit. Par exemple, aux PK 4942-4983 et 2453-2464, il faut retirer 2,3 à 2,7 m.

Les **largeurs trop petites, de 4,3 à 5 m,** apparaissent surtout sur les ponts et les ponceaux dont le bord a été interpolé. Au pont 2777, la reconstitution donne 4,7 m alors que l'image montre deux voies complètes entre les parapets, soit environ 6,8 m. Les ponceaux des PK 4572, 4672 et 6110 sont dans le même cas : il faut compter 5,8 à 6,3 m au lieu de 4,3 m.

Au départ, la largeur de 8 à 9,5 m s'explique par le dégagement où stationnent les véhicules de secours, sur la gauche. La route elle-même mesure environ 7 m à la ligne, puis 6,5 m.

Deux parapets sont mal placés dans `ouvrages_parapets.json`. Le long parapet à dés blancs attribué au pont 1484 se trouve en réalité 50 m plus loin, le long du virage à gauche (PK 1538 à 1590), et il n'y a rien au PK 1484. Le parapet attribué au pont 1963 est en fait celui du virage qui précède la première épingle (PK 2131 à 2174). Au PK 1963, on ne voit qu'une glissière. Enfin, cinq ponceaux à parapets bas ne sont pas modélisés, aux PK 3446, 4572, 4672, 6110 et 6685. L'ouvrage indiqué par la carte IGN au PK 6229 est invisible à l'image.

## Corrections proposées, par ordre d'importance

1. **Pont 2777, PK 2760-2789 :** porter la largeur à 6,8 m, de façon symétrique.
2. **Parapets à déplacer :** ceux des PK 1484 et 1963 vont respectivement aux PK 1535-1590 et 2128-2178. Au PK 1963, il faut mettre une glissière à la place.
3. **Ponceaux, PK 4565-4585, 4670-4690 et 6100-6125 :** porter la largeur à 5,8, 6,0 et 6,3 m, et ajouter les parapets de béton.
4. **Accotements comptés en chaussée :** ramener le bord droit aux PK 4942-4983 (6,8 m), 4726-4780 (6,8 m), 2453-2464 (6,0 m), 3104-3109 (5,8 m) et 675-739 (7,0 m).
5. **Virage à gauche des PK 487-537 :** passer de 9,5 m à environ 7,3 m, en reprenant le bord intérieur.
6. **PK 3356-3399 :** passer de 4,3 m à 6,0 m, côté droit, le long de l'aire de stationnement.
7. **Ponts 4360 et 1661 :** retenir 6,5 m constants de 4325 à 4375, et 7,0 m sur le pont 1661.
8. **Départ :** passer à 6,6-7,0 m et modéliser à part le dégagement de gauche.

Les autres sections douteuses demandent des retouches de moins d'un mètre, ou rien du tout. Elles sont toutes décrites dans le fichier JSON.

## Notes du copilote

Le sens des virages est juste partout. Deux sévérités sont à revoir. Le grand virage à gauche qui suit la première épingle (13.1) est sous-estimé : il faut l'annoncer comme un « gauche 2 long », presque une épingle. Le virage du pont 2777 (15.2) est sans doute surestimé, car il a été calculé sur un tronçon interpolé : un « droite 2 sur pont » conviendrait mieux. Cinq petites inflexions peuvent être simplifiées, et la légère gauche du départ manque au brouillon. Il faut aussi ajouter les dangers : ponts et ponceaux, rétrécissement avant l'épingle, parapets intérieurs à ne pas couper (au Lion d'Or et à l'épingle de la D1), sorties de pistes qui ramènent des gravillons et enrobé rapiécé sur la D1.

## Ce qui reste invérifiable

Ces vidéos ne permettent pas de vérifier les 60 m avant la ligne de départ (les voitures partent arrêtées sur la ligne ; seule la vidéo de nuit les montre), les largeurs dans les épingles et au carrefour, les dévers, l'adhérence réelle, le texte de plusieurs panneaux ni l'arrivée de 2023. Le carrefour du Lion d'Or est décrit en détail dans le fichier JSON pour l'agent qui le reprend.
