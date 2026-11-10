# Intégration dans le jeu : ce que montrent les archives de BioBio et du jeu

*10 novembre 2026. Document destiné au directeur de projet.*

## 1. Résultat

Les sommaires d'archives envoyés par le directeur ont été lus avec un lecteur écrit pour le projet (`scripts/outils/lire_utoc.py`). Un sommaire ne contient que la liste des éléments d'une archive ; rien du contenu n'a été lu ni extrait.

Trois enseignements :

1. **On sait de quoi est faite une spéciale comme BioBio**, élément par élément (§ 2). C'est un niveau simple, pas une spéciale du jeu modifiée.
2. **Notre spéciale peut suivre exactement ce schéma**, et nos données s'y prêtent mieux que celles de BioBio (§ 3).
3. **Le jeu contient déjà le décor provençal dont nous avons besoin**, à commencer par le pin d'Alep (§ 4).

Ce qui n'est pas tranché : **avec quel outil ces fichiers sont fabriqués** (§ 5). C'est maintenant le principal verrou du projet.

## 2. Anatomie de BioBio

L'archive de la spéciale contient 7 751 éléments :

| Élément | Nombre | Rôle |
|---|---:|---|
| Niveau `Levels/SandoChlBio.umap` (et sa version en sens inverse) | 2 | Le niveau que le jeu charge. Aucune des pièces d'un grand monde découpé à la volée (cellules générées, niveaux de détail automatiques, terrain « Landscape ») : c'est un niveau simple. |
| Dalles de terrain `SM_…Terrain_x_y` | 1 936 | Le terrain est un damier de 44 × 44 dalles, des maillages ordinaires. |
| Une texture et un matériau par dalle | 1 936 + 1 936 | Chaque dalle porte sa propre image de sol. 158 dalles, sans doute les plus proches de la route, ont aussi une texture de relief fin. |
| Anneau lointain `FarRing` | 24 | Le paysage d'arrière-plan. |
| Matériaux de route `MI_WrcgRoadSimple` et variantes | 8 | La chaussée. |
| Traces de pneus (décalques) | 14 | |
| Arche d'arrivée, portique, rubalise | 3 maillages | Accessoires propres à l'auteur. |
| `DA_SandoChlBioBakedData` | 1 par sens | La surface de roulage et les obstacles : ce qui fait la physique. |
| `DT_PacenoteSandoChlBioFull` | 1 par sens | Les notes du copilote. |

Deux absences sont aussi instructives :

- **Aucun arbre, aucune herbe, aucun rocher** dans l'archive. La végétation visible en jeu vient donc des éléments du jeu, appelés par leur chemin. La page de l'auteur le dit ; la liste le confirme.
- **Aucun matériau « maître » et aucun programme d'affichage (shader).** Tous les matériaux de BioBio sont des variantes de matériaux existant déjà dans le jeu. C'est une contrainte forte et utile : pour être affichée, notre spéciale ne devra utiliser que des variantes des matériaux du jeu.

L'archive « registre » (10 éléments) remplace six tables du jeu : `DT_Levels`, `DT_Tracks`, `DT_TracksLocations`, ses fonds et logos, `DT_TracksVariants`. Elle ajoute deux images de menu et une table de surfaces. C'est elle qui fait apparaître la spéciale dans les menus.

**Conséquence à connaître :** ces tables sont remplacées en entier. Deux mods qui remplacent la même table ne cohabitent pas : le dernier chargé l'emporte. Si BioBio et notre spéciale doivent être installées ensemble, notre registre devra contenir aussi les lignes de BioBio, ou l'inverse.

## 3. Ce que cela donne pour le Grand Caunet

| Élément | Chez BioBio | Chez nous |
|---|---|---|
| Relief des dalles | Modèle mondial à 30 m | Relevé laser à 0,5 m |
| Image de chaque dalle | Fabriquée à partir d'une carte d'occupation du sol | Photo aérienne réelle à 20 cm |
| Route | Tracé OpenStreetMap | Axe, bords et dévers mesurés tous les mètres (phase 3) |
| Végétation | Éléments du jeu, placés d'après une carte mondiale | Éléments du jeu, placés d'après la carte forestière par essence et la hauteur d'arbres mesurée |
| Physique | `BakedData` | À produire à partir de notre maillage de route et de terrain |
| Notes du copilote | Table dédiée | À produire à partir de nos virages |

Le premier modèle 3D du projet (`modele/`, voir `03_phase3_chaussee.md`) est déjà organisé ainsi : un ruban de route, et un terrain découpé en dalles portant chacune sa photo aérienne.

## 4. Ce que le jeu met à disposition

Le catalogue du jeu (47 246 éléments, version 25170642) est enregistré dans `data/reference/catalogue_jeu_25170642.txt.gz` : des noms uniquement.

- **Spéciales sur asphalte existantes** : Alsace (Munster, Saverne) et Monte-Carlo (Bollène, Sisteron). Les secondes sont dans le sud-est de la France : leur décor est le plus proche du nôtre.
- **Arbres** : pin d'Alep (`Foliage/Trees/AleppoPine`, notre essence dominante à 39 %), pin noir, cyprès, olivier, figuier, arbre à perruque, lyciet, érable, haies.
- **Sol** : herbes sèches (plusieurs variantes), genêt, feuilles mortes, aiguilles de pin.
- **Route** : asphaltes de Bollène et de Sisteron, bas-côtés, fissures, traces de pneus, rapiéçages.
- **Abords** : murs de pierre, murs de soutènement, ponts et parois rocheuses de Monte-Carlo ; panneaux routiers français et panneaux de rallye ; glissières, clôtures, poteaux.
- **Surfaces de roulage** : asphalte lisse (`PM_SurfaceTarmacSmooth`), béton, herbe, graviers, bordure, et une vingtaine de surfaces d'obstacles (muret, glissière, rocher, bois, botte de paille…).

## 5. L'outil de fabrication : ce que dit la notice de BioBio

La notice jointe à BioBio (`THIRD_PARTY_NOTICES.txt`, transmise par le directeur) apporte quatre informations :

| Ce que dit la notice | Ce que j'en retiens |
|---|---|
| « Arbres, rochers, herbe, panneaux, portique d'arrivée et **programme d'affichage du terrain** viennent de votre copie du jeu : la spéciale les désigne par leur nom. » | Confirme la lecture des sommaires. Même le terrain utilise un matériau du jeu, avec les images de l'auteur. |
| « Quelques petits fichiers de réglages **suivent la disposition de ceux du jeu** : des réglages de matériaux qui pointent vers les programmes d'affichage du jeu avec nos textures, et des **modèles d'acteurs**. » | Les objets du niveau sont calqués sur ceux des niveaux du jeu. |
| La carte d'occupation du sol est « transformée en carte forêt / sol nu **pour placer les arbres** ». | Les arbres sont semés par programme, pas posés à la main. Notre carte forestière par essence et nos hauteurs d'arbres mesurées permettent de faire mieux. |
| Le gestionnaire d'installation embarque la bibliothèque de compression Oodle, « **utilisée par retoc pour lire les archives du jeu** ». | L'auteur utilise `retoc`, l'outil en ligne de commande qui lit et réécrit les archives du jeu. |

**Éditeur Unreal Engine 5.6, ou outil qui écrit directement les fichiers ?** Le directeur penche pour l'éditeur. La notice ne tranche pas, mais ses indices vont plutôt dans l'autre sens :

- des fichiers qui « suivent la disposition de ceux du jeu » et des « modèles d'acteurs » décrivent des fichiers recopiés et adaptés à partir de ceux du jeu, ce que fait un outil d'écriture directe, pas un éditeur ;
- l'outil cité est `retoc`, pas l'éditeur ;
- l'éditeur ne peut pas ouvrir les éléments compilés du jeu : pour y poser un pin d'Alep du jeu, il faut d'abord fabriquer des éléments factices portant le même nom, une voie que ACR Extra Stages juge non prouvée.

Rien de cela n'est une preuve : le gestionnaire peut n'utiliser `retoc` que pour fusionner les tables de menus à l'installation, et le niveau lui-même venir de l'éditeur. **Seul l'auteur peut le dire.**

Un point à ne pas confondre : le réalisme du rendu ne dépend pas de l'outil de fabrication. L'image est calculée par le moteur du jeu dans les deux cas. Ce qui fait le réalisme, ce sont le relief, les images de sol, les matériaux et les arbres du jeu que la spéciale désigne.

Deux autres inconnues demeurent :

1. **Le contenu exact du niveau** : quels acteurs y sont posés, et comment les arbres du jeu y sont appelés. Le sommaire donne les noms des fichiers, pas leur intérieur.
2. **Le format de la table des notes du copilote** et celui de `BakedData` : documentés en partie par ACR Extra Stages, à vérifier sur la version actuelle du jeu.

## 6. Suite proposée

1. **Écrire à l'auteur de BioBio** (voir `guide_pc_directeur.md`). La question est maintenant précise : avec quel outil produit-il le niveau et les matériaux ? Une réponse, même partielle, fixe la voie.
2. **Sans attendre, côté données** : terminer le modèle neutre (route texturée, dalles de terrain, placement des arbres par essence, murets et parapets), qui sert dans les deux voies.
3. **Sur le PC du directeur**, quand la voie sera choisie : produire d'abord une spéciale minimale (la route seule et sa physique), la charger en Free Practice, puis enrichir.
