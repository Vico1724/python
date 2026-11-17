# Pièges connus (à relire avant chaque construction)

Chaque ligne a coûté au moins une version au Grand Caunet. Référence entre parenthèses.

## Hôte gallois (Hafren South 1/2)

- **Humidité de base 0,1** de l'acteur météo du niveau : la remettre à 0 (`-HumiditeNiveau`, retouche 0006). (doc 14 § 16)
- **Ligne idéale** : acr-ref y recopiait l'axe avec un couloir fixe et une SkidIntensity nulle ; calculer la trajectoire (`ideal_line` de `stage.json`). Sous-virage signalé deux fois avant de le trouver. (doc 14 § 16)
- **Ligne de la table des variantes** : « Gravel / GravelOnly » et météo Wales ; la livrer en asphalte (Tarmac, TarmacSnow, MonteCarlo). (doc 14 § 6, § 15)
- **Registre tiers dans `Paks`** (pas dans `~mods`) : il masque toute table livrée moins bien classée. Notre table part de la sienne, dans un conteneur `_9_P`, et se refait s'il change. (doc 14 § 6)
- **Personnages du parc étiquetés `ServicePark`** : cachés pendant la spéciale ; neutraliser l'étiquette. (doc 14 § 13)
- **Parc d'assistance** : toujours caché pendant une spéciale, même dans le jeu d'origine ; il reste à sa place galloise si on ne le déplace pas. (doc 16)
- **Cellules World Partition « toujours chargées »** : le drapeau `bIsAlwaysLoaded` ne suffit pas, le jeu cuit charge par cases de grille (`MainGrid` : 350 m, portée 640 m). Une cellule à faire charger ailleurs (officiels du départ et de l'arrivée) doit être rangée dans la case unique du niveau 5, en échangeant sa référence avec une cellule du sens retour. (doc 14 § 17.1)
- **Adhérence de départ** : option de météo du joueur (« Starting Grip Level »), de Dirty 0,85 à Optimal 1,0 ; à mettre sur Optimale avant de juger la tenue de route. Hors trajectoire, l'adhérence perd un niveau. (doc 14 § 17.2)
- **Parc réduit** : le présentoir `BC_TiresRack_C` fait apparaître des pneus que le jeu ne cache pas pendant la spéciale ; l'enfoncer. Placer la tente au pôle d'inaccessibilité du parking, voitures garées exclues. (doc 14 § 17.3)
- **Arbres près des murs** : écarter le tronc ne suffit pas, le houppier traverse les murs ; appliquer la règle du houppier avec la distance au mur. (doc 14 § 17.4)
- **Portiques verts** d'acr-ref au départ et à l'arrivée : les enterrer ; **ne pas** passer d'option de visuels avec notre décor, sinon la zone rouge de départ disparaît aussi. (doc 14 § 10, § 12)
- **Murs de reprise** tracés 20 m au-delà du bout de chaque porte : des bouts très obliques les ramènent sur le terrain près de la route (mur invisible). (doc 14 § 13)
- **Menus** : « Hafren South » reste affiché sans `-Noms` ; la variante 2/2 n'est plus jouable tant que le mod est installé.

## Unreal et cuisson

- `construire_niveau.py` exige l'éditeur complet (`UnrealEditor.exe … -ExecutePythonScript=…`), pas `-Cmd`.
- **Cuire avec versions** (`-Versionne`) dès qu'il y a un niveau.
- **Parent = une variante du jeu** qui a déjà les bons static switch, jamais un maître (`M_Simple` resterait uni).
- Nanite désactivé dans le jeu : ne pas cuire de maillage Nanite.
- L'import **ne remplace pas** un élément existant : supprimer les dossiers concernés avant de réimporter.
- Chemins passés à l'éditeur avec des `/`, jamais des `\`.
- Code de sortie −1073741819 à la fermeture de l'éditeur : sans effet si le rapport JSON est complet.
- Coordonnées Lambert-93 dans les UV : au-delà de ce que le moteur stocke (branche noire au Lion d'Or). Toujours des UV locales.
- Les cubes factices doivent porter les dimensions des vrais maillages (bornes et tri des instances).
- Véhicules du jeu : leurs matériaux refusent les instances ; acteurs individuels.

## Matières et éléments du jeu

- **Couleur de sommet des murs du jeu : blanc = mousse, noir = pierre.** (deux versions perdues)
- Herbes à `UseRVTBaseColor` (plantain, herbe sauvage) et feuilles mortes, plantes rampantes : rendues en noir.
- Arbre à perruque : mauve ; Blackmaple : jaune ; Olivetree : pâle ; Boxthorn : vert sombre dense. Toujours regarder l'image d'ensemble (`T_<Arbre>NNBillboard_B`) avant de choisir.
- Trois « arbres » du jeu sont des souches ou des plants (0,25 à 0,87 m) : choisir le maillage d'après sa hauteur relevée.
- Pierres et rochers du jeu : beige rosé assombri, non réglables.
- Le décalque de marquage du jeu ne s'affiche pas sur nos maillages.
- Le paillis de fond de Bollène est presque noir (52, 43, 27) : remplacer la couche 1 du terrain.
- Une photo aérienne vue du ciel ne montre ni falaise ni sous-bois : ne jamais la poser telle quelle sur le relief lointain.

## Données et vidéos

- Coordonnées imprimées d'un roadbook : indicatives ; les PK font foi.
- Une vidéo surestime la largeur là où un accotement plat longe l'enrobé ; elle la sous-estime sur les ponts interpolés.
- Altitude des bords aux ponts : lue dans le vide si l'on ne vérifie pas le MNS (plis et marches en jeu).
- Ponceaux IGN décalés : le LiDAR montre le vrai vide (26 m d'écart au PK 3 450).
- Le calage de la vidéo de course par les virages échoue souvent ; celui d'une vidéo du jeu part de t = 0 alors que la voiture attend le départ.
- Le tangage de la caméra ne mesure pas le profil en long.

## Contrôles et méthode (conversations du 11 au 15/11)

- **Un contrôle hors jeu prouve la présence, pas la visibilité** : « 10 personnages sur 10 à leur place » alors qu'aucun ne s'affichait (étiquette `ServicePark`). Pour un nouvel acteur, comparer tous ses réglages à ceux d'un acteur du jeu qu'on sait visible.
- **Ne pas conclure « impossible » sans avoir regardé les spéciales du studio** (commissaires le 14/11, faisabilité le 10/11).
- **Demander l'endroit exact d'un défaut** (capture, PK, côté) avant d'en chercher la cause : le mur invisible du Lion d'Or a d'abord été attribué à tort aux parois.
- **Véhicules garés** : variante « feux éteints » imposée à chacun (les monospaces du jeu ont leurs feux de détresse allumés par défaut).
- **Parc d'assistance** : l'écran n'apparaît ni avec « Recommencer » ni en week-end de rallye ; essayer depuis le menu principal, en essais libres.
- **Ne pas empiler plusieurs versions sans essai** quand des relectures d'agents se succèdent : elles peuvent se contredire (pont du PK 2602, v8).

## Placement et construction

- Ordre : route physique → `relever_placement.py` → pose du décor. Après toute modification du tracé, le placement bouge (6,8 cm la première fois).
- Ne pas ouvrir le jeu pendant `7_tout_refaire.ps1` : la route physique est sautée.
- Toute nouvelle règle de placement mérite un contrôle chiffré (degrés comparés à des mètres jusqu'à la v12 ; arbustes dans les bâtiments jusqu'à la v11).
- Avant de supprimer un objet relevé, relire la vidéo : le mur de l'épingle du km 4,08 retiré à tort en v7.
- Une correction locale (zone de départ) ne doit pas changer le reste de la spéciale. Deux pièges : une règle écrite sur « tous les murs » s'applique partout, et tout tirage au sort fait après un filtre (sous-bois, fourré, lacets) se décale sur toute la spéciale dès qu'une seule place change. Le cas s'est produit aux builds 19 et 20, avec un sous-bois différent jusqu'au PK 7 214. Pour figer l'ancien état, tirer la végétation deux fois (anciennes règles, nouvelles) et assembler par PK, puis comparer au code repris de git.
