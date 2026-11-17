# Photos de référence au sol et banques d'assets

État vérifié le 17 novembre 2026. Les mentions `[testé]` = requête réellement exécutée depuis l'environnement ; `[doc]` = lu sur la page officielle ; `[non vérifié]` = à confirmer avant usage. Les licences changent : relire l'URL officielle citée avant toute redistribution.

## Table des matières
1. Imagerie de rue ouverte (Panoramax, Mapillary, KartaView, Commons, Flickr, Geograph, flore)
2. Google Street View / Earth et vidéos embarquées
3. De la photo à la carte (fidélité, triangulation, tableau structuré)
4. Photogrammétrie et reconstruction (COLMAP, RealityScan, splatting)
5. Banques d'assets (tableau, signalisation française, végétation)
6. Assets du jeu cible
7. Gabarit CREDITS

---
## 1. Imagerie de rue ouverte

Ordre de préférence : Panoramax (sans clé, licence claire) > Mapillary (clé, mais détections d'objets) > Commons/Flickr/Geograph (photos isolées).

### 1.1 Panoramax
Géocommun (IGN + OpenStreetMap France + communauté), fédération d'instances, standard STAC. Pas de clé pour la lecture.

| Instance | Rôle |
|---|---|
| `https://api.panoramax.xyz/api` | méta-catalogue : agrège les instances, **à utiliser par défaut** [testé] |
| `https://panoramax.ign.fr/api` | instance IGN [testé : HTTP 200] |
| `https://panoramax.openstreetmap.fr/api` | instance OSM-FR [testé : HTTP 200] |
| `https://panoramax.xyz` | visionneuse web (inspection visuelle humaine) |

Licences : indiquées **par image** (`properties.license` + lien `rel=license`). Vues : `etalab-2.0` (Licence Ouverte, https://alliance.numerique.gouv.fr/licence-ouverte-open-licence/) et `CC-BY-SA-4.0` (https://creativecommons.org/licenses/by-sa/4.0/). Attribution = `geovisio:producer` (pseudo du contributeur) + Panoramax. Lire la licence de chaque image retenue, ne pas la supposer. Doc : https://docs.panoramax.fr/

Requêtes vérifiées (autour de lon 5.60, lat 43.19, Cassis/La Ciotat) :
```bash
# Recherche par bbox (minLon,minLat,maxLon,maxLat) [testé, 200, features GeoJSON]
curl -s "https://api.panoramax.xyz/api/search?bbox=5.59,43.18,5.61,43.20&limit=20"

# Proximité : place_position=lon,lat & place_distance=min-max en mètres [testé]
# NB : renvoie features:[] s'il n'y a rien dans le rayon (5.60,43.19 à 100 m = vide ; 5.6017,43.1888 = 2 résultats)
curl -s "https://api.panoramax.xyz/api/search?place_position=5.6017,43.1888&place_distance=0-100&limit=5"

# Filtre date (RFC3339, intervalle ouvert avec ..) [testé]
curl -s "https://api.panoramax.xyz/api/search?bbox=5.59,43.18,5.61,43.20&datetime=2022-01-01T00:00:00Z/..&limit=5"

# Tuiles vectorielles de couverture z/x/y [testé : 200, 2427 octets, application/vnd.mapbox-vector-tile]
# (tuile z14 contenant lon 5.60, lat 43.19 ; 204 = tuile sans donnée)
curl -s -o t.mvt "https://api.panoramax.xyz/api/map/14/8446/6008.mvt"
```
Note : `datetime=2022-01-01/..` (date seule) a été **refusé** (pas de `features`) ; utiliser `T00:00:00Z`.

Structure d'un item (vérifiée) :
- `geometry.coordinates` = [lon, lat] de la prise de vue ; `properties.view:azimuth` = cap en degrés (0 = nord, sens horaire) ; `properties.datetime` ; `properties.quality:horizontal_accuracy` (m) ; `properties.exif` (GPSImgDirection, GPSAltitude, modèle d'appareil) ; `properties.pers:interior_orientation` (capteur) ; `properties.geovisio:producer`.
- `assets.hd.href` (pleine résolution), `assets.sd.href` (2048 px de large, **suffisant pour la vision par modèle**), `assets.thumb.href` (500 px). Les URL pointent vers l'instance d'origine (`rel=via`). HEAD sur un `sd.jpg` [testé : 200].
- Séquences : `rel=prev/next` dans les liens d'un item ; `/api/collections/{id}/items` pour parcourir une séquence (la route roule : bon pour un tracé de rallye).
- Extraction minimale :
```bash
curl -s "https://api.panoramax.xyz/api/search?bbox=5.59,43.18,5.61,43.20&limit=20" | python3 -c "
import sys,json
for f in json.load(sys.stdin)['features']:
    p=f['properties']; print(f['geometry']['coordinates'], p.get('view:azimuth'), p['datetime'][:10], p['license'], f['assets']['sd']['href'])"
```
Couverture inégale : très bonne en France urbaine/routes départementales, nulle ailleurs parfois. Si vide, élargir la bbox puis passer à Mapillary.

### 1.2 Mapillary
Doc : https://www.mapillary.com/developer/api-documentation [doc]. Jeton **obligatoire** (sans jeton : erreur 190 `Invalid OAuth 2.0 Access Token` [testé]). Créer une app sur https://www.mapillary.com/dashboard/developers puis utiliser le *client token*.
- Base : `https://graph.mapillary.com` (métadonnées), `https://tiles.mapillary.com` (tuiles).
- Auth : `?access_token=MLY|...` ou en-tête `Authorization: OAuth MLY|...`.
- **Limite bbox : < 0,01° de côté** sur `/images`, `/map_features`, détections. Quadriller la zone.
- Recherche radiale d'images (depuis avril 2026) : `lat`, `lng`, `radius` (max 50 m), `limit` (max 100).
- Limites : 60 000 req/min (entités), 10 000/min (recherche), 50 000 tuiles/jour.
- Tuiles : `/maps/vtp/mly1_public/2/{z}/{x}/{y}` (couverture), `mly_map_feature_point` et `mly_map_feature_traffic_sign` (z14, **mobilier et panneaux détectés, positionnés**).
```bash
# [non vérifié : jeton absent] images dans une bbox
curl -s -H "Authorization: OAuth $MLY_TOKEN" "https://graph.mapillary.com/images?bbox=5.600,43.190,5.605,43.195&fields=id,computed_geometry,compass_angle,captured_at,thumb_2048_url,thumb_original_url&limit=50"
# panneaux/objets détectés (valeur `object_value` du type "regulatory--maximum-speed-40--g1")
curl -s -H "Authorization: OAuth $MLY_TOKEN" "https://graph.mapillary.com/map_features?bbox=5.600,43.190,5.605,43.195&fields=id,object_value,geometry,first_seen_at&limit=200"
```
Valeur forte pour le jeu : `map_features` donne directement une liste (type, lon/lat) de panneaux, poteaux, bornes, glissières, lampadaires : tableau de placement quasi prêt. Licence des images : CC BY-SA 4.0 (attribution « Mapillary » + auteur) [non vérifié : page de licence inaccessible, 403 ; la page API ne la mentionne pas] → https://help.mapillary.com/hc/en-us/articles/115001770409-Licensing . Les images sont de la **référence** ; ne pas redistribuer les photos dans le mod.

### 1.3 Autres sources photo
| Source | Accès | Notes |
|---|---|---|
| KartaView (ex-OpenStreetCam) | https://kartaview.org [testé : 200] ; API `https://api.openstreetcam.org/2.0/` **[testé : injoignable (000) depuis ici]** | CC BY-SA ; couverture faible, souvent complémentaire |
| Wikimedia Commons | API `geosearch` [testé] | licences par fichier, métadonnées dans `extmetadata` ; **limiter le débit** (HTTP 429 rapidement ; envoyer un `User-Agent` explicite, `sleep 1` entre appels) |
| Flickr | `flickr.photos.search` avec `lat,lon,radius,license=` ; clé API gratuite requise [testé : sans clé → erreur 100] | licences utiles : 4 (CC-BY), 5 (CC-BY-SA), 9 (CC0), 10 (PDM). Éviter les NC/ND. Doc : https://www.flickr.com/services/api/ |
| Geograph | https://www.geograph.org.uk [testé : 200] | Royaume-Uni/Irlande, CC BY-SA 2.0, photos géoréférencées ; API `https://www.geograph.org.uk/help/api` [non vérifié] |
| iNaturalist | `https://api.inaturalist.org/v1/observations` sans clé [testé] | identification d'essences ; filtrer `license=cc-by,cc-by-sa,cc0` |
| Pl@ntNet | https://my.plantnet.org [testé : 200] ; API sur clé | identifier une essence depuis une photo de feuille/écorce |

```bash
# Commons : photos dans 300 m (namespace 6 = fichiers) avec licence et URL [testé]
curl -s -A "carte-reelle/1.0 (contact-local)" "https://commons.wikimedia.org/w/api.php?action=query&generator=geosearch&ggscoord=48.8584|2.2945&ggsradius=300&ggslimit=10&ggsnamespace=6&prop=imageinfo&iiprop=url|extmetadata&iiextmetadatafilter=LicenseShortName|Artist&format=json"
# Piège : sans résultat, `list=geosearch` renvoie {"geosearch":[]} (rayon trop petit : 1000 m autour de 43.19,5.60 = vide)

# iNaturalist : arbres (Plantae = taxon 47126) recherche 2 km, observations de qualité "research" [testé]
curl -s "https://api.inaturalist.org/v1/observations?lat=43.19&lng=5.60&radius=2&taxon_id=47126&quality_grade=research&license=cc-by,cc-by-sa,cc0&per_page=30"
```
Pour la flore : agréger `taxon.name` des observations (top 10) = palette d'essences à utiliser (pins d'Alep, chênes verts, etc.). Complément : OSM `natural=tree` + tag `species`/`leaf_type`.

---
## 2. Google Street View, Google Earth et vidéos

**Autorisé** : consulter visuellement (navigateur, application) pour comprendre un lieu, comme un humain regarde une photo de référence ; en tirer des observations rédigées soi-même (« mur de pierre sèche, 1,2 m, côté droit »).

**Interdit** (Geo Guidelines [doc] https://about.google/brand-resource-center/products-and-services/geo-guidelines/ ; Conditions Maps Platform https://cloud.google.com/maps-platform/terms ; Service Specific Terms https://cloud.google.com/maps-platform/terms/maps-service-terms) :
- numériser ou **tracer** des informations depuis Street View (« digitizing or tracing ») ;
- utiliser la sortie Google Earth pour **reconstruire des modèles 3D** ou créer un contenu similaire ;
- extraire/aspirer en masse (scraping, API pour stocker les images), enregistrer ou rediffuser du contenu ;
- utiliser des captures comme textures ou matière première d'assets, ou dans un mod redistribué.
Les termes exacts changent : relire les liens avant de s'appuyer dessus.

**Règle opérationnelle pour l'agent** : Google = *référence humaine uniquement*, jamais dans un pipeline automatisé ; aucune capture enregistrée dans le dépôt ; aucun script appelant Street View/Static API ; toute donnée de carte vient de OSM, IGN, Panoramax, Mapillary. Si une vérification visuelle Google est utile, la demander à l'utilisateur, qui regarde et décrit en mots.

**Vidéos embarquées (YouTube, caméra de rallye)** : droits d'auteur du vidéaste ; non redistribuable, non extractible en textures. Usage de calage uniquement, vu par l'utilisateur ou en images fixes **non conservées** : repérer le **sens de parcours**, la vitesse de la zone, la **succession de virages** (rayon, sens, visibilité), les **points de repère** (panneau, pont, mur) et leur ordre, les **zones à pente/dévers**. Recoller sur le tracé : le temps vidéo → distance via la vitesse, vérifier la longueur totale du tracé du jeu, puis ajuster les rayons de courbes. Aucune image n'entre dans le mod.

---
## 3. De la photo à la carte

**Quoi repérer** (par prise de vue) : revêtement (enrobé, béton, gravillons, pavés, terre), état/couleur ; bords (bordure, caniveau, accotement, fossé) ; murs et clôtures (matériau, hauteur) ; glissières (béton, métal, bois) ; panneaux (type, sens) ; poteaux, bornes, lampadaires ; façades (nb d'étages, couleur, toit) ; végétation (essence, densité, hauteur) ; ciel/lumière ; pente et dévers.

**Géolocaliser un objet à partir de deux vues** (triangulation 2D) :
1. Pour chaque vue : position caméra (lon,lat → mètres locaux x,y) et cap `view:azimuth` (Panoramax) / `compass_angle` (Mapillary).
2. Dans l'image, mesurer l'angle horizontal de l'objet par rapport au centre : `θ = cap + (x_px − W/2)/W × FOV_h` (FOV_h : ~90° smartphone ; panoramique 360° : `θ = (x_px/W)×360 − 180 + cap_zero`, selon `pers:` / `projection` de l'item).
3. Rayon i : `P = C_i + t·(sin θ_i, cos θ_i)`. Intersection des deux rayons (angle entre rayons > 15° sinon instable) ; ignorer si t < 0.
4. Reprojeter en coordonnées du jeu (même projection que la carte), contrôler avec Mapillary `map_features` s'il existe, mettre confiance = haute si 3 vues concordent à < 3 m.
Précision GPS smartphone 3 à 10 m : toujours recaler sur la **géométrie OSM** (côté de la route, distance au bord) plutôt que sur le GPS brut.

**Description par modèle de vision à bas coût** : envoyer les images `sd` (2048 px) ou réduites à ~1024 px ; demander **uniquement du JSON** et ne conserver que le tableau (jeter images et texte libre, pour la licence et le poids) :
```json
[{"type":"panneau|mur|glissiere|arbre|poteau|facade|revetement|borne",
  "sous_type":"B14-50|pierre_seche|beton|pin_alep|...",
  "cote":"gauche|droite|axe",
  "distance_bord_m":2.0,
  "hauteur_m":1.2,
  "confiance":0.0,
  "source_id":"uuid_panoramax",
  "lon":5.6017,"lat":43.1888}]
```
Consigne type : « Décris uniquement les objets visibles au bord de la route ; ne devine pas ce qui est hors cadre ; confiance < 0,5 si flou/loin. » Dédoublonner les objets vus sur plusieurs images (même type, < 4 m). Compter ensuite par type pour choisir les assets à référencer (section 6).

---
## 4. Photogrammétrie et reconstruction

| Outil | Licence / conditions | URL |
|---|---|---|
| COLMAP | BSD (nouvelle), usage libre, scriptable CLI/Python | https://github.com/colmap/colmap |
| Meshroom / AliceVision | MPL-2.0, gratuit, GPU NVIDIA (CUDA) pour la densification | https://github.com/alicevision/Meshroom |
| RealityScan (ex RealityCapture) | gratuit pour étudiants, enseignants, entités < 1 M$ de revenu annuel brut ; payant au-delà [doc]. Depuis le 27 mai 2026, les abonnements Unreal n'incluent plus RealityScan. Serveur de licence hérité fermé le 3 août 2026 (version ≥ 1.4 requise) | https://www.realityscan.com/license |
| Metashape (Agisoft) | commercial ; démo/essai sans export complet, licence éducation séparée [non vérifié 2026] | https://www.agisoft.com/buy/licensing-options/ |
| OpenDroneMap | AGPL-3.0, traitement de photos de drone → orthophoto, MNT, maillage ; WebODM | https://github.com/OpenDroneMap/ODM |

**Droits sur les photos sources** : photogrammétrer des photos CC-BY-SA donne une œuvre dérivée soumise à l'attribution et au partage à l'identique ; Street View/Google Earth interdit (§2). Sources acceptables : photos de l'utilisateur, ou photos CC0/CC-BY avec crédit. Panoramax/Mapillary : fond de rue à faible recouvrement, **résultats médiocres** (peu de vues par objet) ; la photogrammétrie réclame 60 à 80 % de recouvrement, d'où surtout des photos prises par l'utilisateur.

**Gaussian splatting** : très beau en rendu, mais **pas de collision** ni de maillage propre. État 2026 des plugins Unreal [doc] :
- NanoGS : rendu « style Nanite » (LOD/clustering), UE 5.6/5.7, gratuit ; https://radiancefields.com/nanogs-brings-nanite-style-gaussian-splatting-to-unreal-engine-5
- Volinga (Windows, NVIDIA, UE 5.3+, 4DGS depuis août 2026 ; relight dans la version Pro payante) ; Luma (plugin gratuit, ancien, UE 5.3) ; XScene (Apache-2.0, https://github.com/xverse-engine/XScene-UEPlugin) ; StarLightGS (open source, UE 5.7+) ; WallGS (bêta, génère de la collision depuis les splats [non vérifié]).
- Limites jeu : pas de collision native, éclairage/ombres limités, pas de moteur physique, poids énorme, plugins tiers non portés sur toutes les versions ni compatibles avec un mod distribué dans un jeu tiers. **Dans un mod d'un jeu existant, ne pas compter dessus.**

**Quand ça vaut le coup** : un objet singulier, visible de près, impossible à trouver en banque : falaise/paroi caractéristique, façade monumentale, rocher repère, pont, chapelle. Quand **non** : tout élément générique (murs, arbres, panneaux, bâtiments ordinaires), routes (utiliser le terrain/spline + matériaux), sujets vus de loin (un matériau suffit).

**Chaîne type** : photos (≥ 60, EXIF conservé, lumière couvert) → COLMAP/RealityScan (alignement, nuage dense, maillage) → nettoyage (couper le sol, remplir les trous, orientation) → décimation (cible 20 à 100 k triangles pour un élément visible, 5 à 20 k pour un secondaire ; Blender *Decimate* ou RealityScan *Simplify*) → UV + bake du détail (normal map + albédo 2K/4K ; dé-éclairer l'albédo si possible) → LOD → export FBX/glTF → import Unreal avec **Nanite activé** si l'actif est dense et statique (le maillage haute densité peut alors être gardé), collision simple (convex/boîtes) et non le maillage complet. Vérifier l'échelle (unités Unreal = cm) et que le jeu cible accepte un contenu importé.

---
## 5. Banques d'assets

Définition « mod redistribué » : l'actif brut ou cuit est livré dans le paquet du mod. CC0 et licences Fab Standard (si l'actif est incorporé dans le jeu et non revendu seul) sont les plus sûrs ; Fab **interdit de revendre ou donner l'actif seul** [doc https://www.fab.com/eula], ce qui rend le cas « mod public » ambigu (page muette sur les mods) → ne pas l'embarquer sans confirmation.

| Nom | URL | Contenu | Licence | API / téléchargement | Mod redistribué |
|---|---|---|---|---|---|
| Poly Haven | https://polyhaven.com | HDRI, textures PBR, modèles | CC0 (https://polyhaven.com/license) ; l'usage de l'API demande un `User-Agent` unique et une mention « Powered by Poly Haven » si API exposée à des utilisateurs (https://polyhaven.com/our-api) | API publique sans clé [testé] | Oui |
| ambientCG | https://ambientcg.com | textures PBR, HDRI, modèles | CC0 (https://docs.ambientcg.com/license/) [non revérifié] | API v2 JSON [testé] | Oui |
| Fab (marché Epic) | https://www.fab.com | modèles, matériaux, VFX, etc. | Standard License, Personnelle/Pro, parfois CC-BY (https://www.fab.com/eula) ; non limité à Unreal [doc] | pas d'API publique scriptable ; téléchargement via compte / lanceur Epic | Non (pas de redistribution seule) |
| Quixel Megascans | via Fab https://www.fab.com | scans (roche, sol, végétation, surfaces) | **Gratuit sur Fab depuis le 5 nov. 2026** (https://quixel.com/news/update-megascans-are-going-free-again) ; Fab Standard License, droits d'entraînement IA ajoutés ; actifs « legacy » pris via Bridge/quixel.com sous l'ancienne Epic Content License (Unreal seulement) | compte Epic requis, pas d'API | Non en l'état (redistribution seule interdite) ; OK pour ce que le **joueur télécharge lui-même** |
| Sketchfab | https://sketchfab.com | modèles utilisateurs | CC par modèle (CC0, CC-BY, CC-BY-SA, NC…), https://help.sketchfab.com/hc/en-us/articles/360046421631-Licenses | API v3 recherche sans clé [testé : `type=models&downloadable=true&license=by`], téléchargement par jeton API/OAuth | selon licence : CC0/CC-BY oui avec crédit ; NC/ND non |
| Kenney | https://kenney.nl/assets | modèles low-poly, UI, icônes | CC0 (https://kenney.nl/support) [doc] | ZIP | Oui (style cartoon : rarement fidèle) |
| OpenGameArt | https://opengameart.org | 2D/3D/audio hétérogène | CC0, CC-BY, CC-BY-SA, GPL, OGA-BY : **par fichier** | pas d'API officielle ; téléchargement manuel | selon fichier |
| BlenderKit | https://www.blenderkit.com | modèles, matériaux, HDRI | Royalty Free ou CC0 par actif (https://www.blenderkit.com/docs/licenses/licensing-faq/) | dans Blender (add-on), API partielle | CC0 oui ; RF : seulement si non « extractible » [doc] → éviter |
| Textures.com / Poliigon | https://www.textures.com, https://www.poliigon.com | photos, textures | Textures.com : redistribution brute interdite (https://www.textures.com/about/terms-of-use) ; Poliigon : free assets utilisables en commercial mais redistribution restreinte (https://help.poliigon.com/en/articles/8749749-asset-use-license) | compte, crédits | Non |
| CGTrader / TurboSquid (gratuits) | https://www.cgtrader.com/free-3d-models, https://www.turbosquid.com/Search/3D-Models/free | modèles | « Royalty-free » propriétaire, hétérogène, souvent sans droit de redistribution brute ; vérifier chaque fiche | manuel | Non par défaut |

**Poly Haven, requêtes testées** (toujours envoyer `-A "nom-appli/1.0"` ; omis dans les tests ci-dessous) :
```bash
curl -s "https://api.polyhaven.com/assets?t=textures&c=road"          # liste (asphalt_01…) [testé]
curl -s "https://api.polyhaven.com/categories/textures"                # catégories + comptes [testé]
curl -s "https://api.polyhaven.com/info/asphalt_01"                    # auteurs, tags, résolution max [testé]
curl -s "https://api.polyhaven.com/files/rock_boulder_cracked"         # diff/nor_gl/rough/arm/disp/gltf aux URL dl.polyhaven.org [testé]
curl -s "https://api.polyhaven.com/files/Camera_01"                    # modèle : gltf, fbx, usd, blend [testé]
curl -s "https://api.polyhaven.com/assets?t=models&c=props"            # modèles par catégorie [testé]
```
Types : `t=hdris|textures|models`. Utiliser les cartes `nor_gl` (OpenGL, Unreal attend DirectX → inverser le canal vert ou prendre `nor_dx`) et `arm` (AO/Rough/Metal packé, compatible ORM Unreal).

**ambientCG, requête testée** :
```bash
curl -s "https://ambientcg.com/api/v2/full_json?q=asphalt&type=Material&limit=5&include=downloadData"
# téléchargement : https://ambientcg.com/get?file=Concrete049_2K-JPG.zip  (champ downloadFolders.default.downloadFiletypeCategories.zip.downloads[].fullDownloadPath)
```
Catégories utiles : Asphalt, Road, Gravel, Ground, Rock, Concrete, Bricks, PavingStones, Moss, Grass.

**Végétation** : Megascans/Megaplants et arbres (via Fab, voir ligne ci-dessus) ; SpeedTree (licence commerciale, https://store.speedtree.com/ ; les modèles Unreal intégrés au jeu cible sont préférables) ; PCG / Foliage d'Unreal pour la dispersion (règles par densité et pente, pas d'actifs externes) ; Poly Haven (arbres limités, quelques modèles `t=models&c=nature` [non vérifié]) ; Sketchfab CC0/CC-BY pour essences spécifiques (pin d'Alep, olivier, cyprès).

**Panneaux de signalisation français** : sources libres.
- Commons, catégorie principale : https://commons.wikimedia.org/wiki/Category:Road_signs_of_France (la page directe via WebFetch a répondu 404 ; passer par https://commons.wikimedia.org/wiki/Category:Road_signs_of_France_by_number [non vérifié : existence confirmée par un miroir]). Fichiers nommés `France road sign B14.svg`, `A3.svg`, `AB6.svg`, `B6d.svg`, `C111.svg`, `CE50.svg`, `G1.svg`, `ID15a.svg` (codes de l'arrêté du 24 novembre 1967 : A danger, AB priorité, B interdiction/obligation, C indication, CE, D direction, K panonceaux, M, EB…). Repères OSM : https://wiki.openstreetmap.org/wiki/Category:FR:Road_sign
- Les panneaux officiels sont du domaine public (œuvre de l'État) ou CC0/CC-BY-SA selon le fichier : **lire la licence de chaque fichier** (API `extmetadata`).
- Conversion en texture : rasteriser le SVG en 512×512 ou 1024 (`rsvg-convert -w 1024 -o B14_50.png France_road_sign_B14.svg` ; ou Inkscape CLI `--export-type=png --export-width=1024`) ; canal alpha pour la forme ; appliquer sur un disque/octogone + poteau fait maison (cylindre) ; rétroréflexion = roughness 0.3, metallic 0.
- Marquages au sol : motifs 100 % géométriques (largeur de ligne continue 0,12 m ; axe discontinu 3 m/10 m selon type de route ; vérifier la norme). Les générer par decal/spline, pas par photo. Textures de peinture usée : Poly Haven/ambientCG « road marking ».
- Mobilier urbain : mêmes sources (Sketchfab CC0, Poly Haven props, Fab payant) ; vérifier d'abord ce que le jeu fournit déjà.

---
## 6. Assets du jeu cible
Principe : **référencer par chemin les assets déjà présents dans le jeu** (ex. `/Game/.../SM_Wall_Stone_01`) plutôt que d'importer des fichiers externes. Ces actifs ne sont pas redistribuables, mais le joueur les possède. Avantages : cohérence visuelle (même éclairage/matériaux), poids du mod minimal (JSON/niveau + éventuels matériaux), performances (instanciation, Nanite/LOD déjà réglés), aucun problème de licence tierce. Étapes : inventorier les assets du jeu (murs, arbres, glissières, panneaux), mapper « type d'objet détecté (§3) → chemin d'asset », importer en externe **uniquement** ce qui manque (panneau français précis, rocher repère). Garder le mapping dans un fichier de données séparé.

---
## 7. Gabarit CREDITS
À créer **dès le premier téléchargement** (`CREDITS.md` dans le dossier du mod) ; une ligne par actif ou photo.

```markdown
# CREDITS
| Élément | Auteur | Source (URL exacte) | Licence (+ URL) | Modifications | Date d'accès | Redistribué dans le mod ? |
|---|---|---|---|---|---|---|
| Texture asphalt_01 | Dario Barresi, Charlotte Baglioni | https://polyhaven.com/a/asphalt_01 | CC0 https://creativecommons.org/publicdomain/zero/1.0/ | recadrée 2K | 2026-11-17 | oui |
| Photo de référence | bernardvoyageur | https://panoramax.openstreetmap.fr/images/… | CC-BY-SA-4.0 https://creativecommons.org/licenses/by-sa/4.0/ | aucune | 2026-11-17 | non (référence seule) |
| Panneau B14 (SVG→PNG) | Gouvernement français / contributeurs Commons | https://commons.wikimedia.org/wiki/File:France_road_sign_B14.svg | à relever sur la page | rastérisé 1024 | 2026-11-17 | oui |
| Données de carte | contributeurs OpenStreetMap | https://www.openstreetmap.org/copyright | ODbL | extraction bbox | 2026-11-17 | dérivé |

Mentions obligatoires : « © contributeurs OpenStreetMap (ODbL) », « Images : Panoramax (CC-BY-SA / Licence Ouverte 2.0), contributeurs nommés ci-dessus », « Powered by Poly Haven » si API exposée.
```
Règles : ne jamais embarquer un actif dont la licence n'est pas lisible ; ne pas mélanger NC/ND ; noter les photos « référence seule » (non redistribuées) pour la traçabilité ; relire les conditions avant publication du mod.
