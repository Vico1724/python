"""Python de l'éditeur Unreal 5.6 (UnrealEditor-Cmd.exe acr.uproject -run=pythonscript -script=...), lancé par
chaine_decor.ps1 avant la cuisson. Importe les images du rallye propre au Grand Caunet (docs/19_rallye_propre.md) :
pc/etape2_unreal/ui/T_GrandCaunetLogo.png et T_GrandCaunetFond.png (faites par outils/images_rallye.py) dans
/Game/Environments/GrandCaunet/UI, dossier que la cuisson inclut déjà (-Inclure 'Environments/GrandCaunet').

Réglages relevés sur les images des lieux du jeu (T_RallyWales, T_WalesRally, lus le 17/11/2026) : groupe UI
(TEXTUREGROUP_UI), compression TC_EditorIcon (BGRA 8 bits, sans perte), jamais en streaming. Les tables du jeu les
désignent par leur chemin (DT_TracksLocationsLogos, DT_TracksLocationsBackgrounds : voir rallye_grand_caunet.json).
"""
import os

import unreal

KIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DEST = "/Game/Environments/GrandCaunet/UI"
IMAGES = ("T_GrandCaunetLogo", "T_GrandCaunetFond")
EAL = unreal.EditorAssetLibrary


def importer(fichier):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", fichier)
    t.set_editor_property("destination_path", DEST)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return list(t.get_editor_property("imported_object_paths"))


for nom in IMAGES:
    png = os.path.join(KIT, "ui", nom + ".png")
    if not os.path.exists(png):
        raise SystemExit(f"{png} absent : lancer pc/etape2_unreal/outils/images_rallye.py")
    chemins = importer(png)
    if not chemins:
        raise SystemExit(f"import de {png} refusé")
    tex = unreal.load_asset(f"{DEST}/{nom}")
    tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property("never_stream", True)
    tex.set_editor_property("srgb", True)
    EAL.save_asset(f"{DEST}/{nom}", only_if_is_dirty=False)
    unreal.log(f"importer_ui : {DEST}/{nom} ({tex.blueprint_get_size_x()} x {tex.blueprint_get_size_y()})")
