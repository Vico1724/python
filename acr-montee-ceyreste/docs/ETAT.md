# État du projet (18/11/2026)

> **Affinage d'après le réel du 18/11/2026 (cloud)** : tracé et largeur vérifiés, bord de route relevé sur Panoramax (87 objets), chaîne 07 → 16 régénérée. Détail : `docs/03_affinage_reel.md` et § « Affinage du 18/11/2026 » ci-dessous. **Pour le PC : cette régénération change la chaussée (largeur minimale, PK 444-468), les ouvrages, le semis et le paquet ; la « génération retenue » `19e1108` n'est plus la dernière.** Avant la route physique, relancer `tout_lancer.py --depuis 7 -- --sol photo` sur le PC à partir de ce commit (même règle qu'avant : route physique, relevé du placement et décor de la même génération).

> **Troisième passe du 18/11/2026 (cloud) : murs, murets, clôtures et bord de route.** Détail, registre des 156 tronçons de 50 m × côté et chiffres : `docs/03_affinage_reel.md` § 9. Relevé exhaustif sur 262 images (53 planches lues), 81 éléments + 5 objets du départ ; murs et murets 1 302 → 2 201 m, clôtures, haies et portails 0 → 1 033 m ; 48 % de la longueur nouvelle calée au mètre (cadastre ou LiDAR). Nouveaux scripts 36 (relevé), 37 (géométrie, dans la chaîne après 31), 38 (visibilité), 39 (panneaux de l'export neutre, dans la chaîne). **Pour le PC : voir « À faire par la session du PC (troisième passe) » ci-dessous.** Chaîne 11 → 16 relancée (`--sol photo`, sans téléchargement) : export Stage IR **0 erreur**, 532 portes, 27 notes sur 27 dans le bon sens, 3 023,5 m, 7 838 obstacles (dont 968 `PM_WallBasic` et 70 `PM_WallBush` de clôtures et haies), 0 retiré sur la chaussée ; paquet **0 erreur**, 566 maillages (81 de la famille `clotures`), 243 480 instances ; export neutre **CONFORME** (24 glb, 229 Mo, non versionné). Planches (regardées) : `figures/affinage/photo_rendu/depart_plan_de_masse.jpg`, `depart_plan_de_masse_avant_apres.jpg`, `approche_parking_m110`, `approche_muret_m70`, `approche_oliveraies_100`, `approche_oliveraies_170`, `approche_grillage_250`, `maison_m122`, `maison_2854`, `hameau_2840`, `hameau_3200`, `soutenement_2120`, `soutenement_2880`, `soutenement_3510`. Défauts vus et non corrigés : façades des maisons nues (on ne reconnaît pas les maisons), talus du rendu de contrôle peints d'une roche claire uniforme, cadrage de `soutenement_2120` décalé (rendu tourné vers l'intérieur de la courbe).

> **Quatrième passe du 19/11/2026 (cloud) : façades des bâtiments vus de près, terrain et silhouette du village.** Détail : `docs/03_affinage_reel.md` § 10. Les 35 bâtiments de premier plan (30) et de plan moyen (5) ont chacun un relevé versionné `data/reference/facades/<cleabs>.json` (images sources citées), lu par `31_bati.py` (géométrie : `scripts/facades.py` ; outils de relevé : `scripts/40_facades.py`). **12 bâtiments ont au moins une façade vue et relevée** (volumes, toit, génoise, enduit mesuré, ouvertures) ; **23 sont cachés sur toutes les images** (haies, murs, arbres, garrigue) : volume LiDAR gardé, teinte de toit de l'ortho, aucune ouverture. Posés : **10 ouvertures, 6 volets, 9 éléments** (auvents, cheminées, conduit, conteneur et armoire de l'abribus) ; abribus du départ ouvert avec banc ; ruine de pierre sèche (PK 3181) ; cabane de planches (PK 2061). **Terrain « en pointes » du village : cause trouvée et corrigée** (le MNH du LiDAR HD, ajouté à la surface lointaine au-delà de 450 m, contient les bâtiments : chaque sommet de 10 m tombé sur un toit montait de 4 à 10 m ; supprimé dans l'emprise bâtie du village, `13_paysage_lointain.py`). Toits du village : 4 teintes mesurées sur l'ortho au lieu d'une tuile rouge uniforme. Silhouette : depuis la route (PK -140, -50, 20), le village est caché ou très bas sur les photos et le clocher n'y est pas visible ; le rendu le montre au même endroit. Planches regardées : `figures/affinage/facades/*.jpg` (13 bâtiments + `depart_synthese_4_directions.jpg`), `figures/affinage/silhouette/*.jpg`. Chaîne 31 → 16 relancée : export **0 erreur** (532 portes, 27 notes sur 27, 3 025,37 m) ; paquet **0 erreur**, 640 maillages (78 `batiments`, 22 `village`), 243 480 instances ; export neutre **CONFORME**. **Pour le PC : relancer `tout_lancer.py --depuis 31 -- --sol photo` ; aucun changement de code côté PC** (voir « À faire par la session du PC (quatrième passe) »).

> **Cinquième passe du 19/11/2026 (cloud) : carrefour du départ, panneaux, poteaux, jardins, terrain au pied du mur ; contrôle chiffré des maisons.** Détail : `docs/03_affinage_reel.md` § 11. Nouveau relevé versionné `data/reference/depart_carrefour.json` (chaque objet cite ses images Panoramax), nouveau script **`41_carrefour_depart.py`** (dans la chaîne, après 37) : voie latérale « Voie Romaine » et arrêt de bus (312 m² d'enrobé), trottoir, îlot long, îlot court et parvis de l'abribus en enrobé rouge à bordures (213 m²), marquage (liserés blancs, « BUS », zigzag et tirets jaunes, deux lignes de cédez-le-passage, passage piéton), **9 panneaux** (mât de jalonnement D 3 / SIGNES / CAUNET / Circuit du Castellet, B1 ×2, panonceau « SAUF … BUS », C13a, AB3a, C20a, B21, B14 « 50 », B13 « 19 t »), **6 poteaux** (3 béton dont 1 à transformateur et 2 à lanterne, 3 bois dont 1 à jambe de force) et 71 m de lignes, 3 coffrets ou boîte aux lettres, 2 potelets, haies des jardins (82 massifs d'après le MNS), bougainvillier, laurier-rose, muret blanc à grillage au-dessus du mur. **Terrain plat jusqu'au pied du mur** (talus supprimé) : `aplanissements.py` (plateforme du carrefour) + ligne de rupture dans `08_modele_3d.py`. Le mur de pierre de la voie latérale, posé à 4,5 m du bord (au milieu de la voie), suit maintenant la marche du LiDAR (2,5 m de haut). EB20/EB10 et panneau jaune remis en travers de la route avec leurs faces (EB10 « CEYRESTE » au dos). Quatrième passe reprise : porte de garage du PK 3226, fenêtre à barreaux de la cabane du PK 2061, mur à vigne vierge (PK −72 et nouveau mur devant la maison du PK −52). **Contrôle des 30 maisons de premier plan** (`42_controle_bati.py`) : faîtage plafonné au MNS absolu (7 maisons du bord, 147 du village), pente de toit du PK −52 corrigée (+1,7 m → +0,1 m). Chaîne 08 → 16 relancée : export **0 erreur** (532 portes, 27 notes sur 27, 3 025,37 m, 7 740 obstacles, 0 retiré sur la chaussée) ; paquet **0 erreur**, 696 maillages (51 de la nouvelle famille `depart`), 243 414 instances ; export neutre **CONFORME** (26 glb). Planche regardée : `figures/affinage/facades/depart_synthese_4_directions.jpg` (+ `pk-0052`, `pk+3226`, `pk+2061`). **Pour le PC : relancer `tout_lancer.py --depuis 8 -- --sol photo`** (voir « À faire par la session du PC (cinquième passe) »).

> **Sixième passe du 19/11/2026 (cloud) : chaussée relevée par tronçon de 50 m (marquage et usure), textures, végétation, maisons, panneaux du haut.** Détail : `docs/03_affinage_reel.md` § 12. Nouveau relevé versionné `data/reference/chaussee_releve_50m.json` (73 tronçons du PK 100 au PK 3750, 121 éléments d'usure, chacun avec ses images Panoramax ; outil `scripts/43_chaussee_releve.py`) ; nouvelles étapes **`44_usure_chaussee.py`** (fissures, faïençage, pièces, traces, bords : maillages minces pour l'aperçu et l'export neutre ; **décalques du jeu** dans le paquet, par 16) et **`45_vegetation_bord.py`** (4 014 touffes d'herbe relevées par zone, 16 massifs sur le LiDAR, 3 bacs ; famille de paquet nouvelle `abords`) ; `scripts/variation.py` (teinte par sommet contre la répétition des textures, aperçu et export neutre). Marquage : axiale T3 et rives T2 confirmées, rive gauche continue dans la zone d'arrêt, rectangles des PR 6 et PR 8, ligne de cédez-le-passage du PK 2938 ; **zone hachurée « Lion d'Or » retirée** (reprise du Grand Caunet, à 2,7 km de là). Maisons : les 3 « écarts non corrigés » et les emprises gonflées du PK −149 étaient des **erreurs de mesure** de 42 (corrigé), test d'assise refait (0 pied flottant). Panneaux : PR 6 trouvé (PK 1113), A15b + A1c au PK 3672, AB3a du PK 3198, plaques de l'export neutre tournées vers les usagers. Grillage du départ : position confirmée par l'orthophoto. Départ : haies sans « dents », bougainvillier et rouge des îlots adoucis. Chaîne 11 → 16 relancée : export **0 erreur** (532 portes, 27 notes sur 27, 3 025,37 m) ; paquet **0 erreur**, 704 maillages, 243 415 instances, 475 décalques ; export neutre **CONFORME**. Planches regardées : `figures/affinage/sixieme_passe/*.jpg` (13 PK + grillage). **Pour le PC : relancer `tout_lancer.py --depuis 11 -- --sol photo`** (voir « À faire par la session du PC (sixième passe) »).

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

## Deuxième passe du 18/11/2026 : bâti, décor, chaussée, OSM, export neutre (cloud)

Détail : `docs/03_affinage_reel.md` § 8 et `docs/04_reutilisation_autre_jeu.md`. **Rien n'a été vu en jeu ni dans Unreal.**

**Choix par défaut, NON CONFIRMÉS par l'utilisateur** (pour avancer à moindre coût, réversibles) :
- décision 7 : option A, village en décor lointain (936 bâtiments en volumes simples, sans collision ; emprise jouable inchangée) — **décidée par l'utilisateur le 18/11/2026** (« En decore ok mais les zone visible doivent etre vraiment bien faite ») ;
- décision 8 : 35 maisons du bord de route en volumes simples, avec collision pour les 21 à moins de 15 m de la chaussée ;
- décision 9 : rubalises, public et commissaires non posés (aucune photo d'édition passée trouvée, deux recherches).

**Où se trouve chaque élément :**
- **présent dans le paquet `paquet_unreal/` et importable tel quel** (familles lues de façon générique par `construire_niveau.py` : acteurs StaticMesh par dossier de destination, groupes d'instances par maillage du jeu) : familles `batiments` et `village` (`Buildings/Meshes`, `Village/Meshes`) ; murs, parapets, glissières, ponceaux (`ouvrages`) ; parois rocheuses ; rocaille ; 30 objets de mobilier (14 poteaux, 8 séparateurs en plastique, 3 triangles, 3 bornes, 2 balises J4) ; décalques de chaussée redosés ;
- **présent, mais demandant une étape côté PC** : les maillages du jeu nouvellement désignés par le mobilier (`SM_PlasticBarrierAFix`, `SM_TrafficSignFraDangerA`, `SM_MileMarkerA`, `SM_TrafficSignFraCurveMarkerD`, `SM_MonPylonC11`) n'existent dans le projet Unreal que comme factices. Il faut relancer `outils/liste_factices.py` puis `creer_factices.py`, qui les lisent de façon générique dans `mobilier_bord_de_route.json`. Aucun changement de code à faire côté PC, d'après la lecture de `construire_niveau.py` (l. 377-386, 594-640, 722-757) et de `liste_factices.py` (l. 213-220) ;
- **visible seulement dans les aperçus** : rien de ce qui est posé. Les arbres des vues `figures/phase5/` sont des figurants calculés, pas ceux du jeu.

### À faire par la session du PC (sixième passe, 19/11/2026)

1. Récupérer ce commit, puis relancer **`tout_lancer.py --depuis 11 -- --sol photo`** (11 : marquage, enrobé plus clair, teintes par sommet ; 12, 31 : pieds de mur ; 37, 41 ; **44 et 45, nouvelles étapes** ; 39 ; 10 : nouvelle zone d'essences au PK 3226 ; 09, 13, 14, 15, 15b, 16). Le terrain (08) ne change pas. Même règle qu'avant : route physique, relevé du placement et décor de la même génération, sans retéléchargement. `modele/usure_chaussee.glb`, `vegetation_bord.glb` et `abords.glb` ne sont pas versionnés (lourds) : ils sortent de 44 et 45.
2. **Nouvelle famille du paquet `abords`** : acteurs StaticMesh `SM_MonteeCeyresteRoadside_<Matière>_<tronçon>` dans `/Game/Environments/MonteeCeyreste/Roadside/Meshes` (massifs de jardin et bacs), lue de façon générique par `construire_niveau.py` (dossier de destination) : aucun changement de code attendu (non vérifié : `construire_niveau.py` n'a jamais tourné). Matériaux nouveaux, variantes modèle (M_Simple) avec leur texture : `MI_GC_Feuillage_bambou`, `MI_GC_Bac_<rrggbb>`, `MI_GC_Roue_noire` (`Feuillage_haie` existe déjà, famille `depart`).
3. **Nouveaux groupes de décalques** (DecalActor, composant « decalques », même maître que les autres) : `GC_Decalques_fissures` (`MI_AsphaltDecalCracks_01`), `fissures_b` (`_02`), `fissures_longues` (`MI_AsphaltDecalCracksLong_01`), `raccord` (`MI_AsphaltTransitionDecal`), tous présents au catalogue ; plus des traces, de la terre, des gravillons et des aiguilles aux PK relevés. **Gabarits et couleurs des fissures et du raccord supposés** : à regarder en jeu (taille, contraste, orientation de la fissure longue le long de la route). Relancer `liste_factices.py` / `creer_factices.py` seulement si le manifeste signale un parent absent.
4. À regarder en jeu : décalques de fissures sur l'enrobé ancien (PK 100-1855 et 2700-3750) ; absence de différence d'enrobé entre le PK 1855 et le PK 2700 (l'enrobé récent sombre n'a pas d'équivalent dans le paquet) ; massifs de la famille `abords` (géométrie bosselée simple, pas des arbustes du jeu).

### À faire par la session du PC (cinquième passe, 19/11/2026)

1. Récupérer ce commit, puis relancer **`tout_lancer.py --depuis 8 -- --sol photo`** : le terrain change au carrefour du départ (08 : plateforme et ligne de rupture au pied du mur), donc tout ce qui suit (11, 12, 31, 37, 41 nouvelle étape, 39, 10, 09, 13, 14, 15, 15b, 16). Même règle qu'avant : route physique, relevé du placement et décor de la même génération, sans retéléchargement.
2. **Nouvelle famille du paquet `depart`** : acteurs StaticMesh `SM_MonteeCeyresteStartJunction_<Matière>_<tronçon>` dans `/Game/Environments/MonteeCeyreste/StartJunction/Meshes`, lue de façon générique par `construire_niveau.py` (dossier de destination) : **aucun changement de code attendu** (non vérifié en exécutant `construire_niveau.py`, qui n'a jamais tourné). Matériaux nouveaux, tous variantes modèle (M_Simple) avec leur texture : `MI_GC_Enrobe_neuf`, `Enrobe_rouge`, `Bordure_beton`, `Peinture_blanche`, `Peinture_jaune`, `Panneau_*` (faces redessinées), `Dos_panneau`, `Mat_galva`, `Poteau_beton`, `Poteau_bois`, `Lierre`, `Lanterne`, `Transformateur`, `Cable`, `Coffret_*`, `Boite_jaune`, `Potelet_vert`, `Feuillage_*`. `enduit_blanc` et `grillage` reprennent ceux de 37 (même image ; `grillage` hérite déjà du grillage du jeu, voir la troisième passe). Relancer `liste_factices.py` / `creer_factices.py` seulement si le manifeste signale un parent absent.
3. **Collision (09)** : `modele/depart_collision.glb` donne le sol de roulage de la voie latérale, du trottoir, des îlots et du parvis (TSD+, 3 cm au-dessus du terrain) et les obstacles (poteaux béton `PM_WallConcrete`, poteaux bois, mâts et potelets `PM_WallBasic`). Le trottoir et les îlots ont une marche de 14 cm sans face verticale dans le sol physique : à essayer en jeu.
4. À regarder en jeu : teinte de l'enrobé rouge (photo : rouge éteint), lisibilité des panneaux, câbles (rayon 9 mm), massifs de feuillage des jardins (géométrie bosselée simple, pas des arbustes du jeu).

### À faire par la session du PC (quatrième passe, 19/11/2026)

1. Récupérer ce commit, puis relancer `tout_lancer.py --depuis 31 -- --sol photo` (31 : bâtiments relevés ; 13 : terrain lointain du village sans pointes ; 15, 16). Même règle de génération qu'avant.
2. **Aucun changement de code côté PC** : les nouveaux maillages restent dans les familles `batiments` et `village` (`Buildings/Meshes`, `Village/Meshes`). Matériaux nouveaux : `MI_GC_Enduit_<rrggbb>` et `MI_GC_Soubassement_<rrggbb>` héritent du béton du jeu (`MI_MonBolConcreteWallsA`, comme `MI_GC_Enduit_maison`, réglages calculés par `teinte_enduit_du_jeu` de 16 et écrits dans le manifeste) ; `MI_GC_Tuile_<rrggbb>`, `Volet_*`, `Menuiserie_*`, `Verre`, `Genoise`, `Faitiere`, `Appui`, `Porte_*`, `Metal_*`, `Bardage_*`, `Tole_*` sont des variantes modèle (M_Simple) avec leur texture, comme `MI_GC_Tuile`. Le parent béton est déjà un factice : relancer `liste_factices.py` / `creer_factices.py` n'est nécessaire que si le manifeste le signale.
3. À regarder en jeu : vitrages (verre sombre en retrait de 18 cm), volets, génoises, et la teinte des enduits relevés sur le béton du jeu (non vérifiée).

### À faire par la session du PC (troisième passe, 18/11/2026 au soir)

1. Récupérer ce commit, puis relancer `tout_lancer.py --depuis 11 -- --sol photo` (11 : couronnements de pierre et bornes corrigées ; 12 et 31 : toits à croupes lus sur le LiDAR ; 37 et 39 : nouvelles étapes ; 09 : nouveaux obstacles `PM_WallBasic` et `PM_WallBush` ; 16 : nouvelle famille). Route physique, relevé du placement et décor de la même génération, comme avant.
2. Nouvelle famille du paquet **`clotures`** : acteurs StaticMesh `SM_MonteeCeyresteFence_<Matière>_<tronçon>` dans `/Game/Environments/MonteeCeyreste/Fences/Meshes`, lue de façon générique par `construire_niveau.py` (dossier de destination) : **aucun changement de code** pour l'importer.
3. Matières nouvelles : `MI_GC_Pierre_seche` et `MI_GC_Pierre_couronnement` ont pour parent la pierre du jeu (`MI_MonBolStoneWallsA`, clé `parent` de `matieres_du_jeu.json`, déjà lue par `liste_factices.py`) ; relancer `outils/liste_factices.py` puis `creer_factices.py`. **`MI_GC_Grillage` hérite de `/Game/Props/Walls/ChainlinkFenceA/MI_ChainlinkFenceA1`** (clé `herite_de`) : ce matériau n'a pas de factice aujourd'hui. **Changement exact à faire dans `pc/etape2_unreal/outils/liste_factices.py`** (je n'ai pas modifié `pc/`) : ajouter à la liste `PARENTS_DU_JEU`, sur le modèle de l'entrée `MI_MonBolConcreteWallsA` (l. 47), une entrée `{"objet": "/Game/Props/Walls/ChainlinkFenceA/MI_ChainlinkFenceA1", "parent": M_SIMPLE (à confirmer : dans `releves/variantes.json` ce matériau est rangé avec les variantes de M_Simple à static switch « Simple_* » et masque d'opacité 0,3333), "pour": ["MI_GC_Grillage"], "pourquoi": "grillage des clôtures (37_clotures.py)"}`, puis relancer `liste_factices.py` et `creer_factices.py`. Sans cela, `construire_niveau.py` signalera le parent absent et mettra le matériau de secours (grillage plein au lieu d'ajouré). À vérifier en jeu : échelle de la maille (notre dépliage : 0,5 m par unité).
4. Optionnel : `python scripts/38_visibilite.py` (analyse, 1 min) et `python scripts/33_export_neutre.py`.

### À faire par la session du PC (passes précédentes)

1. Récupérer ce commit, puis relancer `tout_lancer.py --depuis 7 -- --sol photo`. La nouvelle étape 31 (bâti) est dans la liste, entre 12 et 10. Elle demande `data/raw/lointain/mnt_lidarhd_2m.tif` (déjà téléchargé par 13).
2. Relancer `liste_factices.py` puis `creer_factices.py` (voir ci-dessus).
3. Comparer `manifeste.json` avec celui de la génération `19e1108` (voir la note sur les instances).
4. Optionnel : `python scripts/33_export_neutre.py` produit l'export neutre (environ 1 Go, non versionné).

**Instances.** Génération `19e1108` refaite dans le cloud : 238 666. Passe 1 de l'affinage : 243 457. Passe 2 : voir le compte rendu de 16. Par famille, de `19e1108` à la passe 1 :

| Famille | Écart |
|---|---|
| rocaille (pierres au pied des parois, nouvelle famille) | +4 723 |
| glissières du jeu | +118 |
| mobilier | +8 |
| arbres | +7 |
| arbustes | +37 |
| garrigue | −78 |
| versants | −35 |
| herbes | +11 |

**La « baisse de 263 943 à 243 457 » n'en est pas une** : le même commit `19e1108`, refait ici, donne 238 666, soit 25 277 de moins que sur le PC. L'écart vient de la machine, pas de l'affinage. Cause probable : des familles dont le nombre dépend de fichiers non versionnés présents sur le PC (sols « façon jeu », herbes) ; non isolée.

## Affinage du 18/11/2026 (cloud, Linux)

Détail et chiffres : `docs/03_affinage_reel.md`. **Rien n'a été vu en jeu ni dans Unreal.**

| Point | Résultat | Vérifié (sortie regardée) |
|---|---|---|
| Axe | à 0,25 m en médiane de la ligne axiale peinte (21 points sur l'ortho 20 cm) ; BD TOPO et OSM s'écartent autant entre eux (0,83 m) que de notre axe (0,74 / 0,49 m) ; seul écart > 0,5 m : PK 444-468 (1,0-1,2 m), **corrigé** | `figures/affinage/verif_trace.png`, `verif_axe_zooms.jpg` |
| Largeur | surestimation d'1 m **non confirmée** : entre rives 6,93 m (médiane de 20 mesures), enrobé 8,4 m, 07 = 7,6 m aux mêmes points ; au contraire **sous-estimée sous les pins** (4,8-5,6 m) : minimum de 6,4 m imposé (`data/reference/chaussee_corrections.json`) ; médiane inchangée 7,44 m, 5e centile 5,38 → 6,37 m ; contrôles de 07b passés | `verif_largeur_bandes_1..4.jpg` |
| Relevé du bord de route | Panoramax (Région Sud, 08/09/2025, 360°, Etalab 2.0) sans trou sur tout le parcours ; 87 objets (6 glissières, 32 murs et parapets, 3 têtes de ponceaux, 25 parois, 20 ponctuels), 36 positionnés au mètre par le LiDAR, 51 approximatifs | `figures/affinage/releve_panoramax.png`, 31 planches (non versionnées) |
| Fichiers de relevé remplis | `glissieres.json`, `ouvrages_parapets.json`, `parois_rocheuses.json`, `mobilier_bord_de_route.json` (+ `releve_panoramax_2025.json`, `photos_rue_panoramax.csv`) ; murs BD TOPO génériques remplacés par le relevé ; marquage : tronçons du Grand Caunet retirés, axiale T3 et rives T2 sur toute la D3 | sortie de 11 relue |
| Essences | oliveraies et chênes verts du PK 60-235 (relevé Panoramax) : olivier 95, chêne vert 68, pin 46 arbres à moins de 45 m | `arbres.csv` |
| Accotements (sol « façon jeu ») | terre rouge 60 % et herbe sèche 30 % au lieu de l'herbe verte du Grand Caunet | non regardé (15b sans aperçu dans cette passe) |
| Chaîne 07 → 16 (`--sol photo`, sans téléchargement) | 15 min 55 s, code 0 ; export : **0 erreur**, 532 portes, 27 notes sur 27 dans le bon sens, 3 025,37 m, demi-largeur minimale 3,16 m (2,41 avant) ; paquet : **0 erreur**, 468 maillages, **243 457 instances** (263 943 avant), 20 parois rocheuses (1 187 m), 4 723 pierres de rocaille | `controle_ceyreste.json`, sortie de 16 |
| Comparaisons photo / avant / après | 5 planches, PK ≈ 519, 807, 1147, 1286, 2012 : `figures/affinage/comparaison/comparaison_pk_*.jpg` | regardées (voir § suivant) |
| Village | préparé, rien de construit : deux options chiffrées | `figures/affinage/village_ceyreste.png` |

Baisse des instances (−20 486) : non isolée famille par famille (le manifeste précédent n'est pas versionné) ; causes attendues : herbes et arbustes retirés des parois et des pieds de murs nouvellement posés, chaussée élargie sous les pins (1 953 instances retirées sur la chaussée). À comparer sur le PC avec `manifeste.json` de la génération `19e1108`.

Ce que montrent les planches (aperçu hors jeu, formes seules) : glissière du PK 500-580 et mur-parapet du PK 1120-1188 présents là où la photo les montre ; paroi du PK 1147 rendue en blocs de roche sur le talus (la photo montre des bancs calcaires plus continus) ; têtes du ponceau 2016 plus basses (0,55 m) comme sur la photo. Écarts restants vus : la glissière posée au PK 519 est dessinée comme une lisse unie sur poteaux minces (pas de maillage du jeu), les murs sont des pavés unis (texture de pierre seulement dans le paquet), aucune végétation dans l'aperçu.

Ce qui n'a pas pu être fait ou vérifié : sous-agents de description d'images (outil absent de la session : tout a été lu par l'agent lui-même, avec 20 agrandissements de contrôle) ; déclaration de manifestation (dossier 98930 : erreur 503) et article de La Provence (non chargeable) ; aucune limitation de vitesse vue en montée ; texte de 5 panneaux ; poteaux électriques non comptés ; maisons non posées (voir décision 8).

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

- **Largeur de chaussée** : vérifiée le 18/11/2026 sur l'ortho (voir § Affinage) ; reste non vérifiée sous les pins là où aucune ligne n'est visible (le minimum de 6,4 m y est une borne, pas une mesure).
- Marquage : axiale et rives discontinues vues partout (Panoramax) ; type des traits mesuré en 4 points seulement.
- Notes du copilote : brouillon calculé, jamais confronté à une vidéo.
- Ponceau du PK ≈ 2016 : têtes de béton de 0,55 m vues sur Panoramax ; hauteur à l'œil.
- Paquet avec sol « façon jeu » (`--sol jeu`) : pas fait ici, il demande le placement relevé sur le PC.
- Kit PC (`pc/`) : scripts PowerShell et outils adaptés, **jamais exécutés** (pas de Windows ici).

## Non fait : relevés sans source

Relevés sur Panoramax le 18/11/2026 : glissières, parapets, murs, parois, panneaux et balises (voir § Affinage). Restent vides : carrefours fermés (Plan de Masse, débouchés, D3/D3D), aires et pistes, zone de départ, objets du jour de course (rubalises, public, commissaires, parc de départ).

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
6. Relevés de site faits sur Panoramax (18/11/2026) ; une vidéo embarquée reste utile pour les lignes et les objets du jour de course.
7. **Village de Ceyreste** : **décidé le 18/11/2026 : option A, en décor** (mots exacts : « En decore ok mais les zone visible doivent etre vraiment bien faite »). Ce qu'un pilote voit doit être soigné : voir `03_affinage_reel.md` § 9 (visibilité calculée ; façades de premier plan encore nues).
8. **Maisons au bord de la route** : posées en volumes simples (choix par défaut) ; à remplacer par des assets ? Les 10 plus visibles sont listées dans `03_affinage_reel.md` § 8.
9. **Ambiance du jour de course** : rubalises au-dessus des épingles 893, 1517, 2150, 2950 (déduit d'une description générale, pas de photo) : à poser ou non ?

## Demandes de l'utilisateur à traiter

- 18/11/2026, mots exacts : « il faudra pense au villange de ceyreste en bas aussi ». À faire : étendre la carte vers le bas pour inclure le village de Ceyreste (approche depuis le village jusqu'au départ du Plan de Masse, bâtiments, rues, salle polyvalente et paddock réel derrière la mairie). Aujourd'hui la carte commence au Plan de Masse et le village n'est pas modélisé. Cela rouvre la décision 3 (parc d'assistance au village plutôt qu'au Grand Caunet). **Préparé le 18/11/2026** (`docs/03_affinage_reel.md` § 5, `scripts/28_village.py`) : emprise, itinéraire, bâtiments, deux options chiffrées ; rien de construit, emprise jouable inchangée ; décision prise : option A (décision 7).
- 18/11/2026, mots exacts : « Le tacer a l'air fidel il lanque les murret cloture et tout quand même ». **Traité le 18/11/2026** (troisième passe, `03_affinage_reel.md` § 9) ; restent : façades de premier plan, terrain du village, chaînes DFCI, regards.
- 18/11/2026, mots exacts : « En decore ok mais les zone visible doivent etre vraiment bien faite ». **Traité en grande partie** (§ 9 et § 10) : visibilité calculée, toits relus sur le LiDAR, clôtures posées ; façades relevées sur photo pour les 12 bâtiments dont une façade se voit (23 cachés), terrain du village corrigé, silhouette contrôlée. Restent : abords de jardin (végétation, terrasses) non posés au-delà des clôtures ; quelques ouvertures vues mais non posées faute de position sûre (listées § 10).
- 19/11/2026, mots exacts (transmis par le coordinateur) : « il y a encore des maisons buggées, des trucs pas très bien modélisés, pas très bien intégrés, des textures encore trop répétitives, des maisons un peu plus grandes que la normale peut-être par moment, ou il manque des murets, des éléments devant, des arbres. Ça manque un peu de végétation, de petits éléments, de panneaux, de marquage au sol, de routes abîmées. » **Traité en partie** (`03_affinage_reel.md` § 11, puis § 12 pour la sixième passe : chaussée relevée et rendue sur tout le tracé, textures variées par sommet, végétation relevée, contrôle des maisons corrigé, panneaux du haut) : zone de départ refaite (carrefour, panneaux, marquage, poteaux, petits éléments, jardins) ; contrôle chiffré des 30 maisons de premier plan, hauteurs plafonnées au LiDAR ; murs à vigne vierge ; décalage d'UV par élément pour les murs. **Restent** : textures (répétition à l'intérieur d'un long mur, des enduits, tuiles et du sol : non traitée), végétation de jardin hors du départ (ex. PK 3226 : grand arbre et haie devant la maison, absents), usure de chaussée et marquage hors du départ (pièces et fissures relevées mais non rendues, voir § 8), 3 maisons encore plus hautes que le LiDAR de 1,1 à 1,5 m (§ 11).
- 18/11/2026, mots exacts : « affine quand meme les eleemnt la carte la route les sols les murret lais maison si ya avec les elements relel verifie le tracer de al route, verifei les panneau aussi pour renforcer l'imretion le paysage au alentours ». **Traité le 18/11/2026** (`docs/03_affinage_reel.md`) : tracé et largeur vérifiés et corrigés, murets, murs, glissières, parois et panneaux relevés sur Panoramax et posés, sols (essences, accotements) ajustés ; maisons non posées (décision 8). Jamais vu en jeu.
- 18/11/2026, mots exacts : « queque screen coté ceyreste aussi stp pense a bien contnuer le decore les arbre aussi a palcer les torn 'abre tout ce genre de chsoes » ; « pour tout les objet on reste sur batimetn et tout ca peut etre le top mais si possible de les avoir meme dans la carte unreal c'est encore mieux » ; « dans le sens ou au moins si on veut reuse cette carte dans un autre jeu on a tout les mdoel » ; « Pense bien à intégrer tout ce qui va être barrière, etc., des troncs, aussi sur la route, des fois il y a des traces de pneus, etc., tout ça, il faut l'intégrer, parce que ça montre, c'est aussi ça l'essence de cette route » ; « Tous les panneaux et tout, il faut bien tout le temps penser à tout. C'est pour ça que la script OpenStreetMap est très important. » **Traités le 18/11/2026** (deuxième passe ci-dessus) ; restent : troncs couchés et souches (aucun vu, rien posé), panneaux sans maillage du jeu, modèles de panneaux de l'export neutre, couche de décalques neutre.
- 18/11/2026, complément transmis (résumé d'un autre assistant, à vérifier) : sources du tracé à lire, ambiance du jour de course. Lu : rien ne change la longueur (3,0 km) ni les lignes ; déclaration de manifestation inaccessible (503) ; ambiance : décision 9.
