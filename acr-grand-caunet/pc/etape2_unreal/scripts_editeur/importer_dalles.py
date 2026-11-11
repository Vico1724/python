"""JAMAIS EXÉCUTÉ. Python de l'éditeur Unreal 5.6. Importe nos dalles de terrain (et, pour l'essai E4, la route)
dans /Game/GrandCaunet/, crée pour chaque dalle une variante (MaterialInstanceConstant) du matériau « simple » du jeu
(/Game/Materials/General/Masters/M_Simple, factice créé par creer_factices.py) avec l'image de la dalle, et contrôle
le repère après import.

Sources, dans cet ordre :
 1. data/processed/textures_sol.json, s'il existe (produit par un autre agent ; format à confirmer). Format attendu
    par ce script :
      {"repere": "modele/repere.json",
       "dalles": [{"nom": "terrain_914000_6242500",            # nom du maillage dans le glb
                   "glb": "modele/terrain_sol.glb",              # fichier qui contient ce maillage
                   "texture": "modele/textures_sol/terrain_914000_6242500.jpg",
                   "bornes_l93": [914000, 6242500, 914500, 6243000]}]}
    Si le fichier a une autre forme, le script s'arrête en le disant : adapter la fonction lire_manifeste().
 2. sinon modele/terrain.glb (écrit par scripts/08_modele_3d.py) : un maillage par dalle de 500 m, nommé
    terrain_<x>_<y> (coin sud-ouest en Lambert-93), chacun avec son image JPEG intégrée et ses UV.

Repère : nos glb sont en glTF (+Y haut, main droite, mètres, X est, Z sud). Le projet veut UE = 100 * (gX, gZ, gY)
(scripts_editeur/repere_unreal.py). L'importeur glTF d'Unreal fait SA propre conversion d'axes, que nous ne
connaissons pas avec certitude : ce script mesure les bornes importées et les compare aux bornes attendues,
puis écrit le verdict dans le journal. Si les axes ne correspondent pas, régler la transformation d'import
(ou faire pivoter les acteurs posés) selon ce verdict avant d'aller plus loin.
"""
import json
import os
import struct
import sys

import unreal

RACINE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import repere_unreal as R  # noqa: E402,F401  (gardé pour les conversions dans E4)

DEST = "/Game/GrandCaunet/Terrain"
PARENT = "/Game/Materials/General/Masters/M_Simple"
PARAM_COULEUR = "Simple_BaseColor_Texture"
EAL = unreal.EditorAssetLibrary


def bornes_glb(chemin):
    """{nom de maillage: (min, max)} lus dans le JSON du glb (accessoires POSITION)."""
    b = open(chemin, "rb").read()
    n = struct.unpack_from("<I", b, 12)[0]
    g = json.loads(b[20:20 + n])
    out = {}
    for m in g["meshes"]:
        a = g["accessors"][m["primitives"][0]["attributes"]["POSITION"]]
        out[m["name"]] = (a["min"], a["max"])
    return out


def lire_manifeste():
    f = os.path.join(RACINE, "data", "processed", "textures_sol.json")
    if not os.path.exists(f):
        return None
    m = json.load(open(f, encoding="utf-8"))
    if "dalles" not in m or not all({"nom", "glb", "texture"} <= set(d) for d in m["dalles"]):
        raise SystemExit("textures_sol.json : forme inattendue ; adapter lire_manifeste() (voir l'en-tête du script)")
    return m


def importer(fichier, dest):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", fichier)
    t.set_editor_property("destination_path", dest)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return list(t.get_editor_property("imported_object_paths"))


def variante(nom, texture):
    """MaterialInstanceConstant de M_Simple avec la texture de la dalle. Aucun paramètre « static switch » modifié :
    la variante réutilise alors les programmes d'affichage déjà cuits du parent dans le jeu."""
    chemin = f"{DEST}/MI_{nom}"
    if not EAL.does_asset_exist(chemin):
        f = unreal.MaterialInstanceConstantFactoryNew()
        unreal.AssetToolsHelpers.get_asset_tools().create_asset(f"MI_{nom}", DEST, unreal.MaterialInstanceConstant, f)
    mi = unreal.load_asset(chemin)
    unreal.MaterialEditingLibrary.set_material_instance_parent(mi, unreal.load_asset(PARENT))
    unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi, PARAM_COULEUR, texture)
    EAL.save_asset(chemin)
    return mi


def controle_axes(sm, attendu_min, attendu_max):
    """Compare les bornes du maillage importé (cm) aux bornes attendues 100 * (gX, gZ, gY)."""
    bb = sm.get_bounding_box()
    imp = (bb.min.x, bb.min.y, bb.min.z, bb.max.x, bb.max.y, bb.max.z)
    lo = [attendu_min[0] * 100, attendu_min[2] * 100, attendu_min[1] * 100]
    hi = [attendu_max[0] * 100, attendu_max[2] * 100, attendu_max[1] * 100]
    ok = all(abs(a - b) < 5 for a, b in zip(imp, lo + hi))
    unreal.log(f"{sm.get_name()} : bornes importées {tuple(round(v) for v in imp)} ; attendues {tuple(round(v) for v in lo + hi)} -> "
               f"{'REPÈRE CONFORME' if ok else 'REPÈRE DIFFÉRENT : voir PROTOCOLE.md E3'}")
    return ok


def main():
    man = lire_manifeste()
    if man:
        sources = {d["glb"] for d in man["dalles"]}
    else:
        sources = {"modele/terrain.glb"}
    for s in sorted(sources):
        chemin = os.path.join(RACINE, s)
        attendu = bornes_glb(chemin)
        importes = importer(chemin, DEST)
        verdicts = []
        for p in importes:
            a = unreal.load_asset(p)
            if isinstance(a, unreal.StaticMesh) and a.get_name() in attendu:
                verdicts.append(controle_axes(a, *attendu[a.get_name()]))
                # Pas de collision Unreal à régler ici : la physique du jeu vient du BakedData (docs/decisions.md D4
                # d'ACR Extra Stages) ; les acteurs posés seront mis en « NoCollision » (poser_dalles dans E3/E4).
        unreal.log(f"{s} : {len(importes)} éléments importés, repère conforme sur {sum(verdicts)} / {len(verdicts)} dalles")
    # variantes de matériau : une par dalle, texture importée avec la dalle (même nom) ou depuis le manifeste
    for p in EAL.list_assets(DEST, recursive=False):
        a = unreal.load_asset(p)
        if isinstance(a, unreal.StaticMesh) and a.get_name().startswith("terrain_"):
            nom = a.get_name()
            tex = None
            if man:
                d = next(d for d in man["dalles"] if d["nom"] == nom)
                tex = unreal.load_asset(importer(os.path.join(RACINE, d["texture"]), DEST + "/Textures")[0])
            else:
                cand = [q for q in EAL.list_assets(DEST, recursive=True) if isinstance(unreal.load_asset(q), unreal.Texture2D) and nom in q]
                tex = unreal.load_asset(cand[0]) if cand else None
            if tex is None:
                unreal.log_warning(f"{nom} : pas de texture trouvée")
                continue
            a.set_material(0, variante(nom, tex))
            EAL.save_asset(p)
    unreal.log("dalles importées ; vérifier les verdicts de repère ci-dessus avant de continuer")


main()
