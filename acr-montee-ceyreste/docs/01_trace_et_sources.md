# 01 - Tracé retenu et sources

*Recherche du 17/11/2026. « Certain » = écrit par une source citée ; « estimé » = déduit par nous.*

## Résultat

| Élément | Valeur retenue | Statut |
|---|---|---|
| Manifestation | Montée historique de Ceyreste : démonstration sur route fermée, **sans chronométrage ni classement**, voitures historiques (jusqu'au 31/12/1990), 4 montées dans la journée, environ 90 voitures | certain |
| Organisateur | Phocéa Productions, avec l'Écurie Soleil Classic et la municipalité de Ceyreste | certain |
| Éditions | 2e le 22/05/2016 ; 3e le 09/04/2017 ; 08/04/2018 ; 5e le 07/04/2019 ; 6e le 03/04/2022 ; 7e le 02/04/2023 ; 10e le 12/04/2026 ; 11e annoncée le 11/04/2027 | certain (dates d'articles et d'agenda) |
| Origine | Reprend le tracé de l'ancienne course de côte de Ceyreste (créée en 1913 selon un article, 1902 selon un autre), longtemps comptée au Championnat de France de la Montagne ; tracé « légèrement raccourci pour cause d'urbanisation » | certain (articles), années contradictoires |
| Route | **D3**, « route du Grand Caunet » (BD TOPO : RTE DU GRAND CAUNET, largeur IGN 7 m), revêtement en bon état | certain (route) |
| Sens | Montant : Plan de Masse → Grand Caunet (« à l'assaut du Grand Caunet ») | certain |
| Départ | Au **Plan de Masse** ; ligne placée au carrefour D3 / Voie Romaine / route du Caunet, au droit de l'arrêt de bus « Plan-de-Masse » (43,22313 N ; 5,64904 E ; 214 m) | lieu certain ; ligne **estimée** (±50 m) |
| Longueur | Annoncée 3,1 km (2017), 3,5 km (2018, 2023), **3 km** (2022 et fiche d'agenda 2026-2027 reprenant l'organisateur). Retenu : **3,0 km** | **estimé** |
| Arrivée | PK 3000 sur la D3 (43,23343 N ; 5,66295 E ; 366 m) | **estimée** (aucune source ne la situe) |
| Fin de route modélisée | Carrefour D3 / D3D au Grand Caunet, PK 3746 : couvre la variante 3,5 km et le raccord avec la carte du Grand Caunet | choix du projet |
| Profil (LiDAR HD) | 214 → 366 m, +155 m / −3 m, pente moyenne 5,1 %, maximum 11,8 % ; 450 premiers mètres presque plats | mesuré |
| Virages (axe BD TOPO, indicatif) | 31 virages dont 8 épingles ; le plus serré PK 893 à droite, rayon ≈ 9 m, 198° | mesuré, à affiner |
| Chicanes, ralentisseurs ajoutés | Aucun mentionné | inconnu |
| Parc / paddock | Vérifications administratives à la salle polyvalente, techniques et parc « derrière la mairie » / vers la salle polyvalente, dans le village : **hors du tracé, non modélisé** | certain (articles) |
| Sécurité | Route fermée par arrêté préfectoral, environ 25 commissaires, médecin | certain |

Figures : `figures/carte_generale.png`, `figures/profil_en_long.png`, `figures/zoom_depart.png`, `figures/zoom_arrivee.png`.

## Variantes

- **3,5 km** (2018, 2023) : l'arrivée serait vers le PK 3500, à 250 m du carrefour D3/D3D. La route est modélisée jusqu'au PK 3746 : passer à cette variante revient à changer `longueur_officielle_km` et la position d'`ARRIVEE` dans `data/reference/montee_ceyreste_officiel.json` et `lignes_es.json`, puis relancer la chaîne depuis l'étape 2.
- **Ancienne course de côte** : partait plus bas (avant l'urbanisation) ; tracé non documenté, non retenu.

## Recouvrement avec « Le Grand Caunet »

Aucune portion de route commune. L'ES du Grand Caunet emprunte la D3D puis la D1 ; la montée emprunte la D3. Les deux se touchent en un point : le carrefour D3/D3D, PK 3746 de la montée = point d'approche PK −0,183 de l'ES du Grand Caunet, à côté du parking du Grand Caunet (aire d'accueil). Seuls ce parking et les relevés indépendants du lieu (valeurs lues dans le jeu, catalogue, marquage, textures) sont repris : voir `02_reutilisation.md`.

## Sources

- News Classic Racing, 6e édition (2022) : départ au Plan de Masse, 3 km, 4 montées, route fermée par arrêté — https://www.newsclassicracing.com/La-6e-montee-historique-de
- News Classic Racing, 5e édition (2019) : départ du Plan de Masse vers le Grand Caunet, course créée en 1913, tracé raccourci — https://www.newsclassicracing.com/La-5e-montee-historique-de,10339
- News Classic Racing, 7e édition (2023) : 3,5 km, 90 voitures, vérifications à la salle polyvalente — https://www.newsclassicracing.com/Belle-reussite-pour-la-7e-montee
- News Classic Racing, 3e édition (2017) : 3,1 km, 25 commissaires, paddock derrière la mairie — https://www.newsclassicracing.com/Montee-historique-de-Ceyreste-Et
- News Classic Racing, 2e édition (2016) : route fermée de 8 h à 18 h 30, parc vers la salle polyvalente — https://www.newsclassicracing.com/La-2e-montee-historique-de,7352
- Écurie Soleil Classic, édition 2018 : « les 3,5 kms de la D3 », entre le Plan de Masse et le Grand Caunet — http://ecuriesoleilclassic.fr/montee-historique-de-ceyreste-2/
- Agenda Auto Moto (fiche de l'organisateur, 10e le 12/04/2026 puis 11e le 11/04/2027) : D3 entre Ceyreste et le Grand Caunet, 3 km à parcourir 4 fois — https://www.agendaautomoto.fr/montee-historique-de-ceyreste/
- Site de l'organisateur (aucun plan publié) — https://www.phocea-productions.fr/mh-ceyreste/
- Arrêt « Plan-de-Masse » (OpenStreetMap, nœud 6431686998, via Nominatim) ; réseau de bus La Ciotat-Ceyreste — https://www.laciotat.rtm.fr/plan-de-reseau-la-ciotat-ceyreste_2026-nl_wb
- IGN Géoplateforme (BD TOPO, LiDAR HD, BD ORTHO, BD Forêt), Licence Ouverte Etalab 2.0 — https://data.geopf.fr

**Complément du 18/11/2026** (liens transmis par l'utilisateur, résumé d'un autre assistant) : la fiche Agenda Auto Moto redit 3 km de la D3 entre Ceyreste et le Grand Caunet, 4 montées ; la déclaration de manifestation (https://declaration-manifestations.gouv.fr/dossier/98930/) a répondu « 503 » et n'a pas pu être lue ; l'article de La Provence sur les 10 ans (https://www.laprovence.com/article/sortie-loisirs/6313474701556314/belles-mecaniques-et-pilotes-passionnes-pour-feter-les-10-ans-de-la-montee-historique-de-ceyreste) n'a pas pu être chargé ; Climbfinder (https://climbfinder.com/fr/montees/col-du-grand-caunet-la-ciotat) décrit une montée cycliste depuis La Ciotat (11,7 km, +423 m), sans rapport avec le départ du Plan de Masse. Aucun repère (PR, carrefour) de départ ou d'arrivée n'en ressort : **3,0 km et les lignes estimées sont gardés**. Repère trouvé sur le terrain (Panoramax, 08/09/2025) : borne « D3 PR 7 » au PK ≈ 2111 et plaquette probable du PR 8 au PK ≈ 3112, utiles si un arrêté cite des PR. Ancienne course de côte : aucun tracé documenté trouvé.

**Vidéos embarquées** : aucune trouvée par la recherche (un article espagnol, motorpasion.com, commente une vidéo de la montée sans lien exploitable). C'est la première chose à obtenir : elle fixerait les lignes, la longueur et le mobilier (`chaussee_corrections.json`, glissières, parapets).
