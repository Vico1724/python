"""Étape 9 - Export au format d'échange « Stage IR » v2 du projet ACR Extra Stages.

Le Stage IR (docs/stage-ir.md du dépôt ACR Extra Stages) est le dossier que leur
constructeur côté ACR (`acr-ref stage-build`) consomme. Il est normalement produit à
partir de DiRT Rally 2.0 ; ici il est produit à partir de nos propres mesures.

Entrées : data/processed/chaussee_precise.csv (axe et bords au mètre), points_officiels_recales.csv,
          ouvrages_es.csv, annexes_revetues.geojson, modele/terrain.glb (étape 8), data/raw/mnt_lidarhd_50cm.tif
          (repérage des ponts) ; facultatifs : modele/annexes_collision.glb (étape 12, surfaces des carrefours),
          modele/ouvrages_collision.glb (étape 11, parapets et murs), modele/annexes_collision.glb (parapets du carrefour) et modele/balisage_collision.glb (étape 12)
Sorties (export/stage_ir/grand_caunet/) :
  stage.json             tout sauf la géométrie : identité, longueurs, repère, axe, portes (tous les ~10 m),
                         chronométrage, zone d'arrêt, reprise en piste, sol physique, surfaces, obstacles
                         (`objects`), notes du copilote (BROUILLON généré par la courbure de l'axe), auto-contrôles
  collision.glb          sol physique : un nœud et un maillage « collision », un primitif par code de surface
                         (TSD+ chaussée et enrobé annexe, DBK+ accotement 0-3 m et îlot, GRS+ terrain du couloir),
                         positions seules
  objects_collision.glb  obstacles en volumes simples (pavés, piquets en prismes), un primitif par matériau
                         de paroi du jeu
export/stage_ir/controle_grand_caunet.json : relecture des fichiers écrits (contrôle indépendant de l'écriture)

Obstacles (section `objects`, sous la forme que lit ObjectColliders.cs d'ACR Extra Stages) : chaque volume
balayé des glb de collision (11, 12) est découpé en pavés orientés, un par tronçon d'échantillonnage (~1 m) ;
un gabarit par type (pavé ou cylindre unitaire, origine à la base), une instance par pavé avec rotation et
échelle. La rubalise n'est pas un obstacle : un ruban ne retient pas une voiture, et les obstacles simples
du jeu ne se cassent pas (un ruban solide serait un mur invisible) ; elle n'est donc pas exportée.

Repère de l'IR (le format exige mètres, +Y haut, repère direct, même repère pour tous les fichiers) :
  X = x_L93 - x0 (est), Y = altitude NGF (absolue, pour que les altitudes des menus soient justes),
  Z = -(y_L93 - y0) (sud) ; (x0, y0) = axe au PK 0, comme modele/repere.json (qui, lui, prend Y relatif).
  Pour un sens de marche f, la droite du pilote est cross(f, +Y), comme dans l'IR de DR2.

Ce que l'exporteur ne produit pas (laissé vide ou null comme le prévoit le format) : maillages de rendu
DR2 (`render` = [], ni render/*.glb ni textures DDS : la voie retenue, `pc/`, n'en a pas besoin), cuisson
du sol (`ground_bake` absent), données brutes DR2 des notes (`pacenotes.raw` = null), recalage sur carte
de menu (`validation.route_map_fit` = null), fichier de reprise DR2 (`respawn.resetlines` = null).
"""
import csv
import gzip
import importlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acr_geo import OUT, ROOT, TO_L93, wgs  # noqa: E402
import shapely  # noqa: E402
from shapely.geometry import shape as geo_shape  # noqa: E402

M08 = importlib.import_module("08_modele_3d")      # mêmes lecteurs et même ruban de route que le modèle 3D

EXPORT = ROOT / "export" / "stage_ir"
DOSSIER = EXPORT / "grand_caunet"
STAGE_ID = "grand_caunet_rally_01_route_0"         # forme <lieu>_rally_<nn>_route_<n> exigée par leurs scripts
NOM = "Le Grand Caunet"
PAS_PORTES = 10.0                                  # m
TOL_PORTES = 0.25                                  # m : écart toléré entre la corde de deux portes et l'axe ou un bord
ACCOTEMENT = 3.0                                   # m au-delà du bord de chaussée : code DBK+
CODES = {                                          # code -> (matériau physique ACR, description)
    "TSD+": ("PM_SurfaceTarmacSmooth", "chaussée en enrobé (ruban de route mesuré) et enrobé annexe des carrefours"),
    "DBK+": ("PM_SurfaceGravelHard", f"accotement en terre, {ACCOTEMENT:g} m au-delà des bords, et îlots des carrefours"),
    "GRS+": ("PM_SurfaceGrass", "terrain naturel du couloir (garrigue, sous-bois)"),
}
PM = "/Game/Data/Gameplay/PhysicalMaterials/"
MOD = ROOT / "modele"
# surfaces des carrefours (modele/annexes_collision.glb) : mot du nom de matériau -> code de sol
SOL_ANNEXES = [("enrobe", "TSD+"), ("terre", "DBK+")]
# obstacles : matériau des glb de collision -> (paroi ACR, forme, gabarit). Les noms PM_Wall* sont dans le
# catalogue du jeu ; PM_WallRock, PM_WallConcrete et PM_WallPlasticBarrier sont aussi utilisés par leur
# config/surface-map.toml ; PM_WallPlasticPole ne l'est pas : s'il n'est pas inscrit au registre des surfaces,
# leur constructeur le remplace par PM_WallBasic (StageBuild.cs, objets « unregistered_remapped »).
OBSTACLES = {
    "pierre": ("PM_WallRock", "box", "gc_parapet_pierre"),
    "beton": ("PM_WallConcrete", "box", "gc_parapet_beton"),
    "plastique_barriere": ("PM_WallPlasticBarrier", "box", "gc_barriere"),
    "plastique_piquet": ("PM_WallPlasticPole", "cylinder", "gc_piquet_rubalise"),
    # glissières métalliques (script 11, data/reference/glissieres.json) ; PM_WallMetalGuardrail est au
    # catalogue du jeu et dans leur config/surface-map.toml (« sArmco »)
    "metal_glissiere": ("PM_WallMetalGuardrail", "box", "gc_glissiere"),
}
SOURCES_OBSTACLES = ("ouvrages_collision.glb", "annexes_collision.glb", "balisage_collision.glb")
CATALOGUE = gzip.open(ROOT / "data" / "reference" / "catalogue_jeu_25170642.txt.gz", "rt", encoding="utf-8").read()
CATALOGUE = "\n".join(f'"{m}"' for m in re.findall(r"PhysicalMaterials/(PM_\w+)\.uasset", CATALOGUE))
SPLITS = ("INTER2", "INTER6")                      # points officiels retenus comme temps intermédiaires

# notes du copilote (vocabulaire de config/pacenote-map.toml : direction left/right, sévérité "6".."1",
# square, hairpin ; 6 = le plus rapide). Rayons = médianes de la spéciale hôte ACR (Pacenotes.cs, HostRadius)
FENETRE = 20.0                                     # m : courbure = variation de cap sur cette longueur
R_VIRAGE = 250.0                                   # m : en dessous, on est dans un virage
FUSION = 10.0                                      # m : deux morceaux du même sens séparés de moins sont fusionnés
ANGLE_MIN = 10.0                                   # degrés de cap cumulés pour annoncer
SEUILS = [("1", 17), ("2", 23), ("3", 34), ("4", 54), ("5", 81), ("6", 150)]
ANGLE_DR2 = {"6": 15, "5": 25, "4": 40, "3": 50, "2": 65, "1": 80, "square": 90, "hairpin": 140}
LIEN = 40.0                                        # m : virages plus proches = même annonce (« dans », « et »)
AVANCE = 80.0                                      # m : une note est lue ~50-150 m avant son virage (DR2)
DISTANCES = [40, 50, 60, 70, 80, 90, 100, 120, 150, 200, 250, 300]


# --- données ---------------------------------------------------------------------------
def charger():
    ch = M08.chaussee()
    with open(OUT / "chaussee_precise.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ch["largeur"] = np.array([float(r["largeur_m"]) for r in rows])
    ch["devers"] = np.array([float(r["devers_pct"]) for r in rows])
    return ch


def vers_ir(p, ref):
    """(N,3) Lambert-93 + altitude -> (N,3) repère de l'IR (float64)."""
    p = np.atleast_2d(p)
    return np.column_stack([p[:, 0] - ref["x0"], p[:, 2], -(p[:, 1] - ref["y0"])])


def r3(v, nd=3):
    return [round(float(x), nd) for x in v]


def point_sur_axe(ch, x, y, pk_attendu, fen=400.0):
    """Ligne de chaussee_precise la plus proche en plan du point, PK à ± fen du PK attendu."""
    sel = np.flatnonzero(np.abs(ch["pk"] - pk_attendu) <= fen)
    d = np.hypot(ch["A"][sel, 0] - x, ch["A"][sel, 1] - y)
    k = int(np.argmin(d))
    return int(sel[k]), float(d[k])


# --- lecture des glb du modèle ----------------------------------------------------------
def lire_modele(path):
    """glb de modele/ (étapes 11, 12) : liste de (maillage, matériau, positions (N,3) repère glTF du modèle,
    triangles). Indices 8, 16 ou 32 bits ; les nœuds ne doivent pas porter de transformation."""
    b = Path(path).read_bytes()
    n = int(np.frombuffer(b, "<u4", 1, 12)[0])
    gl = json.loads(b[20:20 + n])
    off = 20 + n + 8
    for nd in gl.get("nodes", []):
        if any(k in nd for k in ("matrix", "translation", "rotation", "scale")):
            raise SystemExit(f"{path} : nœud {nd.get('name')} transformé, non prévu")

    def arr(i):
        a = gl["accessors"][i]
        v = gl["bufferViews"][a["bufferView"]]
        dt = {5126: "<f4", 5125: "<u4", 5123: "<u2", 5121: "u1"}[a["componentType"]]
        k = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
        if v.get("byteStride", 0) not in (0, np.dtype(dt).itemsize * k):
            raise SystemExit(f"{path} : données entrelacées non prévues")
        return np.frombuffer(b, dt, a["count"] * k, off + v.get("byteOffset", 0) + a.get("byteOffset", 0)).reshape(-1, k)

    out = []
    for m in gl["meshes"]:
        for pr in m["primitives"]:
            if pr.get("mode", 4) != 4:
                raise SystemExit(f"{path} : primitif non triangulaire")
            mat = gl["materials"][pr["material"]]["name"] if "material" in pr else ""
            out.append((m.get("name", ""), mat, arr(pr["attributes"]["POSITION"]).astype(np.float64),
                        arr(pr["indices"]).reshape(-1, 3).astype(np.int64)))
    return out


def modele_vers_ir(p, ref):
    """repère glTF du modèle (Y relatif) -> repère de l'IR (Y = altitude)."""
    q = np.array(p, dtype=np.float64)
    q[:, 1] += ref["z0"]
    return q


def ir_vers_l93(p, ref):
    return np.column_stack([p[:, 0] + ref["x0"], ref["y0"] - p[:, 2]])


# --- sol physique ------------------------------------------------------------------------
def sol_physique(ch, ref, rapport):
    """Ruban de route (celui de l'étape 8) + terrain du modèle 3D (sommets fusionnés) + surfaces annexes des
    carrefours (étape 12) ; le terrain entièrement recouvert par une annexe est retiré. Y absolu."""
    route = M08.route(ch, ref)
    rp = route["pos"].astype(np.float64)
    rt = route["idx"].astype(np.int64)
    src = MOD / "terrain.glb"
    if not src.exists():
        raise SystemExit("modele/terrain.glb absent : lancer d'abord 08_modele_3d.py")
    tp, tt, base = [], [], 0
    for _, p, _, _, t in M08.read_glb(src):
        tp.append(p.astype(np.float64))
        tt.append(t.astype(np.int64) + base)
        base += len(p)
    tp, tt = np.vstack(tp), np.vstack(tt)
    # les dalles de 500 m dupliquent leurs sommets de bord : fusion au millimètre
    key = np.round(tp * 1000).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    tp, tt = tp[first], inv.ravel()[tt]
    tt = tt[(tt[:, 0] != tt[:, 1]) & (tt[:, 1] != tt[:, 2]) & (tt[:, 0] != tt[:, 2])]
    for p in (rp, tp):
        p[:, 1] += ref["z0"]                      # Y relatif du modèle -> altitude NGF

    # surfaces annexes des carrefours (facultatives)
    ann = {"TSD+": [], "DBK+": []}
    info = {"fichier": None, "triangles": {}, "terrain_retire_sous_annexes": 0}
    fa = MOD / "annexes_collision.glb"
    if fa.exists():
        info["fichier"] = "modele/annexes_collision.glb"
        for nom, mat, p, t in lire_modele(fa):
            code = next((c for mot, c in SOL_ANNEXES if mot in mat), None)
            if code is None and mat in OBSTACLES:
                continue                                  # parapets du carrefour : exportés comme obstacles
            if code is None:
                print(f"attention : matériau d'annexe inconnu « {mat} » ({nom}) ignoré")
                continue
            ann[code].append((modele_vers_ir(p, ref), t))
            info["triangles"][f"{nom} ({mat})"] = f"{len(t)} -> {code}"
        # terrain sous les surfaces revêtues et l'îlot : retiré quand ses trois sommets sont à la fois dans un
        # polygone de annexes_revetues.geojson et sous le maillage des annexes (les annexes passent 3 cm au-dessus
        # du terrain ; un triangle à cheval est gardé, pour ne laisser aucun trou si les deux fichiers divergent)
        gj = json.loads((OUT / "annexes_revetues.geojson").read_text(encoding="utf-8"))
        polys = []
        for f in gj["features"]:
            if f["geometry"]["type"] in ("Polygon", "MultiPolygon"):
                g = geo_shape(f["geometry"])
                polys.append(shapely.transform(g, lambda c: np.column_stack(TO_L93.transform(c[:, 0], c[:, 1]))))
        if polys:
            zone = shapely.union_all(polys)
            shapely.prepare(zone)
            xy = ir_vers_l93(tp, ref)
            dedans = shapely.contains_xy(zone, xy[:, 0], xy[:, 1])
            couvre = Sol({c: concat(v) for c, v in ann.items() if v})
            for i in np.flatnonzero(dedans):
                dedans[i] = couvre.h(tp[i, 0], tp[i, 2]) is not None
            sous = dedans[tt].all(axis=1)
            tt = tt[~sous]
            info["terrain_retire_sous_annexes"] = int(sous.sum())
    else:
        print("modele/annexes_collision.glb absent : pas de surfaces annexes (facultatif)")
    rapport["annexes"] = info

    # accotement : centre du triangle à moins de ACCOTEMENT m (en plan) d'un bord de chaussée
    bords = np.vstack([vers_ir(ch["G"], ref), vers_ir(ch["D"], ref)])[:, [0, 2]]
    c = tp[tt].mean(axis=1)[:, [0, 2]]
    d, _ = cKDTree(bords).query(c)
    acc = d <= ACCOTEMENT
    out = {"TSD+": [(rp, rt)] + ann["TSD+"], "DBK+": [compact(tp, tt[acc])] + ann["DBK+"],
           "GRS+": [compact(tp, tt[~acc])]}
    return {c: concat(v) for c, v in out.items()}


def concat(parts):
    P, T, k = [], [], 0
    for p, t in parts:
        P.append(p)
        T.append(t + k)
        k += len(p)
    return np.vstack(P), np.vstack(T)


# --- obstacles ---------------------------------------------------------------------------
def sections_balayees(V):
    """Volumes balayés de 11_route_ouvrages.boite() mis bout à bout : chaque bloc a 8n + 8 sommets (4 faces
    de 2n sommets C0C1, C1C2, C2C3, C3C0, puis 2 bouchons de 4). Renvoie une liste de (n, 4, 3) : les 4 coins
    de chaque section (C0, C1 en bas, C2, C3 en haut). ValueError si la disposition n'est pas reconnue."""
    out, o = [], 0
    while o < len(V):
        for n in range(2, (len(V) - o - 8) // 8 + 1):
            blk = V[o:o + 8 * n]
            if (np.allclose(blk[2 * n:3 * n], blk[n:2 * n], atol=1e-5) and np.allclose(blk[4 * n:5 * n], blk[3 * n:4 * n], atol=1e-5)
                    and np.allclose(blk[6 * n:7 * n], blk[5 * n:6 * n], atol=1e-5) and np.allclose(blk[7 * n:8 * n], blk[0:n], atol=1e-5)):
                out.append(np.stack([blk[0:n], blk[n:2 * n], blk[3 * n:4 * n], blk[5 * n:6 * n]], axis=1))
                o += 8 * n + 8
                break
        else:
            raise ValueError(f"disposition de volume balayé non reconnue au sommet {o}")
    return out


def paves(sec):
    """Un pavé orienté par tronçon entre deux sections : (centre, axes (3,3) en colonnes x=épaisseur,
    y=hauteur, z=longueur, dimensions (l_x, l_y, l_z))."""
    out = []
    for i in range(len(sec) - 1):
        Q = np.vstack([sec[i], sec[i + 1]])                     # 8 coins
        z = sec[i + 1].mean(0) - sec[i].mean(0)
        if np.linalg.norm(z) < 1e-6:
            continue
        z /= np.linalg.norm(z)
        y = np.array([0.0, 1.0, 0.0]) - z * z[1]
        if np.linalg.norm(y) < 1e-3:                             # tronçon vertical (non prévu)
            continue
        y /= np.linalg.norm(y)
        x = np.cross(y, z)
        R = np.column_stack([x, y, z])
        loc = Q @ R
        lo, hi = loc.min(0), loc.max(0)
        out.append((R @ ((lo + hi) / 2), R, hi - lo))
    return out


def quaternion(R):
    """Matrice de rotation (colonnes = axes locaux) -> quaternion unitaire [x, y, z, w]."""
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1) * 2
        q = [(R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s, s / 4]
    else:
        i = int(np.argmax(np.diag(R)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = math.sqrt(1 + R[i, i] - R[j, j] - R[k, k]) * 2
        q = [0.0] * 4
        q[i] = s / 4
        q[j] = (R[j, i] + R[i, j]) / s
        q[k] = (R[k, i] + R[i, k]) / s
        q[3] = (R[k, j] - R[j, k]) / s
    q = np.array(q)
    return q / np.linalg.norm(q)


def obstacles(ref):
    """Section `objects` du Stage IR (forme lue par ObjectColliders.cs) + volumes pour objects_collision.glb."""
    gabarits, instances, volumes, info = {}, [], {}, {"sources": [], "par_materiau": {}, "non_exportes": {}}
    for nom_f in SOURCES_OBSTACLES:
        f = MOD / nom_f
        if not f.exists():
            print(f"modele/{nom_f} absent : obstacles correspondants non exportés (facultatif)")
            continue
        info["sources"].append(f"modele/{nom_f}")
        for nom, mat, p, t in lire_modele(f):
            if mat not in OBSTACLES:
                if any(mot in mat for mot, _ in SOL_ANNEXES):
                    continue                                  # surface de roulage des carrefours (sol physique)
                raison = ("rubalise : pas un obstacle physique" if "rubalise" in mat
                          else "matériau sans paroi du jeu associée")
                info["non_exportes"][f"{nom} ({mat})"] = raison
                print(f"obstacles : {nom} ({mat}) non exporté — {raison}")
                continue
            paroi, forme, gab = OBSTACLES[mat]
            secs = sections_balayees(modele_vers_ir(p, ref))
            if gab not in gabarits:
                dims = ({"width": 1.0, "height": 1.0, "length": 1.0, "shell": 0.0} if forme == "box"
                        else {"height": 1.0, "radius": 0.5, "shell": 0.0})
                gabarits[gab] = {
                    "source": f"modele/{nom_f} ({mat})", "renderables": [], "inactive_subentities": 0, "constraints": 0,
                    "bodies": [{"sub_entity": gab, "static": True, "renderable": None, "shapes": [{
                        "id": f"{gab}_col_shape", "kind": forme, "dimensions": dims,
                        "transform": {"position": [0.0, 0.5, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0], "scale": None,
                                      "matrix": None},
                        "shape_class": gab, "dr2_material": None, "acr_wall": paroi, "breaks_on_impulse": None,
                        "mesh_file": None}]}]}
            n0 = len(instances)
            for s in secs:
                for c, R, L in paves(s):
                    if forme == "cylinder":                     # piquet : diamètre = plus grande dimension en plan
                        d = float(max(L[0], L[2]))
                        L = np.array([d, L[1], d])
                    base = c - R[:, 1] * L[1] / 2                # origine à la base, comme les objets DR2
                    instances.append({"id": f"{gab}_{len(instances):04d}", "template": gab, "kind": "basic", "tag": None,
                                      "transform": {"position": r3(base), "rotation": r3(quaternion(R), 6),
                                                    "scale": r3(L, 4), "matrix": None},
                                      "_paroi": paroi, "_forme": forme, "_centre": c, "_R": R, "_L": L})
            info["par_materiau"][f"{nom} ({mat})"] = f"{len(instances) - n0} {forme} -> {paroi}"
    for it in instances:
        volumes.setdefault(it["_paroi"], []).append(volume(it["_forme"], it["_centre"], it["_R"], it["_L"]))
    publiques = [{k: v for k, v in it.items() if not k.startswith("_")} for it in instances]
    return gabarits, publiques, {k: concat(v) for k, v in volumes.items()}, info


def volume(forme, c, R, L):
    """Pavé (8 sommets) ou prisme à 8 pans du piquet, orienté vers l'extérieur."""
    if forme == "box":
        u = np.array([[i, j, k] for i in (-.5, .5) for j in (-.5, .5) for k in (-.5, .5)])
        P = c + (u * L) @ R.T
        f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        T = [t for a, b, cc, d in f for t in ((a, b, cc), (a, cc, d))]
    else:
        a = np.linspace(0, 2 * np.pi, 9)[:-1]
        ring = np.column_stack([np.cos(a) * L[0] / 2, np.zeros(8), np.sin(a) * L[2] / 2])
        u = np.vstack([ring + [0, -L[1] / 2, 0], ring + [0, L[1] / 2, 0]])
        P = c + u @ R.T
        T = [t for i in range(8) for t in ((i, (i + 1) % 8 + 8, (i + 1) % 8), (i, i + 8, (i + 1) % 8 + 8))]
        T += [(0, k + 1, k) for k in range(1, 7)] + [(8, 8 + k, 9 + k) for k in range(1, 7)]
    T = np.array(T)
    nrm = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    out = ((P[T].mean(1) - c) * nrm).sum(1) < 0
    T[out] = T[out][:, [0, 2, 1]]
    return P, T


def compact(p, t):
    used, inv = np.unique(t, return_inverse=True)
    return p[used], inv.reshape(-1, 3)


def ecrire_glb(path, prims, nom="collision"):
    """Un nœud et un maillage `nom`, un primitif par code (ou matériau) ; POSITION + indices seulement."""
    gl = {"asset": {"version": "2.0", "generator": "acr-grand-caunet 09_export_stage_ir.py"},
          "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"name": nom, "mesh": 0}],
          "meshes": [{"name": nom, "primitives": []}], "materials": [], "accessors": [],
          "bufferViews": [], "buffers": []}
    blob = bytearray()

    def view(data, target):
        while len(blob) % 4:
            blob.append(0)
        gl["bufferViews"].append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data), "target": target})
        blob.extend(data)
        return len(gl["bufferViews"]) - 1

    for code, (p, t) in prims.items():
        p32 = p.astype(np.float32)
        gl["accessors"].append({"bufferView": view(p32.tobytes(), 34962), "componentType": 5126, "count": len(p32),
                                "type": "VEC3", "min": p32.min(0).tolist(), "max": p32.max(0).tolist()})
        ia = len(gl["accessors"]) - 1
        gl["accessors"].append({"bufferView": view(t.astype(np.uint32).ravel().tobytes(), 34963),
                                "componentType": 5125, "count": int(t.size), "type": "SCALAR"})
        gl["materials"].append({"name": code})
        gl["meshes"][0]["primitives"].append({"attributes": {"POSITION": ia}, "indices": ia + 1,
                                              "material": len(gl["materials"]) - 1, "mode": 4})
    while len(blob) % 4:
        blob.append(0)
    gl["buffers"].append({"byteLength": len(blob)})
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    with open(path, "wb") as f:
        f.write(b"glTF" + np.array([2, 12 + 8 + len(js) + 8 + len(blob)], "<u4").tobytes())
        f.write(np.array([len(js), 0x4E4F534A], "<u4").tobytes() + js)
        f.write(np.array([len(blob), 0x004E4942], "<u4").tobytes() + bytes(blob))


# --- notes du copilote (brouillon) -------------------------------------------------------
def virages(ch, pk_debut, pk_fin):
    """Virages de l'axe précis : courbure = variation de cap sur FENETRE m, en abscisse plane."""
    xy = ch["A"][:, :2]
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])
    t = np.arange(0.0, s[-1], 1.0)
    P = np.column_stack([np.interp(t, s, xy[:, 0]), np.interp(t, s, xy[:, 1])])
    pk = np.interp(t, s, ch["pk"])
    cap = np.unwrap(np.arctan2(np.gradient(P[:, 1]), np.gradient(P[:, 0])))
    h = int(FENETRE / 2)
    k = np.zeros_like(cap)
    k[h:-h] = (cap[2 * h:] - cap[:-2 * h]) / FENETRE      # rad/m, > 0 = à gauche (sens trigonométrique)
    sgn = np.sign(k) * (np.abs(k) > 1 / R_VIRAGE)
    morceaux = [[a, b, v] for v in (-1, 1) for a, b in M08.runs(sgn == v)]
    fus = []                                                  # fusion des morceaux voisins du même sens
    for a, b, v in sorted(morceaux):
        if fus and fus[-1][2] == v and a - fus[-1][1] <= FUSION:
            fus[-1][1] = b
        else:
            fus.append([a, b, v])
    out = []
    for a, b, v in fus:
        turn = float(np.degrees(k[a:b + 1].sum()))            # cap cumulé (pas de 1 m)
        rmin = float(1 / np.abs(k[a:b + 1]).max())
        if abs(turn) < ANGLE_MIN or pk[a] < pk_debut or pk[b] > pk_fin:
            continue
        sev = severite(rmin, abs(turn), b - a)
        if sev is None:
            continue
        out.append({"pk_debut": float(pk[a]), "pk_fin": float(pk[b]), "sens": "left" if v > 0 else "right",
                    "virage_deg": round(abs(turn), 1), "rayon_min_m": round(rmin, 1), "severite": sev})
    return out


def severite(rmin, turn, longueur):
    # la fenêtre de 20 m adoucit les épingles : rayon mesuré ~20 m pour un rayon réel ~14 m
    if rmin < 11 or (turn >= 135 and rmin < 25):
        return "hairpin"
    if 70 <= turn <= 110 and rmin < 16 and longueur <= 30:
        return "square"
    for sev, r in SEUILS:
        if rmin < r:
            return sev
    return None


def notes(ch, vir, gd_at_pk, pos_at_pk, pk_fin, start_gate_distance):
    """Jetons normalisés de l'IR v2 (docs/stage-ir.md, pacenotes.tokens), dans l'ordre de la route."""
    appels = []                                  # liste de listes de virages
    for v in vir:
        if appels and len(appels[-1]) < 2 and v["pk_debut"] - appels[-1][-1]["pk_fin"] < LIEN:
            appels[-1].append(v)
        else:
            appels.append([v])
    tokens, lu_prec = [], -1e9
    for n, grp in enumerate(appels, start=1):
        lu = max(grp[0]["pk_debut"] - AVANCE, lu_prec + 10.0, 0.0)
        lu_prec = lu
        gd = gd_at_pk(lu)
        base = {"call": n, "distance_m": round(gd - start_gate_distance, 1), "delay_ms": 0,
                "gate_distance": round(gd, 2), "position": r3(pos_at_pk(lu))}
        sub = 0
        for v in grp:
            sub += 1
            tokens.append({**base, "subcall": sub, "kind": "corner", "direction": v["sens"], "severity": v["severite"],
                           "angle": ANGLE_DR2[v["severite"]], "modifiers": list(v.get("modificateurs", [])),
                           "link_code": None,
                           "brouillon": {"pk_virage": [round(v["pk_debut"]), round(v["pk_fin"])],
                                         "virage_deg": v["virage_deg"], "rayon_min_m": v["rayon_min_m"],
                                         "severite_calculee": v.get("severite_calculee", v["severite"]),
                                         "libelle": v.get("libelle"), "retouches": v.get("retouches", [])}})
        suivant = appels[n][0]["pk_debut"] if n < len(appels) else None
        if suivant is not None:
            ecart = suivant - grp[-1]["pk_fin"]
            if LIEN <= ecart <= 325:
                dist = min(DISTANCES, key=lambda x: abs(x - ecart))
                tokens.append({**base, "subcall": sub + 1, "kind": "distance", "distance_call_m": dist,
                               "modifiers": [], "brouillon": {"ecart_mesure_m": round(ecart)}})
    lu = max(pk_fin - 160.0, lu_prec + 10.0)
    gd = gd_at_pk(lu)
    tokens.append({"call": len(appels) + 1, "subcall": 1, "distance_m": round(gd - start_gate_distance, 1),
                   "delay_ms": 0, "kind": "finish", "modifiers": [], "gate_distance": round(gd, 2),
                   "position": r3(pos_at_pk(lu))})
    return tokens


def objets_ir(obst):
    gabarits, instances, volumes, info = obst
    if not instances:
        return None
    parois = sorted({sh["acr_wall"] for g in gabarits.values() for b in g["bodies"] for sh in b["shapes"]})
    return {
        "sources": {"instances": info["sources"], "templates": info["sources"], "shape_classes": None},
        "corridor_m": float(M08.CORRIDOR), "instances_total": len(instances), "instances_in_corridor": len(instances),
        "cloth_instances_skipped": 0, "unknown_shape_kinds": [],
        "collision": {"file": "objects_collision.glb", "triangles": int(sum(len(t) for _, t in volumes.values())),
                      "meshes": [{"gltf_material": w, "acr_physical_material": w, "acr_asset_path": PM + w,
                                  "primitives": sum(1 for i in instances if gabarits[i["template"]]["bodies"][0]
                                                    ["shapes"][0]["acr_wall"] == w)} for w in parois],
                      "mesh_shapes": []},
        "render": None,
        "wall_classes": [{"shape_class": k, "dr2_material": None, "dr2_core_material": None,
                          "acr_wall": [g["bodies"][0]["shapes"][0]["acr_wall"]], "templates": 1} for k, g in gabarits.items()],
        "templates": gabarits,
        "instances": instances,
    }


def portes_adaptees(garde, courbes, dist):
    """Ajoute des portes là où l'axe ou un bord (tous les mètres) s'écarte de plus de TOL_PORTES de la corde entre
    deux portes : leur constructeur trace la chaussée (corridor, splines de bord) en reliant les portes par des
    segments ; sans cela, un rétrécissement de pont ou un carrefour serait mal décrit et les parapets jugés « sur la
    route »."""
    garde = list(garde)
    ajout = True
    while ajout:
        ajout = False
        nouv = [garde[0]]
        for a, b in zip(garde, garde[1:]):
            if b - a > 1:
                u = ((dist[a:b + 1] - dist[a]) / (dist[b] - dist[a]))[:, None]
                ecart = np.max([np.linalg.norm(c[a:b + 1] - (c[a] + u * (c[b] - c[a])), axis=1) for c in courbes], axis=0)
                k = int(np.argmax(ecart))
                if ecart[k] > TOL_PORTES:
                    nouv.append(a + k)
                    ajout = True
            nouv.append(b)
        garde = nouv
    return np.array(garde)


def retirer_sur_chaussee(stage, prims):
    """Retire les obstacles que leur constructeur supprimerait (ObjectColliders.Build : plus de 0,3 m dans le
    corridor, à hauteur de voiture, au-dessus de l'enrobé) et les liste ; c'est le signe que le balisage ou un
    parapet ne coïncide plus avec les bords de chaussee_precise.csv (relancer 11 / 12)."""
    ob = stage["objects"]
    couloir, sol = Couloir(stage), Sol(prims)
    pk = np.array([g["pk_m"] for g in stage["gates"]])
    tree = cKDTree(np.array(stage["centreline"])[:, [0, 2]])
    garde, retires = [], []
    for inst in ob["instances"]:
        sh = ob["templates"][inst["template"]]["bodies"][0]["shapes"][0]
        o, A, L = forme_monde(sh, inst)
        grille = np.array([[i, j, k] for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)], float)
        pen = 0.0
        for q in o + (grille * L / 2) @ A.T:
            c, zc = couloir.clearance(q[0], q[2])
            if c < 0 and zc - 1.0 < q[1] < zc + 2.5 and sol.code(q[0], q[2]) == "TSD+":
                pen = max(pen, -c)
        if pen > 0.3:
            retires.append({"id": inst["id"], "pk_m": float(pk[tree.query(o[[0, 2]])[1]]), "penetration_m": round(pen, 2),
                            "centre": r3(o), "demi_diagonale_m": round(float(np.linalg.norm(L) / 2), 3)})
        else:
            garde.append(inst)
    ob["instances"] = garde
    ob["instances_total"] = ob["instances_in_corridor"] = len(garde)
    stage["export"]["obstacles"]["retires_sur_la_chaussee"] = retires
    if retires:
        print(f"attention : {len(retires)} obstacles retirés car sur la chaussée (PK "
              f"{min(r['pk_m'] for r in retires):.0f} à {max(r['pk_m'] for r in retires):.0f}) : "
              "balisage / parapets à remettre en cohérence avec chaussee_precise.csv (étapes 11, 12)")


def forme_monde(sh, inst):
    """Centre, axes unitaires (colonnes) et dimensions d'une forme placée (même calcul qu'ObjectColliders)."""
    M = trs_numerics(sh["transform"]) @ trs_numerics(inst["transform"])
    o = M[3, :3]
    e = [M[k, :3] for k in range(3)]
    n = [np.linalg.norm(v) for v in e]
    d = sh["dimensions"]
    if sh["kind"] == "box":
        L = np.array([d["width"] * n[0], d["height"] * n[1], d["length"] * n[2]])
    else:
        r = d["radius"] * (n[0] + n[2]) / 2
        L = np.array([2 * r, d["height"] * n[1], 2 * r])
    return o, np.column_stack([v / k for v, k in zip(e, n)]), L


def volumes_retenus(stage, obst):
    ids = {i["id"] for i in stage["objects"]["instances"]}
    paroi = {g: t["bodies"][0]["shapes"][0]["acr_wall"] for g, t in stage["objects"]["templates"].items()}
    vol = {}
    for i in stage["objects"]["instances"]:
        sh = stage["objects"]["templates"][i["template"]]["bodies"][0]["shapes"][0]
        o, A, L = forme_monde(sh, i)
        vol.setdefault(paroi[i["template"]], []).append(volume(sh["kind"], o, A, L))
    for w in stage["objects"]["collision"]["meshes"]:
        w["primitives"] = sum(1 for i in stage["objects"]["instances"] if paroi[i["template"]] == w["gltf_material"])
    out = {k: concat(v) for k, v in vol.items()}
    stage["objects"]["collision"]["triangles"] = int(sum(len(t) for _, t in out.values()))
    assert len(ids) == len(stage["objects"]["instances"])
    return out


# --- retouches des notes (relevé vidéo) -------------------------------------------------
RETOUCHES = ROOT / "data" / "reference" / "notes_copilote_retouches.json"
# Ce que leur constructeur sait dire (config/pacenote-map.toml + Pacenotes.Generate) : un virage (sens, sévérité
# "6".."1", square, hairpin), le modificateur dont_cut -> DontCut, les distances, Into/And entre virages liés et
# l'arrivée. Tout autre jeton (kind "unknown", modificateur non listé) est abandonné par Pacenotes.Generate.
DANGERS_EXPRIMABLES = {"ne_pas_couper": "dont_cut"}
VOCABULAIRE = {
    "exprimable": "virage (gauche/droite, 6 à 1, square, hairpin), dont_cut (« ne pas couper » -> jeton DontCut), "
                  "distances 40-400 m, « dans » / « et » entre virages enchaînés, arrivée",
    "non_exprimable": "pont, ponceau, étroit, gravillons, revêtement, public, parapet, glissière, carrefour, long, "
                      "très long, sur pont, crête",
    "remarque": "le jeu possède d'autres annonces (icônes Caution, Crest, OverCrest, Bumps, Kinks, Tightens, Opens, "
                "Jump... dans le catalogue 25170642), mais leur constructeur ne sait pas les produire ; leurs noms exacts "
                "dans DT_PacenoteTokens_EA ne sont pas vérifiés",
}


def charger_retouches():
    if not RETOUCHES.exists():
        print("notes_copilote_retouches.json absent : notes calculées seules")
        return None
    return json.loads(RETOUCHES.read_text(encoding="utf-8"))


def appliquer_retouches(vir, cfg, pk_fin):
    """Notes calculées + retouches manuelles. Un virage est trouvé par son PK et son sens (tolérance en mètres),
    jamais par son numéro. Renvoie (virages retouchés, compte rendu)."""
    vir = [{**v, "modificateurs": [], "retouches": [], "libelle": None, "severite_calculee": v["severite"]} for v in vir]
    out = {"bilan": {"fichier": None, "appliquees": [], "non_appliquees": []}, "dangers_non_exprimables": []}
    if cfg is None:
        return vir, out
    out["bilan"]["fichier"] = RETOUCHES.relative_to(ROOT).as_posix()
    tol = float(cfg.get("tolerance_pk_m", 30))
    src = cfg.get("source_par_defaut", "")

    def trouver(pk, sens):
        cand = [(max(v["pk_debut"] - pk, pk - v["pk_fin"], 0.0), i) for i, v in enumerate(vir)
                if (sens is None or v["sens"] == sens) and v["pk_debut"] - tol <= pk <= v["pk_fin"] + tol]
        return min(cand)[1] if cand else None

    def trace(r, quoi, v=None):
        e = {"action": r["action"], "pk_m": r.get("pk_m", r.get("pk_debut")), "quoi": quoi,
             "source": r.get("source", src), "confiance": r.get("confiance")}
        if v is not None:
            e["virage_pk"] = [round(v["pk_debut"]), round(v["pk_fin"])]
            v["retouches"].append(f"{r['action']} : {quoi} ({e['confiance']})")
        out["bilan"]["appliquees"].append(e)

    def rate(r, pourquoi):
        out["bilan"]["non_appliquees"].append({"action": r["action"], "pk_m": r.get("pk_m", r.get("pk_debut")),
                                               "pourquoi": pourquoi})
        print(f"attention : retouche {r['action']} au PK {r.get('pk_m', r.get('pk_debut'))} non appliquée : {pourquoi}")

    supprimer = set()
    for r in cfg["retouches"]:
        a = r["action"]
        if a == "ajouter_virage":
            continue
        if a == "danger":
            cat = r["categorie"]
            if cat in DANGERS_EXPRIMABLES and isinstance(r["pk_m"], (int, float)):
                i = trouver(float(r["pk_m"]), None)
                if i is None:
                    rate(r, "aucun virage pour porter le modificateur")
                    continue
                m = DANGERS_EXPRIMABLES[cat]
                if m not in vir[i]["modificateurs"]:
                    vir[i]["modificateurs"].append(m)
                trace(r, f"{m} ({r['libelle']})", vir[i])
            else:
                out["dangers_non_exprimables"].append({
                    "pk_m": r["pk_m"], "categorie": cat, "libelle": r["libelle"], "source": r.get("source", src),
                    "confiance": r.get("confiance"),
                    "raison": "pas de jeton correspondant que leur constructeur sache produire"})
            continue
        i = trouver(float(r["pk_m"]), r.get("sens"))
        if i is None:
            rate(r, f"aucun virage {r.get('sens', '')} à ± {tol:g} m")
            continue
        v = vir[i]
        if a == "supprimer":
            supprimer.add(i)
            trace(r, f"note supprimée ({v['sens']} {v['severite']})", v)
        elif a == "forcer":
            if "severite" in r:
                if r["severite"] not in ANGLE_DR2:
                    rate(r, f"sévérité inconnue {r['severite']}")
                    continue
                trace(r, f"sévérité {v['severite']} -> {r['severite']}", v)
                v["severite"] = r["severite"]
            if r.get("libelle"):
                v["libelle"] = r["libelle"]
        elif a == "modificateur":
            if r["modificateur"] not in DANGERS_EXPRIMABLES.values():
                rate(r, f"modificateur {r['modificateur']} non exprimable")
                continue
            if r["modificateur"] not in v["modificateurs"]:
                v["modificateurs"].append(r["modificateur"])
            trace(r, r["modificateur"], v)
        elif a == "annoter":
            v["libelle"] = "; ".join(x for x in (v["libelle"], r["libelle"]) if x)
            trace(r, f"libellé « {r['libelle']} » (non dit par le jeu)", v)
        else:
            rate(r, f"action inconnue {a}")
    supprimes = [vir[i] for i in sorted(supprimer)]
    vir = [v for i, v in enumerate(vir) if i not in supprimer]
    for r in cfg["retouches"]:
        if r["action"] != "ajouter_virage":
            continue
        a, b = float(r["pk_debut"]), float(r["pk_fin"])
        deja = [v for v in vir if v["sens"] == r["sens"] and v["pk_debut"] <= b + tol and v["pk_fin"] >= a - tol]
        if deja:
            # l'axe a bougé et le calcul trouve désormais ce virage : on le garde, avec la sévérité et le libellé voulus
            v = deja[0]
            trace(r, f"virage déjà calculé : sévérité {v['severite']} -> {r['severite']}", v)
            v["severite"], v["libelle"] = r["severite"], r.get("libelle") or v["libelle"]
            continue
        if r["severite"] not in ANGLE_DR2 or not (0 <= a < b <= pk_fin):
            rate(r, "sévérité ou PK invalides")
            continue
        v = {"pk_debut": a, "pk_fin": b, "sens": r["sens"], "virage_deg": None, "rayon_min_m": None,
             "severite": r["severite"], "severite_calculee": None, "modificateurs": [], "retouches": [],
             "libelle": r.get("libelle")}
        vir.append(v)
        trace(r, f"virage ajouté ({r['sens']} {r['severite']})", v)
    vir.sort(key=lambda v: v["pk_debut"])
    out["bilan"]["notes_supprimees"] = [{"pk_virage": [round(v["pk_debut"]), round(v["pk_fin"])], "sens": v["sens"],
                                         "severite_calculee": v["severite_calculee"]} for v in supprimes]
    return vir, out


# --- stage.json --------------------------------------------------------------------------
def construire(ch, ref, prims, deck, obst, rap_sol):
    pk = ch["pk"]
    A, G, D = vers_ir(ch["A"], ref), vers_ir(ch["G"], ref), vers_ir(ch["D"], ref)
    dist = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(A, axis=0), axis=1))])   # 3D, au mètre
    es = np.flatnonzero(ch["zone"] == "es")
    i_dep, i_arr = int(np.argmin(np.abs(pk))), int(es[-1])

    off = {r["id"]: r for r in csv.DictReader(open(OUT / "points_officiels_recales.csv", encoding="utf-8"))}
    spl = {}
    for nom in SPLITS + ("STOP",):
        r = off[nom]
        spl[nom] = point_sur_axe(ch, float(r["x_l93"]), float(r["y_l93"]), float(r["pk_mesure_m"]))
    i_stop = spl.pop("STOP")[0]

    # portes tous les PAS_PORTES m ; la première et la dernière à 5 m des bouts du ruban (comme la porte 0 de DR2,
    # vers 5 m) pour que chacune ait du sol physique tout autour
    i_a, i_b = int(np.searchsorted(pk, pk[0] + 5)), int(np.searchsorted(pk, pk[-1] - 5))
    garde = {i for i in range(i_a, i_b + 1) if abs(pk[i] / PAS_PORTES - round(pk[i] / PAS_PORTES)) < 1e-6}
    garde |= {i_a, i_b, i_dep, i_arr, i_stop} | {v[0] for v in spl.values()}
    idx = portes_adaptees(sorted(garde), [A, G, D], dist)
    g_of_row = {int(i): k for k, i in enumerate(idx)}
    cen, gl, gr, gdist = A[idx], G[idx], D[idx], dist[idx]

    gd_at_pk = lambda p: float(np.interp(p, pk, dist))                                         # noqa: E731
    pos_at_pk = lambda p: np.array([np.interp(p, pk, A[:, k]) for k in range(3)])               # noqa: E731

    def fwd(g):
        a, b = cen[max(g - 1, 0)], cen[min(g + 1, len(cen) - 1)]
        v = b - a
        return v / np.linalg.norm(v)

    def ligne(type_, sid, row):
        g = g_of_row[row]
        return {"type": type_, "split_id": sid, "gate": g, "distance": round(float(gdist[g]), 3),
                "distance_from_start": round(float(gdist[g] - dist[i_dep]), 2), "position": r3(cen[g]),
                "forward": r3(fwd(g), 5), "left": r3(gl[g]), "right": r3(gr[g])}

    timing = [ligne("start", 0, i_dep)]
    for k, nom in enumerate(SPLITS, start=1):
        timing.append(ligne("time", k, spl[nom][0]))
    timing.append(ligne("finish", len(SPLITS) + 1, i_arr))

    gst = g_of_row[i_stop]
    f = fwd(gst)
    stop = {"type": "VehicleBox", "name": "EndSequenceTriggerBox_point_stop", "position": r3(cen[gst]),
            "forward": r3(f, 5), "size_whl": [round(float(ch["largeur"][i_stop]) + 4, 2), 4.0, 20.0]}

    vir_calc = virages(ch, 0.0, pk[i_arr])
    vir, retouches = appliquer_retouches(vir_calc, charger_retouches(), pk[i_arr])
    toks = notes(ch, vir, gd_at_pk, pos_at_pk, pk[i_arr], float(dist[i_dep]))

    allp = np.vstack([p for p, _ in prims.values()])
    ntri = {c: int(len(t)) for c, (_, t) in prims.items()}
    lon0, lat0 = wgs(ref["x0"], ref["y0"])
    largeur = np.linalg.norm(gr - gl, axis=1)
    deck_rows = {int(i) for i in np.flatnonzero(deck)}

    stage = {
        "schema": "acrxs/stage-ir", "version": 2,
        "id": STAGE_ID, "name": NOM,
        "location": {"id": "grand_caunet", "country": "france",
                     "name": "Le Grand Caunet, Bouches-du-Rhône, France", "archive": None, "route_index": 0},
        "length_m": round(float(dist[i_arr] - dist[i_dep]), 2),
        "total_distance_m": round(float(gdist[-1]), 2),
        "track_type": "point_to_point", "direction": "forwards",
        "coordinates": {
            "frame": "grand_caunet_local_l93", "units": "metres", "up": "+Y",
            "handedness": "right-handed (X est, Y haut, Z sud ; déterminant +1 depuis Lambert-93 est/nord/haut)",
            "origin": {"lambert93_x_m": ref["x0"], "lambert93_y_m": ref["y0"], "lon": round(lon0, 8),
                       "lat": round(lat0, 8), "description": "axe de la chaussée au PK 0 (ligne de départ)"},
            "from_lambert93": "X = x_L93 - x0 ; Y = altitude NGF-IGN69 ; Z = -(y_L93 - y0)",
            "notes": "Toutes les positions (stage.json, collision.glb) sont dans ce repère. Pour un sens de marche f, "
                     "right = normalize(cross(f, +Y)) donne le bord droit des portes et le sens des notes 'right'. "
                     "Y est l'altitude absolue (et non l'altitude moins celle du départ comme dans modele/). "
                     "Nord Lambert-93, convergence des méridiens d'environ -0,9 degré non corrigée.",
        },
        "centreline": [r3(p) for p in cen],
        "gates": [{"id": k, "distance": round(float(gdist[k]), 3), "crossing": r3(cen[k]), "left": r3(gl[k]),
                   "right": r3(gr[k]), "width": round(float(largeur[k]), 2), "pk_m": round(float(pk[i]), 1)}
                  for k, i in enumerate(idx)],
        "timing": timing,
        "pacenotes": {
            "source": "BROUILLON généré par scripts/09_export_stage_ir.py à partir de la courbure de l'axe précis "
                      "(variation de cap sur 20 m) ; à relire sur vidéo embarquée avant tout usage",
            "status": "brouillon",
            "distance_origin": "start_line",
            "distance_reference": "distance_m = mètres le long de la route depuis la ligne de départ ; "
                                  "gate_distance = même point sur l'échelle gates[].distance",
            "start_gate_distance": round(float(dist[i_dep]), 2),
            "shakedown_cutoff_m": None,
            "finish_call_distance_m": next(t["distance_m"] for t in toks if t["kind"] == "finish"),
            "severity_radii_m": {s: r for s, r in SEUILS},
            "tokens": toks,
            "raw": None,
            # extensions du projet (ignorées par leur constructeur, qui ne lit que `tokens`)
            "virages_calcules": len(vir_calc),
            "retouches": retouches["bilan"],
            "dangers_non_exprimables": retouches["dangers_non_exprimables"],
            "vocabulaire": VOCABULAIRE,
        },
        "triggers": [stop],
        "respawn": {
            "method": "gates",
            "notes": "Pas de données de reprise propres : utiliser les portes (crossing = axe de la chaussée, "
                     "left/right = bords, cap = crossing[i+1] - crossing[i-1]).",
            "median_gate_spacing_m": round(float(np.median(np.diff(gdist))), 2),
            "resetlines": None,
        },
        "collision": {
            "file": "collision.glb",
            "source": "data/processed/chaussee_precise.csv (ruban) + modele/terrain.glb (MNT LiDAR HD 0,5 m)"
                      + (" + modele/annexes_collision.glb (carrefours)" if rap_sol["annexes"]["fichier"] else ""),
            "corridor_m": float(M08.CORRIDOR), "triangles": int(sum(ntri.values())),
            "bounds": {"min": r3(allp.min(0)), "max": r3(allp.max(0))},
            "meshes": [{"mesh": "collision", "gltf_material": c, "dr2_surface": c,
                        "acr_physical_material": CODES[c][0], "acr_asset_path": PM + CODES[c][0],
                        "triangles": ntri[c]} for c in prims],
            "flags": None,
        },
        "surfaces": [{"code": c, "acr_physical_material": CODES[c][0], "triangles": ntri[c], "dr2": None,
                      "description": CODES[c][1]} for c in prims],
        "objects": objets_ir(obst),
        "render": [],
        "validation": {},                     # rempli par la relecture (controle)
        "sources": {
            "axe_et_bords": "data/processed/chaussee_precise.csv (phase 3 : LiDAR HD IGN + BD ORTHO 20 cm, Etalab 2.0)",
            "terrain": "modele/terrain.glb (MNT LiDAR HD IGN 0,5 m)",
            "points_officiels": "data/processed/points_officiels_recales.csv",
            "ouvrages": "data/processed/ouvrages_es.csv",
            "annexes": "data/processed/annexes_revetues.geojson + modele/annexes_collision.glb (étape 12)",
            "obstacles": "modele/ouvrages_collision.glb (étape 11), modele/balisage_collision.glb (étape 12)",
        },
        "export": {
            "generateur": "scripts/09_export_stage_ir.py",
            "modele_source": "08_modele_3d.py (même ruban de route)",
            "temps_intermediaires": {nom: {"pk_m": round(float(pk[spl[nom][0]]), 1),
                                           "ecart_au_point_officiel_m": round(spl[nom][1], 1),
                                           "sur_un_pont": spl[nom][0] in deck_rows} for nom in SPLITS},
            "point_stop_pk_m": round(float(pk[i_stop]), 1),
            "sol": rap_sol["annexes"],
            "obstacles": obst[3],
            "manquant": ["objects : ni arbres, ni rochers, ni panneaux (seuls parapets, murs et balisage)",
                         "objects.render, render/objects.glb (pas de maillage de rendu au format DR2 ; modele/terrain.glb n'en suit pas les attributs)",
                         "ground_bake (pas de dalles DDS BC1)", "textures (pas de DDS)",
                         "pacenotes.raw (pas de données brutes DR2)", "validation.route_map_fit (pas de carte de menu DR2)",
                         "respawn.resetlines", "collision.flags"],
        },
    }
    return stage, vir


# --- relecture (indépendante de l'écriture) -------------------------------------------
def lire_glb(path):
    """Relecture brute : {matériau: (positions, triangles)}."""
    b = Path(path).read_bytes()
    assert b[:4] == b"glTF", "pas un glb"
    n = int(np.frombuffer(b, "<u4", 1, 12)[0])
    gl = json.loads(b[20:20 + n])
    off = 20 + n + 8
    out = {}
    for prim in gl["meshes"][0]["primitives"]:
        def arr(i, dt, k):
            a = gl["accessors"][i]
            v = gl["bufferViews"][a["bufferView"]]
            return np.frombuffer(b, dt, a["count"] * k, off + v.get("byteOffset", 0)).reshape(-1, k)
        out[gl["materials"][prim["material"]]["name"]] = (arr(prim["attributes"]["POSITION"], "<f4", 3).astype(np.float64),
                                                          arr(prim["indices"], "<u4", 1).reshape(-1, 3))
        assert set(prim["attributes"]) == {"POSITION"}, "attributs en trop"
    return gl, out


class Sol:
    """Hauteur du sol physique (surface la plus haute) sous des points en plan, par grille de 4 m."""
    C = 4.0

    def __init__(self, prims):
        self.V = np.vstack([p[t] for p, t in prims.values()])          # (T, 3, 3)
        self.codes = np.concatenate([[c] * len(t) for c, (_, t) in prims.items()])
        lo = np.floor(self.V[:, :, [0, 2]].min(1) / self.C).astype(np.int64)
        hi = np.floor(self.V[:, :, [0, 2]].max(1) / self.C).astype(np.int64)
        keys, ids = [], []
        for dx in range(int((hi - lo)[:, 0].max()) + 1):
            for dz in range(int((hi - lo)[:, 1].max()) + 1):
                m = (lo[:, 0] + dx <= hi[:, 0]) & (lo[:, 1] + dz <= hi[:, 1])
                keys.append((lo[m, 0] + dx) * 1_000_003 + (lo[m, 1] + dz))
                ids.append(np.flatnonzero(m))
        keys, ids = np.concatenate(keys), np.concatenate(ids)
        o = np.argsort(keys, kind="stable")
        self.keys, self.ids = keys[o], ids[o]

    def h(self, x, z):
        return self.top(x, z)[0]

    def code(self, x, z):
        return self.top(x, z)[1]

    def top(self, x, z):
        k = int(math.floor(x / self.C)) * 1_000_003 + int(math.floor(z / self.C))
        a, b = np.searchsorted(self.keys, [k, k + 1])
        T = self.V[self.ids[a:b]]
        if not len(T):
            return None, None
        p0, p1, p2 = T[:, 0], T[:, 1], T[:, 2]
        d = (p1[:, 2] - p2[:, 2]) * (p0[:, 0] - p2[:, 0]) + (p2[:, 0] - p1[:, 0]) * (p0[:, 2] - p2[:, 2])
        ok = np.abs(d) > 1e-12
        d = np.where(ok, d, 1)
        w0 = ((p1[:, 2] - p2[:, 2]) * (x - p2[:, 0]) + (p2[:, 0] - p1[:, 0]) * (z - p2[:, 2])) / d
        w1 = ((p2[:, 2] - p0[:, 2]) * (x - p2[:, 0]) + (p0[:, 0] - p2[:, 0]) * (z - p2[:, 2])) / d
        w2 = 1 - w0 - w1
        e = -1e-9
        hit = ok & (w0 >= e) & (w1 >= e) & (w2 >= e)
        if not hit.any():
            return None, None
        y = np.where(hit, w0 * p0[:, 1] + w1 * p1[:, 1] + w2 * p2[:, 1], -np.inf)
        i = int(np.argmax(y))
        return float(y[i]), str(self.codes[self.ids[a:b]][i])


def controle(dossier, deck_pk):
    st = json.loads((dossier / "stage.json").read_text(encoding="utf-8"))
    gl, prims = lire_glb(dossier / "collision.glb")
    r, err = {}, []

    def need(cond, msg):
        if not cond:
            err.append(msg)

    # schéma : clés et types (docs/stage-ir.md, plus ce que lit leur constructeur StageBuild.Ir.Load)
    types = {"schema": str, "version": int, "id": str, "name": str, "location": dict, "length_m": float,
             "total_distance_m": float, "track_type": str, "direction": str, "coordinates": dict, "centreline": list,
             "gates": list, "timing": list, "pacenotes": dict, "triggers": list, "respawn": dict, "collision": dict,
             "surfaces": list, "render": list, "validation": dict, "sources": dict}
    for k, t in types.items():
        need(k in st and isinstance(st[k], t), f"clé {k} absente ou de type inattendu")
    need("objects" in st and (st["objects"] is None or isinstance(st["objects"], dict)), "objects : objet ou null")
    need(len(st["gates"]) == len(st["centreline"]), "une porte par point d'axe")
    for g in st["gates"]:
        need(set(g) >= {"id", "distance", "crossing", "left", "right", "width"}, "porte incomplète")
    need(sum(t["type"] == "start" for t in st["timing"]) == 1 and sum(t["type"] == "finish" for t in st["timing"]) == 1,
         "un départ et une arrivée")
    for t in st["pacenotes"]["tokens"]:
        need(isinstance(t["call"], int) and isinstance(t["subcall"], int) and isinstance(t["gate_distance"], float),
             "jeton : call/subcall/gate_distance")
        need(t["kind"] in ("corner", "distance", "finish"), "jeton : kind")
        if t["kind"] == "corner":
            need(t["direction"] in ("left", "right") and t["severity"] in ANGLE_DR2 and isinstance(t["angle"], int),
                 "jeton virage")
            need(all(m in DANGERS_EXPRIMABLES.values() for m in t["modifiers"]), "modificateur hors vocabulaire")
    gls = {m["name"] for m in gl["materials"]}
    need(gls == {m["gltf_material"] for m in st["collision"]["meshes"]}, "matériaux glb = collision.meshes")
    need(len(gl["nodes"]) == 1 and gl["nodes"][0]["name"] == "collision" and len(gl["meshes"]) == 1, "un nœud collision")

    cen = np.array(st["centreline"])
    L, R = np.array([g["left"] for g in st["gates"]]), np.array([g["right"] for g in st["gates"]])
    gd = np.array([g["distance"] for g in st["gates"]])
    gpk = np.array([g["pk_m"] for g in st["gates"]])
    # repère : déterminant du passage Lambert-93 (est, nord, haut) -> IR (X, Y, Z)
    M = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)   # lignes : X = est, Y = haut, Z = -nord
    r["repere"] = {"determinant": float(np.linalg.det(M)),
                   "y_axe_min_max_m": [round(float(cen[:, 1].min()), 2), round(float(cen[:, 1].max()), 2)]}
    need(abs(np.linalg.det(M) - 1) < 1e-12, "repère indirect")
    # distances croissantes, longueur compétitive
    dd = np.diff(gd)
    r["distances"] = {"croissantes": bool((dd > 0).all()), "pas_min_m": round(float(dd.min()), 2),
                      "pas_median_m": round(float(np.median(dd)), 2), "pas_max_m": round(float(dd.max()), 2)}
    need((dd > 0).all(), "distances non croissantes")
    tm = {t["type"]: t for t in st["timing"]}
    lc = gd[tm["finish"]["gate"]] - gd[tm["start"]["gate"]]
    r["longueur_competitive"] = {"length_m": st["length_m"], "distance_finish_moins_start": round(float(lc), 2),
                                 "polyligne_portes_3d_m": round(float(np.linalg.norm(np.diff(
                                     cen[tm["start"]["gate"]:tm["finish"]["gate"] + 1], axis=0), axis=1).sum()), 2),
                                 "pk_arrivee_plan_m": float(gpk[tm["finish"]["gate"]])}
    need(abs(lc - st["length_m"]) < 0.02, "length_m != distance(finish) - distance(start)")
    need(all(abs(t["distance_from_start"] - (t["distance"] - gd[tm["start"]["gate"]])) < 0.02 for t in st["timing"]),
         "distance_from_start")
    # gauche / droite : right = cross(f, +Y)
    f = np.zeros_like(cen)
    f[1:-1] = cen[2:] - cen[:-2]
    f[0], f[-1] = cen[1] - cen[0], cen[-1] - cen[-2]
    rv = np.cross(f, [0.0, 1.0, 0.0])
    rv /= np.linalg.norm(rv, axis=1, keepdims=True)
    sr, sl = ((R - cen) * rv).sum(1), ((L - cen) * rv).sum(1)
    r["gauche_droite"] = {"portes": len(cen), "droite_du_cote_cross_f_Y": int((sr > 0).sum()),
                          "gauche_du_cote_oppose": int((sl < 0).sum()),
                          "demi_largeur_droite_min_m": round(float(sr.min()), 2),
                          "demi_largeur_gauche_min_m": round(float(-sl.max()), 2),
                          "width_coherente": bool(all(abs(g["width"] - np.linalg.norm(np.array(g["right"]) -
                                                                                        np.array(g["left"]))) < 0.01
                                                      for g in st["gates"]))}
    need((sr > 0).all() and (sl < 0).all(), "gauche/droite incohérents avec le sens de marche")
    # sens des notes : un virage 'right' tourne vers cross(f, +Y)
    ok_sens, n_v = 0, 0
    for t in st["pacenotes"]["tokens"]:
        if t["kind"] != "corner":
            continue
        a, b = t["brouillon"]["pk_virage"]
        i0, i1 = np.searchsorted(gpk, a - 10), min(np.searchsorted(gpk, b + 10), len(gpk) - 2)
        f0, f1 = cen[i0 + 1] - cen[i0], cen[i1 + 1] - cen[i1]
        droite = float(np.dot(f1, np.cross(f0, [0, 1, 0]))) > 0
        n_v += 1
        ok_sens += droite == (t["direction"] == "right")
    r["notes_sens_vs_geometrie"] = {"virages": n_v, "coherents": ok_sens}
    need(ok_sens == n_v, "sens des notes incohérent")
    gdt = [t["gate_distance"] for t in st["pacenotes"]["tokens"]]
    need(all(b >= a for a, b in zip(gdt, gdt[1:])), "notes non ordonnées")

    # sol physique sous les portes, entre les portes et aux bords
    sol = Sol(prims)
    on_deck = np.isin(np.round(gpk), deck_pk)

    def ecarts(pts, mask=None):
        h = [sol.h(p[0], p[2]) for p in pts]
        miss = sum(v is None for v in h)
        dy = np.array([abs(v - p[1]) for v, p in zip(h, pts) if v is not None])
        return miss, dy

    miss, dy = ecarts(cen)
    m2, dy2 = ecarts(cen[~on_deck])
    r["sol_sous_portes"] = {"portes": len(cen), "sans_sol": miss, "max_abs_dy_m": round(float(dy.max()), 3),
                            "moyenne_abs_dy_m": round(float(dy.mean()), 4),
                            "hors_ponts": {"portes": int((~on_deck).sum()), "max_abs_dy_m": round(float(dy2.max()), 3)}}
    need(miss == 0 and dy.max() <= 0.10, "sol physique absent ou décalé sous une porte")
    pts = []
    for i in range(len(cen) - 1):
        k = max(1, int(math.ceil(np.linalg.norm(cen[i + 1] - cen[i]))))
        pts += [cen[i] + (cen[i + 1] - cen[i]) * (j / k) for j in range(k)]
    miss_l, dyl = ecarts(np.array(pts))
    r["sol_le_long_de_l_axe_tous_les_m"] = {"echantillons": len(pts), "sans_sol": miss_l,
                                             "max_abs_dy_a_la_corde_m": round(float(dyl.max()), 3)}
    need(miss_l == 0, "trou dans le sol le long de l'axe")
    E = np.vstack([cen + 0.95 * (L - cen), cen + 0.95 * (R - cen)])
    miss_e, dye = ecarts(E)
    r["sol_aux_bords_95pct"] = {"points": len(E), "sans_sol": miss_e, "max_abs_dy_m": round(float(dye.max()), 3),
                                "p99_abs_dy_m": round(float(np.percentile(dye, 99)), 3)}
    # au-delà de la chaussée : le sol continue (accotement / terrain) à 5 m des bords
    def dehors(B):
        u = (B - cen)
        u[:, 1] = 0
        u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-9)
        return B + 5 * u
    miss_o, _ = ecarts(np.vstack([dehors(L), dehors(R)]))
    r["sol_5m_au_dela_des_bords"] = {"points": 2 * len(cen), "sans_sol": miss_o}

    def juste_dehors(B, k=0.3):
        u = (B - cen)
        u[:, 1] = 0
        u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-9)
        return B + k * u
    miss_j, _ = ecarts(np.vstack([juste_dehors(L), juste_dehors(R)]))
    r["sol_30cm_au_dela_des_bords"] = {"points": 2 * len(cen), "sans_sol": miss_j}
    need(miss_o == 0 and miss_j == 0, "trou dans le sol au bord de la chaussée")
    # orientation des triangles
    up = tot = 0
    for p, t in prims.values():
        nrm = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])
        up += int((nrm[:, 1] > 0).sum())
        tot += len(t)
    r["collision"] = {"triangles": tot, "par_code": {c: int(len(t)) for c, (_, t) in prims.items()},
                      "ccw_vu_du_dessus": round(up / tot, 4),
                      "triangles_annonces_dans_stage_json": st["collision"]["triangles"]}
    need(tot == st["collision"]["triangles"], "nombre de triangles")
    r["obstacles"] = controle_obstacles(dossier, st, sol, need) if st["objects"] else None
    r["annexes"] = controle_annexes(st, sol, prims, need)
    r["erreurs"] = err
    return r, {"ground_height_at_gates": {"checked": len(cen), "missing": miss, "max_abs_dy_m": round(float(dy.max()), 3),
                                          "mean_abs_dy_m": round(float(dy.mean()), 3)},
               "collision_ccw_from_above": round(up / tot, 4), "route_map_fit": None, "object_shapes_vs_render": None}


class Couloir:
    """Le corridor de leur constructeur (Respawn.cs, RoadCorridor.Query) : distance au segment d'axe entre deux
    portes moins la demi-largeur interpolée du côté du point ; négatif = sur la chaussée."""

    def __init__(self, st):
        self.c = np.array(st["centreline"])[:, [0, 2]]
        self.z = np.array(st["centreline"])[:, 1]
        L = np.array([g["left"] for g in st["gates"]])[:, [0, 2]]
        R = np.array([g["right"] for g in st["gates"]])[:, [0, 2]]
        self.lw, self.rw = np.linalg.norm(L - self.c, axis=1), np.linalg.norm(R - self.c, axis=1)
        e = self.c[1:] - self.c[:-1]
        cl = e[:, 0] * (L[:-1, 1] - self.c[:-1, 1]) - e[:, 1] * (L[:-1, 0] - self.c[:-1, 0])
        self.sg = np.sign(cl)
        self.tree = cKDTree((self.c[1:] + self.c[:-1]) / 2)

    def clearance(self, x, z):
        ids = np.array(self.tree.query_ball_point([x, z], 40.0), dtype=int)
        if not len(ids):
            return np.inf, 0.0
        a, b = self.c[ids], self.c[ids + 1]
        e = b - a
        l2 = (e ** 2).sum(1)
        u = np.clip(((x - a[:, 0]) * e[:, 0] + (z - a[:, 1]) * e[:, 1]) / np.maximum(l2, 1e-9), 0, 1)
        p = a + u[:, None] * e
        gauche = np.sign(e[:, 0] * (z - p[:, 1]) - e[:, 1] * (x - p[:, 0])) == self.sg[ids]
        hw = np.where(gauche, self.lw[ids] + u * (self.lw[ids + 1] - self.lw[ids]),
                      self.rw[ids] + u * (self.rw[ids + 1] - self.rw[ids]))
        d = np.hypot(x - p[:, 0], z - p[:, 1]) - hw
        k = int(np.argmin(d))
        return float(d[k]), float(self.z[ids[k]] + u[k] * (self.z[ids[k] + 1] - self.z[ids[k]]))


def trs_numerics(t):
    """Matrice 4x4 (convention System.Numerics, vecteurs lignes) comme ObjectColliders.Trs : S * R(q) * T."""
    if t is None:
        return np.eye(4)
    if t.get("matrix"):
        return np.array(t["matrix"], float).reshape(4, 4)
    x, y, z, w = (np.array(t["rotation"], float) / np.linalg.norm(t["rotation"])) if t.get("rotation") else (0, 0, 0, 1)
    Rm = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w)],
                   [2 * (x * y - z * w), 1 - 2 * (z * z + x * x), 2 * (y * z + x * w)],
                   [2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (y * y + x * x)]])
    M = np.eye(4)
    M[:3, :3] = np.diag(t["scale"] if t.get("scale") else [1, 1, 1]) @ Rm
    M[3, :3] = t["position"] if t.get("position") else [0, 0, 0]
    return M


def controle_obstacles(dossier, st, sol, need):
    """Relit `objects` comme ObjectColliders.Build : gabarits, formes, paroi, statique ; reconstruit chaque forme
    dans le monde, la compare aux volumes source, et vérifie qu'aucune n'entre de plus de 0,3 m dans la
    chaussée à hauteur de voiture (leur constructeur la supprimerait)."""
    ob = st["objects"]
    for k in ("templates", "instances", "collision"):
        need(k in ob, f"objects.{k} absent")
    murs = set(re.findall(r'"(PM_Wall\w+)"', CATALOGUE))
    formes, parois, hors_cat = {}, {}, set()
    couloir = Couloir(st)
    intrus, max_pen, coins = 0, 0.0, []
    for inst in ob["instances"]:
        need(isinstance(inst["id"], str) and inst["template"] in ob["templates"], "instance sans gabarit")
        for body in ob["templates"][inst["template"]]["bodies"]:
            need(body.get("static") is True, "corps non statique (ignoré par leur constructeur)")
            for sh in body["shapes"]:
                need(sh["kind"] in ("box", "cylinder") and sh.get("acr_wall", "none") != "none", "forme ou paroi")
                need(all(isinstance(v, float) for v in sh["dimensions"].values()), "dimensions non réelles")
                hors_cat |= {sh["acr_wall"]} - murs
                o, A, L = forme_monde(sh, inst)
                formes[sh["kind"]] = formes.get(sh["kind"], 0) + 1
                parois[sh["acr_wall"]] = parois.get(sh["acr_wall"], 0) + 1
                grille = np.array([[i, j, k] for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)], float)
                pts = o + (grille * L / 2) @ A.T
                coins.append((o, A, L, pts))
                pen = 0.0
                for q in pts:                                    # règle de ObjectColliders / RoadProbe.Depth
                    c, zc = couloir.clearance(q[0], q[2])
                    if c >= 0 or not (zc - 1.0 < q[1] < zc + 2.5) or sol.code(q[0], q[2]) != "TSD+":
                        continue
                    pen = max(pen, -c)
                max_pen = max(max_pen, pen)
                intrus += pen > 0.3
    need(intrus == 0, f"{intrus} obstacles entrent de plus de 0,3 m dans la chaussée")
    need(not hors_cat, f"parois absentes du catalogue du jeu : {sorted(hors_cat)}")
    # forme reconstruite contre volume écrit (objects_collision.glb) : même enveloppe à 1 cm près
    gl, vol = lire_glb(dossier / "objects_collision.glb")
    P = np.vstack([p for p, _ in vol.values()])
    C = np.vstack([c[3] for c in coins])
    lo_c, hi_c, lo_v, hi_v = C.min(0), C.max(0), P.min(0), P.max(0)
    need(np.allclose(lo_c, lo_v, atol=0.01) and np.allclose(hi_c, hi_v, atol=0.01), "formes et objects_collision.glb diffèrent")
    # contre les volumes source du modèle : chaque sommet source dans au moins une forme reconstruite (+2 cm)
    ecart_src = None
    try:
        ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
        src = []
        for nom_f in SOURCES_OBSTACLES:
            if (MOD / nom_f).exists():
                src += [modele_vers_ir(p, ref) for _, mat, p, _ in lire_modele(MOD / nom_f) if mat in OBSTACLES
                        and OBSTACLES[mat][1] == "box"]
        if src:
            S = np.vstack(src)
            tree = cKDTree(np.array([c[0] for c in coins]))
            ret = st["export"]["obstacles"].get("retires_sur_la_chaussee", [])
            pire, hors = 0.0, 0
            for q in S:
                best = np.inf
                for i in tree.query(q, k=min(8, len(coins)))[1]:
                    o, A, L, _ = coins[i]
                    best = min(best, float((np.abs(A.T @ (q - o)) - L / 2).max()))
                if best > 0.02 and any(np.linalg.norm(q - np.array(x["centre"])) <= x["demi_diagonale_m"] + 0.02 for x in ret):
                    continue                                     # sommet d'un pavé retiré (listé dans stage.json)
                hors += best > 0.02
                pire = max(pire, best)
            ecart_src = round(float(pire), 3)
            need(hors == 0, f"{hors} sommets source hors des pavés exportés (jusqu'à {pire:.3f} m)")
    except FileNotFoundError:
        pass
    return {"instances": len(ob["instances"]), "gabarits": len(ob["templates"]), "formes": formes, "parois": parois,
            "parois_absentes_du_catalogue": sorted(hors_cat),
            "penetration_max_dans_la_chaussee_m": round(max_pen, 3), "intrusions_plus_de_30_cm": intrus,
            "sommets_source_hors_paves_max_m": ecart_src,
            "retires_sur_la_chaussee": len(st["export"]["obstacles"].get("retires_sur_la_chaussee", [])),
            "objects_collision_triangles": int(sum(len(t) for _, t in vol.values()))}


def controle_annexes(st, sol, prims, need):
    """Sol des carrefours : sous chaque surface annexe, le sol le plus haut est l'annexe (TSD+ ou DBK+)."""
    if "annexes" not in st["collision"]["source"]:
        return None
    ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    gj = json.loads((OUT / "annexes_revetues.geojson").read_text(encoding="utf-8"))
    n = trous = dessus = 0
    bosse = 0.0
    codes = {}
    sans_terrain = Sol({c: v for c, v in prims.items() if c != "GRS+"})
    terrain = Sol({"GRS+": prims["GRS+"]})
    rng = np.random.default_rng(3)
    for f in gj["features"]:
        if f["geometry"]["type"] != "Polygon":
            continue
        g = shapely.transform(geo_shape(f["geometry"]), lambda c: np.column_stack(TO_L93.transform(c[:, 0], c[:, 1])))
        g = g.buffer(-0.3)
        if g.is_empty:
            continue
        x0, y0, x1, y1 = g.bounds
        for _ in range(200):
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            if not g.contains(shapely.Point(x, y)):
                continue
            X, Z = x - ref["x0"], ref["y0"] - y
            c = sol.code(X, Z)
            n += 1
            if c is None:
                trous += 1
            else:
                codes[c] = codes.get(c, 0) + 1
                ha, ht = sans_terrain.h(X, Z), terrain.h(X, Z)
                if c == "GRS+" and ha is not None:
                    bosse = max(bosse, ht - ha)
                dessus += c == "GRS+" and (ha is None or ht - ha > 0.02)
    need(trous == 0, f"{trous} trous dans le sol des carrefours")
    # une bosse de quelques cm n'est pas dangereuse (un trou l'est) : avertissement seulement en dessous de 10 cm
    need(bosse <= 0.10, f"terrain naturel {bosse:.2f} m au-dessus d'une surface annexe")
    return {"points_testes": n, "sans_sol": trous, "code_du_sol_le_plus_haut": codes,
            "terrain_plus_de_2_cm_au_dessus": dessus, "terrain_au_dessus_max_m": round(bosse, 3)}


# --- main ----------------------------------------------------------------------------------
def main():
    ch = charger()
    ref = M08.repere(ch)
    rj = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    if any(abs(rj[k] - ref[k]) > 1e-3 for k in ("x0", "y0", "z0")):
        raise SystemExit("modele/repere.json ne correspond plus à chaussee_precise.csv : relancer 08 (puis 11, 12)")
    deck = M08.tablier(ch, M08.MNT())
    DOSSIER.mkdir(parents=True, exist_ok=True)
    rap_sol = {}
    prims = sol_physique(ch, ref, rap_sol)
    ecrire_glb(DOSSIER / "collision.glb", prims)
    obst = obstacles(ref)
    if obst[2]:
        ecrire_glb(DOSSIER / "objects_collision.glb", obst[2], nom="objects_collision")
    else:
        (DOSSIER / "objects_collision.glb").unlink(missing_ok=True)
    stage, vir = construire(ch, ref, prims, deck, obst, rap_sol)
    if stage["objects"]:
        retirer_sur_chaussee(stage, prims)
        ecrire_glb(DOSSIER / "objects_collision.glb", volumes_retenus(stage, obst), nom="objects_collision")
    path = DOSSIER / "stage.json"
    path.write_text(json.dumps(stage, ensure_ascii=False, indent=1), encoding="utf-8")
    rapport, validation = controle(DOSSIER, np.round(ch["pk"][deck]))
    stage["validation"] = validation
    path.write_text(json.dumps(stage, ensure_ascii=False, indent=1), encoding="utf-8")
    sev = {}
    for v in vir:
        sev[v["severite"]] = sev.get(v["severite"], 0) + 1
    toks = stage["pacenotes"]["tokens"]
    pn = stage["pacenotes"]
    rapport["notes_brouillon"] = {"virages_calcules": pn["virages_calcules"], "virages_annonces": len(vir),
                                  "retouches_appliquees": len(pn["retouches"]["appliquees"]),
                                  "retouches_non_appliquees": pn["retouches"]["non_appliquees"],
                                  "dangers_non_exprimables": len(pn["dangers_non_exprimables"]),
                                  "ne_pas_couper": sum("dont_cut" in t["modifiers"] for t in toks if t["kind"] == "corner"),
                                  "par_severite": sev,
                                  "appels": max(t["call"] for t in toks), "jetons": len(toks),
                                  "avance_lecture_m": AVANCE}
    rapport["fichiers_mo"] = {p.name: round(p.stat().st_size / 1e6, 2) for p in sorted(DOSSIER.iterdir())}
    (EXPORT / "controle_grand_caunet.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=2),
                                                       encoding="utf-8")
    print(json.dumps(rapport, ensure_ascii=False, indent=1))
    if rapport["erreurs"]:
        raise SystemExit("contrôle en échec : " + " ; ".join(rapport["erreurs"]))


if __name__ == "__main__":
    main()
