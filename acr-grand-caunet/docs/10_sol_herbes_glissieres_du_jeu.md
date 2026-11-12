# Sol, herbes et glissières repris du jeu

*12 novembre 2026. Document destiné au directeur de projet et à la session qui reprendra le travail.*

**Demande du directeur.** Améliorer la qualité graphique sans attendre un essai en jeu à chaque étape. En jeu, le sol était flou de près, et les glissières étaient unies.

## 1. Ce qui change à l'écran

- **Le sol** ne porte plus la photo aérienne. Il est fait des matières du jeu lui-même : paillis forestier, aiguilles de pin, herbe sèche, herbe haute, terre, cailloux. Elles sont nettes de près, puisqu'elles se répètent tous les 3 m. La photo aérienne sert encore, mais seulement à teinter l'ensemble vu de loin.
- **Les glissières** sont celles du jeu, posées le long des six mêmes tronçons (848 m) : 212 modules de 4 m, avec leurs extrémités.
- **Les bas-côtés** reçoivent 82 000 touffes d'herbe sèche du jeu (12 par mètre de route), sur 14 m de part et d'autre de la chaussée. Ce sont les cinq mêmes végétaux que le jeu pose à Bollène, avec les mêmes tailles. Ils disparaissent au-delà de 100 à 150 m, comme dans le jeu, pour ne pas ralentir l'affichage.
- **L'asphalte** reçoit le réglage de sommets des routes de Bollène, dont il hérite la matière.
- **Les parapets, les arbres et le paysage lointain** ne changent pas.

## 2. Comment le sol est réparti

La répartition vient de trois mesures de l'IGN déjà utilisées par le projet : la hauteur de la végétation (relevé laser), la vigueur de la végétation (photo infrarouge) et la clarté du sol (photo couleur).

| Là où | Le sol reçoit |
|---|---|
| il y a des arbres | aiguilles de pin et paillis, mêlés |
| il y a de la garrigue (0,4 à 2 m) | herbe sèche et cailloux |
| le sol est ouvert et vert | herbe sèche, herbe haute si la végétation est très vigoureuse |
| le sol est nu et clair (calcaire) | cailloux |
| le sol est nu et sombre | terre |
| à moins de 1,5 m de la chaussée | cailloux (accotement) |

Sur les 41 carrés de 350 m qui portent le terrain : 40 % d'aiguilles de pin, 28 % de paillis, 18 % d'herbe sèche, 9 % de cailloux, 4 % de terre, 1 % d'herbe haute.

Ce sont des règles de bon sens, pas un relevé de terrain. Elles placent la bonne matière au bon endroit dans les grandes lignes, pas au mètre près.

## 3. Ce qui a été vérifié, et comment

Tout a été contrôlé hors du jeu, en relisant les fichiers produits avec les archives d'origine du jeu.

- **Le calage des masques du jeu** a été lu sur une dalle de Bollène : une seule des huit orientations possibles place la route du masque sur le tracé de la route.
- **Le calage de la carte de couleur** a été lu sur Hafren South puis sur Bollène, de la même façon.
- **Le terrain redécoupé** a exactement la même surface que l'original (1 985 967 m²), et ses morceaux se raccordent.
- **Les glissières** ont toutes la chaussée du bon côté, à 50 cm du bord, et suivent la pente.
- **Le conteneur livré** a été relu par `pc/etape2_unreal/outils/relire_decor.py` : 458 maillages posés et 246 194 objets (arbres, arbustes, herbes, glissières), comme prévu ; aucun fichier hors de notre dossier ; les 41 matériaux de sol ont bien le terrain de Bollène pour parent ; les 82 masques ont le même format que ceux du jeu et le même contenu que leurs fichiers d'origine ; les sommets du sol et de l'enrobé ont une couleur nulle ; les herbes ont les distances de disparition du jeu et ne portent pas d'ombre. Le détail est dans `pc/etape2_unreal/releves/relecture_decor.json`.

## 4. Ce qui n'est pas vérifié

**Rien de ceci n'a été vu en jeu.** Trois points peuvent mal tourner :

1. nos masques sont des « textures virtuelles » cuites par l'Unreal du commerce, pas par celui du studio ;
2. l'ordre dans lequel le jeu superpose ses matières est supposé ;
3. le matériau de sol de Bollène prévoit de la neige selon la météo du niveau.

## 5. Revenir en arrière

L'ancien décor (sol en photo aérienne, nos glissières, pas d'herbes) est gardé dans `Z:\acrxs\unreal\dist\sol_photo\`. Jeu fermé, recopier ses trois fichiers `zz_gc_gc_P.*` dans `Paks\~mods` à la place des nouveaux. La route et la physique sont les mêmes dans les deux versions.

Si le sol apparaît noir, uni, blanc ou décalé, c'est ce retour en arrière qu'il faut faire, puis le signaler.

## 6. Autre correction faite au passage

Le constructeur de l'étape 1 replace la spéciale dans le niveau hôte à chaque construction, d'après l'emprise de la route. Après la régularisation du tracé, ce placement avait bougé de 6,8 cm : le décor a été reposé avec le nouveau placement avant d'être livré. `pc/etape2_unreal/outils/relever_placement.py` fait désormais ce relevé et dit de combien le placement a bougé.
