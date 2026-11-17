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

## 6. Pneus, et relevé complet de la quatrième version (13 novembre au soir)

**Pneus (demande du directeur).** Le jeu rangeait la spéciale en « terre » et ne proposait que des pneus terre. Cause : elle remplace une spéciale galloise, dont la ligne dans la table des spéciales du jeu dit « Gravel » et « GravelOnly ». Les spéciales sur asphalte du jeu disent « Tarmac » et « TarmacSnow ».

- **Premier essai, sans effet en jeu.** J'ai livré la table corrigée dans le mod de la route physique, après avoir vérifié qu'aucun autre mod n'était installé. Je n'avais regardé que le dossier `~mods`. Or deux mods sont installés directement dans le dossier `Paks` du jeu : la spéciale BioBio et un « registre » (`pakchunk99-SandoRegistry_2_P`) qui livre la même table. Le jeu ne garde qu'une table, celle du mod le mieux classé : c'était la sienne.
- **Solution retenue par le directeur.** Notre table part de celle du registre, et seule notre ligne y change (asphalte, pneus asphalte, 6,74 km au menu). Elle est livrée dans un petit fichier à part, `zz_acrxs_grandcaunet_table_9_P`, dont le nom le classe devant le registre. Relu dans les conditions réelles (jeu, registre, BioBio et notre fichier) : notre ligne est en asphalte, les 47 autres sont identiques à celles du registre. C'est une exception, autorisée pour cette seule table, à la règle « aucun fichier BioBio réutilisé ».
- **À savoir.** Si le registre est mis à jour ou retiré, il faut refaire notre fichier (`pc/scripts/6_table_asphalte.ps1`), sinon il figerait l'ancienne table. La matière physique de la chaussée était déjà de l'asphalte. **Confirmé en jeu par le directeur le 13 novembre au soir** : la spéciale apparaît en asphalte, avec les bons pneus.

**Relevé systématique.** Les 167 paires d'images (jeu à gauche, reconnaissance à droite, tous les 40 m) ont été lues une à une : 161 écarts notés (`data/reference/releve_essai_13_11_v4/`). Les défauts qui reviennent tout le long, et leur correction dans la sixième version :

| Défaut récurrent | Cause | Correction |
|---|---|---|
| Feuillages teintés de mauve et de rose | L'arbre du jeu pris pour les chênes verts et le sous-bois est un arbre à perruque | Remplacé par un arbuste dense vert sombre du jeu ; un tiers des grands chênes prend un feuillu jaune, comme les chênes roussis de novembre |
| Touffes et taches d'un noir pur | Feuilles mortes et plantes rampantes du jeu, rendues en noir | Retirées |
| Accotement d'herbe verte absent (une vingtaine de paires) | Un liseré de pierraille grise de 85 cm bordait l'asphalte | Liseré réduit à un filet de 40 cm, herbe verte plus dense et plus vive jusqu'au bord |
| Parois trop hautes, décalées de 20 à 40 m, ou posées sur un simple talus | Premier relevé fait au PK où la roche s'apercevait, pas où elle se trouve | Toutes les parois relues sur la reconnaissance, une image tous les 6 m (voir ci-dessous) |
| Talus de rocaille rendus en dalles grises ou en murailles | Tout était rendu par un maillage de roche | La rocaille n'a plus de maillage : le sol y est peint en pierraille et semé de pierres calcaires |
| Rochers ronds isolés le long des rives | Rochers sombres du jeu | À reprendre (non fait) |
| Poteaux jumelés en A | Modèle du jeu mal choisi | Poteau simple |
| Tirets de l'axe trop espacés dans les virages | Même trait partout | Traits rapprochés dans les virages (rayon sous 140 m) |
| Parapets « à lisse blanche » | Couronnement peint en blanc | Couronnement en béton gris, seuls les dés restent blancs |
| Pinède du km 4,5 au km 4,9 rendue en feuillus touffus | Le sous-bois était planté partout où le laser mesure de la végétation, y compris sous les pins | Peu de sous-bois sous un couvert haut ; de grands pins à tronc dégagé au ras de la route là où le laser montre la pinède |
| Aires de stationnement en terre brune | Matière | Gravier clair |

**Relecture des parois rocheuses.** Pour chacune des 43 parois et de 6 talus signalés, une planche d'images de la reconnaissance, une vue tous les 6 m, a été lue en notant le PK où la roche arrive à hauteur de la voiture. Résultat : 24 parois de roche en place (738 m) et 61 talus de rocaille (1 843 m), au lieu de 43 parois (1 729 m) ; hauteurs revues, le plus souvent à la baisse. Le calage de la reconnaissance, en avance de 0 à 24 m selon l'endroit, est corrigé d'après vingt repères connus par ailleurs (ponts du relevé laser, débouchés de pistes de l'IGN). Les cinq derniers murs de collision cachés sous des parois sont retirés : les emprises ayant changé, ils ne correspondaient plus à rien.

**Sixième version : construite, relue, installée le 13 novembre à 21 h 10.** Relecture du décor cuit conforme (aucune erreur, aucune alerte) : 24 parois de roche (42 207 triangles), 4 545 pierres calcaires sur les 61 talus de rocaille, 103 grands pins de bord de route, 515 254 objets en tout. Route physique reconstruite avec la table asphalte ; décalage entre la route et le décor : 0,0 cm. Rien de tout cela n'a encore été vu en jeu. La cinquième version est gardée (`sol_jeu_cycle5_du_13_11`).

**Préparé pour la septième version (données seulement, rien de construit ni d'installé).** Le reste du relevé de la reconnaissance (glissières, murets hors pont, poteaux, panneaux, rochers, lisses, aires, rubans du rallye) est recalé comme les parois : 201 objets déplacés de 0,5 à 23 m, valeur lue gardée à côté (`scripts/25_recaler_objets_reco.py`). Le carrefour du Lion d'Or et les objets déjà déplacés à la main ne bougent pas. À vérifier au prochain passage de la chaîne : le raccord de la glissière du PK 3246 avec le parapet du pont 3229. Constat sur les « blocs gris-rosé » des accotements : ce sont les pierres calcaires du jeu, dont la texture est beige rosé assombrie ; piste retenue, non commencée : fabriquer nos propres pierres anguleuses avec notre matière de roche claire, pour les accotements, la rocaille et les blocs isolés.

**Non traité, relevé pour la suite** : glissières réelles fermées par un écran bas (celles du jeu sont à jour dessous) ; murs de pierre sèche des km 3,72, 4,08 et 5,3 à 5,5, trop sombres ou en retrait ; quelques arbres trop près dans les zones ouvertes du km 6 ; rochers ronds isolés.

## 7. Où c'est décrit

- Écarts relevés : `data/reference/releve_essai_13_11/partie_1.json` et `partie_2.json`. Paires d'images : `scripts/20_planches_comparees.py` (images hors dépôt, `figures/compare_jeu_13_11/`).
- Lissage de la route : `scripts/07b_regulariser_chaussee.py` (réglages et raisons en tête de fichier).
- Parois rocheuses : `data/reference/parois_rocheuses.json`, recalées sur le relief par `scripts/22_recaler_parois.py`, fabriquées par `parois_rocheuses()` dans `scripts/16_paquet_unreal.py`. Aperçu des formes sans le jeu : `scripts/21_apercu_conducteur.py`.
- Relief lointain : `vue_rasante()` et `RASANT` dans `scripts/16_paquet_unreal.py` (`--lointain-rasant 0` pour revenir à la photo éclaircie). Aperçu du paysage sans le jeu : `scripts/23_apercu_lointain.py` (images hors dépôt, `figures/apercu_lointain/`).
- Matières du sol, de l'asphalte, des parapets et de la roche : `data/reference/matieres_du_jeu.json`. Couleur des textures du jeu : `pc/etape2_unreal/outils/couleur_texture.py`.
- Répartition du sol : `scripts/15b_sols_du_jeu.py`. Herbes : `HERBES` dans `scripts/16_paquet_unreal.py`.
- Dégagement des arbres, aires et pistes : `scripts/regles_arbres.py` (`choisir`), `data/reference/aires_et_pistes.json`. Forme des arbres du jeu : `pc/etape2_unreal/outils/profils_arbres.py`, `pc/etape2_unreal/releves/profils_arbres.json`.
- Pneus : `pc/scripts/6_table_asphalte.ps1` (lancé par l'option `-Asphalte` de `pc/scripts/4_construire.ps1`), `pc/scripts/pneus_asphalte.py`.
- Relevés du quatrième essai : `data/reference/releve_essai_13_11_v4/`. Relecture des parois : `scripts/24_planches_parois.py`, `data/reference/releve_parois_v2/`, `data/reference/parois_rocheuses.json`. Calage corrigé de la reconnaissance : `scripts/calage_reco.py`, `data/reference/calage_reco_reperes.json`.
- Rocaille : `regles_arbres.rocailles()`, `pierraille_des_talus()` dans `scripts/16_paquet_unreal.py`.
- Les versions vues en jeu sont gardées sur le PC (`sol_jeu_vu_le_13_11`, `_bis`, `_ter`), chacune avec sa route physique.

## 8. Après l'essai de la sixième version (13 novembre au soir)

Retour du directeur : le jeu tourne sans souci ; « il y a encore du travail à faire sur l'aspect visuel et, à certains moments, la route est un peu trop bosselée ». Il a fourni la vidéo du test et quatre captures du relief lointain.

**Ce qui a été fait de cette vidéo.**

- Calée sur la route d'après la barre de progression du jeu (`scripts/19b_calage_barre.py`, qui mesure aussi les secousses de la caméra, tous les 10 m).
- 167 paires d'images jeu / reconnaissance, tous les 40 m, la reconnaissance étant désormais prise à son PK corrigé (`scripts/20_planches_comparees.py`). Toutes lues : 324 écarts notés (`data/reference/releve_essai_13_11_v6/`).

**La route bosselée.** Mesuré sur le profil : l'axe portait des bosses et des creux de 2 à 4 cm sur 4 à 8 m (PK 1655, 2600, 3073, 5578…), soit 1 à 2 g à 90 km/h ; le dévers sautait par endroits (bout du pont du PK 4470 : de +8 % à −2 % en 4 m). C'est le grain du relevé laser et des raccords entre sources, pas la route réelle. Les secousses de la caméra désignent les mêmes endroits. Correction (`scripts/07b_regulariser_chaussee.py`, étape 3 ter) : altitude de l'axe lissée sans s'écarter de plus de 5 cm du relevé, dévers lissé à 2 % près, valeurs aberrantes écartées.

| À 90 km/h, en g | Avant (écart-type / maximum) | Après |
|---|---|---|
| Axe | 0,17 / 1,1 | 0,04 / 0,23 |
| Bord gauche | 0,37 / 4,2 | 0,05 / 0,53 |
| Bord droit | 0,42 / 4,3 | 0,06 / 0,77 |

**Défauts visuels relevés, causes trouvées, corrections de la septième version.**

| Défaut (nombre de paires) | Cause trouvée | Correction |
|---|---|---|
| Touffes d'un noir pur (44) | Deux herbes du jeu (plantain, herbe sauvage : 24 000 touffes) prennent leur couleur dans une texture du niveau gallois d'origine, que notre sol n'alimente pas | Retirées, remplacées par des herbes saines |
| Blocs ronds gris-rosé sur les talus et les accotements (55) | Pierres et rochers du jeu : leur texture est beige rosé assombrie, et ils ne peuvent pas être réglés | Pierres et blocs calcaires fabriqués par le projet (`scripts/pierres_calcaires.py`), anguleux, dans notre roche claire, plus petits et plus nombreux |
| Parois beiges en grandes dalles lisses, ardoise à l'ombre, dessus bruns | Clarté trop faible, teinte chaude, motif de 5 m, couche de terre du matériau du jeu sur les faces du dessus, voile sombre | Roche éclaircie et presque neutre, motif de 3 m, terre du dessus et voile réduits |
| Murets « brun moussu ou noirs », béton strié | La couleur de sommet dosait moitié mousse ; voile sombre du matériau du jeu | Pierre seule, voile éclairci, béton plus clair |
| Sol brun nu sous les pins, pentes nues « en dunes » | Litière d'aiguilles partout ; le semis place un arbre par cime, un taillis n'a pas de cimes | Herbe sous les arbres ; un arbuste là où le laser voit un taillis de 2 à 7 m sans arbre ; buissons bas sous les pins |
| Couloir du km 5,1 à 5,4 ouvert (haies à 3 à 5 m) | Aucun arbuste du jeu ne tenait à moins de 1,6 m du bord | Trois rangs de haie dès 0,9 m du bord, là seulement (`data/reference/bords_vegetation.json`) |
| Buissons collés à la route ailleurs, haies sur le plateau du km 5,8 à 6,7 | Sous-bois semé dès 1,7 m du bord partout | Bande d'herbe de 2,6 m ; bords relevés comme ouverts éclaircis (décor et physique) |
| Poteaux « béton » en bois sombre et épais, gros câbles noirs | Le modèle choisi était un poteau de bois ; câbles de 4 cm | Fût de béton clair du jeu ; câbles de 1,6 cm |
| Aires et accotements de gravier gris ou brun sombre | Teinte du fond pierreux | Gravier éclairci vers le beige |
| Falaises lointaines en taches pâles et floues, sommets « enneigés » | Teinte unie trop étalée ; rocher nu vu du ciel presque blanc sur la photo | Falaises plus blanches, plus nettes, rayées de strates ; plateaux ramenés vers la teinte de la garrigue |
| Mur de soutènement sombre à l'épingle du km 4,08 | Relevé à tort comme un mur | Retiré : c'est le talus de bancs calcaires, déjà rendu en roche |

**Septième version : construite, relue, installée le 14 novembre à 2 h 35.** Relecture du décor cuit conforme (aucune erreur) : 531 maillages dont 7 modèles de pierres, 556 286 objets (515 254 dans la sixième), dont 9 161 pierres sur les talus de rocaille, 16 799 sur les accotements, 99 blocs isolés, 1 441 sujets de haie et 20 601 arbustes de fourré ; 145 arbres retirés des bords relevés comme ouverts. Route physique reconstruite, table asphalte refaite, décalage route / décor de 0,0 cm. À surveiller : l'éditeur Unreal s'est arrêté sur une erreur d'accès à la fermeture, après avoir tout enregistré (rapport de construction complet, cuisson et relecture conformes) ; à revoir si cela se reproduit. Rien de tout cela n'a encore été vu en jeu ; la fluidité avec 41 000 objets de plus n'est pas mesurable hors jeu. La sixième version est gardée (`sol_jeu_vu_le_13_11_soir`).

**Déjà préparé pour la suivante (données seulement)** : aires de stationnement des PK 436, 1474 et 6368 et parapet gauche du ponceau du PK 4571, recoupés avec le relief laser.

**Non traité, relevé pour la suite** : troncs des pins rouge-orangé (c'est le pin du jeu ; les vrais sont gris) ; pas de voûte de branches au-dessus de la route (elle s'oppose à la règle « rien ne déborde sur la chaussée ») ; îlots du Lion d'Or bordurés en dur ; panneaux directionnels (pas d'équivalent dans le jeu) ; aires manquantes ou étroites aux PK 440, 1480, 5040 et 6360 ; mur de pierre sèche du PK 3720 trop court ; écran bas sous les glissières ; enrobé un peu foncé, fissures trop marquées.

**Où c'est décrit** : lissage en long, `scripts/07b_regulariser_chaussee.py` ; pierres, `scripts/pierres_calcaires.py`, `ROCAILLE` et `HERBES` dans `scripts/16_paquet_unreal.py` ; bords de route, `data/reference/bords_vegetation.json`, `scripts/regles_arbres.py`, `SOUS_BOIS` et `FOURRE` dans `16_paquet_unreal.py` ; matières, `data/reference/matieres_du_jeu.json` ; chaîne Unreal complète, `pc/etape2_unreal/scripts_pc/chaine_decor.ps1`.

## 9. Après l'essai de la septième version (14 novembre, 2 h 35)

Retour du directeur : reliefs lointains à retravailler « pour une impression moins géométrique » ; parois rocheuses et leur intégration au bord de la route ; touffes d'herbe à l'horizontale sur des talus à 45 degrés ; « n'as-tu pas trop lissé la route ? Garder un ressenti réel de route non parfaite, mais enlever les bosses non réelles et trop fortes » ; un panneau de rallye sur un piquet à l'extérieur d'un virage à droite est-il fidèle ? Il a aussi fourni 24 captures Street View de la zone avant le départ, à modéliser. Consignes de travail : installer chaque version dès qu'elle est prête, continuer sans test, confier les tâches simples à des agents sur un modèle moins gourmand.

**Relevés faits (par des agents sur Opus).** Vidéo du test calée et comparée à la reconnaissance (`data/reference/releve_essai_14_11_v7/constats.json`, 42 constats) ; inventaire géolocalisé de la zone de départ (`data/reference/zone_depart.json`) ; relecture de la reconnaissance sur douze endroits (`data/reference/relecture_reco_v8.json`).

**Huitième version : construite, relue conforme, installée le 14 novembre à 7 h 09.** 552 maillages, 585 693 objets (556 286 dans la septième). Route physique reconstruite, décalage route / décor de 0,0 cm. Rien n'en a encore été vu en jeu ; la fluidité avec 29 000 objets de plus n'est pas mesurable hors jeu.

| Remarque | Cause trouvée | Correction |
|---|---|---|
| Route trop lissée | Le lissage retirait tout ce qui fait moins de 25 m de long : 0,04 g d'à-coups à 90 km/h, une chaussée parfaite | La route reprend les trois quarts de l'écart mesuré (ondulations de plus de 6 m), écrêté à 1,5 cm : 0,08 g en moyenne, 0,42 g au plus (0,17 et 1,1 à l'origine) |
| Touffes d'herbe à plat sur les talus | Touffes posées droites, sans suivre la pente | Couchées sur la pente (133 833 touffes), raréfiées sur les pentes raides |
| Panneau sur piquet à l'extérieur d'un virage à droite | PK 2614, à gauche : la vidéo de course le montre cloué sur un tronc de pin, que notre semis d'arbres n'avait pas | Un pin planté derrière lui. À l'épingle du km 4,08, le mur de pierres sèches qui porte deux autres panneaux est rétabli (je l'avais retiré à tort dans la septième version) |
| Relief lointain géométrique | Un seul modèle de pin, semis régulier, arrêt net à 650 m ; versants beiges sous les arbres ; falaises en grands triangles plans ; teinte de falaise sur des versants boisés | Quinze pins différents, hauteurs et largeurs variées, frange qui se raréfie par plaques jusqu'à 880 m (157 629 arbres) ; images lointaines plus vertes, mouchetées de houppiers ; faces de roche recoupées en 16 et bosselées, jusqu'à 1 100 m (16 446 faces) ; teinte de calcaire seulement sur le rocher nu |
| Parois proches en gradins, trop propres | Bancs épais, longs blocs, sommet régulier, pied sur un sol nu | Bancs de 18 à 42 cm, blocs de 0,5 à 1,5 m, sommet irrégulier, pierres au pied ; roche moins blanche au soleil et moins bleue à l'ombre |
| Parapets « brun-vert, comme de la mousse » | La couleur de sommet dose la mousse dans le sens inverse de ce que j'avais cru : blanc = mousse | Couleur de sommet noire : pierre seule |
| Zone avant le départ vide | Jamais modélisée | Parking du Grand Caunet et deux aires, long mur enduit, mur de pierres sèches, mur de soutènement, entrée de propriété (rampe, pilier, portail, monolithe), lisse basse, trois barrières, dix bâtiments en volumes simples (`scripts/12_carrefours_annexes.py`, section « constructions de la zone de départ ») |

**Erreurs connues de la huitième version, corrigées dans les données pour la neuvième** : au pont du PK 2602, parapet gauche retiré et parapet droit allongé à 22 m, alors que la relecture montre un parapet gauche de 5 m et un droit de 10 m. Les douze corrections de la relecture (parapets des ponts 1661, 2602 et 2777, murs des PK 3722, 4079 et 5358 à 5508, treize poteaux déplacés et sept ajoutés, six aires) sont dans les données, pas encore construites.

**Non traité** : cédez-le-passage, poteaux directionnels, miroir et panneau de la forêt de la zone de départ (pas d'équivalent dans le jeu) ; portique d'arrivée rendu vert uni ; poteaux qui paraissent bleu sombre à contre-jour ; une retouche des notes du copilote au PK 3173 qui ne s'applique plus.

**Outils ajoutés** : `pc/scripts/7_tout_refaire.ps1` (données, route physique, chaîne Unreal et relecture d'un trait), `pc/etape2_unreal/scripts_pc/chaine_decor.ps1`, `scripts/19b_calage_barre.py`.

**Neuvième version : construite, relue conforme, installée le 14 novembre à 8 h 28.** C'est la huitième, plus les douze endroits de `data/reference/relecture_reco_v8.json` : 553 maillages, 585 907 objets, route physique reconstruite, décalage route / décor de 0,0 cm. Jamais vue en jeu. La huitième est gardée (`sol_jeu_cycle8_du_14_11`).

**Préparé pour la dixième (données seulement).** Relecture systématique de la reconnaissance pour tous les murs, parapets, glissières, clôtures et aires pas encore relus (`data/reference/relecture_reco_v9.json`, 80 objets) : 39 entrées corrigées ou ajoutées (treize murs et parapets, quatre glissières, quinze aires et pistes, six clôtures et barrières). Règle suivie : là où le relevé laser montre le vide d'un pont ou d'un ponceau, il l'emporte sur la lecture vidéo, précise à 5 m au mieux ; cinq corrections de parapets de pont et celle du ponceau final (que la vidéo plaçait 20 à 30 m avant le creux du relief) ne sont donc pas appliquées. Mon déplacement à la main du parapet gauche du ponceau du PK 4571 est défait : deux lectures de la vidéo le replacent à 4554-4563.

**Dixième version : construite, relue conforme, installée le 14 novembre à 9 h 46.** C'est la neuvième, plus les 39 corrections de position de `data/reference/relecture_reco_v9.json`. Route physique reconstruite, décalage route / décor de 0,0 cm. Jamais vue en jeu. La neuvième est gardée (`sol_jeu_cycle9_du_14_11`).

**Onzième version : construite, relue conforme, installée le 14 novembre à 11 h 54.** Défaut trouvé dans les versions 8 à 10 : les arbustes semés d'après la seule hauteur du relevé laser (fourré des versants, sous-bois de bord) ignoraient les bâtiments et les murs ; 342 étaient plantés dans des bâtiments ou des constructions de la zone de départ, 280 à moins d'un mètre d'un mur. Ils sont écartés (`regles_arbres.emprises_interdites`, `hors_du_bati` dans `16_paquet_unreal.py`). Un contrôle hors jeu du placement des objets a relevé 36 anomalies ; les douze plus graves sont corrigées dans les données (champ « controle ») : quatre poteaux (au ras de la chaussée, dans un mur, dans une paroi, au-dessus du vide d'un pont), deux troncs suspendus au-dessus du pont du PK 5554 retirés, blocs pris dans une paroi ou un mur, borne dans un mur, glissière recouvrant un mur. Restent à juger : quatre poteaux posés dans des aires, cinq objets perchés ou enterrés de 1,5 à 1,9 m. Jamais vue en jeu. La dixième est gardée (`sol_jeu_cycle10_du_14_11`).

## 10. Après l'essai de la onzième version (14 novembre, midi)

Retour du directeur : « dans l'ensemble nous sommes sur la bonne voie », avec six captures de bugs graphiques (non exhaustives) et une remarque : « la barrière verte sur le chemin à droite du départ est mal axée ». Relevé de sa vidéo par un agent : `data/reference/releve_essai_14_11_v11/constats.json` (68 constats, aucun de gravité 3 ; les touffes d'herbe suivent bien les pentes).

| Défaut | Cause trouvée | Correction (douzième version) |
|---|---|---|
| Grande dalle verte au départ, portique vert uni à l'arrivée | Portiques que dessine le constructeur de la route physique (deux poteaux de 5 m et une bannière, matière verte unie du jeu), même là où notre décor remplace le reste | Enterrés : `pc/scripts/4_construire.ps1` passe une copie de la configuration avec une hauteur négative |
| Barrière de la piste GC 107 mal axée | Posée le long de la piste ; noire au lieu de verte | En travers de la piste, à l'endroit montré par Street View, vert sombre |
| Long mur de l'approche en béton sombre, en deux morceaux ; volumes de la zone de départ sans matière | Murs de béton du jeu ; couleurs unies | Mur enduit clair continu du PK -140 au PK -86 ; crépi, tuiles, portail, pierre en textures ; dessus des murs réguliers ; monolithe refait |
| Poteaux électriques en caissons bleu-noir | Aucun poteau du jeu ne convient | Poteau de béton du projet (`scripts/pierres_calcaires.py`) : fût effilé de 8,2 m, traverse, isolateurs |
| Tête de ponceau en dalle penchée (PK 6091) | Les deux biseaux se rejoignaient | Biseau limité à 30 % de la longueur de l'ouvrage |
| Falaises lointaines en dômes lisses, bord en dents de scie, arbres sur la roche ; colline tachetée | Relief à 5 m au-delà de 650 m ; texture dépliée à 2,5 m ; moucheté d'une seule taille | Relevé laser à 2 m jusqu'à 2 km ; texture dépliée à 17,5 m ; bord adouci ; arbres retirés au-delà de 40 degrés ; grain à trois échelles plus discret |
| Roche, murs et talus gris bleuté | Teinte trop neutre | Teinte réchauffée, talus de rocaille plus terreux |

**Douzième version : construite, relue conforme, installée le 14 novembre à 17 h 04.** Route physique reconstruite, décalage route / décor de 0,0 cm. Jamais vue en jeu. À surveiller : la roche lointaine compte deux fois plus de triangles qu'avant. La onzième est gardée (`sol_jeu_vu_le_14_11_midi`).

**Non traité** : un « tas » clair près de l'entrée du parking, d'origine inconnue ; l'emprise réservée aux arbres le long du mur enduit suit un recul fixe (0,5 m d'écart vers le PK -86).

## 11. Après l'essai de la douzième version (14 novembre, 17 h 15)

Retour du directeur : reliefs lointains nettement améliorés, jeu fluide. À revoir : couleurs des murs et bâtiments de la zone de départ, parking « bac à sable », commissaires et décor de course au départ et à l'arrivée, parois de bord de route plus détaillées, parapets en trop ou mal raccordés, deux « immenses parapets » à la place de parois (sortie du Lion d'Or, épingle du km 4,08), branche barrée du Lion d'Or inexistante, défauts de sol aux ponts. Relevé des captures : `data/reference/releve_essai_14_11_v12/murs.json`.

**Treizième version : construite, relue conforme, installée le 14 novembre à 19 h 32.** Murs de pierre sèche des PK 3722-3756 et 4079-4105 rendus en parois de roche litée (collision gardée en mur invisible) ; trois parapets corrigés (PK 1960, 5600, 6091) ; tablier des ponts 10 cm sous la chaussée et au gris de l'enrobé ; parois proches deux fois plus fines, avec un grain d'arêtes ; zone de départ recolorée d'après Street View, parking en gravier à grain avec ornières et neuf voitures ; véhicules et décor de course au départ, au poste radio du PK 6502, à l'arrivée et au Lion d'Or ; branche fermée du Lion d'Or prolongée de 140 m en enrobé ; arbres et herbe exclus des routes annexes (le code comparait des degrés à des mètres). Jamais vue en jeu.

**Commissaires et public** : étude dans `docs/15_commissaires_et_public.md`. Consigne du directeur : utiliser les personnages du jeu, ne jamais en créer. Méthode retenue pour la quatorzième version : déplacer les 4 commissaires et 6 spectateurs du niveau persistant de Hafren South vers nos positions, par une retouche du constructeur de la route physique.

## 12. Après l'essai de la treizième version (14 novembre, 20 h)

Retour du directeur : zone de départ et route barrée du Lion d'Or encore insuffisantes ; aucun personnage (normal : version construite sans) ; voitures sans texture ; rien ne matérialise la zone de départ (zone rouge translucide des spéciales du jeu) ; panneau de fin de spéciale en hauteur ; parois encore géométriques et « en suspension », surtout en travers (roche trop avancée au-dessus du vide). Consigne : utiliser les personnages et éléments du jeu, ne pas en créer ; s'appuyer sur les caméras embarquées du rallye.

**Quatorzième version : construite, relue conforme, installée le 14 novembre à 22 h 41.**
- Commissaires et public : les 10 personnages du parc d'assistance de Hafren South déplacés sur la spéciale par la retouche `pc/patches/0005-personnages.patch` du constructeur (option `-Personnages`) ; contrôle « 10 sur 10 à leur place ».
- Zones de départ et d'arrivée : la zone rouge est la boîte du déclencheur du jeu, que le constructeur déplace bien ; nos options de visuels la supprimaient. `4_construire.ps1` ne passe plus d'options de visuels avec notre décor (portiques verts supprimés du même coup). Deux panneaux de départ du jeu et deux cônes posés.
- Véhicules : leurs matériaux refusent la pose en instances (le jeu cuit leur substituait le matériau par défaut) ; posés en acteurs individuels comme le fait le studio.
- Zone de départ : enduits et monolithe hérités des matériaux de mur et de roche du jeu ; parking aplani (`scripts/aplanissements.py`, appelé par `08_modele_3d.py` et `mobilier.py`).
- Lion d'Or : branche fermée noire à cause d'un dépliage en coordonnées Lambert-93 (au-delà de ce que le moteur stocke) ; corrigé, avec un contrôle dans 16 ; murets du ponceau prolongés jusqu'au fond du ruisseau.
- Panneau de fin de spéciale ramené au pied du talus.
- Parois : roche posée sur le terrain (85 % des sommets visibles étaient en porte-à-faux, jusqu'à 2,3 m au-dessus du vide ; contrôle hors jeu à zéro), jupe sous terre, cinq rangs par banc : 491 691 triangles (143 410 avant).

## 13. Après l'essai de la quatorzième version (15 novembre, 0 h 45)

Retour du directeur : personnages absents ; bugs de parapet ; un mur invisible à l'intérieur de l'épingle du Lion d'Or, au niveau des piquets à droite de la route ; asphalte de la branche barrée toujours mal fait.

**Quinzième version : construite, relue conforme, installée le 15 novembre à 3 h 29.**
- Personnages : ils portaient l'étiquette `ServicePark`, que le jeu cache pendant une spéciale (les commissaires du studio le long des spéciales n'en ont pas). La retouche 0005 la neutralise ; contrôle « 10 sur 10 à leur place, aucun étiqueté ServicePark ».
- Mur invisible : murs de reprise du jeu (limites qui ramènent la voiture sur la route), tracés par le constructeur à 20 m au-delà du bout de chaque porte ; au Lion d'Or, les bouts de porte très obliques ramenaient la limite dans le terre-plein, à 4-5 m des piquets. `09_export_stage_ir.py` redresse ces bouts de porte (PK 3656-3700) : limite à plus de 15 m de la chaussée. Les piquets de rubalise n'ont plus de collision.
- Branche barrée : enrobé relevé au niveau du tablier du ponceau, raccord sans marche avec le prolongement, qui suit ensuite le terrain.
- Parapets : PK 6091 (tête refaite en travers), 4062 (alignement), 3637 (collision rétablie), 4462 et 5565 (léger retrait, doublon supprimé), 5320 (muret abaissé), 6676-6684 (parapet inexistant retiré). Relevé : `data/reference/releve_essai_15_11_v14/`.

## 14. Détails de la chaussée et parc d'assistance (15 novembre)

Demande du directeur pendant son essai de la quinzième version : amélioration globale des détails (feuilles ou autres sur l'asphalte, sans toucher à la physique, avec les éléments du jeu) ; pas de parc d'assistance au chargement ; clignotants allumés sur certains véhicules garés.

- **Parc d'assistance** : étude dans `docs/16_parc_assistance.md`. Le jeu cache toujours le parc pendant une spéciale ; nos retouches ne le retirent pas (459 de ses 479 acteurs intacts), mais il reste à son emplacement gallois, à 2,1 km de notre départ, en l'air au-dessus de notre paysage. Essai en jeu demandé au directeur avant de le déplacer (zone plate d'environ 93 × 125 m nécessaire).
- **Seizième version : construite, relue conforme, installée le 15 novembre à 18 h 15.** Habillage de la chaussée comme sur les spéciales goudronnées du jeu (Bollène, Sisteron) : 385 décalques du jeu (terre et débris, aiguilles de pin, gravillons, terre aux débouchés de pistes, ornières, gomme, traces de pneus) posés en acteurs de décalque, et 5 765 feuilles mortes du jeu à plat sur l'enrobé ; décor seul. Feux des véhicules garés éteints par la variante « feux éteints » du jeu, comme le fait le studio (les trois monospaces avaient leurs feux de détresse allumés) ; contrôle dans `relire_decor.py`. La route physique n'a pas été reconstruite (jeu ouvert pendant la fabrication) : celle de la quinzième, inchangée, est gardée. Jamais vue en jeu.

**Essai de la seizième version** : feux des véhicules bien éteints (confirmé par le directeur) ; « trop de débris, et parfois non pertinents » ; parc d'assistance toujours absent (précision demandée : l'écran s'affiche-t-il ?). **Dix-septième version, installée le 15 novembre à 22 h 22** : densité de l'habillage réduite à environ un tiers, plus de terre aux débouchés des petits chemins de l'IGN ; relecture conforme ; route physique reconstruite, identique à la précédente. Jamais vue en jeu.

## 15. Essai de la dix-septième version (16 novembre)

Retour du directeur : encore trop de débris (feuilles mortes, « taches au sol »), pas assez de traces de pneus ; parc d'assistance présent dans Hafren Nord mais pas dans notre spéciale ; commissaires comparés à ceux de Hafren Nord (position, animations) ; la voiture sous-vire et manque d'adhérence par rapport à Munster (même voiture, mêmes réglages, même adhérence de départ). La pénalité « départ anticipé » de 10 s venait du pilote, pas du mod.

- **Débris** (`scripts/16_paquet_unreal.py`) : feuilles mortes retirées (5 837 dans la dix-septième), litière ramenée à 2,5 groupes par km, une boîte au plus par aire et un décalque par débouché, chacun gardé quatre fois sur dix. Traces de pneus en sortie de tous les virages de moins de 40 m de rayon et plus de 60 degrés, en plus des épingles. Bilan : 102 décalques (8 débris, 11 aiguilles, 12 gravillons, 4 terre, 14 ornières, 14 gomme, 39 traces de pneus), au lieu de 151 décalques et 5 837 feuilles.
- **Physique** : la chaussée porte déjà la seule matière asphalte du jeu (PM_SurfaceTarmacSmooth), et la ligne de la table des variantes est classée comme les spéciales asphalte du jeu (Tarmac, TarmacSnow). Écart restant : la ligne gardait la météo galloise (WeatherConfig = Wales, 4 °C affichés), alors que Bollène a MonteCarlo et Munster Alsace. `pneus_asphalte.py --meteo MonteCarlo` (appelé par défaut par `6_table_asphalte.ps1`) change ce seul renvoi. Si le sous-virage persiste, pistes non vérifiées : le masque de débris de la matière asphalte (canal UV 5, courbe FC_TarmacGripDebrisCurve), absent de notre maillage de collision.
- **Parc d'assistance** : l'écran s'affiche, mais le parc reste à son emplacement gallois, hors de notre décor. Déplacement proposé plus tard (champ à 365 m du départ, près de la D3).
- **Commissaires** : ceux du parc sont déplacés (méthode A). Les officiels animés de la séquence de départ et d'arrivée sont dans deux cellules cachées du jeu (méthode B, `docs/15_commissaires_et_public.md`) ; proposé plus tard.

**Dix-huitième version, installée le 16 novembre à 23 h 15** : construite en 83 min, route physique sans échec, table relue conforme (surface Tarmac, pneus TarmacSnow, météo MonteCarlo, 6,737 km, les 47 autres lignes identiques), relecture du décor conforme. L'éditeur Unreal se ferme sur une erreur d'accès (code -1073741819) après la construction, comme dans plusieurs versions précédentes, sans effet sur le résultat. La dix-septième est gardée sous `sol_jeu_vu_le_16_11`. Jamais vue en jeu.

## 16. Essai de la dix-huitième version (17 novembre) : adhérence, officiels, parc, zone de départ

Retour du directeur : les effets au sol sont bons ; la voiture sous-vire toujours, « comme si l'asphalte n'avait pas assez de grip » (la température affichée était encore de 4 °C ; la changer à la main n'a presque rien apporté) ; demande d'intégrer le parc d'assistance (« très réduit et sommaire, sur la route avant la spéciale si besoin ») et les commissaires animés ; défauts graphiques de la zone de départ (mur mal raccordé, arbre au travers d'un mur).

### 16.1 Enquête sur l'adhérence

Comparaison de notre route physique avec Munster (spéciale asphalte du jeu), dans les données du jeu (`acr-ref export`, analyses dans `Z:\acrxs\construction\phys_cmp`) :

| Point | Munster | Nous | Verdict |
|---|---|---|---|
| Matière physique de la chaussée | PM_SurfaceTarmacSmooth | la même | identique |
| Couleurs physiques (canaux lus par la matière, dont « débris ») | une valeur par collisionneur, (0,0,0,1) | la même | identique |
| Autre matière au-dessus de l'asphalte (herbe, gravier) | — | 8 m² de gravier à 1-4 cm au-dessus, sur 50 800 m² | négligeable |
| Rugosité (écart à la surface lissée sur 1 m) | 10 mm | 4 mm | la nôtre est plus lisse |
| Dévers | vers l'intérieur | vers l'intérieur, 6,5 à 7 % sous 60 m de rayon (relevé laser) | réaliste |
| Ligne de la table des variantes (surface, pneus, usure, secteurs) | Tarmac, TarmacSnow | les mêmes | identique |
| **Ligne idéale (IdealSpline)** | suit la trajectoire : 0,6 à 0,8 m vers l'intérieur des virages (médiane), couloir de 150 à 330 cm de chaque côté sur une demi-chaussée de 2,2 m, intensité de gomme (SkidIntensity) 0,2 en médiane, 0,7 sous 30 m de rayon | **notre axe**, couloir fixe de 150 cm de chaque côté sur une demi-chaussée de 3,3 m, **SkidIntensity nulle partout** | **écart** |
| **Humidité de base du niveau** (acteur météo) | aucune | **0,1** (celle de Hafren Sud, niveau hôte) | **écart** |
| Température de référence du lieu (DT_Tracks) | 30 °C | 5 °C (pays de Galles ; Bollène aussi 5 °C) | à comparer plutôt avec Bollène |

La ligne idéale appartient au module physique du jeu : l'acteur qui la porte (SplinesActor : FastLane, MainSpline, IdealSpline…) est construit dans dmphysics (`acr.exe`, fonction en 0x1450455F0), et les réglages physiques globaux (`DA_PhysicsGlobalSettings`) prévoient une largeur de ligne idéale, un bonus de gomme sur la trajectoire (`MarblesGrooveK` 0,08) et des « billes » qui retirent de l'adhérence hors trajectoire. Notre constructeur recopiait l'axe dans la ligne idéale : dans un virage pris à la corde, la voiture sortait du couloir propre et ne profitait d'aucune gomme. C'est la seule différence de physique trouvée qui explique un manque d'adhérence partout, surtout en virage.

**Corrections (retouche `pc/patches/0006-ligne-ideale.patch` du constructeur, `scripts/09_export_stage_ir.py`) :**

- **Ligne idéale** : `ligne_ideale()` calcule une trajectoire à courbure minimale entre les bords de chaussée, à 1,2 m au moins des bords, rappelée vers l'axe dans les lignes droites, écart plafonné à 2,5 m (carrefour du Lion d'Or). Résultat : écart à l'axe médian 0,4 m (Munster 0,47), 1,9 m vers l'intérieur sous 30 m de rayon (chaussée de 6,5 m contre 4,4 m à Munster), couloir jusqu'à 20 cm des bords (150 à 340 cm), SkidIntensity selon le rayon comme Munster et Hafren (médiane 0,24). Écrite dans `stage.json → ideal_line`, lue par le constructeur.
- **Humidité de base** : `--level-wetness 0` (défaut de `4_construire.ps1 -HumiditeNiveau`) remet à 0 le `global_wetness` de l'acteur météo du niveau persistant (un flottant réécrit sur place).

Si le sous-virage persiste : comparer avec **Bollène** (même température de référence, 5 °C) plutôt qu'avec Munster (30 °C) ; puis essayer un départ « adhérence optimale ».

### 16.2 Officiels animés du départ et de l'arrivée (méthode B de `docs/15`)

Option `--officials` (`4_construire.ps1 -CellulesOfficiels`, passée par `7_tout_refaire.ps1`) : les cellules `A0I1…` (départ) et `0QY7…` (arrivée) de Hafren Sud sont extraites, gardées dans le sens aller et rendues toujours chargées ; chaque acteur est reporté le long de notre route à la même distance de son repère (point d'apparition de la voiture, déclencheur de départ, zone d'arrêt), à la même distance du **bord** de la route (notre chaussée est plus large), posé sur notre sol (au plus 25 cm au-dessus), tourné avec la route. Départ : l'officiel assis (Doc) et 2 commissaires au point d'apparition, le commissaire au bâton (séquence de départ, avec ses déclencheurs « Start » et « ComeCloser ») et 3 commissaires à la ligne. Arrivée : l'officiel au portable, le commissaire d'arrêt, 5 commissaires, 6 groupes de public et leurs bruits. Les portiques gallois « Rally Wales » sont enfoncés de 1 000 m.

### 16.3 Parc d'assistance réduit

Option `--service-park 1` (automatique quand `stage.json → service_park` existe) : les 164 acteurs du parc à moins de 8 m du point de la voiture (sa tente, son mobilier) sont posés au PK −47, à l'embouchure du parking du Grand Caunet (3 m à gauche de l'axe), voiture dans l'axe de la route ; le reste du parc gallois (295 acteurs) et son sol de 3 × 3 km sont enfoncés de 1 000 m ; son ambiance sonore, l'occultation de la pluie, l'exclusion PCG et les éoliennes restent en place. Le jeu cache le parc pendant la spéciale : il ne gêne pas la route. Arbres, arbustes et herbes sont écartés d'un disque de 11 m autour de la voiture (`regles_arbres.parc_assistance`).

### 16.4 Zone de départ

- Tronc de pin dans le portail : les grands arbres du semis s'écartent désormais des constructions de la zone de départ et des murs de bord de route (seul le sous-bois le faisait) ; marge portée de 1 à 2 m.
- Mur de la rampe rendu comme un panneau lisse et bleuté : enduit vieilli (nuances, salissures, lichen) au lieu du crépi crème uni.
- Touffes d'herbe sur la rampe béton : les constructions de la zone de départ sont retirées de l'emprise des herbes.

**Dix-neuvième version, installée le 17 novembre** : construite en 83 min, route physique sans échec (ligne idéale, humidité 0, parc et officiels relus PASS), table conforme, relecture du décor conforme ; 49 arbres du semis écartés des murs et constructions. La dix-huitième est gardée sous `sol_jeu_vu_le_17_11`. Vue en jeu le 17 novembre (section 17).

## 17. Essai de la dix-neuvième version (17 novembre, captures `essaiev18`)

Retour du directeur : la tenue de route est un peu meilleure, il la veut « encore un peu plus prononcée » ; le parc d'assistance doit être sur le parking à côté du départ, pas à moitié dessus ; l'officiel n'apparaît pas ; quelques branches dépassent encore du mur au départ. Les captures montrent aussi deux pneus qui flottent au bord de la route, au départ.

### 17.1 Officiels absents : la grille de chargement

Aucun personnage des cellules A0I1 et 0QY7 n'est visible au départ : seul le commissaire de la méthode A (niveau persistant) l'est. Le drapeau « toujours chargée » (`bIsAlwaysLoaded`) posé par la dix-neuvième version ne suffit pas : un World Partition cuit charge les cellules des cases de sa grille autour de la caméra. `MainGrid` a des cases de 350 m et une portée de 640 m. A0I1 est dans la case de niveau 0 du départ gallois, à (−875 ; 875) m, soit 2,1 km de notre départ. Notre arrivée, en X = −2 518 m, est même hors du monde gallois (X min −1 529 m) : aucune case ne la couvre.

Le niveau 5 de la grille est une seule case sur tout le monde, donc toujours à portée. On y trouve les cellules de jeu (22VG, 1LS8) et des cellules du sens retour. Correction (`Officials.cs`, retouche 0006) : chaque cellule des officiels échange sa référence dans le hachage spatial (`WorldPartitionRuntimeSpatialHash`, un entier de 4 octets, taille inchangée) avec une cellule du niveau 5 qui ne se charge jamais dans le sens aller (calques retour seuls : 7FF9 pour le jeu retour, BGX4 pour les décors retour). Les officiels sont alors chargés partout. La cellule donneuse passe dans la case galloise, où son calque inactif la laisse déchargée. La relecture vérifie la référence.

### 17.2 Adhérence

- Le jeu a cinq niveaux d'adhérence de surface (`DA_PhysMaterialsMappingCommon`, asphalte) : Optimal 1,0, Fast 0,92, Green 0,88, Slow 0,86, Dirty 0,85. Hors trajectoire, l'adhérence descend d'un niveau (Optimal → Fast). Le niveau de départ est une **option de météo du joueur** (« Starting Grip Level », `DA_StartingGripOption`), pas une donnée de la spéciale. Elle n'est pas dans la sauvegarde : le jeu prend sa valeur par défaut. **Passer cette option à « Optimale » vaut jusqu'à +13 % d'adhérence par rapport à « Green ».** C'est le premier réglage à faire en jeu.
- Côté spéciale : le couloir de la trajectoire couvre désormais toute la chaussée (`couloir_garde_m` 0, bornes 1,5 à 6 m). La gomme (`SkidIntensity`, bonus `MarblesGrooveK` 0,08 × intensité) est celle d'une route très roulée : 0,5 en ligne droite, 1 en épingle, au lieu des moyennes de Munster et Hafren (0,2 et 0,8).

### 17.3 Parc d'assistance sur le parking

- La tente est posée au point du parking du Grand Caunet le plus éloigné de ses bords, des voitures garées de notre décor (3,5 m de garde) et du mobilier (1 m). C'est le pôle d'inaccessibilité de l'emprise de `zone_depart.json`, avec 11,9 m de dégagement pour 8 m de rayon. La voiture est tournée vers l'entrée principale (PK −60).
- Les deux pneus flottants viennent de `BC_TiresRack_C`. Le jeu cache le présentoir avec le parc pendant la spéciale, mais pas les pneus qu'il fait apparaître comme acteurs à part. Le présentoir est retiré du parc réduit (`ServiceParkSinkClasses`).
- La retouche 0006 enregistrée ne contenait pas `ServicePark.cs`. Elle est régénérée et vérifiée sur une copie neuve d'ACR Extra Stages : appliquée après 0001 à 0005, elle redonne exactement nos fichiers.

### 17.4 Branches à travers les murs

Jusqu'ici, seul le tronc des arbres était écarté du bâti (2 m des constructions, 1 m des murs). Désormais, la place d'un arbre est la plus petite de deux distances : au bord de chaussée et au mur ou bâtiment le plus proche (`regles_arbres.distance_au_bati`). La règle du houppier s'y applique (`choisir` : rien ne dépasse sous 4,5 m, un surplomb de 3 m au plus au-dessus). Un arbre trop grand pour sa place est réduit, ou retiré s'il deviendrait trop petit. Environ 160 arbres sont concernés. La physique applique la même règle : les troncs retirés du décor près du bâti n'ont plus de collision.


**Vingtième version, installée le 17 novembre** : construite en 82 min, route physique sans échec. Les deux cellules d'officiels sont échangées avec les cellules 3H10 et 7FF9 du niveau supérieur de la grille et relues PASS « referenced in the top grid level ». Le parc d'assistance est déplacé au milieu du parking (164 acteurs, 295 enfoncés, le râtelier de pneus compris), relu PASS. La ligne idéale compte 932 points. Table et décor relus conformes. 47 arbres du semis et 353 du bord de route sont écartés du bâti et des murs ; 791 arbres sont réduits pour ne pas déborder. La dix-neuvième est gardée sous `sol_jeu_vu_le_17_11_bis`. Pour l'essai, mettre « Adhérence de départ » sur Optimale dans les options météo. Jamais vue en jeu.

### 17.5 Arbres du build 18 hors de la zone de départ

Le directeur demande que le reste de la spéciale garde les arbres du build 18 et que seule la zone de départ change. Or les builds 19 et 20 avaient étendu deux règles à toute la spéciale : l'écart des troncs du semis aux murs et la tenue du houppier hors des murs. Il y avait un second effet, moins visible. Le sous-bois, le fourré et les orientations des arbres sont tirés au sort à la suite, dans l'ordre des places retenues. Une seule place de plus écartée au départ, à cause de la marge des constructions portée à 2 m ou du parc d'assistance, décalait donc le tirage sur toute la spéciale. Hors du départ, le sous-bois des builds 19 et 20 différait de celui du build 18 aux PK 174 à 7 214.

Correction :
- Les deux règles ne regardent que les murs de la zone de départ (`regles_arbres.ZONE_DEPART_PK_MAX_M` : tronçons finis avant le PK 0, soit le mur de pierres sèches et le long mur enduit, PK −163 à −86).
- `16_paquet_unreal.vegetation_de_bord` tire la végétation deux fois, avec les règles du build 18 puis avec les règles actuelles. Le décor prend la première au-delà du PK +30 (`ZONE_DEPART_ARBRES_PK_MAX_M`) et la seconde en deçà. Les lacets du build 18 sont tirés comme avant, donc la suite du tirage est inchangée.

Vérifications faites avec le code du build 18 repris de git, sur les mêmes données :
- au-delà du PK +30, les 73 512 sujets sont identiques (position, hauteur, maillage, lacet) et la suite du tirage aussi ;
- en deçà du PK +30, il y a 1 677 sujets contre 1 709 au build 18 ;
- les troncs de la physique ne diffèrent qu'entre les PK −165 et −86.

**Vingt et unième version, installée le 17 novembre** : la vingtième, avec les arbres du build 18 au-delà du PK +30 (section 17.5). Construite en 83 min. Route physique ALL PASS (officiels, parc d'assistance, ligne idéale de 932 points), table conforme, relecture du décor conforme. Le journal confirme 73 512 sujets du build 18 et 1 677 sujets de la zone de départ, ainsi que 1 153 troncs dans la physique. La vingtième, jamais vue en jeu, est gardée sous `sol_jeu_cycle20_du_17_11`. Pour l'essai, mettre « Adhérence de départ » sur Optimale. Jamais vue en jeu.

**Vingt-deuxième version, installée le 17 novembre au soir** : la vingt et unième, rangée dans son propre rallye (`docs/19_rallye_propre.md`).
- Au menu Essai libre, le rallye « Sainte Baume Rallye » porte le drapeau français, une plaque faite avec les logos du roadbook et une photographie aérienne en fond. Il contient la spéciale « Le Grand Caunet ». Le pays de Galles ne garde que Hafren Sud inverse.
- Le conteneur des tables livre cinq tables, relues conformes. Le décor a été recuit avec la plaque et le fond (relecture conforme). La route physique est celle du build 21.
- En parallèle : `docs/18_asphalte_parametres_non_reglables.md` recense ce qui agit sur l'adhérence de l'asphalte.
- La vingt et unième est gardée sous `sol_jeu_cycle21_du_17_11`. La vingt-deuxième n'a jamais été vue en jeu.

**Vingt-troisième version, installée le 17 novembre au soir** : la vingt-deuxième avec une météo d'été, sur décision du directeur (`docs/18`, § 18.5). La variante passe de la configuration météo MonteCarlo à Alsace (`6_table_asphalte.ps1 -Meteo`, défaut Alsace). Notre spéciale tire son temps comme l'Alsace et prend 30 °C de température de référence, comme Munster (`rallye_grand_caunet.json`). Seul le conteneur des tables change, relu conforme ; le décor et la route physique sont ceux du build 22. La vingt-deuxième est gardée sous `sol_jeu_cycle22_du_17_11`. Jamais vue en jeu.
