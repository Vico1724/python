"""JAMAIS EXÉCUTÉ. Python de l'éditeur Unreal 5.6 (menu Outils > Exécuter un script Python, ou
UnrealEditor-Cmd.exe acr.uproject -run=pythonscript -script=...). Crée, dans le projet « acr », les éléments
FACTICES listés dans pc/etape2_unreal/factices.json, chacun au chemin exact d'un élément du jeu.

Un factice n'est qu'un repère de chemin : nos éléments cuits le désignent, et le jeu, qui possède le vrai, charge le
sien. Les factices ne sont jamais livrés (outils/filtrer_cuisson.py les retire de la cuisson).
  StaticMesh : copie du cube du moteur (/Engine/BasicShapes/Cube).
  Material   : matériau neuf avec les paramètres de texture listés, branchés sur la couleur de base, pour que nos
               variantes (MaterialInstanceConstant) puissent régler ces paramètres. Les NOMS doivent être exactement
               ceux du jeu ; la structure interne n'a pas besoin de l'être [pratique courante du modding UE, à
               confirmer par l'essai E1b].
  Blueprint  : seulement si "parent" est rempli (une classe native présente dans le projet) ; sinon ignoré avec un
               message, voir PROTOCOLE.md E2.
API Python d'Unreal utilisée : EditorAssetLibrary, AssetToolsHelpers, MaterialEditingLibrary, BlueprintFactory.
À vérifier dans la documentation Python d'Unreal 5.6 sur le PC si un appel est refusé.
"""
import json
import os

import unreal

KIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LISTE = os.path.join(KIT, "factices.json")

outils = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary


def dossier_et_nom(objet):
    d, n = objet.rsplit("/", 1)
    return d, n


def maillage(objet):
    if not EAL.does_asset_exist(objet):
        EAL.duplicate_asset("/Engine/BasicShapes/Cube", objet)


def materiau(objet, textures, scalaires):
    if EAL.does_asset_exist(objet):
        return
    d, n = dossier_et_nom(objet)
    m = outils.create_asset(n, d, unreal.Material, unreal.MaterialFactoryNew())
    y = 0
    for i, p in enumerate(textures):
        e = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -500, y)
        e.set_editor_property("parameter_name", p)
        if i == 0:
            MEL.connect_material_property(e, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
        y += 250
    for p in scalaires:
        e = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -500, y)
        e.set_editor_property("parameter_name", p)
        y += 150
    MEL.recompile_material(m)
    EAL.save_asset(objet)


def blueprint(objet, parent):
    if EAL.does_asset_exist(objet):
        return
    if not parent:
        unreal.log_warning(f"factice Blueprint {objet} ignoré : pas de classe parente (PROTOCOLE.md, E2)")
        return
    d, n = dossier_et_nom(objet)
    f = unreal.BlueprintFactory()
    f.set_editor_property("parent_class", unreal.load_class(None, parent))
    outils.create_asset(n, d, None, f)
    EAL.save_asset(objet)


def main():
    liste = json.load(open(LISTE, encoding="utf-8"))["factices"]
    for x in liste:
        if x["type"] == "StaticMesh":
            maillage(x["objet"])
        elif x["type"] == "Material":
            if x.get("a_completer"):
                unreal.log_warning(f"{x['objet']} : {x['a_completer']} ; non créé")
                continue
            materiau(x["objet"], x.get("parametres_texture", []), x.get("parametres_scalaires", []))
        elif x["type"] == "Blueprint":
            blueprint(x["objet"], x.get("parent"))
    EAL.save_directory("/Game/")
    unreal.log(f"factices : {len(liste)} lus")


main()
