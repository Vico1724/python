# Export vers le format d'échange d'ACR Extra Stages

*10 novembre 2026, mis à jour le 11 novembre. Document destiné au directeur de projet.*

## 1. Ce que fait l'exporteur

ACR Extra Stages travaille en deux temps. Un premier programme lit une spéciale de DiRT Rally 2.0 et l'écrit dans un dossier d'échange, le « Stage IR ». Un second programme, le constructeur, lit ce dossier et fabrique les fichiers que le jeu charge.

Le script `scripts/09_export_stage_ir.py` remplace le premier temps : il écrit ce dossier à partir de nos mesures, en 7 secondes, après les étapes 8, 11 et 12. Les fichiers des étapes 11 et 12 sont facultatifs.

## 2. Ce qu'il produit

Le dossier `export/stage_ir/grand_caunet/` contient trois fichiers.

- **`stage.json`** décrit la spéciale :
  - le nom, la longueur et le tracé de l'axe ;
  - 1 096 « portes », c'est-à-dire le point d'axe et les deux bords de la chaussée, tous les 10 m au plus. Il y en a davantage là où un bord tourne ou se resserre (ponts, carrefour), parce que le constructeur relie les portes par des segments droits ;
  - le départ, deux temps intermédiaires et l'arrivée ;
  - la zone d'arrêt au point stop ;
  - les obstacles et les notes du copilote.
- **`collision.glb`** est le **sol physique**, la surface invisible sur laquelle la voiture roule (758 000 triangles). Il comprend :
  - la chaussée et l'enrobé annexe du carrefour du Lion d'Or, classés en asphalte lisse ;
  - l'accotement en terre sur 3 m et le terre-plein du carrefour, classés en gravier dur ;
  - le terrain du couloir, sur 130 m de part et d'autre de la route, classé en herbe.

  Sous les surfaces du carrefour, le terrain naturel est retiré.
- **`objects_collision.glb`** contient les **obstacles**, en volumes simples : 522 morceaux, issus des parapets des ponts et des murets (pierre ou béton), des parapets et des piquets du Lion d'Or. La rubalise n'est pas exportée : un ruban ne retient pas une voiture, et les obstacles du jeu ne se cassent pas, si bien qu'un ruban solide ferait un mur invisible.

Repères chiffrés :
- La longueur chronométrée est de 6 736 m, mesurée en pente le long de l'axe, presque autant à plat, et de 6 702 m sur le road-book officiel.
- Les temps intermédiaires sont placés aux points officiels INTER2 (PK 2 677) et INTER6 (PK 5 043).

Les notes du copilote sont décrites au § 3 bis.

**Ce qui manque**, laissé vide comme le format le permet : les arbres et autres objets du décor, les maillages d'affichage et leurs textures, les images des menus.

## 3. Contrôles

Deux contrôles indépendants relisent les fichiers écrits, par des calculs différents, et donnent les mêmes résultats :

- le sol est présent et à la bonne hauteur sous les 1 096 portes ;
- il n'y a aucun trou le long de l'axe (8 274 points testés), ni juste au-delà des bords, ni sous les surfaces du carrefour ;
- le bord droit est toujours à droite dans le sens de marche ;
- les virages tournent du côté annoncé ;
- aucun obstacle n'empiète sur la chaussée ;
- les volumes exportés recouvrent les parapets d'origine au millimètre près.

**Un point est à reprendre :** au Lion d'Or, en cours de reprise par ailleurs, 5 morceaux du parapet de pierre du carrefour (PK 3 637 à 3 640) se trouvent sur la nouvelle chaussée. Le constructeur les aurait supprimés. L'exporteur les retire et les liste dans `stage.json`. Il faudra relancer l'export quand ce carrefour sera fini.

## 3 bis. Les notes du copilote

**Ce qui est calculé.** Le script repère les virages d'après la courbure de l'axe. Pour chacun, il donne le sens et une sévérité de 6 (rapide) à 1, ou épingle, d'après le rayon le plus serré. Il donne aussi la distance jusqu'au virage suivant. Il en trouvait 55.

**Ce qui vient de la vidéo.** Le relevé des trois vidéos embarquées a confirmé le sens de 53 virages, les deux autres étant non concluants. Ses corrections sont rangées dans un fichier modifiable à la main, `data/reference/notes_copilote_retouches.json`, que le script applique à chaque exécution. Chaque retouche repère son virage par son point kilométrique, à 30 m près, et non par son numéro, car la route bouge encore de quelques mètres. Elle indique aussi sa source et un degré de confiance. Il y en a seize :

- cinq inflexions supprimées ;
- la légère gauche du départ ajoutée ;
- le grand gauche d'après la première épingle durci en « 1 » (le relevé dit « 2 long », mais le jeu ne sait pas dire « long ») ;
- le droit du pont du PK 2 777 adouci en « 2 » ;
- trois « ne pas couper » (rocher vers le PK 1 550, muret du Lion d'Or, parapet de l'épingle de la D1) ;
- cinq libellés.

Il reste 51 virages annoncés. Un essai où l'on fait glisser les virages de 3 à 10 m donne exactement les mêmes notes.

**Ce que le jeu ne sait pas dire.** Leur constructeur ne produit que les virages, « ne pas couper », les distances, « dans » et « et » entre deux virages enchaînés, et l'arrivée. Le jeu possède d'autres annonces (attention, crête, bosses...), mais leur constructeur ne sait pas les produire. Les ponts et ponceaux, le rétrécissement, les gravillons, l'enrobé rapiécé, le public, les mots « long » et « sur pont » ne sont donc pas annoncés en jeu. Ces 24 dangers sont conservés dans `stage.json` (`pacenotes.dangers_non_exprimables`), pour une version ultérieure.

**Ce qui reste à valider au volant :** le moment où chaque note est lue (80 m avant le virage, recalé ensuite par leur constructeur), les sévérités à vitesse de course, et la note du départ, que la voiture atteint à l'arrêt.

## 4. Peut-on construire notre spéciale avec ACR Extra Stages tel quel ?

**Non, mais avec trois petites retouches, oui pour un essai.** Le constructeur recopie une spéciale galloise du jeu (Hafren South, variante 1/2) et en remplace le sol, le tracé, le chronométrage, les notes et les obstacles.

La voie retenue pour l'essai est ce **remplacement de la variante galloise**. Leur « ajout aux menus » exigerait des fichiers propres à DiRT Rally (décor lointain, textures dans un format d'image que nous ne savons pas encore produire).

Le remplacement demande trois choses :

- **Agrandir la zone physique de l'hôte.** Notre route la dépasse d'environ 45 m. L'option existe dans leur constructeur, mais leur script simple ne l'active pas : notre kit l'appelle directement.
- **Ne pas livrer de table de menus.** C'est une retouche de leur code : sans elle, notre mod et BioBio se masqueraient. Le menu affichera donc encore 4,8 km.
- **Accepter des obstacles sans maillage d'affichage.** C'est une deuxième retouche de leur code.

La troisième retouche, qui accepte un identifiant de spéciale hors DiRT Rally, ne sert qu'à la voie d'ajout aux menus.

L'affichage reste rudimentaire : couleurs de contrôle, piquets de bord, obstacles en pavés unis.

## 5. Sur le PC Windows

Tout est dans **`pc/LISEZMOI.md`**, avec sept scripts numérotés. Dans l'ordre :

1. contrôle de départ ;
2. installation des logiciels, après confirmation ;
3. récupération d'ACR Extra Stages à la version étudiée, avec nos retouches ;
4. fichier de correspondance du jeu ;
5. construction et contrôle hors jeu ;
6. installation dans `Paks\~mods` ;
7. désinstallation.


## 6. Risques

- **Rien n'a été exécuté.** La compilation de leur code retouché n'a pas pu être vérifiée (refusée sur le serveur de travail), ni nos scripts relus par PowerShell. Une faute peut arrêter une étape : le journal dira laquelle.
- **Le projet ACR Extra Stages est en version bêta.** L'agrandissement de la zone physique n'est vérifié qu'hors du jeu.
- **Une mise à jour du jeu** oblige à refaire le fichier de correspondance et à reconstruire.
- **L'affichage réaliste** (photo aérienne, pins d'Alep du jeu, murets) n'existe dans aucun outil libre aujourd'hui. C'est le plus gros chantier restant.
