# Guide PC - Montée historique de Ceyreste dans Assetto Corsa Rally

**Rien de ce kit n'a été exécuté sous Windows ni dans le jeu.** Il reprend le kit du Grand Caunet, qui, lui, a roulé en jeu (route physique dès le 11/11/2026, 14 essais jusqu'au 17/11). Marques : **[vu GC]** = réglage jugé bon en jeu sur le Grand Caunet ; **[jamais vu]** = jamais vu en jeu, même sur le Grand Caunet ; **[neuf]** = propre à la montée, jamais exécuté.

Conventions : `<JEU>` = dossier d'installation du jeu ; `<ATELIER>` = dossier de travail de la montée, **sur le même disque que le jeu** (liens physiques), par défaut `<disque du jeu>\acrxs_ceyreste` ; `<PROJET>` = ce dossier `acr-montee-ceyreste`. Toutes les commandes se lancent depuis `<PROJET>`, dans PowerShell 7 (`pwsh`), jeu fermé, Steam hors ligne.

```powershell
$env:ACR_JEU = '<JEU>'              # sinon : emplacement Steam par défaut
$env:ACR_ATELIER = '<ATELIER>'      # facultatif
```

## 0. Ce qu'il faut savoir avant

- **Une seule des deux cartes à la fois.** La montée et le Grand Caunet remplacent la même variante hôte (Hafren South 1/2), la même table des variantes et la même cellule de décor. Le kit de la montée n'écrit jamais dans l'atelier du Grand Caunet (`acrxs`) ni dans son projet Unreal ; il ne retire ses conteneurs de `~mods` que par la bascule, avec copie vérifiée (§ 5).
- Version du jeu visée : build 25170642 (UE 5.6.1). Autre build : refaire le `.usmap` (étape 3) et prévenir.

## 1. Outils (une fois, 10 à 20 min)

| # | Commande | Durée | Contrôle |
|---|---|---|---|
| 1 | `pwsh -ExecutionPolicy Bypass -File pc\scripts\0_controle.ps1` | 1 min | « rien à signaler », build 25170642 |
| 2 | `pwsh -ExecutionPolicy Bypass -File pc\scripts\1_prerequis.ps1` (si 0 signale un logiciel absent) | 5-15 min | rouvrir la fenêtre |
| 3 | `pwsh -ExecutionPolicy Bypass -File pc\scripts\2_recuperer_acrxs.ps1` | 10-20 min | `acr-ref.exe`, `retoc.exe` dans `<ATELIER>\bin` ; 6 retouches appliquées |
| 4 | `pwsh -ExecutionPolicy Bypass -File pc\scripts\3_usmap.ps1` | 2-5 min | `<ATELIER>\mappings\acr_25170642.usmap` |

L'atelier de la montée est neuf : ces outils y sont reconstruits, sans toucher à ceux du Grand Caunet.

## 2. Données (sur le PC ou ailleurs)

Les produits légers sont versionnés ; s'ils manquent ou si le tracé change :

```powershell
python -m pip install -r requirements.txt
python scripts\tout_lancer.py --sans-rendus -- --sol photo     # 25-40 min la première fois (téléchargements IGN)
```

## 3. Étape 1 : route physique (sol, chrono, notes, obstacles)

| # | Commande | Durée | Contrôle avant essai |
|---|---|---|---|
| 5 | `pwsh -ExecutionPolicy Bypass -File pc\scripts\4_construire.ps1 -Noms -Ciel -Asphalte -Personnages` | 3-6 min | `stage-verify` : aucune ligne `FAIL` ; « Montée de Ceyreste : 3 020 m chronométrés, 534 portes, … notes » ; table : « notre conteneur passe devant », Tarmac / TarmacSnow / MonteCarlo / ≈ 3,02 km |
| 6 | `python pc\etape2_unreal\outils\relever_placement.py` | secondes | écrit `pc\etape2_unreal\releves\placement_etape1.json` (première fois) |
| 7 | `pwsh -ExecutionPolicy Bypass -File pc\scripts\bascule_vers_ceyreste.ps1 -SansDecor` | secondes | met de côté les conteneurs du Grand Caunet s'il y en a (copie + SHA-256), pose `zz_acrxs_ceyreste_P` et `zz_acrxs_ceyreste_table_9_P` |

Réglages repris : sol `TSD+`/`DBK+`/`GRS+`, obstacles, portes à 10 m, seuils de notes, pneus asphalte **[vu GC]** ; humidité de base 0, météo `MonteCarlo`, ligne idéale calculée, parc réduit, officiels **[jamais vu]** (paris des versions 19-21 du Grand Caunet). Les cellules d'officiels de Hafren (`-CellulesOfficiels`) ne sont pas passées au premier essai : leur report n'a jamais été vu en jeu. Parc d'assistance : sur le parking du Grand Caunet, au bout de la route (PK 3746) **[neuf]**.

**Essai 1 (10 min)** : Pays de Galles → Hafren South → variante 1/2 (« Montée de Ceyreste ») → Essais libres ; option « Adhérence de départ » = Optimale. Filmer tout le parcours. À juger : chargement, départ au Plan de Masse, chrono, intermédiaire PK 1500 (technique), arrivée PK 3000, arrêt PK 3700, notes dans les lacets (épingles de plus de 180°), murs invisibles, trous de sol. Tout défaut : capture + PK + côté.

## 4. Étape 2 : décor Unreal (après un essai 1 correct)

Prérequis : Unreal Engine **5.6.1** et un projet Unreal « acr » **propre à la montée**, `<ATELIER>\unreal\acr` (copie d'un projet factice vide préparé comme celui du Grand Caunet : `pc\etape2_unreal\projet\DefaultEngine_extrait.ini`, Nanite coupé). Ne jamais pointer `-Projet` vers le projet du Grand Caunet.

| # | Commande | Durée | Contrôle |
|---|---|---|---|
| 8 | `python scripts\tout_lancer.py --seulement 150 16` (sol « façon jeu », placement de l'étape 6) | 5-8 min | `paquet_unreal\manifeste.json`, `"erreurs": []` |
| 9 | `pwsh -ExecutionPolicy Bypass -File pc\etape2_unreal\scripts_pc\chaine_decor.ps1 -SansPaquet -Projet '<ATELIER>\unreal\acr'` | 55-75 min (1re import ≈ 1 h de plus) | dernière ligne de relecture : « RELECTURE CONFORME » ; conteneur `<ATELIER>\unreal\dist\zz_cey_cey_P.*` |
| 10 | `pwsh -ExecutionPolicy Bypass -File pc\scripts\bascule_vers_ceyreste.ps1` | secondes | pose aussi `zz_cey_cey_P` |

La chaîne du décor est celle du Grand Caunet **[vu GC]** (cellule toujours chargée `1LS8FPM8JIMX697U3QIPKC01K`, cuisson versionnée), mais avec un autre niveau, un autre conteneur et un autre placement **[neuf]**. Ensuite, pour les reconstructions : `pwsh -ExecutionPolicy Bypass -File pc\scripts\7_tout_refaire.ps1` (80-90 min).

## 5. Retour arrière

- Revenir au Grand Caunet : `pwsh -ExecutionPolicy Bypass -File pc\scripts\bascule_vers_grand_caunet.ps1` : retire les conteneurs de la montée et remet ceux du Grand Caunet depuis `<ATELIER>\bascule\grand_caunet_<date>\` (empreintes vérifiées ; la sauvegarde est gardée).
- Tout retirer : `pwsh -ExecutionPolicy Bypass -File pc\scripts\6_desinstaller.ps1` (route physique de la montée ; retirer aussi `zz_acrxs_ceyreste_table_9_P.*` et `zz_cey_cey_P.*` de `<JEU>\acr\Content\Paks\~mods`), ou Steam « Vérifier l'intégrité des fichiers ». Aucune archive d'origine n'est modifiée.
- Les versions construites restent dans `<ATELIER>\construction\dist` et `<ATELIER>\unreal\dist`.
