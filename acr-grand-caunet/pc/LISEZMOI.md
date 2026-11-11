# Essai de la spéciale du Grand Caunet dans Assetto Corsa Rally

*11 novembre 2026. Ce document se suit seul, du début à la fin, sur le PC Windows du directeur. Il sert aussi de feuille de route à une session Claude ouverte sur ce PC.*

**Rien de ce kit n'a encore été exécuté.** Les scripts ont été écrits sur un serveur Linux, sans Windows et sans le jeu. Chaque affirmation porte l'une de ces trois marques :

- **[documenté]** : le projet ACR Extra Stages l'écrit dans sa documentation ;
- **[déduit du code]** : je l'ai lu dans leur code, sans l'exécuter ;
- **[supposé]** : je le crois probable, sans preuve.

## 1. Ce que fait l'essai, et ce qu'il ne fait pas

L'essai permet de rouler sur **notre route, avec sa vraie forme et son vrai relief**, en Free Practice, à la place de la variante 1/2 de la spéciale galloise *Hafren South*. Le jeu ne permet pas d'ajouter une spéciale. On reprend donc une spéciale existante et on remplace ce qu'elle contient : la surface de roulage, le tracé, le chronométrage, les notes du copilote et les obstacles.

Ce qu'on doit pouvoir juger :

- la tenue de route sur l'enrobé ;
- le chronomètre ;
- l'arrêt au point stop ;
- les notes du copilote ;
- les parapets des ponts et le balisage du carrefour du Lion d'Or.

Ce que l'essai **ne fait pas** :

- **L'affichage est rudimentaire.**
  - Le sol est dessiné avec le quadrillage gris par défaut du moteur, et la route en bleu clair uni (ce sont les couleurs de contrôle du jeu).
  - Des piquets magenta marquent les bords tous les 15 m, et des portiques verts le départ et l'arrivée.
  - Les parapets et le balisage apparaissent comme des pavés de couleur unie.
  - Il n'y a ni photo aérienne, ni arbres. **[documenté]** (`docs/decisions.md` D6-D7 de leur projet)
- **Le décor gallois.** Par défaut il est caché, et l'horizon sera vide. Avec l'option `-GarderDecor`, il reste visible et traverse notre route par endroits.
- **Les menus.** Ils continuent d'afficher « Pays de Galles, Hafren South, Afon Bidno - Severn, 4,8 km ». C'est voulu, pour ne pas toucher aux tables de menus (voir § 6).
- **Le sens inverse.** La variante 2/2 de Hafren South n'est plus jouable tant que le mod est installé. Elle partage la même surface de roulage. **[documenté]**
- **Mode de jeu.** L'essai est hors ligne uniquement, en Free Practice.

## 2. D'où viennent les outils

La construction utilise **ACR Extra Stages** (<https://github.com/nitnerolf420/acr-extrastages>, d'après <https://github.com/cherrymcgerry/acr-extrastages>), à la version `1324f07d35549a24bd7d2f7d11fe7faaf3e44265`. Ce logiciel libre est distribué sous **double licence MIT ou Apache-2.0**, au choix. Copyright : les auteurs d'ACR Extra Stages.

Nos trois retouches (`pc/patches/`) sont des modifications de ce logiciel, distribuées sous les mêmes licences. Elles sont marquées `[Grand Caunet]` dans le code. Le texte des licences se trouve dans leur dépôt, aux fichiers `LICENSE-MIT` et `LICENSE-APACHE`. Leur fichier `THIRD_PARTY_NOTICES.md` liste les composants qu'ils utilisent.

| Retouche | Taille | Pourquoi |
|---|---|---|
| `0001-keep-variants.patch` | 3 fichiers, +13 / −4 lignes | Nouvelle option `--keep-variants 1` : le mod ne livre plus la table de menus `DT_TracksVariants`. Cette table est remplacée en entier par quiconque la livre. Sans cette option, notre mod et BioBio se masqueraient l'un l'autre. Le contrôle `stage-verify` connaît la même option. |
| `0002-objets-facultatifs.patch` | 2 fichiers, +11 / −7 lignes | Leur code supposait des objets venant de DiRT Rally, avec leurs maillages d'affichage (`render/objects.glb`). Nous n'avons que des volumes de collision : sans ce fichier, chaque obstacle est dessiné comme son propre volume. Un `objects` vide est aussi accepté. |
| `0003-identifiant-hors-dr2.patch` | 1 fichier, +6 / −1 ligne | Accepte un identifiant de spéciale qui n'a pas la forme DiRT Rally. Cette retouche n'est **pas utilisée par l'essai** (notre identifiant a déjà la bonne forme) ; elle prépare l'autre voie de construction, celle de l'ajout aux menus. |

## 3. Prérequis

- **Windows 10 ou 11** 64 bits, le jeu installé par Steam, Steam ouvert. Mettre Steam **hors ligne** pendant les essais.
- **Espace disque** **[supposé]** :
  - environ **10 Go libres sur Z:**, le disque du jeu : construction, outils compilés, copies de contrôle ;
  - environ **10 Go sur C:** pour les logiciels ci-dessous (dont 5 Go pour les outils C++).
  - Le dossier de travail `Z:\acrxs` doit être sur le même disque que le jeu. Leur outil crée des « liens physiques » vers les archives du jeu au lieu de les copier, et un lien physique ne traverse pas les disques **[déduit du code]**. Le disque doit être formaté en NTFS.
- **Logiciels**, installés par `1_prerequis.ps1` après confirmation, avec winget, le gestionnaire de logiciels de Windows :
  - PowerShell 7 : <https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-windows> **[documenté]** ;
  - Git : <https://git-scm.com/download/win> **[documenté]** ;
  - kit .NET 10 : <https://dotnet.microsoft.com/download/dotnet/10.0> **[documenté]** ;
  - Rust : <https://rustup.rs> **[documenté]** ;
  - outils de compilation C++ de Microsoft : <https://visualstudio.microsoft.com/visual-cpp-build-tools/>. Rust en a besoin sous Windows. **[supposé : leur documentation ne le dit pas]**
  - winget lui-même, s'il manque : application « App Installer » du Microsoft Store.
- **Internet**, pendant la préparation seulement : téléchargement des logiciels, des bibliothèques de compilation, et de la bibliothèque de compression Oodle, que leurs outils récupèrent eux-mêmes **[documenté]**.
- **Notre dépôt `acr-grand-caunet`** sur le PC, avec `export\stage_ir\grand_caunet\stage.json` et `collision.glb`. Ces fichiers sont versionnés.

## 4. Les étapes

Ouvrir une fenêtre PowerShell **dans le dossier du dépôt `acr-grand-caunet`**. Chaque script écrit un journal dans `Z:\acrxs\journal\`. Les chemins par défaut se changent avec `-Jeu "…"` et `-Travail "…"`.

### Étape 0 : contrôle avant départ (ne modifie rien)

```powershell
powershell -ExecutionPolicy Bypass -File pc\scripts\0_controle.ps1
```

**Ce qu'on doit voir :** des lignes `OK`. En particulier :

- « version de construction 25170642 » ;
- « les archives d'origine ont les tailles attendues » ;
- « dossier de travail sur le disque du jeu ».

Les outils absents sont normaux avant l'étape 1.

**Si ça échoue :** lire les lignes `ATTENTION`. Si la version du jeu n'est pas 25170642, le jeu a été mis à jour : l'essai peut quand même marcher, mais le fichier de l'étape 3 doit être refait, et rien n'est garanti.

### Étape 1 : prérequis

```powershell
powershell -ExecutionPolicy Bypass -File pc\scripts\1_prerequis.ps1
```

Ce script demande une confirmation avant chaque installation.

**Ce qu'on doit voir :** « déjà installé » ou « installé » pour chacun des cinq logiciels.

**Si ça échoue :** installer à la main le logiciel en cause depuis le lien du § 3, puis relancer. **Fermer ensuite la fenêtre et en ouvrir une nouvelle**, pour que les nouveaux logiciels soient trouvés. Les étapes suivantes se lancent avec `pwsh`, c'est-à-dire PowerShell 7 (version 7.2 au moins).

### Étape 2 : récupérer et construire les outils

```powershell
pwsh -ExecutionPolicy Bypass -File pc\scripts\2_recuperer_acrxs.ps1
```

Ce script récupère ACR Extra Stages à la version exacte étudiée, applique nos trois retouches, puis construit les outils : `acr-ref` (le constructeur), `acr-additive`, `acr-mappings` et `retoc` (l'outil qui lit et réécrit les archives du jeu). Compter 10 à 20 minutes la première fois **[supposé]**.

**Ce qu'on doit voir :** « 0001… appliquée » (et 0002, 0003), puis « outils prêts ».

**Si ça échoue :**
- Une retouche qui ne s'applique pas signifie que le dossier `Z:\acrxs\acr-extrastages` a été modifié : le renommer, puis relancer.
- Une erreur de construction Rust qui mentionne `link.exe` signifie que les outils C++ manquent (étape 1).
- Une erreur de construction .NET : copier la fin du journal et me la transmettre. **La compilation de leur code retouché n'a pas pu être vérifiée avant l'essai.**

### Étape 3 : fichier de correspondance du jeu

```powershell
pwsh -ExecutionPolicy Bypass -File pc\scripts\3_usmap.ps1
```

Leurs outils ont besoin d'un fichier `.usmap` qui décrit les structures de données de cette version du jeu. Leur outil `acr-mappings` le produit ainsi **[documenté, vérifié par eux sur la version 25170642]** :
- il lance le jeu par Steam ;
- il lit sa mémoire depuis l'extérieur, en lecture seule, sans rien y injecter ;
- il referme le jeu (30 à 60 secondes).

Il faut donc que Steam soit ouvert et que le jeu soit fermé au départ. Le fichier est ensuite contrôlé sur les tables du jeu et sur Hafren South.

**Ce qu'on doit voir :** « fichier de correspondance valable ».

**Si ça échoue :** la voie de secours est **Dumper-7** (<https://github.com/Encryqed/Dumper-7>), que leur projet documente (`CONTRIBUTING.md`). Elle n'est pas automatisée ici, parce qu'elle est hasardeuse :
- Dumper-7 est un module qu'il faut compiler avec Visual Studio, puis injecter dans le jeu en cours d'exécution, Steam hors ligne et en jeu solo uniquement ;
- il écrit un fichier `…\Mappings\5.6.1-0+UE5-acr.usmap`, qu'on donne ensuite au script :

```powershell
pwsh -ExecutionPolicy Bypass -File pc\scripts\3_usmap.ps1 -Usmap "C:\Dumper-7\…\5.6.1-0+UE5-acr.usmap"
```

### Étape 4 : construire le mod (n'écrit rien dans le jeu)

```powershell
pwsh -ExecutionPolicy Bypass -File pc\scripts\4_construire.ps1
```

Le jeu doit être fermé. Le script :

1. copie notre dossier d'échange ;
2. lit les archives d'origine du jeu, sans les mods ni BioBio ;
3. extrait les fichiers de Hafren South ;
4. construit le mod avec agrandissement de la zone physique ;
5. l'empaquette dans trois fichiers `zz_acrxs_grandcaunet_P.utoc`, `.ucas` et `.pak` (environ 0,3 à 0,6 Go **[supposé]**) ;
6. le relit et le contrôle hors du jeu.

**Ce qu'on doit voir :** des lignes `PASS`, quelques `WARN` éventuels, puis « contrôles hors jeu : aucune ligne FAIL ».

**Si ça échoue :** conserver le journal. Les lignes `FAIL` disent quel contrôle a échoué. Me transmettre le journal et le fichier `Z:\acrxs\construction\stage-grandcaunet.report.json`.

Options, à n'utiliser qu'après un premier essai réussi :

- `-Textures` : sol et route avec les matériaux texturés de Hafren. La route aura alors l'aspect du gravier gallois.
- `-Noms` : la variante s'affiche « Le Grand Caunet ».
- `-Ciel` : la position du soleil est réglée sur Monte-Carlo. Le contrôle hors jeu (`stage-verify`) ne vérifie pas ce réglage : leur contrôle du ciel ne connaît que la Nouvelle-Zélande **[déduit du code]**.
- `-GarderDecor` : le décor gallois reste visible.
- `-SansObstacles` : pas de parapets ni de balisage.
- `-Longueur` : le menu affiche 6,74 km. **Cette option est incompatible avec BioBio installé** (§ 6).

### Étape 5 : installer

```powershell
pwsh -ExecutionPolicy Bypass -File pc\scripts\5_installer.ps1
```

Ce script consigne d'abord le contenu du dossier `Paks` dans le journal, puis demande confirmation. Il copie ensuite les trois fichiers dans `…\acr\Content\Paks\~mods\`, dossier qu'il crée s'il n'existe pas. Il ne touche à aucun autre fichier.

### Étape 6 : rouler

1. Lancer le jeu, Steam hors ligne.
2. Choisir **Pays de Galles, Hafren South, variante 1/2 « Afon Bidno - Severn »**.
3. Lancer en **Free Practice**, avec une voiture connue.
4. La voiture part un peu avant la ligne de départ, dans les 170 m d'approche que contient notre export. Le point exact est recopié de la position du départ de Hafren par rapport à sa ligne **[déduit du code]**.

## 5. Désinstaller et revenir à l'état d'origine

```powershell
pwsh -ExecutionPolicy Bypass -File pc\scripts\6_desinstaller.ps1
```

Ce script supprime nos trois fichiers de `Paks\~mods`, ainsi que le dossier `~mods` s'il l'avait créé et qu'il est vide. Le jeu redevient exactement celui d'avant, car aucune archive d'origine n'a été modifiée.

À la main, cela revient à supprimer `Paks\~mods\zz_acrxs_grandcaunet_P.*`. En cas de doute, Steam propose « Vérifier l'intégrité des fichiers du jeu ».

Le dossier `Z:\acrxs` peut être supprimé ensuite pour récupérer la place.

## 6. Cohabitation avec BioBio

BioBio installe deux archives dans `Paks` : `pakchunk99-ChileBioBio_P` (la spéciale) et `pakchunk99-SandoRegistry_2_P` (son « registre »). Le registre remplace en entier les tables de menus `DT_Levels`, `DT_Tracks`, `DT_TracksLocations` et `DT_TracksVariants`.

- **Avec les options par défaut, BioBio peut rester installé.** Notre mod ne livre aucune table de menus. Il ne remplace que des fichiers propres à Hafren South : sa surface de roulage, une cellule du niveau, le niveau lui-même (pour l'agrandissement et le décor caché) et sa table de notes. **[déduit du code]** (liste des paquets écrits par `stage-build`)
- **Avec `-Longueur`**, notre mod livre `DT_TracksVariants`, et l'une des deux versions masquerait l'autre. Avant d'utiliser cette option :
  1. retirer BioBio avec son gestionnaire d'installation, ou déplacer ses deux séries de fichiers `pakchunk99-*` de `Paks` vers `Z:\acrxs\biobio_de_cote\` ;
  2. après l'essai, les remettre à leur place.
- **Avec `-Noms`**, notre mod livre la table de textes `ST_Track`. BioBio ne semble pas la livrer **[supposé]**.
- **Si le jeu plante au chargement de la spéciale** alors que BioBio est installé, refaire un essai BioBio retiré. Son registre contient aussi une « table de surfaces », dont nous ne savons pas si elle remplace le registre des surfaces du jeu **[supposé]**.

## 7. Ce qu'il faut regarder et me rapporter

Pour chaque point, noter : réussi, raté, ou pas atteint. En cas de problème, noter aussi la distance affichée par le jeu et faire une capture d'écran.

1. **Chargement :** la spéciale se charge, et la voiture apparaît posée sur le sol, dans le bon sens.
2. **Longueur :** le menu affiche 4,8 km, ce qui est normal (6,74 km avec `-Longueur`). Le compteur de route en course affiche environ 7,5 km, approche et sortie comprises **[déduit du code : il lit la longueur du tracé]**.
3. **Adhérence :**
   - adhérence d'asphalte sur toute la route, y compris l'enrobé du carrefour du Lion d'Or ;
   - accotement en terre dure sur 3 m ;
   - herbe au-delà ;
   - aucun trou, aucune bosse invisible, aucun mur invisible.
4. **Ponts :** les parapets arrêtent la voiture, et ce sont les seuls obstacles, avec les parapets et les piquets du Lion d'Or.
5. **Chronomètre :**
   - départ au portique vert ;
   - temps intermédiaires vers 2,68 km et 5,04 km ;
   - arrivée à 6,74 km ;
   - un temps plausible.
6. **Point stop :** la voiture est arrêtée environ 580 m après l'arrivée.
7. **Notes du copilote :** elles sont lues au bon moment, avec le bon sens et une sévérité plausible. Ce sont des notes **brouillon**, calculées d'après la courbure de la route ; noter celles qui sont fausses, avec la distance.
8. **Sortie de route :** la remise en piste replace la voiture sur notre route. Au-delà de 130 m de la route, il n'y a plus de sol : on tombe.
9. **Images par seconde :** fluide ou non.

Joindre les journaux de `Z:\acrxs\journal\` et le rapport `Z:\acrxs\construction\notes-grandcaunet.md`.

## 8. Ce qui n'a jamais été testé

- **Aucun script de ce kit n'a été exécuté**, ni même relu par PowerShell. Il peut contenir des fautes de frappe qui arrêtent une étape.
- **La compilation de leur code avec nos retouches n'a pas été vérifiée** (elle a été refusée sur le serveur de travail).
- **Leur constructeur n'a jamais été lancé sur notre dossier.** Leurs contrôles hors jeu peuvent signaler des écarts que je n'ai pas prévus. Mes propres contrôles, refaits indépendamment sur le serveur, sont tous passés : sol sous les 1 096 portes, aucun trou, obstacles hors de la chaussée, côtés gauche et droit cohérents.
- **L'agrandissement de la zone physique** (`--bounds`) est écrit par leur projet, mais son comportement en jeu n'est pas vérifié par eux (`docs/additive-batch-test.md`, § 5).
- **Les obstacles :**
  - `PM_WallPlasticPole` (piquets) n'est peut-être pas inscrit au registre des surfaces du jeu ; leur constructeur le remplacerait alors par une paroi générique **[déduit du code]** ;
  - les piquets sont des poteaux indestructibles : les obstacles simples du jeu ne se cassent pas.
- **Le Lion d'Or :** il était en cours de reprise au moment de l'export. Des morceaux d'obstacles situés sur la nouvelle chaussée (5 morceaux du parapet de pierre du carrefour, PK 3 637 à 3 640, lors du dernier export) ont été retirés de l'export (liste dans `stage.json`, rubrique `export.obstacles`). Il faudra refaire l'export quand ce carrefour sera fini.
- **Les options `-Textures`, `-Noms`, `-Ciel`** reprennent des réglages que leur projet n'a vérifiés que hors du jeu.
- **La cohabitation avec BioBio** n'a jamais été essayée.
- **Points repérés à la relecture, non corrigés faute de certitude :**
  - `1_prerequis.ps1` s'arrête si un installateur renvoie un code autre que 0. Or winget peut renvoyer un code particulier pour « redémarrage requis » (outils C++) : dans ce cas, redémarrer le PC puis relancer le script, qui reprendra où il en était ;
  - l'installation de Rust par winget n'installe peut-être pas la chaîne de compilation « stable » : si l'étape 2 dit que `cargo` est introuvable, lancer `rustup default stable` dans une nouvelle fenêtre ;
  - `5_installer.ps1` ne détecte pas la combinaison de l'option `-Longueur` avec BioBio installé (§ 6).

Le kit a été relu ligne par ligne par un second relecteur, qui l'a confronté au code d'ACR Extra Stages et a corrigé cinq défauts (une option de ciel qui faisait échouer le contrôle final, les fins de ligne des retouches sous Windows, deux garde-fous sur le chemin du jeu, l'arrêt sur erreur). Un contrôle automatique de l'appariement des accolades, des chaînes et des variables est passé sur tous les scripts. Cela ne remplace pas une exécution.

## 9. Si l'export manque, ou pour une session Claude

- `0_controle.ps1` signale un `stage.json` ou un `collision.glb` absent. Il faut alors récupérer la dernière version du dépôt. Pour le régénérer, il faudrait lancer `scripts/09_export_stage_ir.py` (Python), qui a besoin du modèle 3D (`modele/terrain.glb`) et donc de toute la chaîne de `scripts/tout_lancer.sh`.
- Une session Claude ouverte sur le PC doit d'abord lire `pc/controle_avant_depart.md`, puis suivre les étapes ci-dessus dans l'ordre. Elle ne doit pas sauter l'étape 4 ni passer outre une ligne `FAIL`. Elle demande l'accord du directeur avant chaque installation de logiciel et avant l'étape 5.
