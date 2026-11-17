"""Module commun de la chaîne carte-reelle-unreal.

Contenu : lecture de zone.json, choix de la projection, calcul de l'emprise et du repère local,
téléchargements avec reprises et cache (WMS, WFS, Overpass), écriture des journaux.

Repère local (le même pour toutes les étapes) :
  x = est, y = nord, z = haut, en mètres ; origine = centre de l'emprise, arrondi au mètre ;
  z = altitude - z0, z0 = altitude du sol à l'origine (fixée par 02_relief.py).
Unreal (centimètres, main gauche) : UE.X = 100 x, UE.Y = -100 y (sud), UE.Z = 100 z.
glTF (fichiers .glb) : X = est, Y = haut, Z = sud, mètres ; l'importeur glTF d'Unreal donne
UE = 100 x (gX, gZ, gY) (constaté avec Unreal 5.6.1 sur les projets d'origine).

Données : Géoplateforme IGN (https://data.geopf.fr, Licence Ouverte Etalab 2.0),
OpenStreetMap (ODbL), Panoramax (licence propre à chaque image).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests
from pyproj import CRS, Transformer
from shapely.geometry import LineString, MultiLineString, Polygon, box, mapping, shape
import shapely
from shapely.ops import unary_union

# ------------------------------------------------------------------ constantes
WFS = "https://data.geopf.fr/wfs/ows"
WMS = "https://data.geopf.fr/wms-r"
COUCHE_LIDAR_MNT = "IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93"  # sol nu, 0,5 m natif
COUCHE_LIDAR_MNS = "IGNF_LIDAR-HD_MNS_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93"  # sol + sursol, 0,5 m
COUCHE_RGEALTI = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"                     # RGE ALTI 1 m (5 m selon les zones)
COUCHE_ORTHO = "HR.ORTHOIMAGERY.ORTHOPHOTOS"                                  # BD ORTHO 20 cm
COUCHE_IRC = "ORTHOIMAGERY.ORTHOPHOTOS.IRC"                                   # infrarouge couleur (PIR, R, V)
PANORAMAX = "https://api.panoramax.xyz/api/search"
# Overpass : le serveur principal est souvent saturé ; on essaie les miroirs publics dans l'ordre.
OVERPASS = ["https://overpass-api.de/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter"]

# Tailles de Landscape recommandées par Epic (sections de 63, 127 ou 255 quads) : une heightmap de
# l'une de ces tailles est importée sans rognage ni ajout de bord par l'outil Landscape.
TAILLES_LANDSCAPE = (505, 1009, 2017, 4033, 8129)
# Côté maximal d'une requête WMS : la Géoplateforme accepte davantage, mais une dalle de 2 000 px
# reste sous la minute et se relance à moindre coût si elle échoue.
DALLE_PX = 2000
NODATA = -9999.0
# Emprise grossière de la France métropolitaine (Corse comprise) : au-delà, les sources IGN n'ont rien.
FRANCE_LONLAT = (-5.3, 41.3, 9.7, 51.2)

DEFAUTS = {
    "marge_m": 50.0,                 # autour de l'emprise : bord de terrain et objets voisins visibles
    "resolution_terrain_m": 1.0,     # pas de la heightmap (le LiDAR HD est à 0,5 m, le RGE ALTI à 1 m)
    "taille_heightmap": "auto",      # ou une des TAILLES_LANDSCAPE
    "resolution_ortho_m": 0.5,       # 0,2 m est natif mais 6 fois plus lourd
    "texture_max_px": 8192,          # limite courante d'une texture Unreal
    "lointain": {"rayon_m": 4000.0, "pas_m": 25.0, "texture_px": 4096, "abaissement_m": 2.0},
    "vegetation": {"methode": "auto", "hauteur_min_m": 2.0},
    "photos_rue": {"vignettes": False, "max_vignettes": 100},
    "osm": True,
    "sources": {"mnt": None, "ortho": None},
}

_session = requests.Session()
_session.headers["User-Agent"] = "carte-reelle-unreal/1.0"


# ------------------------------------------------------------------ arguments et contexte
def parser(description: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--zone", help="fichier zone.json (facultatif si <sortie>/repere.json existe déjà)")
    ap.add_argument("--sortie", required=True, help="dossier de travail de la zone")
    ap.add_argument("--cache", help="dossier de cache des téléchargements (défaut : <sortie>/cache)")
    ap.add_argument("--force", action="store_true", help="refait l'étape même si ses sorties existent")
    return ap


def fusion(defaut: dict, donne: dict) -> dict:
    out = json.loads(json.dumps(defaut))
    for k, v in (donne or {}).items():
        out[k] = fusion(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


class Contexte:
    """Dossier de sortie, cache, configuration et repère de la zone."""

    def __init__(self, args):
        self.t0 = time.time()
        self.sortie = Path(args.sortie).resolve()
        self.sortie.mkdir(parents=True, exist_ok=True)
        self.cache = Path(args.cache).resolve() if getattr(args, "cache", None) else self.sortie / "cache"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.force = getattr(args, "force", False)
        p = self.sortie / "repere.json"
        if args.zone:
            zone = Path(args.zone).resolve()
            cfg = json.loads(zone.read_text(encoding="utf-8"))
            if p.exists() and not self.force:
                rep = json.loads(p.read_text(encoding="utf-8"))
                if rep.get("config") != cfg:      # zone.json modifiée : on recalcule le repère
                    rep = calculer_repere(cfg, zone.parent, self.sortie)
            else:
                rep = calculer_repere(cfg, zone.parent, self.sortie)
        elif p.exists():
            rep = json.loads(p.read_text(encoding="utf-8"))
        else:
            raise SystemExit("ERREUR : ni --zone ni <sortie>/repere.json : lancer d'abord 01_emprise.py --zone zone.json")
        self.repere = rep
        self.signature = _cle(rep["config"])
        self.cfg = fusion(DEFAUTS, rep["config"])
        self.crs = rep["crs"]
        self.ox, self.oy = rep["origine_proj"]
        self._vers_proj = Transformer.from_crs(4326, self.crs, always_xy=True)
        self._vers_wgs = Transformer.from_crs(self.crs, 4326, always_xy=True)

    # --- repère
    def ecrire_repere(self):
        (self.sortie / "repere.json").write_text(json.dumps(self.repere, ensure_ascii=False, indent=1), encoding="utf-8")

    def en_france(self) -> bool:
        return self.repere["france"]

    def lonlat_vers_local(self, lon, lat):
        x, y = self._vers_proj.transform(lon, lat)
        return np.asarray(x) - self.ox, np.asarray(y) - self.oy

    def local_vers_lonlat(self, x, y):
        return self._vers_wgs.transform(np.asarray(x) + self.ox, np.asarray(y) + self.oy)

    def emprise_locale(self) -> Polygon:
        """Zone de détail (emprise + marge), en repère local."""
        return shape(self.repere["zone_detail_locale"])

    def carre(self) -> dict:
        return self.repere["terrain"]

    def bornes_proj(self, demi: float, pixel: float = 0.0):
        """Carré centré sur l'origine, en coordonnées projetées, élargi d'un demi-pixel si demandé."""
        d = demi + pixel / 2
        return (self.ox - d, self.oy - d, self.ox + d, self.oy + d)

    def bbox_lonlat(self, x0, y0, x1, y1, local=True):
        if local:
            x0, y0, x1, y1 = x0 + self.ox, y0 + self.oy, x1 + self.ox, y1 + self.oy
        xs, ys = np.linspace(x0, x1, 9), np.linspace(y0, y1, 9)
        X, Y = np.meshgrid(xs, ys)
        lon, lat = self._vers_wgs.transform(X.ravel(), Y.ravel())
        return float(min(lon)), float(min(lat)), float(max(lon)), float(max(lat))

    # --- fichiers
    def dossier(self, nom: str) -> Path:
        d = self.sortie / nom
        d.mkdir(parents=True, exist_ok=True)
        return d

    def journal(self, nom: str, donnees: dict) -> Path:
        donnees = {"etape": nom, "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "duree_s": round(time.time() - self.t0, 1), "signature": self.signature,
                   "telechargement": {"octets": Compteur.octets, "requetes": Compteur.requetes,
                                      "lus_en_cache": Compteur.cache}, **donnees}
        p = self.dossier("journaux") / f"{nom}.json"
        p.write_text(json.dumps(donnees, ensure_ascii=False, indent=1, default=_json_defaut), encoding="utf-8")
        return p

    def deja_fait(self, nom: str, fichiers: list[Path], **options) -> dict | None:
        """Journal de l'étape si elle a déjà tourné pour cette zone avec les mêmes options et que ses
        sorties existent ; None sinon (ou avec --force)."""
        p = self.sortie / "journaux" / f"{nom}.json"
        if self.force or not p.exists() or not all(Path(f).exists() for f in fichiers):
            return None
        j = json.loads(p.read_text(encoding="utf-8"))
        if j.get("signature") != self.signature or j.get("options", {}) != json.loads(json.dumps(options, default=str)):
            return None
        return j

    def duree(self) -> str:
        return f"{time.time() - self.t0:.0f} s"


def _json_defaut(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o))


def appliquer(geom, f):
    """Applique f(x, y) -> (x2, y2) à toutes les coordonnées d'une géométrie (résultat en 2D)."""
    return shapely.transform(geom, lambda c: np.column_stack(f(c[:, 0], c[:, 1])))


# ------------------------------------------------------------------ lecture des géométries
def _kml_coords(texte: str):
    return [tuple(float(v) for v in c.split(",")[:2]) for c in texte.split()]


def lire_geometries(chemin: Path) -> list:
    """Géométries (WGS84, lon/lat) d'un fichier GeoJSON, KML ou GPX."""
    suf = chemin.suffix.lower()
    if suf in (".geojson", ".json"):
        d = json.loads(chemin.read_text(encoding="utf-8"))
        feats = d["features"] if d.get("type") == "FeatureCollection" else [d if d.get("type") == "Feature" else {"geometry": d}]
        return [shape(f["geometry"]) for f in feats if f.get("geometry")]
    racine = ET.parse(chemin).getroot()
    if suf == ".kml":
        out = []
        for el in racine.iter():
            tag = el.tag.split("}")[-1]
            if tag == "Polygon":
                ext = [c for c in el.iter() if c.tag.endswith("outerBoundaryIs")]
                coords = next(c for c in (ext[0] if ext else el).iter() if c.tag.endswith("coordinates"))
                out.append(Polygon(_kml_coords(coords.text)))
            elif tag == "LineString":
                coords = next(c for c in el.iter() if c.tag.endswith("coordinates"))
                out.append(LineString(_kml_coords(coords.text)))
        return out
    if suf == ".gpx":
        out = []
        for nom in ("trkseg", "rte"):
            for seg in (e for e in racine.iter() if e.tag.split("}")[-1] == nom):
                pts = [(float(p.get("lon")), float(p.get("lat"))) for p in seg
                       if p.tag.split("}")[-1] in ("trkpt", "rtept")]
                if len(pts) >= 2:
                    out.append(LineString(pts))
        return out
    raise SystemExit(f"ERREUR : format de fichier non reconnu ({chemin.name}) : GeoJSON, KML ou GPX attendu")


def geometrie_emprise(cfg: dict, dossier: Path):
    """Renvoie (type, géométrie WGS84) depuis la rubrique « emprise » de zone.json."""
    e = cfg["emprise"]
    t = e["type"]
    if t == "bbox":
        return t, box(*e["bbox"])
    if "fichier" in e:
        geoms = lire_geometries((dossier / e["fichier"]).resolve())
    elif "coordonnees" in e:
        c = e["coordonnees"]
        geoms = [LineString(c) if t == "trace" else Polygon(c)]
    else:
        raise SystemExit("ERREUR : emprise sans « fichier » ni « coordonnees »")
    if t == "polygone":
        polys = [g for g in geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        if not polys:
            raise SystemExit("ERREUR : aucun polygone dans le fichier d'emprise")
        return t, unary_union(polys)
    if t == "trace":
        lignes = [g for g in geoms if g.geom_type in ("LineString", "MultiLineString")]
        if not lignes:
            raise SystemExit("ERREUR : aucune ligne (trace) dans le fichier d'emprise")
        return t, unary_union(lignes)
    raise SystemExit(f"ERREUR : type d'emprise inconnu « {t} » (bbox, polygone ou trace)")


def choisir_crs(lon: float, lat: float) -> tuple[str, bool]:
    """Lambert-93 en France métropolitaine, sinon la zone UTM du centre (déformation < 0,1 %)."""
    x0, y0, x1, y1 = FRANCE_LONLAT
    if x0 <= lon <= x1 and y0 <= lat <= y1:
        return "EPSG:2154", True
    zone = int((lon + 180) // 6) + 1
    return f"EPSG:{(32600 if lat >= 0 else 32700) + zone}", False


def taille_heightmap(cote_m: float, res: float, voulu) -> tuple[int, float, str]:
    """Plus petite taille de Landscape valide qui couvre cote_m au pas res (le pas grandit si besoin)."""
    note = ""
    if voulu not in (None, "auto"):
        n = int(voulu)
        if n not in TAILLES_LANDSCAPE:
            raise SystemExit(f"ERREUR : taille_heightmap {n} invalide, choisir parmi {TAILLES_LANDSCAPE}")
        if (n - 1) * res < cote_m:
            note = f"la heightmap {n} au pas {res} m ne couvre que {(n - 1) * res:.0f} m sur {cote_m:.0f} m"
        return n, res, note
    for n in TAILLES_LANDSCAPE:
        if (n - 1) * res >= cote_m:
            return n, res, note
    n = TAILLES_LANDSCAPE[-1]
    res2 = math.ceil(cote_m / (n - 1) * 4) / 4          # pas arrondi au quart de mètre supérieur
    return n, res2, f"zone trop grande pour le pas {res} m : pas porté à {res2} m"


def calculer_repere(cfg: dict, dossier_cfg: Path, sortie: Path) -> dict:
    c = fusion(DEFAUTS, cfg)
    genre, g_wgs = geometrie_emprise(c, dossier_cfg)
    lon_c, lat_c = g_wgs.centroid.x, g_wgs.centroid.y
    crs, france = choisir_crs(lon_c, lat_c)
    vers = Transformer.from_crs(4326, crs, always_xy=True)
    g = appliquer(g_wgs, vers.transform)
    if genre == "trace":
        largeur = float(c["emprise"].get("largeur_couloir_m", 200.0))
        zone = g.buffer(largeur / 2)
    else:
        zone = g
    detail = zone.buffer(float(c["marge_m"]), join_style="mitre") if c["marge_m"] else zone
    bx0, by0, bx1, by1 = detail.bounds
    ox, oy = round((bx0 + bx1) / 2), round((by0 + by1) / 2)
    cote = max(bx1 - bx0, by1 - by0)
    n, res, note = taille_heightmap(cote, float(c["resolution_terrain_m"]), c["taille_heightmap"])
    demi = (n - 1) * res / 2
    loc = lambda geom: appliquer(geom, lambda x, y: (x - ox, y - oy))
    rep = {
        "nom": c["nom"],
        "config": cfg,
        "crs": crs,
        "france": france,
        "type_emprise": genre,
        "origine_proj": [ox, oy],
        "origine_wgs84": list(Transformer.from_crs(crs, 4326, always_xy=True).transform(ox, oy)),
        "z0_m": None,
        "axes": {"local": "x = est, y = nord, z = altitude - z0 (m)",
                 "unreal": "UE.X = 100 x, UE.Y = -100 y, UE.Z = 100 z (cm)",
                 "gltf": "X = est, Y = haut, Z = sud (m) ; importeur Unreal : UE = 100 (gX, gZ, gY)"},
        "emprise_locale": mapping(loc(zone)),
        "zone_detail_locale": mapping(loc(detail)),
        "surface_emprise_ha": round(zone.area / 1e4, 2),
        "bornes_detail_locales": [round(v, 2) for v in (bx0 - ox, by0 - oy, bx1 - ox, by1 - oy)],
        "terrain": {"taille_px": n, "pas_m": res, "cote_m": round(2 * demi, 3), "demi_cote_m": demi,
                    "note": note,
                    "bornes_locales": [-demi, -demi, demi, demi],
                    "convention": "pixel (ligne i, colonne j) au point x = -demi + j*pas, y = demi - i*pas ; "
                                  "ligne 0 au nord"},
    }
    if genre == "trace":
        rep["trace_locale"] = mapping(loc(g))
        rep["longueur_trace_m"] = round(g.length, 1)
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "repere.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    return rep


# ------------------------------------------------------------------ téléchargements
def _cle(*parts) -> str:
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:20]


def requete(url: str, params: dict | None = None, data: dict | None = None, essais: int = 4,
            delai: int = 180, accepte=None) -> requests.Response:
    """GET (ou POST si data) avec reprises 2, 4, 8 s sur erreur réseau ou 5xx/429."""
    dernier = None
    for i in range(essais):
        try:
            if data is not None:
                r = _session.post(url, data=data, timeout=delai)
            else:
                r = _session.get(url, params=params, timeout=delai)
            if r.status_code < 500 and r.status_code != 429:
                r.raise_for_status()
                if accepte and not accepte(r):
                    raise RuntimeError(f"réponse inattendue : {r.headers.get('content-type')} {r.text[:200]}")
                return r
            dernier = RuntimeError(f"HTTP {r.status_code}")
        except requests.HTTPError as e:
            raise RuntimeError(f"échec {url} : {e}") from e
        except (requests.RequestException, RuntimeError) as e:
            dernier = e
        if i < essais - 1:
            time.sleep(2 ** (i + 1))
    raise RuntimeError(f"échec {url} : {dernier}")


class Compteur:
    """Volume téléchargé pendant l'étape (hors cache)."""
    octets = 0
    requetes = 0
    cache = 0


def en_cache(cache: Path, sous: str, cle: str, ext: str, produire) -> bytes:
    d = cache / sous
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{cle}{ext}"
    if p.exists() and p.stat().st_size > 0:
        Compteur.cache += 1
        return p.read_bytes()
    b = produire()
    tmp = p.with_suffix(p.suffix + ".part")
    tmp.write_bytes(b)
    tmp.replace(p)
    Compteur.octets += len(b)
    Compteur.requetes += 1
    return b


def wms_dalle(cache: Path, couche: str, x0, y0, x1, y1, w: int, h: int, fmt: str, crs="EPSG:2154") -> bytes:
    params = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": couche, "STYLES": "",
              "CRS": crs, "BBOX": f"{x0:.3f},{y0:.3f},{x1:.3f},{y1:.3f}", "WIDTH": w, "HEIGHT": h, "FORMAT": fmt}
    ok = lambda r: r.headers.get("content-type", "").startswith("image/")
    ext = ".tif" if "tiff" in fmt else ".jpg" if "jpeg" in fmt else ".png"
    return en_cache(cache, "wms", _cle(params), ext, lambda: requete(WMS, params, accepte=ok).content)


def wms_mosaique(cache: Path, couche: str, bornes, res: float, fmt="image/geotiff", bandes=1,
                 crs="EPSG:2154", progres: str | None = None) -> np.ndarray:
    """Mosaïque WMS sur bornes (x0, y0, x1, y1) au pas res. Relief : float32 avec NaN hors donnée ;
    image : uint8 (bandes, h, w)."""
    import rasterio
    from PIL import Image
    x0, y0, x1, y1 = bornes
    W, H = round((x1 - x0) / res), round((y1 - y0) / res)
    flottant = "tiff" in fmt
    out = np.full((bandes, H, W), np.nan if flottant else 0, np.float32 if flottant else np.uint8)
    dalles = [(c, r) for r in range(0, H, DALLE_PX) for c in range(0, W, DALLE_PX)]
    for k, (c, r) in enumerate(dalles, 1):
        w, h = min(DALLE_PX, W - c), min(DALLE_PX, H - r)
        tx0, ty1 = x0 + c * res, y1 - r * res
        b = wms_dalle(cache, couche, tx0, ty1 - h * res, tx0 + w * res, ty1, w, h, fmt, crs)
        if flottant:
            with rasterio.MemoryFile(b) as mf, mf.open() as src:
                a = src.read(1).astype(np.float32)
            a[(a < -1000) | ~np.isfinite(a)] = np.nan       # -9999 (LiDAR) ou -99999 (RGE ALTI, mer)
            out[0, r:r + h, c:c + w] = a
        else:
            im = np.asarray(Image.open(io.BytesIO(b)).convert("RGB"))
            out[:, r:r + h, c:c + w] = np.moveaxis(im, -1, 0)[:bandes]
        if progres and sys.stderr.isatty():          # progression visible en console seulement
            print(f"\r  {progres} : dalle {k}/{len(dalles)}", end="", flush=True, file=sys.stderr)
    if progres and sys.stderr.isatty():
        print("\r" + " " * 60 + "\r", end="", flush=True, file=sys.stderr)
    return out


def wfs_couche(cache: Path, typename: str, bbox_lonlat, srs: str = "EPSG:2154", page: int = 5000) -> list[dict]:
    """Toutes les entités d'une couche WFS de la Géoplateforme dans la bbox (pagination)."""
    feats: dict[str, dict] = {}
    debut = 0
    bbox = ",".join(f"{v:.6f}" for v in bbox_lonlat) + ",urn:ogc:def:crs:OGC:1.3:CRS84"
    while True:
        params = {"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature", "TYPENAMES": typename,
                  "OUTPUTFORMAT": "application/json", "SRSNAME": srs, "COUNT": page, "STARTINDEX": debut,
                  "BBOX": bbox}
        b = en_cache(cache, "wfs", _cle(params), ".json", lambda: requete(WFS, params).content)
        got = json.loads(b).get("features", [])
        for f in got:
            feats[f.get("id") or json.dumps(f["geometry"])[:80]] = f
        if len(got) < page:
            break
        debut += page
    return list(feats.values())


def overpass(cache: Path, requete_ql: str, delai: int = 90) -> tuple[dict | None, str]:
    """Interroge Overpass (miroirs successifs). Renvoie (réponse, serveur) ou (None, raison)."""
    cle = _cle(requete_ql)
    p = cache / "osm" / f"{cle}.json"
    if p.exists():
        Compteur.cache += 1
        return json.loads(p.read_text(encoding="utf-8")), "cache"
    raisons = []
    for url in OVERPASS:
        try:
            r = requete(url, data={"data": requete_ql}, essais=1, delai=delai,
                        accepte=lambda r: "json" in r.headers.get("content-type", ""))
            d = r.json()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(d), encoding="utf-8")
            Compteur.octets += len(r.content)
            Compteur.requetes += 1
            return d, url
        except Exception as e:      # serveur saturé ou injoignable : miroir suivant
            raisons.append(f"{url.split('/')[2]} : {str(e)[:80]}")
    return None, " ; ".join(raisons)


# ------------------------------------------------------------------ rasters
def ecrire_tif(chemin: Path, a: np.ndarray, bornes, res: float, crs: str, nodata=None, image=False):
    import rasterio
    from rasterio.transform import from_origin
    a = a if a.ndim == 3 else a[None]
    opts = (dict(compress="jpeg", photometric="ycbcr", jpeg_quality=90) if image and a.shape[0] == 3
            else dict(compress="deflate", predictor=3 if a.dtype == np.float32 else 2, zlevel=6))
    with rasterio.open(chemin, "w", driver="GTiff", width=a.shape[2], height=a.shape[1], count=a.shape[0],
                       dtype=a.dtype, crs=crs, transform=from_origin(bornes[0], bornes[3], res, res),
                       nodata=nodata, tiled=True, blockxsize=256, blockysize=256, **opts) as dst:
        dst.write(a)


def lire_tif(chemin: Path):
    import rasterio
    with rasterio.open(chemin) as src:
        a = src.read(1).astype(np.float32)
        if src.nodata is not None:
            a[a == src.nodata] = np.nan
        return a, src.transform


def reprojeter(chemin: Path, bornes, res: float, crs: str, bandes=None, resampling="bilinear") -> np.ndarray:
    """Ramène un raster fourni par l'utilisateur (n'importe quel système) sur notre grille."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import from_origin
    from rasterio.warp import reproject
    x0, y0, x1, y1 = bornes
    W, H = round((x1 - x0) / res), round((y1 - y0) / res)
    with rasterio.open(chemin) as src:
        idx = list(range(1, (bandes or 1) + 1)) if bandes else [1]
        idx = idx[:src.count]
        flottant = bandes is None
        dst = np.full((len(idx), H, W), np.nan if flottant else 0, np.float32 if flottant else np.uint8)
        for k, b in enumerate(idx):
            reproject(rasterio.band(src, b), dst[k], dst_transform=from_origin(x0, y1, res, res), dst_crs=crs,
                      dst_nodata=np.nan if flottant else 0, resampling=getattr(Resampling, resampling))
        if flottant and src.nodata is not None:
            dst[dst == src.nodata] = np.nan
    if flottant:
        dst[dst < -1000] = np.nan
    return dst if bandes else dst[0]


def boucher(a: np.ndarray) -> tuple[np.ndarray, int]:
    """Remplace les NaN par la valeur valide la plus proche ; renvoie (tableau, pixels bouchés)."""
    from scipy import ndimage as ndi
    trou = ~np.isfinite(a)
    n = int(trou.sum())
    if n == 0 or n == a.size:
        return a, n
    idx = ndi.distance_transform_edt(trou, return_distances=False, return_indices=True)
    return a[tuple(idx)], n


def echantillonner(a: np.ndarray, tr, x, y) -> np.ndarray:
    """Valeurs d'un raster (transform affine en coordonnées locales ou projetées) aux points x, y (bilinéaire)."""
    from scipy import ndimage as ndi
    c = (np.asarray(x, float) - tr.c) / tr.a - 0.5
    r = (np.asarray(y, float) - tr.f) / tr.e - 0.5
    return ndi.map_coordinates(np.nan_to_num(a, nan=0.0), [np.atleast_1d(r), np.atleast_1d(c)], order=1, mode="nearest")


class Relief:
    """MNT du terrain (relief/mnt.tif) en repère local : z(x, y) = altitude - z0."""

    def __init__(self, ctx: Contexte, nom="relief/mnt.tif"):
        from affine import Affine
        a, tr = lire_tif(ctx.sortie / nom)
        self.a = a
        self.z0 = ctx.repere["z0_m"] or 0.0
        self.tr = Affine(tr.a, tr.b, tr.c - ctx.ox, tr.d, tr.e, tr.f - ctx.oy)   # transform en repère local

    def z(self, x, y):
        return echantillonner(self.a, self.tr, x, y) - self.z0


# ------------------------------------------------------------------ géométries et glTF
def vers_local(ctx: Contexte, geom, depuis_lonlat=False):
    if depuis_lonlat:
        return appliquer(geom, ctx.lonlat_vers_local)
    return appliquer(geom, lambda x, y: (x - ctx.ox, y - ctx.oy))


def lignes(geom):
    if geom.geom_type == "LineString":
        return [geom]
    if geom.geom_type == "MultiLineString":
        return list(geom.geoms)
    if hasattr(geom, "geoms"):
        return [l for g in geom.geoms for l in lignes(g)]
    return []


def polygones(geom):
    if geom.geom_type == "Polygon":
        return [geom]
    if hasattr(geom, "geoms"):
        return [p for g in geom.geoms for p in polygones(g)]
    return []


def ecrire_geojson(chemin: Path, feats: list[dict], **meta):
    fc = {"type": "FeatureCollection", **meta, "features": feats}
    chemin.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":"), default=_json_defaut), encoding="utf-8")


def lire_geojson(chemin: Path) -> list[dict]:
    return json.loads(chemin.read_text(encoding="utf-8"))["features"] if chemin.exists() else []


def gltf(x, y, z) -> np.ndarray:
    """Repère local (est, nord, haut) -> glTF (X = est, Y = haut, Z = sud)."""
    return np.column_stack([x, z, -np.asarray(y)])


def bornes_unreal_cm(sommets_gltf: np.ndarray) -> dict:
    v = np.asarray(sommets_gltf)
    ue = np.column_stack([v[:, 0], v[:, 2], v[:, 1]]) * 100.0
    return {"min": [round(float(a), 1) for a in ue.min(axis=0)], "max": [round(float(a), 1) for a in ue.max(axis=0)]}


def materiaux_mats(glb: bytes) -> bytes:
    """Rend tous les matériaux du GLB non métalliques et double face (sinon les volumes sortent noirs)."""
    import struct
    n = struct.unpack_from("<I", glb, 12)[0]
    doc = json.loads(glb[20:20 + n])
    mats = doc.setdefault("materials", [])
    for m in mats:
        m.setdefault("pbrMetallicRoughness", {}).update(metallicFactor=0.0, roughnessFactor=1.0)
        m["doubleSided"] = True
    for mesh in doc.get("meshes", []):
        for prim in mesh["primitives"]:
            if "material" not in prim:
                mats.append({"pbrMetallicRoughness": {"metallicFactor": 0.0, "roughnessFactor": 1.0}, "doubleSided": True})
                prim["material"] = len(mats) - 1
    j = json.dumps(doc, separators=(",", ":")).encode()
    j += b" " * (-len(j) % 4)
    reste = glb[20 + n:]
    return struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(j) + len(reste)) + struct.pack("<I4s", len(j), b"JSON") + j + reste


def grille_maillage(X, Y, Z, image=None, uv=None):
    """Maillage triangulé d'une grille régulière (tableaux 2D en repère local), texturé si image."""
    import trimesh
    from PIL import Image
    n, m = X.shape
    i = np.arange(n * m).reshape(n, m)
    a, b, c, d = i[:-1, :-1].ravel(), i[:-1, 1:].ravel(), i[1:, :-1].ravel(), i[1:, 1:].ravel()
    faces = np.concatenate([np.column_stack([a, c, b]), np.column_stack([b, c, d])])
    v = gltf(X.ravel(), Y.ravel(), Z.ravel())
    if image is None:
        return trimesh.Trimesh(v, faces, process=False)
    buf = io.BytesIO()
    image.convert("RGB").save(buf, "JPEG", quality=85)    # JPEG dans le GLB (en PNG il pèse 5 à 10 fois plus)
    img = Image.open(buf)
    mat = trimesh.visual.material.PBRMaterial(baseColorTexture=img, metallicFactor=0.0, roughnessFactor=1.0)
    return trimesh.Trimesh(v, faces, visual=trimesh.visual.TextureVisuals(uv=uv, material=mat), process=False)


def ecrire_glb(chemin: Path, maillages) -> dict:
    import trimesh
    sc = trimesh.Scene()
    for nom, m in maillages:
        sc.add_geometry(m, node_name=nom, geom_name=nom)
    chemin.write_bytes(materiaux_mats(sc.export(file_type="glb")))
    v = np.concatenate([np.asarray(m.vertices) for _, m in maillages])
    return bornes_unreal_cm(v)


def resume(lignes_txt: list[str]):
    """Affiche le résumé de l'étape (1 à 5 lignes)."""
    for l in lignes_txt[:5]:
        print(l)


def taille_fichier(p: Path) -> str:
    s = p.stat().st_size
    return f"{s / 1e6:.1f} Mo" if s >= 1e5 else f"{s / 1e3:.0f} ko"


def volume_telecharge() -> str:
    return f"{Compteur.octets / 1e6:.1f} Mo en {Compteur.requetes} requêtes, {Compteur.cache} en cache"
