"""Faux module « unreal », minimal, pour faire tourner HORS D'UNREAL la logique de construire_niveau.py
(parcours du manifeste, imports, variantes, pose des acteurs et des instances). Il ne simule que ce que ce script
appelle, et reproduit l'importeur glb sous l'hypothèse « UE = 100 * (gX, gZ, gY) » (variable d'environnement
GC_FAUX_AXES pour en essayer une autre). Il ne prouve RIEN sur l'API réelle : voir A_VERIFIER.md.
"""
import json
import os
import struct

JOURNAL = []
ASSETS = {}            # chemin -> objet
DOSSIERS = set()
ACTEURS = []


def _j(niveau, msg):
    JOURNAL.append((niveau, msg))
    print(f"[{niveau}] {msg}")


def log(msg):
    _j("info", msg)


def log_warning(msg):
    _j("alerte", msg)


def log_error(msg):
    _j("erreur", msg)


class _Enum:
    def __init__(self, nom):
        self._nom = nom

    def __getattr__(self, k):
        if k.startswith("_"):
            raise AttributeError(k)
        return f"{self._nom}.{k}"


TextureCompressionSettings = _Enum("TextureCompressionSettings")
TextureGroup = _Enum("TextureGroup")
TextureAddress = _Enum("TextureAddress")
CollisionEnabled = _Enum("CollisionEnabled")
ComponentMobility = _Enum("ComponentMobility")
MaterialProperty = _Enum("MaterialProperty")
MaterialSamplerType = _Enum("MaterialSamplerType")


class _Classe:
    def __init__(self, nom):
        self._nom = nom

    def get_name(self):
        return self._nom


class _Objet:
    _classe = "Object"

    def __init__(self, chemin=None):
        self.props = {}
        self.chemin = chemin

    def set_editor_property(self, k, v):
        self.props[k] = v

    def get_editor_property(self, k):
        return self.props.get(k)

    def get_class(self):
        return _Classe(self._classe)

    def get_name(self):
        return self.chemin.rsplit("/", 1)[1] if self.chemin else self._classe


class Vector:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = float(x), float(y), float(z)


class Rotator:
    def __init__(self, roll=0.0, pitch=0.0, yaw=0.0):
        self.roll, self.pitch, self.yaw = roll, pitch, yaw


class Transform:
    def __init__(self, location=None, rotation=None, scale=None):
        self.location, self.rotation, self.scale = location, rotation, scale


class Text(str):
    def is_empty(self):
        return len(self) == 0


class _Boite:
    def __init__(self, lo, hi):
        self.min, self.max = Vector(*lo), Vector(*hi)


class _Slot(_Objet):
    pass


class StaticMesh(_Objet):
    _classe = "StaticMesh"

    def __init__(self, chemin, lo, hi, section):
        super().__init__(chemin)
        self.lo, self.hi = lo, hi
        s = _Slot()
        s.set_editor_property("material_slot_name", section)
        self.props["static_materials"] = [s]
        n = _Objet()
        self.props["nanite_settings"] = n
        self.materiaux = {}

    def get_bounding_box(self):
        return _Boite(self.lo, self.hi)

    def set_material(self, i, m):
        self.materiaux[i] = m


class Texture2D(_Objet):
    _classe = "Texture2D"


class Material(_Objet):
    _classe = "Material"


class MaterialInstanceConstant(_Objet):
    _classe = "MaterialInstanceConstant"


class MaterialInstanceConstantFactoryNew(_Objet):
    pass


class MaterialFactoryNew(_Objet):
    pass


class MaterialExpressionTextureSampleParameter2D(_Objet):
    pass


def _axes():
    t = os.environ.get("GC_FAUX_AXES", "X,Z,Y").split(",")
    return [("XYZ".index(c.lstrip("-")), -1.0 if c.startswith("-") else 1.0) for c in t]


def _importer_glb(fichier, chemin):
    b = open(fichier, "rb").read()
    n = struct.unpack_from("<I", b, 12)[0]
    g = json.loads(b[20:20 + n])
    a = g["accessors"][g["meshes"][0]["primitives"][0]["attributes"]["POSITION"]]
    lo, hi = [], []
    for k, s in _axes():
        v = (a["min"][k] * 100 * s, a["max"][k] * 100 * s)
        lo.append(min(v))
        hi.append(max(v))
    return StaticMesh(chemin, lo, hi, g["materials"][0]["name"])


class AssetImportTask(_Objet):
    pass


class _OutilsAssets:
    def import_asset_tasks(self, taches):
        for t in taches:
            f = t.get_editor_property("filename")
            if not os.path.exists(f):
                raise FileNotFoundError(f)
            d, nom = t.get_editor_property("destination_path"), t.get_editor_property("destination_name")
            chemin = f"{d}/{nom}"
            if f.endswith(".glb"):
                ASSETS[chemin] = _importer_glb(f, chemin)
                mat = f"{d}/MI_importe_parasite"             # l'importeur crée un matériau : le script doit le supprimer
                ASSETS[mat] = MaterialInstanceConstant(mat)
                t.set_editor_property("imported_object_paths", [chemin, mat])
            else:
                ASSETS[chemin] = Texture2D(chemin)
                t.set_editor_property("imported_object_paths", [chemin])

    def create_asset(self, nom, dossier, classe, fabrique):
        chemin = f"{dossier}/{nom}"
        ASSETS[chemin] = (classe or _Objet)(chemin)
        return ASSETS[chemin]


class AssetToolsHelpers:
    @staticmethod
    def get_asset_tools():
        return _OutilsAssets()


class EditorAssetLibrary:
    @staticmethod
    def does_asset_exist(c):
        return c in ASSETS

    @staticmethod
    def does_directory_exist(c):
        return c in DOSSIERS

    @staticmethod
    def make_directory(c):
        DOSSIERS.add(c)

    @staticmethod
    def delete_directory(c):
        DOSSIERS.discard(c)

    @staticmethod
    def load_asset(c):
        return ASSETS.get(c)

    @staticmethod
    def save_asset(c, only_if_is_dirty=True):
        if c not in ASSETS:
            raise KeyError(f"save_asset : {c} absent")

    @staticmethod
    def save_directory(c, only_if_is_dirty=True, recursive=True):
        pass

    @staticmethod
    def delete_asset(c):
        ASSETS.pop(c, None)

    @staticmethod
    def list_assets(d, recursive=True, include_folder=False):
        return [c for c in ASSETS if c.startswith(d + "/")]

    @staticmethod
    def rename_asset(a, b):
        o = ASSETS.pop(a)
        o.chemin = b
        ASSETS[b] = o


class MaterialEditingLibrary:
    @staticmethod
    def set_material_instance_parent(mi, p):
        if p is None:
            raise ValueError("parent None")
        mi.parent = p

    @staticmethod
    def set_material_instance_texture_parameter_value(mi, nom, tex):
        mi.props.setdefault("textures", {})[nom] = tex

    @staticmethod
    def create_material_expression(m, cls, x, y):
        return cls()

    @staticmethod
    def connect_material_property(e, sortie, prop):
        pass

    @staticmethod
    def recompile_material(m):
        pass


class _Composant(_Objet):
    def set_collision_enabled(self, v):
        self.props["collision"] = v

    def set_static_mesh(self, m):
        self.props["mesh"] = m

    def add_instances(self, t, retour, monde):
        self.props.setdefault("instances", []).extend(t)


class Actor(_Objet):
    _classe = "Actor"

    def __init__(self, chemin=None):
        super().__init__(chemin)
        self.props["static_mesh_component"] = _Composant()
        self.label = ""

    def set_actor_label(self, s):
        self.label = s

    def get_actor_label(self):
        return self.label

    def set_folder_path(self, p):
        self.dossier = p


class DirectionalLight(Actor):
    pass


class SkyLight(Actor):
    pass


class SkyAtmosphere(Actor):
    pass


class ExponentialHeightFog(Actor):
    pass


class HierarchicalInstancedStaticMeshComponent(_Composant):
    pass


class _EAS:
    def spawn_actor_from_object(self, o, pos, rot):
        a = Actor()
        a.objet, a.pos, a.rot = o, pos, rot
        ACTEURS.append(a)
        return a

    def spawn_actor_from_class(self, cls, pos, rot):
        a = cls()
        a.pos, a.rot = pos, rot
        ACTEURS.append(a)
        return a

    def get_all_level_actors(self):
        return list(ACTEURS)


class _LES:
    def load_level(self, c):
        log(f"(faux) ouverture du niveau {c}")

    def new_level(self, c):
        ASSETS[c] = _Objet(c)
        log(f"(faux) nouveau niveau {c}")

    def save_current_level(self):
        log("(faux) niveau enregistré")


class _SMES:
    def remove_collisions(self, sm):
        sm.props["collisions_retirees"] = True


class StaticMeshEditorSubsystem:
    pass


class EditorActorSubsystem:
    pass


class LevelEditorSubsystem:
    pass


class SubobjectDataSubsystem:
    pass


def get_editor_subsystem(cls):
    return {"EditorActorSubsystem": _EAS, "LevelEditorSubsystem": _LES, "StaticMeshEditorSubsystem": _SMES}[cls.__name__]()


class AddNewSubobjectParams:
    def __init__(self, parent_handle=None, new_class=None):
        self.parent_handle, self.new_class = parent_handle, new_class


class _SDS:
    def k2_gather_subobject_data_for_instance(self, acteur):
        self.acteur = acteur
        return ["racine"]

    def add_new_subobject(self, p):
        c = p.new_class()
        self.acteur.props.setdefault("composants", []).append(c)
        return c, Text("")

    def rename_subobject(self, h, nom):
        h.nom = nom


def get_engine_subsystem(cls):
    return _SDS()


class SubobjectDataBlueprintFunctionLibrary:
    @staticmethod
    def get_data(h):
        return h

    @staticmethod
    def get_object(d):
        return d


class Paths:
    @staticmethod
    def project_saved_dir():
        return os.environ.get("GC_FAUX_SAVED", os.path.join(os.getcwd(), "Saved"))
