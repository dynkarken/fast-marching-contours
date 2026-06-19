# tree_detection.py
from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

import numpy as np
import requests
from PIL import Image
from deepforest import main as deepforest_main

TILE_SIZE = 256
ESRI_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
R_EARTH = 6_371_000.0


def latlon_to_tile_xy(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert lat/lon to XYZ tile coordinates at the given zoom level."""
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def pixel_to_latlon(px: int, py: int, tile_x_min: int, tile_y_min: int, zoom: int) -> tuple[float, float]:
    """
    Convert a pixel position in the stitched image back to lat/lon.
    (px, py) are pixel offsets from the top-left of the stitched image,
    which starts at tile (tile_x_min, tile_y_min).
    """
    n = 2 ** zoom
    global_px = tile_x_min * TILE_SIZE + px
    global_py = tile_y_min * TILE_SIZE + py
    lon = global_px / (n * TILE_SIZE) * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * global_py / (n * TILE_SIZE)))))
    return lat, lon


def zoom_for_scale(scale: int) -> int:
    """Return the zoom level for the given scale in meters."""
    return 18 if scale <= 1000 else 17


def _download_tile(z: int, x: int, y: int) -> tuple[int, int, Image.Image]:
    """Download a single ESRI tile and return (x, y, image)."""
    url = ESRI_URL.format(z=z, x=x, y=y)
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    return x, y, img


def fetch_esri_tiles(
    lat0: float, lon0: float, radius_m: float, zoom: int
) -> tuple[Image.Image, int, int, int]:
    """
    Download and stitch ESRI World Imagery tiles covering a circle of radius_m
    around (lat0, lon0) at the given zoom level.

    Returns (stitched_image, tile_x_min, tile_y_min, zoom).
    """
    deg_per_m_lat = 1.0 / (R_EARTH * math.pi / 180.0)
    deg_per_m_lon = deg_per_m_lat / math.cos(math.radians(lat0))
    pad = radius_m * 1.05

    lat_min = lat0 - pad * deg_per_m_lat
    lat_max = lat0 + pad * deg_per_m_lat
    lon_min = lon0 - pad * deg_per_m_lon
    lon_max = lon0 + pad * deg_per_m_lon

    x_min, y_max = latlon_to_tile_xy(lat_max, lon_min, zoom)  # NW corner
    x_max, y_min = latlon_to_tile_xy(lat_min, lon_max, zoom)  # SE corner

    cols = list(range(x_min, x_max + 1))
    rows = list(range(min(y_min, y_max), max(y_min, y_max) + 1))

    canvas_w = len(cols) * TILE_SIZE
    canvas_h = len(rows) * TILE_SIZE
    canvas = Image.new("RGB", (canvas_w, canvas_h))

    tasks = [(zoom, x, y) for y in rows for x in cols]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_download_tile, z, x, y): (x, y) for z, x, y in tasks}
        for future in as_completed(futures):
            tx, ty, tile_img = future.result()
            px = (tx - x_min) * TILE_SIZE
            py = (ty - y_min) * TILE_SIZE
            canvas.paste(tile_img, (px, py))

    return canvas, x_min, y_min, zoom


def pixels_to_local(
    pixel_points: list[tuple[int, int]],
    tile_x_min: int,
    tile_y_min: int,
    zoom: int,
    lat0: float,
    lon0: float,
) -> list[tuple[float, float]]:
    """Convert pixel coords in the stitched image to local (x_m, y_m) map coords."""
    result = []
    for px, py in pixel_points:
        lat, lon = pixel_to_latlon(px, py, tile_x_min, tile_y_min, zoom)
        mid_lat = math.radians((lat + lat0) / 2.0)
        x_m = math.radians(lon - lon0) * math.cos(mid_lat) * R_EARTH
        y_m = math.radians(lat - lat0) * R_EARTH
        result.append((x_m, y_m))
    return result


_deepforest_model = None


def _get_model():
    global _deepforest_model
    if _deepforest_model is None:
        _deepforest_model = deepforest_main.deepforest()
        _deepforest_model.use_release()
    return _deepforest_model


def detect_trees_deepforest(image: Image.Image) -> list[tuple[int, int]]:
    """
    Run DeepForest tree crown detection on a PIL Image.
    Returns a list of (px, py) pixel centers for each detected tree crown.
    """
    model = _get_model()
    img_array = np.array(image)
    predictions = model.predict_image(image=img_array, return_plot=False)
    if predictions is None or len(predictions) == 0:
        return []
    centers = [
        (int((row.xmin + row.xmax) / 2), int((row.ymin + row.ymax) / 2))
        for _, row in predictions.iterrows()
    ]
    return centers


def merge_trees(
    osm_trees: list[tuple[float, float]],
    aerial_trees: list[tuple[float, float]],
    dedup_radius: float = 5.0,
) -> list[tuple[float, float]]:
    """
    Merge OSM and aerial tree lists. Drop any aerial tree within dedup_radius
    meters of an existing OSM tree. OSM data is authoritative.
    """
    merged = list(osm_trees)
    for ax, ay in aerial_trees:
        too_close = any(
            math.hypot(ax - ox, ay - oy) < dedup_radius
            for ox, oy in osm_trees
        )
        if not too_close:
            merged.append((ax, ay))
    return merged
