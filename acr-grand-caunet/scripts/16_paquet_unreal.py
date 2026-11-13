"""Étape 16 - Paquet prêt à importer dans Unreal Engine 5.6 (projet factice « acr », niveau GrandCaunet).

Tout ce qui peut être décidé, converti, découpé, nommé et vérifié hors de l'éditeur l'est ici : il ne reste
dans l'éditeur qu'à lancer pc/etape2_unreal/scripts_editeur/construire_niveau.py, piloté par le manifeste.

Entrées : modele/terrain_sol.glb + textures_sol/ (14), modele/lointain.glb (13), route_habillee.glb,
          ouvrages.glb (11), annexes.glb, balisage.glb (12), data/processed/arbres.csv, arbustes.csv.gz (10),
          balisage.csv (12), chaussee_precise.csv (07), modele/repere.json, data/reference/catalogue_jeu_*.txt.gz,
          pc/etape2_unreal/factices.json
Sorties : paquet_unreal/ (complet, non versionné) ou, avec --echantillon, pc/etape2_unreal/echantillon/
          (essais E3 et E4 seulement, images allégées, versionné) :
  manifeste.json          un élément par maillage, texture, variante de matériau, groupe d'instances
  maillages/<famille>/SM_*.glb   un maillage par fichier (glTF binaire), une section de matériau nommée
  textures/<famille>/T_*.jpg|png puissances de 2 ; couleur JPEG (sRGB), relief PNG (linéaire, convention DirectX)
  instances/<famille>/SM_*.csv   une ligne par objet à poser, en unités Unreal (cm, degrés)
  controle.json           contrôles relus sur disque

DÉCISIONS (détail dans pc/etape2_unreal/LISEZMOI_PAQUET.md)
- Repère Unreal : X = est, Y = sud, Z = haut, en cm ; origine = axe de la chaussée au PK 0. C'est la convention
  déjà retenue par le kit (repere_unreal.py) et par ACR Extra Stages : UE = 100 * (gX, gZ, gY), g = glTF du projet.
- Chaque maillage est RECENTRÉ sur son pivot (centre de son emprise en plan, altitude minimale, arrondi au cm) ;
  la position de l'acteur est dans le manifeste. Les sommets restent ainsi petits (précision float32 des tampons
  de sommets, bornes et pivots utilisables dans l'éditeur) et l'acteur porte la grande coordonnée (double en UE5).
- Format : glTF binaire (.glb), lu par l'importeur Interchange d'Unreal 5.6 sans greffon. FBX n'est pas retenu :
  son écriture fiable exige le SDK FBX d'Autodesk (non libre, absent ici) ; OBJ ne porte ni plusieurs UV ni
  normales fiables ni noms de section. Les glb ne portent ni image ni matériau texturé : seulement un nom de
  section, pour que l'import ne crée aucun matériau parasite.
- Axes de l'importeur : supposés UE = 100 * (gX, gZ, gY) pour un glb (« X,Z,Y »). Si la mire (E3) montre une
  autre correspondance, relancer avec --axes <valeur lue par construire_niveau.py> : seuls les sommets des glb
  changent, pas le manifeste.
- Sol (--sol jeu, par défaut pour le paquet complet) : le terrain est redécoupé par cellule de 350 m du monde du jeu
  et prend pour parent le matériau de terrain de Bollène ; ses masques (TGA, textures virtuelles) et sa carte de
  couleur viennent de scripts/15b_sols_du_jeu.py. Le découpage dépend du placement de l'étape 1 : relancer ce script
  après pc/etape2_unreal/outils/relever_placement.py si le placement a changé. --sol photo : l'ancien terrain.
Usage : python 16_paquet_unreal.py [--echantillon] [--pk-min A --pk-max B] [--axes X,Z,Y] [--sortie DOSSIER]
                                   [--sol jeu|photo]
"""
import argparse
import csv
import gzip
import io
import json
import math
import shutil
import time
import zlib
from pathlib import Path

import importlib.util
import numpy as np
import shapely
from PIL import Image
from scipy.spatial import cKDTree

import regles_arbres
from acr_geo import OUT, REF, ROOT

_spec = importlib.util.spec_from_file_location("modele_3d", Path(__file__).with_name("08_modele_3d.py"))
m08 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m08)

MOD = ROOT / "modele"
_f = ROOT / "data" / "reference" / "matieres_du_jeu.json"
MATIERES = json.loads(_f.read_text(encoding="utf-8")) if _f.exists() else {}       # matières du jeu choisies le 13/11/2026


def reglages_du_sol():
    """Textures, nombres et teintes des six couches du sol (matieres_du_jeu.json), pour chaque variante MI_Sol_*."""
    r = {"textures": {}, "scalaires": {}, "vecteurs": {}}
    for c in MATIERES.get("sol", {}).get("couches", {}).values():
        for k in r:
            r[k].update(c.get(k, {}))
    return r if any(r.values()) else None
KIT = ROOT / "pc" / "etape2_unreal"
NOM = "GrandCaunet"
UE = f"/Game/Environments/{NOM}"
NIVEAU = f"/Game/Levels/{NOM}"
GRILLE0 = (913500.0, 6240500.0)     # coin sud-ouest commun des grilles de dalles (Lambert-93)
LOIN_GAMMA, LOIN_GAIN = 0.72, 1.08            # courbe d'éclaircissement des images lointaines (--lointain-clarte)
LOIN_APLAT_DE, LOIN_APLAT_A = 150.0, 800.0   # m de la route : début et fin de l'adoucissement des normales lointaines
LOIN0 = (880000, 6210000)             # coin sud-ouest de la grille kilométrique de l'anneau lointain
# Barres rocheuses du massif lointain (--falaises) : la photo aérienne voit les falaises d'en haut, donc à peine ;
# vues de la route ce sont de longues barres de calcaire clair. Là où le relief est très raide, l'image prend une
# teinte de calcaire. Pentes en degrés : début et fin de la transition, pour le relief à 5 m puis pour celui à 25 m
# (qui écrase les falaises, d'où des seuils plus bas).
FALAISE = {"pente_5m_deg": (40.0, 55.0), "couleur": (196, 186, 166), "taux": 0.70, "elargir_m": 8.0}
# Vu en jeu le 13/11/2026 : massifs lointains blancs, d'aspect enneigé, et rayés de bandes horizontales. Les bancs
# (strates) sont retirés, la teinte est moins claire et moins couvrante, et elle n'est plus posée au-delà du relief à
# 5 m (6 km environ) : le relief à 25 m ne montre pas les falaises, les seuils abaissés teintaient des versants entiers.
TRONCON = 200.0                       # m de PK par tronçon de route et d'ouvrages
PK_E3 = 1653.0                        # pont à parapets de pierre : la dalle qui le contient
PK_E4 = (1600.0, 1800.0)              # 200 m autour de ce pont
SEED = 16
M_SIMPLE = "/Game/Materials/General/Masters/M_Simple"
EDITEUR = "/Game/GC_EditeurSeulement"          # jamais livré : matériau de secours, mires
SECOURS = f"{EDITEUR}/M_GC_Secours"
PARAM_SIMPLE = {"couleur": "Simple_BaseColor_Texture", "orm": "Simple_OcclRoughMet_Texture", "relief": "Simple_Normal_Texture"}
PARAM_SECOURS = {"couleur": "Couleur", "orm": "ORM", "relief": "Relief"}
# Relevé dans le jeu le 11/11/2026 (pc/etape2_unreal/PROTOCOLE.md § 0 bis) : les trois noms de paramètres sont exacts,
# mais M_Simple n'échantillonne ses textures que si ses static switch « Simple_Use_*_Texture » sont actifs, et ils ne
# le sont pas par défaut. construire_niveau.py prend donc pour parent, à la place de M_Simple, la variante du jeu
# MI_SisteronConcrete01 (factices.json, "role": "modele_m_simple"), et donne un relief plat aux variantes sans relief.
# Le manifeste continue de nommer M_Simple : c'est l'import qui substitue.
A_CONFIRMER = ("noms de paramètres confirmés dans le jeu ; M_Simple nommé ici est remplacé à l'import par la variante "
               "modèle du jeu (factices.json, role modele_m_simple), dont les static switch de texture sont actifs ; "
               "sans --parent jeu, le script d'import utilise le parent de secours M_GC_Secours")
# Sol « façon jeu » (--sol jeu) : variante de terrain de Bollène prise pour parent (paillis, aiguilles de pin, herbe
# haute, herbe sèche, terre, cailloux déjà actifs), cellules de 350 m comme dans le jeu, carte de couleur 4096.
# Herbes des bas-côtés (--herbes jeu). Échelles : du 5e au 95e centile de celles de Bollène (du 5e au 50e pour
# WildGrass05, dont les plus grandes touffes font 7 m). Disparition entre 100 et 150 m, sans ombre, comme dans le jeu.
# Vu en jeu le 13/11/2026 : herbes sèches jaune paille de 0,6 à 1,5 m jusqu'au ras de l'asphalte, alors que la réalité
# (vidéo de reconnaissances, novembre) montre une herbe rase verte de 5 à 30 cm, des feuilles mortes et de la pierraille.
# Deux mélanges : « vert » sur la bande d'herbe des accotements, « sec » ailleurs (garrigue, sous-bois clair), où les
# touffes sèches restent, mais basses. Tailles natives lues dans le jeu (largeur, hauteur) ; l'échelle donne la hauteur.
HERBES = {"dossier": "/Game/Foliage/GroundCover", "bande_m": 14.0, "debut_m": 0.35, "portee_m": 4.5,
          "candidats_par_metre": 44, "disparition_cm": [9000, 14000], "petit": "GreenGrassLong02/SM_GreengrassLong02",
          "maillages": {"GreenGrass03/SM_Greengrass03": {"vert": 0.44, "sec": 0.10, "echelle": [0.8, 1.5], "largeur_m": 1.49},       # 14 à 27 cm
                        "GreenGrassLong02/SM_GreengrassLong02": {"vert": 0.24, "sec": 0.06, "echelle": [0.6, 1.1], "largeur_m": 0.93},  # 17 à 32 cm
                        "Ribwort/SM_Ribwort_01": {"vert": 0.10, "sec": 0.0, "echelle": [0.8, 1.3], "largeur_m": 0.97},                # plantain, 13 à 21 cm
                        "WildGrass/SM_WildGrass01": {"vert": 0.10, "sec": 0.12, "echelle": [0.7, 1.2], "largeur_m": 0.99},            # 20 à 35 cm
                        "DeadLeaves/SM_Dead_Leaves_01": {"vert": 0.06, "sec": 0.06, "echelle": [1.4, 2.6], "largeur_m": 0.42},        # feuilles mortes, à plat
                        "DryGrass05/SM_Drygrass05": {"vert": 0.06, "sec": 0.38, "echelle": [0.55, 0.95], "largeur_m": 1.47},          # 18 à 31 cm
                        "DryGrass06/SM_Drygrass06": {"vert": 0.0, "sec": 0.18, "echelle": [0.42, 0.72], "largeur_m": 1.53},           # 34 à 59 cm
                        "WildGrass/SM_WildGrass03": {"vert": 0.0, "sec": 0.10, "echelle": [1.5, 2.6], "largeur_m": 0.62},             # 21 à 36 cm
                        # pierraille calcaire claire, omniprésente sur les accotements et les talus de la reconnaissance :
                        # trois pierres calcaires du jeu (Grèce), de 15 à 70 cm une fois mises à l'échelle
                        "/Game/Props/GreeceProps/GreElaSmallStones/SM_GreElaSmallLimestoneD": {"vert": 0.035, "sec": 0.07, "echelle": [0.6, 1.5], "largeur_m": 0.68},
                        "/Game/Props/GreeceProps/GreElaSmallStones/SM_GreElaSmallLimestoneB": {"vert": 0.04, "sec": 0.08, "echelle": [0.8, 2.2], "largeur_m": 0.33},
                        "/Game/Props/GreeceProps/GreElaSmallStones/SM_GreElaSmallLimestoneA": {"vert": 0.03, "sec": 0.06, "echelle": [1.0, 2.6], "largeur_m": 0.24}}}
# Buissons (--buissons jeu) : à l'import, attribution.py choisit dans ce dossier le maillage à la taille de chaque
# arbuste (Willow_01, 03a, 03b, 04a : 0,5 à 1,4 m de haut). À Bollène ils disparaissent entre 100 et 150 m et ne
# portent pas d'ombre ; ici entre 150 et 220 m, parce qu'ils tiennent lieu de garrigue.
BUISSONS = {"maillage": "/Game/Foliage/GroundCover/Willow/SM_Willow_03a", "hauteur_min_m": 0.55,
            "boxthorn_a_partir_de_m": 1.3, "disparition_cm": [15000, 22000]}
# Parapets, murs et tabliers : leur matière est héritée de deux matériaux de mur de Bollène (factices.json, role
# parent_du_jeu). Lu dans le jeu le 12/11/2026 : les murs de pierre de Bollène sont dépliés à 5 m par unité et
# peints de gris aux sommets (médiane 135, alpha 255) ; ses murs de béton à 3,14 m par unité, sans couleur. Nos
# parapets sont dépliés à 2 m par unité (scripts/11_route_ouvrages.py, S_PAROI).
MURS_DU_JEU = {"pierre": {"uv": 2.0 / 5.0, "couleur": (135, 135, 135, 255)},
               "pierre_sombre": {"uv": 2.0 / 5.0, "couleur": (135, 135, 135, 255)},
               "beton": {"uv": 2.0 / 3.144, "couleur": None}, "dalle": {"uv": 2.0 / 3.144, "couleur": None},
               "chaperon": {"uv": 2.0 / 3.144, "couleur": None}}
# Câbles électriques entre les poteaux (maillage à nous) : trois par portée, accrochés à la traverse du poteau du jeu
# (bouts à ±1 m, milieu), à 8,6 m du sol ; flèche de 0,8 m pour 60 m de portée.
CABLES = {"portee_max_m": 115.0, "fleche_par_m2": 0.8 / 60.0 ** 2, "segments": 12, "rayon_m": 0.02, "couleur": (30, 30, 32)}
# Rubalise du rallye : ruban de 7,5 cm à rayures rouges et blanches, tendu à 0,9 m entre des piquets du jeu.
RUBALISE = {"hauteur_m": 0.90, "largeur_m": 0.075, "periode_m": 0.30, "fleche_par_m": 0.012,
            "rouge": (196, 32, 30), "blanc": (232, 232, 228)}
# Lisses en bois (aires, clôtures) et barrières de piste forestière (rouges) : couleur unie.
LISSES = {"couleurs": {"lisse_bois": (118, 100, 80), "barriere_de_piste": (170, 42, 36)}}
GLISSIERE = {"dossier": "/Game/Props/Guardrails/MetalGuardrailA", "debut": "SM_MetalGuardrailASimpleBegin",
             "milieu": "SM_MetalGuardrailASimpleCenter", "fin": "SM_MetalGuardrailASimpleEnd", "module_m": 4.0,
             "enfoncement_m": 0.05}
SOL_PARENT = "/Game/Environments/MonteCarloS1Bollene/TerrainMaterial/MI_MonteCarloS1BolleneTerrainFirstChild"
SOL_CELLULE_M = 350.0
SOL_MASQUE_PX = 1024
SOL_CARTE_PX = 4096
SOL_CARTE_UNITE_M = 70.0              # côté de la carte = UVDivideWP x 70 m (relevé sur Hafren South et Bollène)
SOL_CARTE_CIBLE = {"moyenne": 118.0}   # clarté moyenne visée sur le terrain, sur 255 (celle de Bollène est de 86,5)
IMPORT_MAILLAGE = {"collision": "aucune", "nanite": False, "generer_lightmap_uv": False, "importer_materiaux": False,
                   "importer_textures": False, "recalculer_normales": False, "recalculer_tangentes": True,
                   "combiner_maillages": True, "echelle_import": 1.0}


# --- repère --------------------------------------------------------------------------------------------
class Axes:
    """Correspondance supposée de l'importeur glb : UE (cm) = 100 * M . g_fichier (m). Valeur « X,Z,Y » :
    UE.X = g.X, UE.Y = g.Z, UE.Z = g.Y. Le paquet écrit g_fichier = M^-1 . (UE_local / 100)."""

    D = np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0]], float)          # glTF du projet -> UE voulu

    def __init__(self, texte="X,Z,Y"):
        self.texte = texte
        M = np.zeros((3, 3))
        for i, c in enumerate(texte.replace(" ", "").split(",")):
            s = -1.0 if c.startswith("-") else 1.0
            M[i, "XYZ".index(c.lstrip("+-").upper())] = s
        if abs(abs(np.linalg.det(M)) - 1) > 1e-9:
            raise SystemExit(f"--axes {texte} : ce n'est pas une permutation signée des axes")
        self.M, self.Minv = M, np.linalg.inv(M)
        self.retourner = np.linalg.det(self.Minv @ self.D) < 0      # orientation des triangles à inverser

    @staticmethod
    def ue(g):
        """glTF du projet (m) -> Unreal (cm)."""
        g = np.asarray(g, float)
        return 100.0 * g[..., [0, 2, 1]]

    def fichier(self, ue_local_cm):
        return (np.asarray(ue_local_cm, float) / 100.0) @ self.Minv.T

    def depuis_fichier(self, g_fichier):
        return 100.0 * (np.asarray(g_fichier, float) @ self.M.T)


def points_de_controle(ch, ref):
    out = []
    for nom, pk in (("départ (PK 0)", 0.0), ("arrivée (PK 6736)", 6736.0)):
        i = int(np.argmin(np.abs(ch["pk"] - pk)))
        x, y, z = (float(v) for v in ch["A"][i])
        g = m08.to_gltf(np.array([[x, y, z]]), ref)[0].astype(float)
        out.append({"nom": nom, "pk_m": pk, "lambert93_m": [round(x, 2), round(y, 2), round(z, 2)],
                    "gltf_m": [round(float(v), 2) + 0.0 for v in g],
                    "unreal_cm": [round(float(v), 1) + 0.0 for v in Axes.ue(g)]})
    return out


# --- lecture des glb du modèle --------------------------------------------------------------------------
def lire_glb(path):
    """Maillages (nom, pos, nrm, uv, idx) et matériau (nom, couleur RVBA, rugosité, image de base en octets ou
    chemin, normal map) d'un glb du projet."""
    path = Path(path)
    b = path.read_bytes()
    n = int(np.frombuffer(b, "<u4", 1, 12)[0])
    gl = json.loads(b[20:20 + n])
    binoff = 20 + n + 8

    def vue(i):
        v = gl["bufferViews"][i]
        o = binoff + v.get("byteOffset", 0)
        return b[o:o + v["byteLength"]]

    def arr(i):
        a = gl["accessors"][i]
        dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}[a["componentType"]]
        k = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[a["type"]]
        v = gl["bufferViews"][a["bufferView"]]
        return np.frombuffer(b, dt, a["count"] * k, binoff + v.get("byteOffset", 0)).reshape(-1, k)

    def image(tex):
        im = gl["images"][gl["textures"][tex["index"]]["source"]]
        return path.parent / im["uri"] if "uri" in im else vue(im["bufferView"])

    out = []
    for m in gl["meshes"]:
        p = m["primitives"][0]
        mat = gl["materials"][p["material"]]
        pbr = mat.get("pbrMetallicRoughness", {})
        out.append({"nom": m["name"], "pos": arr(p["attributes"]["POSITION"]).astype(np.float64),
                    "nrm": arr(p["attributes"]["NORMAL"]).astype(np.float64),
                    "uv": arr(p["attributes"]["TEXCOORD_0"]).astype(np.float64) if "TEXCOORD_0" in p["attributes"] else None,
                    "idx": arr(p["indices"]).reshape(-1, 3).astype(np.int64),
                    "mat": {"nom": mat.get("name", "?"), "couleur": pbr.get("baseColorFactor", [1, 1, 1, 1]),
                            "rugosite": pbr.get("roughnessFactor", 0.9), "metal": pbr.get("metallicFactor", 0.0),
                            "image": image(pbr["baseColorTexture"]) if "baseColorTexture" in pbr else None,
                            "relief": image(mat["normalTexture"]) if "normalTexture" in mat else None}})
    return out


# --- écriture d'un glb « géométrie seule » ----------------------------------------------------------------
def ecrire_glb(path, nom, section, pos, nrm, uv, tri, couleur=None):
    """Un maillage, un nœud, une section de matériau (nom seulement, sans texture) : l'import ne crée aucun
    matériau ni texture, et la section porte le nom de la variante à lui affecter. couleur : RVBA par sommet
    (octets), ou None."""
    gl = {"asset": {"version": "2.0", "generator": "acr-grand-caunet 16_paquet_unreal.py"}, "scene": 0,
          "scenes": [{"nodes": [0]}], "nodes": [{"name": nom, "mesh": 0}],
          "meshes": [{"name": nom, "primitives": [{"attributes": {}, "material": 0, "mode": 4}]}],
          "materials": [{"name": section, "pbrMetallicRoughness": {"baseColorFactor": [0.8, 0.8, 0.8, 1.0],
                                                                    "metallicFactor": 0.0, "roughnessFactor": 0.9}}],
          "accessors": [], "bufferViews": [], "buffers": []}
    blob = bytearray()

    def acc(a, kind, target, minmax=False):
        while len(blob) % 4:
            blob.append(0)
        gl["bufferViews"].append({"buffer": 0, "byteOffset": len(blob), "byteLength": a.nbytes, "target": target})
        blob.extend(a.tobytes())
        d = {"bufferView": len(gl["bufferViews"]) - 1,
             "componentType": {np.float32: 5126, np.uint32: 5125, np.uint16: 5123, np.uint8: 5121}[a.dtype.type],
             "count": int(len(a) if a.ndim > 1 else a.size), "type": kind}
        if a.dtype.type is np.uint8:
            d["normalized"] = True
        if minmax:
            d["min"], d["max"] = a.min(0).tolist(), a.max(0).tolist()
        gl["accessors"].append(d)
        return len(gl["accessors"]) - 1

    pr = gl["meshes"][0]["primitives"][0]
    pr["attributes"]["POSITION"] = acc(pos.astype(np.float32), "VEC3", 34962, True)
    pr["attributes"]["NORMAL"] = acc(nrm.astype(np.float32), "VEC3", 34962)
    if uv is not None:
        pr["attributes"]["TEXCOORD_0"] = acc(uv.astype(np.float32), "VEC2", 34962)
    if couleur is not None:
        pr["attributes"]["COLOR_0"] = acc(np.ascontiguousarray(couleur, dtype=np.uint8), "VEC4", 34962)
    pr["indices"] = acc(tri.ravel().astype(np.uint16 if len(pos) < 65536 else np.uint32), "SCALAR", 34963)
    while len(blob) % 4:
        blob.append(0)
    gl["buffers"].append({"byteLength": len(blob)})
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"glTF" + np.array([2, 12 + 8 + len(js) + 8 + len(blob)], "<u4").tobytes())
        f.write(np.array([len(js), 0x4E4F534A], "<u4").tobytes() + js)
        f.write(np.array([len(blob), 0x004E4942], "<u4").tobytes() + bytes(blob))


def sous_maillage(pos, nrm, uv, tri, sel):
    used, inv = np.unique(tri[sel], return_inverse=True)
    return pos[used], nrm[used], (uv[used] if uv is not None else None), inv.reshape(-1, 3)


def dedoublonne(pos, nrm, uv, tri):
    """Fusionne les sommets strictement identiques (position, normale, UV au 1/10 de mm près)."""
    cle = np.round(np.hstack([pos * 1e4, nrm * 1e4] + ([uv * 1e6] if uv is not None else []))).astype(np.int64)
    _, premier, inv = np.unique(cle, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    t = inv[tri]
    t = t[(t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2])]
    return pos[premier], nrm[premier], (uv[premier] if uv is not None else None), t


class Paquet:
    def __init__(self, sortie, axes, echantillon, pk_min, pk_max):
        self.sortie, self.axes, self.echantillon = Path(sortie), axes, echantillon
        self.pk_min, self.pk_max = pk_min, pk_max
        self.elements, self.vus = [], set()

    def ajoute(self, e):
        if e["nom"] in self.vus:
            raise SystemExit(f"nom en double : {e['nom']}")
        self.vus.add(e["nom"])
        self.elements.append(e)
        return e

    def garde(self, essais):
        """En échantillon, seuls les éléments des essais E3 et E4 sont écrits."""
        return not self.echantillon or bool({"E3", "E4"} & set(essais))

    def maillage(self, nom, famille, dest, pos_g, nrm_g, uv, tri, section, essais, pk=None, extra=None,
                 couleur_nulle=False, couleur=None, couleurs=None):
        """pos_g, nrm_g : glTF du projet (m) ; écrit le glb recentré et renvoie l'élément du manifeste.
        couleur_nulle : couleur de sommet (0, 0, 0, 0) partout, comme les sommets ordinaires des sols du jeu ; sans
        elle Unreal donne du blanc opaque, que le matériau de terrain du jeu pourrait lire comme un masque plein."""
        ue = Axes.ue(pos_g)
        lo, hi = ue.min(0), ue.max(0)
        pivot = np.round(np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]))
        loc = ue - pivot
        f = self.axes.fichier(loc)
        n_ue = np.asarray(nrm_g, float)[:, [0, 2, 1]]
        n_f = n_ue @ self.axes.Minv.T
        n_f /= np.maximum(np.linalg.norm(n_f, axis=1, keepdims=True), 1e-12)
        t = tri[:, [0, 2, 1]] if self.axes.retourner else tri
        if uv is not None and not famille.startswith("terrain") and not famille.startswith("lointain"):
            uv = uv - np.floor(uv.min(0))      # UV répétées : petites valeurs (précision), même aspect
        if couleurs is None:                                 # couleurs : une par sommet (n, 4), sommets gardés tels quels
            f, n_f, uv, t = dedoublonne(f, n_f, uv, t)
        fichier = Path("maillages") / famille / f"{nom}.glb"
        if couleur_nulle:
            couleur = (0, 0, 0, 0)
        ecrire_glb(self.sortie / fichier, nom, section, f, n_f, uv, t,
                   couleur=np.asarray(couleurs, np.uint8) if couleurs is not None
                   else np.tile(np.array(couleur, np.uint8), (len(f), 1)) if couleur is not None else None)
        e = {"type": "StaticMesh", "nom": nom, "fichier": fichier.as_posix(), "destination": dest,
             "chemin_ue": f"{dest}/{nom}", "section_materiau": section, "materiau": section,
             "import": IMPORT_MAILLAGE,
             "acteur": {"label": nom, "position_cm": pivot.tolist(), "rotation_deg": [0.0, 0.0, 0.0],
                        "echelle": [1.0, 1.0, 1.0], "collision": "NoCollision", "mobilite": "Static",
                        "ombre_portee": not famille.startswith("lointain")},
             "bornes_locales_cm": {"min": np.round(loc.min(0), 1).tolist(), "max": np.round(loc.max(0), 1).tolist()},
             "sommets": int(len(f)), "triangles": int(len(t)), "essais": essais}
        if couleur is not None:
            e["couleur_de_sommet"] = [int(v) for v in couleur]
        if pk is not None:
            e["pk_m"] = [round(float(pk[0]), 1), round(float(pk[1]), 1)]
        if extra:
            e.update(extra)
        return self.ajoute(e)

    def texture(self, nom, famille, dest, image, essais, relief=False, adressage="Wrap", px_max=None, qualite=95,
                copie_si_possible=None):
        """image : PIL.Image (couleur RVB, ou relief déjà en convention DirectX) ; écrit JPEG (couleur) ou PNG
        (relief). copie_si_possible : fichier JPEG source à recopier tel quel (évite une recompression)."""
        w, h = image.size
        if px_max and w > px_max:
            image = image.resize((px_max, px_max), Image.LANCZOS)
            copie_si_possible = None
        w, h = image.size
        if (w & (w - 1)) or (h & (h - 1)):
            raise SystemExit(f"{nom} : {w} x {h} n'est pas une puissance de 2")
        ext = ".png" if relief else ".jpg"
        fichier = Path("textures") / famille / f"{nom}{ext}"
        out = self.sortie / fichier
        out.parent.mkdir(parents=True, exist_ok=True)
        if copie_si_possible is not None and not relief:
            shutil.copyfile(copie_si_possible, out)
        elif relief:
            image.save(out, "PNG", optimize=True)
        else:
            image.convert("RGB").save(out, "JPEG", quality=qualite, optimize=True, subsampling=0 if qualite >= 90 else 2)
        return self.ajoute({"type": "Texture2D", "nom": nom, "fichier": fichier.as_posix(), "destination": dest,
                            "chemin_ue": f"{dest}/{nom}", "dimensions": [w, h],
                            "import": {"srgb": not relief,
                                       "compression": "TC_Normalmap" if relief else "TC_Default",
                                       "groupe_lod": "TEXTUREGROUP_WorldNormalMap" if relief else "TEXTUREGROUP_World",
                                       "adressage": adressage, "mipmaps": "FromTextureGroup",
                                       "virtual_texture_streaming": False,
                                       "convention_relief": "DirectX (vert inversé) : ne PAS cocher Flip Green Channel"
                                       if relief else None},
                            "essais": essais})

    def masque(self, nom, famille, dest, rvba, essais):
        """Masque de matières (RVBA, linéaire) pour le matériau de terrain du jeu : TGA sans compression, parce
        qu'Unreal retouche les couleurs des PNG là où l'alpha est nul ; texture virtuelle, comme les masques du jeu."""
        h, w = rvba.shape[:2]
        fichier = Path("textures") / famille / f"{nom}.tga"
        out = self.sortie / fichier
        out.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rvba, "RGBA").save(out, "TGA")
        return self.ajoute({"type": "Texture2D", "nom": nom, "fichier": fichier.as_posix(), "destination": dest,
                            "chemin_ue": f"{dest}/{nom}", "dimensions": [w, h],
                            "import": {"srgb": False, "compression": "TC_Masks", "groupe_lod": "TEXTUREGROUP_World",
                                       "adressage": "Clamp", "mipmaps": "FromTextureGroup",
                                       "virtual_texture_streaming": True, "convention_relief": None},
                            "essais": essais})

    def materiau_du_jeu(self, nom, dest, parent, textures, scalaires, essais, note=None, reglages=None):
        """Variante dont le parent est une variante du jeu (factices.json, role parent_du_jeu) : elle n'y règle que
        les textures et les nombres donnés ici, et hérite du reste, static switch compris.
        reglages : {"textures": {paramètre: chemin /Game/...}, "scalaires": {...}, "vecteurs": {...}} posés en plus
        (data/reference/matieres_du_jeu.json)."""
        e = {"type": "MaterialInstance", "nom": nom, "destination": dest, "chemin_ue": f"{dest}/{nom}",
             "parent_jeu_pressenti": parent, "parent_du_jeu": parent, "parametres_texture": dict(textures),
             "parametres_scalaires": {k: float(v) for k, v in scalaires.items()},
             "parent_secours": SECOURS, "parametres_secours": {},
             "static_switch": "aucun ne doit être modifié", "essais": essais}
        if note:
            e["note"] = note
        if reglages:
            e["reglages_du_jeu"] = reglages
        return self.ajoute(e)

    def materiau(self, nom, dest, textures, essais, parent_jeu=M_SIMPLE, alternatif=None, note=None):
        """textures : {"couleur": nom de texture, "orm": ..., "relief": ...}"""
        e = {"type": "MaterialInstance", "nom": nom, "destination": dest, "chemin_ue": f"{dest}/{nom}",
             "parent_jeu_pressenti": parent_jeu, "parametres_texture": {PARAM_SIMPLE[k]: v for k, v in textures.items()},
             "parent_secours": SECOURS, "parametres_secours": {PARAM_SECOURS[k]: v for k, v in textures.items()},
             "static_switch": "aucun ne doit être modifié", "a_confirmer": A_CONFIRMER, "essais": essais}
        if alternatif:
            e["parent_jeu_alternatif_e3b"] = alternatif
        if note:
            e["note"] = note
        r = MATIERES.get("materiaux", {}).get(nom)
        if r and not self.echantillon:                       # teintes et nombres posés sur le parent du jeu de ce matériau
            e["reglages_du_jeu"] = {k: r[k] for k in ("textures", "scalaires", "vecteurs") if r.get(k)}
        return self.ajoute(e)


# --- utilitaires de données ------------------------------------------------------------------------------
def releve_vert(rgb_u8):
    """Normal map OpenGL (vert = nord, Y+) -> DirectX (Y-) : canal vert inversé."""
    a = np.array(rgb_u8, dtype=np.uint8, copy=True)
    a[..., 1] = 255 - a[..., 1]
    return a


def reechantillonne_relief(im, px):
    """Réduit une normal map en moyennant les vecteurs puis en les renormalisant."""
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 127.5 - 1.0
    if a.shape[0] != px:
        a = np.stack([np.asarray(Image.fromarray(a[..., k]).resize((px, px), Image.BILINEAR)) for k in range(3)], 2)
    a[..., 2] = np.maximum(a[..., 2], 0.05)
    a /= np.linalg.norm(a, axis=2, keepdims=True)
    return np.clip((a * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8)


def image_unie(rgb, px=8):
    return Image.new("RGB", (px, px), tuple(int(round(v)) for v in rgb))


def lin_vers_srgb(c):
    c = np.clip(np.asarray(c, float), 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055) * 255


class PK:
    """PK de points quelconques : axe de chaussee_precise.csv le plus proche (glTF du projet)."""

    def __init__(self, ch, ref):
        self.pk = ch["pk"]
        self.A = m08.to_gltf(ch["A"], ref).astype(float)
        self.t = cKDTree(self.A[:, [0, 2]])

    def __call__(self, g):
        _, k = self.t.query(np.asarray(g)[:, [0, 2]])
        return self.pk[k]


def recouvre(pk, a, b):
    return pk is not None and pk[1] > a and pk[0] < b


def essais_par_pk(pkr, e3=False):
    s = []
    if e3:
        s.append("E3")
    if recouvre(pkr, *PK_E4):
        s.append("E4")
    return s + ["complet"]


# --- familles ----------------------------------------------------------------------------------------------
def terrain(P, ref, pkf, args):
    """Dalles de 500 m (hors bande route) et sous-dalles de 100 m (bande route, 5 cm) de terrain_sol.glb."""
    man = json.loads((OUT / "textures_sol.json").read_text(encoding="utf-8"))
    ms = {m["nom"]: m for m in lire_glb(MOD / "terrain_sol.glb")}
    tex_dest, mesh_dest, mat_dest = f"{UE}/Terrain/Textures", f"{UE}/Terrain/Meshes", f"{UE}/Terrain/Materials"
    # point du pont E3
    ch = pkf
    gE3 = ch.A[int(np.argmin(np.abs(ch.pk - PK_E3)))]
    orm = None
    n = {"dalles": 0, "sous_dalles": 0}
    for d in man["dalles"]:
        bx, by = d["dalle_l93"][:2]
        i, j = int(round((bx - GRILLE0[0]) / 500)), int(round((by - GRILLE0[1]) / 500))
        listes = [("dalle", d, f"{i}_{j}", f"{i}y{j}")]
        for s in d["sous_dalles"]:
            sx, sy = s["cellule_l93"][:2]
            si, sj = int(round((sx - GRILLE0[0]) / 100)), int(round((sy - GRILLE0[1]) / 100))
            listes.append(("sous", s, f"{si}_{sj}", f"{si}y{sj}"))
        for genre, e, suf, suf_t in listes:
            m = ms[e["nom"]]
            pkr = pkf(m["pos"][m["idx"].ravel()])
            pkr = (float(pkr.min()), float(pkr.max())) if genre == "sous" else None
            if genre == "dalle":
                em = e["emprise_l93"]
                x, y = gE3[0] + ref["x0"], ref["y0"] - gE3[2]
                e3 = em[0] <= x <= em[2] and em[1] <= y <= em[3] and bx <= x < bx + 500 and by <= y < by + 500
                pk_dalle = pkf(m["pos"])
                dans = (pk_dalle >= PK_E4[0]) & (pk_dalle <= PK_E4[1])
                essais = (["E3"] if e3 else []) + (["E4"] if e3 or dans.mean() > 0.2 else []) + ["complet"]
                nom_sm, nom_mi = f"SM_{NOM}Terrain_{suf}", f"MI_Terrain_{suf_t}"
                nom_t, nom_n = f"T_Terrain_{suf_t}", f"T_TerrainN_{suf_t}"
                px_c, px_n = args.px_dalle, 1024
                famille = "terrain"
            else:
                essais = essais_par_pk(pkr)
                nom_sm, nom_mi = f"SM_{NOM}TerrainFin_{suf}", f"MI_TerrainFin_{suf_t}"
                nom_t, nom_n = f"T_TerrainFin_{suf_t}", f"T_TerrainFinN_{suf_t}"
                px_c, px_n = 2048, 1024
                famille = "terrain_fin"
            if not P.garde(essais):
                continue
            if P.echantillon:      # images allégées pour tenir dans le dépôt
                px_c = 1024 if genre == "dalle" else 2048
                px_n = 512
            if args.pk_min is not None and pkr is not None and not recouvre(pkr, args.pk_min, args.pk_max):
                continue
            if orm is None:
                orm = P.texture("T_GC_ORM_Sol", "commun", f"{UE}/Shared/Textures", image_unie((255, 242, 0)), ["E3", "E4", "complet"])
            src_c = MOD / e["couleur"]
            im = Image.open(src_c)
            copie = src_c if (im.size[0] == px_c and src_c.suffix == ".jpg" and not P.echantillon) else None
            P.texture(nom_t, famille, tex_dest, im.convert("RGB"), essais, adressage="Clamp", px_max=px_c,
                      qualite=95 if not P.echantillon else 88, copie_si_possible=copie)
            if im.size[0] != px_c and im.size[0] < px_c:
                raise SystemExit(f"{nom_t} : image source plus petite que {px_c}")
            rel = reechantillonne_relief(Image.open(MOD / e["relief"]), px_n)
            P.texture(nom_n, famille, tex_dest, Image.fromarray(releve_vert(rel)), essais, relief=True, adressage="Clamp")
            P.materiau(nom_mi, mat_dest, {"couleur": nom_t, "orm": "T_GC_ORM_Sol", "relief": nom_n}, essais,
                       alternatif="/Game/Environments/RallyShared/Materials/M_TerrainMaster_light")
            uv = m["uv"]
            P.maillage(nom_sm, famille, mesh_dest, m["pos"], m["nrm"], uv, m["idx"], nom_mi, essais, pk=pkr,
                       extra={"emprise_texture_l93": e["emprise_l93"], "source": f"modele/terrain_sol.glb#{e['nom']}"})
            n["dalles" if genre == "dalle" else "sous_dalles"] += 1
    return n


# --- sol « façon jeu » : matériau de terrain de Bollène, masques par cellule de 350 m, carte de couleur ------
class Placement:
    """Passage entre le glTF du projet et le monde du jeu (mètres, X et Y d'Unreal), par le placement de l'étape 1
    (pc/etape2_unreal/releves/placement_etape1.json, tenu à jour par outils/relever_placement.py)."""

    def __init__(self, ref):
        d = json.loads((KIT / "releves" / "placement_etape1.json").read_text(encoding="utf-8"))
        self.p = d["placement"]
        o = json.loads((ROOT / "export" / "stage_ir" / "grand_caunet" / "stage.json").read_text(encoding="utf-8"))["coordinates"]["origin"]
        self.ox, self.oy = o["lambert93_x_m"], o["lambert93_y_m"]
        self.x0, self.y0 = ref["x0"], ref["y0"]
        t = math.radians(self.p["theta_deg"])
        self.c, self.s = math.cos(t), math.sin(t)

    def monde(self, g):
        g = np.asarray(g, float)
        ix, iz = g[:, 0] + self.x0 - self.ox, g[:, 2] - (self.y0 - self.oy)
        dx, dz = ix - self.p["cx"], iz - self.p["cz"]
        return np.column_stack([self.c * dx + self.s * dz + self.p["tx"], -self.s * dx + self.c * dz + self.p["tz"]])

    def l93(self, X, Y):
        ax, az = X - self.p["tx"], Y - self.p["tz"]
        ix = self.c * ax - self.s * az + self.p["cx"]
        iz = self.s * ax + self.c * az + self.p["cz"]
        return ix + self.ox, self.oy - iz


def _couper(poly, axe, borne, sens):
    """Garde la partie du polygone convexe (lignes : X, Y monde, puis attributs) où sens * (coord - borne) >= 0."""
    out = []
    n = len(poly)
    for k in range(n):
        a, b = poly[k], poly[(k + 1) % n]
        da, db = sens * (a[axe] - borne), sens * (b[axe] - borne)
        if da >= 0:
            out.append(a)
        if (da > 0 and db < 0) or (da < 0 and db > 0):
            p, q = (a, b) if (a[0], a[1]) <= (b[0], b[1]) else (b, a)      # même calcul pour les deux triangles voisins
            t = (borne - p[axe]) / (q[axe] - p[axe])
            m = p + t * (q - p)
            m[axe] = borne
            out.append(m)
    return out


def decouper_par_cellule(pos, nrm, tri, xy, pas):
    """Répartit les triangles par cellule de `pas` mètres du monde du jeu ; ceux qui chevauchent une limite sont
    coupés sur cette limite. Rend {(i, j): (pos, nrm, xy, tri)}."""
    ci = np.floor(xy / pas).astype(np.int64)
    tc = ci[tri]
    lo, hi = tc.min(1), tc.max(1)
    simple = (lo == hi).all(1)
    par = {}
    for t in np.flatnonzero(simple):
        par.setdefault((int(lo[t, 0]), int(lo[t, 1])), []).append(t)
    A = np.hstack([xy, pos, nrm])
    coupes = {}
    for t in np.flatnonzero(~simple):
        poly = [A[k].copy() for k in tri[t]]
        for i in range(int(lo[t, 0]), int(hi[t, 0]) + 1):
            pi = _couper(_couper(poly, 0, i * pas, 1.0), 0, (i + 1) * pas, -1.0)
            if len(pi) < 3:
                continue
            for j in range(int(lo[t, 1]), int(hi[t, 1]) + 1):
                pj = _couper(_couper(pi, 1, j * pas, 1.0), 1, (j + 1) * pas, -1.0)
                if len(pj) < 3:
                    continue
                q = np.array(pj)
                aire = 0.5 * abs(np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1]))
                if aire > 1e-6:
                    coupes.setdefault((i, j), []).append(q)
    out = {}
    for cle in sorted(set(par) | set(coupes)):
        P_, N_, X_, T_ = [], [], [], []
        n0 = 0
        if cle in par:
            used, inv = np.unique(tri[par[cle]], return_inverse=True)
            P_.append(pos[used]); N_.append(nrm[used]); X_.append(xy[used]); T_.append(inv.reshape(-1, 3))
            n0 = len(used)
        for q in coupes.get(cle, []):
            k = len(q)
            P_.append(q[:, 2:5]); N_.append(q[:, 5:8]); X_.append(q[:, 0:2])
            T_.append(np.array([[n0, n0 + a, n0 + a + 1] for a in range(1, k - 1)], np.int64))
            n0 += k
        n = np.vstack(N_)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        out[cle] = (np.vstack(P_), n, np.vstack(X_), np.vstack(T_))
    return out, int((~simple).sum())


# Bord d'asphalte irrégulier (--bord-enrobe) : vu en jeu le 13/11/2026, le bord de la chaussée est une ligne nette, alors
# que sur la route réelle la pierraille, la terre et l'herbe mordent inégalement sur l'enrobé. Une mince bande de sol
# suit donc chaque bord : elle recouvre l'enrobé sur BORD["mord_m"] (variable d'un pas à l'autre), 2 cm au-dessus de
# lui, et descend dans l'accotement. Elle fait partie du terrain : même matériau, mêmes masques, même découpage.
BORD = {"pas_m": 0.25, "mord_m": (0.03, 0.42), "dehors_m": 0.6, "au_dessus_m": 0.02, "enfoui_m": 0.12}


def bande_de_bord(ch, ref):
    """(pos glTF, normales, triangles) de la bande de sol qui mord sur chaque bord de l'enrobé."""
    f = REF / "ouvrages_parapets.json"
    murs = {"gauche": [], "droite": []}
    if f.exists():                      # contre un parapet ou un mur au ras du bord, la bande s'arrête au pied du mur
        cfg = json.loads(f.read_text(encoding="utf-8"))
        for e in cfg.get("ouvrages", []) + cfg.get("parapets_hors_tablier", []):
            for cote in murs:
                p = e.get(cote) or {}
                if p.get("type", "aucun") != "aucun" and float(p.get("decalage_m", 0.0)) <= 0.3:
                    a_, b_ = p.get("pk_debut_m", e.get("pk_debut_m")), p.get("pk_fin_m", e.get("pk_fin_m"))
                    if a_ is not None and b_ is not None:
                        murs[cote].append((float(a_) - 1.0, float(b_) + 1.0))
    # pas de bande de sol là où le bord de la chaussée touche une surface revêtue annexe (carrefours, dégagements)
    revetu = None
    f_ann = OUT / "annexes_revetues.geojson"
    if f_ann.exists():
        from pyproj import Transformer
        vers_l93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True).transform
        polys = []
        for ft in json.loads(f_ann.read_text(encoding="utf-8"))["features"]:
            g_ = shapely.geometry.shape(ft["geometry"])
            if g_.geom_type == "Polygon" and "revêtue" in str(ft["properties"].get("type", "")):
                polys.append(shapely.transform(g_, lambda c: np.column_stack(vers_l93(c[:, 0], c[:, 1]))).buffer(0.6))
        if polys:
            revetu = shapely.union_all(polys)
            shapely.prepare(revetu)
    pk = ch["pk"]
    S = np.arange(pk[0] + 1.0, pk[-1] - 1.0, BORD["pas_m"])
    A = np.column_stack([np.interp(S, pk, ch["A"][:, k]) for k in range(3)])
    P_, N_, T_ = [], [], []
    k0 = 0
    for cote, cle, graine in (("gauche", "G", 3), ("droite", "D", 8)):
        E = np.column_stack([np.interp(S, pk, ch[cle][:, k]) for k in range(3)])
        n = E[:, :2] - A[:, :2]
        demi = np.maximum(np.linalg.norm(n, axis=1), 0.5)
        n /= demi[:, None]
        # largeur mordue : deux bruits (1,3 m et 6 m), avec des passages où le bord reste net
        w = _bruit(S / 1.3, 0.0, graine) * 0.6 + _bruit(S / 6.0, 0.0, graine + 1) * 0.4
        w = BORD["mord_m"][0] + (BORD["mord_m"][1] - BORD["mord_m"][0]) * np.clip((w - 0.25) / 0.55, 0.0, 1.0) ** 1.4
        mur = np.zeros(len(S), bool)
        for a_, b_ in murs[cote]:
            mur |= (S >= a_) & (S <= b_)
        dehors = np.where(mur, 0.04, BORD["dehors_m"])
        dedans = np.column_stack([E[:, :2] - n * w[:, None], E[:, 2] + (A[:, 2] - E[:, 2]) * (w / demi) + BORD["au_dessus_m"]])
        bord = np.column_stack([E[:, :2], E[:, 2] + BORD["au_dessus_m"]])
        ext = np.column_stack([E[:, :2] + n * dehors[:, None], E[:, 2] + np.where(mur, BORD["au_dessus_m"], -BORD["enfoui_m"])])
        L = np.stack([dedans, bord, ext], 1).reshape(-1, 3)
        g = m08.to_gltf(L, ref).astype(np.float64)
        i = np.arange(len(S) - 1)
        if revetu is not None:
            sur = shapely.contains_xy(revetu, E[:, 0] + 0.4 * n[:, 0], E[:, 1] + 0.4 * n[:, 1])
            i = i[~(sur[:-1] | sur[1:])]
        for c in (0, 1):
            a0, a1, b0, b1 = 3 * i + c, 3 * i + c + 1, 3 * (i + 1) + c, 3 * (i + 1) + c + 1
            t = np.concatenate([np.column_stack([a0, b0, a1]), np.column_stack([a1, b0, b1])]) + k0
            T_.append(t)
        P_.append(g)
        N_.append(np.tile([0.0, 1.0, 0.0], (len(g), 1)))
        k0 += len(g)
    pos, nrm, tri = np.vstack(P_), np.vstack(N_), np.vstack(T_)
    fn = np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])
    bas = fn[:, 1] < 0
    tri[bas] = tri[bas][:, [0, 2, 1]]
    return pos.astype(np.float32), nrm.astype(np.float32), tri


def terrain_jeu(P, ref, args, ch, ruban):
    """Terrain habillé par le matériau de terrain du jeu (variante de Bollène) au lieu de la photo aérienne.

    Lu dans le jeu le 12/11/2026 (PROTOCOLE.md § 0 sexies) : le matériau lit ses deux masques d'après la position
    dans le monde, par cellule de 350 m alignée sur l'origine, u = 1 - frac(X / 350 m), v = 1 - frac(Y / 350 m) ;
    un maillage ne porte qu'un jeu de masques, donc ne doit pas dépasser de sa cellule. La carte de couleur est lue
    à (tu, tv) = (v0, 1 - u0), u0 = (X + U_Add) / S, v0 = (Y + V_Add) / S, S = UVDivideWP x 70 m."""
    from scipy import ndimage as ndi
    src = MOD / "sols_jeu"
    meta = json.loads((src / "sols_jeu.json").read_text(encoding="utf-8"))
    pl = Placement(ref)
    ms = lire_glb(MOD / "terrain_sol.glb")
    pos = np.vstack([m["pos"] for m in ms])
    nrm = np.vstack([m["nrm"] for m in ms])
    dec = np.cumsum([0] + [len(m["pos"]) for m in ms[:-1]])
    tri = np.vstack([m["idx"] + d for m, d in zip(ms, dec)])
    # Sous la chaussée, le terrain portait jusqu'ici la photo de la route ; il porte maintenant des cailloux. Les rares
    # sommets de terrain situés sous la chaussée (culées de ponts) et qui l'affleurent sont abaissés de 15 cm sous elle.
    x93, y93 = pos[:, 0] + ref["x0"], ref["y0"] - pos[:, 2]
    pres = np.flatnonzero(cKDTree(ch["A"][:, :2]).query(np.column_stack([x93, y93]))[0] < 8.0)
    sous = pres[shapely.contains_xy(ruban.buffer(-0.05), x93[pres], y93[pres])]
    n_abaisses = 0
    if len(sous):
        bords = np.vstack([ch["A"], ch["G"], ch["D"]])
        _, k = cKDTree(bords[:, :2]).query(np.column_stack([x93[sous], y93[sous]]), k=3)
        z_route = bords[k, 2].min(1) - ref["z0"]
        haut = pos[sous, 1] > z_route - 0.08
        pos[sous[haut], 1] = z_route[haut] - 0.15
        n_abaisses = int(haut.sum())
    n_bord = 0
    if args.bord_enrobe:
        bp, bn, bt = bande_de_bord(ch, ref)
        tri = np.vstack([tri, bt + len(pos)])
        pos, nrm = np.vstack([pos, bp]), np.vstack([nrm, bn])
        n_bord = len(bt)
        print(f"  bord d'enrobé irrégulier : {n_bord} triangles ajoutés au terrain")
    xy = pl.monde(pos)
    cellules, n_coupes = decouper_par_cellule(pos, nrm, tri, xy, SOL_CELLULE_M)
    i0, j0 = min(c[0] for c in cellules), min(c[1] for c in cellules)
    tex_dest, mesh_dest, mat_dest = f"{UE}/Terrain/Textures", f"{UE}/Terrain/Meshes", f"{UE}/Terrain/Materials"
    essais = ["complet"]

    # carte de couleur : un carré centré sur le terrain, côté multiple de 70 m
    lo, hi = xy.min(0), xy.max(0)
    centre = np.round((lo + hi) / 2)
    diviseur = math.ceil(float((hi - lo).max()) * 1.04 / SOL_CARTE_UNITE_M)
    S = diviseur * SOL_CARTE_UNITE_M
    n = SOL_CARTE_PX
    tv, tu = np.meshgrid((np.arange(n) + 0.5) / n, (np.arange(n) + 0.5) / n, indexing="ij")
    X = centre[0] + ((1.0 - tv) - 0.5) * S
    Y = centre[1] + (tu - 0.5) * S
    x93, y93 = pl.l93(X, Y)
    e = meta["emprise_l93"]
    pas1 = meta["couleur_1m"]["pas_m"]
    coul = np.load(src / "couleur_1m.npy")
    lig, col = (e[3] - y93) / pas1 - 0.5, (x93 - e[0]) / pas1 - 0.5
    dedans = (lig >= 0) & (lig <= coul.shape[0] - 1) & (col >= 0) & (col <= coul.shape[1] - 1)
    f_sol14 = src / "couleur_1m_sol14.npy"
    if f_sol14.exists():                       # clarté mesurée là où la couleur vient des dalles de sol de l'étape 14
        sol14 = ndi.map_coordinates(np.load(f_sol14).astype(np.float32), [lig, col], order=0, mode="constant") > 0.5
        if (dedans & sol14).sum() > 1000:
            dedans &= sol14
    carte = np.stack([ndi.map_coordinates(ndi.gaussian_filter(coul[..., k].astype(np.float32), 0.7), [lig, col], order=1,
                                          mode="nearest") for k in range(3)], -1)
    del coul
    # mise à la clarté et au contraste de la carte de Bollène (lue dans le jeu), en gardant nos teintes
    lum = carte @ np.array([0.299, 0.587, 0.114], np.float32)
    m_lum, s_lum = float(lum[dedans].mean()), float(lum[dedans].std())
    # Vu en jeu le 12/11/2026 : calée sur la clarté de la carte de Bollène (86 sur 255), la carte donnait un sol
    # anthracite sous les arbres ; les talus de terre claire, eux, étaient justes. La clarté moyenne est donc remontée,
    # sans toucher au contraste ni aux teintes.
    gain = 1.0
    moy = carte[dedans].mean(0)
    carte = carte * (SOL_CARTE_CIBLE["moyenne"] / m_lum)
    carte = np.clip(carte, 0, 255).astype(np.uint8)
    P.texture("T_Sol_Carte", "terrain_jeu", tex_dest, Image.fromarray(carte, "RGB"), essais, adressage="Wrap", qualite=92)
    scal = {"UVDivideWP": float(diviseur), "U_Add": S * 50.0 - centre[0] * 100.0, "V_Add": S * 50.0 - centre[1] * 100.0}

    # masques et maillages, cellule par cellule
    prop = np.load(src / "proportions_l93.npz")
    couches = [prop[k] for k in meta["couches"]]                     # aiguilles, herbe haute, herbe sèche, terre, cailloux
    pas = meta["pas_m"]
    n = SOL_MASQUE_PX
    f = (np.arange(n) + 0.5) / n
    v, u = np.meshgrid(f, f, indexing="ij")
    parts = np.zeros(6)
    for (i, j), (p_c, n_c, xy_c, t_c) in cellules.items():
        suf = f"{i - i0:02d}{j - j0:02d}"
        X, Y = (i + 1.0 - u) * SOL_CELLULE_M, (j + 1.0 - v) * SOL_CELLULE_M
        x93, y93 = pl.l93(X, Y)
        coord = [(e[3] - y93) / pas - 0.5, (x93 - e[0]) / pas - 0.5]
        pr = [ndi.map_coordinates(c, coord, order=1, mode="nearest").astype(np.float32) / 255.0 for c in couches]
        # le jeu superpose ses matières dans l'ordre 2 à 6 : la part voulue de chacune devient une opacité
        reste = np.ones_like(pr[0])
        m = [None] * 5
        for k in (4, 3, 2, 1, 0):
            m[k] = np.clip(pr[k] / np.maximum(reste, 1e-3), 0.0, 1.0)
            reste = np.clip(reste - pr[k], 0.0, 1.0)
        parts += np.array([reste.mean()] + [x.mean() for x in pr])
        a = np.clip(np.stack(m[:4], -1) * 255.0 + 0.5, 0, 255).astype(np.uint8)
        b = np.zeros_like(a)
        b[..., 0] = np.clip(m[4] * 255.0 + 0.5, 0, 255).astype(np.uint8)
        P.masque(f"T_Sol_{suf}_M1", "terrain_jeu", tex_dest, a, essais)
        P.masque(f"T_Sol_{suf}_M2", "terrain_jeu", tex_dest, b, essais)
        P.materiau_du_jeu(f"MI_Sol_{suf}", mat_dest, SOL_PARENT,
                          {"MasksA (T2d)": f"T_Sol_{suf}_M1", "MasksB (T2d)": f"T_Sol_{suf}_M2", "Texture": "T_Sol_Carte"},
                          scal, essais, reglages=reglages_du_sol())
        uv = np.clip(np.column_stack([i + 1.0 - xy_c[:, 0] / SOL_CELLULE_M, j + 1.0 - xy_c[:, 1] / SOL_CELLULE_M]), 0.0, 1.0)
        P.maillage(f"SM_{NOM}Sol_{suf}", "terrain_jeu", mesh_dest, p_c, n_c, uv, t_c, f"MI_Sol_{suf}", essais,
                   extra={"cellule_du_jeu": [i, j], "emprise_monde_m": [i * SOL_CELLULE_M, j * SOL_CELLULE_M,
                                                                        (i + 1) * SOL_CELLULE_M, (j + 1) * SOL_CELLULE_M]},
                   couleur_nulle=True)
    parts /= len(cellules)
    P.sol = {"mode": "jeu", "parent": SOL_PARENT, "cellule_m": SOL_CELLULE_M, "masque_px": SOL_MASQUE_PX,
             "placement": {k: pl.p[k] for k in ("theta_deg", "cx", "cz", "tx", "dy", "tz")},
             "carte": {"px": SOL_CARTE_PX, "cote_m": S, "centre_monde_m": centre.tolist(), **scal,
                       "clarte_avant": round(m_lum, 1), "contraste_avant": round(s_lum, 1), "gain": round(gain, 3)},
             "parts_moyennes": dict(zip(["paillis"] + meta["couches"], [round(float(x), 3) for x in parts]))}
    return {"cellules": len(cellules), "triangles_coupes": n_coupes, "triangles_source": int(len(tri)),
            "sommets_sous_la_chaussee": int(len(sous)), "sommets_abaisses_sous_la_chaussee": n_abaisses,
            "triangles": int(sum(len(c[3]) for c in cellules.values()))}


def troncon(pk):
    return int(math.floor((pk + 200.0) / TRONCON))


def par_troncon(P, pkf, meshes, prefixe, famille, dest_mesh, nom_mat, args, groupe_par_materiau=True):
    """Fusionne les maillages par (tronçon de 200 m, matériau) puis écrit un glb par groupe."""
    groupes = {}
    for m in meshes:
        c = m["pos"][m["idx"]].mean(1)
        k = np.array([troncon(p) for p in pkf(c)])
        for kk in np.unique(k):
            sel = k == kk
            cle = (int(kk), m["mat"]["nom"])
            groupes.setdefault(cle, []).append(sous_maillage(m["pos"], m["nrm"], m["uv"], m["idx"], sel))
    out = []
    for (kk, mat), parts in sorted(groupes.items()):
        pk0 = kk * TRONCON - 200.0
        pkr = (pk0, pk0 + TRONCON)
        essais = essais_par_pk(pkr)
        if not P.garde(essais) or (args.pk_min is not None and not recouvre(pkr, args.pk_min, args.pk_max)):
            continue
        pos = np.vstack([p[0] for p in parts])
        nrm = np.vstack([p[1] for p in parts])
        uv = np.vstack([p[2] if p[2] is not None else np.zeros((len(p[0]), 2)) for p in parts])
        off = np.cumsum([0] + [len(p[0]) for p in parts])
        tri = np.vstack([p[3] + off[i] for i, p in enumerate(parts)])
        suffixe = f"_{mat.capitalize()}" if groupe_par_materiau else ""
        nom = f"SM_{NOM}{prefixe}{suffixe}_{kk:02d}"
        # enrobé : son parent est l'asphalte de Bollène, dont les routes ont des sommets presque noirs (rouge 0 à 10,
        # vert et bleu toujours nuls) ; sans couleur, Unreal donnerait du blanc opaque
        couleur = None
        if not P.echantillon:
            if mat == "enrobe":
                couleur = (0, 0, 0, 0)
            elif mat == "marquage" and "MI_GC_Marquage" in MATIERES.get("materiaux", {}):
                # décalque de marquage du jeu : sa peinture est dépliée à 1,5 m par unité dans les deux sens (nos lignes
                # l'étaient à leur largeur en travers, au mètre en long) ; couleur de sommet blanche = peinture pleine
                uv = uv * np.array([0.12 / 1.5, 1.0 / 1.5])
                couleur = (255, 255, 255, 255)
            elif mat in MURS_DU_JEU:
                # dépliage ramené à celui des murs du jeu dont la matière est héritée, et leur couleur de sommet
                uv = uv * MURS_DU_JEU[mat]["uv"]
                couleur = MURS_DU_JEU[mat]["couleur"]
        P.maillage(nom, famille, dest_mesh, pos, nrm, uv, tri, nom_mat(mat), essais, pk=pkr,
                   extra={"troncon": kk}, couleur=couleur)
        out.append(nom)
    return out


def materiaux_modele(P, glbs, dest_tex, dest_mat, prefixe_mat):
    """Une texture et une variante par matériau des glb 11 / 12 (image intégrée, ou couleur unie 8 x 8)."""
    vus = {}
    for meshes in glbs:
        for m in meshes:
            mat = m["mat"]
            if mat["nom"] in vus:
                continue
            nom_t = f"T_GC_{prefixe_mat}{mat['nom'].capitalize()}"
            if mat["image"] is not None:
                src = mat["image"]
                im = Image.open(src if isinstance(src, Path) else io.BytesIO(src)).convert("RGB")
            else:
                im = image_unie(lin_vers_srgb(mat["couleur"][:3]))
            P.texture(nom_t, "modele", dest_tex, im, ["E3", "E4", "complet"])
            r = int(round(255 * float(mat["rugosite"])))
            mt = int(round(255 * float(mat["metal"])))
            nom_orm = f"T_GC_ORM_R{r:03d}M{mt:03d}"
            if nom_orm not in P.vus:
                P.texture(nom_orm, "commun", f"{UE}/Shared/Textures", image_unie((255, r, mt)), ["E3", "E4", "complet"])
            nom_mi = f"MI_GC_{prefixe_mat}{mat['nom'].capitalize()}"
            P.materiau(nom_mi, dest_mat, {"couleur": nom_t, "orm": nom_orm}, ["E3", "E4", "complet"],
                       alternatif="/Game/Environments/RallyShared/Materials/M_AsphaltMaster_Adv"
                       if mat["nom"] == "enrobe" else None)
            vus[mat["nom"]] = nom_mi
    return vus


class Pentes:
    """Pente du relief (RGE ALTI à 5 m, puis à 25 m au-delà) en un point Lambert-93, pour teinter les falaises."""

    def __init__(self):
        import rasterio
        self.couches = []
        for nom, cle in (("rgealti_5m.tif", "pente_5m_deg"),):
            p = ROOT / "data" / "raw" / "lointain" / nom
            if not p.exists():
                continue
            with rasterio.open(p) as d:
                z, t, nd = d.read(1).astype(np.float32), d.transform, d.nodata
            ok = np.isfinite(z) & (z != nd) if nd is not None else np.isfinite(z)
            z = np.where(ok, z, 0.0).astype(np.float32)
            gl, gc = np.gradient(z, abs(t.e), t.a)
            pente = np.degrees(np.arctan(np.hypot(gl, gc))).astype(np.float32)
            from scipy import ndimage
            pente[~ndimage.binary_erosion(ok, iterations=2)] = 0.0          # pas de fausse falaise au bord des données
            self.couches.append((pente, z, ok, t, FALAISE[cle]))

    def roche(self, x, y):
        """Part de roche (0 à 1) et altitude en chaque point (tableaux Lambert-93 de même forme)."""
        from scipy import ndimage
        w, alt, fait = np.zeros(x.shape, np.float32), np.zeros(x.shape, np.float32), np.zeros(x.shape, bool)
        for pente, z, ok, t, (a, b) in self.couches:
            c, l = (x - t.c) / t.a - 0.5, (y - t.f) / t.e - 0.5
            ici = ~fait & (c >= 0) & (l >= 0) & (c <= z.shape[1] - 1) & (l <= z.shape[0] - 1)
            if not ici.any():
                continue
            cl = np.vstack([l[ici], c[ici]])
            ici[ici] = ndimage.map_coordinates(ok.astype(np.float32), cl, order=0) > 0.5
            cl = np.vstack([l[ici], c[ici]])
            s = np.clip((ndimage.map_coordinates(pente, cl, order=1) - a) / (b - a), 0.0, 1.0)
            w[ici], alt[ici] = s * s * (3.0 - 2.0 * s), ndimage.map_coordinates(z, cl, order=1)
            fait |= ici
        return w, alt


def teinte_falaises(im, m, ref, pentes):
    """Image de la dalle lointaine `m` avec ses versants très raides teintés de calcaire ; part de l'image teintée.

    La position Lambert-93 de chaque pixel vient des sommets de la dalle (u vers l'est, v vers le sud, origine en
    haut à gauche de l'image : convention de 13_paysage_lointain.py)."""
    uv, g = m["uv"].astype(np.float64), m["pos"]
    X, Y = g[:, 0] + ref["x0"], ref["y0"] - g[:, 2]
    if np.ptp(uv[:, 0]) < 1e-6 or np.ptp(uv[:, 1]) < 1e-6:
        return im, 0.0
    ax, bx = np.polyfit(uv[:, 0], X, 1)
    ay, by = np.polyfit(uv[:, 1], Y, 1)
    W, H = im.size
    u, v = (np.arange(W) + 0.5) / W, (np.arange(H) + 0.5) / H
    xx, yy = np.meshgrid(ax * u + bx, ay * v + by)
    w, alt = pentes.roche(xx, yy)
    if w.max() <= 0:
        return im, 0.0
    from scipy import ndimage
    r = FALAISE["elargir_m"] / max(abs(ax) / W, 1e-6)                     # en pixels de cette image
    if r >= 0.75:
        w = ndimage.gaussian_filter(ndimage.maximum_filter(w, size=2 * int(round(r)) + 1), max(r / 2.0, 0.6))
    a = np.asarray(im, np.float32)
    # la roche n'est pas unie : grain tiré de l'image elle-même
    grain = 0.85 + 0.30 * (a.mean(2) / max(float(a.mean()), 1.0)).clip(0.5, 1.5) / 1.5
    roche = np.array(FALAISE["couleur"], np.float32)[None, None, :] * grain[:, :, None]
    k = (FALAISE["taux"] * w)[:, :, None]
    return Image.fromarray(np.clip((1.0 - k) * a + k * roche + 0.5, 0, 255).astype(np.uint8), "RGB"), float((w > 0.5).mean())


def lointain(P, ref, args, pkf):
    """Anneau lointain : un maillage par dalle de 13 (1 km près, 5 km loin), ses images JPEG telles quelles.

    Normales adoucies (--lointain-aplat) : la photo aérienne porte déjà l'ombre du relief ; éclairé en plus par le
    soleil du jeu, un versant à l'ombre devenait très sombre (vu en jeu le 12/11/2026, massif du km 3,9). Les normales
    sont donc ramenées vers la verticale, de 0 % à moins de LOIN_APLAT_DE m de la route (continuité avec notre
    terrain) jusqu'au taux demandé au-delà de LOIN_APLAT_A m. La forme du relief ne change pas."""
    src = MOD / "apercu" / "lointain.glb" if P.echantillon else MOD / "lointain.glb"   # échantillon : version légère
    ms = lire_glb(src)
    centre_e4 = None
    n = 0
    pentes = Pentes() if not P.echantillon and args.falaises else None
    teintees = []
    for m in ms:
        _, taille, kx, ky = m["nom"].split("_")
        kx, ky = int(kx), int(ky)
        L = "" if taille == "1km" else "L"
        i, j = (kx - LOIN0[0]) // 1000, (ky - LOIN0[1]) // 1000      # km depuis le coin sud-ouest de l'anneau
        suf = f"{i}_{j}"
        g = m["pos"]
        if centre_e4 is None:
            centre_e4 = P._centre_e4
        dmin = float(np.min(np.hypot(g[:, 0] - centre_e4[0], g[:, 2] - centre_e4[2])))
        essais = (["E4"] if taille == "1km" and dmin < 1500 else []) + ["complet"]
        if not P.garde(essais):
            continue
        nom_t, nom_mi, nom_sm = f"T_FarRing{L}_{suf}", f"MI_FarRing{L}_{suf}", f"SM_{NOM}FarRing{L}_{suf}"
        im = Image.open(io.BytesIO(m["mat"]["image"])).convert("RGB")
        if not P.echantillon and args.lointain_clarte:
            # même courbe pour toutes les dalles, pour ne pas créer de marche entre voisines : les forêts vues du ciel
            # sont très sombres sur la photo (66 sur 255 pour le massif au sud), et bleu ardoise une fois dans le jeu
            a = np.asarray(im, np.float32) / 255.0
            im = Image.fromarray(np.clip(255.0 * LOIN_GAIN * a ** LOIN_GAMMA + 0.5, 0, 255).astype(np.uint8), "RGB")
        if pentes is not None:
            im, part = teinte_falaises(im, m, ref, pentes)
            if part > 0:
                teintees.append((part, nom_t))
        P.texture(nom_t, "lointain", f"{UE}/FarRing/Textures", im, essais, adressage="Clamp",
                  px_max=256 if P.echantillon else None, qualite=90)
        if "T_GC_ORM_Lointain" not in P.vus:
            P.texture("T_GC_ORM_Lointain", "commun", f"{UE}/Shared/Textures", image_unie((255, 255, 0)), ["E4", "complet"])
        P.materiau(nom_mi, f"{UE}/FarRing/Materials", {"couleur": nom_t, "orm": "T_GC_ORM_Lointain"}, essais,
                   note="anneau lointain : sans ombre portée ; pas de relief")
        nrm = m["nrm"]
        aplat = 0.0 if P.echantillon else float(args.lointain_aplat)
        if aplat > 0:
            d = pkf.t.query(g[:, [0, 2]])[0]
            t = np.clip((d - LOIN_APLAT_DE) / (LOIN_APLAT_A - LOIN_APLAT_DE), 0.0, 1.0)
            k = (aplat * t * t * (3.0 - 2.0 * t))[:, None]
            nrm = (1.0 - k) * nrm + k * np.array([0.0, 1.0, 0.0])
            nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
        P.maillage(nom_sm, "lointain", f"{UE}/FarRing/Meshes", m["pos"], nrm, m["uv"], m["idx"], nom_mi, essais,
                   extra={"distance_min_e4_m": round(dmin), "source": f"{src.relative_to(ROOT).as_posix()}#{m['nom']}",
                          **({"normales_adoucies": aplat} if aplat > 0 else {})})
        n += 1
    if teintees:
        print(f"  falaises : {len(teintees)} images lointaines teintées ; les plus rocheuses : "
              + ", ".join(f"{t} {100 * p:.0f} %" for p, t in sorted(teintees, reverse=True)[:4]))
    return n


def mire_relief(P):
    """Normal map d'un dôme (256 px), dans la convention du paquet (DirectX) : la moitié HAUTE de l'image est
    violacée (vert faible), la moitié BASSE verdâtre ; la moitié droite plus rouge que la gauche. Posée sur un
    plan éclairé, elle doit paraître BOMBÉE ; si elle paraît creusée de haut en bas, le canal vert est inversé."""
    n = 256
    y, x = np.mgrid[0:n, 0:n] + 0.5
    u, v = (x - n / 2) / (n * 0.4), (n / 2 - y) / (n * 0.4)              # v > 0 : haut de l'image (nord)
    r2 = u * u + v * v
    dome = r2 < 1
    nx, ny = np.where(dome, u, 0.0), np.where(dome, v, 0.0)
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0.05, 1))
    a = np.clip((np.dstack([nx, ny, nz]) * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8)   # OpenGL (Y+)
    P.texture("T_GC_MireRelief", "mire", f"{EDITEUR}/Mire", Image.fromarray(releve_vert(a)), ["E3", "E4", "complet"],
              relief=True)


def mire(P):
    """Trois barres le long des axes du FICHIER glb (4 m en X, 2 m en Y, 1 m en Z), à importer d'abord :
    leurs bornes après import donnent la correspondance d'axes de l'importeur (construire_niveau.py --mire)."""
    for axe, L in (("X", 4.0), ("Y", 2.0), ("Z", 1.0)):
        k = "XYZ".index(axe)
        lo = np.full(3, -0.05)
        hi = np.full(3, 0.05)
        lo[k], hi[k] = 0.0, L
        c = np.array([[lo[0], lo[1], lo[2]], [hi[0], lo[1], lo[2]], [hi[0], hi[1], lo[2]], [lo[0], hi[1], lo[2]],
                      [lo[0], lo[1], hi[2]], [hi[0], lo[1], hi[2]], [hi[0], hi[1], hi[2]], [lo[0], hi[1], hi[2]]])
        tri = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
                        [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
        nrm = c - c.mean(0)
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
        nom = f"SM_GC_MireAxe{axe}"
        fichier = Path("maillages") / "mire" / f"{nom}.glb"
        ecrire_glb(P.sortie / fichier, nom, "MI_GC_Mire", c, nrm, None, tri)
        P.ajoute({"type": "StaticMesh", "nom": nom, "fichier": fichier.as_posix(), "destination": f"{EDITEUR}/Mire",
                  "chemin_ue": f"{EDITEUR}/Mire/{nom}", "section_materiau": "MI_GC_Mire", "materiau": None,
                  "import": IMPORT_MAILLAGE, "acteur": None, "mire": {"axe_fichier": axe, "longueur_m": L},
                  "essais": ["E3", "E4", "complet"]})


# --- instances --------------------------------------------------------------------------------------------
class Sol:
    """Altitude du terrain de terrain_sol.glb en un point (interpolation dans ses triangles) : les arbres
    sont posés sur le maillage importé, pas sur le MNT brut."""

    def __init__(self):
        ms = lire_glb(MOD / "terrain_sol.glb")
        self.T = np.vstack([m["pos"][m["idx"]] for m in ms])           # (n, 3 sommets, xyz glTF)
        self.arbre = cKDTree(self.T[:, :, [0, 2]].mean(1))

    def __call__(self, gx, gz, k=16):
        """Altitude interpolée dans le triangle qui contient (gx, gz) ; NaN hors terrain."""
        q = np.column_stack([gx, gz])
        _, cand = self.arbre.query(q, k=k)
        z = np.full(len(q), np.nan)
        reste = np.ones(len(q), bool)
        for j in range(k):
            t = self.T[cand[:, j]]
            a, b, c = t[:, 0, [0, 2]], t[:, 1, [0, 2]], t[:, 2, [0, 2]]
            v0, v1, v2 = b - a, c - a, q - a
            den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
            ok = np.abs(den) > 1e-12
            den = np.where(ok, den, 1)
            u = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den
            v = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
            dedans = ok & (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6) & reste
            zz = t[:, 0, 1] + u * (t[:, 1, 1] - t[:, 0, 1]) + v * (t[:, 2, 1] - t[:, 0, 1])
            z[dedans] = zz[dedans]
            reste &= ~dedans
        return z


# Arbres des versants proches (--arbres-lointains) : le semis relevé s'arrête à 135 m de l'axe ; au-delà le relief
# lointain n'est qu'une surface peinte, jugée plate et floue en jeu le 13/11/2026. Des arbres du jeu y sont plantés
# jusqu'à ARBRES_LOIN["a_m"], là où le relevé de hauteur de végétation de l'IGN montre de la forêt. Ils sont posés au
# sol : la surface lointaine passe à hauteur de houppier, seules leurs cimes en sortent, ce qui donne aux crêtes une
# silhouette d'arbres. Positions tirées au sort (graine fixe) : un habillage, pas un relevé. Aucune collision.
ARBRES_LOIN = {"de_m": 135.0, "a_m": 430.0, "pas_m": 8.5, "mnh_min_m": 3.0, "part_pin": 0.65, "depasse_m": (2.0, 4.0),
               "disparition_cm": [95000, 130000],
               "pin": ("Foliage/Trees/AleppoPine", "SM_AleppoPine04", "pin d'Alep"),
               "feuillu": ("Foliage/Trees/Smoketree", "SM_Smoketree01", "chêne vert")}


def arbres_lointains(ref):
    """Lignes au format de data/processed/arbres.csv pour les versants entre le semis relevé et ARBRES_LOIN["a_m"]."""
    import rasterio
    f_mnh, f_alt = ROOT / "data" / "raw" / "lointain" / "mnh_5m.tif", ROOT / "data" / "raw" / "lointain" / "rgealti_5m.tif"
    if not (f_mnh.exists() and f_alt.exists()):
        return []
    with open(OUT / "chaussee_precise.csv", encoding="utf-8") as h:
        axe = np.array([[float(r["x_axe"]), float(r["y_axe"])] for r in csv.DictReader(h)])
    rng = np.random.default_rng(SEED + 31)
    pas, R = ARBRES_LOIN["pas_m"], ARBRES_LOIN["a_m"]
    xs = np.arange(axe[:, 0].min() - R, axe[:, 0].max() + R, pas)
    ys = np.arange(axe[:, 1].min() - R, axe[:, 1].max() + R, pas)
    X, Y = np.meshgrid(xs, ys)
    X = (X + rng.uniform(-0.45, 0.45, X.shape) * pas).ravel()
    Y = (Y + rng.uniform(-0.45, 0.45, Y.shape) * pas).ravel()
    d, _ = cKDTree(axe[::3]).query(np.column_stack([X, Y]))
    sel = (d >= ARBRES_LOIN["de_m"]) & (d <= R)
    X, Y, d = X[sel], Y[sel], d[sel]

    def lire(fichier):
        with rasterio.open(fichier) as src:
            v = np.array([q[0] for q in src.sample(np.column_stack([X, Y]))], float)
            return np.where((v == src.nodata) | (v < -1000), np.nan, v)

    mnh, alt = lire(f_mnh), lire(f_alt)
    ok = np.isfinite(mnh) & np.isfinite(alt) & (mnh >= ARBRES_LOIN["mnh_min_m"])
    # moins dense en s'éloignant : on ne distingue plus les arbres un à un au-delà de 300 m
    ok &= rng.random(len(X)) < np.clip(1.15 - 0.55 * (d - ARBRES_LOIN["de_m"]) / (R - ARBRES_LOIN["de_m"]), 0.4, 1.0)
    X, Y, d, mnh, alt = X[ok], Y[ok], d[ok], mnh[ok], alt[ok]
    haut = np.clip(mnh + rng.uniform(*ARBRES_LOIN["depasse_m"], len(X)), 5.0, 18.0)
    pin = rng.random(len(X)) < ARBRES_LOIN["part_pin"]
    rows = []
    for i in range(len(X)):
        fam, elt, ess = ARBRES_LOIN["pin" if pin[i] else "feuillu"]
        rows.append({"x_l93": f"{X[i]:.2f}", "y_l93": f"{Y[i]:.2f}", "z_sol_m": f"{alt[i]:.2f}", "hauteur_m": f"{haut[i]:.1f}",
                     "diametre_houppier_m": f"{0.7 * haut[i]:.1f}", "essence": ess, "famille_jeu": fam, "element_jeu_propose": elt,
                     "regle_essence": "versant lointain", "dist_axe_m": f"{d[i]:.1f}", "pk_m": "", "cote": "", "detection": "tirage"})
    print(f"  arbres des versants : {len(rows)} entre {ARBRES_LOIN['de_m']:.0f} et {R:.0f} m de l'axe ({int(pin.sum())} pins)")
    return rows


# Sous-bois de bord de route (--sous-bois) : vu sur les paires jeu / reconnaissance du 13/11/2026, la route réelle court
# entre deux murs de végétation de 2 à 5 m (chênes verts, arbustes), alors que le semis relevé ne compte que les grands
# arbres (1 800 à moins de 10 m de l'axe) et des buissons de moins de 2 m. De petits arbres sont donc ajoutés dans une
# bande le long de chaque bord, là où le relevé laser (hauteur au-dessus du sol) montre de la végétation. La règle de
# dégagement (scripts/regles_arbres.py) les tient hors de la chaussée. Positions tirées au sort ; aucune collision.
SOUS_BOIS = {"de_m": 1.7, "a_m": 9.0, "pas_m": 1.1, "par_pas": 2, "mnh_min_m": 1.3, "garde": 0.6, "voisin_min_m": 1.3,
             "hauteur_m": (1.6, 4.8), "famille": ("Foliage/Trees/Smoketree", "SM_Smoketree01", "chêne vert")}


def sous_bois_de_bord(ref, arbres):
    import rasterio
    f_mns, f_mnt = ROOT / "data" / "raw" / "mns_lidarhd_50cm.tif", ROOT / "data" / "raw" / "mnt_lidarhd_50cm.tif"
    if not (f_mns.exists() and f_mnt.exists()):
        return []
    with open(OUT / "chaussee_precise.csv", encoding="utf-8") as h_:
        r_ = list(csv.DictReader(h_))
    ch = {"pk": np.array([float(x["pk_m"]) for x in r_]),
          "A": np.array([[float(x["x_axe"]), float(x["y_axe"])] for x in r_]),
          "G": np.array([[float(x["x_gauche"]), float(x["y_gauche"])] for x in r_]),
          "D": np.array([[float(x["x_droite"]), float(x["y_droite"])] for x in r_])}
    rng = np.random.default_rng(SEED + 53)
    pk = ch["pk"]
    S = np.arange(pk[0] + 2.0, pk[-1] - 2.0, SOUS_BOIS["pas_m"])
    A = np.column_stack([np.interp(S, pk, ch["A"][:, k]) for k in (0, 1)])
    pts = []
    for cle in ("G", "D"):
        E = np.column_stack([np.interp(S, pk, ch[cle][:, k]) for k in (0, 1)])
        n = E - A
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        t = np.gradient(E, axis=0)
        t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
        for _ in range(SOUS_BOIS["par_pas"]):
            d = SOUS_BOIS["de_m"] + (SOUS_BOIS["a_m"] - SOUS_BOIS["de_m"]) * rng.random(len(S)) ** 1.5      # plus dense près du bord
            pts.append(np.column_stack([E + n * d[:, None] + t * rng.uniform(-0.5, 0.5, (len(S), 1)), np.repeat(S, 1)]))
    Q = np.vstack(pts)
    Q = Q[rng.random(len(Q)) < SOUS_BOIS["garde"]]
    with rasterio.open(f_mns) as a_, rasterio.open(f_mnt) as b_:
        zs = np.array([v[0] for v in a_.sample(Q[:, :2])], float)
        zt = np.array([v[0] for v in b_.sample(Q[:, :2])], float)
    mnh = zs - zt
    ok = np.isfinite(mnh) & (zt > -1000) & (zs > -1000) & (mnh >= SOUS_BOIS["mnh_min_m"])
    if arbres:                                                   # pas dans le pied d'un arbre du semis
        tr = cKDTree(np.array([[float(r["x_l93"]), float(r["y_l93"])] for r in arbres]))
        ok &= tr.query(Q[:, :2])[0] >= SOUS_BOIS["voisin_min_m"]
    Q, mnh, zt = Q[ok], mnh[ok], zt[ok]
    h0, h1 = SOUS_BOIS["hauteur_m"]
    haut = np.clip(np.minimum(mnh, h1 * 1.2) * rng.uniform(0.6, 1.0, len(Q)), h0, h1)
    fam, elt, ess = SOUS_BOIS["famille"]
    rows = [{"x_l93": f"{Q[i, 0]:.2f}", "y_l93": f"{Q[i, 1]:.2f}", "z_sol_m": f"{zt[i]:.2f}", "hauteur_m": f"{haut[i]:.1f}",
             "diametre_houppier_m": f"{0.9 * haut[i]:.1f}", "essence": ess, "famille_jeu": fam, "element_jeu_propose": elt,
             "regle_essence": "sous-bois de bord de route", "dist_axe_m": "", "pk_m": f"{Q[i, 2]:.0f}", "cote": "", "detection": "tirage"}
            for i in range(len(Q))]
    print(f"  sous-bois de bord de route : {len(rows)} petits arbres de {h0} à {h1} m, entre {SOUS_BOIS['de_m']} et {SOUS_BOIS['a_m']} m du bord")
    return rows


def instances(P, ref, sol, ruban, pkf, args):
    """Tables d'instances (cm, degrés, repère Unreal du projet), une par maillage du jeu."""
    cat = set()
    with gzip.open(sorted(REF.glob("catalogue_jeu_*.txt.gz"))[-1], "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.endswith(".uasset"):
                cat.add("/Game/" + line[len("acr/Content/"):-len(".uasset")])
    bilan = {}
    rng = np.random.default_rng(SEED)
    emprises = regles_arbres.emprises_degagees(ROOT)
    degagee = shapely.union_all([g_ for g_, _ in emprises]) if emprises else None
    if degagee is not None:
        shapely.prepare(degagee)

    def table(famille, rows, chemin_de, hauteur, extra_cols, sur_terrain=True, degagement=None, reglages=None, ajuster=None):
        x = np.array([float(r["x_l93"]) for r in rows])
        y = np.array([float(r["y_l93"]) for r in rows])
        zc = np.array([float(r.get("z_sol_m") or r.get("z_m")) for r in rows])
        g = m08.to_gltf(np.column_stack([x, y, zc]), ref).astype(float)
        if sur_terrain:
            zs = sol(g[:, 0], g[:, 2])
            g[:, 1] = np.where(np.isfinite(zs), zs, g[:, 1])
        ue = Axes.ue(g)
        lacet = rng.uniform(-180.0, 180.0, len(rows))
        pk = pkf(g)
        sur_chaussee = shapely.contains_xy(ruban, x, y)
        if degagee is not None:                              # aires et débouchés de pistes : ni arbre ni buisson
            sur_chaussee |= shapely.contains_xy(degagee, x, y)
        if degagement is not None:
            # Dégagement : une plante trop près du bord de chaussée est retirée, pas seulement celle qui est dessus.
            # Vu en jeu le 12/11/2026 (km 0,1) : des branches basses barraient la route jusqu'au pare-brise.
            marge = np.array([degagement(r) for r in rows])
            sur_chaussee |= shapely.distance(ruban, shapely.points(x, y)) < marge
        h_voulue = np.array([hauteur(r) for r in rows])
        chemins = [chemin_de(r) for r in rows]
        reduits = 0
        if ajuster is not None:
            # arbres : houppier du maillage du jeu tenu hors de la chaussée (scripts/regles_arbres.py) ; trop grand
            # pour sa place, l'arbre est réduit, et prend au besoin un maillage d'une famille à petits sujets
            dist = shapely.distance(ruban, shapely.points(x, y))
            for i in np.flatnonzero(dist < 12.0):
                garde, h_i, fam, elt = ajuster(rows[i], float(dist[i]))
                if not garde:
                    sur_chaussee[i] = True
                elif h_i < h_voulue[i] - 1e-6:
                    h_voulue[i] = h_i
                    reduits += 1
                    if elt:
                        chemins[i] = f"/Game/{fam}/{elt}"
        groupes = {}
        for i, r in enumerate(rows):
            groupes.setdefault(chemins[i], []).append(i)
        for chemin, ids in sorted(groupes.items()):
            nom = chemin.rsplit("/", 1)[1]
            ids = np.array(ids)
            ids = ids[~sur_chaussee[ids]]
            pk_sel = pk[ids]
            essais = (["E4"] if ((pk_sel >= PK_E4[0]) & (pk_sel <= PK_E4[1])).any() else []) + ["complet"]
            if P.echantillon:
                ids = ids[(pk_sel >= PK_E4[0]) & (pk_sel <= PK_E4[1])]
                essais = ["E4"]
            if args.pk_min is not None:
                ids = ids[(pk[ids] >= args.pk_min) & (pk[ids] <= args.pk_max)]
            if not len(ids):
                continue
            fichier = Path("instances") / famille / f"{nom}.csv"
            out = P.sortie / fichier
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(["id", "x_cm", "y_cm", "z_cm", "lacet_deg", "hauteur_voulue_m", "pk_m"] + extra_cols)
                for i in ids:
                    r = rows[i]
                    w.writerow([i, f"{ue[i, 0]:.1f}", f"{ue[i, 1]:.1f}", f"{ue[i, 2]:.1f}", f"{lacet[i]:.1f}",
                                f"{h_voulue[i]:.2f}", f"{pk[i]:.0f}"] + [r.get(c, "") for c in extra_cols])
            e = P.ajoute({"type": "InstanceGroup", "nom": f"GC_{famille.capitalize()}_{nom}", "maillage_jeu": chemin,
                          "present_au_catalogue": chemin in cat, "fichier": fichier.as_posix(), "nombre": int(len(ids)),
                          "composant": "HierarchicalInstancedStaticMeshComponent", "collision": "NoCollision",
                          "hauteur_native_cm": None,
                          "echelle": "à l'import, scripts_editeur/attribution.py rechoisit le maillage dans ce dossier "
                                     "d'après la taille de chaque plante (releves/maillages_vegetation.json) et en "
                                     "déduit l'échelle ; le maillage nommé ici est tiré sans connaître les tailles",
                          "retirees_sur_chaussee": int(sur_chaussee[np.array(groupes[chemin])].sum()),
                          "essais": essais})
            if reglages and reglages(chemin):
                e.update(reglages(chemin))
            bilan[e["nom"]] = e["nombre"]
        if ajuster is not None:
            print(f"  {famille} : {int(sur_chaussee.sum())} retirés (sur la chaussée ou trop près), {reduits} réduits pour ne pas déborder")

    with open(OUT / "arbres.csv", encoding="utf-8") as f:
        arbres = list(csv.DictReader(f))
    if args.sous_bois and not P.echantillon and args.pk_min is None:
        arbres += sous_bois_de_bord(ref, arbres)
    loin = arbres_lointains(ref) if args.arbres_lointains and not P.echantillon and args.pk_min is None else []
    def chemin_arbre(r):
        """Les grands chênes verts étaient rendus par un érable du jeu (BlackmapleMonteCarlo, 13 à 20 m, grandes feuilles) :
        vu en jeu le 13/11/2026, « feuillus tempérés » au lieu de chênes verts. Le Smoketree du jeu, à petites feuilles
        vertes et à houppier rond, en est plus proche ; il rend désormais tous les chênes verts."""
        if r["essence"] == "chêne vert" and r["famille_jeu"] == "Foliage/Trees/BlackmapleMonteCarlo":
            return "/Game/Foliage/Trees/Smoketree/SM_Smoketree06"
        return f"/Game/{r['famille_jeu']}/{r['element_jeu_propose']}"

    table("arbres", arbres, chemin_arbre,
          lambda r: float(r["hauteur_m"]), ["essence", "diametre_houppier_m"],
          ajuster=lambda r, d: regles_arbres.ajuste(float(r["hauteur_m"]), d, r["famille_jeu"]))
    if loin:
        # Arbres des versants : un groupe à part, sans ombre portée et masqué au-delà d'un kilomètre environ. Ils sont
        # 29 000 de plus ; avec les ombres et sans limite de distance, ils pèseraient sur la fluidité pour rien.
        table("versants", loin, chemin_arbre, lambda r: float(r["hauteur_m"]), ["essence", "diametre_houppier_m"],
              reglages=lambda chemin: {"distances_de_disparition_cm": ARBRES_LOIN["disparition_cm"], "ombre_dynamique": False})
    with gzip.open(OUT / "arbustes.csv.gz", "rt", encoding="utf-8") as f:
        arbustes = list(csv.DictReader(f))
    buissons_jeu = args.buissons == "jeu" and not P.echantillon

    def chemin_arbuste(r):
        """Le script 10 propose une plante rampante plate (BroomCreeper) pour les arbustes de 0,4 à 1 m et un arbre
        (Boxthorn, 3,5 à 12 m) pour ceux de 1 à 2 m, que l'import réduisait au tiers. Le jeu a de vrais buissons
        vert olive de 0,5 à 1,4 m (GroundCover/Willow, ceux de Bollène) : ils prennent les arbustes de 0,55 m et
        plus, sauf un quart de ceux de 1,3 m et plus, laissés en Boxthorn pour varier et rester visibles de loin."""
        h = float(r["hauteur_m"])
        if buissons_jeu and h >= BUISSONS["hauteur_min_m"] and (
                h < BUISSONS["boxthorn_a_partir_de_m"] or zlib.crc32(f"{r['x_l93']}:{r['y_l93']}".encode()) % 4):
            return BUISSONS["maillage"]
        return f"/Game/{r['famille_jeu']}/{r['element_jeu_propose']}"

    table("arbustes", arbustes, chemin_arbuste,
          lambda r: float(r["hauteur_m"]), ["diametre_m"],
          # buissons et couvre-sols : leur demi-diamètre plus 0,5 m
          degagement=lambda r: 0.5 + 0.5 * float(r.get("diametre_m") or 0),
          reglages=lambda chemin: {"distances_de_disparition_cm": BUISSONS["disparition_cm"], "ombre_dynamique": False}
          if chemin == BUISSONS["maillage"] else None)
    with open(OUT / "balisage.csv", encoding="utf-8") as f:
        bal = [r for r in csv.DictReader(f) if r["type"] == "piquet de rubalise"]
    table("balisage", bal, lambda r: "/Game/" + r["maillage_jeu_propose"][len("acr/Content/"):],
          lambda r: 1.0, ["carrefour", "type", "cap_deg"], sur_terrain=False)
    return bilan


def glissieres_du_jeu(P, ref, ch, pkf, args):
    """Glissières métalliques du jeu (Props/Guardrails/MetalGuardrailA) posées bout à bout le long de nos tronçons de
    glissière (data/reference/glissieres.json), à la place de nos lisses unies. Lu dans le jeu le 12/11/2026 : module
    de 4 m le long de +X, lisse côté +Y (à droite du sens de pose), poteaux derrière, tous les 2 m ; un maillage de
    début, un de milieu, un de fin. La physique ne change pas : elle vient des boîtes de l'étape 1, sur la même ligne."""
    cfg = json.loads((REF / "glissieres.json").read_text(encoding="utf-8"))
    dec = cfg["geometrie"]["decalage_depuis_bord_m"]["valeur"]
    M = GLISSIERE["module_m"]
    rangs = {"debut": [], "milieu": [], "fin": []}
    for t in cfg["troncons"]:
        s0, s1 = max(t["pk_debut_m"], ch["pk"][0]), min(t["pk_fin_m"], ch["pk"][-1])
        sel = (ch["pk"] >= s0) & (ch["pk"] <= s1)
        if sel.sum() < 2 * M:
            continue
        E, A = ch["G" if t["cote"] == "gauche" else "D"][sel], ch["A"][sel]
        n = E[:, :2] - A[:, :2]
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        L = np.column_stack([E[:, :2] + n * dec, E[:, 2]])
        if t["cote"] != "gauche":
            L = L[::-1]                                   # la chaussée doit rester à droite du sens de pose
        # ligne dense (2 cm), puis points espacés d'un module en corde
        d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(L[:, :2], axis=0), axis=1))]
        sd = np.arange(0.0, d[-1], 0.02)
        Ld = np.column_stack([np.interp(sd, d, L[:, k]) for k in range(3)])
        pts, k = [Ld[0]], 0
        while True:
            reste = Ld[k:]
            loin = np.flatnonzero(np.linalg.norm(reste[:, :2] - pts[-1][:2], axis=1) >= M)
            if not len(loin):
                break
            k += int(loin[0])
            pts.append(Ld[k])
        nb = len(pts) - 1
        for i in range(nb):
            a, b = pts[i], pts[i + 1]
            piece = "milieu" if nb == 1 else "debut" if i == 0 else "fin" if i == nb - 1 else "milieu"
            dx, dy, dz = b - a
            rangs[piece].append((a[0], a[1], a[2] - GLISSIERE["enfoncement_m"], math.degrees(math.atan2(-dy, dx)),
                                 math.degrees(math.atan2(dz, math.hypot(dx, dy)))))
    cat = catalogue_du_jeu()
    bilan = {}
    for piece, rows in rangs.items():
        if not rows:
            continue
        r = np.array(rows)
        g = m08.to_gltf(r[:, :3], ref).astype(float)
        ue = Axes.ue(g)
        pk = pkf(g)
        nom = GLISSIERE[piece]
        chemin = f"{GLISSIERE['dossier']}/{nom}"
        fichier = Path("instances") / "glissieres" / f"{nom}.csv"
        out = P.sortie / fichier
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["id", "x_cm", "y_cm", "z_cm", "lacet_deg", "hauteur_voulue_m", "pk_m", "tangage_deg"])
            for i in range(len(r)):
                w.writerow([i, f"{ue[i, 0]:.1f}", f"{ue[i, 1]:.1f}", f"{ue[i, 2]:.1f}", f"{r[i, 3]:.2f}", "1.00", f"{pk[i]:.0f}",
                            f"{r[i, 4]:.2f}"])
        e = P.ajoute({"type": "InstanceGroup", "nom": f"GC_Glissieres_{nom}", "maillage_jeu": chemin,
                      "present_au_catalogue": chemin in cat, "fichier": fichier.as_posix(), "nombre": int(len(r)),
                      "composant": "HierarchicalInstancedStaticMeshComponent", "collision": "NoCollision",
                      "hauteur_native_cm": None, "echelle": "1 : maillage du jeu posé tel quel, orienté par lacet_deg et tangage_deg",
                      "retirees_sur_chaussee": 0, "essais": ["complet"]})
        bilan[e["nom"]] = e["nombre"]
    return bilan


def herbes_du_bord(P, ref, ch, pkf, sol, ruban, args):
    """Touffes d'herbe du jeu sur les bas-côtés, là où notre répartition des sols (scripts/15b_sols_du_jeu.py) dit
    qu'il y a de l'herbe, de la garrigue ou du sol nu. Recette lue dans le niveau de Bollène le 12/11/2026 : mêmes
    maillages (DryGrass04, 05, 06, WildGrass05, 03), mêmes échelles, une vingtaine de touffes par mètre de route
    chez eux ; ici une dizaine, sur HERBES["bande_m"] de part et d'autre. Les positions sont tirées au sort (graine
    fixe) : c'est un habillage, pas un relevé."""
    from scipy import ndimage as ndi
    src = MOD / "sols_jeu"
    meta = json.loads((src / "sols_jeu.json").read_text(encoding="utf-8"))
    prop = np.load(src / "proportions_l93.npz")
    e, pas = meta["emprise_l93"], meta["pas_m"]
    rng = np.random.default_rng(SEED + 7)
    A, G, D = ch["A"], ch["G"], ch["D"]
    es = ch["zone"] == "es" if "zone" in ch else np.ones(len(A), bool)
    n_par_m = HERBES["candidats_par_metre"]
    pts = []
    for bord in (G, D):
        nrm = bord[:, :2] - A[:, :2]
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
        tan = np.gradient(bord[:, :2], axis=0)
        k = rng.integers(0, len(bord), int(len(bord) * n_par_m / 2))
        d = HERBES["debut_m"] + rng.exponential(HERBES["portee_m"], len(k))
        d = d[d < HERBES["bande_m"]]
        k = k[:len(d)]
        pts.append(bord[k, :2] + nrm[k] * d[:, None] + tan[k] * rng.uniform(-0.5, 0.5, (len(k), 1)))
    xy = np.vstack(pts)
    coord = [(e[3] - xy[:, 1]) / pas - 0.5, (xy[:, 0] - e[0]) / pas - 0.5]
    c = {k: ndi.map_coordinates(prop[k], coord, order=1, mode="nearest").astype(np.float32) / 255.0 for k in meta["couches"]}
    paillis = np.clip(1.0 - sum(c.values()), 0.0, 1.0)
    w = (0.75 * c["herbe_seche"] + c["herbe_haute"] + 0.10 * c["cailloux"] + 0.25 * c["terre"] + 0.20 * c["aiguilles_de_pin"]
         + 0.30 * paillis)
    garde = rng.random(len(xy)) < w
    # hors chaussée et hors routes annexes revêtues
    interdit = [ruban]
    f_ann = OUT / "annexes_revetues.geojson"
    if f_ann.exists():
        for ft in json.loads(f_ann.read_text(encoding="utf-8"))["features"]:
            g = shapely.geometry.shape(ft["geometry"])
            interdit.append(g.buffer(0.5) if g.geom_type == "Polygon" else g.buffer(2.5))
    interdit += [g_ for g_, _ in regles_arbres.emprises_degagees(ROOT)]         # aires de terre : pas de touffes
    zone = shapely.union_all(interdit)
    shapely.prepare(zone)
    dist = shapely.distance(zone, shapely.points(xy[:, 0], xy[:, 1]))
    # maillage et échelle : tirage pondéré, puis dégagement (une touffe ne doit pas déborder sur la chaussée)
    noms = list(HERBES["maillages"])
    vert = c["herbe_haute"] > 0.3                       # sur la bande d'herbe verte : le mélange vert ; ailleurs : le sec
    choix = np.zeros(len(xy), np.int64)
    for cle, sel in (("vert", vert), ("sec", ~vert)):
        poids = np.array([HERBES["maillages"][n][cle] for n in noms], float)
        choix[sel] = rng.choice(len(noms), int(sel.sum()), p=poids / poids.sum())
    ech = np.zeros(len(xy))
    rayon = np.zeros(len(xy))
    for i, n in enumerate(noms):
        m = HERBES["maillages"][n]
        sel = choix == i
        ech[sel] = rng.uniform(m["echelle"][0], m["echelle"][1], sel.sum())
        rayon[sel] = 0.4 * m["largeur_m"] * ech[sel]
    petit = noms.index(HERBES["petit"])
    trop_pres = garde & (dist < 0.3 + rayon)
    choix[trop_pres] = petit                         # près du bord : la plus petite touffe, à petite échelle
    mp = HERBES["maillages"][HERBES["petit"]]
    ech[trop_pres] = rng.uniform(mp["echelle"][0], (mp["echelle"][0] + mp["echelle"][1]) / 2, trop_pres.sum())
    rayon[trop_pres] = 0.4 * mp["largeur_m"] * ech[trop_pres]
    garde &= dist >= 0.3 + rayon
    xy, choix, ech = xy[garde], choix[garde], ech[garde]
    g = m08.to_gltf(np.column_stack([xy, np.zeros(len(xy))]), ref).astype(float)
    zs = sol(g[:, 0], g[:, 2])
    ok = np.isfinite(zs)
    g, choix, ech = g[ok], choix[ok], ech[ok]
    g[:, 1] = zs[ok] - 0.03
    ue = Axes.ue(g)
    pk = pkf(g)
    lacet = rng.uniform(-180.0, 180.0, len(g))
    cat = catalogue_du_jeu()
    bilan = {}
    for i, n in enumerate(noms):
        sel = np.flatnonzero(choix == i)
        if not len(sel):
            continue
        chemin = n if n.startswith("/Game/") else f"{HERBES['dossier']}/{n}"
        nom = n.rsplit("/", 1)[1]
        fichier = Path("instances") / "herbes" / f"{nom}.csv"
        out = P.sortie / fichier
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", newline="", encoding="utf-8") as fh:
            wr = csv.writer(fh, lineterminator="\n")
            wr.writerow(["id", "x_cm", "y_cm", "z_cm", "lacet_deg", "hauteur_voulue_m", "pk_m", "echelle"])
            for j in sel:
                wr.writerow([j, f"{ue[j, 0]:.1f}", f"{ue[j, 1]:.1f}", f"{ue[j, 2]:.1f}", f"{lacet[j]:.1f}", "1.00", f"{pk[j]:.0f}",
                             f"{ech[j]:.3f}"])
        el = P.ajoute({"type": "InstanceGroup", "nom": f"GC_Herbes_{nom}", "maillage_jeu": chemin,
                       "present_au_catalogue": chemin in cat, "fichier": fichier.as_posix(), "nombre": int(len(sel)),
                       "composant": "HierarchicalInstancedStaticMeshComponent", "collision": "NoCollision",
                       "hauteur_native_cm": None, "echelle": "colonne « echelle » de la table, maillage posé tel quel",
                       "distances_de_disparition_cm": HERBES["disparition_cm"], "ombre_dynamique": False,
                       "retirees_sur_chaussee": 0, "essais": ["complet"]})
        bilan[el["nom"]] = el["nombre"]
    return bilan


def mobilier_du_bord(P, ref, pkf, sol, args):
    """Poteaux électriques, panneaux du rallye, barrières et haie posés avec des maillages du jeu, et câbles entre
    les poteaux (data/reference/mobilier_bord_de_route.json, scripts/mobilier.py). Les mêmes objets reçoivent leur
    collision dans scripts/09_export_stage_ir.py."""
    import mobilier
    objets, lignes = mobilier.objets()
    if not objets:
        return {}
    cat = catalogue_du_jeu()
    bilan, par_maillage = {}, {}
    for o in objets:
        g = m08.to_gltf(np.array([[o["x"], o["y"], o["z_sol"]]]), ref).astype(float)[0]
        zs = sol(np.array([g[0]]), np.array([g[2]]))[0]
        if np.isfinite(zs):
            g[1] = zs                                    # posé sur le terrain importé, pas sur le MNT brut
        o["_g"] = g
        cap = math.degrees(math.atan2(-o["dir"][1], o["dir"][0]))           # lacet Unreal du sens de la course
        par_maillage.setdefault(o["maillage_jeu"], []).append((g, cap + o["lacet_relatif_deg"], o))
    for chemin, lot in sorted(par_maillage.items()):
        nom = chemin.rsplit("/", 1)[1]
        ue = Axes.ue(np.array([x[0] for x in lot]))
        pk = pkf(np.array([x[0] for x in lot]))
        fichier = Path("instances") / "mobilier" / f"{nom}.csv"
        out = P.sortie / fichier
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["id", "x_cm", "y_cm", "z_cm", "lacet_deg", "hauteur_voulue_m", "pk_m", "echelle", "type"])
            for i, (g, lacet, o) in enumerate(lot):
                w.writerow([i, f"{ue[i, 0]:.1f}", f"{ue[i, 1]:.1f}", f"{ue[i, 2] - 100.0 * o.get('enfoncement_m', 0.03):.1f}",
                            f"{(lacet + 180) % 360 - 180:.2f}", "1.00", f"{pk[i]:.0f}", f"{o.get('echelle', 1.0):.3f}", o["type"]])
        e = P.ajoute({"type": "InstanceGroup", "nom": f"GC_Mobilier_{nom}", "maillage_jeu": chemin, "present_au_catalogue": chemin in cat,
                      "fichier": fichier.as_posix(), "nombre": len(lot), "composant": "HierarchicalInstancedStaticMeshComponent",
                      "collision": "NoCollision", "hauteur_native_cm": None,
                      "echelle": "colonne « echelle » de la table, maillage posé tel quel", "retirees_sur_chaussee": 0, "essais": ["complet"]})
        bilan[e["nom"]] = e["nombre"]
    # câbles : trois par portée, en chaînette approchée, accrochés aux bouts et au milieu de la traverse
    pos, nrm, tri = [], [], []
    k0 = 0
    for l in lignes:
        if not l["cables"]:
            continue
        pts = l["poteaux"]
        for a, b in zip(pts[:-1], pts[1:]):
            if math.hypot(b["x"] - a["x"], b["y"] - a["y"]) > CABLES["portee_max_m"] or not a.get("cable") or not b.get("cable"):
                continue
            for k_fil in range(3):
                bouts = []
                for o in (a, b):
                    d = np.array(o["dir"])
                    travers = np.array([-d[1], d[0]])                       # en travers de la ligne (est, nord)
                    lat = o["cable"]["ecarts_m"][k_fil]
                    bouts.append(m08.to_gltf(np.array([[o["x"] + travers[0] * lat, o["y"] + travers[1] * lat, 0.0]]), ref).astype(float)[0]
                                 * np.array([1.0, 0.0, 1.0]) + np.array([0.0, o["_g"][1] + o["cable"]["hauteur_m"], 0.0]))
                A, B = bouts
                portee = float(np.linalg.norm(B - A))
                fleche = CABLES["fleche_par_m2"] * portee ** 2
                n = CABLES["segments"]
                t = np.linspace(0.0, 1.0, n + 1)
                axe = A[None, :] + (B - A)[None, :] * t[:, None]
                axe[:, 1] -= 4.0 * fleche * t * (1.0 - t)
                u = (B - A) / max(portee, 1e-9)
                w1 = np.cross(u, [0.0, 1.0, 0.0]); w1 /= max(np.linalg.norm(w1), 1e-9)
                w2 = np.cross(u, w1)
                for i in range(n + 1):
                    for s in range(3):
                        ang = 2.0 * math.pi * s / 3.0
                        r = math.cos(ang) * w1 + math.sin(ang) * w2
                        pos.append(axe[i] + CABLES["rayon_m"] * r); nrm.append(r)
                for i in range(n):
                    for s in range(3):
                        p0, p1, q0, q1 = k0 + 3 * i + s, k0 + 3 * i + (s + 1) % 3, k0 + 3 * (i + 1) + s, k0 + 3 * (i + 1) + (s + 1) % 3
                        tri += [[p0, q0, p1], [p1, q0, q1]]
                k0 += 3 * (n + 1)
    if pos:
        pos, nrm, tri = np.array(pos), np.array(nrm), np.array(tri, np.int64)
        # triangles orientés vers l'extérieur du câble
        fn = np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])
        dehors = (fn * nrm[tri].sum(1)).sum(1) < 0
        tri[dehors] = tri[dehors][:, [0, 2, 1]]
        if "T_GC_Cable" not in P.vus:
            P.texture("T_GC_Cable", "commun", f"{UE}/Shared/Textures", image_unie(CABLES["couleur"]), ["complet"])
        if "T_GC_ORM_R140M000" not in P.vus:
            P.texture("T_GC_ORM_R140M000", "commun", f"{UE}/Shared/Textures", image_unie((255, 140, 0)), ["complet"])
        P.materiau("MI_GC_Cable", f"{UE}/Shared/Materials", {"couleur": "T_GC_Cable", "orm": "T_GC_ORM_R140M000"}, ["complet"])
        P.maillage(f"SM_{NOM}Cables", "mobilier", f"{UE}/Props/Meshes", pos, nrm, np.zeros((len(pos), 2)), tri, "MI_GC_Cable", ["complet"],
                   extra={"portees": int(k0 // (3 * 3 * (CABLES["segments"] + 1)))})
    objets_en_long(P, ref, sol, mobilier.en_long())
    return bilan


def _boite(a, b, largeur, hauteur):
    """Pavé d'axe a -> b (glTF, m), de section largeur x hauteur : 24 sommets à normales franches, 12 triangles."""
    u = b - a
    L = max(float(np.linalg.norm(u)), 1e-9)
    u = u / L
    haut = np.array([0.0, 1.0, 0.0])
    if abs(float(u @ haut)) > 0.95:                       # pavé vertical (poteau) : sa « hauteur » est horizontale
        haut = np.array([1.0, 0.0, 0.0])
    w = np.cross(u, haut); w /= max(np.linalg.norm(w), 1e-9)
    v = np.cross(w, u)
    c = [a + sx * w * largeur / 2 + sy * v * hauteur / 2 + t * u * L for t in (0, 1) for sy in (-1, 1) for sx in (-1, 1)]
    faces = [((0, 1, 3, 2), -u), ((4, 6, 7, 5), u), ((0, 4, 5, 1), -v), ((2, 3, 7, 6), v), ((0, 2, 6, 4), -w), ((1, 5, 7, 3), w)]
    pos, nrm, tri = [], [], []
    for q, n in faces:
        k = len(pos)
        pts = [c[i] for i in q]
        if float(np.cross(pts[1] - pts[0], pts[2] - pts[0]) @ n) < 0:
            pts = pts[::-1]
        pos += pts; nrm += [n] * 4; tri += [[k, k + 1, k + 2], [k, k + 2, k + 3]]
    return pos, nrm, tri


def objets_en_long(P, ref, sol, liste):
    """Rubalises, lisses en bois et barrières de piste : maillages à nous, d'après les tracés de scripts/mobilier.py.

    Rubalise : ruban vertical de RUBALISE["largeur_m"], vu des deux côtés, à rayures rouges et blanches (texture
    répétée), qui pend un peu entre deux appuis. Lisse : poteaux carrés et une ou deux lisses horizontales."""
    def au_sol(p):
        g = m08.to_gltf(np.array([[p["x"], p["y"], p["z_sol"]]]), ref).astype(float)[0]
        zs = sol(np.array([g[0]]), np.array([g[2]]))[0]
        if np.isfinite(zs):
            g[1] = zs
        return g

    lots = {}
    for e in liste:
        pts = [au_sol(p) for p in e["points"]]
        genre = e["genre"]
        pos, nrm, uv, tri = lots.setdefault(genre, ([], [], [], []))
        if genre == "rubalise":
            h, larg = float(e.get("hauteur_m", RUBALISE["hauteur_m"])), RUBALISE["largeur_m"]
            cumul = 0.0
            for A, B in zip(pts[:-1], pts[1:]):
                A, B = A + np.array([0.0, h, 0.0]), B + np.array([0.0, h, 0.0])
                L = float(np.linalg.norm(B - A))
                n = max(2, int(math.ceil(L / 1.5)))
                t = np.linspace(0.0, 1.0, n + 1)
                axe = A[None, :] + (B - A)[None, :] * t[:, None]
                axe[:, 1] -= 4.0 * RUBALISE["fleche_par_m"] * L * t * (1.0 - t)
                d = (B - A) * np.array([1.0, 0.0, 1.0])
                nz = np.cross(d / max(np.linalg.norm(d), 1e-9), [0.0, 1.0, 0.0])
                for face in (1.0, -1.0):                                      # deux faces : le ruban se voit des deux côtés
                    k = len(pos)
                    for i in range(n + 1):
                        for dv, v in ((larg / 2, 0.0), (-larg / 2, 1.0)):
                            pos.append(axe[i] + np.array([0.0, dv, 0.0])); nrm.append(face * nz)
                            uv.append([(cumul + L * t[i]) / RUBALISE["periode_m"], v])
                    for i in range(n):
                        q = [k + 2 * i, k + 2 * i + 1, k + 2 * i + 3, k + 2 * i + 2]
                        if face < 0:
                            q = q[::-1]
                        tri += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
                cumul += L
        else:
            h = float(e.get("hauteur_m", 1.0))
            sec = float(e.get("section_poteau_m", 0.10))
            niveaux = [] if e.get("sans_lisse") else e.get("lisses_a_m") or ([h - 0.08, 0.5 * h] if h >= 0.8 else [h - 0.06])
            for g in pts:
                p, n_, t_ = _boite(g - np.array([0.0, 0.25, 0.0]), g + np.array([0.0, h, 0.0]), sec, sec)
                k = len(pos); pos += p; nrm += n_; tri += [[k + a for a in x] for x in t_]; uv += [[0.5, 0.5]] * len(p)
            for A, B in zip(pts[:-1], pts[1:]):
                for z in niveaux:
                    p, n_, t_ = _boite(A + np.array([0.0, z, 0.0]), B + np.array([0.0, z, 0.0]), 0.04, float(e.get("hauteur_lisse_m", 0.10)))
                    k = len(pos); pos += p; nrm += n_; tri += [[k + a for a in x] for x in t_]; uv += [[0.5, 0.5]] * len(p)
    faits = {}
    for genre, (pos, nrm, uv, tri) in sorted(lots.items()):
        if not pos:
            continue
        pos, nrm, uv, tri = np.array(pos), np.array(nrm), np.array(uv), np.array(tri, np.int64)
        fn = np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])
        envers = (fn * nrm[tri].sum(1)).sum(1) < 0
        tri[envers] = tri[envers][:, [0, 2, 1]]
        nom = {"rubalise": "RallyTape", "lisse_bois": "WoodRails", "barriere_de_piste": "TrackBarriers"}[genre]
        if genre == "rubalise":
            n = 64                                                            # rayures en biais, une période sur la largeur
            y, x = np.mgrid[0:16, 0:n]
            rouge = ((x + y) // (n // 2)) % 2 == 0
            img = np.where(rouge[:, :, None], np.array(RUBALISE["rouge"], np.uint8), np.array(RUBALISE["blanc"], np.uint8)).astype(np.uint8)
            P.texture("T_GC_RallyTape", "commun", f"{UE}/Shared/Textures", Image.fromarray(img, "RGB"), ["complet"])
        else:
            P.texture(f"T_GC_{nom}", "commun", f"{UE}/Shared/Textures", image_unie(LISSES["couleurs"][genre]), ["complet"])
        if "T_GC_ORM_R200M000" not in P.vus:
            P.texture("T_GC_ORM_R200M000", "commun", f"{UE}/Shared/Textures", image_unie((255, 200, 0)), ["complet"])
        P.materiau(f"MI_GC_{nom}", f"{UE}/Shared/Materials", {"couleur": f"T_GC_{nom}", "orm": "T_GC_ORM_R200M000"}, ["complet"])
        P.maillage(f"SM_{NOM}{nom}", "mobilier", f"{UE}/Props/Meshes", pos, nrm, uv, tri, f"MI_GC_{nom}", ["complet"],
                   extra={"troncons": sum(1 for e in liste if e["genre"] == genre),
                          "longueur_m": round(float(sum(np.linalg.norm(np.diff(np.array([[p["x"], p["y"]] for p in e["points"]]), axis=0), axis=1).sum()
                                                        for e in liste if e["genre"] == genre)), 1)})
        faits[genre] = len(tri)
    if faits:
        print("  objets en long :", {k: f"{v} triangles" for k, v in faits.items()})
    return faits


# --- parois rocheuses ------------------------------------------------------------------------------------
# Parois et talus rocheux du bord de route (data/reference/parois_rocheuses.json), habillés de la roche répétable de
# Bollène (MI_GC_Roche, matieres_du_jeu.json). La roche ÉPOUSE LE RELIEF du relevé laser : c'est le terrain, avancé
# de quelques décimètres vers la route et débité en bancs et en blocs. Le relevé vidéo dit où il y a de la roche, de
# quel genre et jusqu'à quelle hauteur ; le relief dit où le talus monte, et à quelle pente.
# Par genre : avancée devant le terrain, épaisseur des bancs (min, max), part de la largeur d'un banc occupée par son
# front (0,3 : front raide et replat ; 1 : pente continue), décrochement des blocs, longueur des blocs (min, max),
# lacunes (plus la valeur est basse, plus la terre reparaît par plaques entre les roches).
ROCHE = {"pas_m": 0.4, "biseau_m": 7.0, "allonge_m": 6.0, "portee_m": 10.0, "pas_profil_m": 0.1, "enfoui_m": 0.45,
         "epaisseur_m": 0.16, "pente_deg": (9.0, 24.0), "plat_m": (2.0, 0.35), "uv_m": 2.5, "marge_chaussee_m": 0.3,
         "couleur_secours": (188, 182, 168),
         "genres": {"lite": {"avance_m": 0.8, "banc_m": (0.28, 0.6), "front": 0.3, "decroche_m": 0.3, "bloc_m": (0.9, 2.5), "lacunes": 0.16},
                    "blocs": {"avance_m": 1.0, "banc_m": (0.6, 1.1), "front": 0.25, "decroche_m": 0.45, "bloc_m": (1.2, 2.4), "lacunes": 0.2},
                    "eboulis": {"avance_m": 0.45, "banc_m": (0.3, 0.45), "front": 1.0, "decroche_m": 0.22, "bloc_m": (0.6, 1.3), "lacunes": 0.08}}}


def _alea(i, j, k):
    h = np.sin(i * 127.1 + j * 311.7 + k * 74.7) * 43758.5453
    return h - np.floor(h)


def _bruit(u, v, k):
    """Bruit de valeur lissé, entre 0 et 1, reproductible."""
    i, j = np.floor(u), np.floor(v)
    fu, fv = u - i, v - j
    su, sv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
    return ((_alea(i, j, k) * (1 - su) + _alea(i + 1, j, k) * su) * (1 - sv)
            + (_alea(i, j + 1, k) * (1 - su) + _alea(i + 1, j + 1, k) * su) * sv)


def _fbm(u, v, k, octaves=4):
    """Somme de bruits de plus en plus fins, centrée sur 0, entre -1 et 1 environ."""
    out, amp, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        out = out + amp * (_bruit(u * 2 ** o, v * 2 ** o, k + 17 * o) - 0.5) * 2.0
        tot += amp
        amp *= 0.5
    return out / tot


def parois_rocheuses(P, ref, sol):
    """Une nappe de roche par paroi relevée, posée sur le terrain.

    Histoire de la forme (aperçus hors jeu du 13/11/2026, scripts/21_apercu_conducteur.py) : un front dressé à la pente
    et à la hauteur relevées se tenait comme une dalle isolée devant un terrain plus bas, ou sur un sol plat quand le
    relevé était décalé ; la vidéo de reconnaissance montre en fait des talus de roche brisée à la pente du terrain
    (PK 2800, PK 3080), rarement des fronts verticaux. D'où la règle : la roche suit le terrain.
      - profil lisse = terrain avancé de `avance_m` vers la route, plus une épaisseur ;
      - ce profil est débité en bancs horizontaux (front raide, replat), chaque banc en blocs qui avancent ou reculent ;
      - la roche s'efface là où le terrain est plat, s'arrête à la hauteur relevée ou là où le talus cesse de monter.
    """
    f = ROOT / "data" / "reference" / "parois_rocheuses.json"
    if not f.exists():
        return 0
    import mobilier
    cfg = json.loads(f.read_text(encoding="utf-8"))
    route = mobilier.Route()
    haut = np.array([0.0, 1.0, 0.0])
    if "T_GC_Roche" not in P.vus:
        P.texture("T_GC_Roche", "commun", f"{UE}/Shared/Textures", image_unie(ROCHE["couleur_secours"]), ["complet"])
    if "T_GC_ORM_R230M000" not in P.vus:
        P.texture("T_GC_ORM_R230M000", "commun", f"{UE}/Shared/Textures", image_unie((255, 230, 0)), ["complet"])
    P.materiau("MI_GC_Roche", f"{UE}/Shared/Materials", {"couleur": "T_GC_Roche", "orm": "T_GC_ORM_R230M000"}, ["complet"],
               note="parois rocheuses : parent du jeu MI_BolleneRockfacesParent (factices.json), réglages dans matieres_du_jeu.json")
    do = ROCHE["pas_profil_m"]
    n_o = int(round(ROCHE["portee_m"] / do)) + 1
    t0, t1 = (math.tan(math.radians(a)) for a in ROCHE["pente_deg"])
    n_faits, longueur, n_tri = 0, 0.0, 0
    for k, e in enumerate(cfg["parois"]):
        g = ROCHE["genres"][e["genre"]]
        rec = float(e.get("recalage_pk_m", 0.0))
        pk0, pk1, cote = float(e["pk_debut_m"]) + rec, float(e["pk_fin_m"]) + rec + float(e.get("allonge_m", 0.0)), e["cote"]
        S = np.arange(pk0 - ROCHE["allonge_m"], pk1 + ROCHE["allonge_m"] + 1e-6, ROCHE["pas_m"])
        ns = len(S)
        if ns < 3:
            continue
        h0, h1 = e["hauteur_m"]
        # bord de chaussée, direction vers l'extérieur (horizontale), dans le repère glTF du projet
        B = np.array([m08.to_gltf(np.array([[*route.point(s, cote, 0.0)[:3]]]), ref).astype(float)[0] for s in S])
        B1 = np.array([m08.to_gltf(np.array([[*route.point(s, cote, 1.0)[:3]]]), ref).astype(float)[0] for s in S])
        dehors = (B1 - B) * np.array([1.0, 0.0, 1.0])
        dehors /= np.maximum(np.linalg.norm(dehors, axis=1, keepdims=True), 1e-9)
        fin = np.clip(np.minimum(S - S[0], S[-1] - S) / ROCHE["biseau_m"], 0.0, 1.0)
        fin = fin * fin * (3 - 2 * fin)                                             # la paroi meurt en sifflet à ses bouts
        H = (h0 + (h1 - h0) * _bruit(S / 9.0, 0.0, k)) * (0.85 + 0.35 * _bruit(S / 2.1, 7.0, k + 2)) * (0.1 + 0.9 * fin)
        avance = g["avance_m"] * (0.65 + 0.7 * _bruit(S / 7.0, 3.0, k + 4)) * (0.15 + 0.85 * fin)
        # profil du terrain en travers, tous les 10 cm, hauteurs comptées depuis le bord de chaussée
        o0 = max(float(e["decalage_m"]) - 0.8, ROCHE["marge_chaussee_m"])
        OO = o0 + np.arange(n_o + int(round(3.4 / do))) * do
        pts = B[:, None, :] + dehors[:, None, :] * OO[None, :, None]
        T = sol(pts[:, :, 0].ravel(), pts[:, :, 2].ravel()).reshape(ns, len(OO)) - B[:, 1][:, None]
        for i in np.flatnonzero(~np.isfinite(T).all(1)):                            # trous du terrain : prolongés, ou supposés bas
            ok = np.isfinite(T[i])
            T[i] = np.interp(OO, OO[ok], T[i][ok]) if ok.sum() >= 2 else -1.0
        cols = np.arange(n_o)[None, :]

        def terrain(dec):
            """Terrain à (décalage de la grille + dec), dec étant donné par station."""
            x = cols + (np.asarray(dec, float) / do)[:, None]
            i = np.clip(np.floor(x).astype(int), 0, T.shape[1] - 2)
            r = np.clip(x - i, 0.0, 1.0)
            return np.take_along_axis(T, i, 1) * (1 - r) + np.take_along_axis(T, i + 1, 1) * r

        un = np.ones(ns)
        zS = terrain(avance) + ROCHE["epaisseur_m"] * (0.2 + 0.8 * fin)[:, None]    # profil lisse de la roche
        zM = np.maximum.accumulate(zS, axis=1)
        pente = terrain(avance + 0.5) - terrain(np.maximum(avance - 0.5, 0.0))      # montée du terrain sur 1 m, sous la roche
        W = np.clip((pente - t0) / (t1 - t0), 0.0, 1.0)
        W = W * W * (3 - 2 * W)                                                     # 0 sur le plat, 1 sur un vrai talus
        # la roche finit là où, le talus une fois commencé, le terrain ne monte plus (ROCHE["plat_m"])
        commence = np.maximum.accumulate(W > 0.5, axis=1)
        fini = commence & ((terrain(avance + ROCHE["plat_m"][0]) - terrain(avance)) < ROCHE["plat_m"][1])
        i_fin = np.where(fini.any(1), fini.argmax(1), n_o - 1)
        i_fin = np.where(commence.any(1), i_fin, 0)
        r_ns = np.arange(ns)
        z_top = np.minimum(H, zM[r_ns, i_fin])

        def ou(niveau):
            """Rang (fractionnaire) du premier point du profil qui atteint `niveau` (par station)."""
            atteint = zM >= niveau[:, None]
            j = np.where(atteint.any(1), atteint.argmax(1), n_o - 1)
            jm = np.maximum(j - 1, 0)
            za, zb_ = zM[r_ns, jm], zM[r_ns, j]
            r = np.where(zb_ - za > 1e-6, np.clip((niveau - za) / np.maximum(zb_ - za, 1e-6), 0.0, 1.0), 1.0)
            return np.where(j == 0, 0.0, jm + r)

        def en(x, champ):
            """Valeur de `champ` (stations x rangs) au rang fractionnaire x."""
            i = np.clip(np.floor(x).astype(int), 0, n_o - 2)
            r = np.clip(x - i, 0.0, 1.0)
            return champ[r_ns, i] * (1 - r) + champ[r_ns, i + 1] * r

        # bancs : épaisseurs inégales, léger pendage le long de la route, joints qui ondulent
        bords = [-ROCHE["enfoui_m"]]
        while bords[-1] < float(H.max()) + 0.2:
            n = len(bords)
            bords.append(bords[-1] + g["banc_m"][0] + (g["banc_m"][1] - g["banc_m"][0]) * float(_alea(n, 0.0, k + 13)))
        pendage = (float(_alea(k, 5.0, 3.0)) - 0.5) * 0.04
        penche = pendage * (S - S.mean())
        T0 = T[:, :n_o]
        x_top = ou(z_top)
        rangs, rentres = [], []

        def rang(niveau, z_sortie, dx):
            rentre = niveau > z_top
            x = np.where(rentre, x_top + 0.3 / do, ou(np.minimum(niveau, z_top)))
            x = np.minimum(x, i_fin + 0.3 / do)
            # présence : nulle sur le plat, et par plaques ailleurs (la roche affleure entre la terre et les touffes)
            plaque = np.clip((_fbm(S / 4.5, niveau / 1.6 + 2.3 * k, k + 31, 3) + g["lacunes"]) / 0.2, 0.0, 1.0)
            w = en(x, W) * plaque * plaque * (3 - 2 * plaque)
            o = np.where(rentre, o0 + x * do, np.maximum(o0 + x * do - dx, ROCHE["marge_chaussee_m"]))
            sous_terre = en((o - o0) / do, T0) - 0.35
            z = np.where(rentre, sous_terre - 0.1, sous_terre + (z_sortie - sous_terre) * w)
            rangs.append(B + dehors * o[:, None] + haut[None, :] * z[:, None])
            rentres.append(rentre | (w < 0.02))

        rang(bords[0] + penche, np.minimum(bords[0] + penche, T0[:, 0] - 0.4), 0.0)
        ampl = np.clip(avance / 0.8, 0.15, 1.0)
        for n in range(len(bords) - 1):
            ep = bords[n + 1] - bords[n]
            joint = lambda m: 0.10 * (_bruit(S / 8.0, 0.37 * m, k + 12) - 0.5) * 2.0 + 0.07 * (_bruit(S / 1.9, 0.61 * m, k + 29) - 0.5) * 2.0  # noqa: E731
            bas, hautb = bords[n] + penche + joint(n), bords[n + 1] + penche + joint(n + 1)
            long_bloc = g["bloc_m"][0] + (g["bloc_m"][1] - g["bloc_m"][0]) * float(_alea(n, 0.0, k + 14))
            u = S / long_bloc + 3.7 * float(_alea(n, 1.0, k + 15)) + 0.45 * (_bruit(S / 3.3, 1.7 * n, k + 28) - 0.5) * 2.0   # blocs de longueur inégale
            bloc = np.floor(u)
            dx = g["decroche_m"] * (_alea(bloc, float(n), k + 5) - 0.5) * 2.0                 # chaque bloc avance ou recule d'un coup
            dx += g["decroche_m"] * 0.8 * (_alea(bloc, float(n), k + 27) - 0.5) * 2.0 * (u % 1.0 - 0.5)   # et se présente de biais
            oblique = (S + 1.6 * bords[n] + 0.8 * n) / 6.1 + float(_alea(k, 9.0, 4.0))
            dx -= 0.22 * np.clip((np.abs(oblique % 1.0 - 0.5) * 2.0 - 0.9) / 0.1, 0.0, 1.0)   # grandes cassures obliques
            de_niveau = 0.07 * (_alea(bloc, n + 0.5, k + 19) - 0.5) * 2.0                     # dessus des blocs à des hauteurs inégales
            dx += 0.10 * (float(_alea(n, 2.0, k + 16)) - 0.5) * 2.0                          # un banc entier en saillie ou en retrait
            dx += 0.25 * _fbm(S / 2.6, 0.6 * n + 3.1 * k, k)                                 # grandes bosses
            dx -= 0.14 * np.clip((np.abs(u % 1.0 - 0.5) * 2.0 - 0.86) / 0.14, 0.0, 1.0)      # joints verticaux en creux
            dx *= ampl
            fb, ft = 0.5 - g["front"] / 2, 0.5 + g["front"] / 2
            rang(bas + fb * ep, bas - de_niveau, dx)
            rang(bas + ft * ep, hautb + de_niveau, dx - 0.05 * ampl)
        G = np.stack(rangs, 1)                                    # (stations, rangs, 3)
        nr = G.shape[1]
        pos = G.reshape(-1, 3)
        i, j = np.meshgrid(np.arange(ns - 1), np.arange(nr - 1), indexing="ij")
        a0 = (i * nr + j).ravel(); a1 = a0 + 1; b0 = a0 + nr; b1 = b0 + 1
        tri = np.concatenate([np.column_stack([a0, b0, a1]), np.column_stack([a1, b0, b1])])
        fn = np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])
        enfoui = np.stack(rentres, 1).ravel()
        tri = tri[(np.linalg.norm(fn, axis=1) > 2e-5) & ~enfoui[tri].all(1)]       # ni triangles écrasés, ni triangles sous terre
        if not len(tri):
            continue
        attendu = np.repeat(-dehors + haut[None, :], nr, axis=0)
        fn = np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])
        envers = np.einsum("ij,ij->i", fn, attendu[tri[:, 0]]) < 0
        tri[envers] = tri[envers][:, [0, 2, 1]]
        fn[envers] *= -1.0
        nrm = np.zeros_like(pos)
        for c in range(3):
            np.add.at(nrm, tri[:, c], fn)
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
        long_s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(B, axis=0), axis=1))]
        dev = np.concatenate([np.zeros((ns, 1)), np.cumsum(np.linalg.norm(np.diff(G, axis=1), axis=2), axis=1)], axis=1)   # développé en travers
        uv = np.column_stack([np.repeat(long_s, nr) / ROCHE["uv_m"], -dev.ravel() / ROCHE["uv_m"]])
        usure = np.clip(0.28 + 0.45 * _fbm(np.repeat(S, nr) / 3.0, dev.ravel() / 1.5, k + 23, 3), 0.0, 0.62)
        coul = np.column_stack([(255 * usure).astype(np.uint8), np.zeros(len(pos), np.uint8), np.full(len(pos), 255, np.uint8),
                                np.full(len(pos), 255, np.uint8)])
        # facettes franches : chaque triangle porte sa propre normale, à peine adoucie vers celle de ses voisins ; une
        # roche fracturée a des arêtes vives, des normales moyennées la faisaient fondre
        fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-9)
        nrm = 0.72 * np.repeat(fn, 3, axis=0) + 0.28 * nrm[tri].reshape(-1, 3)
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
        pos, uv, coul = pos[tri].reshape(-1, 3), uv[tri].reshape(-1, 2), coul[tri].reshape(-1, 4)
        tri = np.arange(len(pos)).reshape(-1, 3)
        P.maillage(f"SM_{NOM}Rock_{int(pk0):04d}{'L' if cote == 'gauche' else 'R'}", "parois", f"{UE}/Bridges/Meshes", pos, nrm, uv, tri, "MI_GC_Roche",
                   ["complet"], pk=(float(S[0]), float(S[-1])), couleurs=coul,
                   extra={"genre": e["genre"], "hauteur_m": [h0, h1], "decalage_m": float(e["decalage_m"]), "cote": cote,
                          "recalage_pk_m": rec})
        n_faits += 1
        longueur += pk1 - pk0
        n_tri += len(tri)
    print(f"  parois rocheuses : {n_faits} parois, {longueur:.0f} m, {n_tri} triangles")
    return n_faits


def catalogue_du_jeu():
    cat = set()
    with gzip.open(sorted(REF.glob("catalogue_jeu_*.txt.gz"))[-1], "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.endswith(".uasset"):
                cat.add("/Game/" + line[len("acr/Content/"):-len(".uasset")])
    return cat


# --- contrôles relus sur disque --------------------------------------------------------------------------
def lire_glb_paquet(path):
    b = Path(path).read_bytes()
    n = int(np.frombuffer(b, "<u4", 1, 12)[0])
    gl = json.loads(b[20:20 + n])
    binoff = 20 + n + 8

    def arr(i):
        a = gl["accessors"][i]
        v = gl["bufferViews"][a["bufferView"]]
        dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}[a["componentType"]]
        k = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[a["type"]]
        return np.frombuffer(b, dt, a["count"] * k, binoff + v["byteOffset"]).reshape(-1, k)

    p = gl["meshes"][0]["primitives"][0]
    return (gl, arr(p["attributes"]["POSITION"]), arr(p["attributes"]["NORMAL"]),
            arr(p["attributes"]["TEXCOORD_0"]) if "TEXCOORD_0" in p["attributes"] else None, arr(p["indices"]).reshape(-1, 3))


def controle(P, sources_sommets):
    r = {"maillages": 0, "erreurs": []}
    mondes = {}
    tailles = []
    for e in P.elements:
        f = P.sortie / e["fichier"] if "fichier" in e else None
        if f is not None and not f.exists():
            r["erreurs"].append(f"fichier absent : {e['fichier']}")
            continue
        if e["type"] == "StaticMesh":
            gl, pos, nrm, uv, tri = lire_glb_paquet(f)
            r["maillages"] += 1
            tailles.append(f.stat().st_size)
            if gl["meshes"][0]["name"] != e["nom"] or gl["materials"][0]["name"] != e["section_materiau"]:
                r["erreurs"].append(f"{e['nom']} : nom de maillage ou de section inattendu")
            if np.isnan(pos).any() or np.isnan(nrm).any() or (uv is not None and np.isnan(uv).any()):
                r["erreurs"].append(f"{e['nom']} : NaN")
            if tri.max() >= len(pos):
                r["erreurs"].append(f"{e['nom']} : indice hors tampon")
            if e.get("acteur") is None:
                continue
            loc = P.axes.depuis_fichier(pos)
            lo, hi = loc.min(0), loc.max(0)
            b = e["bornes_locales_cm"]
            if np.abs(lo - b["min"]).max() > 0.2 or np.abs(hi - b["max"]).max() > 0.2:
                r["erreurs"].append(f"{e['nom']} : bornes relues {lo.round(1)}..{hi.round(1)} != manifeste")
            if e["destination"].endswith("/Terrain/Meshes") or "TerrainFin" in e["nom"]:
                if uv.min() < -1e-4 or uv.max() > 1 + 1e-4:
                    r["erreurs"].append(f"{e['nom']} : UV hors de 0..1")
            if e["nom"].startswith(f"SM_{NOM}Terrain"):
                mondes[e["nom"]] = loc + np.array(e["acteur"]["position_cm"])
        elif e["type"] == "Texture2D":
            with Image.open(f) as im:
                if list(im.size) != e["dimensions"]:
                    r["erreurs"].append(f"{e['nom']} : dimensions {im.size} != {e['dimensions']}")
                w, h = im.size
                if (w & (w - 1)) or (h & (h - 1)):
                    r["erreurs"].append(f"{e['nom']} : pas une puissance de 2")
                if e["import"]["compression"] == "TC_Normalmap":
                    a = np.asarray(im.convert("RGB")).astype(float) / 127.5 - 1
                    a[..., 1] *= -1                      # retour en Y+ pour vérifier la norme et z > 0
                    if abs(np.linalg.norm(a, axis=2).mean() - 1) > 0.03 or a[..., 2].min() < 0:
                        r["erreurs"].append(f"{e['nom']} : relief anormal")
        elif e["type"] == "MaterialInstance":
            for t in e["parametres_texture"].values():
                if t not in P.vus:
                    r["erreurs"].append(f"{e['nom']} : texture {t} absente du manifeste")
    for e in P.elements:
        if e["type"] == "StaticMesh" and e.get("materiau") and e["materiau"] not in P.vus:
            r["erreurs"].append(f"{e['nom']} : variante {e['materiau']} absente")
    # raccord des dalles voisines : sommets partagés dans la source -> même point du monde après découpe
    if mondes:
        pts = np.vstack(list(mondes.values()))
        src = np.vstack([Axes.ue(v) for k, v in sources_sommets.items() if k in mondes])
        t = cKDTree(src)
        d, _ = t.query(pts)
        r["terrain_ecart_au_modele_cm"] = {"max": round(float(d.max()), 4), "moyen": round(float(d.mean()), 5)}
        cle = np.round(pts / 0.5).astype(np.int64)          # sommets confondus à 5 mm près
        _, inv, cnt = np.unique(cle, axis=0, return_inverse=True, return_counts=True)
        partages = cnt[inv.ravel()] > 1
        r["terrain_sommets_partages_entre_dalles"] = int(partages.sum())
        if partages.any():
            grp = {}
            for p, k in zip(pts[partages], inv.ravel()[partages]):
                grp.setdefault(int(k), []).append(p)
            ec = [np.ptp(np.array(v), axis=0).max() for v in grp.values()]
            r["terrain_ecart_max_sommets_partages_cm"] = round(float(max(ec)), 4)
    r["glb_taille_max_mo"] = round(max(tailles) / 1e6, 2) if tailles else 0
    tot = sum((P.sortie / e["fichier"]).stat().st_size for e in P.elements if "fichier" in e)
    r["taille_totale_mo"] = round(tot / 1e6, 1)
    r["fichier_le_plus_gros_mo"] = round(max((P.sortie / e["fichier"]).stat().st_size for e in P.elements
                                             if "fichier" in e) / 1e6, 2)
    par_type = {}
    for e in P.elements:
        par_type[e["type"]] = par_type.get(e["type"], 0) + 1
    r["elements_par_type"] = par_type
    r["instances_par_maillage"] = {e["maillage_jeu"].rsplit("/", 1)[1]: e["nombre"] for e in P.elements
                                   if e["type"] == "InstanceGroup"}
    r["instances_retirees_sur_chaussee"] = sum(e["retirees_sur_chaussee"] for e in P.elements if e["type"] == "InstanceGroup")
    r["instances_absentes_du_catalogue"] = [e["maillage_jeu"] for e in P.elements
                                            if e["type"] == "InstanceGroup" and not e["present_au_catalogue"]]
    return r


# --- programme principal --------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--echantillon", action="store_true", help="essais E3 et E4 seulement, dans pc/etape2_unreal/echantillon")
    ap.add_argument("--sortie", help="dossier de sortie (défaut : paquet_unreal/ ou l'échantillon)")
    ap.add_argument("--axes", default="X,Z,Y", help="correspondance d'axes de l'importeur glb (lue par la mire)")
    ap.add_argument("--pk-min", type=float)
    ap.add_argument("--pk-max", type=float)
    ap.add_argument("--px-dalle", type=int, default=2048, help="images des dalles de 500 m : 2048 (26 cm) ou 4096")
    ap.add_argument("--sol", choices=("jeu", "photo"), default="jeu",
                    help="jeu : matériau de terrain du jeu, masques et carte de couleur (scripts/15b_sols_du_jeu.py) ; "
                         "photo : photo aérienne plaquée, comme avant le 12/11/2026. L'échantillon reste en photo.")
    ap.add_argument("--lointain-clarte", type=int, default=1, help="1 : images du paysage lointain éclaircies ; 0 : telles quelles")
    ap.add_argument("--sous-bois", type=int, default=1,
                    help="1 : petits arbres le long des bords, là où le relevé laser montre de la végétation ; 0 : non")
    ap.add_argument("--bord-enrobe", type=int, default=1,
                    help="1 : bande de sol qui mord inégalement sur les bords de l'enrobé ; 0 : bord net")
    ap.add_argument("--arbres-lointains", type=int, default=1,
                    help="1 : arbres du jeu sur les versants entre 135 et 430 m de l'axe (cimes au-dessus du relief lointain) ; 0 : non")
    ap.add_argument("--falaises", type=int, default=1,
                    help="1 : versants très raides du paysage lointain teintés de calcaire clair (barres rocheuses) ; 0 : non")
    ap.add_argument("--lointain-aplat", type=float, default=0.85,
                    help="part de verticale mêlée aux normales du paysage lointain, loin de la route (0 = normales du relief)")
    ap.add_argument("--buissons", choices=("jeu", "script10"), default="jeu",
                    help="jeu : buissons du jeu (GroundCover/Willow) pour les arbustes de 0,55 m et plus ; script10 : "
                         "les maillages proposés par le script 10 (plantes rampantes et arbres réduits)")
    ap.add_argument("--mobilier", choices=("jeu", "sans"), default="jeu",
                    help="jeu : poteaux électriques et câbles, panneaux du rallye, barrières, haie (mobilier_bord_de_route.json)")
    ap.add_argument("--herbes", choices=("jeu", "sans"), default="jeu",
                    help="jeu : touffes d'herbe du jeu sur les bas-côtés (paquet complet seulement) ; sans : aucune")
    ap.add_argument("--glissieres", choices=("jeu", "modele"), default="jeu",
                    help="jeu : glissières métalliques du jeu posées le long de nos tronçons ; modele : nos lisses "
                         "modélisées. L'échantillon garde les nôtres.")
    args = ap.parse_args()
    if (args.pk_min is None) != (args.pk_max is None):
        raise SystemExit("--pk-min et --pk-max vont ensemble")
    t0 = time.time()
    sortie = Path(args.sortie) if args.sortie else (KIT / "echantillon" if args.echantillon else ROOT / "paquet_unreal")
    if sortie.exists():
        for sous in ("maillages", "textures", "instances"):
            shutil.rmtree(sortie / sous, ignore_errors=True)
    sortie.mkdir(parents=True, exist_ok=True)
    ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    ch = m08.chaussee()
    pkf = PK(ch, ref)
    P = Paquet(sortie, Axes(args.axes), args.echantillon, args.pk_min, args.pk_max)
    P._centre_e4 = pkf.A[int(np.argmin(np.abs(ch["pk"] - sum(PK_E4) / 2)))]
    mire(P)
    mire_relief(P)
    print("terrain…", flush=True)
    P.sol = {"mode": "photo"}
    G, D = ch["G"][:, :2], ch["D"][:, :2]
    ruban = shapely.union_all(shapely.make_valid(shapely.polygons(
        [np.array([G[i], G[i + 1], D[i + 1], D[i], G[i]]) for i in range(len(G) - 1)])))
    shapely.prepare(ruban)
    if args.sol == "jeu" and not args.echantillon:
        n_terrain = terrain_jeu(P, ref, args, ch, ruban)
    else:
        n_terrain = terrain(P, ref, pkf, args)
    sources = {}
    for m in lire_glb(MOD / "terrain_sol.glb"):
        sources[m["nom"]] = m["pos"]
    # correspondance nom source -> nom paquet pour le contrôle de raccord
    sources_paquet = {}
    for e in P.elements:
        if e["type"] == "StaticMesh" and "source" in e and e["source"].startswith("modele/terrain_sol.glb#"):
            sources_paquet[e["nom"]] = sources[e["source"].split("#")[1]]
    print("route, ouvrages, carrefours…", flush=True)
    route = lire_glb(MOD / "route_habillee.glb")
    ouvr = lire_glb(MOD / "ouvrages.glb")
    annx = lire_glb(MOD / "annexes.glb")
    glissieres_jeu = args.glissieres == "jeu" and not args.echantillon and args.pk_min is None
    if glissieres_jeu:
        ouvr = [m for m in ouvr if not m["mat"]["nom"].startswith("glissiere")]
    bali = lire_glb(MOD / "balisage.glb")
    mats = materiaux_modele(P, [route, ouvr, annx, bali], f"{UE}/Shared/Textures", f"{UE}/Shared/Materials", "")
    mi = lambda mat: mats[mat]                                            # noqa: E731
    chaussee = [m for m in route if m["mat"]["nom"] == "enrobe"]
    marquage = [m for m in route if m["mat"]["nom"] == "marquage"]
    aspect = [m for m in route if m["mat"]["nom"] in ("reprise", "fissure")]          # pièces d'enrobé, fissures pontées
    noms = {"route": par_troncon(P, pkf, chaussee, "Road", "route", f"{UE}/Road/Meshes", mi, args, False),
            "marquage": par_troncon(P, pkf, marquage, "RoadMarking", "route", f"{UE}/Road/Meshes", mi, args, False),
            "aspect": par_troncon(P, pkf, aspect, "RoadWear", "route", f"{UE}/Road/Meshes", mi, args),
            "ouvrages": par_troncon(P, pkf, ouvr, "Bridge", "ouvrages", f"{UE}/Bridges/Meshes", mi, args),
            "annexes": par_troncon(P, pkf, annx, "Junction", "annexes", f"{UE}/Junctions/Meshes", mi, args),
            "balisage": par_troncon(P, pkf, bali, "Tape", "balisage", f"{UE}/Props/Meshes", mi, args)}
    print("anneau lointain…", flush=True)
    n_loin = lointain(P, ref, args, pkf)
    print("instances…", flush=True)
    bilan_inst = instances(P, ref, Sol(), ruban, pkf, args)
    if glissieres_jeu:
        bilan_inst.update(glissieres_du_jeu(P, ref, ch, pkf, args))
    if args.mobilier == "jeu" and not args.echantillon and args.pk_min is None:
        bilan_inst.update(mobilier_du_bord(P, ref, pkf, Sol(), args))
        parois_rocheuses(P, ref, Sol())
    if args.herbes == "jeu" and not args.echantillon and args.pk_min is None and (MOD / "sols_jeu" / "sols_jeu.json").exists():
        bilan_inst.update(herbes_du_bord(P, ref, ch, pkf, Sol(), ruban, args))
    manifeste = {
        "description": f"Paquet d'import Unreal Engine 5.6 de la spéciale {NOM} (scripts/16_paquet_unreal.py)",
        "version": 1, "genere_le": time.strftime("%Y-%m-%d %H:%M"), "echantillon": args.echantillon,
        "chemins": {"racine": UE, "niveau": NIVEAU, "niveau_e3": f"{NIVEAU}_E3", "niveau_e4": f"{NIVEAU}_E4",
                    "materiau_secours": SECOURS, "editeur_seulement": EDITEUR},
        "repere": {
            "unreal": "X = est, Y = sud, Z = haut ; centimètres ; origine = axe de la chaussée au PK 0 (départ)",
            "depuis_gltf_du_projet": "UE_cm = 100 * (gX, gZ, gY)  (modele/*.glb : X est, Y haut, Z sud, mètres)",
            "depuis_lambert93": f"UE_cm = 100 * (x - {ref['x0']}, {ref['y0']} - y, z - {ref['z0']})",
            "maillages": "chaque maillage est recentré sur son pivot ; l'acteur se pose à acteur.position_cm, sans "
                         "rotation ni échelle",
            "axes_import_glb": {"valeur": P.axes.texte,
                                "sens": "UE_cm = 100 * M . g_fichier, M lue ligne par ligne (« X,Z,Y » : UE.X = g.X, "
                                        "UE.Y = g.Z, UE.Z = g.Y)",
                                "verification": "construire_niveau.py --mire : importe SM_GC_MireAxeX/Y/Z et en déduit la "
                                                "valeur réelle ; si elle diffère, relancer 16_paquet_unreal.py --axes <valeur>"},
            "points_de_controle": points_de_controle(ch, ref),
            "lacet": "degrés, autour de UE +Z, de +X (est) vers +Y (sud) ; arbres : tirage à graine fixe"},
        "essais": {"E3": {"description": "la dalle de 500 m qui contient le pont de pierre du PK 1653, avec sa photo et son "
                                         "relief, plus la mire d'axes", "niveau": f"{NIVEAU}_E3"},
                   "E4": {"description": f"PK {PK_E4[0]:.0f} à {PK_E4[1]:.0f} : route, marquage, pont et parapets, "
                                         "terrain fin et dalle, anneau proche, arbres, arbustes", "niveau": f"{NIVEAU}_E4",
                          "pk_m": list(PK_E4)},
                   "complet": {"description": "toute la spéciale", "niveau": NIVEAU}},
        "materiau_secours": {"chemin": SECOURS, "parametres": PARAM_SECOURS,
                             "role": "matériau simple créé par le script d'import pour voir le décor dans l'éditeur tant "
                                     "que le parent du jeu n'est pas confirmé ; à NE PAS livrer"},
        "sol": P.sol,
        "elements": P.elements,
    }
    manifeste["controle"] = controle(P, sources_paquet)
    manifeste["controle"].update({"terrain": n_terrain, "lointain": n_loin, "groupes": {k: len(v) for k, v in noms.items()},
                                  "instances": sum(bilan_inst.values()), "duree_s": round(time.time() - t0)})
    (sortie / "manifeste.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8",
                                           newline="\n")
    print(json.dumps(manifeste["controle"], ensure_ascii=False, indent=1))
    if manifeste["controle"]["erreurs"]:
        raise SystemExit(f"{len(manifeste['controle']['erreurs'])} erreurs de contrôle")


if __name__ == "__main__":
    main()
