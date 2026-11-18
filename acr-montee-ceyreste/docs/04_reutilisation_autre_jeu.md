# 04 - Réutiliser la carte dans un autre jeu (export neutre)

*Demande de l'utilisateur (18/11/2026, mots exacts) : « dans le sens ou au moins si on veut reuse cette carte dans un autre jeu on a tout les mdoel ».*

**Rien de cet export n'a été importé dans un autre jeu ni dans un projet Unreal vierge.** Ce qui suit dit ce qu'il contient, comment il est construit et contrôlé, et ce qu'il faudra refaire.

## Ce que contient `export/neutre/`

Régénéré par `python scripts/33_export_neutre.py`, après `16_paquet_unreal.py`. Seuls `manifeste.json`, `correspondance_types.csv` et `controle.json` sont versionnés. Le reste est lourd et se régénère.

| Dossier | Contenu |
|---|---|
| `modeles/` | Toute la géométrie propre à la carte, en glb autonomes : `terrain_sol.glb` (terrain proche, avec ses images de dalles dans `modeles/textures_sol/`), `lointain.glb`, `route_habillee.glb` (enrobé et marquage), `ouvrages.glb` (murs, murets, parapets, glissières à nous, tabliers), `annexes.glb`, `balisage.glb`, `bati_bord.glb` (maisons du bord de route), `village.glb` (village de Ceyreste), `clotures.glb` (murs, murets, grillages, toiles, haies, portails, piliers et panneaux du départ de la troisième passe, textures CC0 et calculées, grillage à transparence), `panneaux_neutres.glb` (12 panneaux exacts mât + plaque, voir plus bas), et les maillages fabriqués par le projet que le paquet ACR pose en instances (pierres calcaires, blocs, poteau de béton). |
| `collisions/` | Collisions séparées : `collision.glb` (sol physique, un primitif par surface) et `objects_collision.glb` (obstacles), tous deux de l'export Stage IR ; `ouvrages_collision.glb`, `annexes_collision.glb`, `bati_bord_collision.glb`, `clotures_collision.glb` (volumes bruts ; matières pierre, beton, cloture, haie). |
| `placements/` | Un CSV par famille : arbres, arbustes, garrigue, versants, herbes, rocaille, glissières du jeu, mobilier. Colonnes : `type, x_l93, y_l93, z_ngf, x_local_m, y_local_haut_m, z_local_sud_m, cap_deg, echelle, hauteur_m, pk_m, source`. |
| `correspondance_types.csv` | Pour chaque type : description en clair, maillages ACR utilisés, substitut libre, nature du substitut (réel, forme simple, projet, rien) et nombre posé. |
| `manifeste.json` | Repère, liste des fichiers avec taille, bornes et nombre de maillages, comptes par famille et par type, licences. |
| `controle.json` | Verdict du contrôle (voir plus bas). |

Aucun asset du jeu n'est extrait ni copié : ils ne sont pas redistribuables. Les arbres, herbes, panneaux et glissières du jeu ne sont présents que par leur type et leur placement.

## Repère

- glb : mètres ; X = est, Y = haut, Z = sud (glTF 2.0) ; X = x_L93 − x0, Y = z − z0, Z = −(y_L93 − y0). L'origine est l'axe de la chaussée au PK 0, en Lambert-93 et NGF dans `manifeste.json`. Les sommets sont en coordonnées absolues du repère : aucun nœud n'est transformé.
- Vers Unreal : UE_cm = 100 × (X, Z, Y), c'est-à-dire X est, Y sud, Z haut. Vérifié pour le paquet ACR par une mire d'axes ; pas pour un projet vierge.
- Placements : Lambert-93 (EPSG:2154) et altitude NGF-IGN69, plus le repère local. `cap_deg` donne la direction de l'axe +X du maillage d'origine, depuis le nord dans le sens horaire.

## Importer dans un projet Unreal vierge

`carte-reelle-unreal/scripts/unreal/importer_paquet.py` ne s'applique pas tel quel : il attend un paquet carte-reelle-unreal (heightmap de Landscape, `placements/arbres.csv` à son format, `table_assets.csv`). De même, `controle_paquet.py` ne s'applique pas. Voie proposée, **non essayée** :

1. Importer les glb de `modeles/` sans Nanite, avec « Combine Meshes » coupé. Les poser à l'origine, sans rotation, à l'échelle 100 si l'import ne convertit pas les mètres en centimètres. Vérifier un point : le PK 0 doit tomber à (0, 0, 0).
2. Pour chaque type de `correspondance_types.csv`, choisir un maillage. Puis créer un composant d'instances par type depuis les CSV de `placements/`, à la position (x_local, z_local, y_local) × 100 et au lacet = cap_deg − 90 (convention Unreal).
3. Refaire les matériaux : les glb portent des images de base, sans relief ni rugosité réglée.
4. Refaire la physique : surfaces (asphalte, gravier, herbe) d'après `collision.glb`, obstacles d'après `objects_collision.glb`.

## À refaire pour chaque jeu

- Matériaux : enrobé, marquage, murs, roche, sol.
- Acteurs propres au jeu : départ, arrivée, points de passage, notes du copilote (le Stage IR de `export/stage_ir/` en donne les positions).
- Physique des surfaces et des obstacles.
- Arbres et herbes (voir la liste suivante).
- Décalques de chaussée : la couche neutre est à faire (voir plus bas).

## Types sans modèle libre

D'après `correspondance_types.csv` :
- **Forme simple à fabriquer** (cône, cylindre, cartes croisées, plaque) : pin d'Alep, chêne vert, chêne pubescent, olivier, cyprès, autre pin, touffes d'herbe verte et sèche, panneaux de danger (A15b, A1d), balises J4, bornes de PR, poteaux en bois. Pour les pins, les textures Poly Haven `pine_tree_01` (CC0) existent, mais le modèle (17 millions de polygones) est inutilisable tel quel. Pour l'olivier, le seul modèle du catalogue est sous licence Fab « Personal » : non redistribuable.
- **Substitut réel** : arbustes de garrigue → Poly Haven `wild_rooibos_bush` (CC0, approchant).
- **Fournis par le projet** : pierres calcaires, blocs, poteau de béton, glissière (lisse et poteaux de `ouvrages.glb`).
- **Rien** : véhicules garés.

**Pas encore fait dans cet export :**
- Panneaux : **faits le 18/11/2026** (`scripts/39_panneaux_neutres.py`, `modeles/panneaux_neutres.glb`, placements et source de chaque face dans `data/processed/panneaux_neutres.json`). Faces A15b et A1d : Wikimedia Commons, auteur Roulex_45, **CC BY-SA 3.0** (pas domaine public : citer l'auteur, partager à l'identique) ; les dix autres (EB20, B13, B14, A14 + panonceau, AB3a, J4 ×2, PR 5, 7, 8) **redessinées simplement** (Wikimedia a refusé le téléchargement : « 429 »). Restent sans modèle : B1, panneaux d'information non lus, abri de bus.
- Couche de décalques de chaussée indépendante du jeu : les traces relevées sont dans `data/reference/chaussee_surface_releve.json` ; elles ne sont pas encore exportées en CSV avec des textures libres (`muddy_tracks` Poly Haven pour les ornières ; pour la gomme, une texture à générer).

## Contrôle

`controle.json` vérifie que chaque glb listé est présent et lisible, que ses bornes sont finies et tiennent dans 25 km autour de l'origine, et que les images du terrain sont là. Pour chaque famille de placements, il mesure l'écart au MNT LiDAR 0,5 m : médiane, 1er et 99e centiles, objets flottants de plus de 0,3 m, objets enterrés de plus de 0,5 m. Un objet posé sur une paroi, un mur ou un tablier peut s'écarter légitimement du MNT nu. Verdict et chiffres : voir `docs/ETAT.md`.
