"""Étape 8 - Premier modèle 3D neutre (glTF 2.0 binaire) : chaussée et terrain du couloir.

Entrées : data/processed/chaussee_precise.csv (axe et bords au mètre, z compris),
          data/processed/ouvrages_es.csv, data/raw/mnt_lidarhd_50cm.tif, data/raw/ortho_20cm.tif
Sorties (modele/) :
  route.glb     ruban de chaussée (bord gauche, axe, bord droit tous les mètres), UV : u en
                travers 0..1, v = PK / 10 ; matériau gris simple
  terrain.glb   terrain du couloir (130 m de part et d'autre de l'axe) issu du MNT LiDAR,
                maillage plus fin près de la route (1 m jusqu'à 15 m, 2 m jusqu'à 40 m, 4 m
                au-delà), découpé en dalles de 500 m texturées par l'ortho 20 cm (JPEG)
  repere.json   origine et convention d'axes
  apercu/       même chose en léger (2 / 4 / 8 m, textures 512 px), seule version versionnée

Raccord route / terrain : le terrain s'arrête aux bords de la chaussée, dont il reprend
exactement les sommets (mêmes x, y, z) ; sur 2 m au-delà, le MNT est recalé
progressivement sur l'altitude du bord. Sur les ponts (là où le tablier passe à plus de
30 cm au-dessus du MNT), le terrain n'est pas troué : il garde le vallon sous la route.

Repère : mètres, +Y vers le haut, repère direct ; origine = axe au PK 0 (départ) ;
X = est, -Z = nord, Y = altitude - altitude du départ.
"""
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import rasterio
import shapely
from PIL import Image
from rasterio.windows import from_bounds
from scipy.ndimage import distance_transform_edt, map_coordinates
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay, cKDTree
from shapely.geometry import LineString, Point, Polygon

from acr_geo import FIG, OUT, RAW, ROOT, wgs

MOD = ROOT / "modele"
TILE = 500                   # m : dalle de terrain (une texture par dalle)
CORRIDOR = 130.0             # m de part et d'autre de l'axe
BLEND = 2.0                  # m : recalage du terrain sur les bords de chaussée
DECK_GAP = 0.3               # m : au-delà, la route est un tablier au-dessus du MNT
VERSIONS = {                 # (bandes (distance max, pas), texture px, qualité JPEG)
    "complet": ([(15, 1), (40, 2), (CORRIDOR, 4)], 2048, 82),
    "apercu": ([(15, 2), (40, 4), (CORRIDOR, 8)], 512, 80),
}


# --- données -------------------------------------------------------------------
def chaussee():
    with open(OUT / "chaussee_precise.csv") as f:
        rows = list(csv.DictReader(f))
    g = lambda *k: np.array([[float(r[c]) for c in k] for r in rows])   # noqa: E731
    return {"pk": g("pk_m")[:, 0], "A": g("x_axe", "y_axe", "z_axe"), "G": g("x_gauche", "y_gauche", "z_gauche"),
            "D": g("x_droite", "y_droite", "z_droite"), "zone": np.array([r["zone"] for r in rows])}


class MNT:
    def __init__(self):
        with rasterio.open(RAW / "mnt_lidarhd_50cm.tif") as s:
            self.a, self.inv = s.read(1), ~s.transform

    def z(self, x, y):
        c, r = self.inv * (np.asarray(x), np.asarray(y))
        z = map_coordinates(self.a, [np.asarray(r) - 0.5, np.asarray(c) - 0.5], order=1, mode="nearest")
        if (z < -1000).any():
            raise SystemExit("terrain hors de l'emprise du MNT")
        return z


def tablier(ch, mnt):
    """Lignes de la chaussée qui sont un tablier : zone d'ouvrage BD TOPO (± 8 m, PK
    projetés sur le nouvel axe) où la route passe à plus de DECK_GAP au-dessus du MNT."""
    with open(OUT / "axe_bdtopo_l93.csv") as f:
        rows = list(csv.DictReader(f))
    pk_old = np.array([float(r["pk_m"]) for r in rows])
    old = np.array([[float(r["x_l93"]), float(r["y_l93"])] for r in rows])
    line = LineString(ch["A"][:, :2])
    s0 = line.project(Point(ch["A"][np.argmin(np.abs(ch["pk"])), :2]))
    zone = np.zeros(len(ch["pk"]), bool)
    with open(OUT / "ouvrages_es.csv") as f:
        for r in csv.DictReader(f):
            ab = [line.project(Point(np.interp(float(r[k]), pk_old, old[:, 0]), np.interp(float(r[k]), pk_old, old[:, 1])))
                  - s0 for k in ("pk_debut_m", "pk_fin_m")]
            zone |= (ch["pk"] >= min(ab) - 8) & (ch["pk"] <= max(ab) + 8)
    gap = ch["A"][:, 2] - mnt.z(ch["A"][:, 0], ch["A"][:, 1])
    return zone & (gap > DECK_GAP)


def runs(mask):
    d = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1))


# --- repère ----------------------------------------------------------------------
def repere(ch):
    i0 = int(np.argmin(np.abs(ch["pk"])))
    x0, y0, z0 = (float(v) for v in ch["A"][i0])
    lon, lat = wgs(x0, y0)
    return {
        "origine": {"description": "axe de la chaussée au PK 0 (départ de l'ES)",
                    "lambert93_x_m": round(x0, 3), "lambert93_y_m": round(y0, 3),
                    "lon": round(lon, 8), "lat": round(lat, 8), "altitude_m": round(z0, 3),
                    "systeme_altimetrique": "NGF-IGN69 (altitudes du MNT LiDAR HD)"},
        "unites": "mètres",
        "axes": {"X": "est", "Y": "haut (altitude - altitude d'origine)", "Z": "sud (-Z = nord)",
                 "repere": "direct (main droite), convention glTF 2.0 +Y vers le haut"},
        "passage_lambert93_vers_gltf": "X = x_L93 - x0 ; Y = z - z0 ; Z = -(y_L93 - y0)",
        "passage_gltf_vers_lambert93": "x_L93 = X + x0 ; y_L93 = y0 - Z ; z = Y + z0",
        "x0": round(x0, 3), "y0": round(y0, 3), "z0": round(z0, 3),
        "nord": "nord Lambert-93 (convergence des méridiens d'environ -0,9° ici, non corrigée)",
    }


def to_gltf(p, ref):
    """(N,3) Lambert-93 + z -> (N,3) glTF float32."""
    return np.column_stack([p[:, 0] - ref["x0"], p[:, 2] - ref["z0"], -(p[:, 1] - ref["y0"])]).astype(np.float32)


# --- écriture glb ----------------------------------------------------------------
def write_glb(path, meshes):
    """meshes : liste de dict(name, pos, nrm, uv, idx, color | jpeg)."""
    gl = {"asset": {"version": "2.0", "generator": "acr-grand-caunet 08_modele_3d.py"},
          "scene": 0, "scenes": [{"nodes": list(range(len(meshes)))}], "nodes": [], "meshes": [],
          "accessors": [], "bufferViews": [], "materials": [], "buffers": []}
    blob = bytearray()

    def view(data, target=None):
        while len(blob) % 4:
            blob.append(0)
        v = {"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)}
        if target:
            v["target"] = target
        blob.extend(data)
        gl["bufferViews"].append(v)
        return len(gl["bufferViews"]) - 1

    def acc(arr, kind, target, minmax=False):
        ctype = {np.float32: 5126, np.uint32: 5125}[arr.dtype.type]
        a = {"bufferView": view(arr.tobytes(), target), "componentType": ctype, "count": len(arr), "type": kind}
        if minmax:
            a["min"], a["max"] = arr.min(0).tolist(), arr.max(0).tolist()
        gl["accessors"].append(a)
        return len(gl["accessors"]) - 1

    for m in meshes:
        mat = {"name": m["name"], "pbrMetallicRoughness": {"metallicFactor": 0.0, "roughnessFactor": 0.95}}
        if "jpeg" in m:
            gl.setdefault("images", []).append({"bufferView": view(m["jpeg"]), "mimeType": "image/jpeg"})
            gl.setdefault("samplers", [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}])
            gl.setdefault("textures", []).append({"sampler": 0, "source": len(gl["images"]) - 1})
            mat["pbrMetallicRoughness"]["baseColorTexture"] = {"index": len(gl["textures"]) - 1}
        else:
            mat["pbrMetallicRoughness"]["baseColorFactor"] = m["color"]
        gl["materials"].append(mat)
        attrs = {"POSITION": acc(m["pos"], "VEC3", 34962, True), "NORMAL": acc(m["nrm"], "VEC3", 34962),
                 "TEXCOORD_0": acc(m["uv"], "VEC2", 34962)}
        prim = {"attributes": attrs, "indices": acc(m["idx"].ravel().astype(np.uint32), "SCALAR", 34963),
                "material": len(gl["materials"]) - 1, "mode": 4}
        gl["meshes"].append({"name": m["name"], "primitives": [prim]})
        gl["nodes"].append({"name": m["name"], "mesh": len(gl["meshes"]) - 1})
    while len(blob) % 4:
        blob.append(0)
    gl["buffers"].append({"byteLength": len(blob)})
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    with open(path, "wb") as f:
        f.write(b"glTF" + np.array([2, total], "<u4").tobytes())
        f.write(np.array([len(js), 0x4E4F534A], "<u4").tobytes() + js)
        f.write(np.array([len(blob), 0x004E4942], "<u4").tobytes() + bytes(blob))


def read_glb(path):
    """Relit un glb : liste de (nom, positions, normales, uv, indices)."""
    b = Path(path).read_bytes()
    n = int(np.frombuffer(b, "<u4", 1, 12)[0])
    gl = json.loads(b[20:20 + n])
    binoff = 20 + n + 8
    out = []

    def arr(i):
        a = gl["accessors"][i]
        v = gl["bufferViews"][a["bufferView"]]
        dt = {5126: np.float32, 5125: np.uint32}[a["componentType"]]
        k = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[a["type"]]
        return np.frombuffer(b, dt, a["count"] * k, binoff + v["byteOffset"]).reshape(-1, k)

    for m in gl["meshes"]:
        p = m["primitives"][0]
        out.append((m["name"], arr(p["attributes"]["POSITION"]), arr(p["attributes"]["NORMAL"]),
                    arr(p["attributes"]["TEXCOORD_0"]), arr(p["indices"]).reshape(-1, 3)))
    return out


def normales(pos, tri):
    n = np.zeros_like(pos, dtype=np.float64)
    f = np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])
    for k in range(3):
        np.add.at(n, tri[:, k], f)
    return (n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)).astype(np.float32)


# --- route -------------------------------------------------------------------------
def route(ch, ref):
    """Ruban à trois sommets par ligne (gauche, axe, droite), triangles orientés vers le haut."""
    n = len(ch["pk"])
    P = np.stack([ch["G"], ch["A"], ch["D"]], axis=1).reshape(-1, 3)
    pos = to_gltf(P, ref)
    uv = np.column_stack([np.tile([0.0, 0.5, 1.0], n), np.repeat(ch["pk"] / 10.0, 3)]).astype(np.float32)
    i = np.arange(n - 1)[:, None] * 3
    L, A, R = i, i + 1, i + 2
    L2, A2, R2 = L + 3, A + 3, R + 3
    # dans le repère direct, (bord, vers l'axe, vers l'avant) tourne vers le haut
    tri = np.concatenate([np.hstack([L, A, A2]), np.hstack([L, A2, L2]), np.hstack([A, R, R2]),
                          np.hstack([A, R2, A2])]).astype(np.uint32)
    return {"name": "chaussee", "pos": pos, "nrm": normales(pos, tri), "uv": uv, "idx": tri,
            "color": [0.32, 0.32, 0.33, 1.0]}


# --- terrain ---------------------------------------------------------------------
def terrain(ch, ref, deck, mnt, bands, tex_px, quality, ortho):
    axis = ch["A"][:, :2]
    x0, y0 = (np.floor(axis.min(0) - CORRIDOR - 8) // 8 * 8)
    x1, y1 = axis.max(0) + CORRIDOR + 8
    W, H = int(x1 - x0) + 1, int(y1 - y0) + 1
    # distance à l'axe sur une grille de 1 m (nœud (i, j) = point (x0 + j, y0 + i))
    seg = LineString(axis).segmentize(0.4)
    c = np.asarray(seg.coords)
    occ = np.ones((H, W), bool)
    occ[np.rint(c[:, 1] - y0).astype(int), np.rint(c[:, 0] - x0).astype(int)] = False
    dist = distance_transform_edt(occ)
    ii, jj = np.indices((H, W))
    keep = np.zeros((H, W), bool)
    lo = 0.0
    for dmax, step in bands:
        keep |= (dist > lo) & (dist <= dmax) & (ii % step == 0) & (jj % step == 0)
        lo = dmax
    keep |= (dist == 0) & (ii % bands[0][1] == 0) & (jj % bands[0][1] == 0)
    gx, gy = (x0 + jj[keep]).astype(float), (y0 + ii[keep]).astype(float)

    # trou de la chaussée (hors tabliers) : polygones gauche -> droite par plage continue
    holes = []
    for a, b in runs(~deck):
        if b - a >= 1:
            ring = np.vstack([ch["G"][a:b + 1, :2], ch["D"][a:b + 1, :2][::-1]])
            holes.append(shapely.make_valid(Polygon(ring)))
    hole = shapely.union_all(holes)
    shapely.prepare(hole)
    near = hole.buffer(0.5)
    shapely.prepare(near)
    out = ~shapely.contains_xy(near, gx, gy)
    gx, gy = gx[out], gy[out]
    gz = mnt.z(gx, gy)

    # sommets de bord (exactement ceux de la route) et recalage du MNT sur 2 m
    E = np.vstack([ch["G"][~deck], ch["D"][~deck]])
    dz = E[:, 2] - mnt.z(E[:, 0], E[:, 1])
    d, k = cKDTree(E[:, :2]).query(np.column_stack([gx, gy]))
    w = np.clip(1 - d / BLEND, 0, 1)
    gz = gz + w * dz[k]
    P = np.vstack([E, np.column_stack([gx, gy, gz])])

    tri = Delaunay(P[:, :2]).simplices
    cx, cy = P[tri, 0].mean(1), P[tri, 1].mean(1)
    ed = np.max([np.hypot(*(P[tri[:, a], :2] - P[tri[:, b], :2]).T) for a, b in ((0, 1), (1, 2), (2, 0))], axis=0)
    dc = dist[np.clip(np.rint(cy - y0).astype(int), 0, H - 1), np.clip(np.rint(cx - x0).astype(int), 0, W - 1)]
    ok = (dc <= CORRIDOR) & (ed <= 3 * bands[-1][1]) & ~shapely.contains_xy(hole, cx, cy)
    tri = tri[ok]
    # orientation : sens trigonométrique vu du dessus (normale vers le haut)
    v1, v2 = P[tri[:, 1], :2] - P[tri[:, 0], :2], P[tri[:, 2], :2] - P[tri[:, 0], :2]
    neg = v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0] < 0
    tri[neg] = tri[neg][:, [0, 2, 1]]
    pos = to_gltf(P, ref)
    nrm = normales(pos, tri)

    # dalles de 500 m, chacune avec sa texture
    cx, cy = P[tri, 0].mean(1), P[tri, 1].mean(1)
    tkey = (np.floor(cx / TILE).astype(int), np.floor(cy / TILE).astype(int))
    meshes = []
    for tx, ty in sorted(set(zip(*tkey))):
        sel = tri[(tkey[0] == tx) & (tkey[1] == ty)]
        used, inv = np.unique(sel, return_inverse=True)
        bx0, by0 = tx * TILE, ty * TILE
        # emprise réelle de la dalle (les triangles du bord débordent un peu)
        ex0, ey0 = np.floor(P[used, :2].min(0)) - 1
        ex1, ey1 = np.ceil(P[used, :2].max(0)) + 1
        ex0, ey0, ex1, ey1 = min(ex0, bx0), min(ey0, by0), max(ex1, bx0 + TILE), max(ey1, by0 + TILE)
        im = ortho.read(window=from_bounds(ex0, ey0, ex1, ey1, ortho.transform),
                        out_shape=(3, tex_px, tex_px), boundless=True, fill_value=0)
        buf = io.BytesIO()
        Image.fromarray(np.moveaxis(im, 0, 2)).save(buf, "JPEG", quality=quality, optimize=True)
        uv = np.column_stack([(P[used, 0] - ex0) / (ex1 - ex0), (ey1 - P[used, 1]) / (ey1 - ey0)]).astype(np.float32)
        meshes.append({"name": f"terrain_{tx * TILE}_{ty * TILE}", "pos": pos[used], "nrm": nrm[used], "uv": uv,
                       "idx": inv.reshape(-1, 3).astype(np.uint32), "jpeg": buf.getvalue()})
    stats = {"sommets": int(len(P)), "triangles": int(len(tri)), "dalles": len(meshes),
             "sommets_de_bord": int(len(E)), "recalage_bords_mnt_m": {
                 "median_abs": round(float(np.median(np.abs(dz))), 3),
                 "p95_abs": round(float(np.percentile(np.abs(dz), 95)), 3),
                 "max_abs": round(float(np.abs(dz).max()), 2)}}
    return meshes, stats


# --- contrôles ---------------------------------------------------------------------
def controle(dossier, ch, ref, deck):
    """Relit les glb : tailles, bornes, NaN, normales de la route, écart route/terrain aux bords."""
    r = {}
    for name in ("route", "terrain"):
        meshes = read_glb(dossier / f"{name}.glb")
        pos = np.vstack([m[1] for m in meshes])
        nrm = np.vstack([m[2] for m in meshes])
        r[name] = {"taille_mo": round((dossier / f"{name}.glb").stat().st_size / 1e6, 2), "maillages": len(meshes),
                   "sommets": int(len(pos)), "triangles": int(sum(len(m[4]) for m in meshes)),
                   "nan": bool(np.isnan(pos).any() or np.isnan(nrm).any() or any(np.isnan(m[3]).any() for m in meshes)),
                   "bornes_min": np.round(pos.min(0), 1).tolist(), "bornes_max": np.round(pos.max(0), 1).tolist()}
        if name == "route":
            _, p, _, _, t = meshes[0]
            f = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])
            r[name]["triangles_normale_vers_le_haut_pct"] = round(float((f[:, 1] > 0).mean() * 100), 2)
        else:
            tpos = pos
    # écart vertical aux bords : altitude du terrain (sommet le plus proche en plan) - bord de route
    E = to_gltf(np.vstack([ch["G"][~deck], ch["D"][~deck]]), ref)
    d, k = cKDTree(tpos[:, [0, 2]]).query(E[:, [0, 2]])
    shared = d < 0.01
    # bords non partagés : altitude du terrain interpolée linéairement autour du point
    zt = tpos[k, 1].astype(float)
    if (~shared).any():
        zt[~shared] = LinearNDInterpolator(tpos[:, [0, 2]], tpos[:, 1])(E[~shared][:, [0, 2]])
    dz = np.abs(zt - E[:, 1])
    r["ecart_bords_route_terrain_hors_ponts"] = {
        "bords_testes": int(len(E)), "sommets_partages_pct": round(float(shared.mean() * 100), 3),
        "ecart_vertical_max_m": round(float(np.nanmax(dz)), 3),
        "ecart_vertical_p99_m": round(float(np.nanpercentile(dz, 99)), 3)}
    return r


# --- rendus de contrôle ---------------------------------------------------------------
RENDER_HTML = """<!doctype html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#cfd8e0}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script></head><body>
<script type="module">
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const P = new URLSearchParams(location.search);
const W = +P.get('w'), H = +P.get('h');
const r = new THREE.WebGLRenderer({antialias:true, preserveDrawingBuffer:true});
r.setSize(W, H); r.outputColorSpace = THREE.SRGBColorSpace; document.body.appendChild(r.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0xcfd8e0);
scene.add(new THREE.HemisphereLight(0xffffff, 0x445544, 2.2));
const sun = new THREE.DirectionalLight(0xffffff, 1.4); sun.position.set(-300, 600, 400); scene.add(sun);
const cam = new THREE.PerspectiveCamera(+P.get('fov'), W / H, 1, 20000);
cam.position.fromArray(P.get('eye').split(',').map(Number)); cam.lookAt(...P.get('at').split(',').map(Number));
const L = new GLTFLoader(); let n = 0;
for (const f of P.get('files').split(',')) L.load(f, g => { scene.add(g.scene); if (++n == P.get('files').split(',').length) {
  r.render(scene, cam); document.title = 'ok'; } }, undefined, e => { document.title = 'erreur ' + e; });
</script></body></html>"""

RENDER_JS = """const { chromium } = require('playwright');
(async () => {
  const views = JSON.parse(process.argv[2]);
  const b = await chromium.launch({args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']});
  const p = await b.newPage({viewport: {width: 1400, height: 800}});
  for (const v of views) {
    await p.goto(v.url);
    await p.waitForFunction(() => document.title !== '', null, {timeout: 240000});
    const t = await p.title();
    if (t !== 'ok') { console.error(t); process.exit(2); }
    await p.screenshot({path: v.out});
  }
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });"""


def rendus(dossier, ch, ref, deck, vues):
    """Rendus three.js dans Chromium sans écran (WebGL logiciel). Renvoie True si réussi."""
    tmp = Path(tempfile.mkdtemp())
    try:
        (tmp / "rendu.html").write_text(RENDER_HTML, encoding="utf-8")
        (tmp / "rendu.js").write_text(RENDER_JS, encoding="utf-8")
        for f in ("route.glb", "terrain.glb"):
            shutil.copy(dossier / f, tmp / f)
        srv = subprocess.Popen([sys.executable, "-m", "http.server", "8765", "--bind", "127.0.0.1"], cwd=tmp,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            views, outs = [], []
            for name, eye, at, fov in vues:
                q = (f"w=1400&h=800&fov={fov}&files=terrain.glb,route.glb&eye={','.join(f'{v:.1f}' for v in eye)}"
                     f"&at={','.join(f'{v:.1f}' for v in at)}")
                outs.append((tmp / f"{name}.png", FIG / "phase3" / f"modele_3d_{name}.png"))
                views.append({"url": f"http://127.0.0.1:8765/rendu.html?{q}", "out": str(outs[-1][0])})
            node_path = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
            res = subprocess.run(["node", "rendu.js", json.dumps(views)], cwd=tmp, capture_output=True, text=True,
                                 timeout=900, env={**os.environ, "NODE_PATH": node_path})
        finally:
            srv.terminate()
        if res.returncode != 0:
            print("rendu WebGL impossible :", res.stderr[-500:])
            return False
        for src, dst in outs:
            Image.open(src).convert("RGB").save(dst.with_suffix(".png"), optimize=True)
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ch = chaussee()
    mnt = MNT()
    deck = tablier(ch, mnt)
    ref = repere(ch)
    print(f"chaussée : {len(ch['pk'])} lignes, PK {ch['pk'][0]:.0f} à {ch['pk'][-1]:.0f}, "
          f"{deck.sum()} m de tablier ({len(runs(deck))} ouvrages)")
    rapport = {"repere": ref}
    with rasterio.open(RAW / "ortho_20cm.tif") as ortho:
        for version, (bands, tex_px, quality) in VERSIONS.items():
            dossier = MOD if version == "complet" else MOD / "apercu"
            dossier.mkdir(parents=True, exist_ok=True)
            write_glb(dossier / "route.glb", [route(ch, ref)])
            meshes, stats = terrain(ch, ref, deck, mnt, bands, tex_px, quality, ortho)
            write_glb(dossier / "terrain.glb", meshes)
            (dossier / "repere.json").write_text(json.dumps(ref, ensure_ascii=False, indent=2), encoding="utf-8")
            rapport[version] = {"bandes_m": bands, "texture_px_par_dalle": tex_px, "terrain": stats,
                                "relecture": controle(dossier, ch, ref, deck)}
            print(version, json.dumps(rapport[version], ensure_ascii=False))
    # vues : ensemble oblique (aperçu) et rapprochée sur le plus long pont (complet)
    A = to_gltf(ch["A"], ref)
    c = (A.min(0) + A.max(0)) / 2
    a, b = max(runs(deck), key=lambda ab: ab[1] - ab[0])
    m = (a + b) // 2
    t = A[min(m + 60, len(A) - 1)] - A[max(m - 60, 0)]
    t /= np.linalg.norm(t)
    side = np.array([-t[2], 0, t[0]])
    # virage le plus serré de l'ES (courbure de l'axe lissé sur 15 m)
    es = np.flatnonzero(ch["zone"] == "es")
    h = np.unwrap(np.arctan2(np.gradient(A[:, 2]), np.gradient(A[:, 0])))
    k = np.abs(np.convolve(np.gradient(h), np.ones(15) / 15, "same"))
    v = es[np.argmax(k[es])]
    cv = A[max(v - 25, 0):v + 26].mean(0)              # centre approximatif de l'épingle
    out = A[v] - cv
    out[1] = 0
    out /= max(np.linalg.norm(out), 1e-6)
    vues_ap = [("ensemble", c + np.array([-400, 2300, 2900]), c + np.array([0, -150, 150]), 45)]
    vues_co = [("pont", A[m] + 55 * side + np.array([0, 22, 0]) - 25 * t, A[m] - np.array([0, 4, 0]), 50),
               ("virage", A[v] + 70 * out + np.array([0, 35, 0]), A[v] - 10 * out, 50)]
    ok = rendus(MOD / "apercu", ch, ref, deck, vues_ap) and rendus(MOD, ch, ref, deck, vues_co)
    rapport["rendus_webgl"] = ok
    rapport["vues_rapprochees_pk"] = {"pont": [round(float(ch["pk"][a])), round(float(ch["pk"][b]))],
                                      "virage": round(float(ch["pk"][v]))}
    (MOD / "controle_modele.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy(MOD / "controle_modele.json", MOD / "apercu" / "controle_modele.json")


if __name__ == "__main__":
    main()
