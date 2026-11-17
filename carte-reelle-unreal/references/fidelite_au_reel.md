# Fidélité au réel

« Fidèle » veut dire : l'utilisateur reconnaît le lieu en comparant son rendu à ses photos, à cadrage égal. Tout ce qui suit sert à rendre cette comparaison possible et à ne pas refaire ce qui a déjà été jugé bon.

## Table des matières
1. Hiérarchie des sources
2. Relevé d'objets depuis vidéo et photos
3. Tableau zone → photos → vue de capture → comparaison
4. Fichiers de critères par zone et de demandes de l'utilisateur
5. Priorité aux assets scannés et aux assets du jeu
6. Lire les valeurs sur un niveau existant du jeu
7. Protocole d'essai en jeu
8. Contrôles automatiques avant essai
9. Protection des retouches manuelles de l'utilisateur

## 1. Hiérarchie des sources

Quelle source fait foi pour quoi (en cas de désaccord, la plus haute dans la colonne « fait foi » l'emporte pour cet objet) :

| Source | Fait foi pour | Ne fait pas foi pour |
|---|---|---|
| Repères officiels (points kilométriques, documents de l'organisateur) | positions et distances le long du tracé | coordonnées imprimées sur ces documents (indicatives, écarts de 30-80 m vus) |
| LiDAR (MNT, MNS, nuage classé brut) | toute géométrie physique : relief, talus, ponts et ponceaux (le MNT voit le fond du vallon, le MNS voit le tablier), parapets, hauteurs de toits, cimes d'arbres | sol et sous-bois sous couvert dense (précision 1-2 m), houppiers jointifs, taillis |
| Orthophoto et infrarouge | bords visibles de l'asphalte, emprises, pistes, aires, couleur du sol nu, absence de chlorophylle | sol sous les arbres, ombres, saison, falaises (vue du ciel) |
| Vecteurs (bâti, voies, peuplements) | topologie, emprise des bâtiments, essence d'un peuplement | position exacte de l'axe (médiane 0,7 m, max 4,4 m), hauteurs de bâtiments (écarts > 5 m avec le LiDAR) |
| Photos de terrain | détails, matériaux, couleurs de sol (teinte « éclairée »), textures, mesure de façade en perspective (±5 % avec un repère connu) | positions absolues, dimensions à l'œil, zones à l'ombre (teintes bleutées fausses) |
| Imagerie de rue | abords, enduits, teintes mesurées au soleil et à l'ombre ; la position de prise se lit sur l'adresse affichée | à redistribuer (jamais intégrée, références de forme et de teinte seulement) |
| Vidéo embarquée de reconnaissance (lente, sans public) | décor fixe : parapets, glissières, murs, parois, poteaux, aires, haies, marquage | rayon exact des virages, largeur fine (tranche entre 5 et 9 m, ±15 %), dévers, bosses et profil en long, texte des panneaux, ~60 m avant la ligne de départ |
| Vidéo de course | objets posés pour l'événement (rubalises, panneaux, horloge, cônes, public, véhicules), lignes de départ et d'arrivée | calage grand angle avec tableau de bord dans l'image (échoue) |
| Vue de drone | repérage d'ensemble, images fixes extraites (une image toutes les 12 s) | photogrammétrie lourde : refusée par l'utilisateur ; ne pas la proposer |
| Mémoire de l'utilisateur | vérité terrain contre une photo satellite (« en vérité elle est centrée ») ; ses mots exacts datés priment sur toute description antérieure | ses dimensions « à l'œil » : les fusionner avec les données satellite |
| Niveau existant du jeu | valeurs de matières, couleurs de sommet, densités, physique (voir §6) | l'apparence d'un lieu |
| Essai en jeu (vidéo et captures) | seule référence pour matières, éclairage, ressenti | la couleur et la luminosité si l'écran de l'utilisateur est HDR/OLED |

Règles de lecture :
- Deux vidéos qui se contredisent : permanent → reconnaissance ; posé pour l'événement → course ; différent → course.
- Géométrie ambiguë (carrefour, ouvrage) : LiDAR brut d'abord, images ensuite ; sinon on refait trois fois.
- Les photos priment sur les descriptions plus anciennes ; les mots de l'utilisateur priment sur les photos ; les relevés d'ortho viennent en dernier et se recontrôlent.
- Chaque information porte une confiance : Sûr (~1 m), Estimé (1,5-3 m, hauteurs à l'œil), Pas situé (ne pas poser sans relevé), ou mesuré / vu / estimé / inconnu. Une fiche qui a un point « à trancher » ne sert pas à poser un objet : une seule question précise à l'utilisateur.
- Décrire chaque photo une fois dans un fichier (lieu, direction, ce qu'on voit, sol en détail avec teinte hex « éclairée » = médiane du tiers le plus clair), puis ne plus rouvrir l'image.
- Dimensions : bâtiments par données satellite/LiDAR, détails par photos ; tracer la limite jouable sur la vue satellite avant construction.

## 2. Relevé d'objets depuis vidéo et photos

Où placer un objet vu en vidéo :
- Un objet est au PK de l'image où il SORT DU CHAMP par le côté, pas de l'image où il apparaît au loin (erreurs de 20 à 60 m constatées en notant l'apparition).
- Un relevé fait sur une vidéo « intermédiaire » ne vaut pas un relevé sur la vidéo lisible : refaire (haies et barrières inventées, poteaux comptés 26 au lieu de 96).
- Ne supprimer un objet « incompris » qu'après relecture de la vidéo ; en cas de doute, garder.
- Un panneau cloué sur un tronc exige un tronc à cet endroit ; une rubalise nouée à des arbres absents reçoit un mince piquet.

Calage temps → position :
- Vidéo lente sans glisse : lacet de la caméra par corrélation de phase, aligné sur le cap de la route (Viterbi) ; fiable pour l'ordre et le sens des virages, pas pour corriger un rayon (la glissade fait tourner la caméra sans que la route tourne).
- Vidéo de course (grand angle, échelle fausse) : le calage par les virages échoue ; recaler chaque objet sur des repères fixes sûrs de la reconnaissance (ponts vus au LiDAR, débouchés), garder la valeur lue à côté de la valeur recalée, ne recaler qu'une fois.
- Vidéo du jeu : lire la barre de progression (étalonnée sur deux instants sûrs, ±7 m) ; ne pas s'en servir pour placer des objets si elle est en avance (jusqu'à 30 m).
- Le tangage d'une caméra n'est pas le profil en long : pas de contrôle des compressions par vidéo.

Faire relever par un agent :
- Imposer un schéma JSON, joindre un exemple de chaque fichier cible, exiger `source`, `confiance`, ancienne valeur gardée à côté, `non_poses` / `a_verifier` pour l'illisible.
- Donner des planches d'images ciblées (une image tous les 6 m autour d'une paroi, des paires jeu/reconnaissance tous les 40 m) plutôt que la vidéo entière.
- Relevé par repère de façade (s le long, t vers la cour) depuis un angle ; hauteurs en fraction de l'égout ; incertitudes chiffrées.
- Pour une photo prise d'un point connu : position de prise lue sur l'adresse de l'imagerie de rue → coordonnées projetées → projection sur l'axe ; objets placés par croisement de visées.
- Contrôle final : redessiner tous les relevés sur l'orthophoto (cohérence ≈ 1 m) ; vérifier l'orientation face à la photo (erreur de miroir constatée).

## 3. Tableau zone → photos → vue de capture → comparaison

Un tableau de correspondance, une ligne par zone (une quinzaine dans le projet de référence) :

| Zone | Photos qui font foi (fichiers nommés) | Vue de capture (numéro, point de vue fixe) | Dernière comparaison | État daté |
|---|---|---|---|---|

- Une zone n'est « conforme » que si l'utilisateur l'a dit.
- Un point de vue fixe par zone (position en cm du repère de la carte, lacet en degrés) sert de contrôle visuel reproductible ; les vues « à la pose de la photo » (pose calculée par point de fuite et focale connue, capture à 90° puis recadrage) permettent la comparaison à cadrage égal.
- Comparaison : réel à gauche, rendu à droite, numéro et nom de fichier, légende ; la regarder, noter les écarts un par un, chercher la CAUSE, corriger, recapturer, seulement alors passer au point suivant.
- Pour retrouver la cause d'un détail inexpliqué : masquer une famille d'acteurs à la fois, une image par famille ; identifier ce qui est derrière un pixel.
- Le tableau est tenu à jour à chaque passe ; il évite de rouvrir des photos déjà rattachées (une vingtaine restaient « à compléter »).

## 4. Fichiers de critères par zone et de demandes de l'utilisateur

Fichier de demandes (la fin = le plus récent) :
- Chaque message de l'utilisateur est consigné avec ses mots exacts, daté à la minute, sans reformulation ; à côté, une « lecture du coordinateur (à vérifier) » si le texte est dicté ou ambigu.
- Les retours arrivés dans la mauvaise conversation sont recopiés dès qu'on les repère ; les messages hors sujet (autre projet, compte) ne sont pas des consignes.
- Noter son vocabulaire (un mot peut désigner un objet précis) pour ne pas le « traduire ».

Fichier de critères par zone :
- Section « valable partout » : interdits globaux (blocs unis, plantes plates en 2D, masses de feuillage lisses, essences hors région, motif de texture répété, matériaux brillants ou mouillés, éléments inventés) et le code couleur de ses annotations de captures.
- Une section par zone : « jugé » (ce qu'il a dit, daté), « validé / NE PLUS TOUCHER », règles datées (« une seule carte de travail »), ce qu'il attend à chaque passe (statuts très courts, images, avis honnête).
- Ses critères de validation : « pas de bug, pas de vide graphique → on laisse comme ça ».

Liste « ne plus toucher » :
- Placée en tête de chaque brief de constructeur ; elle protège contre les régressions (bardage, falaise, abri jugés réussis puis refaits).
- Une exception à la liste vient de l'utilisateur lui-même, jamais du constructeur.
- Une zone se finit (façade, herbe, finitions) avant de passer à la suivante.

Ordre de lecture à une reprise : critères → état/à faire → fin des demandes → fiches photos ; ne pas lire les scripts (c'est le travail du constructeur).

Au démarrage, poser en une fois les questions manquantes (contour exact, interdits, assets autorisés, seuil d'arrêt, référence visuelle avec échelle), puis ne plus interrompre pour des choix mineurs.

## 5. Priorité aux assets scannés et aux assets du jeu

- Règle de l'utilisateur, répétée : « assets scannés partout, plus de matériaux peints ni d'objets fabriqués en code » ; « même si ce n'est pas la vraie texture, quelque chose de cohérent, de détaillé, presque photoréaliste ». Un constructeur qui fabrique des objets malgré des assets téléchargés fait perdre du temps et des jetons.
- Ordre de préférence : (1) asset du jeu posé par chemin, mesuré ; (2) asset scanné ou de banque, importé et mesuré ; (3) objet fabriqué en code seulement si rien de convenable n'existe (pierres anguleuses, poteau d'un modèle absent du jeu), l'exception étant écrite.
- Avant de poser : taille de fichier (les bouchons font ~17 Ko), format importable, bornes, nombre de triangles, présence de logos, licence (libre, attribution à créditer, usage personnel à vérifier avant tout mod public) ; la liste des assets fabriqués est tenue pour pouvoir supprimer les inutilisés.
- Si un objet n'existe nulle part (table, camion, pelle), le dire et poser un substitut signalé comme écart ; ne pas télécharger de payant.
- Une photo peut devenir une texture (photo de falaise recadrée, raccordée par miroir et fondu, dé-éclairée, relief tiré de la luminance) ; ne jamais poser une orthophoto telle quelle sur le sol.
- Le réalisme vient du désordre contrôlé (chutes, outils, cartons, palettes cassées), avec mesure : trop surcharger est une erreur, laisser vides les endroits vides.

## 6. Lire les valeurs sur un niveau existant du jeu

À relever dans les archives avant toute valeur (un script régénérable, une minute) :
- paramètres des matériaux du jeu (interrupteurs statiques, textures, teintes), variantes de matière, couleurs de sommet des murs et sols ;
- hauteurs réelles et rayons de feuillage des maillages d'arbres, couleur moyenne des textures, image d'ensemble de chaque essence ;
- densités et types de décalques, de débris, d'herbes sur un niveau du jeu de même type de lieu ; orientation des panneaux (lacet) ;
- physique complète d'un niveau de même surface (matière, ligne idéale, humidité, météo), classes d'acteurs, réglages moteur (Nanite, textures virtuelles, éclairage).

Règles : ne jamais inventer une valeur de matière, densité ou physique ; partir de la valeur du jeu puis ajuster d'après essai et consigner la valeur jugée bonne avec date et lieu ; mesurer la teinte d'une texture du jeu plutôt que la deviner ; chaque nouveau parent de matériau s'essaie sur 200 m ; les essais abandonnés sont consignés avec « ne pas réessayer sans comprendre pourquoi ».

## 7. Protocole d'essai en jeu

Avant l'essai :
- tous les contrôles hors jeu verts (§8) ; version précédente gardée ; jeu fermé ; accord de l'utilisateur pour installer ;
- une version = un essai ; nom de version qui dit si elle a été vue en jeu ou non ; versions gardées avec leur physique et une commande de retour arrière ;
- prévoir un essai de réception avec les valeurs déjà calibrées, puis un second pour retouches : viser peu d'essais.

À demander au joueur :
- mode de jeu simple, véhicule et réglages connus, adhérence/réglages identiques à ceux d'un niveau de référence ;
- vidéo de TOUT le parcours (départ arrêté compris) ; si possible le même tronçon sur le niveau de référence pour comparer ;
- captures pour chaque défaut, avec position (repère ou PK) et côté ; les captures de la plateforme de jeu sont lues par un petit modèle ;
- réponses courtes sur une liste fixe : chargement et sens ; matière du sol, météo ; départ/arrivée et objets de l'épreuve ; chrono ; notes ; ressenti ; murs invisibles, trous, sorties ; relief lointain, falaises, parois ; sol, herbe, débris ; arbres et objets sur la chaussée, flottants ou enterrés ; fidélité du départ et de l'arrivée ; fluidité.

Exploitation :
- chaque capture : où et vers où (déduit, pas lu sur une coordonnée), défauts par type (végétation, sol, échelle, face manquante, forme fausse, enfoncé, flotte, matériau, reflets, éclairage), « réussi » ; synthèse par gravité avec colonne VU / SUPPOSÉ pour la cause ;
- ordres de correction vérifiables (avec capture de contrôle) ; tableau « défaut précédent → état (corrigé vu / amélioré / inchangé) » à chaque série ;
- regrouper les constats PAR CAUSE (une cause = une constante ou un relevé), corriger les données puis les constantes, rejouer les contrôles, faire UNE construction ;
- jamais corriger la luminosité d'après ses captures ; elles servent aux bugs de texture, pixelisation, formes trop géométriques, manque de fondu ;
- ne dire « installé » ou « corrigé » qu'après constat en jeu ou sur capture ; marquer « jamais vu en jeu » sinon.

Quand l'essai est impossible (le jeu n'affiche plus les cartes ajoutées) : parcourir la carte dans l'éditeur à hauteur d'homme, jamais en désactivant une protection du jeu.

## 8. Contrôles automatiques avant essai

À écrire dès la première construction, avec un bilan court et un rapport JSON qui fait foi (le code de sortie ne fait pas foi) :
- collisions fantômes : tirs de rayons verticaux sur une grille (8 m, 1 m dans la zone jouable), contre la collision simple ET complexe ; tout impact > 40 cm doit être légitime (toit, tronc, rocher) ; alerte si le joueur « marche dans les airs » ;
- objets flottants (> 8 cm) et enterrés (> 0,5 m) : correction automatique « écart + 2 cm » ; véhicules : boîte + 30 cm ; portails, balustres hors contrôle à traiter à part ;
- relief : écart relu 0,00 cm (ou 1,5 cm si la plateforme arrondit) ; comptes d'acteurs et d'instances comparés au paquet ;
- chaque règle de placement (dégagement des arbres, distance aux murs, porte-à-faux de la roche : zéro sommet en porte-à-faux) a son contrôle chiffré ;
- matériau assigné et texture par défaut pour chaque bâtiment ; textures noires = matériau non assigné ;
- relecture du niveau cuit avec les archives du jeu : chemins, instances, maillages désignés, parents de matériaux, couleurs de sommet, éléments factices absents du conteneur, référence des cellules, « relecture conforme » ;
- visibilité : un contrôle porte sur ce que le joueur voit (acteur caché par une étiquette, matériau qui ne s'affiche pas), pas sur le fichier ;
- aperçus hors jeu (profondeur ou nuage de points) pour juger formes, raccords, relief lointain : ils ne montrent ni matières ni éclairage ; mesure de luminosité par script sans ouvrir l'image ;
- placement physique/décor décalé de 0,0 cm à viser à chaque version ; déterminisme : deux constructions identiques donnent un diff nul, donc pas de revalidation visuelle de ce qui n'a pas changé ;
- ce qui n'a pas été contrôlé est écrit dans le rapport (liste d'alertes non relue, jeu non lancé).

## 9. Protection des retouches manuelles de l'utilisateur

- Copie éditable dont le chemin n'est jamais réécrit par les scripts ; la carte générée est une autre copie, lanceurs distincts (« ma copie », « dernière version générée », « refaire la copie depuis l'original »).
- Avant toute reconstruction : date du fichier de niveau ; s'il a été retouché, construire sous un autre nom ; ne pas reconstruire tant que l'éditeur de l'utilisateur est ouvert ; lui rappeler d'enregistrer.
- Inventaire du niveau avant/après sa retouche (acteurs, positions) et décisions de l'utilisateur rejouées à chaque construction ; ses couches installées font foi : les copier vers le dépôt avant de régénérer.
- Ne plus relancer un générateur de relief ou de terrasses qui efface le terrain sculpté ; recaler les objets au sol par script idempotent ; ne jamais fermer ni tuer une session d'éditeur de l'utilisateur ; vérifier qu'aucun éditeur n'est ouvert avant une opération qui écrit dans le projet.
- Instances groupées : documenter la méthode de dégroupage pour qu'il puisse déplacer un seul objet ; regrouper ensuite ; sauvegarder avant toute opération lourde ; restaurer depuis le dépôt si un monde est écrasé.
- Ne jamais présenter comme vérifié ce qui ne l'a pas été ; ne jamais inventer un format, un chemin ou un identifiant : s'appuyer sur un fichier réel ou l'index des ressources du jeu.
