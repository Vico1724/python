"""Étape 9 - Export au format d'échange « Stage IR » v2 du projet ACR Extra Stages.

Le Stage IR (docs/stage-ir.md du dépôt ACR Extra Stages) est le dossier que leur
constructeur côté ACR (`acr-ref stage-build`) consomme. Il est normalement produit à
partir de DiRT Rally 2.0 ; ici il est produit à partir de nos propres mesures.

Entrées : data/processed/chaussee_precise.csv (axe et bords au mètre), points_officiels_recales.csv,
          ouvrages_es.csv, modele/terrain.glb (étape 8), data/raw/mnt_lidarhd_50cm.tif (repérage des ponts)
Sorties (export/stage_ir/grand_caunet/) :
  stage.json      tout sauf la géométrie : identité, longueurs, repère, axe, portes (tous les ~10 m),
                  chronométrage, zone d'arrêt, reprise en piste, sol physique, surfaces, notes du
                  copilote (BROUILLON généré par la courbure de l'axe), auto-contrôles
  collision.glb   sol physique : un nœud et un maillage « collision », un primitif par code de surface
                  (TSD+ chaussée, DBK+ accotement 0-3 m, GRS+ terrain du couloir), positions seules
export/stage_ir/controle_grand_caunet.json : relecture des fichiers écrits (contrôle indépendant de l'écriture)

Repère de l'IR (le format exige mètres, +Y haut, repère direct, même repère pour tous les fichiers) :
  X = x_L93 - x0 (est), Y = altitude NGF (absolue, pour que les altitudes des menus soient justes),
  Z = -(y_L93 - y0) (sud) ; (x0, y0) = axe au PK 0, comme modele/repere.json (qui, lui, prend Y relatif).
  Pour un sens de marche f, la droite du pilote est cross(f, +Y), comme dans l'IR de DR2.

Ce que l'exporteur ne produit pas (laissé vide ou null comme le prévoit le format) : objets
(`objects` = null), maillages de rendu DR2 (`render` = []), cuisson du sol (`ground_bake` absent),
données brutes DR2 des notes (`pacenotes.raw` = null), recalage sur carte de menu
(`validation.route_map_fit` = null), fichier de reprise DR2 (`respawn.resetlines` = null).
"""
import csv
import importlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acr_geo import OUT, ROOT, wgs  # noqa: E402

M08 = importlib.import_module("08_modele_3d")      # mêmes lecteurs et même ruban de route que le modèle 3D

EXPORT = ROOT / "export" / "stage_ir"
DOSSIER = EXPORT / "grand_caunet"
STAGE_ID = "grand_caunet_rally_01_route_0"         # forme <lieu>_rally_<nn>_route_<n> exigée par leurs scripts
NOM = "Le Grand Caunet"
PAS_PORTES = 10.0                                  # m
ACCOTEMENT = 3.0                                   # m au-delà du bord de chaussée : code DBK+
CODES = {                                          # code -> (matériau physique ACR, description)
    "TSD+": ("PM_SurfaceTarmacSmooth", "chaussée en enrobé (ruban de route mesuré)"),
    "DBK+": ("PM_SurfaceGravelHard", f"accotement en terre, {ACCOTEMENT:g} m au-delà des bords"),
    "GRS+": ("PM_SurfaceGrass", "terrain naturel du couloir (garrigue, sous-bois)"),
}
PM = "/Game/Data/Gameplay/PhysicalMaterials/"
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
    with open(OUT / "chaussee_precise.csv") as f:
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


# --- sol physique ------------------------------------------------------------------------
def sol_physique(ch, ref):
    """Ruban de route (celui de l'étape 8) + terrain du modèle 3D, sommets fusionnés, Y absolu."""
    route = M08.route(ch, ref)
    rp = route["pos"].astype(np.float64)
    rt = route["idx"].astype(np.int64)
    src = ROOT / "modele" / "terrain.glb"
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
    # accotement : centre du triangle à moins de ACCOTEMENT m (en plan) d'un bord de chaussée
    bords = np.vstack([vers_ir(ch["G"], ref), vers_ir(ch["D"], ref)])[:, [0, 2]]
    c = tp[tt].mean(axis=1)[:, [0, 2]]
    d, _ = cKDTree(bords).query(c)
    acc = d <= ACCOTEMENT
    return {"TSD+": (rp, rt), "DBK+": compact(tp, tt[acc]), "GRS+": compact(tp, tt[~acc])}


def compact(p, t):
    used, inv = np.unique(t, return_inverse=True)
    return p[used], inv.reshape(-1, 3)


def ecrire_glb(path, prims):
    """Un nœud, un maillage « collision », un primitif par code de surface ; POSITION + indices seulement."""
    gl = {"asset": {"version": "2.0", "generator": "acr-grand-caunet 09_export_stage_ir.py"},
          "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"name": "collision", "mesh": 0}],
          "meshes": [{"name": "collision", "primitives": []}], "materials": [], "accessors": [],
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
                           "angle": ANGLE_DR2[v["severite"]], "modifiers": [], "link_code": None,
                           "brouillon": {"pk_virage": [round(v["pk_debut"]), round(v["pk_fin"])],
                                         "virage_deg": v["virage_deg"], "rayon_min_m": v["rayon_min_m"]}})
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


# --- stage.json --------------------------------------------------------------------------
def construire(ch, ref, prims, deck):
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
    idx = np.array(sorted(garde))
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

    vir = virages(ch, 0.0, pk[i_arr])
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
            "source": "data/processed/chaussee_precise.csv (ruban) + modele/terrain.glb (MNT LiDAR HD 0,5 m)",
            "corridor_m": float(M08.CORRIDOR), "triangles": int(sum(ntri.values())),
            "bounds": {"min": r3(allp.min(0)), "max": r3(allp.max(0))},
            "meshes": [{"mesh": "collision", "gltf_material": c, "dr2_surface": c,
                        "acr_physical_material": CODES[c][0], "acr_asset_path": PM + CODES[c][0],
                        "triangles": ntri[c]} for c in prims],
            "flags": None,
        },
        "surfaces": [{"code": c, "acr_physical_material": CODES[c][0], "triangles": ntri[c], "dr2": None,
                      "description": CODES[c][1]} for c in prims],
        "objects": None,
        "render": [],
        "validation": {},                     # rempli par la relecture (controle)
        "sources": {
            "axe_et_bords": "data/processed/chaussee_precise.csv (phase 3 : LiDAR HD IGN + BD ORTHO 20 cm, Etalab 2.0)",
            "terrain": "modele/terrain.glb (MNT LiDAR HD IGN 0,5 m)",
            "points_officiels": "data/processed/points_officiels_recales.csv",
            "ouvrages": "data/processed/ouvrages_es.csv",
        },
        "export": {
            "generateur": "scripts/09_export_stage_ir.py",
            "modele_source": "08_modele_3d.py (même ruban de route)",
            "temps_intermediaires": {nom: {"pk_m": round(float(pk[spl[nom][0]]), 1),
                                           "ecart_au_point_officiel_m": round(spl[nom][1], 1),
                                           "sur_un_pont": spl[nom][0] in deck_rows} for nom in SPLITS},
            "point_stop_pk_m": round(float(pk[i_stop]), 1),
            "manquant": ["objects (aucun objet ni obstacle : arbres, murets, parapets)",
                         "render (pas de maillage de rendu au format DR2 ; modele/terrain.glb n'en suit pas les attributs)",
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
        k = int(math.floor(x / self.C)) * 1_000_003 + int(math.floor(z / self.C))
        a, b = np.searchsorted(self.keys, [k, k + 1])
        T = self.V[self.ids[a:b]]
        if not len(T):
            return None
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
            return None
        return float((w0 * p0[:, 1] + w1 * p1[:, 1] + w2 * p2[:, 1])[hit].max())


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
    need("objects" in st and st["objects"] is None, "objects doit être null")
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
    r["erreurs"] = err
    return r, {"ground_height_at_gates": {"checked": len(cen), "missing": miss, "max_abs_dy_m": round(float(dy.max()), 3),
                                          "mean_abs_dy_m": round(float(dy.mean()), 3)},
               "collision_ccw_from_above": round(up / tot, 4), "route_map_fit": None, "object_shapes_vs_render": None}


# --- main ----------------------------------------------------------------------------------
def main():
    ch = charger()
    ref = M08.repere(ch)
    deck = M08.tablier(ch, M08.MNT())
    DOSSIER.mkdir(parents=True, exist_ok=True)
    prims = sol_physique(ch, ref)
    ecrire_glb(DOSSIER / "collision.glb", prims)
    stage, vir = construire(ch, ref, prims, deck)
    path = DOSSIER / "stage.json"
    path.write_text(json.dumps(stage, ensure_ascii=False, indent=1), encoding="utf-8")
    rapport, validation = controle(DOSSIER, np.round(ch["pk"][deck]))
    stage["validation"] = validation
    path.write_text(json.dumps(stage, ensure_ascii=False, indent=1), encoding="utf-8")
    sev = {}
    for v in vir:
        sev[v["severite"]] = sev.get(v["severite"], 0) + 1
    toks = stage["pacenotes"]["tokens"]
    rapport["notes_brouillon"] = {"virages_annonces": len(vir), "par_severite": sev,
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
