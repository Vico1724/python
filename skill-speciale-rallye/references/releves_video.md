# Relevés vidéo et Street View : consignes pour les agents

Les relevés d'images sont confiés à des agents sur un modèle moins coûteux (règle adoptée le 14/11/2026). Le modèle principal leur donne ces consignes, les planches et le fichier cible ; il ne lit que le JSON rendu. Les schémas sont ceux des fichiers du Grand Caunet, que les scripts savent lire : un exemple de chaque fichier est à joindre à la consigne.

## 1. Règles de lecture (à recopier dans chaque consigne)

1. **Un objet est au PK de l'image où il sort du champ par le côté**, pas de celle où on l'aperçoit au loin (écart de 20 à 60 m constaté au Grand Caunet).
2. **Permanent → vidéo de reconnaissance** (plus lisible, sans public) ; **posé pour le rallye → vidéo de course** (rubalises, panneaux de spéciale, horloge, cônes) ; **différent entre les deux → la course**.
3. **Le relevé laser l'emporte** pour les ponts, ponceaux et talus : une lecture vidéo n'est précise qu'à 5 m au mieux.
4. Chaque entrée porte `source` (vidéo, temps, planche), `confiance` (élevée / moyenne / faible) et, si elle corrige une valeur, l'ancienne valeur gardée à côté.
5. Côté : `gauche` / `droite` dans le sens de la course. Décalage : mètres depuis le **bord de chaussée** (positif vers l'extérieur), pas depuis l'axe.
6. Ne rien inventer : ce qui n'est pas lisible va dans `non_poses` ou `a_verifier`, avec la raison.
7. Un mur haut de pierre sèche ou un talus rocheux taillé est une **paroi rocheuse**, pas un parapet ; un parapet borde un pont, un ponceau ou un ravin.

## 2. Calage des vidéos

| Vidéo | Outil | Contrôle |
|---|---|---|
| Reconnaissance | `python -P scripts/19_calage_video.py <vidéo> --nom reco` depuis un dossier neutre (la vidéo est un fichier téléchargé) | tous les changements de direction retrouvés ; écart d'angle médian < 8° ; corriger le biais sur repères (`calage_reco_reperes.json` : ponts LiDAR, débouchés IGN) |
| Course | `19_calage_video.py` échoue souvent (allure, coupures) : recaler chaque objet sur un repère fixe connu par la reconnaissance | écart au repère consigné |
| Essai en jeu | `19b_calage_barre.py` : remplissage de la barre de progression (une colonne par 9,6 m en 1080p), étalonné sur deux instants sûrs | 7 m près ; mesure aussi les secousses de la caméra tous les 10 m |

Planches : `24_planches_parois.py` (une image tous les 6 m sur un intervalle de PK) ; paires jeu / reconnaissance : `20_planches_comparees.py` (tous les 40 m, 167 paires pour 6,7 km).

## 3. Relevés à faire, et fichier cible

| Relevé | Vidéo | Fichier | Champs essentiels |
|---|---|---|---|
| Ouvrages et parapets | reconnaissance + LiDAR | `ouvrages_parapets.json` (`ouvrages`, `parapets_hors_tablier`) | `pk_debut_m`, `pk_fin_m`, par côté `type` (aucun, pierre, pierre_des_blancs, beton…), `hauteur_m`, `decalage_m` |
| Glissières | reconnaissance | `glissieres.json` (`troncons`) | bornes, côté, `confiance_bornes` |
| Parois rocheuses | reconnaissance, planche tous les 6 m | `parois_rocheuses.json` (`parois`) | bornes au PK où la roche arrive à hauteur de la voiture, côté, `decalage_m`, `hauteur_m` [min, max], `genre` (lite, blocs, eboulis), `raide`, `couleur` |
| Poteaux et lignes | reconnaissance | `mobilier_bord_de_route.json` (`lignes_electriques`) | chaque poteau vu : `pk_m`, `decalage_m`, `type` (béton, bois) |
| Arbres isolés, rochers, lisses, barrières, bornes | reconnaissance | `mobilier_bord_de_route.json` (`objets`, `rochers`, `lisses`) | type, PK, côté, décalage, hauteur |
| Aires et débouchés de pistes | reconnaissance + ortho | `aires_et_pistes.json` (`emprises`) | bornes, côté, profondeur, `matiere` (pierre, terre, gravier), `genre` |
| Bords de végétation | reconnaissance | `bords_vegetation.json` (`zones`) | `pk` [début, fin], côté, `genre` (`haie_au_ras`, `ouvert`) |
| Marquage | reconnaissance | `marquage_route.json` (`troncons`, `zones_hachurees`) | ligne (axiale, rives), type (T1, T3, continue), bornes |
| Objets du rallye | course | `mobilier_bord_de_route.json` (`objets` de type panneau_radio, panneau_radio_annonce, public_interdit, horloge, cone… ; `rubalises`) | PK recalé sur un repère, côté, décalage, `lacet_en_plus_deg` (180 si vu de dos), appui des rubalises |
| Lignes de départ et d'arrivée | course | `lignes_es.json` | PK de sortie du champ du panneau |
| Notes du copilote | course (audio si présent) | `notes_copilote_retouches.json` | PK, note entendue, correction |

## 4. Street View

- Navigateur intégré, Google Maps en Street View aux coordonnées tirées du tracé ; noter pour chaque capture le PK, la direction du regard et la date de prise de vue affichée.
- À prendre : 200 m avant le départ et le départ lui-même (bâtiments, murs, parkings, barrières, panneaux), 100 m autour de l'arrivée et du point stop, chaque carrefour de la spéciale ; ailleurs seulement pour lever un doute de relevé vidéo.
- Fichier cible : `zone_depart.json` (`captures` avec `position_pk_m`, `regard`, `montre` ; `objets` ; `sol` ; `constructions` avec `polygone_l93` lu sur l'ortho, hauteurs, toitures, enduits ; `a_verifier`).
- **Teintes** : mesurer la couleur moyenne d'un enduit ou d'un mur au soleil et à l'ombre sur la capture (valeurs RVB consignées), pour régler les matériaux `MI_<court>_Enduit_*`.
- Les captures restent hors du dépôt et ne vont jamais dans le mod.

## 5. Relevé d'un essai en jeu (après l'essai)

Consigne : lire chaque paire jeu / reconnaissance, noter chaque écart avec PK, côté, catégorie (relief lointain, roche, sol, végétation, ouvrage, objet, chaussée, personnages), gravité 1 à 3 et cause probable. Sortie : `data/reference/releve_essai_<date>_v<n>/constats.json`. Le modèle principal regroupe ensuite par cause, pas par constat.
