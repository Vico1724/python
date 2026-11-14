# Appels Unreal à vérifier sur le PC

*11 novembre 2026. Pour la session Claude ouverte sur le PC du directeur.*

`scripts_editeur/construire_niveau.py` n'a **jamais été exécuté dans Unreal**. Il a été écrit d'après l'API Python de l'éditeur Unreal 5, que je connais sans l'avoir vérifiée sur la version 5.6.1. Sa logique (lecture du manifeste, choix des éléments, comptes, ordre des opérations) a été vérifiée hors d'Unreal avec un faux module `unreal` (`outils/essai_construire.py`). Cet essai ne prouve rien sur les appels eux-mêmes.

Chaque appel incertain est isolé dans une fonction courte dont le nom commence par `v_`, en tête du script. Si un appel est refusé, il suffit de corriger cette fonction.

**Où chercher.** La référence Python de l'éditeur est en ligne : `dev.epicgames.com/documentation/en-us/unreal-engine/python-api/` (choisir la version 5.6). Dans l'éditeur, on peut aussi taper dans la console Python `help(unreal.<Classe>)` ou `dir(unreal.<Classe>)`.

| Fonction | Appel incertain | Ce qu'il faut regarder |
|---|---|---|
| `v_importer_fichier` | `AssetImportTask` avec `destination_name`, puis `import_asset_tasks`, pour un `.glb` | Avec Interchange (le défaut en 5.6), vérifier que `imported_object_paths` est bien rempli. Sinon, le script se rabat sur la liste du dossier tampon. Vérifier aussi que `destination_name` est respecté : le script ne s'y fie pas, il renomme le StaticMesh trouvé. Page « Interchange Import Pipeline » et classe `AssetImportTask`. |
| `v_importer_fichier` (glb) | Options d'import par défaut | L'importeur peut créer un matériau par section, que le script supprime. Il pourrait aussi réorienter ou mettre à l'échelle le maillage. La mire (`--mire`) le détecte. Si les options par défaut gênent, utiliser `unreal.InterchangeManager` avec une copie de `/Interchange/Pipelines/DefaultAssetsPipeline` : import des matériaux désactivé, collision désactivée, « Combine Static Meshes » activé. |
| `v_regler_texture` | Noms des propriétés `srgb`, `compression_settings`, `lod_group`, `address_x`, `address_y`, `virtual_texture_streaming`, `flip_green_channel` | Classe `Texture2D` / `Texture`. Valeurs d'énumération `TextureCompressionSettings.TC_NORMALMAP` et `TC_DEFAULT`, `TextureGroup.TEXTUREGROUP_WORLD` et `TEXTUREGROUP_WORLD_NORMAL_MAP`. Le manifeste écrit les noms C++ (`TC_Normalmap`, `TEXTUREGROUP_WorldNormalMap`). `nom_enum_python` les convertit en noms Python (`TC_NORMALMAP`, `TEXTUREGROUP_WORLD_NORMAL_MAP`). Si `getattr` échoue, lister les valeurs avec `dir(unreal.TextureGroup)`. |
| `v_regler_maillage` | `StaticMeshEditorSubsystem.remove_collisions` ; `nanite_settings.enabled` | Classe `StaticMeshEditorSubsystem` (anciennement `EditorStaticMeshLibrary`) ; structure `MeshNaniteSettings`. |
| `v_bornes_maillage` | `StaticMesh.get_bounding_box()` | Vérifier qu'elle renvoie des bornes **locales**, en cm. Sinon, utiliser `get_bounds()`. |
| `v_nom_section` | `static_materials[0].material_slot_name` | Structure `StaticMaterial`. |
| `v_creer_variante`, `v_parametre_texture` | `MaterialInstanceConstantFactoryNew`, `MaterialEditingLibrary.set_material_instance_parent`, `set_material_instance_texture_parameter_value` | Classe `MaterialEditingLibrary`. Le nom de paramètre doit exister dans le parent, sinon l'appel est sans effet : vérifier dans la variante ouverte. |
| `v_creer_materiau_secours` | `create_material_expression`, `connect_material_property` avec les sorties `"RGB"`, `"R"`, `"G"`, `"B"` ; `sampler_type` | Classe `MaterialEditingLibrary` ; énumérations `MaterialProperty` (`MP_BASE_COLOR`, `MP_NORMAL`, `MP_ROUGHNESS`, `MP_METALLIC`, `MP_AMBIENT_OCCLUSION`) et `MaterialSamplerType`. Ce matériau sert à voir le décor dans l'éditeur. **Il ne doit pas être livré.** |
| `v_ouvrir_ou_creer_niveau` | `LevelEditorSubsystem.new_level(chemin)` et `load_level` | Vérifier que `new_level` crée un niveau **sans World Partition**. Sinon, créer `GrandCaunet_E3` à la main (Fichier > Nouveau niveau > « Empty Level »), puis relancer : le script ouvre un niveau existant. |
| `v_poser_maillage` | `EditorActorSubsystem.spawn_actor_from_object`, `set_folder_path`, propriétés `static_mesh_component`, `mobility`, `cast_shadow` | Classe `EditorActorSubsystem` ; `StaticMeshActor`. |
| `v_composant_instances` | Ajout d'un `HierarchicalInstancedStaticMeshComponent` à un acteur vide par `SubobjectDataSubsystem` | **L'appel le plus incertain.** Classe `SubobjectDataSubsystem` (`k2_gather_subobject_data_for_instance`, `add_new_subobject`, `rename_subobject`). S'il est refusé, deux replis : (1) un Blueprint d'acteur `BP_GC_Instances` portant le composant, créé une fois à la main puis posé par `spawn_actor_from_class` ; (2) l'outil Foliage de l'éditeur. |
| `v_ajouter_instances` | `add_instances(transforms, should_return_indices, world_space)` | Classe `InstancedStaticMeshComponent`. Si la signature diffère, ajouter les instances une à une avec `add_instance(transform)` (plus lent). |
| `v_transfo` | `Transform(location=..., rotation=Rotator(roll, pitch, yaw), scale=...)` | Vérifier l'ordre des arguments de `Rotator` en Python : le script les nomme pour l'éviter. |
| `v_dossier_saved` | `Paths.project_saved_dir()` | Classe `Paths`. |
| fin du script | `main()` lancé quand le fichier est exécuté par `py fichier.py` | Si rien ne se passe, ajouter un appel `main()` en dernière ligne. |

**Ce qui n'est pas incertain** (vérifié ici) :
- la forme du manifeste et sa cohérence : chaque variante pointe vers des textures présentes, chaque maillage vers une variante présente ;
- les fichiers : glb relisibles, images aux dimensions annoncées en puissances de 2, reliefs de norme 1 ;
- les comptes : 590 maillages, 619 textures, 457 variantes et 164 186 instances pour le paquet complet ; 31 maillages et 8 304 instances pour l'échantillon E4.

**Ordre conseillé sur le PC :**
1. `--etendue E3 --mire` : vérifie les axes de l'importeur et pose une dalle. Lire le rapport dans `<projet>\Saved\GrandCaunet\`.
2. Corriger les fonctions `v_` qui échouent.
3. Lancer E4, puis `complet`.
