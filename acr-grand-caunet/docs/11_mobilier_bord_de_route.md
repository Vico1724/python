# Obstacles et objets de bord de route ajoutés

*12 novembre 2026. Document destiné au directeur de projet et à la session qui reprendra le travail.*

**Demande du directeur.** Ajouter, sans attendre d'essai en jeu, les obstacles que l'on sait manquants : poteaux électriques, barrières, etc.

## 1. Ce qui est ajouté

Tout est posé avec des objets du jeu lui-même, sauf les câbles et les murs, qui sont à nous.

| Objet | Nombre | Où | D'après |
|---|---|---|---|
| Poteaux électriques de 9 m, à droite, à 3 m du bord | 26 | km 3,85 à 4,34 (8 poteaux) et km 5,57 à 6,67 (18 poteaux) | captures de la vidéo et inventaire du relevé |
| Câbles entre ces poteaux, trois par portée | 24 portées | les deux mêmes lignes | déduit des poteaux |
| Panneaux jaunes « annonce de point radio » | 7 | km 2,18 ; 2,61 ; 2,86 ; 3,55 ; 4,97 ; 5,37 ; 5,59 | inventaire (« panneau jaune ») et capture à 4 min 12 |
| Panneaux bleus « point radio » | 6 | débouchés de pistes des km 1,50 ; 2,66 ; 2,99 ; 3,19 ; 5,03 ; 6,49 | inventaire (« panneau bleu ») |
| Panneau jaune « annonce de secours » | 1 | km 3,08 | inventaire (« jaune à pictogramme rouge ») |
| Panneaux d'arrivée : annonce jaune à damier, puis rouge à damier | 2 | km 6,54 et 6,74, à gauche | inventaire |
| Barrières plastique rouges et blanches | 9 | km 2,65 à 2,67, à droite : piste barrée | inventaire |
| Haie taillée de 2 m | 31 modules, 200 m | km 5,04 à 5,23, à droite | inventaire (« haie dense continue ») |
| Mur de pierre bas | 23 m | km 1,69 à 1,71, à droite | inventaire |
| Murets de pierre | 34 m et 12 m | km 5,26 à 5,29 et km 5,49, à droite | inventaire |
| Blocs de béton | 2 | km 2,34 à droite (fin de glissière), km 2,70 à gauche | inventaire |
| Parapets du pont du km 3,2 allongés à 37 m | 2 | km 3,19 à 3,23 | inventaire |

## 2. Ce que la voiture rencontre

Les poteaux, la haie, les barrières et les murs sont aussi dans la physique : la voiture les heurte.

| Objet | Matière de choc du jeu |
|---|---|
| Poteau | béton (cylindre de 30 cm) |
| Haie | buisson |
| Barrière plastique | barrière plastique |
| Murs et blocs | roche ou béton, comme les parapets |

Les panneaux et les câbles n'ont pas de collision. Le mod de l'étape 1 compte maintenant 2 763 obstacles, contre 2 578.

## 3. Ce qu'il faut savoir sur la précision

- **Les poteaux ne sont pas à leur place exacte.** Dix d'entre eux sont vus sur la vidéo, à 25 m près ; les seize autres sont répartis régulièrement entre eux. La première ligne (km 3,85 à 4,34) n'était pas dans l'inventaire : elle vient de vos captures du 12 novembre.
- **Un poteau n'est jamais planté dans un ravin** : s'il tombe sur un pont ou un ponceau, il est décalé de 8 à 24 m le long de la ligne.
- **Les panneaux jaunes « non lus »** de l'inventaire sont rendus par le panneau jaune de point radio du jeu. C'est une déduction : ils sont presque tous 40 à 110 m avant un panneau bleu, comme le veut le règlement, et votre capture à 4 min 12 en montre un.
- **Hauteurs des murs et de la haie** : supposées (0,5 m pour les murets, 2 m pour la haie).
- **Sens des panneaux** : relevé dans le niveau de Bollène, où le jeu les tourne de 90° par rapport au sens de la route pour qu'ils fassent face aux concurrents.

## 4. Ce qui n'est pas ajouté

- **Panneaux routiers** (triangles de danger des km 2,13 ; 3,50 ; 3,72 ; 5,29 ; 5,37) : le jeu en a, mais je n'ai pas pu identifier leurs dessins sans les voir.
- **Balises de virage à chevrons** (km 0 ; 2,28 ; 5,52).
- **Rochers au ras de la chaussée** (km 1,54 à 1,61, à gauche) et **talus rocheux** (km 0,25 à 0,84 ; 2,08 à 2,18) : ce sont des obstacles durs dont la position exacte compte. Je préfère les poser d'après votre prochaine vidéo plutôt qu'au jugé.
- **Clôture en bois** du km 5,26 et **garde-corps** du km 5,50 : seuls leurs murets sont modélisés.
- **Public, véhicules, commissaires, chronométrage.**

## 5. Où c'est décrit

- La liste des objets, avec la source et la confiance de chacun : `data/reference/mobilier_bord_de_route.json`.
- Les murs : `data/reference/ouvrages_parapets.json`, rubrique `parapets_hors_tablier`.
- Le code : `scripts/mobilier.py`, utilisé par `09_export_stage_ir.py` (collisions) et `16_paquet_unreal.py` (décor).
- Pour tout retirer : `python scripts\16_paquet_unreal.py --mobilier sans`, et retirer les objets du fichier pour la physique.

**Rien de ceci n'a encore été vu en jeu.**
