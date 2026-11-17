r"""Construit un niveau Unreal Engine 5 à partir d'un paquet carte-reelle-unreal (manifeste.json).

NON EXÉCUTÉ DANS UNREAL : écrit hors de l'éditeur, syntaxe vérifiée, et la partie sans éditeur
(lecture du manifeste et de la table, calcul des transformations) testée avec --essai en Python
ordinaire. Les appels à l'éditeur sont repris de scripts d'éditeur qui ont fonctionné avec Unreal
5.6.1 (import glb par AssetImportTask, bornes, matériaux simples, pose d'acteurs, composants
d'instances par SubobjectDataSubsystem) ; chacun est isolé dans une petite fonction pour corriger
en un endroit si une version de l'API diffère. Lire le rapport à chaque premier lancement.

Ce que fait le script :
  1. importe les maillages glb du paquet dans /Game/CarteReelle/<nom>/ et compare leurs bornes à
     celles du manifeste (verdict « REPÈRE CONFORME », sinon arrêt avant de poser quoi que ce soit) ;
  2. crée ou rouvre le niveau, retire les acteurs qu'il avait posés au lancement précédent (dossier
     d'acteurs « CarteReelle ») ;
  3. pose le lointain, les bâtiments, les routes ; et le terrain en maillage (terrain_proche.glb)
     tant qu'aucun Landscape n'est dans le niveau. Le Landscape lui-même n'a pas d'API Python
     d'import fiable d'une version à l'autre : le script écrit la consigne exacte (fichier, position,
     échelles), à suivre dans le mode Landscape, puis relancer le script avec --sans-terrain-maillage ;
  4. pose les arbres en instances (un composant HierarchicalInstancedStaticMesh par asset), d'après
     placements/arbres.csv et table_assets.csv (type -> asset ; par défaut des formes de base) ;
  5. éclairage de contrôle (soleil, ciel, atmosphère, brouillard) si le niveau est neuf ;
  6. enregistre le niveau et écrit <Projet>/Saved/CarteReelle/<nom>/rapport.json.

Utilisation, projet ouvert : Outils > Exécuter un script Python (le paquet est le dossier du script),
ou dans la console : py "C:\...\paquet_unreal\importer_paquet.py" --paquet "C:\...\paquet_unreal"
Options : --dossier-ue /Game/..., --niveau /Game/.../Niveau, --table fichier.csv, --sans-arbres,
  --sans-lointain, --sans-terrain-maillage, --sans-eclairage, --max-instances N, --seulement-assets
Hors d'Unreal : python importer_paquet.py --paquet DOSSIER --essai   (plan, sans rien modifier)
"""
import argparse
import csv
import json
import os
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
TOL_CM = 5.0                   # écart de bornes toléré à l'import (arrondis de l'importeur)
TOL_REL = 1e-5                 # et une part de la taille, pour les grands maillages (précision flottante)
DOSSIER_ACTEURS = "CarteReelle"
RAPPORT = {"alertes": [], "etapes": [], "consignes": []}
unreal = None                  # module de l'éditeur, importé seulement dans Unreal


def journal(msg, alerte=False):
    if unreal is not None:
        (unreal.log_warning if alerte else unreal.log)("[CarteReelle] " + msg)
    else:
        print(("ALERTE " if alerte else "") + msg)
    RAPPORT["alertes" if alerte else "etapes"].append(msg)


# ---------------------------------------------------------------- partie sans éditeur (testable)
def lire_manifeste(paquet):
    p = os.path.join(paquet, "manifeste.json")
    if not os.path.exists(p):
        raise SystemExit(f"manifeste.json introuvable dans {paquet} : donner --paquet")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def lire_table(chemin):
    """type -> réglages de l'asset ; lignes sans asset ignorées (types non posés)."""
    table = {}
    if not os.path.exists(chemin):
        return table
    with open(chemin, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("type") and (r.get("asset") or "").strip():
                table[r["type"].strip()] = {
                    "asset": r["asset"].strip(),
                    "h_ref": float(r.get("hauteur_ref_m") or 1.0),
                    "r_ref": float(r.get("rayon_ref_m") or 0.5),
                    "echelle": (r.get("echelle") or "uniforme").strip(),
                    "pivot_z_cm": float(r.get("pivot_z_cm") or 0.0),
                    "collision": (r.get("collision") or "non").strip().lower() in ("oui", "1", "true", "vrai"),
                }
    return table


def local_vers_unreal(x, y, z):
    """Repère local (m, est/nord/haut) -> Unreal (cm, X est, Y sud, Z haut)."""
    return x * 100.0, -y * 100.0, z * 100.0


def groupes_arbres(paquet, man, table, maximum):
    """{asset: {"collision": bool, "transfos": [(x, y, z, lacet, sx, sy, sz)], "types": set}} et types sans asset."""
    p = os.path.join(paquet, man["placements"]["arbres"]["fichier"])
    groupes, sans = {}, {}
    if not os.path.exists(p):
        return groupes, sans
    n = 0
    with open(p, encoding="utf-8") as f:
        for i, r in enumerate(csv.DictReader(f)):
            t = table.get(r["type"])
            if t is None:
                sans[r["type"]] = sans.get(r["type"], 0) + 1
                continue
            if n >= maximum:
                break
            h, ray = float(r["hauteur"]), float(r["rayon"])
            if t["echelle"] == "hauteur_rayon":
                sz = h / t["h_ref"]
                sx = sy = max(ray, 0.3) / t["r_ref"]
            else:
                sx = sy = sz = h / t["h_ref"]
            x, y, z = local_vers_unreal(float(r["x"]), float(r["y"]), float(r["z"]))
            lacet = (i * 137.508) % 360.0 - 180.0          # angle d'or : orientation variée et reproductible
            g = groupes.setdefault(t["asset"], {"collision": t["collision"], "transfos": [], "types": set()})
            g["transfos"].append((x, y, z + t["pivot_z_cm"] * sz, lacet, sx, sy, sz))
            g["types"].add(r["type"])
            n += 1
    return groupes, sans


def consigne_landscape(paquet, man):
    L = man["landscape"]
    e, c = L["echelle_cm"], L["position_centre_cm"]
    return (f"Landscape : mode Landscape > Manage > New > Import from File = {os.path.join(paquet, L['fichier'])} ; "
            f"Location X {c[0]} Y {c[1]} Z {c[2]} ; Scale X {e['x']} Y {e['y']} Z {e['z']} ; résolution "
            f"{L['taille_px']} x {L['taille_px']}. Texture : {L['texture']} (importée dans le dossier Textures). "
            "Puis relancer ce script avec --sans-terrain-maillage.")


def nom_court(asset):
    return asset.rsplit("/", 1)[-1].split(".")[0]


# ---------------------------------------------------------------- appels à l'éditeur, un par fonction
def EAL():
    return unreal.EditorAssetLibrary


def importer(fichier, dossier, nom):
    t = unreal.AssetImportTask()
    for k, v in (("filename", fichier), ("destination_path", dossier), ("destination_name", nom),
                 ("automated", True), ("replace_existing", True), ("save", True)):
        t.set_editor_property(k, v)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return [str(p) for p in t.get_editor_property("imported_object_paths")]


def trouver_maillage(chemins, dossier, nom):
    """L'importeur glb peut nommer le maillage d'après le nœud : on prend le premier StaticMesh créé."""
    cand = [f"{dossier}/{nom}"] + [p.split(".")[0] for p in chemins]
    for c in cand:
        if EAL().does_asset_exist(c):
            a = EAL().load_asset(c)
            if isinstance(a, unreal.StaticMesh):
                return a, c
    return None, None


def regler_maillage(sm, collision):
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    try:
        sub.remove_collisions(sm)
    except Exception:
        pass
    try:
        ns = sm.get_editor_property("nanite_settings")
        ns.set_editor_property("enabled", False)
        sm.set_editor_property("nanite_settings", ns)
    except Exception as e:
        journal(f"Nanite non réglé sur {sm.get_name()} ({e})", True)
    if collision == "complexe":
        try:
            bs = sm.get_editor_property("body_setup")
            bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        except Exception as e:
            journal(f"collision complexe refusée sur {sm.get_name()} ({e}) : à régler à la main "
                    "(Collision Complexity = Use Complex Collision As Simple)", True)


def bornes(sm):
    b = sm.get_bounding_box()
    return [b.min.x, b.min.y, b.min.z], [b.max.x, b.max.y, b.max.z]


def materiau_uni(chemin, rvb):
    MEL = unreal.MaterialEditingLibrary
    if EAL().does_asset_exist(chemin):
        return EAL().load_asset(chemin)
    dossier, nom = chemin.rsplit("/", 1)
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(nom, dossier, unreal.Material, unreal.MaterialFactoryNew())
    c = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -600, -200)
    c.set_editor_property("constant", unreal.LinearColor(rvb[0], rvb[1], rvb[2], 1.0))
    MEL.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -600, 100)
    r.set_editor_property("r", 0.9)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    EAL().save_asset(chemin, only_if_is_dirty=False)
    return m


def ouvrir_niveau(chemin):
    """Renvoie True si le niveau est neuf."""
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if EAL().does_asset_exist(chemin):
        les.load_level(chemin)
        eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        for a in list(eas.get_all_level_actors()):          # on retire ce que le script avait posé
            if a.get_folder_path() and str(a.get_folder_path()).startswith(DOSSIER_ACTEURS):
                eas.destroy_actor(a)
        return False
    les.new_level(chemin)
    return True


def landscape_present():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return any(isinstance(a, unreal.LandscapeProxy) for a in eas.get_all_level_actors())


def poser_maillage(sm, label, collision, ombre):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    a = eas.spawn_actor_from_object(sm, unreal.Vector(0, 0, 0), unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0))
    a.set_actor_label(label)
    a.set_folder_path(f"{DOSSIER_ACTEURS}/Decor")
    c = a.get_editor_property("static_mesh_component")
    if not collision:
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    c.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    c.set_editor_property("cast_shadow", bool(ombre))
    return a


def poser_classe(classe, pos, label, dossier, lacet=0.0, tangage=0.0):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    a = eas.spawn_actor_from_class(classe, unreal.Vector(*pos), unreal.Rotator(roll=0.0, pitch=tangage, yaw=lacet))
    a.set_actor_label(label)
    a.set_folder_path(dossier)
    return a


def composant_instances(acteur, nom, mesh, collision):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    racine = sds.k2_gather_subobject_data_for_instance(acteur)[0]
    h, raison = sds.add_new_subobject(unreal.AddNewSubobjectParams(
        parent_handle=racine, new_class=unreal.HierarchicalInstancedStaticMeshComponent))
    if not raison.is_empty():
        raise RuntimeError(f"composant refusé : {raison}")
    sds.rename_subobject(h, unreal.Text(nom))
    comp = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h))
    comp.set_static_mesh(mesh)
    if not collision:
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return comp


def eclairage():
    d = f"{DOSSIER_ACTEURS}/Eclairage"
    soleil = poser_classe(unreal.DirectionalLight, (0, 0, 20000), "Soleil", d, -60.0, -50.0)
    ciel = poser_classe(unreal.SkyLight, (0, 0, 20000), "Ciel", d)
    for act in (soleil, ciel):
        try:
            act.get_editor_property("light_component").set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        except Exception as e:
            journal(f"mobilité de {act.get_actor_label()} non réglée ({e})", True)
    try:
        ciel.get_editor_property("light_component").set_editor_property("real_time_capture", True)
    except Exception as e:
        journal(f"SkyLight : Real Time Capture non réglé ({e})", True)
    poser_classe(unreal.SkyAtmosphere, (0, 0, 0), "Atmosphere", d)
    poser_classe(unreal.ExponentialHeightFog, (0, 0, 0), "Brouillard", d)


# ---------------------------------------------------------------- déroulé
def arguments():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paquet", default=ICI, help="dossier du paquet (défaut : celui du script)")
    ap.add_argument("--dossier-ue", help="dossier de contenu (défaut : /Game/CarteReelle/<nom>)")
    ap.add_argument("--niveau", help="chemin du niveau (défaut : <dossier-ue>/<nom>)")
    ap.add_argument("--table", help="table type -> asset (défaut : <paquet>/table_assets.csv)")
    ap.add_argument("--sans-arbres", action="store_true")
    ap.add_argument("--sans-lointain", action="store_true")
    ap.add_argument("--sans-terrain-maillage", action="store_true")
    ap.add_argument("--sans-eclairage", action="store_true")
    ap.add_argument("--seulement-assets", action="store_true")
    ap.add_argument("--max-instances", type=int, default=10 ** 9)
    ap.add_argument("--essai", action="store_true", help="hors Unreal : affiche le plan sans rien modifier")
    return ap.parse_args(sys.argv[1:])


def essai(a, man, groupes, sans):
    print(f"paquet {man['nom']} : {len(man['maillages'])} maillages, {sum(len(g['transfos']) for g in groupes.values())} "
          f"instances en {len(groupes)} groupes, types sans asset : {sans or 'aucun'}")
    for m in man["maillages"]:
        print(f"  {m['nom']:18s} {m['fichier']:28s} bornes {m['bornes_cm']['min']} -> {m['bornes_cm']['max']}")
    for asset, g in sorted(groupes.items()):
        print(f"  {nom_court(asset):10s} {len(g['transfos']):6d} instances, ex. {tuple(round(v, 1) for v in g['transfos'][0])}")
    print("  " + consigne_landscape(a.paquet, man))


def main():
    global unreal
    a = arguments()
    a.paquet = os.path.abspath(a.paquet)
    man = lire_manifeste(a.paquet)
    table = lire_table(a.table or os.path.join(a.paquet, "table_assets.csv"))
    groupes, sans = groupes_arbres(a.paquet, man, table, a.max_instances) if not a.sans_arbres else ({}, {})
    if a.essai:
        return essai(a, man, groupes, sans)
    import unreal as _u
    unreal = _u
    t0 = time.time()
    nom = man["nom"]
    D = a.dossier_ue or f"/Game/CarteReelle/{nom}"
    niveau = a.niveau or f"{D}/{nom}"
    for d in (D, D + "/Maillages", D + "/Textures", D + "/Materiaux"):
        if not EAL().does_directory_exist(d):
            EAL().make_directory(d)

    # 1. maillages et contrôle du repère
    poses = []
    for m in man["maillages"]:
        if a.sans_lointain and m["role"] == "lointain":
            continue
        crees = importer(os.path.join(a.paquet, m["fichier"]), D + "/Maillages", m["nom"])
        sm, chemin = trouver_maillage(crees, D + "/Maillages", m["nom"])
        if sm is None:
            journal(f"{m['nom']} : import échoué ({m['fichier']}), objets créés : {crees}", True)
            continue
        regler_maillage(sm, m["collision"])
        lo, hi = bornes(sm)
        attendu = m["bornes_cm"]["min"] + m["bornes_cm"]["max"]
        taille = max(abs(v) for v in attendu) or 1.0
        ecart = max(abs(x - y) for x, y in zip(lo + hi, attendu))
        conforme = ecart <= max(TOL_CM, TOL_REL * taille)
        journal(f"{m['nom']} : {'REPÈRE CONFORME' if conforme else 'REPÈRE DIFFÉRENT'} (écart {ecart:.1f} cm ; "
                f"bornes {[round(v) for v in lo]} à {[round(v) for v in hi]})", not conforme)
        if not conforme:
            journal("Arrêt : l'importeur glb n'a pas placé les axes comme attendu (UE = 100 x (gX, gZ, gY)). "
                    "Vérifier les options d'import glTF (échelle, rotation) et renvoyer ce rapport.", True)
            return finir(t0, nom)
        if "couleur" in m:
            sm.set_material(0, materiau_uni(f"{D}/Materiaux/M_{m['nom'][3:]}", m["couleur"]))
        EAL().save_asset(chemin, only_if_is_dirty=False)
        poses.append((m, sm))
    tex = os.path.join(a.paquet, man["landscape"]["texture"])
    importer(tex, D + "/Textures", "T_OrthoTerrain")
    if a.seulement_assets:
        return finir(t0, nom)

    # 2-3. niveau et décor
    neuf = ouvrir_niveau(niveau)
    avec_landscape = landscape_present()
    for m, sm in poses:
        if m["role"] == "terrain_proche":
            if avec_landscape or a.sans_terrain_maillage:
                continue
            poser_maillage(sm, m["nom"], True, True)
            journal("terrain posé en maillage (pas de Landscape dans le niveau)")
        elif m.get("poser", True):
            poser_maillage(sm, m["nom"], m["collision"] != "aucune", m["ombre"])
    if not avec_landscape:
        RAPPORT["consignes"].append(consigne_landscape(a.paquet, man))
        journal(RAPPORT["consignes"][-1], True)
    if neuf and not a.sans_eclairage:
        eclairage()

    # 4. arbres en instances
    total = 0
    for t, n in sans.items():
        journal(f"type {t} : pas d'asset dans la table, {n} arbres non posés", True)
    for asset, g in sorted(groupes.items()):
        mesh = EAL().load_asset(asset) if EAL().does_asset_exist(asset) else None
        if mesh is None:
            journal(f"{asset} absent du projet : {len(g['transfos'])} arbres non posés", True)
            continue
        nc = nom_court(asset)
        act = poser_classe(unreal.Actor, (0, 0, 0), f"Arbres_{nc}", f"{DOSSIER_ACTEURS}/Vegetation")
        try:
            comp = composant_instances(act, f"HISM_{nc}", mesh, g["collision"])
        except Exception as e:
            journal(f"composant d'instances refusé pour {nc} ({e}) : utiliser l'outil Foliage", True)
            continue
        tr = [unreal.Transform(location=unreal.Vector(x, y, z), rotation=unreal.Rotator(roll=0.0, pitch=0.0, yaw=l),
                               scale=unreal.Vector(sx, sy, sz)) for x, y, z, l, sx, sy, sz in g["transfos"]]
        comp.add_instances(tr, False, True)
        total += len(tr)
        journal(f"{nc} : {len(tr)} arbres ({', '.join(sorted(g['types']))})")
    RAPPORT["instances"] = total

    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    journal(f"niveau enregistré : {niveau}")
    return finir(t0, nom)


def finir(t0, nom):
    RAPPORT["duree_s"] = round(time.time() - t0, 1)
    d = os.path.join(unreal.Paths.project_saved_dir(), "CarteReelle", nom)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "rapport.json"), "w", encoding="utf-8") as f:
        json.dump(RAPPORT, f, ensure_ascii=False, indent=1)
    journal(f"terminé en {RAPPORT['duree_s']} s, {len(RAPPORT['alertes'])} alerte(s) ; rapport : {d}")
    return RAPPORT


main()
