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
Usage : python 16_paquet_unreal.py [--echantillon] [--pk-min A --pk-max B] [--axes X,Z,Y] [--sortie DOSSIER]
"""
import argparse
import csv
import gzip
import io
import json
import math
import shutil
import time
from pathlib import Path

import importlib.util
import numpy as np
import shapely
from PIL import Image
from scipy.spatial import cKDTree

from acr_geo import OUT, REF, ROOT

_spec = importlib.util.spec_from_file_location("modele_3d", Path(__file__).with_name("08_modele_3d.py"))
m08 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m08)

MOD = ROOT / "modele"
KIT = ROOT / "pc" / "etape2_unreal"
NOM = "GrandCaunet"
UE = f"/Game/Environments/{NOM}"
NIVEAU = f"/Game/Levels/{NOM}"
GRILLE0 = (913500.0, 6240500.0)     # coin sud-ouest commun des grilles de dalles (Lambert-93)
LOIN0 = (880000, 6210000)             # coin sud-ouest de la grille kilométrique de l'anneau lointain
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
def ecrire_glb(path, nom, section, pos, nrm, uv, tri):
    """Un maillage, un nœud, une section de matériau (nom seulement, sans texture) : l'import ne crée aucun
    matériau ni texture, et la section porte le nom de la variante à lui affecter."""
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
             "componentType": {np.float32: 5126, np.uint32: 5125, np.uint16: 5123}[a.dtype.type],
             "count": int(len(a) if a.ndim > 1 else a.size), "type": kind}
        if minmax:
            d["min"], d["max"] = a.min(0).tolist(), a.max(0).tolist()
        gl["accessors"].append(d)
        return len(gl["accessors"]) - 1

    pr = gl["meshes"][0]["primitives"][0]
    pr["attributes"]["POSITION"] = acc(pos.astype(np.float32), "VEC3", 34962, True)
    pr["attributes"]["NORMAL"] = acc(nrm.astype(np.float32), "VEC3", 34962)
    if uv is not None:
        pr["attributes"]["TEXCOORD_0"] = acc(uv.astype(np.float32), "VEC2", 34962)
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

    def maillage(self, nom, famille, dest, pos_g, nrm_g, uv, tri, section, essais, pk=None, extra=None):
        """pos_g, nrm_g : glTF du projet (m) ; écrit le glb recentré et renvoie l'élément du manifeste."""
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
        f, n_f, uv, t = dedoublonne(f, n_f, uv, t)
        fichier = Path("maillages") / famille / f"{nom}.glb"
        ecrire_glb(self.sortie / fichier, nom, section, f, n_f, uv, t)
        e = {"type": "StaticMesh", "nom": nom, "fichier": fichier.as_posix(), "destination": dest,
             "chemin_ue": f"{dest}/{nom}", "section_materiau": section, "materiau": section,
             "import": IMPORT_MAILLAGE,
             "acteur": {"label": nom, "position_cm": pivot.tolist(), "rotation_deg": [0.0, 0.0, 0.0],
                        "echelle": [1.0, 1.0, 1.0], "collision": "NoCollision", "mobilite": "Static",
                        "ombre_portee": not famille.startswith("lointain")},
             "bornes_locales_cm": {"min": np.round(loc.min(0), 1).tolist(), "max": np.round(loc.max(0), 1).tolist()},
             "sommets": int(len(f)), "triangles": int(len(t)), "essais": essais}
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
        P.maillage(nom, famille, dest_mesh, pos, nrm, uv, tri, nom_mat(mat), essais, pk=pkr,
                   extra={"troncon": kk})
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


def lointain(P, ref, args):
    """Anneau lointain : un maillage par dalle de 13 (1 km près, 5 km loin), ses images JPEG telles quelles."""
    src = MOD / "apercu" / "lointain.glb" if P.echantillon else MOD / "lointain.glb"   # échantillon : version légère
    ms = lire_glb(src)
    centre_e4 = None
    n = 0
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
        P.texture(nom_t, "lointain", f"{UE}/FarRing/Textures", im, essais, adressage="Clamp",
                  px_max=256 if P.echantillon else None, qualite=90)
        if "T_GC_ORM_Lointain" not in P.vus:
            P.texture("T_GC_ORM_Lointain", "commun", f"{UE}/Shared/Textures", image_unie((255, 255, 0)), ["E4", "complet"])
        P.materiau(nom_mi, f"{UE}/FarRing/Materials", {"couleur": nom_t, "orm": "T_GC_ORM_Lointain"}, essais,
                   note="anneau lointain : sans ombre portée ; pas de relief")
        P.maillage(nom_sm, "lointain", f"{UE}/FarRing/Meshes", m["pos"], m["nrm"], m["uv"], m["idx"], nom_mi, essais,
                   extra={"distance_min_e4_m": round(dmin), "source": f"{src.relative_to(ROOT).as_posix()}#{m['nom']}"})
        n += 1
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

    def table(famille, rows, chemin_de, hauteur, extra_cols, sur_terrain=True):
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
        groupes = {}
        for i, r in enumerate(rows):
            groupes.setdefault(chemin_de(r), []).append(i)
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
                                f"{hauteur(r):.2f}", f"{pk[i]:.0f}"] + [r.get(c, "") for c in extra_cols])
            e = P.ajoute({"type": "InstanceGroup", "nom": f"GC_{famille.capitalize()}_{nom}", "maillage_jeu": chemin,
                          "present_au_catalogue": chemin in cat, "fichier": fichier.as_posix(), "nombre": int(len(ids)),
                          "composant": "HierarchicalInstancedStaticMeshComponent", "collision": "NoCollision",
                          "hauteur_native_cm": None,
                          "echelle": "à l'import, scripts_editeur/attribution.py rechoisit le maillage dans ce dossier "
                                     "d'après la taille de chaque plante (releves/maillages_vegetation.json) et en "
                                     "déduit l'échelle ; le maillage nommé ici est tiré sans connaître les tailles",
                          "retirees_sur_chaussee": int(sur_chaussee[np.array(groupes[chemin])].sum()),
                          "essais": essais})
            bilan[e["nom"]] = e["nombre"]

    with open(OUT / "arbres.csv", encoding="utf-8") as f:
        arbres = list(csv.DictReader(f))
    table("arbres", arbres, lambda r: f"/Game/{r['famille_jeu']}/{r['element_jeu_propose']}",
          lambda r: float(r["hauteur_m"]), ["essence", "diametre_houppier_m"])
    with gzip.open(OUT / "arbustes.csv.gz", "rt", encoding="utf-8") as f:
        arbustes = list(csv.DictReader(f))
    table("arbustes", arbustes, lambda r: f"/Game/{r['famille_jeu']}/{r['element_jeu_propose']}",
          lambda r: float(r["hauteur_m"]), ["diametre_m"])
    with open(OUT / "balisage.csv", encoding="utf-8") as f:
        bal = [r for r in csv.DictReader(f) if r["type"] == "piquet de rubalise"]
    table("balisage", bal, lambda r: "/Game/" + r["maillage_jeu_propose"][len("acr/Content/"):],
          lambda r: 1.0, ["carrefour", "type", "cap_deg"], sur_terrain=False)
    return bilan


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
    bali = lire_glb(MOD / "balisage.glb")
    mats = materiaux_modele(P, [route, ouvr, annx, bali], f"{UE}/Shared/Textures", f"{UE}/Shared/Materials", "")
    mi = lambda mat: mats[mat]                                            # noqa: E731
    chaussee = [m for m in route if m["mat"]["nom"] == "enrobe"]
    marquage = [m for m in route if m["mat"]["nom"] != "enrobe"]
    noms = {"route": par_troncon(P, pkf, chaussee, "Road", "route", f"{UE}/Road/Meshes", mi, args, False),
            "marquage": par_troncon(P, pkf, marquage, "RoadMarking", "route", f"{UE}/Road/Meshes", mi, args, False),
            "ouvrages": par_troncon(P, pkf, ouvr, "Bridge", "ouvrages", f"{UE}/Bridges/Meshes", mi, args),
            "annexes": par_troncon(P, pkf, annx, "Junction", "annexes", f"{UE}/Junctions/Meshes", mi, args),
            "balisage": par_troncon(P, pkf, bali, "Tape", "balisage", f"{UE}/Props/Meshes", mi, args)}
    print("anneau lointain…", flush=True)
    n_loin = lointain(P, ref, args)
    print("instances…", flush=True)
    G, D = ch["G"][:, :2], ch["D"][:, :2]
    ruban = shapely.union_all(shapely.make_valid(shapely.polygons(
        [np.array([G[i], G[i + 1], D[i + 1], D[i], G[i]]) for i in range(len(G) - 1)])))
    shapely.prepare(ruban)
    bilan_inst = instances(P, ref, Sol(), ruban, pkf, args)
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
