"""REMPLACÉ PAR construire_niveau.py (piloté par le manifeste de scripts/16_paquet_unreal.py), qui fait la même chose
au complet ; ce squelette est gardé pour mémoire et ne doit plus être lancé. Il a été corrigé le 11/11/2026 d'après
les relevés du jeu (parent des variantes, les trois textures, réglages de texture) : ces corrections restent à
reporter dans construire_niveau.py (PROTOCOLE.md, § 0 bis).

JAMAIS EXÉCUTÉ. Python de l'éditeur Unreal 5.6. Importe nos dalles de terrain dans /Game/GrandCaunet/Terrain,
crée pour chaque dalle une variante (MaterialInstanceConstant) avec son image, et contrôle le repère après import.

Parent des variantes (relevé sur le PC le 11/11/2026) : la variante du jeu désignée dans factices.json par
"role": "modele_m_simple" (MI_SisteronConcrete01), et non M_Simple directement. M_Simple n'échantillonne ses textures
que si ses static switch « Simple_Use_*_Texture » sont actifs ; ils ne le sont pas par défaut, et les activer dans
notre variante demanderait des programmes d'affichage que le jeu n'a pas. La variante modèle les a déjà : la nôtre
ne règle que des textures. Elle règle les TROIS textures du modèle, sinon elle hériterait du béton de Sisteron :
  Simple_BaseColor_Texture     notre photo de dalle (sRVB)
  Simple_Normal_Texture        notre relief, ou une normale plate
  Simple_OcclRoughMet_Texture  une texture plate (occlusion 1, rugosité 0,85, métal 0 : valeurs d'ACR Extra Stages)

Sources, dans cet ordre :
 1. data/processed/textures_sol.json (scripts/14_textures_sol.py) : 26 dalles « dalle_<x>_<y> » et 126 sous-dalles
    « sous_<x>_<y> » le long de la route, images dans modele/textures_sol/, maillages dans modele/terrain_sol.glb.
    Ces fichiers lourds ne sont pas dans le dépôt (scripts/tout_lancer.sh les régénère).
 2. à défaut, modele/apercu/terrain_sol.glb (versionné) : les 26 dalles, images de 512 px intégrées. Suffisant pour
    l'essai E3a.
 3. à défaut, modele/terrain.glb ou modele/apercu/terrain.glb (dalles « terrain_<x>_<y> », photo aérienne brute).

Les images de dalle font 2660 px : elles sont étirées à la puissance de deux à l'import (réglage « Power Of Two
Mode »), faute de quoi Unreal ne leur calcule pas de niveaux de détail.

Repère : nos glb sont en glTF (+Y haut, main droite, mètres, X est, Z sud). Le projet veut UE = 100 * (gX, gZ, gY)
(scripts_editeur/repere_unreal.py). L'importeur glTF d'Unreal fait SA propre conversion d'axes, que nous ne
connaissons pas avec certitude : ce script mesure les bornes importées et les compare aux bornes attendues,
puis écrit le verdict dans le journal. Si les axes ne correspondent pas, régler la transformation d'import
(ou faire pivoter les acteurs posés) selon ce verdict avant d'aller plus loin.

Usage : py "…/importer_dalles.py" [--seulement dalle_913500_6242500,sous_913800_6242900]
"""
import argparse
import json
import os
import struct
import sys
import tempfile
import zlib

import unreal

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.abspath(os.path.join(ICI, "..", "..", ".."))
sys.path.insert(0, ICI)
import repere_unreal as R  # noqa: E402,F401  (gardé pour les conversions dans E4)

DEST = "/Game/GrandCaunet/Terrain"
TEXTURES = "/Game/GrandCaunet/Textures"
M_SIMPLE = "/Game/Materials/General/Masters/M_Simple"
P_COULEUR, P_NORMALE, P_ORM = "Simple_BaseColor_Texture", "Simple_Normal_Texture", "Simple_OcclRoughMet_Texture"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary


def parent_des_variantes():
    f = json.load(open(os.path.join(ICI, "..", "factices.json"), encoding="utf-8"))["factices"]
    modele = next((x["objet"] for x in f if x.get("role") == "modele_m_simple"), None)
    p = unreal.load_asset(modele) if modele else None
    if p is None:
        unreal.log_warning("variante modèle absente (creer_factices.py) : parent M_Simple, les textures ne s'afficheront "
                           "probablement pas en jeu (static switch inactifs)")
        p = unreal.load_asset(M_SIMPLE)
    return p


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


def sources():
    """(glb à importer, {nom de maillage: {"couleur": fichier ou None, "relief": fichier ou None}})"""
    man = os.path.join(RACINE, "data", "processed", "textures_sol.json")
    complet = os.path.join(RACINE, "modele", "terrain_sol.glb")
    if os.path.exists(man) and os.path.exists(complet):
        images = {}
        for d in json.load(open(man, encoding="utf-8"))["dalles"]:
            for e in [d] + d.get("sous_dalles", []):
                images[e["nom"]] = {k: os.path.join(RACINE, "modele", e[k]) if e.get(k) else None for k in ("couleur", "relief")}
        return complet, images
    for g in ("modele/apercu/terrain_sol.glb", "modele/terrain.glb", "modele/apercu/terrain.glb"):
        chemin = os.path.join(RACINE, g)
        if os.path.exists(chemin):
            unreal.log_warning(f"données complètes absentes : import de {g} (images intégrées au glb)")
            return chemin, {}
    raise SystemExit("aucun terrain à importer : voir l'en-tête du script")


def importer(fichier, dest):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", fichier)
    t.set_editor_property("destination_path", dest)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return list(t.get_editor_property("imported_object_paths"))


def png_uni(chemin, rvb, cote=8):
    """Écrit un PNG uni (sans bibliothèque d'images)."""
    ligne = b"\x00" + bytes(rvb) * cote

    def bloc(nom, donnees):
        return struct.pack(">I", len(donnees)) + nom + donnees + struct.pack(">I", zlib.crc32(nom + donnees) & 0xFFFFFFFF)

    with open(chemin, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", cote, cote, 8, 2, 0, 0, 0))
                + bloc(b"IDAT", zlib.compress(ligne * cote)) + bloc(b"IEND", b""))


def regler_texture(tex, genre):
    """Réglages relevés sur les textures du jeu (releves/textures.json) : couleur = sRVB, compression par défaut ;
    normale = TC_Normalmap, groupe WorldNormalMap, sans sRVB ; masques (occlusion, rugosité, métal) = TC_Masks, sans sRVB."""
    try:
        tex.set_editor_property("power_of_two_mode", unreal.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO)
    except Exception as e:  # noqa: BLE001
        unreal.log_warning(f"{tex.get_name()} : « Power Of Two Mode » non réglé ({e}) ; le régler à la main si l'image n'est pas en puissance de 2")
    tex.set_editor_property("virtual_texture_streaming", False)
    if genre == "normale":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP)
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("flip_green_channel", True)      # nos reliefs sont en convention OpenGL (textures_sol.json)
    elif genre == "masques":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property("srgb", False)
    EAL.save_loaded_asset(tex)


def texture(fichier, genre):
    chemins = importer(fichier, TEXTURES)
    tex = unreal.load_asset(chemins[0]) if chemins else None
    if tex is not None:
        regler_texture(tex, genre)
    return tex


def textures_plates():
    tmp = tempfile.mkdtemp(prefix="gc_plat_")
    out = {}
    for nom, rvb, genre in (("T_GC_Plat_L", (255, 217, 0), "masques"), ("T_GC_Plat_N", (128, 128, 255), "normale")):
        if not EAL.does_asset_exist(f"{TEXTURES}/{nom}"):
            png_uni(os.path.join(tmp, nom + ".png"), rvb)
            texture(os.path.join(tmp, nom + ".png"), genre)
        out[genre] = unreal.load_asset(f"{TEXTURES}/{nom}")
    return out


def variante(nom, parent, couleur, normale, orm):
    """Aucun « static switch » modifié : la variante réutilise les programmes d'affichage de son parent dans le jeu."""
    chemin = f"{DEST}/MI_{nom}"
    if not EAL.does_asset_exist(chemin):
        f = unreal.MaterialInstanceConstantFactoryNew()
        unreal.AssetToolsHelpers.get_asset_tools().create_asset(f"MI_{nom}", DEST, unreal.MaterialInstanceConstant, f)
    mi = unreal.load_asset(chemin)
    MEL.set_material_instance_parent(mi, parent)
    for p, t in ((P_COULEUR, couleur), (P_NORMALE, normale), (P_ORM, orm)):
        if t is not None:
            MEL.set_material_instance_texture_parameter_value(mi, p, t)
    MEL.update_material_instance(mi)
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--seulement", default="", help="noms de maillages séparés par des virgules (défaut : tous)")
    a = ap.parse_args(sys.argv[1:])
    seulement = {s for s in a.seulement.split(",") if s}
    glb, images = sources()
    attendu = bornes_glb(glb)
    importes = importer(glb, DEST)
    verdicts = []
    for p in importes:
        x = unreal.load_asset(p)
        if isinstance(x, unreal.StaticMesh) and x.get_name() in attendu:
            verdicts.append(controle_axes(x, *attendu[x.get_name()]))
            # Pas de collision Unreal à régler ici : la physique du jeu vient du BakedData (docs/decisions.md D4
            # d'ACR Extra Stages) ; les acteurs posés seront mis en « NoCollision » (E3/E4).
    unreal.log(f"{glb} : {len(importes)} éléments importés, repère conforme sur {sum(verdicts)} / {len(verdicts)} maillages")

    parent = parent_des_variantes()
    plates = textures_plates()
    importees = [q for q in EAL.list_assets(DEST, recursive=True) if isinstance(unreal.load_asset(q), unreal.Texture2D)]
    faits = 0
    for p in EAL.list_assets(DEST, recursive=False):
        sm = unreal.load_asset(p)
        if not isinstance(sm, unreal.StaticMesh) or sm.get_name() not in attendu:
            continue
        nom = sm.get_name()
        if seulement and nom not in seulement:
            continue
        im = images.get(nom, {})
        if im.get("couleur"):
            couleur = texture(im["couleur"], "couleur")
            normale = texture(im["relief"], "normale") if im.get("relief") else plates["normale"]
        else:                                   # image intégrée au glb : importée avec lui, retrouvée par son nom
            cand = [q for q in importees if nom in q]
            couleur = unreal.load_asset(cand[0]) if cand else None
            normale = plates["normale"]
            if couleur is not None:
                regler_texture(couleur, "couleur")
        if couleur is None:
            unreal.log_warning(f"{nom} : pas d'image trouvée ; variante non créée")
            continue
        sm.set_material(0, variante(nom, parent, couleur, normale, plates["masques"]))
        EAL.save_asset(p)
        faits += 1
    unreal.log(f"{faits} dalles avec leur variante ; vérifier les verdicts de repère ci-dessus avant de continuer")


main()
