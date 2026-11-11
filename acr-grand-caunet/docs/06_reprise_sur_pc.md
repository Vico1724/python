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

**Décision du directeur du 11/11/2026 : Unreal Engine 5.6 sera installé sur son PC**, avec une session Claude Desktop. Le rendu visé est beau et réaliste, à la manière de BioBio.

**Le protocole à suivre est `pc/etape2_unreal/PROTOCOLE.md`.** C'est une suite d'essais courts, du plus simple au plus ambitieux, avec ce qu'il faut conclure de chaque résultat :

- **E0** : installer UE 5.6.1, la version du jeu, créer le projet factice « acr » et sa chaîne de cuisson (retoc vers `Paks\~mods`) ;
- **E1** : le jeu accepte-t-il une texture, puis un maillage avec une variante d'un matériau du jeu, cuits par notre éditeur ?
- **E2** : un niveau simple à nous, inscrit aux menus, avec un pin d'Alep du jeu désigné par son chemin. Les acteurs de jeu viennent soit de « classes souches », soit de la voie hybride (notre décor posé dans le clone de Hafren d'ACR Extra Stages) ;
- **E3** : une dalle de terrain avec sa photo ;
- **E4** : 200 m complets, puis toute la spéciale.

Le protocole décrit aussi la voie B de repli, sans éditeur : une partie existe déjà chez ACR Extra Stages.

Le kit fournit :
- les éléments du jeu utiles, avec leurs chemins (`elements_jeu_utiles.json`) ;
- la liste des éléments factices ;
- des squelettes de scripts, jamais exécutés : création des factices, import des dalles, pose des 41 584 arbres, cuisson.

Données encore à produire côté projet : la photo aérienne en dalles au format du jeu (en cours : `terrain_sol.glb`, `textures_sol/`), l'anneau lointain (`lointain.glb`), les hauteurs réelles des maillages d'arbres du jeu (à relever sur le PC).

## 5. Règles de prudence sur le PC

- Ne jamais modifier les archives d'origine du jeu : tout mod va dans des fichiers séparés, retirables.
- Jeu hors ligne pour tous les essais.
- Garder une copie du dossier `Paks` avant le premier essai.
- Demander l'accord du directeur avant toute installation de logiciel.
