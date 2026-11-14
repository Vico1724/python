"""Relève dans les fichiers du jeu installé tout ce que le protocole de l'étape 2 demandait de lire « sur le PC » :
hauteurs des maillages d'arbres, paramètres des matériaux maîtres, variantes du jeu utilisables comme parents,
réglages des textures, classes natives des acteurs de niveau. Ne modifie rien dans le jeu : il lit des exports JSON
produits par acr-ref (outil d'ACR Extra Stages, construit par l'étape 1) sur la vue « d'origine » des archives.

EXÉCUTÉ sur le PC du directeur le 11/11/2026 (jeu 25170642). Python ordinaire, sans dépendance.

Usage (depuis la racine du dépôt) :
    python pc/etape2_unreal/outils/relever_jeu.py              # exporte si besoin, puis écrit les relevés
    python pc/etape2_unreal/outils/relever_jeu.py --exporter   # refait les exports (après une mise à jour du jeu)

Écrit :
    pc/etape2_unreal/hauteurs_maillages.json      {"SM_AleppoPine14": 1041.4, ...} en cm (sans les plaques de couvre-sol)
    pc/etape2_unreal/releves/maillages_arbres.json
    pc/etape2_unreal/releves/maillages_vegetation.json   lu par scripts_editeur/attribution.py
    pc/etape2_unreal/releves/materiaux_maitres.json
    pc/etape2_unreal/releves/variantes.json
    pc/etape2_unreal/releves/textures.json
    pc/etape2_unreal/releves/acteurs.json
    pc/etape2_unreal/releves/niveau_hote.json
Les exports bruts restent hors du dépôt, dans <travail>\\unreal\\lu (exports : 91 Mo ; niveau_hafren : 565 Mo).
"""
import argparse
import collections
import json
import re
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
RACINE = Path(__file__).resolve().parents[3]
RELEVES = KIT / "releves"

# Ce qu'on exporte (expressions régulières sur les chemins de paquets, comme acr-ref list).
FILTRES = [
    r"^acr/Content/.*/(M|MI)_[^/]+\.uasset$",                                        # matériaux et variantes
    r"/BC_[^/]+\.uasset$",                                                           # Blueprints d'acteurs
    r"^acr/Content/Foliage/.*/SM_[^/]+\.uasset$",                                    # arbres, arbustes, couvre-sols
    r"^acr/Content/(Environments/(MonteCarlo[^/]*|RallyShared)/.*|Props/RallyProps/Gantries/|Materials/PhotoMode/"
    r"Textures/|Effects/Vehicles/Skid/)T_[^/]+\.uasset$",                            # textures utiles
    r"^acr/Content/Props/RallyProps/Gantries/SM_[^/]+\.uasset$",                     # portiques (essai E1b)
]
MAITRES = ["/Game/Materials/General/Masters/M_Simple",
           "/Game/Environments/RallyShared/Materials/M_TerrainMaster_light",
           "/Game/Environments/RallyShared/Materials/M_RoadSurface_Layered",
           "/Game/Environments/RallyShared/Materials/M_AsphaltMaster_Adv"]
# Rubriques de elements_jeu_utiles.json dont on détaille les variantes.
RUBRIQUES_VARIANTES = ["asphalte_bollene", "asphalte_sisteron", "terrain_monte_carlo_materiaux", "glissieres_bornes",
                       "portiques_rallye", "murs_parapets_ponts"]
VARIANTES_EN_PLUS = [  # modèles retenus par ACR Extra Stages (config/visuals.toml) et matériaux de Hafren de l'étape 1
    "/Game/Environments/MonteCarloS2Sisteron/TileableMaterials/MI_SisteronConcrete01",
    "/Game/Environments/WalesS4HafrenSouth/TerrainMaterialInstances/MI_Terrain9MatBlend1001",
    "/Game/Environments/WalesS4HafrenSouth/GravelMaterial/MI_WalesS4HafrenSouthGravelRoad1"]
TEXTURES_EN_PLUS = ["/Game/Props/RallyProps/Gantries/T_RallyGantryWales_B", "/Game/Materials/PhotoMode/Textures/T_Dirt",
                    "/Game/Effects/Vehicles/Skid/T_SkidDebug_N"]
# Classes du moteur : leurs propriétés ne sont pas recopiées dans acteurs.json (seulement leur nombre).
CLASSES_MOTEUR = {"Object", "Actor", "Info", "GameModeBase", "GameMode", "TriggerBase", "TriggerBox", "TargetPoint",
                  "CameraActor", "ActorComponent", "SceneComponent", "PrimitiveComponent", "Volume", "Brush"}


def objet_de(fichier, exports):
    """Z:\\...\\exports\\acr\\Content\\A\\B.uasset.json -> /Game/A/B"""
    rel = fichier.relative_to(exports).as_posix()[:-len(".uasset.json")]
    return "/Game/" + rel[len("acr/Content/"):]


def fichier_de(objet, exports):
    return exports / ("acr/Content/" + objet[len("/Game/"):] + ".uasset.json")


def lire(objet, exports):
    f = fichier_de(objet, exports)
    return json.loads(f.read_text(encoding="utf-8-sig")) if f.exists() else None


def chemin(ref):
    """{"ObjectName": "Texture2D'T_X'", "ObjectPath": "/Game/A/T_X.0"} -> /Game/A/T_X"""
    if not ref:
        return None
    if "AssetPathName" in ref:
        return ref["AssetPathName"].rsplit(".", 1)[0] or None
    return ref["ObjectPath"].rsplit(".", 1)[0]


def nom_objet(ref):
    m = re.match(r"^[^']*'(.*)'$", ref["ObjectName"]) if ref else None
    return m.group(1) if m else None


def exporter(a):
    a.exports.mkdir(parents=True, exist_ok=True)
    for f in FILTRES:
        r = subprocess.run([str(a.acr_ref), "export-many", "--filter", f, "--out", str(a.exports), "--game", str(a.vue),
                            "--usmap", str(a.usmap)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        print("  ", (r.stdout.strip().splitlines() or [r.stderr.strip()])[-1])
        if r.returncode != 0:
            raise SystemExit(f"acr-ref export-many en échec pour {f}\n{r.stderr}")


# --- maillages -------------------------------------------------------------------------------------------------------
def maillages(exports):
    arbres = {}
    for f in sorted((exports / "acr/Content/Foliage/Trees").rglob("SM_*.uasset.json")):
        j = json.loads(f.read_text(encoding="utf-8-sig"))
        sm = next((o for o in j if o.get("Type") == "StaticMesh"), None)
        if not sm:
            continue
        p = sm["Properties"]
        b = p.get("ExtendedBounds")
        if not b:
            continue
        lods = (sm.get("RenderData") or {}).get("LODs") or []
        arbres[sm["Name"]] = {
            "objet": objet_de(f, exports),
            "haut_cm": round(b["Origin"]["Z"] + b["BoxExtent"]["Z"], 1),      # au-dessus du pivot (pied de l'arbre)
            "bas_cm": round(b["Origin"]["Z"] - b["BoxExtent"]["Z"], 1),       # négatif : racines sous le pivot
            "demi_largeur_cm": round(max(b["BoxExtent"]["X"], b["BoxExtent"]["Y"]), 1),
            "centre_xy_cm": [round(b["Origin"]["X"], 1), round(b["Origin"]["Y"], 1)],
            "niveaux_de_detail": len(lods),
            "triangles_par_niveau": [sum(s.get("NumTriangles", 0) for s in l.get("Sections") or []) for l in lods],
            "materiaux": [chemin(m.get("MaterialInterface")) for m in p.get("StaticMaterials") or []],
        }
    return arbres


def vegetation(exports):
    """Tous les maillages de Foliage, par dossier : {"/Game/Foliage/Trees/AleppoPine": {"SM_AleppoPine01": [haut, largeur]}}
    en cm. haut = sommet au-dessus du pivot ; largeur = plus grande dimension horizontale. Lu par
    scripts_editeur/attribution.py pour choisir un maillage à la taille de chaque plante."""
    out = collections.defaultdict(dict)
    for f in sorted((exports / "acr/Content/Foliage").rglob("SM_*.uasset.json")):
        sm = next((o for o in json.loads(f.read_text(encoding="utf-8-sig")) if o.get("Type") == "StaticMesh"), None)
        b = ((sm or {}).get("Properties") or {}).get("ExtendedBounds")
        if b:
            out[objet_de(f, exports).rsplit("/", 1)[0]][sm["Name"]] = [
                round(b["Origin"]["Z"] + b["BoxExtent"]["Z"], 1), round(2 * max(b["BoxExtent"]["X"], b["BoxExtent"]["Y"]), 1)]
    return dict(out)


# --- matériaux -------------------------------------------------------------------------------------------------------
def charger_materiaux(exports):
    mats = {}
    for f in exports.rglob("*.uasset.json"):
        n = f.name[:-len(".uasset.json")]
        if not n.startswith(("M_", "MI_")):
            continue
        for o in json.loads(f.read_text(encoding="utf-8-sig")):
            if o.get("Type") in ("Material", "MaterialInstanceConstant") and o.get("Name") == n:
                mats[objet_de(f, exports)] = o
                break
    return mats


def parametres_maitre(o):
    """Paramètres d'un matériau maître, avec leurs valeurs par défaut, lus dans CachedExpressionData."""
    c = o.get("CachedExpressionData") or {}

    def noms(i):
        e = c.get("RuntimeEntries" if i == 0 else f"RuntimeEntries[{i}]") or {}
        return [p["Name"] for p in e.get("ParameterInfoSet") or []]

    def couple(i, valeurs, conv=lambda v: v):
        v = c.get(valeurs) or []
        return {n: (conv(v[k]) if k < len(v) else None) for k, n in enumerate(noms(i))}

    return {
        "scalaires": couple(0, "ScalarValues"),
        "vecteurs": couple(1, "VectorValues", lambda v: [v["R"], v["G"], v["B"], v["A"]]),
        "textures": couple(3, "TextureValues", chemin),
        "textures_virtuelles_runtime": couple(5, "RuntimeVirtualTextureValues", chemin),
        "static_switch": couple(8, "StaticSwitchValues"),
        "ecrit_dans_une_texture_virtuelle_runtime": c.get("bHasRuntimeVirtualTextureOutput"),
        "couches_de_materiaux": c.get("bHasMaterialLayers"),
        "collections_de_parametres": [chemin(x.get("ParameterCollection")) for x in c.get("ParameterCollectionInfos") or []],
    }


def reglages_variante(o):
    """Ce qu'une variante (MaterialInstanceConstant) règle elle-même, sans ce qu'elle hérite."""
    p = o.get("Properties") or {}

    def liste(cle):
        v = p.get(cle)
        return v if isinstance(v, list) else ([v] if v else [])

    sw = (p.get("StaticParametersRuntime") or {}).get("StaticSwitchParameters") or []
    if isinstance(sw, dict):
        sw = [sw]
    return {
        "parent": chemin(p.get("Parent")),
        "textures": {x["ParameterInfo"]["Name"]: chemin(x.get("ParameterValue")) for x in liste("TextureParameterValues")},
        "scalaires": {x["ParameterInfo"]["Name"]: x.get("ParameterValue") for x in liste("ScalarParameterValues")},
        "vecteurs": {x["ParameterInfo"]["Name"]: [x["ParameterValue"][k] for k in "RGBA"] for x in liste("VectorParameterValues")
                     if isinstance(x.get("ParameterValue"), dict)},
        "static_switch": {x["ParameterInfo"]["Name"]: x["Value"] for x in sw if x.get("bOverride", True)},
        "permutation_propre": bool(p.get("bHasStaticPermutationResource")),
        "surface_physique": nom_objet(p.get("PhysMaterial")),
        "reglages_de_base": p.get("BasePropertyOverrides") or {},
    }


def lignee(objet, mats):
    """[objet, parent, grand-parent, ..., matériau maître]"""
    out = [objet]
    while True:
        o = mats.get(out[-1])
        if o is None or o["Type"] == "Material":
            return out
        par = chemin((o.get("Properties") or {}).get("Parent"))
        if not par or par in out:
            return out
        out.append(par)


def switchs_effectifs(objet, mats, maitres):
    """Valeur de chaque static switch pour une variante : défaut du maître, puis réglages de la lignée (du haut vers le bas)."""
    l = lignee(objet, mats)
    racine = l[-1]
    if racine not in maitres:
        maitres[racine] = parametres_maitre(mats[racine]) if racine in mats else {"static_switch": {}}
    v = dict(maitres[racine]["static_switch"])
    for x in reversed(l[:-1]):
        v.update(reglages_variante(mats[x])["static_switch"])
    return racine, v


# --- textures --------------------------------------------------------------------------------------------------------
def texture(objet, exports):
    j = lire(objet, exports)
    t = next((o for o in j or [] if o.get("Type", "").startswith("Texture")), None)
    if not t:
        return None
    p = dict(t.get("Properties") or {})
    for k in ("LightingGuid", "AssetImportData", "ImportedSize"):
        p.pop(k, None)
    return {"classe": t["Type"], "largeur": t.get("SizeX"), "hauteur": t.get("SizeY"), "format": t.get("PixelFormat"),
            "mips": len(t.get("Mips") or []), "premier_mip_en_ligne": t.get("FirstMipToSerialize"),
            "reglages_non_par_defaut": p}


# --- acteurs ---------------------------------------------------------------------------------------------------------
def classe_blueprint(objet, exports):
    """Remonte d'un Blueprint à sa classe native : [("BC_X_C", "/Game/.../BC_X"), ..., ("TrackAvatar", "/Script/dmphysics")]"""
    out, premiers = [], []
    while objet:
        j = lire(objet, exports)
        g = next((o for o in j or [] if o.get("Type") == "BlueprintGeneratedClass"), None)
        if not g:
            out.append((None, objet + " (non exporté)"))
            return out, premiers

        def porteur(o):
            x = o.get("Outer")
            return (nom_objet(x) or "") if isinstance(x, dict) else (x or "")

        comps = [{"nom": o["Name"], "classe": o["Type"]} for o in j
                 if o["Name"].endswith("_GEN_VARIABLE") or porteur(o).startswith("Default__")]
        if not out:
            premiers = comps
        out.append((g["Name"], objet))
        s = g.get("SuperStruct") or g.get("Super")
        if not s:
            return out, premiers
        if s["ObjectPath"].startswith("/Script/"):
            out.append((nom_objet(s), s["ObjectPath"]))
            return out, premiers
        objet = chemin(s)
    return out, premiers


def schema(a, classes):
    """acr-ref schema : ordre des propriétés (sérialisation sans versions). {classe: [(indice, propriétaire, nom, type)]}"""
    r = subprocess.run([str(a.acr_ref), "schema", *classes, "--usmap", str(a.usmap)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out, cur = {}, None
    for l in r.stdout.splitlines():
        if l.startswith("== "):
            cur = l[3:].strip()
            out[cur] = []
            continue
        m = re.match(r"^\s*(\d+)\s+([^.\s]+)\.(.+?) : (.+)$", l)
        if m and cur:
            out[cur].append((int(m.group(1)), m.group(2), m.group(3), m.group(4)))
    return out


# --- niveau hôte -----------------------------------------------------------------------------------------------------
NIVEAU = r"^acr/Content/Levels/WalesS4HafrenSouth(\.umap|/_Generated_/[^/]+\.umap)$"


def niveau_hote(a):
    """Acteurs de Hafren South (niveau persistant + cellules) : combien de chaque classe, et, pour les acteurs
    uniques (un ou deux exemplaires : ce sont les acteurs « de jeu »), quelles propriétés le studio a réglées."""
    d = a.travail / "unreal" / "lu" / "niveau_hafren"
    if a.exporter or not d.exists():
        d.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(a.acr_ref), "export-many", "--filter", NIVEAU, "--out", str(d), "--game", str(a.vue),
                        "--usmap", str(a.usmap)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    compte, exemples = collections.Counter(), collections.defaultdict(list)
    for f in sorted(d.rglob("*.json")):
        persistant = "_Generated_" not in f.as_posix()
        for o in json.loads(f.read_text(encoding="utf-8-sig")):
            x = o.get("Outer")
            porteur = (nom_objet(x) or "") if isinstance(x, dict) else (x or "")
            if not porteur.endswith("PersistentLevel"):
                continue                                              # on ne garde que les acteurs
            compte[o["Type"]] += 1
            if len(exemples[o["Type"]]) < 2:
                p = o.get("Properties") or {}
                exemples[o["Type"]].append({
                    "nom": o["Name"], "dans": "niveau persistant" if persistant else "cellule " + f.name.split(".")[0],
                    "proprietes_reglees": {k: (v if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False)[:160])
                                           for k, v in p.items()}})
    return {"niveau": "/Game/Levels/WalesS4HafrenSouth", "fichiers": len(list(d.rglob("*.json"))),
            "acteurs_par_classe": dict(compte.most_common()),
            "acteurs_uniques": {t: exemples[t] for t, c in sorted(compte.items()) if c <= 2}}


def ecrire(nom, donnees, dossier=RELEVES):
    dossier.mkdir(parents=True, exist_ok=True)
    f = dossier / nom
    f.write_text(json.dumps(donnees, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"  {f.relative_to(RACINE).as_posix()} ({f.stat().st_size // 1024} Ko)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--travail", type=Path, default=Path(r"Z:\acrxs"))
    ap.add_argument("--exporter", action="store_true", help="refaire les exports même s'ils existent")
    a = ap.parse_args()
    a.acr_ref = a.travail / "bin" / "acr-ref" / "acr-ref.exe"
    a.vue = a.travail / "construction" / "vanilla"
    a.usmap = next((a.travail / "mappings").glob("acr_*.usmap"), None)
    a.exports = a.travail / "unreal" / "lu" / "exports"
    for f in (a.acr_ref, a.vue, a.usmap):
        if not f or not Path(f).exists():
            raise SystemExit(f"introuvable : {f} (faire d'abord l'étape 1, pc/LISEZMOI.md)")
    if a.exporter or not a.exports.exists():
        print("exports :")
        exporter(a)
    source = {"jeu": "Assetto Corsa Rally", "version_de_construction": a.usmap.stem.split("_")[-1],
              "outil": "acr-ref export-many (ACR Extra Stages) sur la vue d'origine, sans mods ni BioBio"}
    elements = json.loads((KIT / "elements_jeu_utiles.json").read_text(encoding="utf-8"))["rubriques"]
    factices = json.loads((KIT / "factices.json").read_text(encoding="utf-8"))["factices"]
    print("relevés :")

    # 1. maillages d'arbres
    arbres = maillages(a.exports)
    ecrire("maillages_arbres.json", {"source": source, "unite": "cm, repère du maillage (pivot au pied)", "maillages": arbres})
    veg = vegetation(a.exports)
    ecrire("maillages_vegetation.json", {"source": source, "unite": "cm : [haut au-dessus du pivot, plus grande largeur]",
            "lecture": "lu par scripts_editeur/attribution.py ; un dossier dont tous les maillages font moins de 30 cm de "
                       "haut est un couvre-sol en plaques", "dossiers": veg})
    # hauteurs seules, pour les scripts qui calculent une échelle hauteur voulue / hauteur du maillage : les plaques de
    # couvre-sol (moins de 30 cm) en sont exclues, cette échelle n'ayant pas de sens pour elles
    ecrire("hauteurs_maillages.json", {n: v[0] for d in sorted(veg) for n, v in sorted(veg[d].items()) if v[0] >= 30}, KIT)

    # 2. matériaux maîtres
    mats = charger_materiaux(a.exports)
    maitres = {m: parametres_maitre(mats[m]) for m in MAITRES}
    racines = collections.Counter(lignee(k, mats)[-1] for k, o in mats.items() if o["Type"] == "MaterialInstanceConstant")
    for m in MAITRES:
        maitres[m]["variantes_dans_le_jeu"] = racines[m]
    ecrire("materiaux_maitres.json", {"source": source, "lecture": "valeurs par défaut du matériau ; static_switch : "
            "une variante qui en change un exige des programmes d'affichage que le jeu n'a pas forcément", "maitres": maitres})

    # 3. variantes
    choisies = list(VARIANTES_EN_PLUS)
    for r in RUBRIQUES_VARIANTES:
        choisies += [e["objet"].rsplit(".", 1)[0] for e in elements[r]["elements"]]
    variantes = {}
    for v in dict.fromkeys(choisies):
        o = mats.get(v)
        if o is None or o["Type"] != "MaterialInstanceConstant":
            continue
        d = reglages_variante(o)
        l = lignee(v, mats)
        d["lignee"] = l[1:]
        racine, sw = switchs_effectifs(v, mats, maitres)
        d["static_switch_actifs"] = sorted(k for k, x in sw.items() if x)
        variantes[v] = d
    # familles de variantes de M_Simple : même jeu de static switch actifs = mêmes programmes d'affichage dans le jeu
    familles = collections.defaultdict(list)
    for k, o in mats.items():
        if o["Type"] == "MaterialInstanceConstant" and lignee(k, mats)[-1] == MAITRES[0]:
            _, sw = switchs_effectifs(k, mats, maitres)
            base = (o.get("Properties") or {}).get("BasePropertyOverrides") or {}
            cle = (tuple(sorted(n for n, x in sw.items() if x)), json.dumps(base, sort_keys=True))
            familles[cle].append(k)
    fam = [{"static_switch_actifs": list(c[0]), "reglages_de_base": json.loads(c[1]), "nombre": len(v), "exemples": sorted(v)[:6]}
           for c, v in sorted(familles.items(), key=lambda kv: -len(kv[1]))]
    ecrire("variantes.json", {"source": source,
            "lecture": "pour chaque variante : ce qu'elle règle elle-même ; static_switch_actifs = état complet après héritage",
            "familles_de_M_Simple": fam, "variantes": variantes})

    # 4. textures : celles des variantes relevées, des rubriques de textures, et les modèles
    tex = set(TEXTURES_EN_PLUS)
    for d in variantes.values():
        tex |= {t for t in d["textures"].values() if t and t.startswith("/Game/")}
    for r in ("terrain_textures_monte_carlo", "asphalte_textures_monte_carlo"):
        tex |= {e["objet"].rsplit(".", 1)[0] for e in elements[r]["elements"]}
    textures = {t: texture(t, a.exports) for t in sorted(tex)}
    non_lues = sorted(t for t, v in textures.items() if v is None)
    ecrire("textures.json", {"source": source, "non_exportees": non_lues,
            "textures": {t: v for t, v in textures.items() if v}})

    # 5. acteurs : classe native de chaque Blueprint factice, composants, ordre des propriétés
    bps = [x["objet"] for x in factices if x["type"] == "Blueprint"]
    bps += [e["objet"].rsplit(".", 1)[0] for e in elements["portiques_rallye"]["elements"] if "/BC_" in e["objet"]]
    acteurs, natives = {}, set()
    for b in dict.fromkeys(bps):
        l, comps = classe_blueprint(b, a.exports)
        nat = l[-1] if l and l[-1][1].startswith("/Script/") else None
        acteurs[b] = {"classe_native": f"{nat[1]}.{nat[0]}" if nat else None,
                      "lignee": [f"{p}.{n}" if n else p for n, p in l], "composants": comps}
        if nat:
            natives.add(nat[0])
    sch = schema(a, sorted(natives))
    ordre = {}
    for c, props in sch.items():
        par = collections.OrderedDict()
        for i, proprio, nom, typ in props:
            par.setdefault(proprio, []).append([i, nom, typ])
        ordre[c] = {"nombre_de_proprietes": len(props),
                    "classes_dans_l_ordre": [{"classe": k, "nombre": len(v), "premier_indice": v[0][0]} for k, v in par.items()],
                    "proprietes_hors_moteur": {k: v for k, v in par.items() if k not in CLASSES_MOTEUR}}
    ecrire("acteurs.json", {"source": source,
            "lecture": "ordre = indice de sérialisation sans versions (acr-ref schema) ; une classe souche doit déclarer "
                       "ses propriétés dans cet ordre", "blueprints": acteurs, "ordre_des_proprietes": ordre})

    # 6. niveau hôte : ce qu'un niveau du jeu contient (repère pour l'essai E2)
    niv = niveau_hote(a)
    ecrire("niveau_hote.json", {"source": source, "lecture": "acteurs_uniques = acteurs présents une ou deux fois dans "
            "Hafren South, avec les propriétés que le studio a réglées (valeurs longues coupées à 160 caractères)", **niv})
    print(f"{len(arbres)} maillages, {len(variantes)} variantes, {len(textures) - len(non_lues)} textures, {len(acteurs)} acteurs, "
          f"{sum(niv['acteurs_par_classe'].values())} acteurs de niveau")


if __name__ == "__main__":
    main()
