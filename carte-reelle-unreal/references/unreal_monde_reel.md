# Unreal Engine 5 : recréer un lieu réel par scripts (référence pour l'agent)

Rédigé en novembre 2026. Cible : UE 5.4 à 5.7 (5.8 existe, non couvert). Légende : **[V]** = à vérifier selon la version / dans le projet ; **[Q]** = source de qualité moyenne (forum, presse) ; URL suffixée † = page non relue en entier lors de la rédaction (la doc Epic servait des pages vides). Les noms exacts de nœuds, propriétés et flags changent : en cas de doute, introspecter (`dir(unreal.X)`, `help(unreal.X)`) avant d'écrire.

## Table des matières
1. Unités et repères
2. Landscape depuis un MNT
3. World Partition
4. Géométrie importée
5. Végétation et dispersion
6. Matériaux de terrain
7. Lumière et ciel
8. Lointain
9. Automatisation
10. Outils géospatiaux
11. Performance
12. Liste de contrôle avant cuisson

Règle d'or : **la donnée source (MNT, GeoJSON, CSV, textures) est la vérité ; le niveau est un artefact reconstruit par script**. Un seul fichier `zone.json` (origine, emprise, échelles, chemins) alimente tous les scripts.

---
## 1. Unités et repères
Doc : https://dev.epicgames.com/documentation/en-us/unreal-engine/large-world-coordinates-rendering-in-unreal-engine-5 ; https://dev.epicgames.com/documentation/en-us/unreal-engine/landscape-technical-guide-in-unreal-engine

| Sujet | Valeur / règle |
|---|---|
| Unité | 1 uu = 1 cm ; 1 m = 100 uu ; 1 km = 100 000 uu |
| Repère | Main gauche, Z haut, X avant, Y droite. Yaw positif = X vers Y (sens horaire vu de dessus) |
| Convention recommandée | **X = est, Y = -nord, Z = altitude** (vue de dessus : est à droite, nord en haut ; un raster nord-en-haut s'importe sans retournement) |
| Conversion | `X = (E - E0)*100`, `Y = -(N - N0)*100`, `Z = (alt - alt0)*100` |
| Cap compas (0° = nord, horaire) → yaw UE | `yaw = cap - 90` (cap 90° est → yaw 0 ; cap 180° sud → yaw 90) |
| Origine | Centre de la zone, E0/N0 arrondis (ex. multiples de 1000 m), notés dans `zone.json` |
| Projection | Repère métrique **local** : `+proj=tmerc +lat_0=.. +lon_0=.. +k=1 +ellps=WGS84` (pas d'échelle). UTM (k0 = 0,9996) ou Lambert-93 : distorsion jusqu'à ~0,04 % = 4 m sur 10 km, tolérable mais à connaître |
| Courbure terrestre | ~7,8 m de chute sur 10 km ; ignorée en projection plane (zones < 20 km) |
| Altitude | Vérifier le datum (orthométrique type NGF-IGN69 vs ellipsoïde WGS84 : écart ~45-55 m en France) |
| Précision float32 | ~0,06 cm à 5 km de l'origine, ~0,5-1 cm à 50-100 km. Garder l'origine au centre |
| LWC (UE 5.0+) | `FVector` en double précision ; monde utilisable ~88 000 km (2^43 cm) [V]. Les matériaux et certains systèmes restent en précision relative (tile offset). Pas d'excuse pour une origine excentrée : les shaders, la physique et certains plugins se dégradent |

```python
import unreal, math
def enu_to_ue(e, n, alt, o):            # mètres -> unreal.Vector (cm), o = (E0, N0, alt0)
    return unreal.Vector((e-o[0])*100.0, -(n-o[1])*100.0, (alt-o[2])*100.0)
def bearing_to_yaw(b): return b - 90.0
```
`unreal.Vector` est en double depuis UE 5.0. Piège : Sun Position suppose le nord le long de +X (voir §7) ; avec la convention ci-dessus le nord est -Y, donc renseigner `North Offset` (typiquement 270 ou -90, signe **[V]** par test visuel : à midi, hors zone tropicale nord, le soleil doit apparaître côté sud, soit +Y).

---
## 2. Landscape depuis un MNT réel
Doc : https://dev.epicgames.com/documentation/en-us/unreal-engine/landscape-technical-guide-in-unreal-engine ; https://dev.epicgames.com/documentation/en-us/unreal-engine/landscape-edit-layers-in-unreal-engine ; https://dev.epicgames.com/documentation/en-us/unreal-engine/landscape-patch-system

### 2.1 Tailles recommandées (tableau officiel, lu sur la doc)
| Résolution (sommets) | Quads/section | Sections/composant | Taille composant (quads) | Composants |
|---|---|---|---|---|
| 8129 x 8129 | 127 | 4 (2x2) | 254 | 1024 (32x32) |
| 4033 x 4033 | 63 | 4 (2x2) | 126 | 1024 (32x32) |
| 2017 x 2017 | 63 | 4 (2x2) | 126 | 256 (16x16) |
| 1009 x 1009 | 63 | 4 (2x2) | 126 | 64 (8x8) |
| 1009 x 1009 | 63 | 1 | 63 | 256 (16x16) |
| 505 x 505 | 63 | 4 (2x2) | 126 | 16 (4x4) |
| 505 x 505 | 63 | 1 | 63 | 64 (8x8) |
| 253 x 253 | 63 | 4 (2x2) | 126 | 4 (2x2) |
| 127 x 127 | 63 | 4 (2x2) | 126 | 1 |

Règle : taille = composants x quads + 1. Un MNT hors tableau doit être rééchantillonné (`gdal_translate -outsize`) à la taille valide la plus proche **ou** importé avec l'option de redimensionnement/padding de l'éditeur (le redimensionnement flou le relief : préférer rééchantillonner soi-même, `-r cubicspline`).

### 2.2 Échelles et codage 16 bits
| Élément | Formule |
|---|---|
| Emprise | `(N_sommets - 1) x échelle_XY` cm (1009 px à 100 cm/px = 1008 m) |
| Échelle XY (cm/pixel) | `pas_MNT_m x 100` (MNT 1 m -> 100 ; 5 m -> 500 ; 0,5 m -> 50). Ne pas descendre sous 50 sans raison (coût) |
| Valeur 16 bits | 0..65535 ; 32768 = hauteur locale 0 |
| Hauteur locale (cm) | `(v - 32768)/128 x ScaleZ` ; plage totale = `512 x ScaleZ` cm (ScaleZ = 100 donne -256..+255,99 m) |
| **Échelle Z** | `ScaleZ = plage_m x 100 / 512` (doc : 4207 m -> 420700 cm -> 821,6796875). Plage = `alt_max - alt_min` du MNT (ou un peu plus) |
| Encodage | `v = round((alt - alt_min)/(alt_max - alt_min) x 65535)` |
| Position Z de l'acteur Landscape | `Z = (alt_min - alt0)x100 + 256 x ScaleZ` cm (la valeur 0 se trouve à `-256 x ScaleZ`) ; **vérifier par un point de contrôle connu** |
| Pas vertical | `plage/65535` : 400 m -> 0,6 mm ; 3000 m -> 4,6 cm (paliers visibles sur pentes douces : alors tuiler, une plage par tuile) |

Formats d'import : PNG gris 16 bits (recommandé), r16, r8 ; `.raw` exige un `.json` voisin (largeur, hauteur, profondeur de bits ; la doc écrit `bbp`, probablement une coquille de `bpp` **[V]**). Orientation : raster nord-en-haut = pas de retournement avec la convention §1.

```python
import numpy as np
from PIL import Image
def write_height_png(dem, path):          # dem float32 mètres, déjà à la taille valide (ex. 1009x1009), nord en haut
    lo, hi = float(np.nanmin(dem)), float(np.nanmax(dem))
    u16 = np.rint((np.nan_to_num(dem, nan=lo)-lo)/(hi-lo)*65535).astype('<u2')
    Image.fromarray(u16).save(path)       # PNG 16 bits
    return lo, hi, (hi-lo)*100/512        # alt_min, alt_max, ScaleZ
```
GDAL équivalent : `gdalwarp -t_srs "<proj local>" -tr 1 1 -r cubicspline mnt.tif loc.tif` puis `gdal_translate -of PNG -ot UInt16 -scale <min> <max> 0 65535 -outsize 1009 1009 loc.tif h.png`.

### 2.3 Import, tuiles, World Partition
- Import éditeur : mode Landscape > Manage > Import from File (heightmap + weightmaps + échelle + taille de composant). **Pas d'API Python stable connue pour l'import de heightmap** **[V]** : options (a) une petite fonction C++ / plugin éditeur exposée à Python, (b) un Editor Utility qui pilote le flux, (c) import manuel unique d'un niveau gabarit puis scripts pour tout le reste. Interroger `dir(unreal)` pour `Landscape*` avant de choisir.
- Grande zone (> 8129 px ou plusieurs km à 1 m/px) : découper en **tuiles** (ex. 4033 ou 2017) avec recouvrement d'un sommet partagé ; en World Partition, le Landscape est découpé en **Landscape Streaming Proxies** (regroupement de composants configurable à l'import, à aligner sur la taille de cellule §3) **[V]**. Import par région possible (Import Region / 5.x) **[V]**.
- Un Landscape = champ de hauteur 2,5D : ni surplomb, ni tunnel, ni falaise verticale.

### 2.4 Landscape ou maillage statique ?
| Besoin | Choix |
|---|---|
| Relief naturel, grandes surfaces, peinture par couches | Landscape |
| Route de rallye précise au cm (devers, bords, fossés), ponts, tunnels | Maillage statique de route (spline mesh ou export Blender/Houdini) posé sur Landscape, marge +1 à +3 cm contre le z-fighting, Landscape creusé sous la route (spline/patch) |
| Falaises, carrières, surplombs, photogrammétrie | Maillage statique Nanite |
| Pas 1 m insuffisant (route de 4 m, 4 quads) | Landscape à 50 cm, ou route en mesh |

### 2.5 Édition non destructive
| Outil | État | Usage |
|---|---|---|
| Landscape Edit Layers | Stable (mode Landscape > Layers) | Calques de hauteur/poids empilés : MNT brut, correctifs, routes. Cuisson aplatie ; garder les calques dans le projet source [V] |
| Landscape Patches (plugin) | Expérimental jusqu'à 5.6 ; sortie d'« experimental » annoncée par Epic pour 5.7 sur forum, **non confirmée par les notes de version lues** [Q][V] | Patch Edit Layer procédural, patches texture/mesh pilotables par script ; s'attachent au premier calque Patch du premier Landscape trouvé |
| Landscape Splines | Stable | Routes/rivières déformant le terrain, mesh le long de la spline ; peu précis au cm |
| Brushes Blueprint (legacy) | Déprécié au profit des patches | Éviter pour du neuf |

### 2.6 Couches de peinture (weightmaps)
- Une image 8 bits grise par couche, même taille que la heightmap, importée avec le nom de la couche ; chaque couche a un **Layer Info** (asset `LandscapeLayerInfoObject`) avec son **matériau physique** (adhérence, voir §4). Noms de couches = noms des nœuds `Landscape Layer Blend/Sample` du matériau.
- Source : classes d'occupation du sol (OSM, CLC, OCS GE, BD TOPO) rasterisées (`gdal_rasterize`) ou classification de l'ortho (indices de couleur, NDVI). Lisser (flou 1-2 px) pour éviter les bords crénelés ; somme des poids <= 255.
- Routes/chemins : rasteriser la ligne à la largeur réelle dans une couche « route » (+ décalques §6).
- Runtime Virtual Texture (RVT) : un `RuntimeVirtualTextureVolume` couvrant la zone, une RVT (Base Color/Normal/Roughness/Specular), nœud `Runtime Virtual Texture Output` dans le matériau Landscape ; les objets (routes, rochers) échantillonnent la RVT pour fusionner avec le sol. Exige le Virtual Texture support du projet [V] ; coût mémoire/pool à surveiller.

---
## 3. World Partition
Doc : https://dev.epicgames.com/documentation/en-us/unreal-engine/world-partition-in-unreal-engine ; HLOD/Data Layers † https://dev.epicgames.com/documentation/en-us/unreal-engine/world-partition---hierarchical-level-of-detail-in-unreal-engine

| Élément | Valeur / règle |
|---|---|
| Grille d'exécution (World Settings > World Partition Setup > Runtime Grids) | Hash 2D par défaut. Valeurs usuelles : cellule 12800 uu (128 m, gabarit Open World), exemple doc 256 m ; distance de chargement 25600 uu (gabarit) ou 768 m (exemple doc) **[V]** |
| Réglage conseillé (véhicule rapide) | Cellule 25600 (256 m) ; chargement >= 1000-1500 m pour géométrie proche (55 m/s à 200 km/h : 20 s de marge) ; au-delà, HLOD. Une seule grille (plusieurs = coût, avertissement doc) |
| Landscape | Proxys alignés sur la grille ; une taille de proxy ~ cellule |
| Is Spatially Loaded | Décoché = acteur toujours chargé (ciel, soleil, Sky Atmosphere, post-process, GameMode helpers, volumes globaux). Acteurs référencés par le Level Blueprint = toujours chargés |
| Data Layers | Calques éditeur/runtime ; acteurs d'un calque désactivé non chargés. Usage : variantes (saison, version du circuit), masquer les acteurs de l'ancien monde |
| One File Per Actor | Un `.uasset` par acteur : fusions et contrôle de source propres, mais **des dizaines de milliers de fichiers** : commit/lecture lents, ne pas semer des acteurs unitaires (voir §11) |
| HLOD | Assets `HLODLayer` (types instancing / merged / simplified / approximated ; choix **[V]**) ; build : Build > Build HLODs ou commandlet WorldPartition HLODs Builder (`-run=WorldPartitionBuilderCommandlet -Builder=WorldPartitionHLODsBuilder`, drapeaux **[V]**). Rebâtir après chaque changement de contenu |
| Source de streaming | Contrôleur du joueur par défaut ; pour caméra de replay/photo, ajouter un composant `WorldPartitionStreamingSource` |
| Conversion d'une carte | Commandlet `WorldPartitionConvertCommandlet` **[V]** ; préférer créer la carte depuis le gabarit Open World (`/Engine/Maps/Templates/OpenWorld`) |

Mod qui remplace une partie d'un monde existant (dépend du jeu hôte **[V]**) :
- Ne jamais modifier le niveau persistant du jeu : fournir **sa propre carte** (ou un sous-niveau/Level Instance) avec son WP, et neutraliser l'ancien contenu par Data Layer ou par désactivation de la carte d'origine.
- Raccord : mêmes origine, orientation, ScaleZ, taille de composant et grille que le monde hôte ; sinon couture visible. Prévoir 50-100 m de recouvrement avec fondu (patch/HLOD).
- Reprendre **les assets de matériaux physiques du jeu** (les `SurfaceType` sont définis par projet ; en créer d'autres casse l'adhérence). Reprendre ses classes de sol/route/volumes de météo.
- Ne pas livrer un second Sky/Sun/ExponentialHeightFog si le jeu en spawne un (§7). Même version de moteur et mêmes réglages de cuisson que l'hôte (IoStore/pak, chunk id).

---
## 4. Géométrie importée
Doc : https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-assets-using-interchange-in-unreal-engine ; https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-gltf-files-into-unreal-engine ; https://dev.epicgames.com/documentation/unreal-engine/nanite-virtualized-geometry-in-unreal-engine

| Format | Notes |
|---|---|
| glTF/GLB | Import via Interchange (la doc glTF et la doc Interchange décrivent .gltf/.glb ; quel importeur est le défaut selon 5.4/5.5/5.6/5.7 : **[V]**, non confirmé). Pas de collision ni d'UCX. Matériaux PBR de base ; unités en mètres (échelle d'import x100 ou conversion préalable, **vérifier la taille obtenue**) |
| FBX | Référence pour collisions UCX, LOD, sockets. Via Interchange : « expérimental » derrière `Interchange.FeatureFlags.Import.FBX` dans la doc consultée **[V]** ; l'importeur FBX legacy reste utilisable. Unités cm, Z haut |
| USD | Plugin USD (Stage Actor) ou Interchange ; pratique pour scènes entières issues de Houdini/Blender |
| Datasmith | Pour CAO/Revit, hors sujet pour du terrain |

Conventions d'export (Blender/Houdini) : Z haut, échelle appliquée, +X avant, un matériau par type de surface, noms stables (`SM_<zone>_<lot>_<index>`).

**Nanite** :
| Cas | Décision |
|---|---|
| Opaque statique dense (bâtiments, rochers, falaises, routes) | Oui |
| Masqué (feuilles, grillages) | Possible mais coûteux en overdraw ; régressions signalées sur dithering/WPO entre 5.4 et 5.6 (UE-307863) [Q][V] ; trunks/branches Nanite + cartes de feuilles masquées classiques reste le schéma sûr |
| Translucide, matériaux additifs/vitres | Non (rendu non-Nanite) |
| Petits objets (< ~20 cm, props bas poly) | Peu d'intérêt ; instancier en non-Nanite ou Nanite selon le nombre |
| Feuillage Nanite (Assemblies/Skinning/Voxels) | **Expérimental en 5.7** ; Assemblies introduits avant (5.6, **[V]**) ; ne pas bâtir le pipeline principal dessus |
| Tessellation/displacement Nanite sur Landscape | Instable : bug UE-367789 (direction de déplacement faussée avec ScaleZ non uniforme, toujours signalé en 5.7+) [Q] ; éviter sur un terrain à gros ScaleZ |
| Skeletal Nanite | Expérimental depuis 5.5 **[V]**, inutile ici |

**Collision** (cruciale pour une course) :
| Besoin | Réglage |
|---|---|
| Route avec adhérence par surface | Mesh route, **un slot de matériau par surface**, chaque matériau avec son `PhysicalMaterial`, collision « Use Complex Collision As Simple » (la physique lit alors le matériau du triangle) |
| Décor solide (rocher, mur) | Collision simple (UCX ou auto-convex), jamais complexe sur gros maillages (coût Chaos) |
| Landscape | Collision heightfield auto ; matériau physique pris sur le **Layer Info** de chaque couche |
| Mesh Nanite en collision complexe | La collision complexe repose sur le maillage de repli (fallback) : sur route cm-précise, régler/forcer un fallback fidèle ou fournir une collision dédiée **[V]** |

```python
import unreal
sm = unreal.EditorAssetLibrary.load_asset("/Game/Zone/Roads/SM_Route_01")
bs = sm.get_editor_property("body_setup")
bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
# matériau physique : à poser sur chaque MaterialInstance (propriété phys_material), pas sur le mesh
mi = unreal.EditorAssetLibrary.load_asset("/Game/Zone/Mat/MI_Gravier")
mi.set_editor_property("phys_material", unreal.EditorAssetLibrary.load_asset("/Game/Phys/PM_Gravier"))
unreal.EditorAssetLibrary.save_loaded_asset(mi)
```
(`unreal.EditorStaticMeshLibrary` : `set_convex_decomp_collisions`, `add_simple_collisions`, `set_lods`, `enable_section_collision`.)

**LOD** : auto-générés ou manuels ; non-Nanite : 3-4 LOD, écran 1 / 0,5 / 0,2 / 0,05. **Lightmap UV** : inutile avec Lumen (décocher `Generate Lightmap UVs` à l'import) ; seulement pour éclairage statique baké (mobile, VR).

---
## 5. Végétation et dispersion
Doc : https://dev.epicgames.com/documentation/en-us/unreal-engine/procedural-content-generation-overview ; https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-7-release-notes

| Outil | État | Note |
|---|---|---|
| Foliage Tool / `InstancedFoliageActor` (HISM) | Stable | Manuel/peinture ; peu scriptable proprement |
| HISM/ISM dans un acteur script | Stable | Choix par défaut pour placement exact en lot |
| Landscape Grass Types | Stable | Herbe procédurale de proximité, sans stockage |
| PCG Framework | Expérimental (5.2-5.4), progression en 5.5/5.6 [V], **« production-ready » en 5.7** (presse + Epic) [Q] | Graphes, GPU compute (plus rapide en 5.7), exécution en éditeur ou runtime |
| PCG Biome Core / Procedural Vegetation Editor | PVE expérimental en 5.7 [Q] ; Biome Core : état [V] | Utile pour du biome « artistique », pas pour du placement mesuré |
| Nanite Foliage + PCG | Expérimental 5.7 | Voir §4 |

**Placement d'arbres individuels réels (LiDAR)** : CHM (modèle de hauteur de canopée = MNS - MNT, PDAL/lidR/rasterio), maxima locaux (fenêtre 2-4 m), export `x,y,z_sol,hauteur,rayon_couronne,essence` en CSV. Le script place un instance par arbre : échelle = `hauteur / hauteur_mesh`, yaw aléatoire à graine fixe, mesh choisi par essence, Z lu sur le MNT (déterministe) ou par line trace (suit la collision réelle).

```python
import unreal, csv, random
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
host = eas.spawn_actor_from_class(unreal.Actor, unreal.Vector(0,0,0))
host.set_actor_label("ARBRES_LIDAR_tuile_03")
comp = host.add_component_by_class(unreal.HierarchicalInstancedStaticMeshComponent, False,
                                   unreal.Transform(), False)
comp.set_static_mesh(unreal.EditorAssetLibrary.load_asset("/Game/Veg/SM_Chene"))
random.seed(42); H0 = 1500.0                       # hauteur du mesh en cm
tfs = []
for r in csv.DictReader(open("arbres_03.csv")):
    p = enu_to_ue(float(r["e"]), float(r["n"]), float(r["z"]), ORIGIN)
    s = float(r["h"])*100/H0
    tfs.append(unreal.Transform(p, unreal.Rotator(0, 0, random.uniform(0, 360)), unreal.Vector(s, s, s)))
comp.add_instances(tfs, should_return_indices=False)   # API exposée à Python : [V] selon version
comp.set_editor_property("cull_distances", unreal.Int32Interval(0, 150000))  # fin de culling 1,5 km
```
(Ne pas oublier `unreal.Rotator(roll, pitch, yaw)` : l'ordre Python est roll, pitch, yaw.) Découper **par tuile spatiale** (un acteur HISM par cellule WP, ~10-50 k instances max) pour que le streaming et le culling fonctionnent ; un seul HISM géant n'est pas « spatialement chargeable ».

PCG piloté par des données : graphe `Get Landscape Data / Surface Sampler` pour le fond ; pour les points réels : charger la table (Data Table/CSV : nœuds du type `Load Data Table`/`Data Table To Attribute Set`, puis `Create Points From Attribute Set`, **noms [V]**), `Transform Points`, `Static Mesh Spawner` (ou `Spawn Static Mesh`). Lancer depuis Python : `PCGComponent.generate(...)` / `generate_local` **[V]**. Garder une graine fixe et sauvegarder les sorties pour la reproductibilité.

Densités réalistes (indicatif) : forêt tempérée mûre 200-600 arbres/ha (plantation résineuse jusqu'à 1000+) ; buissons 500-2000/ha ; herbe/touffes 20-80 /m² en proche (< 30 m), rien au-delà. Distances de fin de culling : herbe 25-50 m, buissons 80-150 m, arbres 1-2 km avec LOD/impostor, rochers 500 m-1 km.

---
## 6. Matériaux de terrain
Doc † https://dev.epicgames.com/documentation/en-us/unreal-engine/landscape-materials-in-unreal-engine ; † https://dev.epicgames.com/documentation/en-us/unreal-engine/virtual-texturing-in-unreal-engine

| Technique | Réglage / règle |
|---|---|
| Couches | `Landscape Layer Blend` (LB_WeightBlend, LB_HeightBlend) ; 4-8 couches par matériau (limite de samplers : bornée par pente/altitude ou RVT) |
| Mélange par hauteur | `LB_HeightBlend` avec le canal hauteur des textures (ou masque noise) : bords de mélange nets, pas de fondu pâteux |
| Par pente/altitude | Pente = `1 - dot(normale_monde, Z)` ; roche au-delà de 35-45°, neige/végétation par altitude, en complément des weightmaps |
| Macro-variation | Noise basse fréquence (100-500 m) multipliant l'albédo (±10-20 %), 2 échelles ; casse la répétition vue de loin |
| Anti-tiling | Texture à 2-4 m physiques, double échantillonnage à échelles non multiples (x1 et x0,37), rotation/hex-tiling, « distance blend » vers une version basse fréquence |
| Ortho comme teinte lointaine | **Oui** : échantillon basse fréquence, mélangé à 20-50 % de l'albédo procédural, fondu avec la distance (> 30-50 m). **Non en proche** : ombres, perspective et reflets déjà cuits, résolution 10-50 cm/px floue, pas de normal/roughness |
| Résolution ortho | 0,2-0,5 m/px source ; stocker à 2-4 m/px pour la teinte (Virtual Texture) |
| Décalques | DBuffer/Deferred decals : marquages, traces de pneus, boue, rapiéçage, usure sur routes ; ou mesh route avec matériau en couches. Décalques sur Nanite : OK ; garder < ~ quelques centaines visibles |
| Virtual Texturing | Streaming VT pour grosses textures (ortho, masques) ; RVT pour fusion route/terrain ; vérifier que le projet l'active et la taille du pool (`r.VT.PoolSizeScale`, `r.Streaming.PoolSize`) |

---
## 7. Lumière et ciel fidèles au lieu
Doc : https://dev.epicgames.com/documentation/en-us/unreal-engine/geographically-accurate-sun-positioning-tool-in-unreal-engine ; https://dev.epicgames.com/documentation/en-us/unreal-engine/sun-and-sky-actor-in-unreal-engine ; Python : https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/SunPositionFunctionLibrary

- Plugin **Sun Position Calculator** (activer) : acteur `SunSky`. Champs : Latitude (positive nord), Longitude en **degrés** est/négatif ouest (l'ancienne doc 4.26 disait « heures » : ne pas s'y fier), Time Zone, Daylight Saving, Date, Heure, **North Offset**, option de calcul de la hauteur de soleil. Ne pas pivoter l'acteur : seul `North Offset` oriente le nord (doc). Par défaut le nord = +X (§1 pour l'ajustement).
- Calcul en Python : `unreal.SunPositionFunctionLibrary.get_sun_position(lat, lon, tz, dst, year, month, day, h, m, s)` renvoie azimut/élévation (signature **[V]**) ; utile pour contrôle automatique (le soleil du niveau doit coïncider).
- Heure et date : lire les ombres dans l'ortho (photos aériennes IGN : prise de vue ~ mi-journée, été) pour choisir un éclairage cohérent avec la teinte.
- **Sky Atmosphere** : rayon sol 6360 km ; pour altitude réelle, régler la transformation du « sol » du ciel à l'altitude du lieu (`Transform Mode`) ; **Volumetric Clouds** + Sky Light en capture temps réel ; **Exponential Height Fog** avec brume volumétrique.
- **Lumen** (GI/reflets logiciels par défaut ; matériel optionnel) : réglage projet ; éviter UV lightmap ; Virtual Shadow Maps pour Nanite. MegaLights **expérimental 5.7** [Q].
- **Exposition** : manuelle pour contrôle fidèle : ciel dégagé EV100 ~ 14,5-15 avec soleil physique ~ 100 000-120 000 lux ; sous-bois ~ 10-12 ; sinon exposition auto avec bornes serrées. Les valeurs par défaut d'une `DirectionalLight` (10 lux) supposent l'auto-exposition.
- **Hôte** : si le jeu a son cycle jour/nuit/météo, **ne pas remplacer**. Piloter ses paramètres (heure, météo) ou ajouter uniquement la donnée du lieu (latitude, longitude, North Offset, date) à son système ; un second soleil casse la cohérence.

---
## 8. Lointain
Doc †: https://dev.epicgames.com/documentation/en-us/unreal-engine/landscape-outdoor-terrain-in-unreal-engine ; HLOD (§3)

| Technique | Détail |
|---|---|
| Relief lointain | Deuxième Landscape (ou maillage) très basse résolution : MNT à 10-30 m/px (ex. Copernicus GLO-30 / IGN 25 m), 1009 ou 2017 sommets, couvrant 20-60 km ; abaissé de 2-10 m ou troué sous la zone jouable (couche Visibility) pour éviter le z-fighting |
| Raccord | Recouvrement avec fondu d'altitude ; la zone jouable vient du MNT fin |
| Textures | Ortho 2-8 m/px (VT) ou teinte procédurale + masque de couverture du sol |
| HLOD | Build des HLOD pour bâtiments/arbres au-delà de ~1-2 km (types merged/instancing **[V]**) |
| Impostors | Arbres lointains : impostor/billboard ou Nanite Voxels (expérimental) ; forêts denses : un mesh « canopée » simplifié |
| Brume / atmosphère | Perspective aérienne par Sky Atmosphere + fog : masque la rupture de résolution |
| Silhouettes | Montagnes réelles identifiables : vérifier avec une vue panoramique de référence |

---
## 9. Automatisation
Doc : https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python ; https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/SunPositionFunctionLibrary (index API)

| Besoin | API (5.4-5.7) |
|---|---|
| Assets | `unreal.EditorAssetLibrary` (`load_asset`, `save_loaded_asset`, `does_asset_exist`, `make_directory`) |
| Acteurs | `unreal.get_editor_subsystem(unreal.EditorActorSubsystem)` : `spawn_actor_from_class`, `get_all_level_actors`, `destroy_actor`. `EditorLevelLibrary` (acteurs) est **déprécié** au profit des sous-systèmes |
| Niveaux | `unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)` : `new_level`, `new_level_from_template` **[V]**, `load_level`, `save_current_level` |
| Import | `unreal.AssetImportTask` + `unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([...])` ; ou `unreal.InterchangeManager.get_interchange_manager()` (exemples officiels sur la page Interchange) |
| Sélection / contrôle | `EditorActorSubsystem.get_selected_level_actors`, `set_actor_selection_state` |

```python
import unreal, json
def import_fbx(src, dest):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", src); t.set_editor_property("destination_path", dest)
    t.set_editor_property("automated", True); t.set_editor_property("save", True)
    t.set_editor_property("replace_existing", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return t.get_editor_property("imported_object_paths")

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for o in json.load(open(r"D:/data/objets.json")):          # [{mesh,e,n,alt,cap,echelle}, ...]
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, enu_to_ue(o["e"], o["n"], o["alt"], ORIGIN),
                                   unreal.Rotator(0, 0, bearing_to_yaw(o["cap"])))
    a.static_mesh_component.set_static_mesh(unreal.EditorAssetLibrary.load_asset(o["mesh"]))
    a.set_actor_scale3d(unreal.Vector(*(o.get("echelle", 1.0),)*3))
    a.set_actor_label(f"{o['id']}")                         # étiquettes stables = relecture et idempotence
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
```
Pour beaucoup d'objets identiques : HISM (§5), jamais un acteur par objet (§11). Rendre les scripts **idempotents** : détruire/recréer les acteurs d'un dossier (`actor.set_folder_path`) ou d'un tag avant de régénérer.

**Sans interface**
| Mode | Commande | Notes |
|---|---|---|
| Commandlet Python | `UnrealEditor-Cmd.exe "D:/P/P.uproject" -run=pythonscript -script="D:/S/build.py" -unattended -nopause -nosplash -stdout -FullStdOutLogOutput` | Léger, sans UI ; plugin **Python Editor Script Plugin** activé dans le `.uproject` ; certains sous-systèmes (rendu, Interchange asynchrone, compilation de shaders, landscape) peuvent manquer en mode commandlet **[V]** |
| Éditeur piloté | `UnrealEditor-Cmd.exe "D:/P/P.uproject" -ExecutePythonScript="D:/S/build.py arg1" -unattended -stdout` | Doc officielle ; l'éditeur se ferme dès la fin du script (coupe le travail asynchrone) ; arguments dans la même chaîne quotée, `sys.argv` |
| Variante rendu null | ajouter `-nullrhi` | Suffit pour assets/acteurs ; pas de textures/shaders compilés |
| Sorties | `unreal.log`, `unreal.log_warning`, code de sortie : lever une exception pour échouer | Les journaux sont dans `Saved/Logs` |

Fiabilité : plusieurs rapports forum de scripts qui démarrent puis arrêtent sans erreur (5.5) [Q] ; garder des `try/except` avec `unreal.log_error`, tester sur un petit niveau, privilégier des opérations synchrones (`AssetImportTask`).

**Cuisson**
```
UnrealEditor-Cmd.exe "D:/P/P.uproject" -run=cook -targetplatform=Windows -map=/Game/Maps/Zone -iterate -unattended
RunUAT.bat BuildCookRun -project="D:/P/P.uproject" -platform=Win64 -clientconfig=Shipping -cook -stage -pak -archive -archivedirectory=D:/out -map=Zone -unattended -utf8output
```
(+ build HLOD préalable, §3.) Pour un mod : les chemins de pak/chunk et le `-DLCName`/Plugin de contenu dépendent de l'hôte **[V]**.

**Relecture automatique** : après génération, un second script parcourt le niveau et vérifie, puis écrit un rapport JSON : nombre d'acteurs par classe, absence de mesh/matériau manquant, bornes de l'emprise (min/max X, Y, Z des acteurs = emprise du `zone.json` ± tolérance), altitude de N points de contrôle (line trace vs MNT, écart < 1 pas de ScaleZ), acteurs sous le sol ou flottants, couches avec matériau physique assigné, orientation du soleil vs `get_sun_position`, captures (`unreal.AutomationLibrary.take_high_res_screenshot`, **[V]**) depuis des points de vue fixes comparés à la photo aérienne/street view de référence.

---
## 10. Outils géospatiaux
Doc/sites : https://cesium.com/platform/cesium-for-unreal/ † ; https://github.com/CesiumGS/cesium-unreal † ; https://github.com/domlysz/BlenderGIS † ; https://gdal.org †

| Outil | Coût (à confirmer) | Quand | Script maison plutôt si |
|---|---|---|---|
| GDAL / rasterio / pyproj / PDAL | Gratuit, open source | Toujours : reprojection, rééchantillonnage, PNG 16 bits, rasterisation, CHM | — (c'est la base du script maison) |
| GeoReferencing (plugin Epic, intégré) | Gratuit | Conversions lat/long/projeté <-> moteur (PROJ), `GeoReferencingSystem`, origine géographique du niveau ; fonctions BP/Python **[V]** | Un `zone.json` + `enu_to_ue` suffit pour une zone locale |
| Cesium for Unreal | Plugin open source (Apache-2.0) ; Cesium ion a un palier gratuit, payant au-delà **[V]** | 3D Tiles, globe, géoréférencement, **référence visuelle** | Le niveau jouable ne doit pas dépendre du streaming Cesium |
| Google Photorealistic 3D Tiles (via Cesium ion ou clé Google) | Facturé à l'usage, quota gratuit **[V]** | Seulement comme **référence visuelle** pendant la construction | Interdit en pratique pour la cuisson : les conditions Google interdisent mise en cache/stockage/hors-ligne et la création de contenu dérivé, attribution obligatoire [Q] ; vérifier les conditions en vigueur |
| UnrealGDAL (plugin GDAL, open source) | Gratuit | Lire GeoTIFF/shapefile dans l'éditeur | Préférer GDAL en Python hors éditeur (plus stable) |
| Landscaping (Fab), TerraForm Pro (Fab) | Payants (prix à vérifier) | Import MNT/OSM clé en main en éditeur | Pas pilotables en ligne de commande, version/maintenance incertaines [V] : script maison |
| Blender + BlenderGIS (gratuit) / Blosm (freemium) | Gratuit / payant | Extrusion de bâtiments OSM, nettoyage, export GLB/FBX, routes en maillage | Gros volumes : script Python headless `blender -b -P` |
| Houdini (+ Houdini Engine) | Apprentice gratuit non commercial ; Indie/FX payants | Terrain, routes procédurales, érosion, PCG avancé | Quand la logique est simple : numpy |
| Gaea / World Machine | Éditions gratuites limitées, versions payantes **[V]** | Érosion, terrains fictifs ou compléter un MNT trop lisse | Pour un lieu réel, ne pas éroder le MNT mesuré ; ajouter du détail microrelief seulement |

Sources de données : MNT IGN RGE ALTI / LiDAR HD, Copernicus GLO-30, SRTM, BD TOPO/OSM (Overpass), CORINE/OCS GE, ortho IGN/Sentinel. **Vérifier la licence** (ODbL, Etalab) et l'attribution.

---
## 11. Performance
Doc † https://dev.epicgames.com/documentation/en-us/unreal-engine/optimizing-unreal-engine-projects (budgets indicatifs, PC milieu de gamme 60 FPS ; à étalonner sur la machine cible)

| Budget | Valeur indicative |
|---|---|
| Triangles non-Nanite à l'écran | 2-5 M |
| Nanite | quelques dizaines de millions de triangles source visibles OK ; surveiller overdraw (masqué) |
| Draw calls | 2-5 k (non-Nanite) ; fusionner matériaux, instancier |
| Instances HISM | 100 k - 1 M visibles avec culling par tuile |
| Acteurs au chargement | < 100-200 k au total par monde WP, quelques milliers chargés |
| Mémoire textures | pool de streaming 2-4 GB (`r.Streaming.PoolSize`) ; plafond VRAM du public visé |
| Couches Landscape | 4-8 par matériau ; weightmaps 1 px/quad |
| Textures | Couches de sol 1K-2K tuilées (BC/DXT) ; terrain/ortho en VT ; **8K : seulement VT ou hero**. Puissances de 2, mips activés, sRGB correct, masques ORM groupés |
| Lumières dynamiques | quelques dizaines ; VSM coûteuses : limiter lumières mobiles |

**Ce qui fait chuter les FPS dans un niveau issu de données réelles** :
1. Milliers d'acteurs uniques (bâtiments, arbres, poteaux) au lieu d'instances / meshes fusionnés (cause n°1, aussi lenteur de chargement OFPA).
2. Textures 4K-8K uniques par bâtiment ou par tuile en non-VT.
3. Collisions complexes sur de gros maillages et sur la végétation.
4. Feuillage masqué non-Nanite dense sans culling (overdraw), herbe sans distance de fin.
5. Matériaux Landscape à beaucoup de couches ou de samplers ; décalques en excès ; translucide à grande échelle.
6. Distance de chargement WP trop grande, cellules trop petites (hitch), pas de HLOD.
7. Trop de Landscape Edit Layers/Patches non nettoyés en développement ; RVT trop grande.
Outils : `stat unit`, `stat gpu`, `stat scenerendering`, `r.Nanite.Visualize`, `ProfileGPU`, Unreal Insights ; `wp.Runtime.ToggleDrawRuntimeHash2D`.

---
## 12. Liste de contrôle avant cuisson
- [ ] `zone.json` : origine, unités, ScaleZ, taille de tuile ; **repère** vérifié sur 3 points de contrôle (coin, centre, point remarquable) ; nord et soleil cohérents
- [ ] Heightmap : taille valide (§2.1), 16 bits, ScaleZ = plage x 100 / 512, Z de l'acteur vérifié
- [ ] Layer Infos avec matériaux physiques (ceux de l'hôte) ; noms de couches = noms du matériau
- [ ] Routes : collision complexe + un matériau physique par slot ; pas de trous ni de z-fighting
- [ ] Collisions des décors simples ; pas de complexe inutile
- [ ] Végétation en HISM par tuile ; distances de culling ; graines fixes
- [ ] Aucun acteur unique répété (> ~20 copies d'un même mesh = instancier)
- [ ] Textures : tailles, VT activés, pool dimensionné
- [ ] World Partition : une grille, cellule/chargement choisis, acteurs globaux non spatiaux, Data Layers corrects
- [ ] HLOD construits après le dernier changement
- [ ] Ciel/soleil : pas de doublon avec l'hôte ; exposition fixée
- [ ] Zéro référence manquante, zéro avertissement bloquant (`Map Check`)
- [ ] Relecture automatique OK (§9) ; captures comparées à la référence
- [ ] Cuisson d'essai (`-run=cook` ou BuildCookRun) puis test packagé : chargement, adhérence par surface, mémoire, FPS sur matériel cible
- [ ] Licences des données et attributions consignées
