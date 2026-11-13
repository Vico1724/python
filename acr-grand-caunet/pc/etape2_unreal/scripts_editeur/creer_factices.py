"""JAMAIS EXÉCUTÉ. Python de l'éditeur Unreal 5.6 (menu Outils > Exécuter un script Python, ou
UnrealEditor-Cmd.exe acr.uproject -run=pythonscript -script=...). Crée, dans le projet « acr », les éléments
FACTICES listés dans pc/etape2_unreal/factices.json, chacun au chemin exact d'un élément du jeu.

Un factice n'est qu'un repère de chemin : nos éléments cuits le désignent, et le jeu, qui possède le vrai, charge le
sien. Les factices ne sont jamais livrés (cuire_et_empaqueter.ps1 les écarte de la cuisson).
  StaticMesh : copie du cube du moteur (/Engine/BasicShapes/Cube).
  Material   : matériau neuf portant les paramètres du vrai (noms relevés dans le jeu le 11/11/2026 :
               releves/materiaux_maitres.json) : textures, scalaires, vecteurs et static switch, ceux-ci avec la
               valeur par défaut du jeu. Seule la première texture est branchée (couleur de base) ; les autres nœuds
               restent libres : ils servent à ce que nos variantes puissent régler ces paramètres par leur nom.
               La structure interne n'a pas besoin d'être celle du jeu [pratique courante, à confirmer par E1b].
  MaterialInstanceConstant : variante factice d'un factice (champ "parent"), avec les static switch que la vraie
               variante règle dans le jeu. Sert de PARENT à nos variantes : voir outils/liste_factices.py,
               MODELE_M_SIMPLE, pour la raison.
  Blueprint  : seulement si la classe native "parent" existe dans le projet (classes souches, PROTOCOLE.md E2b) ;
               sinon ignoré avec un message.
API Python d'Unreal utilisée : EditorAssetLibrary, AssetToolsHelpers, MaterialEditingLibrary, BlueprintFactory.
À vérifier dans la documentation Python d'Unreal 5.6 sur le PC si un appel est refusé.
"""
import json
import os

import unreal

KIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LISTE = os.path.join(KIT, "factices.json")
TEXTURE_PAR_DEFAUT = "/Engine/EngineResources/DefaultTexture"

outils = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary


def dossier_et_nom(objet):
    d, n = objet.rsplit("/", 1)
    return d, n


def dimensions_reelles():
    """{chemin du maillage du jeu: (haut_cm, largeur_cm)} d'après releves/maillages_vegetation.json, s'il existe."""
    f = os.path.join(KIT, "releves", "maillages_vegetation.json")
    if not os.path.exists(f):
        return {}
    with open(f, encoding="utf-8") as h:
        d = json.load(h)["dossiers"]
    return {f"{dossier}/{nom}": v for dossier, m in d.items() for nom, v in m.items()}


DIMENSIONS = dimensions_reelles()


def maillage(objet, bornes=None):
    """Cube du moteur (1 m), dont les bornes sont étendues à celles du vrai maillage du jeu quand on les connaît.
    Constaté le 11/11/2026 : un composant d'instances calcule son arbre de tri et ses bornes avec les bornes du
    maillage au moment où les instances sont ajoutées ; avec un cube d'un mètre à la place d'un pin de 15 m, les
    arbres seraient éliminés de l'affichage trop tôt."""
    if not EAL.does_asset_exist(objet):
        EAL.duplicate_asset("/Engine/BasicShapes/Cube", objet)
    dim = DIMENSIONS.get(objet)
    if dim:
        haut, largeur = dim
        sm = EAL.load_asset(objet)
        cote = max(0.0, largeur / 2.0 - 50.0)
        sm.set_editor_property("positive_bounds_extension", unreal.Vector(cote, cote, max(0.0, haut - 50.0)))
        sm.set_editor_property("negative_bounds_extension", unreal.Vector(cote, cote, 0.0))
        EAL.save_asset(objet)
    elif bornes:                                      # bornes réelles (cm) ; le cube du moteur va de -50 à +50
        sm = EAL.load_asset(objet)
        sm.set_editor_property("positive_bounds_extension", unreal.Vector(*[max(0.0, v - 50.0) for v in bornes["max"]]))
        sm.set_editor_property("negative_bounds_extension", unreal.Vector(*[max(0.0, -v - 50.0) for v in bornes["min"]]))
        EAL.save_asset(objet)


def completer_materiau(x):
    """Matériau factice déjà créé : lui ajoute les paramètres qui lui manquent (liste allongée depuis sa création)."""
    m = EAL.load_asset(x["objet"])
    ajouts = 0
    for cle, lire, classe in (("parametres_texture", MEL.get_texture_parameter_names, unreal.MaterialExpressionTextureSampleParameter2D),
                              ("parametres_scalaires", MEL.get_scalar_parameter_names, unreal.MaterialExpressionScalarParameter),
                              ("parametres_vecteur", MEL.get_vector_parameter_names, unreal.MaterialExpressionVectorParameter)):
        presents = {str(n) for n in lire(m)}
        for i, p in enumerate(x.get(cle, [])):
            if p in presents:
                continue
            e = MEL.create_material_expression(m, classe, -2400 - 400 * ajouts // 40, 120 * (ajouts % 40))
            e.set_editor_property("parameter_name", p)
            if classe is unreal.MaterialExpressionTextureSampleParameter2D:
                e.set_editor_property("texture", unreal.load_asset(TEXTURE_PAR_DEFAUT))
            ajouts += 1
    if ajouts:
        MEL.recompile_material(m)
        EAL.save_asset(x["objet"])
        unreal.log(f"{x['objet']} : {ajouts} paramètres ajoutés")


def texture(objet):
    """Texture factice à un chemin du jeu : copie de la texture par défaut du moteur. Nos variantes la désignent ; en jeu,
    c'est la vraie texture du jeu, au même chemin, qui est chargée."""
    if not EAL.does_asset_exist(objet):
        EAL.duplicate_asset(TEXTURE_PAR_DEFAUT, objet)


def materiau(x):
    objet = x["objet"]
    if EAL.does_asset_exist(objet):
        completer_materiau(x)
        return
    d, n = dossier_et_nom(objet)
    m = outils.create_asset(n, d, unreal.Material, unreal.MaterialFactoryNew())
    defaut = unreal.load_asset(TEXTURE_PAR_DEFAUT)
    y = 0
    textures = x.get("parametres_texture", [])
    # la couleur de base d'abord, pour que l'aperçu dans l'éditeur montre notre image
    textures = sorted(textures, key=lambda p: (0 if "BaseColor" in p else 1, p))
    for i, p in enumerate(textures):
        e = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, y)
        e.set_editor_property("parameter_name", p)
        e.set_editor_property("texture", defaut)
        if i == 0:
            MEL.connect_material_property(e, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
        y += 250
    y = 0
    for p in x.get("parametres_scalaires", []):
        e = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -1000, y)
        e.set_editor_property("parameter_name", p)
        y += 100
    y = 0
    for p in x.get("parametres_vecteur", []):
        e = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -1400, y)
        e.set_editor_property("parameter_name", p)
        y += 200
    y = 0
    for p, valeur in x.get("static_switch", {}).items():
        e = MEL.create_material_expression(m, unreal.MaterialExpressionStaticBoolParameter, -1800, y)
        e.set_editor_property("parameter_name", p)
        e.set_editor_property("default_value", bool(valeur))
        y += 100
    MEL.recompile_material(m)
    EAL.save_asset(objet)


def variante(x):
    objet = x["objet"]
    if EAL.does_asset_exist(objet):
        return
    parent = unreal.load_asset(x["parent"])
    if parent is None:
        unreal.log_warning(f"variante factice {objet} ignorée : parent {x['parent']} absent")
        return
    d, n = dossier_et_nom(objet)
    mi = outils.create_asset(n, d, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    regler = getattr(MEL, "set_material_instance_static_switch_parameter_value", None)
    for p, valeur in x.get("static_switch", {}).items():
        if regler is None:
            unreal.log_warning(f"{n} : cette version ne sait pas régler un static switch depuis Python ; cocher "
                               f"« {p} » = {valeur} à la main dans la variante factice")
        else:
            regler(mi, p, bool(valeur))
    MEL.update_material_instance(mi)
    EAL.save_asset(objet)


def blueprint(objet, parent):
    if EAL.does_asset_exist(objet):
        return
    classe = unreal.load_class(None, parent) if parent else None
    if classe is None:
        unreal.log_warning(f"factice Blueprint {objet} ignoré : classe native {parent} absente du projet (PROTOCOLE.md, E2b)")
        return
    d, n = dossier_et_nom(objet)
    f = unreal.BlueprintFactory()
    f.set_editor_property("parent_class", classe)
    outils.create_asset(n, d, None, f)
    EAL.save_asset(objet)


def main():
    liste = json.load(open(LISTE, encoding="utf-8"))["factices"]
    # les matériaux d'abord : les variantes factices ont besoin de leur parent
    ordre = {"Material": 0, "MaterialInstanceConstant": 1, "StaticMesh": 2, "Blueprint": 3}
    for x in sorted(liste, key=lambda x: ordre.get(x["type"], 9)):
        if x["type"] == "StaticMesh":
            maillage(x["objet"], x.get("bornes_cm"))
        elif x["type"] == "Material":
            if x.get("a_completer"):
                unreal.log_warning(f"{x['objet']} : {x['a_completer']} ; non créé")
                continue
            materiau(x)
        elif x["type"] == "MaterialInstanceConstant":
            variante(x)
        elif x["type"] == "Blueprint":
            blueprint(x["objet"], x.get("parent"))
        elif x["type"] == "Texture2D":
            texture(x["objet"])
    EAL.save_directory("/Game/")
    unreal.log(f"factices : {len(liste)} lus")


main()
