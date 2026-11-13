# Sol, herbes, buissons et glissières repris du jeu

*12 novembre 2026. Document destiné au directeur de projet et à la session qui reprendra le travail.*

**Demande du directeur.** Améliorer la qualité graphique sans attendre un essai en jeu à chaque étape. En jeu, le sol était flou de près, et les glissières étaient unies.

## 1. Ce qui change à l'écran

- **Le sol** ne porte plus la photo aérienne. Il est fait des matières du jeu lui-même : paillis forestier, aiguilles de pin, herbe sèche, herbe haute, terre, cailloux. Elles sont nettes de près, puisqu'elles se répètent tous les 3 m. La photo aérienne sert encore, mais seulement à teinter l'ensemble vu de loin.
- **Les glissières** sont celles du jeu, posées le long des six mêmes tronçons (848 m) : 212 modules de 4 m, avec leurs extrémités.
- **Les bas-côtés** reçoivent 82 000 touffes d'herbe sèche du jeu (12 par mètre de route), sur 14 m de part et d'autre de la chaussée. Ce sont les cinq mêmes végétaux que le jeu pose à Bollène, avec les mêmes tailles. Ils disparaissent au-delà de 100 à 150 m, comme dans le jeu, pour ne pas ralentir l'affichage.
- **Les arbustes de garrigue** étaient rendus par des arbres réduits au tiers et par des plantes rampantes plates. 98 000 d'entre eux deviennent de vrais buissons vert olive du jeu, à leur taille (0,5 à 2 m). Ils disparaissent au-delà de 150 à 220 m.
- **L'asphalte** reçoit le réglage de sommets des routes de Bollène, dont il hérite la matière.
- **Le paysage lointain** est éclairé plus doucement. Sa photo aérienne porte déjà l'ombre des versants ; le soleil du jeu les ombrait une seconde fois, d'où le massif très sombre vu au km 3,9. C'est une hypothèse sur la cause, à juger en jeu.
- **Les parapets et les arbres** ne changent pas.

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

## 4. Essai en jeu du 12 novembre

Le directeur confirme que le nouveau décor s'affiche : sol, herbes, buissons, glissières. Les trois craintes d'avant l'essai (textures de masques, ordre des matières, neige) ne se sont pas réalisées.

Il relève en revanche des défauts, corrigés depuis : chaussée pliée aux ponts, parapets trop hauts et unis, sol anthracite sous les arbres, massif lointain bleu ardoise. Le détail est dans `pc/etape2_unreal/PROTOCOLE.md` (§ 0 septies) et dans `docs/09_regularisation_et_videos.md` (section 7). **Ces corrections n'ont pas encore été vues en jeu.**

## 5. Revenir en arrière

Onze versions sont gardées sur le PC. Chacune est rangée avec la route physique qui va avec elle, et le script installe les deux ensemble.

| Version | Contenu |
|---|---|
| `sol_jeu` (installée) | cinquième version du 13 novembre : carrefour du Lion d'Or repris, versants boisés, roche sur les falaises, spéciale classée en asphalte (`docs/14_apres_essai_du_13_11.md`, sections 5 et 6) ; jamais vue en jeu |
| `sol_jeu_vu_le_13_11_ter` | quatrième version, vue en jeu le 13 novembre au soir : lignes blanches rétablies, bords nets, arbres du bord choisis d'après leur forme |
| `sol_jeu_vu_le_13_11_bis` | troisième version, vue en jeu le 13 novembre après-midi : parois rocheuses sur le relief, versants lointains verts, herbe verte ; lignes blanches absentes, bords en zigzag, arbres qui débordent |
| `sol_jeu_cycle1_du_13_11` | première version faite après l'essai du 13 novembre au matin ; jamais vue en jeu |
| `sol_jeu_vu_le_13_11` | celle que vous avez vue en jeu le 13 novembre : falaises, rochers, panneaux routiers, objets du rallye replacés (`docs/13_decor_fixe_et_objets_du_rallye.md`) |
| `sol_jeu_releve_reco` | bords repris d'après la vidéo des reconnaissances (`docs/12_releve_reconnaissances.md`) ; jamais vue en jeu |
| `sol_jeu_avant_releve_reco` | la suivante, plus les poteaux estimés, panneaux, barrières, haie et murs de l'ancien relevé (`docs/11_mobilier_bord_de_route.md`) ; jamais vue en jeu |
| `sol_jeu_sans_mobilier` | chaussée corrigée aux ponts, parapets bas en pierre et en béton, sol et lointain éclaircis ; jamais vue en jeu |
| `sol_jeu_vu_le_12_11` | celle que vous avez vue en jeu le 12 novembre au matin, avec ses défauts |
| `sol_photo_plus` | la même que la précédente, mais avec l'ancien sol en photo aérienne |
| `sol_photo` | le décor vu en jeu le 11 novembre : sol en photo, nos glissières, pas d'herbes |

Jeu fermé, pour changer de version :

```
pwsh -ExecutionPolicy Bypass -File pc\etape2_unreal\scripts_pc\choisir_decor.ps1 -Decor sol_jeu_vu_le_12_11
```

Sans `-Decor`, le script liste les versions et dit laquelle est installée. Chaque nouveauté se retire aussi séparément dans `scripts/16_paquet_unreal.py` (`--herbes sans`, `--buissons script10`, `--glissieres modele`, `--lointain-aplat 0`, `--lointain-clarte 0`, `--sol photo`), au prix d'une reconstruction du décor de 10 à 50 minutes.

## 6. Autre correction faite au passage

Le constructeur de l'étape 1 replace la spéciale dans le niveau hôte à chaque construction, d'après l'emprise de la route. Après la régularisation du tracé, ce placement avait bougé de 6,8 cm : le décor a été reposé avec le nouveau placement avant d'être livré. `pc/etape2_unreal/outils/relever_placement.py` fait désormais ce relevé et dit de combien le placement a bougé.
