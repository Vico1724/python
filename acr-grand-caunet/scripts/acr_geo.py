"""Outils communs de la chaîne géographique (ES Le Grand Caunet).

Toutes les données viennent de la Géoplateforme IGN (https://data.geopf.fr),
en Licence Ouverte Etalab 2.0. Système de travail : Lambert-93 (EPSG:2154),
en mètres, ce qui permet de mesurer directement distances et pentes.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
import requests
from pyproj import Transformer

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REF = DATA / "reference"
RAW = DATA / "raw"            # téléchargements bruts volumineux (non versionnés)
OUT = DATA / "processed"      # produits légers versionnés
FIG = ROOT / "figures"
for _d in (RAW, OUT, FIG):
    _d.mkdir(parents=True, exist_ok=True)

OFFICIAL = REF / "es_grand_caunet_2026_officiel.json"

WFS = "https://data.geopf.fr/wfs/ows"
WMS = "https://data.geopf.fr/wms-r"

# Emprise de collecte (lon/lat) : large autour du massif, tous carrefours inclus.
BBOX_LONLAT = (5.610, 43.225, 5.685, 43.268)

LAYER_MNT = "IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93"   # sol nu, 0,5 m
LAYER_MNS = "IGNF_LIDAR-HD_MNS_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93"   # sol + végétation + bâti
LAYER_ORTHO = "HR.ORTHOIMAGERY.ORTHOPHOTOS"                             # BD ORTHO 20 cm

TO_L93 = Transformer.from_crs(4326, 2154, always_xy=True)
TO_WGS = Transformer.from_crs(2154, 4326, always_xy=True)

_session = requests.Session()
_session.headers["User-Agent"] = "acr-stage-geodata/1.0"


def get(url: str, params: dict, tries: int = 4, timeout: int = 180) -> requests.Response:
    """GET avec reprises (2 s, 4 s, 8 s) sur erreur réseau ou 5xx."""
    last = None
    for i in range(tries):
        try:
            r = _session.get(url, params=params, timeout=timeout)
            if r.status_code < 500:
                r.raise_for_status()
                return r
            last = RuntimeError(f"HTTP {r.status_code}")
        except requests.RequestException as e:  # réseau
            last = e
        time.sleep(2 ** (i + 1))
    raise RuntimeError(f"échec {url}: {last}")


def wfs_layer(typename: str, bbox_lonlat=BBOX_LONLAT, page: int = 5000) -> list[dict]:
    """Télécharge toutes les entités d'une couche WFS dans l'emprise (pagination)."""
    feats: dict[str, dict] = {}
    start = 0
    while True:
        params = {
            "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
            "TYPENAMES": typename, "OUTPUTFORMAT": "application/json",
            "SRSNAME": "EPSG:4326", "COUNT": page, "STARTINDEX": start,
            "BBOX": ",".join(map(str, bbox_lonlat)) + ",urn:ogc:def:crs:OGC:1.3:CRS84",
        }
        got = get(WFS, params).json().get("features", [])
        for f in got:
            feats[f.get("id") or json.dumps(f["geometry"])[:80]] = f
        if len(got) < page:
            break
        start += page
    return list(feats.values())


def wms_tile(layer: str, x0: float, y0: float, x1: float, y1: float, res: float,
             fmt: str = "image/geotiff", style: str = "") -> bytes:
    """Une dalle WMS en Lambert-93, alignée sur la grille native (res en m/pixel)."""
    w, h = round((x1 - x0) / res), round((y1 - y0) / res)
    params = {
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": layer,
        "STYLES": style, "CRS": "EPSG:2154", "BBOX": f"{x0},{y0},{x1},{y1}",
        "WIDTH": w, "HEIGHT": h, "FORMAT": fmt,
    }
    r = get(WMS, params)
    if not r.headers.get("content-type", "").startswith("image/"):
        raise RuntimeError(f"réponse WMS inattendue: {r.text[:300]}")
    return r.content


def load_official() -> dict:
    return json.loads(OFFICIAL.read_text(encoding="utf-8"))


def l93(lon: float, lat: float) -> tuple[float, float]:
    return TO_L93.transform(lon, lat)


def wgs(x: float, y: float) -> tuple[float, float]:
    return TO_WGS.transform(x, y)


def cumdist(xy: np.ndarray) -> np.ndarray:
    """Abscisse curviligne (m) le long d'une polyligne (N,2) ou (N,3)."""
    d = np.sqrt((np.diff(xy, axis=0) ** 2).sum(axis=1))
    return np.concatenate([[0.0], np.cumsum(d)])


def project_on_line(xy: np.ndarray, p: tuple[float, float]) -> tuple[float, float]:
    """Projette p sur la polyligne : renvoie (abscisse curviligne, écart latéral) en m."""
    s = cumdist(xy)
    best = (math.inf, 0.0)
    for i in range(len(xy) - 1):
        a, b = xy[i], xy[i + 1]
        ab = b - a
        L2 = float(ab @ ab)
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, float((np.array(p) - a) @ ab) / L2))
        q = a + t * ab
        d = math.hypot(p[0] - q[0], p[1] - q[1])
        if d < best[0]:
            best = (d, s[i] + t * math.sqrt(L2))
    return best[1], best[0]


def resample(xy: np.ndarray, step: float) -> tuple[np.ndarray, np.ndarray]:
    """Rééchantillonne une polyligne à pas constant. Renvoie (s, points)."""
    s = cumdist(xy)
    t = np.arange(0.0, s[-1], step)
    if s[-1] - t[-1] > 1e-6:
        t = np.append(t, s[-1])
    return t, np.column_stack([np.interp(t, s, xy[:, k]) for k in range(xy.shape[1])])


def write_geojson(path: Path, features: list[dict], name: str | None = None) -> None:
    fc = {"type": "FeatureCollection", "features": features}
    if name:
        fc["name"] = name
    path.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
