r"""JAMAIS EXÉCUTÉ DANS UNREAL. Écrit d'après l'API Python de l'éditeur Unreal Engine 5.x ; seule la logique de
parcours du manifeste a été vérifiée, avec un faux module « unreal » (outils/faux_unreal/, outils/essai_construire.py).
Les appels dont je ne suis pas sûr sont isolés dans les fonctions de la section « APPELS À VÉRIFIER » et listés
dans pc/etape2_unreal/A_VERIFIER.md.

Construit le décor de la spéciale GrandCaunet à partir d'un manifeste produit par scripts/16_paquet_unreal.py :
  1. dossiers du projet ;
  2. textures (sRGB, compression, adressage, groupe de LOD réglés d'après le manifeste) ;
  3. maillages glb (un fichier = un maillage ; collision supprimée, Nanite désactivé, section vérifiée) et contrôle
     de leurs bornes contre le manifeste (verdict « REPÈRE CONFORME ») ;
  4. variantes de matériaux : parent du jeu s'il existe dans le projet et si --parent jeu, sinon matériau de
     secours M_GC_Secours créé ici (à ne pas livrer). Relevé dans le jeu le 11/11/2026 (PROTOCOLE.md § 0 bis) :
     quand le manifeste désigne M_Simple, le parent pris est la variante modèle du jeu (factices.json,
     "role": "modele_m_simple"), parce que M_Simple n'échantillonne ses textures que si des static switch sont
     actifs et qu'ils ne le sont pas par défaut ; et une variante qui ne règle pas de relief en reçoit un plat,
     faute de quoi elle hériterait du relief de béton de la variante modèle ;
  5. niveau (/Game/Levels/GrandCaunet[_E3|_E4]) : un acteur par maillage, posé à acteur.position_cm, sans
     collision ; éclairage de contrôle facultatif ;
  6. arbres, arbustes, piquets : un acteur par maillage du jeu, avec un composant d'instances. Si le relevé
     releves/maillages_vegetation.json existe, le maillage de chaque plante est rechoisi dans le dossier de son
     essence d'après sa taille (attribution.py) : le manifeste les tire au hasard, souches comprises ;
  7. enregistrement, et rapport JSON dans <projet>/Saved/GrandCaunet/.

Utilisation, dans l'éditeur (Outils > Exécuter un script Python, ou console « py ») :
  py "Z:\...\pc\etape2_unreal\scripts_editeur\construire_niveau.py" --etendue E3 --mire
  py "Z:\...\pc\etape2_unreal\scripts_editeur\construire_niveau.py" --etendue E4
  py "Z:\...\pc\etape2_unreal\scripts_editeur\construire_niveau.py" --manifeste Z:\...\paquet_unreal\manifeste.json --etendue complet
Options : --manifeste (défaut : ../echantillon/manifeste.json), --etendue E3|E4|complet, --mire (importe d'abord
  la mire d'axes et s'arrête si les axes diffèrent), --parent secours|jeu, --placement rapport_stage_build.json
  (pose dans le repère physique d'ACR Extra Stages), --sans-instances, --sans-eclairage, --max-instances N,
  --seulement-assets (n'ouvre ni ne modifie aucun niveau).
"""
import argparse
import csv
import json
import math
import os
import re
import struct
import sys
import time
import zlib

import unreal

ICI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(ICI)
sys.path.insert(0, ICI)
import attribution as A  # noqa: E402
import repere_unreal as R  # noqa: E402

TOL_BORNES_CM = 2.0
M_SIMPLE = "/Game/Materials/General/Masters/M_Simple"
PARAM_RELIEF = "Simple_Normal_Texture"
RELIEF_PLAT = "T_GC_Relief_Plat"


# =====================================================================================================
# APPELS À VÉRIFIER (voir A_VERIFIER.md) : chacun dans une fonction courte, pour corriger en un endroit
# =====================================================================================================
def v_journal(msg, niveau="info"):
    {"info": unreal.log, "alerte": unreal.log_warning, "erreur": unreal.log_error}[niveau](f"[GrandCaunet] {msg}")


def v_dossier(chemin):
    if not unreal.EditorAssetLibrary.does_directory_exist(chemin):
        unreal.EditorAssetLibrary.make_directory(chemin)


def v_existe(chemin):
    return unreal.EditorAssetLibrary.does_asset_exist(chemin)


def v_charger(chemin):
    return unreal.EditorAssetLibrary.load_asset(chemin)


def v_enregistrer(chemin):
    unreal.EditorAssetLibrary.save_asset(chemin, only_if_is_dirty=False)


def v_supprimer(chemin):
    if unreal.EditorAssetLibrary.does_asset_exist(chemin):
        unreal.EditorAssetLibrary.delete_asset(chemin)


def v_lister(dossier):
    return list(unreal.EditorAssetLibrary.list_assets(dossier, recursive=True, include_folder=False))


def v_importer_fichier(fichier, dossier, nom):
    """Import automatique d'un fichier (image ou glb) ; renvoie les chemins des objets créés.
    glb : passe par Interchange dans UE 5.6 ; les options par défaut peuvent créer matériaux et textures, que
    v_nettoyer_import supprime ensuite (le glb n'en porte pas, mais l'importeur crée un matériau par section)."""
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", fichier)
    t.set_editor_property("destination_path", dossier)
    t.set_editor_property("destination_name", nom)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return [str(p) for p in t.get_editor_property("imported_object_paths")]


def nom_enum_python(nom):
    """Nom C++ d'une valeur d'énumération -> nom Python : « TEXTUREGROUP_WorldNormalMap » ->
    « TEXTUREGROUP_WORLD_NORMAL_MAP », « TC_Normalmap » -> « TC_NORMALMAP »."""
    pre, _, reste = nom.partition("_")
    return pre + "_" + re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", reste).upper()


def v_regler_texture(tex, imp):
    tex.set_editor_property("srgb", bool(imp["srgb"]))
    tex.set_editor_property("compression_settings", getattr(unreal.TextureCompressionSettings, nom_enum_python(imp["compression"])))
    tex.set_editor_property("lod_group", getattr(unreal.TextureGroup, nom_enum_python(imp["groupe_lod"])))
    adr = unreal.TextureAddress.TA_CLAMP if imp["adressage"] == "Clamp" else unreal.TextureAddress.TA_WRAP
    tex.set_editor_property("address_x", adr)
    tex.set_editor_property("address_y", adr)
    tex.set_editor_property("virtual_texture_streaming", bool(imp.get("virtual_texture_streaming", False)))
    if imp["compression"] == "TC_Normalmap":
        tex.set_editor_property("flip_green_channel", False)       # le paquet fournit déjà la convention DirectX


def v_regler_maillage(sm):
    """Pas de collision (la physique du jeu vient du BakedData), pas de Nanite au départ."""
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    sub.remove_collisions(sm)
    ns = sm.get_editor_property("nanite_settings")
    ns.set_editor_property("enabled", False)
    sm.set_editor_property("nanite_settings", ns)


def v_bornes_maillage(sm):
    """Bornes locales (cm) du maillage importé : (min xyz, max xyz)."""
    b = sm.get_bounding_box()
    return (b.min.x, b.min.y, b.min.z), (b.max.x, b.max.y, b.max.z)


def v_nom_section(sm):
    mats = sm.get_editor_property("static_materials")
    return str(mats[0].get_editor_property("material_slot_name")) if mats else None


def v_affecter_materiau(sm, mi):
    sm.set_material(0, mi)


def v_creer_variante(nom, dossier, parent):
    chemin = f"{dossier}/{nom}"
    existait = v_existe(chemin)
    if not existait:
        unreal.AssetToolsHelpers.get_asset_tools().create_asset(nom, dossier, unreal.MaterialInstanceConstant,
                                                               unreal.MaterialInstanceConstantFactoryNew())
    mi = v_charger(chemin)
    if existait:
        # variante gardée d'une construction précédente (Shared/Materials n'est pas vidé) : ses anciens réglages
        # resteraient posés. Relu le 13/11/2026 : MI_GC_Marquage, passé au décalque du jeu, portait encore les trois
        # textures de son ancien parent M_Simple (sans effet à l'écran, mais livrées pour rien).
        unreal.MaterialEditingLibrary.clear_all_material_instance_parameters(mi)
    unreal.MaterialEditingLibrary.set_material_instance_parent(mi, parent)
    return mi


def v_parametre_texture(mi, nom, tex):
    unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi, nom, tex)


def v_parametre_scalaire(mi, nom, valeur):
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, nom, float(valeur))


def v_parametre_vecteur(mi, nom, valeur):
    v = [float(x) for x in valeur] + [1.0] * (4 - len(valeur))
    unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi, nom, unreal.LinearColor(v[0], v[1], v[2], v[3]))


def v_creer_materiau_secours(chemin, params):
    """Matériau simple : Couleur -> BaseColor, ORM (R occlusion, G rugosité, B métal), Relief -> Normal."""
    if v_existe(chemin):
        return v_charger(chemin)
    dossier, nom = chemin.rsplit("/", 1)
    MEL = unreal.MaterialEditingLibrary
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(nom, dossier, unreal.Material, unreal.MaterialFactoryNew())
    c = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, -200)
    c.set_editor_property("parameter_name", params["couleur"])
    MEL.connect_material_property(c, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    o = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, 100)
    o.set_editor_property("parameter_name", params["orm"])
    o.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    MEL.connect_material_property(o, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(o, "G", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(o, "B", unreal.MaterialProperty.MP_METALLIC)
    n = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, 400)
    n.set_editor_property("parameter_name", params["relief"])
    n.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    MEL.connect_material_property(n, "RGB", unreal.MaterialProperty.MP_NORMAL)
    MEL.recompile_material(m)
    v_enregistrer(chemin)
    return m


def v_ouvrir_ou_creer_niveau(chemin):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if v_existe(chemin):
        les.load_level(chemin)
    else:
        les.new_level(chemin)          # niveau vide, sans World Partition [à vérifier]


def v_enregistrer_niveau():
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()


def v_acteurs_du_niveau():
    return list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())


def v_poser_maillage(sm, pos, lacet, label, dossier_outliner, ombre=True):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    a = eas.spawn_actor_from_object(sm, unreal.Vector(*pos), unreal.Rotator(roll=0.0, pitch=0.0, yaw=lacet))
    a.set_actor_label(label)
    a.set_folder_path(dossier_outliner)
    c = a.get_editor_property("static_mesh_component")
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    c.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    c.set_editor_property("cast_shadow", bool(ombre))
    return a


def v_poser_classe(classe, pos, label, dossier_outliner, rotation=(0.0, 0.0, 0.0)):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    a = eas.spawn_actor_from_class(classe, unreal.Vector(*pos), unreal.Rotator(roll=rotation[0], pitch=rotation[1], yaw=rotation[2]))
    a.set_actor_label(label)
    a.set_folder_path(dossier_outliner)
    return a


def v_composant_instances(acteur, nom, mesh):
    """Ajoute un HierarchicalInstancedStaticMeshComponent à un acteur vide (SubobjectDataSubsystem)."""
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    racine = sds.k2_gather_subobject_data_for_instance(acteur)[0]
    p = unreal.AddNewSubobjectParams(parent_handle=racine, new_class=unreal.HierarchicalInstancedStaticMeshComponent)
    h, raison = sds.add_new_subobject(p)
    if not raison.is_empty():
        raise RuntimeError(f"composant refusé : {raison}")
    sds.rename_subobject(h, unreal.Text(nom))
    comp = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h))
    comp.set_static_mesh(mesh)
    comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return comp


def v_regler_herbes(comp, distances_cm, ombre):
    """Réglages des herbes du jeu (relevés à Bollène) : disparition progressive avec la distance, pas d'ombre portée."""
    comp.set_cull_distances(int(distances_cm[0]), int(distances_cm[1]))
    comp.set_editor_property("cast_dynamic_shadow", bool(ombre))
    comp.set_editor_property("affect_distance_field_lighting", False)


def v_ajouter_instances(comp, transfos):
    comp.add_instances(transfos, False, True)          # (transforms, renvoyer les indices, espace monde)


def v_transfo(pos, lacet, echelle, tangage=0.0):
    return unreal.Transform(location=unreal.Vector(*pos), rotation=unreal.Rotator(roll=0.0, pitch=tangage, yaw=lacet),
                            scale=unreal.Vector(echelle, echelle, echelle))


def v_dossier_saved():
    return os.path.join(unreal.Paths.project_saved_dir(), "GrandCaunet")


# =====================================================================================================
# LOGIQUE (vérifiée hors d'Unreal avec le faux module)
# =====================================================================================================
def arguments():
    ap = argparse.ArgumentParser(prog="construire_niveau.py")
    ap.add_argument("--manifeste", default=os.path.join(KIT, "echantillon", "manifeste.json"))
    ap.add_argument("--etendue", choices=["E3", "E4", "complet"], default="E3")
    ap.add_argument("--mire", action="store_true")
    ap.add_argument("--parent", choices=["secours", "jeu"], default="secours")
    ap.add_argument("--placement")
    ap.add_argument("--sans-instances", action="store_true")
    ap.add_argument("--sans-eclairage", action="store_true")
    ap.add_argument("--seulement-assets", action="store_true")
    ap.add_argument("--max-instances", type=int, default=10 ** 9)
    ap.add_argument("--quitter", action="store_true", help="ferme l'éditeur à la fin (lancement par -ExecutePythonScript)")
    ap.add_argument("--niveau", help="chemin /Game/... du niveau à construire, à la place de celui du manifeste")
    return ap.parse_args(sys.argv[1:])


class Construction:
    def __init__(self, a):
        self.a = a
        self.man = json.load(open(a.manifeste, encoding="utf-8"))
        self.base = os.path.dirname(os.path.abspath(a.manifeste))
        self.el = [e for e in self.man["elements"] if a.etendue in e["essais"] or a.etendue == "complet"]
        self.par_nom = {e["nom"]: e for e in self.man["elements"]}
        self.rapport = {"manifeste": a.manifeste, "etendue": a.etendue, "debut": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "textures": 0, "maillages": 0, "variantes": 0, "acteurs": 0, "instances": 0,
                        "verdicts_bornes": {"conformes": 0, "differents": []}, "alertes": []}
        self.rapport.update({"variantes_sur_le_modele_du_jeu": 0, "reliefs_plats_ajoutes": 0, "instances_reattribuees": 0})
        # variante du jeu qui remplace M_Simple comme parent (voir l'en-tête, point 4)
        self.modele = None
        ffile = os.path.join(KIT, "factices.json")
        if os.path.exists(ffile):
            with open(ffile, encoding="utf-8") as f:
                self.modele = next((x["objet"] for x in json.load(f)["factices"] if x.get("role") == "modele_m_simple"), None)
        # variantes du jeu prises comme parent de certaines de nos variantes (factices.json, "role": "parent_du_jeu") :
        # la nôtre n'y règle rien, elle hérite de tout (asphalte de Bollène pour l'enrobé, par exemple)
        self.parents_du_jeu = {}
        if os.path.exists(ffile):
            with open(ffile, encoding="utf-8") as f:
                for x in json.load(f)["factices"]:
                    if x.get("role") == "parent_du_jeu":
                        for nom in x.get("pour", []):
                            self.parents_du_jeu[nom] = x["objet"]
        self.rapport["variantes_sur_un_materiau_du_jeu"] = 0
        self._relief_plat = None
        self.placement = self.origine_ir = None
        if a.placement:
            self.placement = json.load(open(a.placement, encoding="utf-8"))["placement"]
            racine = os.path.abspath(os.path.join(KIT, "..", ".."))
            self.origine_ir = json.load(open(os.path.join(racine, "export", "stage_ir", "grand_caunet", "stage.json"),
                                             encoding="utf-8"))["coordinates"]["origin"]
            self.rep = R.charger_repere()
            # le sol « façon jeu » est découpé d'après le placement : le paquet et la pose doivent utiliser le même
            sol = self.man.get("sol", {}).get("placement")
            if sol:
                ecart = max(abs(sol[k] - self.placement[k]) for k in ("theta_deg", "cx", "cz", "tx", "dy", "tz"))
                if ecart > 0.005:
                    self.alerte(f"le paquet a été découpé avec un autre placement que --placement (écart {ecart:.3f}) : "
                                f"relancer outils/relever_placement.py puis scripts/16_paquet_unreal.py")

    def alerte(self, msg):
        self.rapport["alertes"].append(msg)
        v_journal(msg, "alerte")

    def fichier(self, e):
        return os.path.normpath(os.path.join(self.base, *e["fichier"].split("/")))

    # --- sélection : seuls les textures et matériaux utilisés par les maillages retenus ---
    def selection(self):
        # maillages posés (avec acteur) et modèles d'instances fabriqués par le paquet (pierres calcaires : importés,
        # jamais posés seuls, désignés ensuite par des groupes d'instances)
        mesh = [e for e in self.el if e["type"] == "StaticMesh" and (e.get("acteur") or e.get("modele_d_instances"))]
        mats = {e["materiau"] for e in mesh if e.get("materiau")}
        mi = [self.par_nom[m] for m in sorted(mats) if m in self.par_nom]
        tex = sorted({t for m in mi for t in m["parametres_texture"].values()})
        return [self.par_nom[t] for t in tex if t in self.par_nom], mi, mesh

    # --- mire d'axes ---
    def mire(self):
        res = {}
        for e in self.man["elements"]:
            if e["type"] == "StaticMesh" and e.get("mire"):
                sm = self.importer_maillage(e, controler=False)
                lo, hi = v_bornes_maillage(sm)
                L = e["mire"]["longueur_m"] * 100.0
                for k in range(3):
                    if abs(hi[k] - L) < 5:
                        res[e["mire"]["axe_fichier"]] = (k, +1)
                    elif abs(-lo[k] - L) < 5:
                        res[e["mire"]["axe_fichier"]] = (k, -1)
        if len(res) != 3:
            raise RuntimeError(f"mire illisible : {res}")
        if "T_GC_MireRelief" in self.par_nom:            # contrôle à l'œil de la convention des reliefs
            self.importer_texture(self.par_nom["T_GC_MireRelief"])
            v_journal("ouvrir T_GC_MireRelief (dossier Mire) : moitié haute violacée, moitié basse verdâtre = convention "
                      "DirectX attendue par Unreal ; voir LISEZMOI_PAQUET.md")
        lignes = [""] * 3
        for axe, (k, s) in res.items():
            lignes[k] = ("-" if s < 0 else "") + axe
        valeur = ",".join(lignes)
        attendu = self.man["repere"]["axes_import_glb"]["valeur"]
        self.rapport["mire"] = {"valeur_mesuree": valeur, "valeur_du_paquet": attendu}
        if valeur != attendu:
            v_journal(f"AXES DIFFÉRENTS : l'importeur donne « {valeur} », le paquet suppose « {attendu} ». "
                      f"Corriger le paquet : python pc/etape2_unreal/outils/reaxer_paquet.py \"{self.a.manifeste}\" --axes {valeur} "
                      f"(ou refaire le paquet : python scripts/16_paquet_unreal.py --axes {valeur}), puis relancer ce script.",
                      "erreur")
            return False
        v_journal(f"axes de l'importeur conformes au paquet ({valeur})")
        return True

    # --- textures ---
    def importer_texture(self, e):
        chemin = e["chemin_ue"]
        if not v_existe(chemin):
            v_dossier(e["destination"])
            v_importer_fichier(self.fichier(e), e["destination"], e["nom"])
        tex = v_charger(chemin)
        if tex is None:
            self.alerte(f"texture non importée : {chemin}")
            return None
        v_regler_texture(tex, e["import"])
        v_enregistrer(chemin)
        self.rapport["textures"] += 1
        return tex

    # --- maillages ---
    def importer_maillage(self, e, controler=True):
        chemin = e["chemin_ue"]
        if not v_existe(chemin):
            tampon = f"{self.man['chemins'].get('editeur_seulement', self.man['chemins']['racine'])}/_Import/{e['nom']}"
            v_dossier(tampon)
            crees = v_importer_fichier(self.fichier(e), tampon, e["nom"])
            sm = None
            for p in crees or v_lister(tampon):          # repli : ce qui est arrivé dans le dossier tampon
                o = v_charger(p)
                if o is not None and o.get_class().get_name() == "StaticMesh":
                    sm = p
            if sm is None:
                raise RuntimeError(f"{e['fichier']} : aucun StaticMesh importé ({crees})")
            v_dossier(e["destination"])
            unreal.EditorAssetLibrary.rename_asset(sm, chemin)
            for p in v_lister(tampon):                     # matériaux ou textures créés par l'importeur
                v_supprimer(p)
            unreal.EditorAssetLibrary.delete_directory(tampon)
        sm = v_charger(chemin)
        v_regler_maillage(sm)
        sec = v_nom_section(sm)
        if sec != e["section_materiau"]:
            self.alerte(f"{e['nom']} : section « {sec} » au lieu de « {e['section_materiau']} » (sans conséquence)")
        if controler:
            self.controle_bornes(e, sm)
        v_enregistrer(chemin)
        self.rapport["maillages"] += 1
        return sm

    def controle_bornes(self, e, sm):
        lo, hi = v_bornes_maillage(sm)
        b = e["bornes_locales_cm"]
        ecart = max(max(abs(x - y) for x, y in zip(lo, b["min"])), max(abs(x - y) for x, y in zip(hi, b["max"])))
        if ecart <= TOL_BORNES_CM:
            self.rapport["verdicts_bornes"]["conformes"] += 1
        else:
            self.rapport["verdicts_bornes"]["differents"].append({"maillage": e["nom"], "ecart_cm": round(ecart, 1),
                                                                   "importe": [lo, hi], "attendu": b})
            v_journal(f"{e['nom']} : REPÈRE DIFFÉRENT (écart {ecart:.0f} cm) ; lancer --mire", "erreur")

    # --- matériaux ---
    def parent(self, e):
        """(parent, paramètres de texture, vrai si le parent est la variante modèle du jeu)"""
        if self.a.parent == "jeu" and e.get("parent_du_jeu"):
            # variante du jeu nommée par le paquet (sol « façon jeu ») : la nôtre y règle ses textures et ses nombres
            if v_existe(e["parent_du_jeu"]):
                self.rapport["variantes_sur_un_materiau_du_jeu"] += 1
                return v_charger(e["parent_du_jeu"]), e["parametres_texture"], False
            self.alerte(f"{e['nom']} : parent du jeu {e['parent_du_jeu']} absent (liste_factices.py puis creer_factices.py) ; secours")
            sec = self.man["materiau_secours"]
            return v_creer_materiau_secours(sec["chemin"], sec["parametres"]), e["parametres_secours"], False
        if self.a.parent == "jeu":
            special = self.parents_du_jeu.get(e["nom"])
            if special:
                if v_existe(special):
                    self.rapport["variantes_sur_un_materiau_du_jeu"] += 1
                    return v_charger(special), {}, False              # aucune texture réglée : tout est hérité
                self.alerte(f"{e['nom']} : parent du jeu {special} absent (creer_factices.py) ; variante modèle à la place")
            p = e["parent_jeu_pressenti"]
            if p == M_SIMPLE:
                if self.modele and v_existe(self.modele):
                    return v_charger(self.modele), e["parametres_texture"], True
                self.alerte(f"{e['nom']} : variante modèle du jeu absente (creer_factices.py) ; avec M_Simple pour parent, "
                            f"les textures ne s'afficheront pas en jeu (static switch inactifs, PROTOCOLE.md § 0 bis)")
            if v_existe(p):
                return v_charger(p), e["parametres_texture"], False
            self.alerte(f"{e['nom']} : parent du jeu {p} absent (creer_factices.py) ; secours")
        sec = self.man["materiau_secours"]
        return v_creer_materiau_secours(sec["chemin"], sec["parametres"]), e["parametres_secours"], False

    def relief_plat(self):
        """Texture de relief unie (128, 128, 255), créée une fois, dans le dossier des textures de matière du paquet :
        elle est livrée avec le décor, puisque nos variantes la désignent."""
        if self._relief_plat is None:
            modele = self.par_nom.get("T_GC_ORM_Sol") or next(
                (x for x in self.man["elements"] if x["type"] == "Texture2D" and x["nom"].startswith("T_GC_ORM")), None)
            dest = modele["destination"] if modele else self.man["chemins"]["racine"] + "/Materials/Textures"
            chemin = f"{dest}/{RELIEF_PLAT}"
            if not v_existe(chemin):
                d = v_dossier_saved()
                os.makedirs(d, exist_ok=True)
                fichier = os.path.join(d, RELIEF_PLAT + ".png")
                ligne = b"\x00" + bytes((128, 128, 255)) * 8

                def bloc(nom, donnees):
                    return struct.pack(">I", len(donnees)) + nom + donnees + struct.pack(">I", zlib.crc32(nom + donnees) & 0xFFFFFFFF)

                with open(fichier, "wb") as f:
                    f.write(b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0))
                            + bloc(b"IDAT", zlib.compress(ligne * 8)) + bloc(b"IEND", b""))
                v_dossier(dest)
                v_importer_fichier(fichier, dest, RELIEF_PLAT)
            tex = v_charger(chemin)
            if tex is None:
                self.alerte(f"relief plat non importé : {chemin}")
                return None
            v_regler_texture(tex, {"srgb": False, "compression": "TC_Normalmap", "groupe_lod": "TEXTUREGROUP_WorldNormalMap",
                                   "adressage": "Wrap", "mipmaps": "FromTextureGroup", "virtual_texture_streaming": False})
            v_enregistrer(chemin)
            self._relief_plat = tex
        return self._relief_plat

    def variante(self, e, textures):
        v_dossier(e["destination"])
        parent, params, sur_modele = self.parent(e)
        mi = v_creer_variante(e["nom"], e["destination"], parent)
        for p, t in params.items():
            if t in textures and textures[t] is not None:
                v_parametre_texture(mi, p, textures[t])
        if self.a.parent == "jeu" and e.get("parent_du_jeu") and v_existe(e["parent_du_jeu"]):
            for p, valeur in e.get("parametres_scalaires", {}).items():
                v_parametre_scalaire(mi, p, valeur)
        if self.a.parent == "jeu":
            # réglages posés sur un parent du jeu (matieres_du_jeu.json) : teintes, nombres, textures du jeu désignées
            # par leur chemin (/Game/..., un factice de texture doit exister à ce chemin : il n'est jamais livré)
            r = e.get("reglages_du_jeu") or {}
            for p, valeur in r.get("scalaires", {}).items():
                v_parametre_scalaire(mi, p, valeur)
            for p, valeur in r.get("vecteurs", {}).items():
                v_parametre_vecteur(mi, p, valeur)
            for p, chemin in r.get("textures", {}).items():
                if v_existe(chemin):
                    v_parametre_texture(mi, p, v_charger(chemin))
                else:
                    self.alerte(f"{e['nom']} : texture du jeu {chemin} absente (liste_factices.py puis creer_factices.py)")
            if r:
                self.rapport["variantes_reglees_sur_le_jeu"] = self.rapport.get("variantes_reglees_sur_le_jeu", 0) + 1
        if sur_modele:
            self.rapport["variantes_sur_le_modele_du_jeu"] += 1
            if PARAM_RELIEF not in params:
                plat = self.relief_plat()
                if plat is not None:
                    v_parametre_texture(mi, PARAM_RELIEF, plat)
                    self.rapport["reliefs_plats_ajoutes"] += 1
        v_enregistrer(e["chemin_ue"])
        self.rapport["variantes"] += 1
        return mi

    # --- placement ---
    def position(self, p_cm, lacet=0.0):
        """Mode propre : tel quel. Mode acrxs : repère physique du constructeur d'ACR Extra Stages."""
        if not self.placement:
            return tuple(p_cm), lacet
        rep = self.rep
        x = p_cm[0] / 100.0 + rep["x0"]
        y = rep["y0"] - p_cm[1] / 100.0
        z = p_cm[2] / 100.0 + rep["z0"]
        return R.l93_vers_unreal_acrxs(x, y, z, self.origine_ir, self.placement), lacet - self.placement["theta_deg"]

    def eclairage(self):
        if self.a.sans_eclairage:
            return
        noms = {a.get_actor_label() for a in v_acteurs_du_niveau()}
        for cls, label, rot in ((unreal.DirectionalLight, "GC_Soleil", (0.0, -35.0, 25.0)), (unreal.SkyLight, "GC_CielLumiere", (0, 0, 0)),
                                (unreal.SkyAtmosphere, "GC_Atmosphere", (0, 0, 0)), (unreal.ExponentialHeightFog, "GC_Brume", (0, 0, 0))):
            if label not in noms:
                v_poser_classe(cls, (0.0, 0.0, 20000.0), label, "GrandCaunet/Controle", rot)

    def instances(self):
        hfile = os.path.join(KIT, "hauteurs_maillages.json")
        hauteurs = json.load(open(hfile, encoding="utf-8")) if os.path.exists(hfile) else {}
        if not hauteurs:
            self.alerte("hauteurs_maillages.json absent : échelle 1 pour toutes les instances (PROTOCOLE.md E2)")
        # dimensions réelles des maillages du jeu, par dossier : permet de rechoisir le maillage de chaque plante
        vegetation = A.charger(KIT)
        if vegetation is None:
            self.alerte("releves/maillages_vegetation.json absent (outils/relever_jeu.py) : maillages du manifeste gardés, "
                        "dont des souches et des plaques de couvre-sol mises à l'échelle sur leur hauteur")
        reste = self.a.max_instances
        pk = self.man["essais"].get(self.a.etendue, {}).get("pk_m")
        groupes = {}                                   # (étiquette de l'acteur, chemin du maillage) -> transformations
        reglages = {}                                  # même clé -> élément du manifeste (distances de disparition, ombre)
        for e in self.el:
            if e["type"] != "InstanceGroup" or reste <= 0:
                continue
            dossier, nom_mesh = e["maillage_jeu"].rsplit("/", 1)
            prefixe = e["nom"][:-len(nom_mesh) - 1] if e["nom"].endswith("_" + nom_mesh) else e["nom"]
            candidats = (vegetation or {}).get(dossier)
            h_nat = hauteurs.get(nom_mesh) or e.get("hauteur_native_cm")
            with open(self.fichier(e), encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if pk and not (pk[0] <= float(r["pk_m"]) <= pk[1]):
                        continue
                    if reste <= 0:
                        break
                    p, lacet = self.position((float(r["x_cm"]), float(r["y_cm"]), float(r["z_cm"])), float(r["lacet_deg"]))
                    if r.get("echelle"):                       # échelle fixée par le paquet : maillage posé tel quel
                        choisi, s = nom_mesh, float(r["echelle"])
                    elif candidats:
                        diam = r.get("diametre_m") or r.get("diametre_houppier_m")
                        choisi, s = A.choisir(candidats, float(r["hauteur_voulue_m"]), float(diam) if diam else None,
                                              f"{e['nom']}:{r['id']}")
                        if choisi != nom_mesh:
                            self.rapport["instances_reattribuees"] += 1
                    else:
                        choisi = nom_mesh
                        s = float(r["hauteur_voulue_m"]) * 100.0 / h_nat if h_nat and h_nat >= A.PLAT_CM else 1.0
                    reglages[(f"{prefixe}_{choisi}", f"{dossier}/{choisi}")] = e
                    groupes.setdefault((f"{prefixe}_{choisi}", f"{dossier}/{choisi}"), []).append(
                        v_transfo(p, lacet, s, float(r.get("tangage_deg") or 0.0)))
                    reste -= 1
        for (label, chemin), transfos in sorted(groupes.items()):
            if not v_existe(chemin):
                self.alerte(f"{chemin} : factice absent (lancer creer_factices.py) ; {len(transfos)} instances de {label} ignorées")
                continue
            acteur = v_poser_classe(unreal.Actor, (0.0, 0.0, 0.0), label, "GrandCaunet/Vegetation")
            comp = v_composant_instances(acteur, f"HISM_{chemin.rsplit('/', 1)[1]}", v_charger(chemin))
            el = reglages.get((label, chemin), {})
            if el.get("distances_de_disparition_cm"):
                v_regler_herbes(comp, el["distances_de_disparition_cm"], el.get("ombre_dynamique", True))
            v_ajouter_instances(comp, transfos)
            self.rapport["instances"] += len(transfos)
            v_journal(f"{label} : {len(transfos)} instances")

    def executer(self):
        a = self.a
        if a.mire and not self.mire():
            return self.fin()
        tex_el, mi_el, mesh_el = self.selection()
        v_journal(f"{a.etendue} : {len(tex_el)} textures, {len(mi_el)} variantes, {len(mesh_el)} maillages")
        textures = {e["nom"]: self.importer_texture(e) for e in tex_el}
        variantes = {e["nom"]: self.variante(e, textures) for e in mi_el}
        maillages = {}
        for e in mesh_el:
            sm = self.importer_maillage(e)
            if e.get("materiau") in variantes:
                v_affecter_materiau(sm, variantes[e["materiau"]])
                v_enregistrer(e["chemin_ue"])
            maillages[e["nom"]] = sm
        if not a.seulement_assets:
            # --niveau : voie hybride, le niveau prend le chemin d'une cellule de Hafren South (PROTOCOLE.md § 0 quater)
            niveau = a.niveau or self.man["essais"][a.etendue]["niveau"]
            v_ouvrir_ou_creer_niveau(niveau)
            deja = {x.get_actor_label() for x in v_acteurs_du_niveau()}
            for e in mesh_el:
                ac = e.get("acteur")
                if not ac or ac["label"] in deja:                  # modèle d'instances : pas d'acteur
                    continue
                p, lacet = self.position(ac["position_cm"], ac["rotation_deg"][2])
                famille = e["destination"].split("/")[-2]
                v_poser_maillage(maillages[e["nom"]], p, lacet, ac["label"], f"GrandCaunet/{famille}", ac.get("ombre_portee", True))
                self.rapport["acteurs"] += 1
            self.eclairage()
            if not a.sans_instances:
                self.instances()
            v_enregistrer_niveau()
        unreal.EditorAssetLibrary.save_directory(self.man["chemins"]["racine"], only_if_is_dirty=True, recursive=True)
        return self.fin()

    def fin(self):
        self.rapport["fin"] = time.strftime("%Y-%m-%d %H:%M:%S")
        d = v_dossier_saved()
        os.makedirs(d, exist_ok=True)
        f = os.path.join(d, f"construire_niveau_{self.a.etendue}.json")
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(self.rapport, fh, ensure_ascii=False, indent=1)
        vb = self.rapport["verdicts_bornes"]
        v_journal(f"terminé : {self.rapport['textures']} textures, {self.rapport['maillages']} maillages, "
                  f"{self.rapport['variantes']} variantes, {self.rapport['acteurs']} acteurs, {self.rapport['instances']} "
                  f"instances ; bornes : {vb['conformes']} REPÈRE CONFORME, {len(vb['differents'])} REPÈRE DIFFÉRENT ; "
                  f"{len(self.rapport['alertes'])} alertes ; rapport : {f}")
        return self.rapport


def main():
    a = arguments()
    if unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) is None:
        # Constaté le 11/11/2026 : en ligne de commande (UnrealEditor-Cmd -run=pythonscript), les sous-systèmes de
        # l'éditeur n'existent pas. Il faut l'éditeur complet :
        #   UnrealEditor.exe acr.uproject -ExecutePythonScript="...\construire_niveau.py --etendue E3 --mire --quitter"
        raise RuntimeError("sous-systèmes de l'éditeur absents : lancer ce script dans l'éditeur complet "
                           "(UnrealEditor.exe ... -ExecutePythonScript=\"...\"), pas avec -run=pythonscript")
    try:
        return Construction(a).executer()
    except Exception:
        # avec --quitter personne ne lit la console : l'erreur va dans un fichier à côté du rapport
        import traceback
        d = v_dossier_saved()
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"construire_niveau_{a.etendue}_erreur.txt"), "w", encoding="utf-8") as fh:
            fh.write(traceback.format_exc())
        raise
    finally:
        if a.quitter:
            unreal.SystemLibrary.quit_editor()


# Dans l'éditeur, « py fichier.py » exécute le fichier comme __main__ [à vérifier] ; on lance aussi main() si le nom
# diffère, sauf pendant l'essai hors d'Unreal (outils/essai_construire.py), qui l'appelle lui-même.
if __name__ == "__main__" or not os.environ.get("GC_ESSAI_HORS_UNREAL"):
    main()
