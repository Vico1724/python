r"""Essai E1a (PROTOCOLE.md § 3) : importe une image AU CHEMIN d'une texture du jeu, avec les réglages relevés sur
l'originale, pour vérifier que le jeu accepte une texture cuite par notre éditeur.

Cible par défaut : la bannière du portique gallois, /Game/Props/RallyProps/Gantries/T_RallyGantryWales_B. Relevé du
11/11/2026 (releves/textures.json) : 2048 x 2048, PF_DXT1, 12 niveaux de détail, aucun réglage hors défaut (donc
sRVB, compression par défaut, groupe World, pas de texture virtuelle). L'image fournie doit faire 2048 x 2048 et ne
pas avoir de canal alpha, sinon la compression par défaut donnerait du DXT5.

EXÉCUTÉ le 11/11/2026 en ligne de commande :
  UnrealEditor-Cmd.exe acr.uproject -run=pythonscript -script="...\essai_e1a.py Z:\acrxs\unreal\sources\T_RallyGantryWales_B.png"
"""
import os
import sys

import unreal

CIBLE = "/Game/Props/RallyProps/Gantries/T_RallyGantryWales_B"


def main():
    image = sys.argv[1] if len(sys.argv) > 1 else r"Z:\acrxs\unreal\sources\T_RallyGantryWales_B.png"
    if not os.path.exists(image):
        raise SystemExit(f"image absente : {image}")
    dossier, nom = CIBLE.rsplit("/", 1)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", image)
    t.set_editor_property("destination_path", dossier)
    t.set_editor_property("destination_name", nom)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    tex = unreal.EditorAssetLibrary.load_asset(CIBLE)
    if tex is None:
        raise SystemExit(f"import refusé : {image}")
    tex.set_editor_property("srgb", True)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD)
    tex.set_editor_property("virtual_texture_streaming", False)
    tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    unreal.EditorAssetLibrary.save_asset(CIBLE)
    unreal.log(f"E1a : {CIBLE} importée ({tex.blueprint_get_size_x()} x {tex.blueprint_get_size_y()}) depuis {image}")


main()
