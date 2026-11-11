"""Étape 15 - Vues de contrôle « conducteur » avec le décor complet.

Six vues à hauteur d'œil (1,1 m au-dessus de la chaussée, voie de droite, 1,2 m à droite de
l'axe), regard 35 m devant : pinède dense de la D3D, pont à parapets de pierre, épingle,
carrefour du Lion d'Or, montée ouverte de la D1, arrivée.

Scène : route habillée (11), ouvrages (11), carrefours et balisage (12), terrain à images de sol
(14), paysage lointain (13), ciel en dégradé, brume, soleil et ombres portées, et les arbres et
arbustes du semis (10) représentés par des FIGURANTS : trois plans verticaux croisés et un plan
horizontal par arbre, texturés par des silhouettes de pin d'Alep, de chêne vert et d'arbustes de
garrigue dessinées ici par calcul (tronc, branches, touffes d'aiguilles ou feuillage dense ;
aucune ressource externe). Ils servent à juger la composition, pas à figurer dans le jeu, qui
posera ses propres arbres (AleppoPine...).

Entrées : modele/terrain_sol.glb + modele/textures_sol/, modele/lointain.glb, route_habillee.glb,
          ouvrages.glb, annexes.glb, balisage.glb, data/processed/arbres.csv, arbustes.csv.gz,
          chaussee_precise.csv, data/reference/releve_video.json (correspondance PK -> temps de la
          vidéo de référence, pour la comparaison faite à la main ; aucune image de la vidéo n'est
          écrite dans le dépôt)
Sorties : figures/phase5/vue_<nom>.png (< 1,5 Mo), figures/phase5/figurants_arbres.png
          (planche des silhouettes), figures/phase5/vues_decor.json (positions, PK, temps vidéo)
Rendu : three.js 0.160 dans Chromium sans écran (WebGL logiciel), comme 08 et 11.
"""
import csv
import gzip
import importlib.util
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from acr_geo import FIG, OUT, REF, ROOT

_spec = importlib.util.spec_from_file_location("modele_3d", Path(__file__).with_name("08_modele_3d.py"))
m08 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m08)
_spec = importlib.util.spec_from_file_location("route_ouvrages", Path(__file__).with_name("11_route_ouvrages.py"))
m11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m11)
_spec = importlib.util.spec_from_file_location("textures_sol", Path(__file__).with_name("14_textures_sol.py"))
m14 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m14)

MOD = ROOT / "modele"
FIG5 = FIG / "phase5"
SEED = 15
OEIL_H = 1.1          # m au-dessus de la chaussée
OEIL_LAT = 1.2        # m à droite de l'axe
VISEE = 35.0          # m devant
FOV = 52.0            # degrés (vertical), image 16:9
W, H = 1600, 900
R_ARBRES = 700.0      # m autour de l'œil
R_ARBUSTES = 250.0


# --- silhouettes d'arbres (calculées) --------------------------------------------------------------
def _bruit(h, w, rng, echelle):
    a = rng.random((max(2, h // echelle), max(2, w // echelle))).astype(np.float32)
    return cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def _touffe(img, alpha, cx, cy, rx, ry, couleur, rng, densite=0.75, clair=0.25):
    """Touffe de feuillage : disque irrégulier, criblé de trous, éclairé par le haut."""
    h, w = alpha.shape
    x0, x1 = max(0, int(cx - rx * 1.4)), min(w, int(cx + rx * 1.4) + 1)
    y0, y1 = max(0, int(cy - ry * 1.4)), min(h, int(cy + ry * 1.4) + 1)
    if x1 <= x0 or y1 <= y0:
        return
    Y, X = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = (X - cx) / rx, (Y - cy) / ry
    r = np.sqrt(dx * dx + dy * dy)
    ang = np.arctan2(dy, dx)
    bord = 1 + 0.22 * np.sin(5 * ang + rng.random() * 6) + 0.12 * np.sin(11 * ang + rng.random() * 6)
    n = _bruit(y1 - y0, x1 - x0, rng, 3)
    m = (r < bord) & (n < densite + 0.25 * (1 - r))
    lum = 1 + clair * (-dy) * 0.8 + 0.25 * (n - 0.5) - 0.15 * r
    col = np.clip(np.array(couleur, np.float32)[None, None] * lum[..., None], 0, 255)
    sub = img[y0:y1, x0:x1]
    sub[m] = col[m]
    alpha[y0:y1, x0:x1][m] = 255


def _tronc(img, alpha, pts, larg, couleur, rng):
    """Tronc ou branche : polyligne épaisse, écorce sombre avec une face éclairée."""
    c = np.array(couleur, np.float32) * (0.94 + 0.12 * rng.random())
    for (x0, y0), (x1, y1), (l0, l1) in zip(pts[:-1], pts[1:], zip(larg[:-1], larg[1:])):
        n = max(2, int(math.hypot(x1 - x0, y1 - y0)))
        for t in np.linspace(0, 1, n):
            x, y, l = x0 + t * (x1 - x0), y0 + t * (y1 - y0), max(1.0, l0 + t * (l1 - l0))
            cv2.circle(img, (int(x), int(y)), int(l), c.tolist(), -1)
            cv2.circle(alpha, (int(x), int(y)), int(l), 255, -1)
            cv2.circle(img, (int(x - l * 0.35), int(y)), max(1, int(l * 0.35)), (c * 1.15).clip(0, 255).tolist(), -1)


def pin_alep(seed, w=512, h=1024, jeune=False):
    """Pin d'Alep vu de côté : fût élancé souvent penché, branches montantes, houppier clair,
    irrégulier et ajouré, en touffes d'aiguilles vert-gris à l'extrémité des branches. « jeune » :
    houppier descendant plus bas (sujets de moins de 9 m, les plus nombreux)."""
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w, 3), np.float32)
    al = np.zeros((h, w), np.uint8)
    pen = rng.normal(0, 0.06) * w
    base = (w / 2 - pen * 0.5, h - 1)
    hc = h * (rng.uniform(0.62, 0.72) if jeune else rng.uniform(0.42, 0.55))   # base du houppier (depuis le haut)
    top = (w / 2 + pen, h * 0.12)
    mid = (w / 2 + pen * 0.6 + rng.normal(0, 0.03) * w, hc)
    ecorce = (92, 86, 80)
    _tronc(img, al, [base, mid, top], [w * 0.022, w * 0.015, w * 0.006], ecorce, rng)
    touffes = []
    for k in range(rng.integers(5, 9)):
        t = rng.uniform(0.0, 0.85)
        sx, sy = mid[0] + t * (top[0] - mid[0]), mid[1] + t * (top[1] - mid[1])
        cote = rng.choice([-1, 1])
        ex = sx + cote * rng.uniform(0.15, 0.45) * w
        ey = max(sy - rng.uniform(0.04, 0.2) * h, 0.09 * h)
        ex = np.clip(ex, 0.14 * w, 0.86 * w)
        _tronc(img, al, [(sx, sy), (ex, ey)], [w * 0.008, w * 0.004], ecorce, rng)
        touffes.append((ex, ey))
    touffes.append(top)
    vert = [(80, 92, 60), (72, 84, 54), (90, 100, 66)]
    for ex, ey in touffes:
        for j in range(rng.integers(5, 9)):
            cx = ex + rng.normal(0, 0.07) * w
            cy = ey + rng.normal(0, 0.03) * h
            _touffe(img, al, cx, cy, rng.uniform(0.05, 0.10) * w, rng.uniform(0.022, 0.042) * h,
                    vert[rng.integers(3)], rng, densite=0.5, clair=0.35)
    return img, al


def chene_vert(seed, w=512, h=512):
    """Chêne vert : tronc court souvent multiple, houppier dense et arrondi, vert sombre."""
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w, 3), np.float32)
    al = np.zeros((h, w), np.uint8)
    ecorce = (74, 70, 64)
    for k in range(rng.integers(1, 4)):
        x0 = w / 2 + rng.normal(0, 0.05) * w
        _tronc(img, al, [(x0, h - 1), (x0 + rng.normal(0, 0.08) * w, h * 0.55)], [w * 0.017, w * 0.009], ecorce, rng)
    vert = [(58, 70, 42), (52, 64, 38), (66, 76, 46)]
    for j in range(70):
        a = rng.uniform(0, 2 * math.pi)
        rr = math.sqrt(rng.random())
        cx = w / 2 + math.cos(a) * rr * 0.36 * w
        cy = h * 0.42 + math.sin(a) * rr * 0.30 * h
        _touffe(img, al, cx, cy, rng.uniform(0.07, 0.13) * w, rng.uniform(0.07, 0.12) * h,
                vert[rng.integers(3)], rng, densite=0.85, clair=0.3)
    return img, al


def arbuste(seed, w=256, h=256, couleur=(70, 80, 52)):
    """Arbuste de garrigue (chêne kermès, romarin, genêt) : dôme bas, dense."""
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w, 3), np.float32)
    al = np.zeros((h, w), np.uint8)
    for j in range(40):
        a = rng.uniform(math.pi, 2 * math.pi)
        rr = math.sqrt(rng.random())
        cx = w / 2 + math.cos(a) * rr * 0.38 * w
        cy = h * 0.92 + math.sin(a) * rr * 0.62 * h
        c = np.array(couleur) * rng.uniform(0.85, 1.12)
        _touffe(img, al, cx, cy, rng.uniform(0.08, 0.16) * w, rng.uniform(0.08, 0.14) * h, c.tolist(), rng,
                densite=0.8, clair=0.3)
    return img, al


def vue_dessus(seed, couleurs, w=512, densite=0.6):
    """Plan horizontal du houppier (vu de dessous ou de dessus) : touffes en couronne."""
    rng = np.random.default_rng(seed)
    img = np.zeros((w, w, 3), np.float32)
    al = np.zeros((w, w), np.uint8)
    for j in range(60):
        a = rng.uniform(0, 2 * math.pi)
        rr = math.sqrt(rng.random()) * 0.38
        _touffe(img, al, w / 2 + math.cos(a) * rr * w, w / 2 + math.sin(a) * rr * w, rng.uniform(0.06, 0.12) * w,
                rng.uniform(0.06, 0.12) * w, couleurs[rng.integers(len(couleurs))], rng, densite=densite, clair=0.0)
    return img, al


def atlas_figurants():
    """Atlas RGBA : 4 pins, 4 chênes, 4 arbustes, 2 vues de dessus. Renvoie (png, cases uv)."""
    cases = {}
    A = np.zeros((2048, 2048, 4), np.uint8)

    def pose(nom, rgb, al, x, y):
        h, w = al.shape
        # couleur prolongée sous les zones transparentes (pas de liseré noir au filtrage)
        m = al > 0
        if m.any():
            fill = cv2.inpaint(np.clip(rgb, 0, 255).astype(np.uint8), (~m).astype(np.uint8), 3, cv2.INPAINT_TELEA) \
                if m.mean() < 0.98 else rgb.astype(np.uint8)
        else:
            fill = rgb.astype(np.uint8)
        A[y:y + h, x:x + w, :3] = fill
        A[y:y + h, x:x + w, 3] = al
        cases[nom] = [x / 2048, y / 2048, (x + w) / 2048, (y + h) / 2048]

    for k in range(4):
        pose(f"pin{k}", *pin_alep(SEED + k, jeune=k >= 2), 512 * k, 0)
    for k in range(4):
        pose(f"chene{k}", *chene_vert(SEED + 10 + k), 512 * k, 1024)
    cols = [(70, 80, 52), (92, 98, 70), (110, 108, 60), (62, 72, 50)]
    for k in range(4):
        pose(f"arbuste{k}", *arbuste(SEED + 20 + k, couleur=cols[k]), 256 * k, 1536)
    pose("pin_dessus", *vue_dessus(SEED + 30, [(96, 112, 60), (88, 104, 56)], 512, 0.6), 1024, 1536)
    pose("chene_dessus", *vue_dessus(SEED + 31, [(58, 70, 42), (52, 64, 38)], 512, 0.85), 1536, 1536)
    buf = io.BytesIO()
    Image.fromarray(A, "RGBA").save(buf, "PNG", optimize=True)
    return buf.getvalue(), cases, A


# --- scène par vue ---------------------------------------------------------------------------------------
def lire_glb_images(path):
    """Relit un glb : maillages (comme m14.lire_glb) avec les octets des images intégrées."""
    b = Path(path).read_bytes()
    n = int(np.frombuffer(b, "<u4", 1, 12)[0])
    gl = json.loads(b[20:20 + n])
    binoff = 20 + n + 8
    ms = m14.lire_glb(path)
    for m, gm in zip(ms, gl["meshes"]):
        mat = gl["materials"][gm["primitives"][0]["material"]]
        imgs = {}
        for cle, t in (("couleur", mat["pbrMetallicRoughness"].get("baseColorTexture")), ("relief", mat.get("normalTexture"))):
            if not t:
                continue
            im = gl["images"][gl["textures"][t["index"]]["source"]]
            if "uri" in im:
                imgs[cle] = Path(path).parent / im["uri"]
            else:
                v = gl["bufferViews"][im["bufferView"]]
                imgs[cle] = b[binoff + v.get("byteOffset", 0): binoff + v.get("byteOffset", 0) + v["byteLength"]]
        m["imgs"] = imgs
    return ms


def reduit(src, px, png=False):
    im = Image.open(src if isinstance(src, Path) else io.BytesIO(src))
    if im.size[0] > px:
        im = im.resize((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    if png:
        im.save(buf, "PNG", optimize=False, compress_level=1)
    else:
        im.convert("RGB").save(buf, "JPEG", quality=90)
    return buf.getvalue()


def dist_plan(pos, eye):
    lo, hi = pos[:, [0, 2]].min(0), pos[:, [0, 2]].max(0)
    q = np.clip(eye[[0, 2]], lo, hi)
    return float(np.linalg.norm(q - eye[[0, 2]]))


def glb_vue(path, eye, regle, sortie):
    """Copie d'un glb pour une vue : images réduites selon la distance à l'œil (WebGL logiciel)."""
    meshes = []
    for m in lire_glb_images(path):
        d = dist_plan(m["pos"], eye)
        px_c, px_r = regle(m["name"], d)
        mm = {"name": m["name"], "pos": m["pos"], "nrm": m["nrm"], "uv": m["uv"], "idx": m["idx"], "rough": 0.97}
        if "couleur" in m["imgs"]:
            mm["couleur"] = reduit(m["imgs"]["couleur"], px_c)
        if px_r and "relief" in m["imgs"]:
            mm["relief"] = reduit(m["imgs"]["relief"], px_r, png=True)
        meshes.append(mm)
    m14.ecrire_glb(sortie, meshes)


def regle_sol(nom, d):
    if nom.startswith("sous_"):
        return (2048 if d < 60 else 1024 if d < 200 else 512 if d < 600 else 128), (1024 if d < 150 else 0)
    return (2048 if d < 250 else 1024 if d < 800 else 512), (1024 if d < 400 else 0)


def regle_lointain(nom, d):
    return (1024 if d < 1500 else 512 if d < 4000 else 256 if d < 10000 else 128), 0


def figurants(eye, vers, ref):
    """Instances d'arbres et d'arbustes autour de l'œil : (x, y, z, h, largeur, angle, type)."""
    rng = np.random.default_rng(SEED)
    out = []
    with open(OUT / "arbres.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    A = np.array([[float(r["x_l93"]), float(r["y_l93"]), float(r["z_sol_m"]), float(r["hauteur_m"]),
                   float(r["diametre_houppier_m"])] for r in rows])
    ess = np.array([r["essence"] for r in rows])
    G = m08.to_gltf(A[:, :3], ref)
    d = np.hypot(G[:, 0] - eye[0], G[:, 2] - eye[2])
    av = (G[:, 0] - eye[0]) * vers[0] + (G[:, 2] - eye[2]) * vers[2]
    sel = (d < R_ARBRES) & (av > -40)
    conif = np.isin(ess, ["pin d'Alep", "autre pin (pignon ou maritime)", "cyprès"])
    for i in np.flatnonzero(sel):
        h, dia = A[i, 3], A[i, 4]
        if conif[i]:
            typ = int(rng.integers(0, 2)) if h >= 9 else int(rng.integers(2, 4))
            larg = max(min(dia * 1.15, h * 0.9), h * 0.35)
        else:
            typ = 4 + int(rng.integers(0, 4))
            larg = max(min(dia * 1.1, h * 1.4), h * 0.7)
        out.append([*G[i], h, larg, rng.uniform(0, math.pi), typ])
    n_arbres = len(out)
    with gzip.open(OUT / "arbustes.csv.gz", "rt", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    B = np.array([[float(r["x_l93"]), float(r["y_l93"]), float(r["z_sol_m"]), float(r["hauteur_m"]), float(r["diametre_m"])]
                  for r in rows])
    G = m08.to_gltf(B[:, :3], ref)
    d = np.hypot(G[:, 0] - eye[0], G[:, 2] - eye[2])
    av = (G[:, 0] - eye[0]) * vers[0] + (G[:, 2] - eye[2]) * vers[2]
    for i in np.flatnonzero((d < R_ARBUSTES) & (av > -20)):
        out.append([*G[i], B[i, 3], max(B[i, 4], B[i, 3] * 1.1), rng.uniform(0, math.pi), 8 + int(rng.integers(0, 4))])
    return np.array(out, np.float32), n_arbres


RENDER_HTML = r"""<!doctype html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script></head><body>
<script type="module">
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const P = new URLSearchParams(location.search);
const W = +P.get('w'), H = +P.get('h');
const V = JSON.parse(await (await fetch(P.get('vue'))).text());
const r = new THREE.WebGLRenderer({antialias:true, preserveDrawingBuffer:true, logarithmicDepthBuffer:true});
r.setSize(W, H); r.outputColorSpace = THREE.SRGBColorSpace;
r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = V.exposition;
r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(r.domElement);
const scene = new THREE.Scene();
const horizon = new THREE.Color(V.ciel_horizon), zenith = new THREE.Color(V.ciel_zenith);
scene.fog = new THREE.FogExp2(V.brume, V.brume_densite);
// ciel : dégradé
const sky = new THREE.Mesh(new THREE.SphereGeometry(60000, 32, 16), new THREE.ShaderMaterial({
  side: THREE.BackSide, depthWrite: false, fog: false,
  uniforms: {h: {value: horizon}, z: {value: zenith}},
  vertexShader: 'varying vec3 p; void main(){ p = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
  fragmentShader: 'uniform vec3 h; uniform vec3 z; varying vec3 p; void main(){ float t = clamp(p.y*2.2, 0.0, 1.0); gl_FragColor = vec4(mix(h, z, pow(t, 0.7)), 1.0); }'}));
sky.renderOrder = -1;
const eye = new THREE.Vector3(...V.oeil), at = new THREE.Vector3(...V.vise);
sky.position.copy(eye); scene.add(sky);
scene.add(new THREE.HemisphereLight(V.hemi_ciel, V.hemi_sol, V.hemi_intensite));
const sun = new THREE.DirectionalLight(0xfff4e6, V.soleil_intensite);
const sd = new THREE.Vector3(...V.soleil_dir).normalize();
const c0 = eye.clone().add(at.clone().sub(eye).setY(0).normalize().multiplyScalar(110));
sun.position.copy(c0).add(sd.clone().multiplyScalar(400)); sun.target.position.copy(c0);
sun.castShadow = true; sun.shadow.mapSize.set(4096, 4096);
const sc = sun.shadow.camera; sc.left = -200; sc.right = 200; sc.top = 200; sc.bottom = -200; sc.near = 10; sc.far = 900;
sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.04;
scene.add(sun); scene.add(sun.target);
const cam = new THREE.PerspectiveCamera(V.fov, W / H, 0.2, 90000);
cam.position.copy(eye); cam.lookAt(at);
// figurants : plans croisés
const atlas = await new THREE.TextureLoader().loadAsync('atlas.png');
atlas.colorSpace = THREE.SRGBColorSpace; atlas.anisotropy = 8;
const arbres = new Float32Array(await (await fetch('arbres.bin')).arrayBuffer());
const cases = V.cases;
function geo(type) {
  const nom = type < 4 ? 'pin' + type : type < 8 ? 'chene' + (type - 4) : 'arbuste' + (type - 8);
  const [u0, v0, u1, v1] = cases[nom];
  const pos = [], nrm = [], uv = [], idx = [];
  const N = 4;
  function quad(ang, flip) {
    const ax = Math.cos(ang), az = Math.sin(ang);
    const base = pos.length / 3;
    for (let j = 0; j <= N; j++) for (let i = 0; i <= N; i++) {
      const s = i / N - 0.5, t = j / N;
      pos.push(s * ax, t, s * az);
      const n = new THREE.Vector3(s * ax * 1.6, 0.55 + 0.6 * t, s * az * 1.6).add(new THREE.Vector3(-az, 0, ax).multiplyScalar(flip * 0.25)).normalize();
      nrm.push(n.x, n.y, n.z);
      uv.push(u0 + (i / N) * (u1 - u0), 1 - (v1 - t * (v1 - v0)));
    }
    for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
      const a = base + j * (N + 1) + i, b = a + 1, c = a + N + 1, d = c + 1;
      if (flip > 0) idx.push(a, b, d, a, d, c); else idx.push(a, d, b, a, c, d);
    }
  }
  for (const k of [0, 1, 2]) { quad(k * Math.PI / 3, 1); quad(k * Math.PI / 3, -1); }
  if (type >= 4 && type < 8) {   // chêne : plan horizontal du houppier (vu d'en dessous)
    const [a0, b0, a1, b1] = cases[type < 4 ? 'pin_dessus' : 'chene_dessus'];
    const hy = type < 2 ? 0.78 : type < 4 ? 0.62 : 0.5, base = pos.length / 3;
    for (const [x, z, uu, vv] of [[-0.5, -0.5, a0, b0], [0.5, -0.5, a1, b0], [0.5, 0.5, a1, b1], [-0.5, 0.5, a0, b1]]) {
      pos.push(x, hy, z); nrm.push(x * 0.7, 0.45, z * 0.7); uv.push(uu, 1 - vv);
    }
    idx.push(base, base + 1, base + 2, base, base + 2, base + 3, base, base + 2, base + 1, base, base + 3, base + 2);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  return g;
}
const matF = new THREE.MeshStandardMaterial({map: atlas, alphaTest: 0.45, roughness: 0.92, metalness: 0});
const n = arbres.length / 7;
for (let type = 0; type < 12; type++) {
  const ids = [];
  for (let i = 0; i < n; i++) if (arbres[i * 7 + 6] == type) ids.push(i);
  if (!ids.length) continue;
  const im = new THREE.InstancedMesh(geo(type), matF, ids.length);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3();
  ids.forEach((i, k) => {
    const o = i * 7;
    p.set(arbres[o], arbres[o + 1] - 0.15, arbres[o + 2]);
    q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), arbres[o + 5]);
    s.set(arbres[o + 4], arbres[o + 3], arbres[o + 4]);
    im.setMatrixAt(k, m.compose(p, q, s));
  });
  im.castShadow = true; im.receiveShadow = true; im.frustumCulled = false;
  scene.add(im);
}
const L = new GLTFLoader();
for (const f of V.fichiers) {
  const g = await L.loadAsync(f);
  g.scene.traverse(o => { if (o.isMesh) { o.receiveShadow = true; o.castShadow = !f.startsWith('lointain');
    if (o.material.map) o.material.map.anisotropy = 16;
    if (f.startsWith('lointain')) o.material.fog = true; } });
  scene.add(g.scene);
}
r.render(scene, cam);
document.title = 'ok';
</script></body></html>"""

RENDER_JS = """const { chromium } = require('playwright');
(async () => {
  const views = JSON.parse(process.argv[2]);
  const b = await chromium.launch({args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
                                          '--js-flags=--max-old-space-size=8192']});
  const p = await b.newPage({viewport: {width: VW, height: VH}});
  p.on('console', m => { if (m.type() === 'error') console.error('console:', m.text()); });
  p.on('pageerror', e => console.error('pageerror:', e.message));
  for (const v of views) {
    await p.goto(v.url);
    await p.waitForFunction(() => document.title !== '', null, {timeout: 900000});
    if ((await p.title()) !== 'ok') { console.error(await p.title()); process.exit(2); }
    await p.screenshot({path: v.out});
  }
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });""".replace("VW", str(W)).replace("VH", str(H))


def temps_video(pk):
    """Temps (s) de la vidéo de référence v2 au PK donné (table du relevé vidéo, interpolée)."""
    t = json.loads((REF / "releve_video.json").read_text(encoding="utf-8"))["table_temps_pk"]["v2"]
    pts = [(t["depart"]["t_s"], t["depart"]["pk_m"])] + [(r["t_s"], r["pk_m"]) for r in t["reperes"]] + \
          [(t["arrivee"]["t_s"], t["arrivee"]["pk_m"])]
    pts.sort()
    return float(np.interp(pk, [p[1] for p in pts], [p[0] for p in pts]))


def choix_vues(ch):
    """PK des six vues. Pinède : fenêtre de la D3D la plus dense en pins à moins de 20 m ;
    montée de la D1 : fenêtre la plus dégagée (le moins d'arbres à moins de 25 m) en montée."""
    with open(OUT / "arbres.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    pk = np.array([float(r["pk_m"]) for r in rows])
    da = np.array([float(r["dist_axe_m"]) for r in rows])
    pin = np.array([r["essence"] == "pin d'Alep" for r in rows])
    def compte(p0, p1, dmax, m=None):
        s = (pk >= p0) & (pk < p1) & (da < dmax)
        return int((s & m).sum()) if m is not None else int(s.sum())
    cand = np.arange(300, 3400, 20)
    p_pin = int(cand[np.argmax([compte(p + 5, p + 60, 20, pin) for p in cand])])
    z = np.interp(np.arange(0, 7000), ch["pk"], ch["A"][:, 2])
    cand = np.arange(4400, 6400, 20)
    score = [compte(p, p + 90, 25) - 3 * (z[p + 80] - z[p]) for p in cand]
    p_d1 = int(cand[np.argmin(score)])
    return {"pinede_d3d": (p_pin, VISEE), "pont_pierre_1653": (1615, 38.0), "epingle_2225": (2192, 26.0),
            "lion_dor": (3588, 40.0), "montee_d1": (p_d1, 45.0), "arrivee": (6680, 45.0),
            # contrôles du paysage lointain : vers la Sainte-Baume depuis la D1, et raccord vu d'en haut
            "controle_horizon": (6000, ("azimut", 48.0, 0.012)), "controle_raccord": (4900, ("survol", 230.0, 140.0))}


def rendus(vues_cfg, dossier_tmp, fichiers_communs):
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "8767", "--bind", "127.0.0.1"], cwd=dossier_tmp,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(0.5)
        views = [{"url": f"http://127.0.0.1:8767/{v}/rendu.html?w={W}&h={H}&vue=vue.json", "out": str(dossier_tmp / v / "rendu.png")}
                 for v in vues_cfg]
        npm, node = shutil.which("npm"), shutil.which("node")      # npm.cmd sous Windows : chemin complet
        if not (npm and node):
            print("rendu WebGL impossible : Node.js (npm, node) introuvable ; rendus sautés")
            return False
        node_path = subprocess.run([npm, "root", "-g"], capture_output=True, text=True).stdout.strip()
        res = subprocess.run([node, "rendu.js", json.dumps(views)], cwd=dossier_tmp, capture_output=True, text=True,
                             timeout=3600, env={**os.environ, "NODE_PATH": node_path})
    finally:
        srv.terminate()
    if res.returncode != 0:
        print("rendu WebGL impossible :", res.stderr[-1500:])
        return False
    return True


def main():
    t0 = time.time()
    FIG5.mkdir(parents=True, exist_ok=True)
    ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    ch = m08.chaussee()
    rg = m11.Rangs(ch)
    png, cases, A = atlas_figurants()
    # planche des figurants (sur fond de ciel)
    bg = np.zeros_like(A[..., :3])
    bg[:] = (205, 216, 226)
    a = A[..., 3:4] / 255.0
    Image.fromarray((A[..., :3] * a + bg * (1 - a)).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS).save(
        FIG5 / "figurants_arbres.png", optimize=True)
    choix = choix_vues(ch)
    seules = set(sys.argv[1:])
    tmp = Path(tempfile.mkdtemp())
    info = {}
    try:
        (tmp / "rendu.js").write_text(RENDER_JS, encoding="utf-8")
        communs = ["route_habillee.glb", "ouvrages.glb", "annexes.glb", "balisage.glb"]
        noms = [n for n in choix if not seules or n in seules]
        for nom in noms:
            pk, visee = choix[nom]
            d = tmp / nom
            d.mkdir()
            (d / "rendu.html").write_text(RENDER_HTML, encoding="utf-8")
            (d / "atlas.png").write_bytes(png)
            for f in communs:
                try:
                    os.symlink(MOD / f, d / f)
                except OSError:                      # Windows sans droit de créer des liens : copie
                    shutil.copy(MOD / f, d / f)
            e_l93 = rg.point(np.array([float(pk)]), OEIL_LAT, OEIL_H)
            if isinstance(visee, tuple) and visee[0] == "azimut":        # regard horizontal vers un azimut
                az_v = math.radians(visee[1])
                a_l93 = e_l93 + np.array([[1000 * math.sin(az_v), 1000 * math.cos(az_v), 1000 * visee[2]]])
                visee = 1000.0
            elif isinstance(visee, tuple):                                # survol : au-dessus et à côté de la route
                A_, _, _, _, _ = rg(np.array([float(pk) - 1, float(pk) + 1]))
                t_ = (A_[1] - A_[0])[:2] / np.linalg.norm((A_[1] - A_[0])[:2])
                n_ = np.array([t_[1], -t_[0]])
                c_ = rg(np.array([float(pk)]))[0][0]
                e_l93 = np.array([[*(c_[:2] + n_ * visee[1] - t_ * 60), c_[2] + visee[2]]])
                a_l93 = np.array([[*(c_[:2] - n_ * 150 + t_ * 80), c_[2] - 20]])
                visee = 0.0
            else:
                a_l93 = rg.point(np.array([float(pk + visee)]), 0.6, OEIL_H * 0.75)
            eye = m08.to_gltf(e_l93, ref)[0]
            at = m08.to_gltf(a_l93, ref)[0]
            vers = (at - eye) / np.linalg.norm(at - eye)
            glb_vue(MOD / "terrain_sol.glb", eye, regle_sol, d / "sol.glb")
            glb_vue(MOD / "lointain.glb", eye, regle_lointain, d / "lointain.glb")
            arb, n_arb = figurants(eye, vers, ref)
            (d / "arbres.bin").write_bytes(arb.tobytes())
            az, el = math.radians(205), math.radians(30)            # soleil de novembre, début d'après-midi
            V = {"oeil": eye.tolist(), "vise": at.tolist(), "fov": FOV, "cases": cases, "exposition": 1.15,
                 "ciel_horizon": "#e4e8ea", "ciel_zenith": "#b4c4d3", "brume": "#d8dde1", "brume_densite": 0.00005,
                 "hemi_ciel": "#dbe3ea", "hemi_sol": "#7a6c58", "hemi_intensite": 2.0, "soleil_intensite": 1.5,
                 "soleil_dir": [math.sin(az) * math.cos(el), math.sin(el), -math.cos(az) * math.cos(el)],
                 "fichiers": ["sol.glb", "lointain.glb"] + communs}
            (d / "vue.json").write_text(json.dumps(V), encoding="utf-8")
            info[nom] = {"pk_oeil": pk, "pk_vise": pk + visee if visee else None, "oeil_gltf": np.round(eye, 2).tolist(),
                         "vise_gltf": np.round(at, 2).tolist(), "arbres": n_arb, "arbustes": int(len(arb) - n_arb),
                         "temps_video_v2_s": round(temps_video(pk), 1)}
            print(nom, info[nom], flush=True)
        ok = rendus(noms, tmp, communs)
        if ok:
            for nom in noms:
                im = Image.open(tmp / nom / "rendu.png").convert("RGB")
                dst = FIG5 / f"vue_{nom}.png"
                im.save(dst, optimize=True)
                if dst.stat().st_size > 1.45e6:
                    im.resize((1280, 720), Image.LANCZOS).save(dst, optimize=True)
                if dst.stat().st_size > 1.45e6:
                    im.resize((1280, 720), Image.LANCZOS).quantize(256, method=Image.Quantize.MEDIANCUT,
                                                                   dither=Image.Dither.FLOYDSTEINBERG).save(dst, optimize=True)
                info[nom]["fichier"] = dst.relative_to(ROOT).as_posix()
                info[nom]["taille_mo"] = round(dst.stat().st_size / 1e6, 2)
                im_chk = np.asarray(Image.open(dst).convert("RGB"))
                info[nom]["controle_image"] = {"pixels_noirs_pct": round(float((im_chk.sum(2) < 15).mean() * 100), 2),
                                               "luminance_moyenne": round(float(im_chk.mean()), 1)}
        old = json.loads((FIG5 / "vues_decor.json").read_text(encoding="utf-8")) if (FIG5 / "vues_decor.json").exists() else {}
        old.update(info)
        (FIG5 / "vues_decor.json").write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"durée : {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
