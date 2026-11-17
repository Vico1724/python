# L'essai unique en jeu : préparation, liste de contrôle, exploitation

## 1. Avant de proposer l'essai

Tous ces points sont verts, sinon on ne propose pas d'essai :

- [ ] `stage-verify` : aucune ligne `FAIL`.
- [ ] Table relue : surface Tarmac, pneus TarmacSnow, météo MonteCarlo, longueur au menu, autres lignes identiques au registre installé.
- [ ] Comparaison physique avec Munster ou Bollène (`acr-ref export`) : même matière, ligne idéale calculée (écart médian à l'axe ~0,4 m, SkidIntensity médiane ~0,2), humidité de base 0.
- [ ] `relire_decor.py` : RELECTURE CONFORME ; décalage route / décor 0,0 cm ; véhicules feux éteints ; variantes portant leurs réglages du jeu.
- [ ] Aperçus hors jeu aux PK de contrôle comparés à la reconnaissance (relief, falaises, parois, carrefours, départ, arrivée).
- [ ] Contrôles de placement à zéro : porte-à-faux de roche, arbres dans le bâti, houppiers sur la chaussée, objets perchés ou enterrés.
- [ ] Version précédente gardée (`choisir_decor.ps1`), jeu fermé, accord du directeur pour installer.

## 2. Ce que le directeur fait

Essais libres, voiture et réglages connus, Steam hors ligne. **Enregistrer une vidéo de tout le parcours**, départ arrêté compris. Puis, si possible, le même tronçon sur une spéciale goudronnée du jeu (Bollène ou Munster) pour comparer le ressenti.

## 3. Liste de contrôle à lui donner

| # | À regarder | Réponse attendue |
|---|---|---|
| 1 | Chargement, voiture posée dans le bon sens, nom au menu, longueur | oui / non |
| 2 | Pneus asphalte proposés, température et météo plausibles | oui / non |
| 3 | Zone rouge de départ, officiels animés au départ et à l'arrivée (si demandés) | oui / non |
| 4 | Chrono : départ, intermédiaires, arrivée, arrêt au point stop | oui / non |
| 5 | Notes du copilote au bon moment et dans le bon sens | PK des notes fausses |
| 6 | Adhérence et ressenti de la route (bosses irréelles, route trop lisse) comparés à Bollène ou Munster | appréciation |
| 7 | Murs invisibles, trous, sorties de route mal replacées | PK |
| 8 | Relief lointain, falaises, parois proches | appréciation + captures |
| 9 | Sol, herbe, débris et traces sur la chaussée | appréciation |
| 10 | Arbres ou objets sur la chaussée, objets flottants ou enterrés | PK + captures |
| 11 | Zone de départ et arrivée comparées à la réalité | captures |
| 12 | Fluidité | oui / non |

## 4. Après l'essai

1. Caler la vidéo (`19b_calage_barre.py`), paires tous les 40 m (`20_planches_comparees.py`), relevé par agents (`releves_video.md` § 5).
2. Regrouper les constats **par cause** ; chaque cause renvoie à une constante de `valeurs_calibrees.md` ou à un relevé.
3. Corriger dans les données et les constantes, refaire les contrôles hors jeu, **une** construction de retouche.
4. Consigner les valeurs nouvellement jugées bonnes dans `valeurs_calibrees.md`, avec la date et la spéciale : c'est ce qui rend la spéciale suivante moins chère.
