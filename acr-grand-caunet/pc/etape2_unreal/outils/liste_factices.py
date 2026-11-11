"""Écrit pc/etape2_unreal/factices.json : la liste des éléments FACTICES à créer dans le projet Unreal « acr », au
chemin exact d'un élément du jeu. Un factice sert seulement à ce que nos éléments cuits désignent le bon chemin ; il
n'est JAMAIS livré (outils/filtrer_cuisson.py le retire avant l'empaquetage), et le jeu charge à sa place son propre
élément. Tous les chemins sont vérifiés présents dans le catalogue du jeu.

Usage : python3 pc/etape2_unreal/outils/liste_factices.py   (quelques secondes)
"""
import csv
import gzip
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
CATALOGUE = RACINE / "data" / "reference" / "catalogue_jeu_25170642.txt.gz"
SORTIE = Path(__file__).resolve().parents[1] / "factices.json"

# Matériau « simple » du jeu : noms de paramètres lus dans la configuration d'ACR Extra Stages (config/visuals.toml,
# [dr2_textures] mic_base_texture... et StageVerify.cs « Simple_BaseColor_Texture ») [déduit de leur code].
M_SIMPLE = {"objet": "/Game/Materials/General/Masters/M_Simple", "type": "Material",
            "parametres_texture": ["Simple_BaseColor_Texture", "Simple_OcclRoughMet_Texture", "Simple_Normal_Texture"],
            "parametres_scalaires": [], "essai": "E1b, E3"}
# Les autres parents (M_TerrainMaster_light, M_RoadSurface_Layered, M_AsphaltMaster_Adv, M_SpeedTree) ne sont listés
# qu'avec leur chemin : leurs paramètres doivent être lus sur le PC (PROTOCOLE.md, E3) avant de créer leur factice.
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


def main():
    cat = {l.strip() for l in gzip.open(CATALOGUE, "rt", encoding="utf-8")}
    arbres = sorted({(r["famille_jeu"], r["element_jeu_propose"]) for r in csv.DictReader(open(RACINE / "data" / "processed" / "arbres.csv"))})
    liste = [M_SIMPLE]
    liste += [{"objet": f"/Game/{f}/{e}", "type": "StaticMesh", "essai": "E2, E4"} for f, e in arbres]
    liste += [{"objet": o, "type": "Material", "parametres_texture": [], "parametres_scalaires": [], "essai": "E3",
               "a_completer": "paramètres à lire sur le PC avant création"} for o in AUTRES_MATERIAUX]
    liste += [{"objet": o, "type": "Blueprint", "parent": None, "essai": "E2",
               "a_completer": "classe parente native du jeu : voir PROTOCOLE.md E2"} for o in BLUEPRINTS]
    absents = [x["objet"] for x in liste if fichier(x["objet"]) not in cat]
    if absents:
        raise SystemExit(f"absents du catalogue : {absents}")
    SORTIE.write_text(json.dumps({"description": __doc__.strip().splitlines()[0], "factices": liste}, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    print(f"{len(liste)} factices ({len(arbres)} maillages d'arbres) -> {SORTIE}")


if __name__ == "__main__":
    main()
