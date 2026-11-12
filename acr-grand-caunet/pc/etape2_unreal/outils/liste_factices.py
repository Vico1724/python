"""Écrit pc/etape2_unreal/factices.json : la liste des éléments FACTICES à créer dans le projet Unreal « acr », au
chemin exact d'un élément du jeu. Un factice sert seulement à ce que nos éléments cuits désignent le bon chemin ; il
n'est JAMAIS livré (cuire_et_empaqueter.ps1 l'écarte avant l'empaquetage), et le jeu charge à sa place son propre
élément. Tous les chemins sont vérifiés présents dans le catalogue du jeu.

Depuis le 11/11/2026, la liste est complétée par les relevés faits sur le PC (outils/relever_jeu.py, dossier
releves/) quand ils existent : paramètres réels des matériaux maîtres, variante modèle de M_Simple, classe native de
chaque Blueprint, et tous les maillages des dossiers de végétation utilisés (scripts_editeur/attribution.py choisit
parmi eux, à l'import, un maillage à la taille de chaque plante).

Usage : python pc/etape2_unreal/outils/liste_factices.py   (quelques secondes)
"""
import csv
import gzip
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
KIT = Path(__file__).resolve().parents[1]
CATALOGUE = RACINE / "data" / "reference" / "catalogue_jeu_25170642.txt.gz"
SORTIE = KIT / "factices.json"
RELEVES = KIT / "releves"

M_SIMPLE = "/Game/Materials/General/Masters/M_Simple"
# Sans relevés : noms lus dans la configuration d'ACR Extra Stages (config/visuals.toml, [dr2_textures]).
M_SIMPLE_SANS_RELEVE = {"parametres_texture": ["Simple_BaseColor_Texture", "Simple_OcclRoughMet_Texture", "Simple_Normal_Texture"]}
# Variante du jeu qui sert de PARENT à nos variantes de M_Simple. M_Simple n'échantillonne ses textures que si les
# static switch « Simple_Use_*_Texture » sont actifs, et ils ne le sont pas par défaut ; une variante qui les active
# elle-même exigerait des programmes d'affichage absents du jeu. MI_SisteronConcrete01 les a déjà actifs (couleur,
# normale, occlusion, rugosité, métal), comme 311 autres variantes du jeu : nos variantes en héritent sans rien
# recompiler. C'est aussi le modèle retenu par ACR Extra Stages (config/visuals.toml, mic_template).
MODELE_M_SIMPLE = "/Game/Environments/MonteCarloS2Sisteron/TileableMaterials/MI_SisteronConcrete01"
# Variantes du jeu prises comme parent de certaines de nos variantes, à la place de la variante modèle de M_Simple
# (essais « matériaux du jeu », PROTOCOLE.md § 0 quinquies). "pour" : noms de nos variantes dans le manifeste.
# Notre variante n'y règle RIEN : elle hérite des textures et des static switch de la variante du jeu.
PARENTS_DU_JEU = [
    {"objet": "/Game/Environments/MonteCarloS1Bollene/AsphaltMaterial/MI_BolleneAsphalt1",
     "parent": "/Game/Environments/RallyShared/Materials/M_AsphaltMaster_Adv", "pour": ["MI_GC_Enrobe"],
     "pourquoi": "asphalte de Bollène : plaqué d'après la position dans le monde (static switch UseWSPlanarUV), donc "
                 "indépendant du dépliage de nos maillages ; fissures, traces de pneus, taches d'huile"},
    {"objet": "/Game/Environments/MonteCarloS1Bollene/TerrainMaterial/MI_MonteCarloS1BolleneTerrainFirstChild",
     "parent": "/Game/Environments/RallyShared/Materials/M_TerrainMaster_light", "pour": [],
     "pourquoi": "terrain de Bollène : paillis, aiguilles de pin, herbe haute, herbe sèche, terre et cailloux déjà "
                 "actifs. Parent des variantes MI_Sol_* du paquet (scripts/16_paquet_unreal.py --sol jeu), qui le "
                 "désignent elles-mêmes (\"parent_du_jeu\") et n'y règlent que leurs deux masques, la carte de couleur "
                 "et son cadrage"},
]
# Maillages du jeu posés tels quels par le paquet (scripts/16_paquet_unreal.py, glissières). "bornes_cm" : bornes
# réelles lues dans le jeu, données au cube factice pour que les instances ne soient pas éliminées trop tôt.
MAILLAGES_POSES = {
    "/Game/Props/Guardrails/MetalGuardrailA/SM_MetalGuardrailASimpleBegin": {"min": [-60, -40, 0], "max": [420, 0, 80]},
    "/Game/Props/Guardrails/MetalGuardrailA/SM_MetalGuardrailASimpleCenter": {"min": [-20, -30, 0], "max": [420, 0, 70]},
    "/Game/Props/Guardrails/MetalGuardrailA/SM_MetalGuardrailASimpleEnd": {"min": [-20, -40, 0], "max": [460, 0, 80]},
    # herbes des bas-côtés : leurs dimensions sont dans releves/maillages_vegetation.json
    "/Game/Foliage/GroundCover/DryGrass04/SM_Drygrass04": None, "/Game/Foliage/GroundCover/DryGrass05/SM_Drygrass05": None,
    "/Game/Foliage/GroundCover/DryGrass06/SM_Drygrass06": None, "/Game/Foliage/GroundCover/WildGrass/SM_WildGrass05": None,
    "/Game/Foliage/GroundCover/WildGrass/SM_WildGrass03": None,
    # buissons : attribution.py choisit parmi les quatre d'après la taille de chaque arbuste
    "/Game/Foliage/GroundCover/Willow/SM_Willow_01": None, "/Game/Foliage/GroundCover/Willow/SM_Willow_03a": None,
    "/Game/Foliage/GroundCover/Willow/SM_Willow_03b": None, "/Game/Foliage/GroundCover/Willow/SM_Willow_04a": None,
}
AUTRES_MATERIAUX = ["/Game/Environments/RallyShared/Materials/M_TerrainMaster_light",
                    "/Game/Environments/RallyShared/Materials/M_RoadSurface_Layered",
                    "/Game/Environments/RallyShared/Materials/M_AsphaltMaster_Adv"]
# Classes Blueprint des acteurs indispensables (docs/acr-stage-anatomy.md d'ACR Extra Stages, § 4) : un factice de
# Blueprint exige une classe parente native du jeu, qui manque à notre projet (PROTOCOLE.md, E2, « classes du jeu »).
BLUEPRINTS = ["/Game/Data/Environments/Common/BC_TrackAvatar", "/Game/Data/Gameplay/SceneManagement/BC_PhysicsAvatar",
              "/Game/Data/Gameplay/SceneManagement/BC_PlayerStartsManager", "/Game/Data/Gameplay/General/BC_GameMode",
              "/Game/Data/Gameplay/Triggers/BC_StartSequenceTrigger", "/Game/Data/Gameplay/Triggers/BC_EndSequenceTrigger",
              "/Game/Data/Gameplay/Triggers/BC_CompleStartTargetPoint", "/Game/Data/Cameras/Common/BC_PostRaceCamera",
              "/Game/Data/Gameplay/SceneManagement/BC_WeatherActor", "/Game/Data/Gameplay/SceneManagement/BC_DynamicSurfaceManager",
              "/Game/Data/Environments/Common/BC_DMSky_Montecarlo_Bollene"]


def fichier(objet):
    return "acr/Content/" + objet[len("/Game/"):] + ".uasset"


def releve(nom):
    f = RELEVES / nom
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def maillages_utilises():
    """Chemins /Game/... des maillages du jeu que nos instances peuvent désigner : arbres, arbustes, piquets.

    Avec le relevé releves/maillages_vegetation.json : TOUS les maillages des dossiers utilisés, parce que
    scripts_editeur/attribution.py choisit à l'import, dans le dossier, un maillage à la taille de chaque plante.
    Sans relevé : seulement les maillages nommés dans arbres.csv et arbustes.csv.gz."""
    donnees = RACINE / "data" / "processed"
    paires = {(r["famille_jeu"], r["element_jeu_propose"]) for r in csv.DictReader(open(donnees / "arbres.csv", encoding="utf-8"))}
    if (donnees / "arbustes.csv.gz").exists():
        paires |= {(r["famille_jeu"], r["element_jeu_propose"]) for r in csv.DictReader(gzip.open(donnees / "arbustes.csv.gz", "rt", encoding="utf-8"))}
    veg = (releve("maillages_vegetation.json") or {}).get("dossiers")
    chemins = {f"/Game/{f}/{e}" for f, e in paires}
    if veg:
        for f in {f for f, _ in paires}:
            chemins |= {f"/Game/{f}/{n}" for n in veg.get(f"/Game/{f}", {})}
    if (donnees / "balisage.csv").exists():                       # piquets de rubalise (scripts/16_paquet_unreal.py)
        chemins |= {"/Game/" + r["maillage_jeu_propose"][len("acr/Content/"):] for r in csv.DictReader(open(donnees / "balisage.csv", encoding="utf-8"))
                    if r.get("type") == "piquet de rubalise" and r.get("maillage_jeu_propose", "").startswith("acr/Content/")}
    return sorted(c[:-len(".uasset")] if c.endswith(".uasset") else c for c in chemins), bool(veg)


def materiau(objet, maitres, essai):
    x = {"objet": objet, "type": "Material", "essai": essai}
    m = (maitres or {}).get(objet)
    if m:
        x["parametres_texture"] = sorted(m["textures"])
        x["parametres_scalaires"] = sorted(m["scalaires"])
        x["parametres_vecteur"] = sorted(m["vecteurs"])
        x["static_switch"] = dict(sorted(m["static_switch"].items()))      # nom -> valeur par défaut dans le jeu
        x["releve"] = "releves/materiaux_maitres.json (valeurs par défaut, textures par défaut)"
    elif objet == M_SIMPLE:
        x.update(M_SIMPLE_SANS_RELEVE, parametres_scalaires=[])
    else:
        x.update(parametres_texture=[], parametres_scalaires=[], a_completer="paramètres à lire sur le PC : outils/relever_jeu.py")
    return x


def main():
    cat = {l.strip() for l in gzip.open(CATALOGUE, "rt", encoding="utf-8")}
    maitres = (releve("materiaux_maitres.json") or {}).get("maitres")
    variantes = (releve("variantes.json") or {}).get("variantes")
    acteurs = (releve("acteurs.json") or {}).get("blueprints")
    maillages, par_dossier = maillages_utilises()

    liste = [materiau(M_SIMPLE, maitres, "E1b, E3")]
    if variantes and MODELE_M_SIMPLE in variantes:
        v = variantes[MODELE_M_SIMPLE]
        liste.append({"objet": MODELE_M_SIMPLE, "type": "MaterialInstanceConstant", "parent": v["parent"],
                      "role": "modele_m_simple", "static_switch": v["static_switch"],
                      "parametres_texture": sorted(v["textures"]), "essai": "E1b, E3",
                      "pourquoi": "parent de nos variantes : ses static switch de texture sont déjà actifs dans le jeu"})
    liste += [{"objet": c, "type": "StaticMesh", "essai": "E2, E4"} for c in maillages]
    deja = {x["objet"] for x in liste}
    liste += [{"objet": c, "type": "StaticMesh", "essai": "maillages du jeu posés tels quels", **({"bornes_cm": b} if b else {})}
              for c, b in MAILLAGES_POSES.items() if c not in deja]
    liste += [materiau(o, maitres, "E3") for o in AUTRES_MATERIAUX]
    liste += [{"objet": p["objet"], "type": "MaterialInstanceConstant", "parent": p["parent"], "role": "parent_du_jeu",
               "pour": p["pour"], "static_switch": {}, "essai": "E3b", "pourquoi": p["pourquoi"]} for p in PARENTS_DU_JEU]
    for o in BLUEPRINTS:
        a = (acteurs or {}).get(o)
        x = {"objet": o, "type": "Blueprint", "parent": a["classe_native"] if a else None, "essai": "E2"}
        if a:
            x["lignee"] = a["lignee"]
        if not x["parent"]:
            x["a_completer"] = ("classe native non trouvée (parent dans une extension du moteur) : voir lignee"
                                if a else "classe parente native du jeu : outils/relever_jeu.py")
        liste.append(x)
    absents = [x["objet"] for x in liste if fichier(x["objet"]) not in cat]
    if absents:
        raise SystemExit(f"absents du catalogue : {absents}")
    SORTIE.write_text(json.dumps({"description": __doc__.strip().splitlines()[0],
                                  "releves_du_pc": bool(maitres), "tous_les_maillages_des_dossiers": par_dossier,
                                  "factices": liste}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(liste)} factices ({len(maillages)} maillages de végétation et de balisage ; relevés du PC : "
          f"{'oui' if maitres else 'non'}) -> {SORTIE}")


if __name__ == "__main__":
    main()
