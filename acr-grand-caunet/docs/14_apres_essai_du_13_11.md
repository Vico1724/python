# Après l'essai en jeu du 13 novembre : route lissée, roche, sol, herbe, végétation

*13 novembre 2026. Document destiné au directeur de projet et à la session qui reprendra le travail.*

**Constat du directeur après son essai** (vidéo de 4 min 30 fournie). La surface de la route, les obstacles ajoutés et le profil de la route sont en progrès. Mais :

- la qualité du relief, proche comme lointain, laisse à désirer ;
- des parois rocheuses naturelles sont devenues d'immenses parapets ;
- les bords de l'asphalte et les lignes blanches sont saccadés, alors que la route réelle est lisse ;
- des arbres dépassent sur la route ;
- l'herbe est jaune et haute, alors que sur les vidéos elle est courte et verte.

**Consigne.** Carte blanche pour obtenir le rendu le plus réaliste possible, en prenant la vidéo de reconnaissance comme modèle de qualité ; travailler sans arrêt, il dira quand faire un essai.

## 1. Comment les écarts ont été relevés

La vidéo de l'essai a été calée sur la route, puis 167 paires d'images ont été tirées, une tous les 40 m : le jeu à gauche, la reconnaissance à droite, au même endroit. Deux relevés systématiques de ces paires donnent environ 200 écarts localisés (`data/reference/releve_essai_13_11/`). Ils confirment les cinq constats et en ajoutent :

- des rectangles gris clair et des faisceaux de lignes grises sur la chaussée : c'étaient mes « pièces d'enrobé » et mes « fissures » de la veille ;
- un sol gris anthracite et nu, là où la réalité montre de la pierraille claire, de la terre ocre et de la litière rousse ;
- des massifs lointains blancs, d'aspect enneigé, rayés de bandes : ma teinte de falaise de la veille, trop forte ;
- un asphalte trop sombre et bleuté ; des parapets trop sombres ; des poteaux électriques démesurés ; des rochers ronds, identiques, alignés ;
- des aires de terre et des débouchés de pistes absents.

## 2. Ce qui est corrigé

| Défaut | Cause trouvée | Correction |
|---|---|---|
| Ligne centrale en dents de scie | Une coordonnée de l'axe était écrite au décimètre au lieu du millimètre : 5 cm de zigzag à chaque mètre | Écriture au millimètre |
| Bords et lignes qui serpentent | Sur les lignes droites, l'axe relevé ondule de 15 cm tous les 25 à 30 m ; l'ancien lissage ne retirait que les défauts plus courts | Lissage fort partout où la route ne tourne pas vraiment, léger dans les vrais virages. Sur la ligne droite du km 1,05 à 1,13, l'ondulation est divisée par six. Aucun point ne bouge de plus de 25 cm ; les contrôles sur les virages passent tous |
| Bord d'asphalte en ligne nette | La chaussée s'arrêtait d'un trait | Une mince bande de sol mord inégalement sur chaque bord (3 à 42 cm), comme la terre et la pierraille sur la route réelle |
| Rectangles et lignes parasites sur la chaussée | Bandes de couleur unie posées sur l'enrobé | Retirées entièrement |
| Parois rocheuses en « parapets » ; talus lisses et sombres | 9 parois rendues par un mur de pierre ; les autres talus rocheux n'étaient que du terrain | 43 affleurements (1,7 km) habillés de la roche du jeu, éclaircie vers le calcaire. La roche épouse le talus du relevé laser : bancs, blocs de biais, cassures, plaques de terre entre les roches. Huit parois que la vidéo plaçait là où le terrain est plat ont été glissées de 4 à 28 m le long de la route, là où le talus monte vraiment |
| Arbres sur la route | Les arbres du jeu sont plus larges que les houppiers relevés ; seule la position du tronc était contrôlée | Le houppier ne doit plus passer le bord. Un arbre trop grand pour sa place est réduit, pas retiré : les bords restent fermés par la végétation. Même règle dans la physique |
| Herbe haute et jaune | Touffes sèches de 0,6 à 1,5 m | Herbes vertes de 15 à 35 cm sur les accotements, feuilles mortes ; touffes sèches basses ailleurs |
| Sol anthracite | La matière de fond du jeu (« paillis ») est presque noire | Fond pierreux clair, aiguilles dorées, herbe rase verte en bande le long de la route, roche sur les pentes : textures du jeu (Grèce, Alsace, Bollène) désignées par nos matériaux, teintes réglées |
| Asphalte sombre et bleuté | Réglage de Bollène | Teinte éclaircie et réchauffée, grandes fissures atténuées |
| Parapets sombres | Pierre brute sombre | Pierre claire de Bollène, teintée beige |
| Massifs blancs et rayés | Teinte de falaise trop claire, posée jusque sur le relief lointain à 25 m | Bandes retirées, teinte moins claire, limitée au relief fin (6 km) |
| Versants lointains gris pâle, rayés de pistes blanches | La photo aérienne montre le sol entre les arbres, et ses forêts sont gris-bleu ; je l'avais en plus éclaircie le 12 novembre | Images retraitées pour être vues de la route : là où la forêt domine, le versant prend le vert sombre des pins, les pistes et les trouées disparaissent sous les arbres ; champs, villages et rocher nu gardent la photo. Contrôlé sur un aperçu hors jeu : au km 3,08, on retrouve la falaise claire au-dessus des versants verts de la reconnaissance |
| Taches blanches floues sur les versants | Ma teinte de falaise débordait sur des pentes boisées | Réservée aux pentes de plus de 46°, sans débord |
| Relief proche plat et flou | Au-delà de 135 m, une surface peinte sans arbres | Arbres du jeu sur les versants jusqu'à 430 m : seules leurs cimes dépassent de la surface |
| Bords de route ouverts et clairsemés | Le semis ne compte que les grands arbres ; la route réelle court entre deux murs de végétation de 2 à 5 m | Environ 9 000 petits arbres ajoutés le long des bords, là où le relevé laser montre de la végétation |
| Lignes blanches en aplat pur | Blanc uni | Nos lignes héritent de la peinture de marquage du jeu : usée, bords rongés, fondue dans l'asphalte |
| Béton des parapets gris sombre, dés d'un blanc pur | Teintes de Bollène | Béton éclairci vers le beige, blanc cassé |
| Pierraille claire absente des accotements | Non rendue | Petites pierres calcaires du jeu semées avec l'herbe |
| Grands chênes verts rendus en érables | Essence du jeu mal choisie | Tous les chênes verts prennent l'arbre du jeu à petites feuilles et houppier rond |
| Pistes et sentiers absents | Non rendus | Les pistes, chemins et sentiers de l'IGN sont tracés en terre, dégagés de végétation |
| Poteaux démesurés | Modèle de 9 m à large traverse | Modèle de 6,9 m, mince |
| Rochers alignés | Espacement et taille réguliers | Espacement, taille et enfoncement variés |
| Aires et pistes absentes | Non modélisées | 27 emprises en terre claire, sans herbe ni arbre |

## 3. Ce qu'il faut savoir

- **Deux aperçus hors jeu m'ont servi d'yeux** faute de voir le jeu : l'un montre les formes proches (route, talus, parois), l'autre le paysage (relief lointain avec ses images, arbres en silhouettes). Quinze vues ont été comparées à la reconnaissance, du km 0,4 au km 6,4 : tracé, talus, glissières, parapets et grandes masses d'arbres tombent au bon endroit. Ces aperçus ne montrent ni les matières ni l'éclairage du jeu.
- **Rien de ceci n'a encore été vu en jeu.** Plusieurs réglages sont des choix de teinte faits d'après la couleur mesurée des textures du jeu : ils demanderont sans doute une retouche après essai.
- **Trois paris techniques** dans cette version : nos matériaux désignent des textures du jeu par leur chemin (jamais copiées) ; ils règlent des teintes sur les matériaux du jeu ; la roche hérite d'un matériau de Bollène que le jeu n'emploie lui-même que comme modèle. Si l'un échoue, le sol ou la roche paraîtront gris uni ou d'une teinte inattendue : c'est le premier point à regarder.
- **La largeur de la route n'a pas été touchée.** Sur les images, la chaussée du jeu paraît plus large que la réelle. J'ai vérifié : là où l'asphalte est visible sur la photo aérienne, il mesure 6,4 à 6,8 m, ce que donne aussi l'IGN (6,5 à 7 m) ; le modèle est à 6,2 à 6,5 m. L'impression vient de la caméra (capot dans le jeu, pare-brise sur la vidéo).
- **Le détail de chaque paroi rocheuse est inventé** (bancs, blocs, cassures). Son emplacement, son genre et sa hauteur viennent de la reconnaissance ; sa pente et son pied viennent du relevé laser. Une paroi ne se dresse plus jamais devant un terrain plus bas qu'elle : c'était le défaut des premières versions, vu sur des aperçus hors jeu (`scripts/21_apercu_conducteur.py`).
- **Quatre parois n'arrêtent plus la voiture comme un mur** (km 1,96, 2,00, 2,92 et 3,46) : le terrain ne montait pas derrière le mur de collision, qui aurait été invisible. La voiture y rencontre le talus lui-même. Cinq autres gardent leur mur.
- **Les pièces d'enrobé et les fissures ne sont plus rendues.** Le matériau d'asphalte du jeu sait en dessiner lui-même ; c'est une piste pour plus tard.
- **Pas repris dans cette passe** : la forme des pins (troncs orangés et droits du jeu, contre des pins d'Alep gris et tortueux), l'éclairage du relief lointain, les murets de pierre sèche du km 5,3 à 5,5, les panneaux directionnels.

## 4. Second essai du directeur, le 13 novembre (troisième version)

**Son constat.** Net progrès du décor ; l'herbe courte et verte convient. Restent trois défauts :

| Défaut | Cause | Correction (quatrième version) |
|---|---|---|
| Les lignes blanches ont totalement disparu | J'avais fait hériter nos lignes de la peinture de marquage du jeu : elle ne s'affiche pas sur nos maillages | Retour aux lignes blanches de la première version. L'essai est consigné comme abandonné dans `data/reference/matieres_du_jeu.json` |
| Les bords de l'asphalte zigzaguent (« petit droite, petit gauche ») | Les bords de la chaussée sont lisses dans le modèle (flèche médiane de 3 mm d'un mètre au suivant). Le zigzag venait de ma bande de terre, qui mordait de 3 à 42 cm sur l'asphalte en changeant tous les 25 cm | Bande retirée : le bord de l'asphalte redevient une ligne nette |
| Des arbres débordent encore sur la route | À l'import, chaque arbre recevait au hasard l'un des modèles de sa famille. Or les quinze pins du jeu vont du pin parasol à tronc nu au pin bas, plus large que haut et feuillu jusqu'au sol ; ma règle supposait une largeur unique | La forme de chaque arbre du jeu est mesurée (rayon du feuillage à chaque hauteur). À moins de 14 m de la route, le modèle est choisi pour que rien ne dépasse le bord de la chaussée sous 4,5 m ; au-dessus, le houppier peut surplomber la route de 3 m au plus, comme les pins réels. 11 287 arbres sont posés ainsi ; les grands pins du bord gardent leur taille |

Dans la même version : l'échelle de la texture de roche est réglée sur celle des parois du jeu.

## 5. Troisième essai du directeur, le 13 novembre au soir (quatrième version)

**Son constat** (vidéo fournie). « C'est beaucoup mieux. » Restent : les parois rocheuses proches et surtout lointaines à affiner ; les reliefs à mi-distance, qui « font tas de sable avec une photo de dessus » ; au carrefour du Lion d'Or, un nivellement étrange de la route vers le terre-plein, et pas de lignes au sol.

La vidéo a été calée sur la route d'après la barre de progression du jeu (7 m près), puis comparée à la reconnaissance tous les 40 m.

| Défaut | Cause trouvée | Correction (cinquième version) |
|---|---|---|
| Nivellement étrange au Lion d'Or | La chaussée passe sur un ponceau. Comme pour un pont, le modèle y tirait une ligne droite entre les deux bouts : un palier plat, 15 à 60 cm au-dessus de la vraie chaussée, avec une cassure de pente à chaque bout. Le terre-plein, lui, était au bon niveau | La hauteur de la chaussée sur les ouvrages est maintenant lue dans le relevé laser des surfaces. Au Lion d'Or, l'écart au laser tombe sous 2 cm et les cassures disparaissent |
| Terre-plein blanc et nu | Une nappe à part, d'une teinte unie | Retirée : le terrain qui était dessous porte le sol, l'herbe et les arbres du reste du décor |
| Pas de lignes au Lion d'Or | Jamais modélisées | Ligne axiale continue jusqu'à la pointe de la zone hachurée, zone hachurée (position lue dans le relevé laser), rive gauche continue, rive droite continue le long du terre-plein |
| Bloc de béton sombre à l'entrée du carrefour | Rendu en béton gris | Peint en blanc, comme le vrai |
| Reliefs à mi-distance en « tas de sable » | Au-delà de 140 à 220 m de la route, le relief était une nappe lisse posée à hauteur de cime des arbres, avec la photo aérienne dessus ; trois fois moins d'arbres que près de la route, aucun buisson | Le relief reste au niveau du sol jusqu'à 450 m, avec le détail du relevé laser. Des arbres entiers y sont plantés à la densité mesurée (plus de 200 par hectare), puis moins serrés jusqu'à 650 m ; des buissons couvrent la garrigue |
| Parois rocheuses lointaines molles | Le maillage écrasait les barres rocheuses, et la photo aérienne n'y met que quelques pixels étirés | Maillage deux fois plus fin sur les versants raides, jusqu'à 4 km. À moins de 700 m de la route, les faces très raides sont habillées de la roche du jeu |
| Parois proches gris ardoise | Roche trop sombre à l'ombre | Éclaircie et réchauffée (au soleil elle était déjà beige clair : réglage mesuré) |
| Pointes de roche en forme de tente (km 2, km 4) | Un sommet de roche visible isolé au milieu de voisins enfouis | La roche ne peut plus dépasser nettement son voisinage |
| Terre orange vif sur les talus (km 4, km 6,4) | Teinte trop saturée | Désaturée vers le beige gris |
| Parapets plus sombres que les vrais | Réglage | Pierre et béton éclaircis |
| Route trop ouverte vers le km 5,2 | La vraie route passe entre deux haies ; le modèle plantait trop peu au ras du bord | Un rang serré de végétation basse est ajouté tout près du bord, là où le relevé laser montre une végétation haute |
| Accotement en marches d'escalier | La limite pierraille / herbe suivait une grille de 50 cm | Calculée d'après le bord exact de la chaussée, à la finesse des masques du jeu (34 cm) |

**Deux corrections de la route elle-même**, trouvées en vérifiant le Lion d'Or. Elles ne déplacent rien en plan.

- **Pont du km 5,5** (59 m). Le tablier réel est en creux ; la ligne droite du modèle passait jusqu'à 1,04 m trop haut en son milieu. Le profil suit maintenant le tablier mesuré au laser, à 3 cm près.
- **Ponceau du km 3,45.** L'IGN le place au PK 3443-3450, mais le relevé laser ne montre un vide sous la chaussée qu'au PK 3472-3474. Ses deux parapets sont déplacés de 26 m. La paroi rocheuse qui le suit avait déjà été recalée de 28 m dans le même sens.

## 6. Où c'est décrit

- Écarts relevés : `data/reference/releve_essai_13_11/partie_1.json` et `partie_2.json`. Paires d'images : `scripts/20_planches_comparees.py` (images hors dépôt, `figures/compare_jeu_13_11/`).
- Lissage de la route : `scripts/07b_regulariser_chaussee.py` (réglages et raisons en tête de fichier).
- Parois rocheuses : `data/reference/parois_rocheuses.json`, recalées sur le relief par `scripts/22_recaler_parois.py`, fabriquées par `parois_rocheuses()` dans `scripts/16_paquet_unreal.py`. Aperçu des formes sans le jeu : `scripts/21_apercu_conducteur.py`.
- Relief lointain : `vue_rasante()` et `RASANT` dans `scripts/16_paquet_unreal.py` (`--lointain-rasant 0` pour revenir à la photo éclaircie). Aperçu du paysage sans le jeu : `scripts/23_apercu_lointain.py` (images hors dépôt, `figures/apercu_lointain/`).
- Matières du sol, de l'asphalte, des parapets et de la roche : `data/reference/matieres_du_jeu.json`. Couleur des textures du jeu : `pc/etape2_unreal/outils/couleur_texture.py`.
- Répartition du sol : `scripts/15b_sols_du_jeu.py`. Herbes : `HERBES` dans `scripts/16_paquet_unreal.py`.
- Dégagement des arbres, aires et pistes : `scripts/regles_arbres.py` (`choisir`), `data/reference/aires_et_pistes.json`. Forme des arbres du jeu : `pc/etape2_unreal/outils/profils_arbres.py`, `pc/etape2_unreal/releves/profils_arbres.json`.
- La version vue en jeu le 13 novembre est gardée sur le PC sous `sol_jeu_vu_le_13_11`, avec sa route physique.
