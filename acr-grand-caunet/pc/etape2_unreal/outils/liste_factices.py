"""Écrit pc/etape2_unreal/factices.json : la liste des éléments FACTICES à créer dans le projet Unreal « acr », au
chemin exact d'un élément du jeu. Un factice sert seulement à ce que nos éléments cuits désignent le bon chemin ; il
n'est JAMAIS livré (cuire_et_empaqueter.ps1 l'écarte avant l'empaquetage), et le jeu charge à sa place son propre
élément. Tous les chemins sont vérifiés présents dans le catalogue du jeu.

Depuis le 11/11/2026, la liste est complétée par les relevés faits sur le PC (outils/relever_jeu.py, dossier
releves/) quand ils existent : paramètres réels des matériaux maîtres, variante modèle de M_Simple, classe native de
chaque Blueprint, et maillages d'arbres réattribués selon leur hauteur (outils/reattribuer_arbres.py).

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


def arbres_utilises():
    """(famille, maillage) : d'après arbres_jeu.csv.gz (réattribué selon les hauteurs) s'il existe, sinon arbres.csv."""
    f = KIT / "arbres_jeu.csv.gz"
    if f.exists():
        lignes, col = csv.DictReader(gzip.open(f, "rt", encoding="utf-8")), "element_jeu"
    else:
        lignes, col = csv.DictReader(open(RACINE / "data" / "processed" / "arbres.csv", encoding="utf-8")), "element_jeu_propose"
    return sorted({(r["famille_jeu"], r[col]) for r in lignes}), f.exists()


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
    arbres, reattribues = arbres_utilises()

    liste = [materiau(M_SIMPLE, maitres, "E1b, E3")]
    if variantes and MODELE_M_SIMPLE in variantes:
        v = variantes[MODELE_M_SIMPLE]
        liste.append({"objet": MODELE_M_SIMPLE, "type": "MaterialInstanceConstant", "parent": v["parent"],
                      "role": "modele_m_simple", "static_switch": v["static_switch"],
                      "parametres_texture": sorted(v["textures"]), "essai": "E1b, E3",
                      "pourquoi": "parent de nos variantes : ses static switch de texture sont déjà actifs dans le jeu"})
    liste += [{"objet": f"/Game/{f}/{e}", "type": "StaticMesh", "essai": "E2, E4"} for f, e in arbres]
    liste += [materiau(o, maitres, "E3") for o in AUTRES_MATERIAUX]
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
                                  "releves_du_pc": bool(maitres), "arbres_reattribues": reattribues,
                                  "factices": liste}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(liste)} factices ({len(arbres)} maillages d'arbres ; relevés du PC : {'oui' if maitres else 'non'}) -> {SORTIE}")


if __name__ == "__main__":
    main()
