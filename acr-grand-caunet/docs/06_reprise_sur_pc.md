# Feuille de route pour une session sur le PC du directeur

*11 novembre 2026. Ce document sert de point de reprise : une session Claude ouverte sur le PC Windows du directeur doit pouvoir enchaîner à partir d'ici sans autre contexte.*

## 1. Pourquoi travailler sur le PC

Le projet a été mené jusqu'ici sur un serveur Linux qui n'a ni Windows, ni le jeu. Tout ce qui touche au jeu s'y fait à l'aveugle. Sur le PC, une session peut :

- lire les fichiers du jeu installé, et pas seulement leurs noms ;
- lancer le constructeur du mod, lire ses erreurs et corriger aussitôt ;
- installer et piloter Unreal Engine 5.6 par scripts ;
- déposer le mod dans le jeu, le directeur n'ayant plus qu'à rouler et à dire ce qu'il voit.

Ce que la session ne fera pas à la place du directeur : conduire et juger le ressenti.

## 2. État du projet à la reprise

| Élément | Où | État |
|---|---|---|
| Tracé, relief, décor cartographié | `data/processed/` | Fait (phase 2) |
| Chaussée au mètre : axe, bords, dévers | `data/processed/chaussee_precise.csv` | Fait ; zone du départ et carrefour du Lion d'Or à reprendre |
| Lignes de départ et d'arrivée | `data/reference/lignes_es.json` | Fixées sur vidéo ; PK 0 = départ, arrivée au PK 6 722 de l'axe IGN |
| Modèle 3D neutre | `modele/` | Route et terrain texturé ; ni marquage, ni parapets, ni arbres |
| Export au format d'échange | `export/stage_ir/grand_caunet/` | Fait et contrôlé ; jamais passé dans le constructeur |
| Structure d'une spéciale non officielle | `docs/04_integration_jeu.md` | Analysée d'après les sommaires de BioBio |
| Étude du constructeur ACR Extra Stages | `docs/05_export_stage_ir.md` | Faite sur le code, sans exécution |

Jeu du directeur : Assetto Corsa Rally, version de construction 25170642, installé dans `Z:\Steamlibrary\steamapps\common\Assetto Corsa Rally`. BioBio 0.3.0 y est installé.

Décisions du directeur à respecter :
- objectif final à la manière de BioBio : rendu réaliste et jouable ;
- pas de contact avec l'auteur de BioBio, et aucun de ses fichiers réutilisé ;
- étape 1 (essai avec ACR Extra Stages) validée, puis étape 2 (spéciale finale).

Les fichiers lourds ne sont pas dans le dépôt. `scripts/tout_lancer.sh` les régénère (Python 3.11 ou plus, `pip install -r requirements.txt`, accès à `data.geopf.fr`).

## 3. Étape 1 : rouler sur notre route dans le jeu

> **Mise à jour du 11/11/2026.** Cette étape est maintenant décrite pas à pas, avec ses scripts et les retouches du constructeur, dans [`pc/LISEZMOI.md`](../pc/LISEZMOI.md). C'est ce document qui fait foi ; le résumé ci-dessous est conservé pour mémoire. Différences à connaître : le fichier de correspondance se produit avec l'outil `acr-mappings` du projet, sans injection (Dumper-7 n'est qu'un secours) ; avec les options par défaut, BioBio peut rester installé.

But : vérifier la physique, le chronométrage et les notes du copilote. Le décor n'est pas jugé.

1. **Sauvegarder** le dossier `acr\Content\Paks` tel qu'il est, ou au minimum noter son contenu. Désinstaller BioBio avec son gestionnaire le temps de l'essai : les deux mods remplacent les mêmes tables de menus et ne cohabitent pas.
2. **Installer les prérequis** indiqués par `CONTRIBUTING.md` d'ACR Extra Stages : kit .NET 10, PowerShell 7, Git, Rust, puis `retoc`.
3. **Produire le fichier de correspondance du jeu** (`.usmap`) avec Dumper-7, Steam hors ligne. Dumper-7 s'injecte dans le jeu en cours d'exécution : le faire en jeu solo uniquement.
4. **Récupérer ACR Extra Stages** (<https://github.com/nitnerolf420/acr-extrastages>, licences MIT et Apache) et le compiler.
5. **Vérifier d'abord leur propre chaîne** sans rien changer : `mods\stage\build.ps1 -Verify` doit afficher « ALL PASS ». Cela demande une copie de DiRT Rally 2.0 ; à défaut, passer directement au point 6.
6. **Passer notre export** dans leur constructeur `acr-ref stage-build`. D'après la lecture du code, trois retouches sont nécessaires :
   - l'identifiant doit avoir la forme `<lieu>_rally_NN_route_N` : copier notre dossier sous `work\ir\grand_caunet_rally_01_route_0` ;
   - notre spéciale dépasse la zone de la spéciale hôte de 45 m en plan et de 11 m en hauteur : activer l'agrandissement (`--bounds`), que leur script simple n'active pas sans objets ;
   - rendre facultatifs les objets, le décor lointain et les textures, que nous ne fournissons pas.
7. **Installer et rouler** : copier les fichiers `zz_acrxs_…_P` produits dans `Paks\~mods`, lancer le jeu, Pays de Galles, Hafren South, en Free Practice hors ligne.

À constater en jeu : la longueur affichée (environ 6,74 km), la tenue de route sur l'asphalte, le déclenchement du chrono au départ et à l'arrivée, l'arrêt au point stop, les notes annoncées au bon moment. Tout écart est à consigner avec le PK.

Points non vérifiés par leurs auteurs eux-mêmes : l'agrandissement de la zone, et leurs versions 1.6 et suivantes. Prévoir que l'essai échoue une ou plusieurs fois.

## 4. Étape 2 : la spéciale finale, à la manière de BioBio

Cible, d'après les sommaires de BioBio : un niveau simple, un terrain en dalles avec une image par dalle, des variantes des matériaux du jeu, les arbres et objets du jeu désignés par leur chemin, un fichier de physique, une table de notes, un registre de tables de menus.

Deux voies à départager par un essai court de chacune :

**Voie A : Unreal Engine 5.6.** Créer un projet dont les dossiers et les noms imitent ceux du jeu, avec des éléments factices à la place des arbres et matériaux du jeu ; y importer notre terrain et notre route ; cuire le niveau ; n'empaqueter que nos éléments. À l'exécution, le jeu substitue ses vrais éléments aux factices. C'est la voie la plus naturelle pour le décor. ACR Extra Stages la décrit sans l'avoir prouvée. Compter environ 60 Go pour l'éditeur.

Premier essai à faire : un niveau vide avec un seul cube et un seul pin d'Alep factice, inscrit dans les menus, chargé en jeu. S'il se charge et que le vrai pin apparaît, la voie est ouverte.

**Voie B : écriture directe.** Fabriquer les fichiers en recopiant et en adaptant ceux du jeu, comme le fait ACR Extra Stages pour la physique. Pas d'éditeur à installer, mais il faut écrire nous-mêmes les maillages et les textures au format du jeu.

Dans les deux cas, réutiliser d'ACR Extra Stages ce qui écrit la physique, le chronométrage, les notes et les tables de menus.

Données à produire côté projet pour l'une ou l'autre voie :
- la photo aérienne découpée en dalles, au format d'image du jeu ;
- le semis des arbres : position, essence (carte forestière), hauteur (relevé laser), associé aux arbres du catalogue du jeu (`Foliage/Trees/AleppoPine`, etc.) ;
- les parapets de pierre et de béton des ponts, les murets, les panneaux ;
- la texture et le marquage de la route.

## 5. Règles de prudence sur le PC

- Ne jamais modifier les archives d'origine du jeu : tout mod va dans des fichiers séparés, retirables.
- Jeu hors ligne pour tous les essais.
- Garder une copie du dossier `Paks` avant le premier essai.
- Demander l'accord du directeur avant toute installation de logiciel.
