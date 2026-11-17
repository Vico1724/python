# Sources de géodonnées pour recréer une zone réelle

Testé le 2026-11-17 depuis l'environnement de l'agent (`curl` via proxy). Légende : **[V]** = requête exécutée avec succès ce jour ; **[NV]** = non vérifié (non testé, ou hôte injoignable ici). Zone de test : lon 5.60, lat 43.19 (Bouches-du-Rhône) = Lambert-93 X=911462, Y=6235790.

## Table des matières
1. France - IGN Géoplateforme (clés, altimétrie, imagerie, vecteur, plans, classes LiDAR)
2. Hors de France (tableau)
3. OpenStreetMap (Overpass, miroirs, Geofabrik, limites)
4. Projections et repères (L93, NGF/RAF20, repère local, Unreal)
5. Choisir la bonne source (arbre de décision, volumes)
6. Licences et crédits

---
## 1. France - IGN Géoplateforme

**Règles générales [V]**
- Aucun compte ni clé pour les services publics `https://data.geopf.fr/...` (anciens `wxs.ign.fr/{clé}` et `geoportail.gouv.fr` = obsolètes). `/private/...` répond 401.
- Catalogue et CGU : https://cartes.gouv.fr/ (CGU : https://cartes.gouv.fr/cgu). Les anciennes pages `geoservices.ign.fr/lidarhd`, `.../documentation/...` redirigent (301) vers cartes.gouv.fr.
- En-têtes de limite observés : WFS `ratelimit-limit: 30`, WMS-R `40`, téléchargement `10` (par seconde). Les rafales de requêtes `Range` sur les dalles COPC ont donné 403 : espacer d'environ 0,25 s.
- **WCS : n'existe pas** (`/wcs` = 404 [V]). Pour de l'altimétrie raster, utiliser WMS-R avec `FORMAT=image/geotiff` (float32, valeurs réelles en mètres).
- Capabilities (à relire en cas de doute, noms de couches mouvants ; ~1-5 Mo chacun) :
  - WMS-R `https://data.geopf.fr/wms-r/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities`
  - WMTS `https://data.geopf.fr/wmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetCapabilities`
  - WFS `https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities`
  - Téléchargement (Atom, 10 entrées/page, `?page=N`) `https://data.geopf.fr/telechargement/capabilities`
- Limite WMS-R : `MaxWidth/MaxHeight = 5010` px (5011 -> 400 [V]) ; 2 couches max par requête.
- WMS 1.3.0 + EPSG:4326 = ordre lat,lon. Préférer `CRS=EPSG:2154` (X,Y) : plus simple.

### 1.1 Altimétrie

| Produit | Usage carte de jeu | Résolution / précision | Accès |
|---|---|---|---|
| **LiDAR HD MNT** | heightmap du terrain (sol nu) | 50 cm ; altim. ~10 cm, planim. ~50 cm (annoncé par l'API alti [V]) | WMS-R / dalles |
| **LiDAR HD MNS** | surface (toits, canopée, ponts) | 50 cm | WMS-R / dalles |
| **LiDAR HD MNH** | = MNS - MNT, hauteur des arbres/bâtiments | 50 cm | WMS-R / dalles |
| **Nuage LiDAR HD classé** | arbres individuels, murs, glissières, câbles | >= 10 pts/m² (5 au-dessus de 3200 m) ; ~159 Mo la dalle de 1 km² [V] | COPC par dalle |
| **RGE ALTI 1 m** | repli si LiDAR HD absent | 1 m, Z en IGN69 | WMS-R, API alti, 7z par département |
| BD ALTI 25 m, SRTM3 | zone très vaste, relief lointain | 25 m / 90 m | WMS-R/WMTS |

Couverture LiDAR HD : programme visé France entière fin 2026, avancement : https://macarte.ign.fr/carte/mThSup/diffusionMNxLiDARHD. Zones ZICAD (interdites de captation aérienne) : MNx confidentialisés (« trous »), cf. fiche https://www.data.gouv.fr/datasets/mnt-lidar-hd/ . Toujours tester le nodata.

**MNT/MNS/MNH LiDAR HD par WMS-R [V]** (couches : `IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93`, `..._MNS_...LAMB93`, `..._MNH_...LAMB93`). Sortie GeoTIFF float32, nodata -9999, EPSG:2154. 2000x2000 px = 16 Mo non compressé pour 1 km² à 0,5 m.
```bash
# dalle LiDAR HD alignée sur la grille native (dalle NW = 911 km / 6236 km)
curl -o mnt.tif "https://data.geopf.fr/wms-r?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93&FORMAT=image/geotiff&STYLES=&CRS=EPSG:2154&BBOX=910999.75,6235000.25,911999.75,6236000.25&WIDTH=2000&HEIGHT=2000"
```
- Alignement : les nœuds sont aux coordonnées entières, donc la BBOX est décalée de 0,25 m (`X0-0.25 .. X0+999.75`, `Y0-999.75 .. Y0+0.25`). Pour une emprise quelconque : WIDTH = (xmax-xmin)/0.5 <= 5010, BBOX décalée pareil. Contrôle : valeur lue à (911462,6235790) = 40,51 m, identique à l'API alti.
- Style `hypso` = rendu coloré (PNG pour affichage) ; pour du Z utiliser le style par défaut + `image/geotiff`.
- Échelle min : la couche MNT n'est servie qu'en dessous d'un certain dénominateur d'échelle ; si l'image est vide, réduire l'emprise ou augmenter la taille.
- **Dalles natives** (livraison par dalles de 1 km, MNx GeoTIFF 0,5 m ~24 Mo pour le MNS ; nom `LHD_FXX_0911_6236_MNT_O_0M50_LAMB93_IGN69.tif`) : l'index est la couche WFS `IGNF_LIDAR-HD_METADONNEE:metadata`, qui fournit pour une emprise les URL exactes `url_mnt`, `url_mns`, `url_mnh` (requêtes WMS-R ci-dessus) et `url_npl` (nuage COPC), + `capteur`, `date_fin_acquisition`, `nombre_points`, `systeme_altimetrique` (IGN69), `procede_classement` [V] :
```bash
curl -s "https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&OUTPUTFORMAT=application/json&TYPENAMES=IGNF_LIDAR-HD_METADONNEE:metadata&BBOX=43.19,5.60,43.191,5.601,urn:ogc:def:crs:EPSG::4326" | jq '.features[].properties | {url_mnt,url_npl,date_fin_acquisition}'
```
  (BBOX 4326 en lat,lon avec le suffixe `urn:ogc:def:crs:EPSG::4326` ; en L93 : `BBOX=x1,y1,x2,y2,EPSG:2154`.) Les couches `IGNF_MNT-LIDAR-HD:dalle` etc. citées sur data.gouv ne répondent pas (« Unknown namespace ») : ne pas les utiliser.
- Autres jeux du service de téléchargement [V] : `LiDARHD-CARTES-CLASSES`, `LiDARHD-DENSITES`, `LiDARHD-NUALID`, `MNS-CORREL`. Documentation produit : https://geoservices.ign.fr/sites/default/files/2024-09/DC_LiDAR_HD_1-0.pdf [NV contenu].

**Nuage de points COPC [V]** : `url_npl` = `https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_PQ_2025-03-14/LHD_FXX_0911_6236_PTS_LAMB93_IGN69.copc.laz`. Format LAZ 1.4, point format 6, échelle 0,01, CRS L93 + Z IGN69, `Accept-Ranges: bytes` : lecture partielle possible (COPC). Exemple vérifié avec `laspy[lazrs]` (`laspy.CopcReader`, `query(bounds=..., resolution=...)`) en lisant par Range.
```python
# classes lues dans la dalle de test (résolution 8 m) : {1,2,3,4,5,6,64,66,67}
```
- Un fichier COPC = 1 km² complet (~159 Mo ici, jusqu'à ~1-2 Go en zone dense). Pour 200 m de côté, ne lire que les nœuds COPC concernés (Range), pas la dalle entière.

**Classes du nuage LiDAR HD** (11 classes ; 1,2,3,4,5,6 constatées [V] ; 64/66/67 constatées, libellés d'après présentation IGN ; 9 et 17 = ASPRS standard, [NV] sur cette dalle) :

| Code | Classe | Usage jeu |
|---|---|---|
| 1 | non classé | ignorer |
| 2 | sol | MNT, détection de talus |
| 3 / 4 / 5 | végétation basse (<0,5 m) / moyenne (0,5-1,5 m) / haute (>1,5 m) | haute = canopée : segmentation en arbres (maxima locaux du MNH, rayon 1-3 m), hauteur et diamètre de couronne |
| 6 | bâtiment | emprises/hauteurs, murs = verticalité du nuage |
| 9 | eau | plans d'eau |
| 17 | tablier de pont | ponts (hauteur sous tablier) |
| 64 | sursol pérenne | éoliennes, antennes, structures de pont > 5 m, pylônes, portiques |
| 65 | artefact | à rejeter |
| 66 | points virtuels | sous les ponts, retirés des MNx |
| 67 | divers bâti | murs bas, glissières, mobilier : candidats pour clôtures/glissières (peu fiable seul, croiser avec BD TOPO `construction_lineaire`) |
Source des libellés : DC_LiDAR_HD_1-0.pdf ci-dessus ; présentation https://www.openig.org/sites/default/files/2025-12/IGN-ATELIER%20LIDAR-2025.pdf [NV]. Dérivés pratiques : hauteur canopée = MNH ou `Z - sol` des classes 3-5 ; arbres = `scipy.ndimage.maximum_filter` sur le MNH lissé ; murs = classe 6/67 avec grande hauteur et faible emprise.

**RGE ALTI 1 m**
```bash
# WMS-R (couche MNT RGE ALTI ; nodata -99999) [V]
curl -o rge.tif "https://data.geopf.fr/wms-r/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES&FORMAT=image/geotiff&STYLES=&CRS=EPSG:2154&BBOX=911000,6235300,912000,6236300&WIDTH=1000&HEIGHT=1000"
# MNS photogrammétrique : ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES.MNS [NV pixel]
```
Téléchargement départemental (dalles ASC 1 m, L93-IGN69, 7z multi-volumes ; D013 = 2 volumes, ~7,2 Go au total [V]) : liste `https://data.geopf.fr/telechargement/resource/RGEALTI` (page 2 pour D011-D021), fiche d'un département : `.../resource/RGEALTI/RGEALTI_2-0_1M_ASC_LAMB93-IGN69_D013_2022-12-16`, fichiers `.../download/RGEALTI/<id>/<id>.7z.001`. À éviter pour une petite zone.

**API altimétrie (points / profils) [V]**
```bash
curl "https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json?lon=5.60&lat=43.19&resource=ign_lidar_hd_mnt_mono_wld&zonly=false"
# {"elevations":[{"lon":5.6,"lat":43.19,"z":40.51,"acc":"Pas de 50 cm"}]}
curl "https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevationLine.json?lon=5.60|5.601&lat=43.19|43.191&resource=ign_rge_alti_wld&profile_mode=simple&sampling=3"
```
Ressources (liste : `https://data.geopf.fr/altimetrie/resources`) : `ign_lidar_hd_mnt_mono_wld` (avec interpolation), `..._multi_wld` (sans), `ign_lidar_hd_mnx_*`, `ign_rge_alti_wld`, `ign_rge_alti_par_territoires`. `resource=ALTIMETRIE` a rendu -99999 au point de test : ne pas l'utiliser. Réservé à de petits nombres de points (contrôle, calage), pas au maillage.

### 1.2 Imagerie

Orthophotos : WMS-R (GeoTIFF/JPEG/PNG, tout CRS, <= 5010 px) ou WMTS (tuiles 256 px).
| Couche | Contenu | Notes |
|---|---|---|
| `HR.ORTHOIMAGERY.ORTHOPHOTOS` | BD ORTHO HR (annoncée 20 cm ; 2000 px pour 400 m = 20 cm [V]) | meilleure pour les textures ; TMS `PM_6_19` |
| `ORTHOIMAGERY.ORTHOPHOTOS` | BD ORTHO (mosaïque 20 cm), `PM_0_19` | repli [V] |
| `ORTHOIMAGERY.ORTHOPHOTOS.BDORTHO` | idem, millésimes | [V] |
| `ORTHOIMAGERY.ORTHOPHOTOS.IRC` | infrarouge couleur (végétation) | [V], PNG 4 bandes |
| `ORTHOIMAGERY.ORTHOPHOTOS.1950-1965`, `.1965-1980`, `.1980-1995`, `...2000-2005` | historiques | **PNG obligatoire** (4 bandes ; JPEG -> erreur) [V] |
| `ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2012...2026` | Pléiades (~50 cm) | couverture partielle : image vide à notre point en 2024 [V] ; PNG |
| `ORTHOIMAGERY.ORTHO-SAT.SPOT.2013...2025` | SPOT 1,5 m | [NV] |
| `IGNF_COSIA_2021-2023`, `IGNF_COSIA_2024-2026` | occupation du sol IA 20 cm (WMTS) | [NV] couches ; vérité terrain utile pour surfaces |
```bash
# ortho 20 cm d'une emprise 400 m (L93) [V]
curl -o ortho.jpg "https://data.geopf.fr/wms-r/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=HR.ORTHOIMAGERY.ORTHOPHOTOS&FORMAT=image/jpeg&STYLES=&CRS=EPSG:2154&BBOX=911000,6235300,911400,6235700&WIDTH=2000&HEIGHT=2000"
# max par requête : WIDTH=HEIGHT=5010 (5011 -> HTTP 400) ; 400 m / 2000 px ~ 0,68 Mo, ~4 Mo/km² en JPEG
# tuile WMTS Web-Mercator (z19, ~0,22 m/px à cette latitude) [V]
curl -o t.jpg "https://data.geopf.fr/wmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER=HR.ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&FORMAT=image/jpeg&TILEMATRIXSET=PM&TILEMATRIX=19&TILEROW=192270&TILECOL=270299"
```
- WMTS : TileMatrixSet `PM` (3857, toutes échelles) ou `PM_x_y` (zoom limité) ; versions L93 : `2154_5cm`, `2154_10cm`, `2154_10m` (certaines couches `.L93`, ex. `HR.ORTHOIMAGERY.ORTHOPHOTOS.L93`) [NV usage]. Préférer WMS-R en L93 pour éviter reprojection et déformation.
- Pour des textures sol en Unreal : découper en blocs de 4096-8192 px, JPEG qualité 90, garder la BBOX exacte de chaque bloc.
- Orthos « ZICAD » ou zones restreintes : couche `ORTHOIMAGERY.ORTHOPHOS.RESTRICTEDAREAS`.

### 1.3 Vecteur - BD TOPO via WFS [V]
Endpoint `https://data.geopf.fr/wfs/ows`, version 2.0.0, `OUTPUTFORMAT=application/json` (GeoJSON), `SRSNAME=EPSG:2154` (coordonnées **X,Y,Z** en mètres ; les géométries BD TOPO sont en 3D). **Max 5000 entités par requête** (CountDefault=5000) : paginer avec `STARTINDEX` + `SORTBY=cleabs` (ou découper la BBOX).
```bash
# bâtiments avec hauteur sur 400 m [V] : 254 entités
curl -G "https://data.geopf.fr/wfs/ows" --data-urlencode "SERVICE=WFS" --data-urlencode "VERSION=2.0.0" --data-urlencode "REQUEST=GetFeature" --data-urlencode "OUTPUTFORMAT=application/json" --data-urlencode "SRSNAME=EPSG:2154" --data-urlencode "TYPENAMES=BDTOPO_V3:batiment" --data-urlencode "BBOX=911000,6235300,911400,6235700,EPSG:2154" -o bat.json
# pagination [V] : &COUNT=1000&STARTINDEX=1000&SORTBY=cleabs ; numberMatched donne le total
# filtre CQL [V] (nature='Route à 1 chaussée' -> 45 tronçons)
... --data-urlencode "CQL_FILTER=BBOX(geometrie,911000,6235300,911400,6235700,'EPSG:2154') AND nature='Route à 1 chaussée'"
```
Couches `BDTOPO_V3:*` (liste exacte dans les Capabilities) et attributs utiles (relevés [V]) :
| Couche | Attributs clés pour le jeu |
|---|---|
| `troncon_de_route` (LineString) | `nature` (Route à 1 chaussée, Route à 2 chaussées, Type autoroutier, Bretelle, Rond-point, Route empierrée, Chemin, Sentier, Escalier), `largeur_de_chaussee` (m), `nombre_de_voies`, `sens_de_circulation`, `importance` (1-6), `position_par_rapport_au_sol` (0 sol, >0 pont, <0 tunnel), `acces_vehicule_leger`, `urbain`, `vitesse_moyenne_vl`, `nom_collaboratif_gauche`, `prive` |
| `batiment` (MultiPolygon 3D) | `hauteur` (m), `nombre_d_etages`, `altitude_minimale_sol`, `altitude_maximale_toit`, `nature`, `usage_1`, `materiaux_des_murs`, `materiaux_de_la_toiture` |
| `zone_de_vegetation` | `nature` : Bois, Forêt fermée de feuillus/conifères/mixte, Forêt ouverte, Haie, Vigne, Verger, Lande ligneuse... |
| `haie`, `terrain_de_sport` (`nature` : tennis, bassin de natation, piste...), `cimetiere`, `zone_d_activite_ou_d_interet` | surfaces d'usage |
| `construction_lineaire` | `nature` : Mur de soutènement, Mur, Pont, Tunnel, Quai, Ruines (murs, soutènements) |
| `construction_surfacique` / `construction_ponctuelle` | Pont, Cale / Antenne, Croix, Clocher, Phare, Cheminée, Transformateur |
| `surface_hydrographique` (Réservoir-bassin, Retenue...), `troncon_hydrographique` (`nature`, `persistance`, `classe_de_largeur`), `plan_d_eau`, `cours_d_eau` | eau |
| `ligne_electrique` (`voltage`), `pylone` (`hauteur`), `poste_de_transformation`, `transport_par_cable` | lignes et pylônes |
| `troncon_de_voie_ferree`, `equipement_de_transport`, `piste_d_aerodrome`, `aerodrome` | rail, gares, pistes |
| `toponymie` (`graphie_du_toponyme`, `nature_de_l_objet`) | noms |
Limites : pas de largeur d'arbres ; `hauteur` bâtiment parfois nulle (-> calculer depuis MNH) ; routes sans nombre de voies ni largeur sur chemins/sentiers ; couches vides si rien dans l'emprise (réponse de 147 octets, normal). Mise à jour régulière : https://www.data.gouv.fr/datasets/bd-topo-r (dernière modif. constatée 2026-11-12).
Téléchargement départemental complet (GPKG/SHP, plusieurs Go) : `https://data.geopf.fr/telechargement/resource/BDTOPO` [NV usage]. Pour >5 km², préférer ce téléchargement au WFS.

**Autres vecteurs WFS [V sauf mention]**
| Produit | Couche WFS | Note |
|---|---|---|
| BD Forêt v2 (`LANDCOVER.FORESTINVENTORY.V2`) | `LANDCOVER.FORESTINVENTORY.V2:formation_vegetale` | attributs `tfv`, `essence` (ex. Pin d'Alep), `tfv_g11` : essences pour choisir les arbres ; BD Forêt v1 `BDFORETV1_BDD_FXX_LAMB93_20140403:resu_bdv1_shape` [NV] |
| Masque forêt / formations végétales | `IGNF_MASQUE-FORET.2021-2023:masque_foret` [NV] | |
| RPG (parcelles agricoles) | `RPG.LATEST:parcelles_graphiques` (`code_cultu`, `cat_cult_p`) ; `codes_cultures` | test OK en Beauce (600000,6800000) ; vide en zone non agricole |
| Cadastre PCI (Parcellaire Express) | `CADASTRALPARCELS.PARCELLAIRE_EXPRESS:parcelle`, `:batiment`, `:commune`, `:feuille` | limites de propriétés, utile pour clôtures/haies |
| OCS GE | pas de couche WFS nationale sûre ; téléchargement `https://data.geopf.fr/telechargement/resource/OCSGE` ; affichage WMTS `OCSGE.COUVERTURE.2021-2023`, `OCSGE.USAGE.2021-2023` | couverture/usage du sol par département, millésimes variables [NV] |
| BD CARTO v5 | `BDCARTO_V5:*` | 1:50 000, pour zones très vastes [NV] |
| Courbes de niveau | `ELEVATION.CONTOUR.LINE:courbe` | [NV] |

### 1.4 Plans et cartes pour le repérage visuel
- Plan IGN : WMS-R/WMTS `GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2` (PNG, `PM_0_19`, WMTS aussi `.L93`) [V WMS] ; `IGNF_PLAN-IGN-HD` (JPEG, `PM_6_18`) [NV].
- Classes LiDAR HD en 2D : `IGNF_LIDAR-HD_CLASS` (WMS-R/WMTS, PNG) [V] ; densité : `IGNF_LIDAR-HD_DENSITE-SOL`, `..._DENSITE-SURSOL` [NV] ; ombrages `IGNF_LIDAR-HD_MN{T,S,H}_ELEVATION.ELEVATIONGRIDCOVERAGE.SHADOW` (WMTS/WMS) [NV].
- Cartes SCAN : `SCAN1000`, `SCANREG` (SCAN Régional), `SCAN50_1950` (WMTS `PM_...`) ; `SCAN25`/`SCAN Express` ne figurent plus dans les couches publiques listées [V : absence] : ne pas compter dessus. Pour du repérage détaillé, le Plan IGN suffit.

---
## 2. Hors de France

| Source | Contenu / résolution | Accès | Licence |
|---|---|---|---|
| **Copernicus DEM GLO-30** | MNS mondial 30 m (GLO-90 aussi), Z orthométrique EGM2008 | AWS COG sans clé : `https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N43_00_E005_00_DEM/Copernicus_DSM_COG_10_N43_00_E005_00_DEM.tif` (tuile 1°, 35 Mo) [V] ; schéma `N{lat}_00_E{lon}_00` | Licence Copernicus, usage libre avec mention (texte exact : https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) [NV] |
| SRTM 1 arc-sec | ~30 m, 60°N-56°S, trous, EGM96 | OpenTopography `globaldem` (clé API gratuite obligatoire : 401 sans clé [V]), USGS EarthExplorer | domaine public (NASA) |
| OpenTopography | portail MNT/LiDAR mondial (COP30, SRTMGL1, ALOS, 3DEP) | `https://portal.opentopography.org/API/globaldem?demtype=COP30&south=..&north=..&west=..&east=..&outputFormat=GTiff&API_Key=...` ; doc https://portal.opentopography.org/apidocs/ | variable selon jeu |
| **Pays-Bas AHN4/5** | MNS+MNT 0,5 m, nuage ~10 pts/m² | index GeoJSON `https://service.pdok.nl/rws/ahn/atom/downloads/dsm_05m/kaartbladindex.json` (feuilles GeoTIFF ~46 Mo, EPSG:28992) [V] ; `dtm_05m` analogue [NV] ; nuage : https://www.ahn.nl | CC0 |
| **Suisse** swissALTI3D (MNT 0,5 m ou 2 m) / swissSURFACE3D (nuage) / swissSURFACE3D Raster (MNS 0,5 m) / SWISSIMAGE 10 cm | dalles 1 km | STAC `https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.swissalti3d` (et `ch.swisstopo.swisssurface3d-raster`, `ch.swisstopo.swisssurface3d`, `ch.swisstopo.swissimage-dop10`) [V collections] ; CRS LV95 EPSG:2056, alt. LN02 | OGD gratuit, source à citer : https://www.swisstopo.admin.ch/en/geodata/ogd.html [NV] |
| **Royaume-Uni** (Angleterre) | LiDAR EA : MNT/MNS composites 1 m (jusqu'à 25 cm), nuage ; Écosse/Pays de Galles : portails propres | https://environment.data.gov.uk/survey [NV] | Open Government Licence v3 |
| **Espagne PNOA** | LiDAR 1ère couv. ~0,5-1 pt/m², 2ème couv. >=2-5 pts/m² ; MDT 2/5 m ; PNOA ortho 25-50 cm | CNIG https://centrodedescargas.cnig.es (interface web, hôte injoignable via curl ici) [NV] | CC BY 4.0 scne.es |
| **Italie** | TINITALY DEM 10 m (INGV) ; LiDAR régional variable (ex. Emilia-Romagna, Lombardie, Piémont), Géoportail national PCN | https://tinitaly.pi.ingv.it ; https://gn.mase.gov.it/portale/ [NV] | CC BY 4.0 (TINITALY) ; varie par région |
| **Allemagne** (par Land) | DGM1 (MNT 1 m) + nuages : NRW, Berlin, Brandenburg, Thüringen, Bayern (open data), Saxe... ; ATKIS/LoD2 bâtiments 3D | NRW `https://www.opengeodata.nrw.de` ; Bayern https://geodaten.bayern.de/opengeodata ; couverture variable [NV] | dl-de/by-2-0 ou dl-de/zero-2-0, CC BY 4.0 |
| **USA 3DEP** | MNT 1 m (60 %+ du pays), nuages EPT (AWS `usgs-lidar-public`), 1/3 arc-sec nationale | API produits `https://tnmaccess.nationalmap.gov/api/v1/products` ; nuages : https://registry.opendata.aws/usgs-lidar/ (chemin `s3://usgs-lidar-public/<projet>/ept.json`, nom de projet à lister) [NV] | domaine public (citer USGS) |
| **Overture Maps** | bâtiments (hauteurs partielles), routes, eau, occupation ; GeoParquet | CLI `overturemaps download --bbox=lon0,lat0,lon1,lat1 -f geojson --type=building -o b.geojson` ; DuckDB sur S3 ; release : https://docs.overturemaps.org/getting-data/ [NV : S3 injoignable ici] | par thème : ODbL (partie OSM), CDLA-Permissive-2.0, CC BY 4.0 : https://docs.overturemaps.org/attribution/ |
| **Microsoft GlobalMLBuildingFootprints** | emprises bâtiments IA mondiales, hauteurs partielles | https://github.com/microsoft/GlobalMLBuildingFootprints [NV] | ODbL |
| **Google Open Buildings** (v3, 2.5D temporel) | emprises + hauteur estimée (Afrique, Asie, Amérique latine, Asie du Sud-Est) | https://sites.research.google/gr/open-buildings/ ; miroir combiné VIDA sur source.coop [NV] | CC BY 4.0 + ODbL |
| ESA WorldCover 10 m | occupation du sol mondiale (arbres, herbe, bâti, eau) | https://esa-worldcover.org [NV] | CC BY 4.0 |
Ortho ouverte hors France : Suisse SWISSIMAGE (10 cm, STAC ci-dessus), Pays-Bas Luchtfoto (PDOK, CC0), PNOA, Allemagne selon Land, USA NAIP (1 m, domaine public). Sinon imagerie commerciale (Bing/Google/Mapbox) : **interdite à l'extraction massive**, ne pas la télécharger.

---
## 3. OpenStreetMap

**Overpass** : instance principale `https://overpass-api.de/api/interpreter` : **injoignable depuis cet environnement** (connexion reset) [NV] ; peut l'être aussi ailleurs (charge). Miroirs, politique et quotas : https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances
- `https://maps.mail.ru/osm/tools/overpass/api/interpreter` [V]
- `https://ovp.dresel.systems/api/interpreter` (Europe, 4 requêtes parallèles/IP) [V]
- `https://overpass.private.coffee/api/interpreter`, `https://overpass.kumi.systems/api/interpreter` : timeouts constatés [V : échec], `overpass.osm.jp` : injoignable [V : échec].
Règles : un `User-Agent` descriptif, pas de requêtes parallèles, pause ~30 s sur HTTP 429/406, mettre les réponses en cache. Ordre de la BBOX Overpass : **(sud, ouest, nord, est)**.
```bash
# routes + bâtiments + barrières + arbres sur 400 m [V sur maps.mail.ru et dresel : 402 éléments]
curl -A "carte-reelle-unreal/1.0" --data-urlencode 'data=[out:json][timeout:60];
(way["highway"](43.188,5.598,43.192,5.604);
 way["building"](43.188,5.598,43.192,5.604);
 way["barrier"](43.188,5.598,43.192,5.604);
 node["natural"="tree"](43.188,5.598,43.192,5.604);
 way["natural"="tree_row"](43.188,5.598,43.192,5.604););
out geom;' https://ovp.dresel.systems/api/interpreter
```
Requêtes types [syntaxe NV sauf routes/bâtiments] : mobilier `node["highway"~"street_lamp|bus_stop"]`, `node["amenity"~"bench|waste_basket"]`, `node["emergency"="fire_hydrant"]`, murs `way["barrier"~"wall|retaining_wall|fence|guard_rail"]`, revêtement `way["highway"]["surface"~"asphalt|gravel|dirt|paving_stones"]` (+ `lanes`, `width`, `maxspeed`, `oneway`, `bridge`, `tunnel`, `layer`), eau `way["natural"="water"]` / `way["waterway"]`, usage du sol `way["landuse"]`, `way["natural"~"wood|scrub|grassland|bare_rock"]`, bâtiments `building:levels`, `height`, `roof:shape`, `roof:colour`, relations bâtiments multipolygon : utiliser `nwr[...]; out geom;`.
Pour des grandes zones : `[maxsize:1073741824]`, découper en tuiles de ~2 km, ou utiliser un extrait.

**Extraits** : Geofabrik `https://download.geofabrik.de/europe/france/provence-alpes-cote-d-azur-latest.osm.pbf` (par région, mise à jour quotidienne, ODbL) : hôte injoignable ici [NV]. Découper ensuite : `osmium extract -b 5.55,43.15,5.65,43.22 in.osm.pbf -o zone.osm.pbf`, puis `osmium export` (GeoJSON) ou `ogr2ogr`. Alternative : https://extract.bbbike.org, https://download.openstreetmap.fr (France, ODbL) [NV].

**Complétude** : bâtiments/routes bonnes en ville, hauteurs (`height`, `building:levels`) souvent absentes ; arbres, `barrier`, mobilier : couverture inégale, riche en centre-ville et parcs, quasi vide en rase campagne (aucun arbre/barrière sur notre zone test [V]) ; `surface=`/`lanes=` renseignés sur une minorité de routes. En France, BD TOPO > OSM pour géométrie/hauteur ; OSM > BD TOPO pour mobilier, `surface`, noms de voies cyclables/sentiers, `barrier`, `natural=tree`.

---
## 4. Projections et repères

- **Lambert-93 = EPSG:2154** (RGF93 / Lambert-93), mètres, X est, Y nord ; valable pour la métropole, les DROM ont leur UTM propre (ex. Réunion EPSG:2975, Guyane 2972, Mayotte 4471 ; Antilles : cf. capabilities WMS-R, couches suffixées WGS84UTM20). Les services IGN acceptent aussi 4326 (lat,lon en WMS 1.3.0 / WFS 2.0 urn), 3857.
- **Altitudes** : LiDAR HD et RGE ALTI = **NGF-IGN69** (altitude orthométrique ; `systeme_altimetrique: IGN69` [V]). Hauteur ellipsoïdale h = H + N, N = ondulation de la grille **RAF20** (France métropolitaine, ~44-54 m en France ; grille et notice : https://geodesie.ign.fr/index.php?page=grilles [NV]). Copernicus DEM = EGM2008, SRTM = EGM96 : décalages de plusieurs mètres entre sources -> **ne pas mélanger sans caler** (corriger par la différence médiane sur des zones plates communes). Pour un jeu, rester en altitude orthométrique, soustraire l'altitude de l'origine du niveau.
- **Conversion** (pyproj, `always_xy=True`) : `Transformer.from_crs(4326, 2154, always_xy=True).transform(5.60, 43.19)` -> (911462.13, 6235790.22) [V].
- **Repère local** : choisir une origine (X0,Y0) au centre de la zone, arrondie (ex. au km), `x_loc = X - X0`, `y_loc = Y - Y0` (mètres). Dans Unreal (cm, Z haut, repère main gauche, X vers l'avant) : `UE_X = x_loc*100`, `UE_Y = -y_loc*100` (**Y inversé** : le nord image est en haut, Unreal a Y croissant vers le sud / la droite), `UE_Z = (alt - alt_ref)*100`. Garder (X0,Y0,alt_ref) dans un fichier de métadonnées pour retrouver la géoréférence.
- **Heightmap Unreal** : 16 bits ; Landscape tailles utiles 505, 1009, 2017, 4033, 8129 sommets ; résolution 100 cm/quad de base = 1 m ; plage Z : à ZScale=100 la hauteur totale couvre 512 m (-256..+256 m autour de l'origine) ; ajuster ZScale à (zmax-zmin) ; valeur uint16 = round((z - zmin)/(zmax-zmin)*65535). Rééchantillonner le MNT 0,5 m vers la grille Landscape en conservant le lien nord haut (ligne 0 = nord). Docs : https://dev.epicgames.com/documentation/en-us/unreal-engine/landscape-technical-guide [NV].
- **Déclinaison / azimut du soleil** : le nord du carroyage L93 n'est pas le nord vrai. Convergence des méridiens au point test : **+1,89°** (`pyproj.Proj('EPSG:2154').get_factors(lon,lat).meridian_convergence` [V] ; approx. (lon-3°)·sin(lat) = 1,78°) ; positive à l'est de 3° E, négative à l'ouest. Un azimut solaire vrai (astral/pysolar, mesuré depuis le nord vrai, sens horaire) devient `az_grille = az_vrai - γ`. Dans Unreal, régler le North Offset du SunSky (ou l'actor Geo-referencing) pour que la direction « nord grille » corresponde à l'axe -Y d'Unreal (Y inversé, §ci-dessus). La déclinaison magnétique n'intervient pas pour le soleil.
- Pièges fréquents : BBOX WMS 1.3.0 en 4326 = lat,lon ; WFS `BBOX=` sans suffixe CRS = ordre du CRS par défaut ; GeoJSON WFS en L93 avec Z (3 valeurs par point) ; nodata -9999 (LiDAR) vs -99999 (RGE ALTI) ; orthos 4 bandes en PNG ; MNx WMS float32 non compressés.

---
## 5. Choisir la bonne source

```
Zone en France métropolitaine ?
├─ oui : LiDAR HD couvert (WFS metadata non vide) ?
│   ├─ oui  -> MNT/MNS/MNH 0,5 m (WMS-R) + ortho HR 20 cm (WMS-R) + BD TOPO (WFS)
│   │          + COPC (Range) si arbres individuels / murs / glissières
│   └─ non  -> RGE ALTI 1 m (WMS-R) + ortho + BD TOPO + canopée via BD Forêt / OSM
└─ non : pays avec LiDAR ouvert (NL, CH, UK, USA, ES, DE) -> tableau §2 ;
         sinon Copernicus GLO-30 + OSM/Overture + ortho libre si disponible
```
| Cas | Emprise | Source recommandée | Volume approximatif |
|---|---|---|---|
| Hangar 200 m | ~0,05 km² | WMS-R MNT+MNS+MNH 0,5 m (400x400 px chacun, <1 Mo) ; ortho HR 2000 px (~0,7 Mo) ; WFS bâtiments/routes ; points COPC via Range sur ~0,25 km² (quelques dizaines de Mo) ; relevé photo pour détails | < 50 Mo |
| Spéciale 7 km (couloir ~7x0,5 km) | ~3,5 km² | MNT/MNS/MNH 0,5 m en dalles de 1 km (2000x2000 px, 16 Mo chacune) ; ortho HR en blocs 5010 px (2,5 km) ; BD TOPO par tronçons ; tuiles ~8 dalles | MNx ~0,4 Go brut (~0,1 Go GeoTIFF compressé) ; ortho ~20 Mo JPEG ; COPC 1-1,5 Go si utilisé |
| Ville 5 km² | ~5 km² | idem par blocs, 5-6 dalles de 1 km ; BD TOPO >5000 entités : paginer (ex. 59 527 bâtiments sur 300 km²) ; Overpass/OSM pour mobilier ; COPC pour arbres | MNx ~0,3-0,5 Go ; ortho ~25 Mo JPEG (20 cm) ; COPC ~0,8 Go |
Ordres de grandeur [V] : ortho 20 cm = ~4 Mo/km² (JPEG) ; MNx 0,5 m = 16 Mo/km²/couche non compressé (24 Mo GeoTIFF natif annoncé) ; COPC = ~160 Mo/km² (jusqu'à 1-2 Go) ; RGE ALTI département = plusieurs Go. Pour les carreaux au-delà de 5010 px : boucler sur des dalles de 1 km, mettre une pause entre requêtes (< 10/s), reprendre les dalles échouées, valider avec `rasterio` (nodata, min/max plausibles) avant l'assemblage.

---
## 6. Licences et crédits

| Données | Licence | Page officielle |
|---|---|---|
| IGN : LiDAR HD, RGE ALTI, BD TOPO, BD ORTHO, BD Forêt, RPG, PCI, OCS GE (tous « lov2 » sur data.gouv.fr, vérifié par API) | **Licence Ouverte 2.0 (Etalab)** : réutilisation libre, y compris commerciale, **mention de la source et de la date de mise à jour** | https://www.etalab.gouv.fr/licence-ouverte-open-licence/ ; CGU https://cartes.gouv.fr/cgu |
| OpenStreetMap | **ODbL 1.0** : attribution « © les contributeurs d'OpenStreetMap » ; une base dérivée (carte/vecteurs réutilisables) doit rester sous ODbL (partage à l'identique) ; un rendu (carte de jeu) est un « Produced Work » : attribution suffit | https://www.openstreetmap.org/copyright |
| Copernicus DEM, ESA WorldCover, PNOA, TINITALY, Google Open Buildings | CC BY 4.0 / licence Copernicus : mention du producteur | liens du §2 |
| AHN, USGS 3DEP | CC0 / domaine public | liens du §2 |

Modèle de crédits à intégrer dans un mod (adapter aux couches utilisées, indiquer l'année de l'extraction) :
```
Données géographiques : © IGN - LiDAR HD, RGE ALTI®, BD ORTHO®, BD TOPO® (Licence Ouverte Etalab 2.0, extraction novembre 2026)
Données cartographiques : © les contributeurs d'OpenStreetMap (ODbL), https://www.openstreetmap.org/copyright
Copernicus DEM GLO-30 : produit avec les données Copernicus WorldDEM-30 © DLR e.V. 2010-2014 et © Airbus Defence and Space GmbH 2014-2018, fournies par l'Union européenne et l'ESA (si utilisé)
```
Ne pas indiquer ou suggérer une approbation officielle par l'IGN. Les marques de jeux, voitures et logos ne sont pas couverts par ces licences. Les textes ci-dessus ne constituent pas un avis juridique ; en cas de doute lire les pages officielles citées.
