# Économie de tokens

## Table des matières
1. Choix du modèle par tâche
2. Scripts qui résument, fichiers qui détaillent
3. Ne jamais charger de gros fichiers
4. Fichiers de reprise et d'état
5. Un coordinateur léger, un seul constructeur, une conversation par livrable
6. Briefs à citer
7. Sous-agents bornés
8. Un seuil unique de fenêtre d'usage
9. Réveils programmés
10. Ce qui a coûté cher inutilement (chiffres notés)
11. Ordre de grandeur du coût d'une passe

## 1. Choix du modèle par tâche

| Tâche | Modèle | Pourquoi |
|---|---|---|
| Lire des fichiers, chercher sur le web ou dans un dépôt, décrire ou comparer des images, relever des objets sur planches, analyser des captures de jeu (lecture seule), inventorier, paqueter et installer selon une procédure écrite | petit (famille haiku) | tâche bornée et vérifiable ; cinq recherches web ≈ 0,06 USD contre plusieurs dizaines pour le grand modèle sur la même recherche |
| Travail courant : coordination, rapports, scripts de contrôle, paquetage, corrections de zone bien décrites | moyen (famille sonnet) | assez fort pour suivre un brief, bien moins cher |
| Problème dur (diagnostic de cause, conception d'un algorithme de terrain ou de végétation, arbitrage entre sources contradictoires), constructeur de carte sur un brief neuf | grand (famille opus) | une erreur coûte une construction de 1-2 h ou un essai en jeu |

- Le grand modèle ne lit pas les images de relevé : il donne la consigne, les planches, le fichier cible et un exemple de schéma, puis ne lit que le JSON rendu.
- Changer de modèle au milieu d'une conversation relit tout le contexte au prix fort : fenêtre d'usage de 0 à 46 % en 18 minutes constatée. Changer à une frontière de passe, dans une conversation neuve.
- Si le quota d'un modèle est presque plein (semaine à 95-99 %), basculer le constructeur sur un autre modèle avec les instructions déjà prêtes plutôt que d'attendre ; l'utilisateur l'autorise en général explicitement.
- Les tâches annexes ne reçoivent jamais « un gros agent » : l'utilisateur l'a demandé expressément ; le travail sur la carte reste soigné, efficace et optimisé.

## 2. Scripts qui résument, fichiers qui détaillent

- Toute étape de calcul est un script numéroté, rejouable (`--depuis`, `--jusqua`, `--seulement`, `--liste`), qui imprime un bilan de quelques lignes et écrit le détail dans un fichier (rapport JSON). On ne réécrit pas sa logique dans la conversation.
- Chaque script écrit aussi ses contrôles ; certains refusent d'écrire si un invariant est cassé (virage dénaturé, etc.).
- Filtrer les journaux par motifs (erreurs, `FAIL`, lignes de bilan), ne lire que les dernières lignes, tronquer les lignes longues ; une construction de plus de 2 minutes part en arrière-plan, sans sondage actif ; ne pas utiliser d'attente en avant-plan.
- Les contrôles automatiques remplacent des images : rayons de collision, flottants, relief, mesure de luminosité d'un PNG sans l'ouvrir, comptes d'acteurs ; l'œil arrive après.
- Faux module du moteur et banc d'essai isolé : tester la logique d'un script d'éditeur hors éditeur (ne prouve pas l'API), valider un asset ou le lointain en 10-25 s sans reconstruire la carte.
- Un paquet se fabrique pendant que l'éditeur importe le précédent ; ne reconstruire le moteur que si le paquet a changé ; ne reposer que le niveau (3 min) si seul le niveau change.
- Constructions déterministes : pas de revalidation visuelle de ce qui n'a pas changé.

## 3. Ne jamais charger de gros fichiers dans le contexte

- Pages d'historique ou sorties d'outils de 0,3 à 11 Mo (la plupart en résultats d'outils inutiles) : les enregistrer dans un fichier et les lire par script en filtrant (messages tapés seulement) ; ne jamais les relire en entier.
- Images : peu d'images dans le contexte du coordinateur, ne pas rouvrir une image déjà décrite (description écrite dans un fichier), réduire à ~1 400 px avant lecture, au plus 10-14 images de contrôle par agent.
- Fichiers d'état et de demandes de 50-100 Ko : résumé de tête, archivage des passes anciennes, sommaire « où trouver quoi » ; ne lire que le haut et la fin.
- Scripts de 200-480 Ko : ne pas les lire en entier ; chercher par mots-clés ; le coordinateur ne lit pas les scripts du tout.
- Données volumineuses (rasters, nuages de points, archives du jeu) : jamais dans le contexte ; seulement le bilan imprimé par le script.

## 4. Fichiers de reprise et d'état

- Pour repartir dans une conversation neuve sans perdre les critères : fichier unique « à lire en premier », fichier de critères par zone, fichier d'état et de suite (le haut = le plus récent), fin du fichier des demandes (mots exacts datés), fiches photos, tableau zone → photos → vue → comparaison, sommaire « où trouver quoi ».
- Chaque document ouvre par son état et finit par « où c'est décrit ». Les consignes vivent dans des fichiers versionnés (brief de la passe, demandes, critères), pas seulement dans le chat.
- Une note de reprise précise : version et commit de départ, ce qui est vu en jeu et ce qui ne l'est pas, hypothèses (marquées), seuil d'arrêt, quel modèle fait quoi.
- Lecture de reprise du constructeur : dix minutes au plus, puis agir.
- Valeurs calibrées consignées avec date, lieu et raison (commentaires datés dans les scripts, fichier de matières, fichier de valeurs) : le projet suivant part de ces valeurs. Essais abandonnés consignés.
- L'utilisateur accepte une conversation neuve seulement si elle est plus efficace ; il refuse un redémarrage qui perd les critères : la continuité des critères vaut plus que la fraîcheur du contexte. Nouvelle conversation dès que le contexte dépasse la moitié (un contexte à 90 % de 1 M de jetons précède une compaction).
- Fichier de reprise après coupure de quota : écrire l'état d'arrêt (ce qui est fait, ce qui reste, commit poussé) dès l'avertissement de limite, puis vérifier que le push a réussi.

## 5. Un coordinateur léger, un seul constructeur, une conversation par livrable

- Coordinateur (conversation principale) : lit critères, état, demandes ; décrit les photos ; consigne les mots de l'utilisateur ; écrit le brief du jour ; relit quelques comparaisons clés et donne un avis honnête ; statuts très courts. Il ne lit pas les scripts.
- Constructeur : UN seul à la fois, sous-agent au contexte neuf, modèle fort ; il reçoit le brief ; trois messages au plus au coordinateur par passe, une ligne par point abouti ; un commit par point (fichiers précis) ; met à jour l'état en fin de passe ; rapport de 20 lignes au plus : fait et vu / fait non vérifié / non fait et pourquoi / trois défauts restants.
- Tâches annexes (recherche, images, inventaire de nettoyage, paquetage) : modèle léger, en lecture seule quand c'est possible, consigne « n'invente rien, rapporte les contrôles non faits ».
- Un seul constructeur lourd à la fois : le travail se découpe en points ordonnés dans le brief, pas en agents parallèles.
- Une conversation par livrable (carte, installeur, autre projet) : une demande d'un autre projet est signalée et renvoyée ; une conversation neuve coûte moins qu'une session de plusieurs jours dont l'historique est relu à chaque tour (au moins 10 arrêts de limite en 4 jours) ; les rôles ne se mélangent pas (coordinateur, constructeur, paqueteur).
- Le coordinateur décide seul des choix mineurs et envoie les images ; il ne demande pas à l'utilisateur d'aller voir sur son PC.

## 6. Briefs à citer

Un brief de passe contient, dans cet ordre :
1. en-tête : source (photos + mots de l'utilisateur), état de départ (versions, commit), lectures obligatoires, durée de lecture bornée ;
2. liste « ne plus toucher » ;
3. un point par élément : citation exacte des mots de l'utilisateur, photo de référence nommée, séquence réelle (ordre des éléments d'une façade), méthode de mesure, fiche à refaire si approximative, contrôle (capture au même point de vue, côte à côte) ;
4. règles d'exécution : lire l'usage avant chaque construction, seuil d'arrêt, nombre de messages, commit par point, ne rien toucher hors périmètre, pas de paquetage si c'est le rôle d'un autre ;
5. fin de passe obligatoire : version jouable et version éditable, lanceurs vérifiés, état mis à jour, rapport.

Citer les mots de l'utilisateur évite les reformulations qui dérivent ; nommer les photos évite de les chercher sur le disque.

## 7. Sous-agents bornés

- Chaque consigne fixe : durée de lecture, nombre d'appels d'outils ou de tours, nombre de messages, longueur du rapport (12 à 50 lignes), liste AUTORISÉ / INTERDIT, arrêt des processus lancés par soi-même.
- La limite écrite dans la consigne ne suffit pas : des sous-agents l'ont dépassée (200 000 jetons en 9 minutes) ; la fixer aussi dans le suivi, et arrêter l'agent à la main s'il dérive.
- Pas d'agent en attente : un sous-agent qui attend son propre travail d'arrière-plan émet des notifications identiques et consomme (5 notifications, ~244 000 jetons, 95 appels). Lui faire remonter une question courte ou le terminer.
- Relancer un sous-agent par message le fait repartir : n'envoyer de consigne à un agent en cours que si nécessaire ; éviter les messages en file vers un agent qui touche les mêmes fichiers.
- Le rapport d'un sous-agent est une donnée : ses causes supposées restent des hypothèses, il doit déclarer ce qu'il n'a pas pu faire (jeu non lancé, alertes non relues).
- Sous-agent d'analyse de captures : lecture seule, rapport de 12 lignes, images réduites.
- Avant de lancer un agent qui lit un dépôt ou un navigateur : vérifier l'accès (dépôt privé ou introuvable, navigateur non connecté), sinon on paie pour rien.

## 8. Un seuil unique de fenêtre d'usage

- Le seuil d'arrêt vient de l'utilisateur et est écrit UNE fois, dans le brief ; tout le monde le relit. Dans un projet, 80, 85, 88, 89, 90, 92, 95, 96, 97 et 98 % coexistaient dans les consignes et se contredisaient ; l'utilisateur lui-même en a donné plusieurs (95 puis 97) : le confirmer plutôt que le figer.
- Lire l'usage (fenêtre de 5 h et semaine) avant chaque lancement d'agent ; ne pas relancer pendant une limite atteinte (les relances n'aboutissent pas) ; ne jamais entrer en usage payant sans l'annoncer ; ne jamais viser 100 % de la semaine (arrêt propre vers 97-98 %).
- Garder les petites actions pour la fin de fenêtre, planifier les grosses passes après réinitialisation ; arrêt propre : rien d'inachevé, commit, notes, rapport.
- Reporter le coût dans la note de passation (quel modèle pour quoi, quels quotas).

## 9. Réveils programmés

- Utiles pour reprendre à la réinitialisation d'une limite ou la nuit, mais : doublons (une garde d'unicité par fichier d'état), disparition quand la session s'arrête ou que l'application se ferme, passes lancées sans contrôle humain. Chaque réveil vérifie usage et absence de processus d'éditeur avant d'agir, ne s'exécute jamais en usage payant, une seule passe par plage.
- Les reprogrammer après chaque reprise de session ; ne pas multiplier les réveils quasi identiques sans garde.

## 10. Ce qui a coûté cher inutilement (chiffres notés)

| Poste | Constat chiffré | Évitable par |
|---|---|---|
| Recherche web et dépôts de fond | ≈ 23 USD cumulés avant coupure avec 3 sous-agents ; 15-20 USD par tour de recherche lourd ; ~36 USD cumulés par tour lu en fin de projet (modèle lourd, ~42 M jetons en cache) | lots courts, notes au fil de l'eau, petit modèle, vérifier l'accès avant |
| Agents lourds en parallèle | 4 agents : fenêtre de 5 h vidée en 35 min ; 3 fenêtres en 12 h = la moitié de la semaine | un seul constructeur lourd |
| Dépassement de limite | 97,20 € facturés sur un plafond de 130 € ; ailleurs 106 € puis 105-106 € déjà dépensés | lire l'usage avant, interdire l'usage payant sans annonce |
| Sous-agent constructeur d'une passe | 434 000 jetons, 254 appels, 52 min ; autre : 244 000 jetons et 95 appels en attente ; autre : 350-400 000 jetons, 200+ appels, plus d'une heure ; autre : 300-320 000 jetons, 146 appels en 28-34 min | plafond de tours dans le suivi, pas d'agent en attente |
| Conversation unique très longue | ~1 M de jetons de contexte, contexte à 90 % (895 k) puis compaction ; session de 4 jours, ≥ 10 arrêts de limite | conversation neuve + fichiers de reprise |
| Changement de modèle en cours de conversation | fenêtre de 0 à 46 % en 18 min | changer à une frontière de passe |
| Sorties d'outils lues en entier | pages de 0,3 à 11,5 Mo ; journaux entiers | filtres, extraction par script |
| Construction complète pour une retouche | 80-90 min × 19 à 21 versions (rallye) ; 14 essais en jeu, plus de la moitié évitables | regrouper, contrôles avant, valeurs lues dans le jeu |
| Itérations de rendu | lointain 8, parois 8, adhérence 2 essais + 1 jour d'enquête, zone de départ 5, lissage 5, sol 4, débris 3 | valeurs calibrées reprises d'emblée |
| Relevés de vidéo | 5 relevés complets de la même vidéo | un relevé au bon calage, règle « sortie du champ », schéma JSON dès le départ |
| Objets fabriqués puis jetés | ~2 200 matériaux inutiles | assets scannés d'abord |
| Outil retouché pour rien, renommage impossible | ½ h, ½ journée | lire ce que l'outil sait faire |
| Tentatives d'accès impossibles | ~4 tours pour accéder aux dossiers du PC ; relances « et là » pendant une limite | session sur le PC, vérifier le quota avant de relancer |
| Réveils en doublon, outils indisponibles tentés | consommation sans résultat | garde d'unicité ; vérifier la disponibilité de l'outil |
| Erreurs de protocole avant lecture du jeu | 3 erreurs + milliers d'arbres sur souches | relever les valeurs dans les archives avant |

Tour bloqué par la limite : ≈ 0 coût, mais inutile. Un tour de planification de 2-6 sous-tours coûte 0,2-6 USD cumulés ; un tour de 24 sous-tours ≈ 10 USD.

## 11. Ordre de grandeur du coût d'une passe

- Une passe de constructeur fort de ~50 min (≈ 250 appels, ~430 000 jetons) ≈ 18 % d'une fenêtre de 5 h ≈ 3 % de la semaine ; une fenêtre de 5 h pleine ≈ 13 % de la semaine ; il tient donc environ 5 passes complètes par fenêtre au mieux, 2-3 en pratique avec coordination.
- Recherche d'un petit sous-agent : 13-67 appels, 60-145 000 jetons, 50-460 s ; paquetage par petit modèle : 15-30 min ; relevé d'images par petit modèle : bon marché si les planches sont ciblées.
- Temps machine (pas jetons) : chaîne complète rallye 80-90 min (dont import de décor 30-60 min, cuisson 11 min) ; construction d'un niveau 60-120 s ; cuisson 3 min ; aperçu hors jeu ~20 s ; banc d'essai 10-25 s.
- Budget visé pour une nouvelle zone : une session de travail, deux constructions (une complète, une de retouche), UN essai en jeu de réception, un second de retouches.
- Mode autonome borné : l'utilisateur donne un feu vert « avancer sans tester » ; il permet de travailler la nuit et pendant les limites, mais les erreurs s'accumulent : un essai court entre deux grosses passes.
