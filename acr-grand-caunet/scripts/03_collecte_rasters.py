"""Étape 3 - Télécharge le relief LiDAR HD et l'orthophoto le long de l'ES.

Seules les dalles de 500 m qui touchent le couloir de l'ES sont téléchargées.

Sorties brutes (data/raw, non versionnées car volumineuses) :
  mnt_lidarhd_50cm.tif    sol nu, 0,5 m           (relief de la route et des talus)
  mns_lidarhd_50cm.tif    sol + arbres + bâti     (hauteur de la végétation = MNS - MNT)
  ortho_20cm.tif          photo aérienne 20 cm    (marquage, bas-côtés, textures)
Sortie versionnée (data/processed) :
  mnt_couloir_1m.tif      relief à 1 m, limité à 150 m de part et d'autre de l'axe
"""
import csv
import io
import sys

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from shapely.geometry import LineString, box

from acr_geo import LAYER_MNS, LAYER_MNT, LAYER_ORTHO, OUT, RAW, wms_tile

TILE = 500          # m
BUFFER_RAW = 300    # m de part et d'autre de l'axe pour les bruts
BUFFER_REPO = 150   # m pour le produit versionné


def axis_line() -> LineString:
    with open(OUT / "axe_bdtopo_l93.csv") as f:
        return LineString([(float(r["x_l93"]), float(r["y_l93"])) for r in csv.DictReader(f)])


def tiles(line: LineString, buf: float):
    zone = line.buffer(buf)
    x0, y0, x1, y1 = (int(v // TILE * TILE) for v in zone.bounds)
    x1, y1 = x1 + TILE, y1 + TILE
    todo = [(x, y) for x in range(x0, x1, TILE) for y in range(y0, y1, TILE)
            if zone.intersects(box(x, y, x + TILE, y + TILE))]
    return (x0, y0, x1, y1), todo


def mosaic(layer: str, path, res: float, fmt: str, bands: int, dtype: str, nodata, extra: dict):
    line = axis_line()
    (x0, y0, x1, y1), todo = tiles(line, BUFFER_RAW)
    w, h = round((x1 - x0) / res), round((y1 - y0) / res)
    profile = dict(driver="GTiff", width=w, height=h, count=bands, dtype=dtype, crs="EPSG:2154",
                   transform=from_origin(x0, y1, res, res), tiled=True, blockxsize=512,
                   blockysize=512, nodata=nodata, BIGTIFF="IF_SAFER", **extra)
    n = round(TILE / res)
    with rasterio.open(path, "w", **profile) as dst:
        for k, (tx, ty) in enumerate(todo, 1):
            raw = wms_tile(layer, tx, ty, tx + TILE, ty + TILE, res, fmt=fmt)
            with rasterio.open(io.BytesIO(raw)) as src:
                data = src.read()[:bands]
            if nodata is not None:  # les sources n'ont pas toutes la même valeur « vide »
                data = np.where(data < -1000, nodata, data)
            win = rasterio.windows.Window(round((tx - x0) / res), round((y1 - ty - TILE) / res), n, n)
            dst.write(data.astype(dtype), window=win)
            print(f"\r{path.name}: dalle {k}/{len(todo)}", end="", flush=True)
    print()


def corridor_product():
    """MNT à 1 m (moyenne 2x2 du 0,5 m), masqué au-delà de BUFFER_REPO."""
    line = axis_line()
    zone = line.buffer(BUFFER_REPO)
    with rasterio.open(RAW / "mnt_lidarhd_50cm.tif") as src:
        bx0, by0, bx1, by1 = (int(v // 10 * 10) for v in zone.bounds)
        bx1, by1 = bx1 + 10, by1 + 10
        win = rasterio.windows.from_bounds(bx0, by0, bx1, by1, src.transform)
        w, h = bx1 - bx0, by1 - by0
        a = src.read(1, window=win, out_shape=(h, w), resampling=Resampling.average, masked=True)
    tr = from_origin(bx0, by1, 1.0, 1.0)
    outside = geometry_mask([zone], out_shape=(h, w), transform=tr, invert=False)
    out = np.where(outside | a.mask, -9999.0, np.round(a.filled(-9999.0), 2)).astype("float32")
    with rasterio.open(OUT / "mnt_couloir_1m.tif", "w", driver="GTiff", width=w, height=h, count=1,
                       dtype="float32", crs="EPSG:2154", transform=tr, nodata=-9999.0, tiled=True,
                       compress="deflate", predictor=3, zlevel=9) as dst:
        dst.write(out, 1)
    valid = out[out > -9999]
    print(f"mnt_couloir_1m.tif : {w}x{h} px, altitudes {valid.min():.1f} à {valid.max():.1f} m, "
          f"{(out == -9999).mean() * 100:.0f} % hors couloir")


if __name__ == "__main__":
    what = set(sys.argv[1:]) or {"mnt", "mns", "ortho", "couloir"}
    elev = dict(compress="deflate", predictor=3, zlevel=6)
    if "mnt" in what:
        mosaic(LAYER_MNT, RAW / "mnt_lidarhd_50cm.tif", 0.5, "image/geotiff", 1, "float32", -9999.0, elev)
    if "mns" in what:
        mosaic(LAYER_MNS, RAW / "mns_lidarhd_50cm.tif", 0.5, "image/geotiff", 1, "float32", -9999.0, elev)
    if "ortho" in what:
        mosaic(LAYER_ORTHO, RAW / "ortho_20cm.tif", 0.2, "image/geotiff", 3, "uint8", None,
               dict(compress="jpeg", photometric="ycbcr", jpeg_quality=88))
    if "couloir" in what:
        corridor_product()
