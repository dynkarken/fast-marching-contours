# tree_detection.py
from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

import requests
from PIL import Image

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
