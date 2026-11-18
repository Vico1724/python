# État du projet (18/11/2026)

**Rien n'a encore tourné dans Unreal ni dans le jeu.** Sur le PC Windows : données régénérées et outils construits (§ PC). Le jeu et Unreal 5.6.1 ne sont pas encore installés.

## Sur le PC Windows (17-18/11/2026)

« Vérifié » ici = sortie relue sur le PC. Emplacements : dépôt `F:\Unreal\Projets\python` ; jeu prévu dans `F:\SteamLibrary\steamapps\common\Assetto Corsa Rally` (`ACR_JEU`) ; atelier de la montée `F:\acrxs_ceyreste` (`ACR_ATELIER`) ; journaux dans `F:\acrxs_ceyreste\journaux`. Aucun atelier ni conteneur du Grand Caunet sur ce PC (pas de `Z:\acrxs`).

| Point | État |
|---|---|
| Python | celui du PC est un 3.14 **32 bits** (inutilisable : étape 14 à 8 Go) ; environnement 3.12 64 bits `F:\Unreal\Projets\venv-ceyreste`, `requirements.txt` installé. Lancer `F:\Unreal\Projets\venv-ceyreste\Scripts\python.exe`, pas `python` (alias du Microsoft Store) |
| `1_prerequis` | PowerShell 7.7 et Rust 1.100 installés ; Windows SDK 10.0.26100 installé à part (manquait : voir corrections) ; .NET 10, Git, outils C++ (Visual Studio Community 2022) déjà là |
| `2_recuperer_acrxs` | ACR Extra Stages au commit `1324f07d`, retouches 0001 à 0006 appliquées, `acr-ref`, `acr-additive`, `retoc` 0.1.5 et `acr-mappings` construits et lancés (aide affichée) |
| `0_controle`, `3_usmap` | **non faits** : il faut le jeu |
| Données (`tout_lancer.py`, 01 à 16, `--sol photo`) | régénérées sur le PC ; export : 0 erreur, 533 portes, sol sous toutes, 27 notes sur 27 dans le bon sens, 3 024,39 m ; paquet : 0 erreur, 419 maillages, **263 943 instances** |

Commandes à lancer **depuis PowerShell**, pas depuis Git Bash : depuis Git Bash, `link.exe` désigne l'utilitaire `link` de Git et Rust échoue (« extra operand »).

### Corrections du kit faites sur le PC

- `2_recuperer_acrxs.ps1` n'était pas rejouable : le test « déjà appliquée » par retrait à blanc échoue pour 0005, que 0006 retouche ensuite (`StageBuild.cs`). Il remet maintenant à l'origine les seuls fichiers touchés par nos retouches puis réapplique la série ; toute autre modification l'arrête. Vérifié au 3e et au 4e lancement.
- `1_prerequis.ps1` ne contrôlait que le compilateur C++ ; Visual Studio déclarait le composant SDK sans ses bibliothèques. Ajout du Windows SDK 10.0.26100, contrôlé par la présence de `kernel32.lib`.
- Non corrigé, à savoir : l'étape 01 écrit « ECHEC » et continue quand une couche WFS échoue (constaté : `zone_de_vegetation` vide au premier passage). Relire la sortie de 01 avant la suite ; c'est ce qu'a fait la régénération retenue (20 couches, aucune en échec).

### L'écart de 87 instances (cause cherchée le 18/11)

- **Déterministe sur des entrées identiques** : deux passes 02 → 16 sur les mêmes téléchargements donnent le même paquet (263 943 instances, mêmes arbres, même semis) ; seuls diffèrent la date, la durée et l'en-tête gzip de `arbustes.csv.gz`. Le code de l'étape 16 n'est pas en cause.
- **Sensible aux entrées** : une chaussée qui diffère d'au plus 1 mm sur quelques points (arrondi entre machines) fait changer 21 arbres sur 17 900 ; avec le `chaussee_precise.csv` du cloud, l'étape 10 du PC redonne exactement les arbres du cloud (0 différence). Les 13 arbustes d'écart viennent d'ailleurs (couches BD TOPO retéléchargées, qui ont changé), cause précise non isolée.
- **Écartée** : l'étape 10 lit `stage.json` de la génération précédente (parc d'assistance) ; sans lui, arbres et instances sont identiques.
- Conséquence : la route physique, le relevé du placement et le décor doivent sortir **de la même génération**, sans retéléchargement entre les trois. Génération retenue : commit `19e1108` pour les fichiers versionnés (comparer avec `git diff --ignore-cr-at-eol`, Python écrivant en CRLF sous Windows) ; empreintes des fichiers non versionnés (terrain, lointain, sols, paquet) dans `F:\acrxs_ceyreste\determinisme\empreintes_B.txt`.

## Fait et vérifié dans le cloud (17/11/2026, Linux)

| Étape | Sortie | Vérification |
|---|---|---|
| Recherche du tracé | `docs/01_trace_et_sources.md` | sources citées ; départ certain (lieu), arrivée estimée |
| 01 collecte vecteurs IGN | `data/raw/*.geojson` (non versionné) | 20 couches, aucune en échec |
| 02 tracé | `data/processed/trace_es.*`, `axe_bdtopo_l93.csv` | D3 continue du PK −150 au PK 3746 ; points à moins de 0,4 m de l'axe ; `figures/carte_generale.png`, `zoom_depart.png` regardées |
| 03 rasters | MNT/MNS 0,5 m, ortho 20 cm (non versionnés), `mnt_couloir_1m.tif` | altitudes 186-406 m |
| 04 profil, virages | `profil_es.csv`, `virages_es.csv`, `synthese_es.json` | 214 → 366 m, +155 m, max 11,8 % ; `figures/profil_en_long.png` regardée |
| 05 couloir | `couloir/`, `inventaire_couloir.json` | pinède d'Alep 73 % (BD Forêt) |
| 07 / 07b chaussée au mètre | `chaussee_precise.csv` | contrôles de 07b tous passés (cassures > 5° de l'axe : 11 → 0 ; rayons ±0,8 % médian) ; axe juste sur les planches `figures/phase3/planche_*.png` ; **largeur : voir « non vérifié »** |
| 08 modèle 3D | `modele/route.glb`, `terrain.glb` | raccord route-terrain ≤ 3 mm, normales 100 % vers le haut |
| 11 route, ouvrages | `modele/route_habillee.glb`, `ouvrages.glb` | rendus `figures/phase4/route_*.png` regardés |
| 10 arbres | `arbres.csv` (17 900 dans le fichier versionné), `arbustes.csv.gz` (31 548 ; 31 535 sur le PC) | `figures/phase4/semis_synthese.png` : 75 % pin d'Alep, médiane 9 m |
| 09 export Stage IR | `export/stage_ir/ceyreste/` | `controle_ceyreste.json` : **aucune erreur** (534 portes, sol sous toutes, 27 notes dans le bon sens, 428 troncs) |
| 13 lointain | `modele/lointain.glb` | 0 arête de bord manquante ; horizon jusqu'à 38 km |
| 14 textures de sol | `modele/terrain_sol.glb` | terminé sans erreur |
| 15 vues de contrôle | `figures/phase5/vue_*.png` | vues de l'épingle du PK 893 et du raccord au Grand Caunet regardées |
| 15b sols du jeu | `modele/sols_jeu/` | proportions par matière écrites |
| 16 paquet Unreal (`--sol photo`) | `paquet_unreal/` (non versionné) | `manifeste.json` : 0 erreur, 419 maillages, 263 997 instances (263 910 au passage précédent : écart de 87 ; les passes du cloud ne sont pas rejouables, mais le mécanisme est établi sur le PC : § « L'écart de 87 instances »), écart terrain < 0,001 cm |
| 21 aperçu conducteur | `figures/apercu_conducteur/pk_*.jpg` | regardé |
| Autonomie | — | chaîne complète relancée avec `acr-grand-caunet/` rendu inaccessible : voir § Autonomie |

## Autonomie (essai du 17/11/2026)

`acr-grand-caunet/` a été déplacé hors du dépôt, puis `python scripts/tout_lancer.py --sans-telechargement -- --sol photo` et `python scripts/tout_lancer.py --seulement 6` ont été lancés depuis ce dossier : **15 étapes + 1 en 15,7 min, code de sortie 0, aucune erreur Python** ; contrôle de l'export sans erreur (27 notes sur 27 dans le bon sens), paquet sans erreur. Le dossier a ensuite été remis en place ; `git diff origin/claude/epic-shannon-a8f6rp -- acr-grand-caunet skill-speciale-rallye` est vide. Non couvert par cet essai : les téléchargements (01, 03 : faits plus tôt, même code) et le kit PC.

## Fait, non vérifié

- **Largeur de chaussée** : médiane 7,44 m mesurée (BD TOPO : 7 m) ; sur les planches, les bords détectés passent 1 à 2 m au-delà de l'enrobé visible par endroits (épingle du PK 893, PK 1300, PK 2187) : 72 % du linéaire n'est vu que par le LiDAR, sous les pins. Probablement surestimée d'environ 1 m. À corriger d'après une vidéo (`data/reference/chaussee_corrections.json`, même format que le Grand Caunet).
- Marquage (axe discontinu, rives) repris du Grand Caunet : l'axe discontinu se voit sur l'ortho, les rives non vérifiées.
- Notes du copilote : brouillon calculé, jamais confronté à une vidéo.
- Ponceau du PK ≈ 2024 : parapets supposés (béton 0,70 m).
- Paquet avec sol « façon jeu » (`--sol jeu`) : pas fait ici, il demande le placement relevé sur le PC.
- Kit PC (`pc/`) : scripts PowerShell et outils adaptés, **jamais exécutés** (pas de Windows ici).

## Non fait : relevés sans source

Glissières, parapets hors ouvrages, parois rocheuses, mobilier (panneaux, poteaux), carrefours fermés (Plan de Masse, débouchés, D3/D3D), aires et pistes, zone de départ. Les fichiers existent avec des listes vides. Il faut une vidéo embarquée ou des photos (Panoramax couvre la D3).

## À faire sur le PC

Dans l'ordre de `docs/guide_pc.md`. Faits le 18/11 : outils (sauf `.usmap`), données. Reste : installer le jeu (Steam, `F:\SteamLibrary`) et Unreal 5.6.1 (`F:\Unreal\UE_5.6`, à passer en `-Moteur` à `chaine_decor.ps1`) ; `0_controle` ; `3_usmap` ; route physique (`4_construire.ps1`) ; relevé du placement ; copie complète de `~mods` avant la première bascule ; essai 1 ; puis sol « façon jeu », décor Unreal dans un projet Unreal propre à la montée, cuisson, relecture, essai 2.

## Coexistence avec le Grand Caunet : impossible avec la voie actuelle

Les deux cartes remplacent **la même variante hôte** (Hafren South 1/2), **la même table des variantes** (`DT_TracksVariants`, livrée entière en `_9_P`) et **la même cellule de décor** (`1LS8FPM8JIMX697U3QIPKC01K`). Installées ensemble, l'une masquerait l'autre de façon imprévisible. Choix fait : **bascule propre** :

- noms distincts partout : `ceyreste_rally_01_route_0`, `zz_acrxs_ceyreste_P`, `zz_acrxs_ceyreste_table_9_P`, `zz_cey_cey_P`, niveau `/Game/Environments/MonteeCeyreste`, atelier `acrxs_ceyreste`, projet Unreal à part ;
- `5_installer.ps1` refuse d'installer si un conteneur du Grand Caunet est présent ;
- `bascule_vers_ceyreste.ps1` copie les conteneurs du Grand Caunet dans `<ATELIER>\bascule\grand_caunet_<date>\`, vérifie les SHA-256, puis seulement les retire et pose la montée ; `bascule_vers_grand_caunet.ps1` retire la montée et remet les fichiers sauvegardés à l'identique (sauvegarde gardée). Jamais exécutés.

Pistes de coexistence, **non validées** : (1) une autre spéciale hôte pour la montée (autre variante d'une autre spéciale : chemins de `BakedData`, cellule, table de notes à lire dans le catalogue et à essayer en jeu) ; il resterait la table des variantes, unique, qu'il faudrait livrer avec les deux lignes modifiées à la fois ; (2) le registre de menus (`zz_cey_registre_P`, voie « ajout aux menus » d'ACR Extra Stages), jamais installé même pour le Grand Caunet.

## Inconnues et décisions pour l'utilisateur

1. **Longueur et arrivée** : 3,0 km retenus (fiche de l'organisateur) ; 3,1 et 3,5 km aussi publiés. Une vidéo embarquée trancherait.
2. **Ligne de départ** : au carrefour du Plan de Masse, ±50 m.
3. **Parc d'assistance du jeu** : placé sur le parking du Grand Caunet, au bout de la route (le vrai paddock est au village, hors tracé). Le garder, ou le mettre au départ ?
4. **Points techniques** : intermédiaire au PK 1500 et zone d'arrêt au PK 3700, absents de l'épreuve réelle (non chronométrée).
5. Faut-il viser la coexistence (autre hôte, travail en jeu) ou la bascule suffit-elle ?
6. Les relevés de site (glissières, murs, parapets, panneaux) attendent une vidéo ou des photos.
