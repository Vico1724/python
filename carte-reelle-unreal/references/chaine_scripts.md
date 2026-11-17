# Chaîne de scripts `scripts/`

Une zone = un `zone.json` ; toutes les étapes prennent `--zone zone.json --sortie DOSSIER [--cache DOSSIER] [--force]`
(`--zone` facultatif dès que `DOSSIER/repere.json` existe). Chaque étape imprime 1 à 5 lignes, écrit ses détails
dans `DOSSIER/journaux/<étape>.json`, garde ses téléchargements dans `DOSSIER/cache/` (partageable entre zones
avec `--cache`) et se saute si elle a déjà tourné pour le même `zone.json` (sauf `--force`).
Tout enchaîner : `python scripts/tout_lancer.py --zone zone.json --sortie DOSSIER` (une ligne par étape,
log complet dans `journaux/tout_lancer.log`, arrêt à la première étape en échec, options `--depuis 03 --jusqua 07`,
`--mnt`, `--ortho`, `--sans-osm`, `--vignettes`, `--table`). Dépendances : `scripts/requirements.txt`.

## Étapes

| script | rôle | sorties principales | durée observée (compact / couloir) |
|---|---|---|---|
| `01_emprise.py` | lit zone.json, choisit la projection (Lambert-93 en France, UTM ailleurs), origine au centre de la zone de détail, taille de heightmap | `repere.json`, `emprise.geojson` (WGS84) | < 1 s |
| `02_relief.py` | MNT LiDAR HD + RGE ALTI (trous : mer = 0 m, sinon voisin), heightmap 16 bits, échelles Unreal ; MNT/MNS LiDAR 0,5 m de la zone de détail. `--mnt f.tif`, `--sans-lidar-fin` | `relief/mnt.tif`, `relief/heightmap_<N>.png` + `.r16`, `relief/mnt_50cm.tif`, `mns_50cm.tif` | 7 s / 10 s (10 / 36 Mo) |
| `03_ortho.py` | BD ORTHO en dalles : texture exacte du Landscape (≤ 8192 px) + basse résolution du lointain. `--ortho f.tif` | `ortho/ortho.tif`, `ortho_terrain.jpg`, `ortho_lointain.jpg` | 7 s / 11 s |
| `04_vecteurs.py` | BD TOPO WFS (13 couches) + OSM Overpass (miroirs, budget 150 s, non bloquant en France, obligatoire ailleurs), découpe à la zone de détail, repère local. `--sans-osm` | `vecteurs/bdtopo_*.geojson`, `vecteurs/osm_*.geojson` | 218 s (Overpass en échec) / 35 s (OSM obtenu) |
| `05_vegetation.py` | arbres par maxima locaux du MNH LiDAR + houppiers (filtre NDVI IRC), sinon semis dans les zones de végétation ; type = famille + taille. `--methode auto\|lidar\|semis` | `vegetation/arbres.csv` (`x,y,z,hauteur,rayon,type`) | 4 s / 10 s |
| `06_photos_rue.py` | images Panoramax (API STAC, bbox subdivisée si saturée), filtrées à la zone. `--vignettes --max N` | `photos/photos_rue.csv` (`id,lon,lat,x,y,cap,date,url_image,licence`), `photos/vignettes/` | 10 s (20 vignettes) / 1 s |
| `07_lointain.py` | relief RGE ALTI 25 m sur 2 × rayon, drapé de l'ortho basse résolution, abaissé de 2 m sous le Landscape ; terrain proche en maillage | `lointain/lointain.glb`, `lointain/terrain_proche.glb` | 2 s / 3 s |
| `08_paquet_unreal.py` | assemble le paquet : bâtiments extrudés, rubans de routes, placements, manifeste, LISEZMOI. `--table t.csv` | `paquet_unreal/` | 1-2 s |
| `unreal/importer_paquet.py` | **éditeur Unreal** : importe les glb, contrôle les bornes, pose décor + arbres en HISM d'après `table_assets.csv`, éclairage ; consigne Landscape. `--essai` hors Unreal | niveau `/Game/CarteReelle/<nom>/<nom>`, `Saved/CarteReelle/<nom>/rapport.json` | non exécuté |
| `controle_paquet.py` | `--sortie DOSSIER` ou `--paquet P` : verdict CONFORME / NON CONFORME (code 1), écarts | `paquet_unreal/controle.json` | < 1 s |
| `geo.py` | module commun : config, projections, repère, requêtes avec reprises et cache, WMS/WFS/Overpass, rasters, glTF | | |

Limites connues :
- Overpass est souvent saturé (504, délais) : en France l'étape 04 continue sans OSM après le budget de 150 s (218 s observées au total) ; relancer plus tard
  la complète (`osm_budget_s` dans zone.json). Hors France sans OSM, 04 échoue avec la marche à suivre.
- Le Landscape n'est pas créé par script (pas d'API Python stable) : consigne exacte écrite (fichier, Location, Scale) ;
  en attendant, `terrain_proche.glb` sert de sol. Ponts et tunnels : dans `routes.json`, sans ruban.
- Arbres LiDAR : un bosquet dense peut être compté comme un seul arbre ; la famille vient de la zone de végétation
  BD TOPO (nature du peuplement, pas l'essence de l'arbre). Hors LiDAR, le semis donne une densité, pas des positions.
- Bâtiments en blocs (pas de toits à pans). Contour « France » grossier : une zone frontalière (Genève) est traitée
  comme française et finit en trous bouchés. Une zone de plus de ~8 km de côté au pas 1 m fait monter le pas (8129 px max).

## zone.json

```json
{"nom": "ma_zone",
 "emprise": {"type": "bbox", "bbox": [lon_min, lat_min, lon_max, lat_max]},
 // ou {"type": "polygone", "fichier": "contour.kml"}      (KML ou GeoJSON, chemin relatif à zone.json)
 // ou {"type": "polygone", "coordonnees": [[lon, lat], ...]}
 // ou {"type": "trace", "fichier": "trace.gpx", "largeur_couloir_m": 200}   (GPX, KML ou GeoJSON)
 // ou {"type": "trace", "coordonnees": [[lon, lat], ...], "largeur_couloir_m": 200}
 "marge_m": 50, "resolution_terrain_m": 1.0, "taille_heightmap": "auto",
 "resolution_ortho_m": 0.5, "texture_max_px": 8192,
 "lointain": {"rayon_m": 4000, "pas_m": 25, "texture_px": 4096, "abaissement_m": 2.0},
 "vegetation": {"methode": "auto", "hauteur_min_m": 2.0},
 "photos_rue": {"vignettes": false, "max_vignettes": 100},
 "osm": true, "osm_budget_s": 150,
 "sources": {"mnt": null, "ortho": null}}     // fichiers fournis, relatifs à zone.json (hors France)
```
Toutes les clés sauf `nom` et `emprise` ont ces valeurs par défaut. Exemples : `assets/zone_exemple.json`
(compact, bbox ~400 m) et `assets/zone_exemple_couloir.json` (couloir de 200 m sur ~1 km de route).

## repere.json (dans DOSSIER, copié dans le paquet)

`crs`, `france`, `origine_proj` [x, y] (m, arrondis), `origine_wgs84`, `z0_m` (sol à l'origine, fixé par 02),
`axes` (local : x est, y nord, z = altitude − z0 ; Unreal : X = 100x, Y = −100y, Z = 100z cm ; glTF : X est,
Y haut, Z sud), `emprise_locale` / `zone_detail_locale` (GeoJSON local), `bornes_detail_locales`,
`terrain` {`taille_px`, `pas_m`, `demi_cote_m`, `bornes_locales`; pixel (i, j) au point x = −demi + j·pas,
y = demi − i·pas}, `altitude_min_m`, `altitude_max_m`, `unreal_landscape` {`echelle_cm` x/y/z,
`position_centre_cm` (Location du panneau New Landscape), `position_coin_acteur_cm`, `z_min_m`, `z_max_m`,
formule : z = z_min + valeur/65535 · (z_max − z_min)}, `ortho`, `maillages` (bornes Unreal en cm), `lidar_fin`.
Échelle Z = (z_max − z_min) · 12800 / 65535 ; Z de position = 100 · z_min + 32768/65535 · 100 · (z_max − z_min).

## manifeste.json (paquet_unreal/)

`format` = `carte-reelle-unreal/1`, `nom`, `cree_le`, `repere` (extrait de repere.json), `unites`,
`emprise_locale`, `bornes_detail_locales`, `altitudes_m`, `landscape` (fichier, texture, échelles, positions,
taille, pas, bornes), `maillages` [{`nom`, `fichier`, `role` (lointain, terrain_proche, batiments, routes),
`bornes_cm` {min, max} en Unreal, `collision` (aucune / complexe), `poser`, `ombre`, `couleur` éventuelle}],
`placements` {`arbres` {fichier, colonnes, nombre, types, table}, `batiments` {fichier, nombre, sources_hauteur},
`routes` {fichier, nombre}}, `fichiers` [{`chemin`, `role`, `octets`, `format`, `nombre`}], `sources` (licences).
`table_assets.csv` : `type,asset,hauteur_ref_m,rayon_ref_m,echelle (uniforme|hauteur_rayon),pivot_z_cm,collision`.

## Ce qui a été testé (novembre 2026, ce dépôt, Python 3.13)

- Chaîne complète `tout_lancer.py` sur deux zones réelles près de lon 5,60 / lat 43,19 (Bouches-du-Rhône) :
  compacte (bbox ~400 m, heightmap 505) et couloir de 200 m le long d'~1 km de la D40B (heightmap 1009) ;
  `controle_paquet.py` : CONFORME sur les deux. Compact : 2417 arbres, 321 bâtiments, 118 routes,
  252 s dont 218 s d'attente d'Overpass injoignable, 14 Mo téléchargés, paquet 18 Mo. Couloir : 3679 arbres,
  186 bâtiments, 92 routes, 76 s avec OSM, 42 Mo téléchargés, paquet 22 Mo. Relance : 6 s (tout « déjà fait »).
- Rasters relus : dimensions, min/max, aucun pixel sans donnée, heightmap relue = écrite ; superposition
  ortho / bâtiments / routes / arbres vérifiée à l'œil.
- Entrées GPX (tracé) et KML (polygone) par `01_emprise.py` ; zone hors France (Barcelone) : 02, 03, 04 échouent
  avec la marche à suivre, puis chaîne complète CONFORME avec `sources.mnt`/`sources.ortho` (rasters synthétiques
  en WGS84) et OSM.
- Contrôle négatif : heightmap trouée, glb supprimé, arbre déplacé hors zone -> NON CONFORME avec les écarts.
- Idempotence : relance de `tout_lancer.py` -> étapes « déjà fait ».

## Non testé

- `unreal/importer_paquet.py` dans Unreal (pas d'éditeur ici) : syntaxe vérifiée, mode `--essai` exécuté
  (lecture du manifeste et de la table, calcul des transformations). Premier lancement : lire le rapport.
- Import manuel du Landscape avec les valeurs calculées (formules d'Unreal, non vérifiées en éditeur).
- Zones de plus de 1 km, montagne, DOM-TOM (hors Lambert-93), Windows (chemins et encodage prévus, non essayés).
