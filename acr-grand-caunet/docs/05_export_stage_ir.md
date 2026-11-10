# Export vers le format d'échange d'ACR Extra Stages

*10 novembre 2026. Document destiné au directeur de projet.*

## 1. Ce que fait l'exporteur

ACR Extra Stages travaille en deux temps : un programme lit une spéciale de DiRT Rally 2.0 et l'écrit dans un dossier d'échange (« Stage IR ») ; un second, le constructeur, lit ce dossier et fabrique les fichiers que le jeu charge. Le script `scripts/09_export_stage_ir.py` remplace le premier temps : il écrit ce dossier à partir de nos mesures, en 3 secondes, après l'étape 8.

## 2. Ce qu'il produit

Le dossier `export/stage_ir/grand_caunet/` contient deux fichiers.

- **`stage.json`** décrit la spéciale : nom, longueur, tracé de l'axe, une « porte » tous les 10 m (le point d'axe et les deux bords de la chaussée, 760 portes), le départ, deux temps intermédiaires, l'arrivée, la zone d'arrêt au point stop, et les notes du copilote.
- **`collision.glb`** est le **sol physique**, c'est-à-dire la surface invisible sur laquelle la voiture roule. Il comprend trois matières : la chaussée en enrobé, l'accotement en terre sur 3 m, et le terrain du couloir (130 m de part et d'autre de la route), soit 758 000 triangles. Ces matières sont des codes que leur table des surfaces associe déjà à l'asphalte lisse, au gravier dur et à l'herbe du jeu.

Repères chiffrés : longueur chronométrée 6 742 m (mesurée en pente le long de l'axe ; 6 736 m à plat, 6 702 m sur le road-book officiel) ; temps intermédiaires aux points officiels INTER2 (PK 2 677) et INTER6 (PK 5 043), qui découpent la spéciale en trois secteurs comme le jeu en affiche trois ; aucun des deux n'est sur un pont.

**Les notes du copilote sont un brouillon.** Elles sont calculées d'après la courbure de la route : 56 virages annoncés, avec le sens, la sévérité de 1 (lent) à 6 (rapide), deux épingles et les distances entre virages. Il faudra les relire sur une vidéo embarquée.

**Ce qui manque**, laissé vide comme le format le permet : les objets (arbres, murets, parapets), les maillages d'affichage et leurs textures, les images des menus.

## 3. Contrôles

Un contrôle relit les fichiers écrits, indépendamment du programme qui les écrit : sol physique présent et à la bonne hauteur sous les 760 portes, aucun trou le long de l'axe (7 977 points) ni à 5 m au-delà des bords, bord droit toujours à droite dans le sens de marche, 56 virages qui tournent du côté annoncé.

Le constructeur lui-même n'a pas été lancé : il exige Windows et le jeu installé.

## 4. Peut-on construire notre spéciale avec ACR Extra Stages tel quel ?

**Non, pas tel quel. Mais le cœur fonctionne.** Leur constructeur sait déjà poser notre route et sa physique dans le jeu. Il le fait en recopiant une spéciale galloise du jeu (Hafren South) et en y remplaçant le sol, le tracé, le chronométrage et les notes. Trois obstacles demandent cependant des retouches :

1. Notre spéciale est un peu trop large pour la zone galloise d'origine (il manque environ 45 m de marge). Leur option d'agrandissement existe, mais leur script simple ne l'active pas, et son effet en jeu n'est pas encore vérifié.
2. Leur chaîne complète (la spéciale ajoutée aux menus sans rien remplacer) exige des fichiers propres à DiRT Rally : décor lointain, objets, textures au format DirectX. Nous ne les avons pas encore.
3. L'affichage reste rudimentaire. Le sol est dessiné avec des matériaux empruntés à la spéciale galloise (gravier gallois sur notre asphalte), ou avec un matériau « simple » du jeu portant une seule image. Notre photo aérienne pourrait y être plaquée par dalles, mais il faut d'abord la convertir au format d'image du jeu, ce qui n'est pas fait.

## 5. Ce qu'il faudra faire sur le PC Windows

**Documenté par le projet** (`CONTRIBUTING.md`) :

1. Installer le kit .NET 10, Git, Rust (pour installer retoc), PowerShell 7.
2. Installer retoc, l'outil qui lit et réécrit les archives du jeu. Au premier lancement, il télécharge lui-même la bibliothèque de compression Oodle.
3. Produire le fichier de correspondance du jeu (`.usmap`) avec Dumper-7, Steam hors ligne.
4. Lancer `mods\stage\build.ps1 -Verify`. Le résultat attendu est « ALL PASS », puis trois fichiers `zz_acrxs_…_P` à copier dans `Paks\~mods`.
5. Dans le jeu : Pays de Galles, Hafren South, variante 1/2, en Free Practice hors ligne.

**Ce que je suppose**, et qui reste à essayer :

6. Copier notre dossier dans `work\ir\grand_caunet_rally_01_route_0`, puis lancer leur constructeur directement, avec l'option d'agrandissement (`--bounds 1`) et sans les objets. Leur script simple ne prévoit pas cette combinaison.
7. Ce qu'on doit voir : la longueur de 6,74 km dans le menu, une route lisible avec des piquets de bord, le chronomètre qui démarre et s'arrête, la voiture arrêtée au point stop, des notes jouées. Le décor gallois restera visible autour.

## 6. Risques

- **Le projet est en version bêta.** Plusieurs étapes ne sont vérifiées qu'hors du jeu, notamment le monde agrandi et l'ajout aux menus sans remplacement.
- **Leur méthode remplace la variante galloise.** Tant que le mod est installé, le sens inverse de Hafren South est inutilisable. Il ne peut pas cohabiter avec un autre mod qui remplace les mêmes tables, BioBio compris.
- **Une mise à jour du jeu peut tout casser.** Il faut alors reconstruire avec un fichier de correspondance à jour.
- **L'affichage réaliste** (photo aérienne, pins d'Alep du jeu, murets) n'existe dans aucun outil libre aujourd'hui. C'est le plus gros chantier restant, quelle que soit la voie choisie.
