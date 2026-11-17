"""Extrait du catalogue du jeu (data/reference/catalogue_jeu_25170642.txt.gz) les éléments utiles au décor provençal,
rangés par rubrique, avec leur chemin complet. Écrit pc/etape2_unreal/elements_jeu_utiles.json.

Seuls des noms présents dans le catalogue sont écrits (le catalogue ne contient que des NOMS de fichiers : rien sur
leur contenu, leurs dimensions ou leurs paramètres). Chemins donnés sous deux formes :
  fichier : acr/Content/Foliage/Trees/AleppoPine/SM_AleppoPine01.uasset (tel que dans les archives)
  objet   : /Game/Foliage/Trees/AleppoPine/SM_AleppoPine01.SM_AleppoPine01 (tel qu'Unreal le désigne)

Usage : python3 pc/etape2_unreal/outils/extraire_elements.py   (quelques secondes, aucune dépendance)
"""
import gzip
import json
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
CATALOGUE = RACINE / "data" / "reference" / "catalogue_jeu_25170642.txt.gz"
SORTIE = Path(__file__).resolve().parents[1] / "elements_jeu_utiles.json"

# rubrique -> (explication, motif sur le chemin de fichier)
RUBRIQUES = {
    "arbres_pin_alep": ("pin d'Alep (55 % de nos arbres) : maillages, matériaux, types de feuillage",
                        r"Foliage/Trees/AleppoPine/(SM_|MI_|FT_)"),
    "arbres_substitut_chene_vert": ("substituts retenus pour le chêne vert : arbre à perruque, érable noir de Monte-Carlo",
                                    r"Foliage/Trees/(Smoketree|BlackmapleMonteCarlo)/(SM_|MI_|FT_)"),
    "arbres_substitut_chene_pubescent": ("substitut retenu pour le chêne pubescent : érable noir",
                                         r"Foliage/Trees/Blackmaple/(SM_|MI_|FT_)"),
    "arbres_autres_provencaux": ("pin noir de Monte-Carlo (pins pignon / maritime), cyprès, olivier, figuier, lyciet, haies",
                                 r"Foliage/Trees/(BlackpineMonteCarlo|Cypress|CypressWildMonteCarlo|Olivetree|Fig|Boxthorn|Hedge)/SM_"),
    "arbres_destructibles": ("versions destructibles (pin d'Alep et autres)", r"Foliage/DestructibleTrees/"),
    "couvre_sol_sec": ("herbes sèches, genêt rampant, feuilles mortes, herbes sauvages, couvre-sol grec",
                       r"Foliage/GroundCover/(DryGrass\d+|BroomCreeper|DeadLeaves|FallenLeaf|WildGrass|Greece|Citrus|FlowerPlant01)/"),
    "types_de_feuillage": ("types de feuillage (FoliageType) génériques", r"Foliage/FoliageTypes/"),
    "asphalte_bollene": ("variantes de matériaux d'asphalte et de bas-côté de Bollène (Monte-Carlo S1)",
                         r"Environments/MonteCarloS1Bollene/AsphaltlMaterialInstances/"),
    "asphalte_sisteron": ("variantes de matériaux d'asphalte de Sisteron (Monte-Carlo S2)",
                          r"Environments/MonteCarloS2Sisteron/AsphaltMaterialInstances/"),
    "asphalte_textures_monte_carlo": ("textures d'asphalte et de décalques partagées de Monte-Carlo",
                                      r"Environments/MonteCarloShared/(AsphaltTextures|DecalsTextures)/"),
    "asphalte_alsace": ("matériau et textures d'asphalte d'Alsace (autre asphalte français)",
                        r"Environments/AlsaceShared/(AsphaltMaterial|AsphaltTextures)/"),
    "terrain_monte_carlo_materiaux": ("variantes de matériaux de terrain (une par dalle) et maillages de terrain de Bollène / Sisteron",
                                      r"Environments/MonteCarloS[12]\w+/(TerrainMaterialInstances|TerrainMaterial|MeshesTerrain)/"),
    "terrain_textures_monte_carlo": ("textures de sol de Monte-Carlo : terre, herbe sèche, aiguilles de pin, cailloux...",
                                     r"Environments/MonteCarloShared/(TerrainTextures|TrimTextures|TrimMaterials|TileableMaterialsTextures)/"),
    "materiaux_maitres": ("matériaux maîtres (parents) du jeu : ne pas les livrer, seulement leur faire des variantes",
                          r"(Materials/General/Masters/|Environments/RallyShared/Materials/)"),
    "fonctions_materiaux_terrain": ("fonctions de matériaux de terrain (pour comprendre le mélange de 9 couches)",
                                    r"Environments/RallyShared/MaterialFunctions/MF_Terrain"),
    "murs_parapets_ponts": ("murs de pierre, murs de soutènement, ponts, murs de ville de Monte-Carlo",
                            r"Props/MonteCarloProps/(MonBolStoneWallsA|MonBolRetainers|MonSisRetainers|MonSisWalls|MonBolBridges|MonSisBridges|MonBolTownWalls)/SM_"),
    "rochers_falaises": ("parois rocheuses, falaises et blocs de Monte-Carlo",
                         r"Props/MonteCarloProps/(MonBolRockfaces|MonSisRockfaces|MonSisCliffs|MonSisBoulders)/SM_"),
    "glissieres_bornes": ("glissières métal et bois, bornes plastique", r"Props/(Guardrails/|AlsaceProps/(SaverneCityGuardrailA|BollardPlasticC)/)"),
    "panneaux_francais": ("panneaux routiers et publicités français (Monte-Carlo, Alsace), panneaux de rallye",
                          r"Props/(MonteCarloSignage|AlsaceSignage/FraSaverneSignage|RallyProps/Signs)/"),
    "rubalise_piquets": ("rubalise sur piquets et acteur de ruban", r"(Props/RallyProps/TapePlasticPoleA/|BC_NarrowTapeActor|Props/RallyProps/SafetyNetting/)"),
    "portiques_rallye": ("portiques de départ et d'arrivée", r"Props/RallyProps/Gantries/"),
    "ciel_meteo": ("ciels (Blueprints dmsky) et réglages météo, dont Monte-Carlo",
                   r"(Data/Environments/Common/(BC_)?DMSky|dmenvironment/Content/dmsky/Blueprints/BC_DMSky|Data/Weather/Configs/|DT_WeatherConfigurations)"),
    "surfaces_physiques": ("matériaux physiques (adhérence, parois) et leur registre", r"Data/Gameplay/PhysicalMaterials/"),
    "acteurs_de_niveau": ("classes Blueprint des acteurs qu'une spéciale doit contenir (docs/acr-stage-anatomy.md d'ACR Extra Stages)",
                          r"(BC_TrackAvatar|BC_PhysicsAvatar|BC_PlayerStartsManager|BC_GameMode\.|BC_StartSequenceTrigger|BC_EndSequenceTrigger|BC_CompleStartTargetPoint|BC_PostRaceCamera|BC_WeatherActor\.|BC_DynamicSurfaceManager|BC_SplineMeshRepeatCollisions|BC_RefuelZoneTargetPoint)"),
    "tables_menus_et_notes": ("tables de menus (registre) et de notes du copilote",
                              r"(Data/Database/Main/(DA_DBMain|Common/DT_Levels|TrackSelection/DT_Tracks|TrackSelection/DT_TracksVariants\.|TrackSelection/DT_TracksLocations)|Data/Pacenote/Config/|Data/Pacenote/Tables/DT_Pacenote(Bollene|Sisteron)Full)"),
    "niveaux_et_donnees_physiques": ("niveaux du jeu et leurs données physiques cuites (BakedData)",
                                     r"(^acr/Content/Levels/[^/]+\.umap$|BakedData)"),
    "visuel_proche_essai_E1": ("éléments anodins et visibles au départ de Hafren South, pour la preuve de chargement E1",
                               r"Props/RallyProps/Gantries/(SM_RallyGantry8m|T_RallyGantryWales_B|MI_RallyGantryWales|BC_GantryWales)"),
}


def objet(chemin):
    p = chemin
    for a, b in (("acr/Content/", "/Game/"), ("Engine/Plugins/darkmatter/dmenvironment/Content/", "/dmenvironment/"),
                 ("Engine/Content/", "/Engine/")):
        if p.startswith(a):
            p = b + p[len(a):]
            break
    p = re.sub(r"\.(uasset|umap)$", "", p)
    return f"{p}.{p.rsplit('/', 1)[1]}"


def main():
    noms = [l.strip() for l in gzip.open(CATALOGUE, "rt", encoding="utf-8")]
    actifs = [n for n in noms if n.endswith((".uasset", ".umap"))]
    out = {"source": "data/reference/catalogue_jeu_25170642.txt.gz (Assetto Corsa Rally, build 25170642, UE 5.6.1)",
           "attention": "noms seulement : dimensions, paramètres et parents des matériaux sont à lire sur le PC (FModel ou acr-ref export)",
           "rubriques": {}}
    for cle, (expl, motif) in RUBRIQUES.items():
        rx = re.compile(motif)
        sel = sorted(n for n in actifs if rx.search(n))
        out["rubriques"][cle] = {"explication": expl, "nombre": len(sel),
                                 "elements": [{"fichier": n, "objet": objet(n)} for n in sel]}
        print(f"{cle:36s} {len(sel):5d}")
    SORTIE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {SORTIE}")


if __name__ == "__main__":
    main()
