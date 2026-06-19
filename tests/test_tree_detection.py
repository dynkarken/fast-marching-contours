# tests/test_tree_detection.py
import math
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
import io
import numpy as np
from tree_detection import (
    latlon_to_tile_xy,
    pixel_to_latlon,
    fetch_esri_tiles,
    zoom_for_scale,
    pixels_to_local,
    merge_trees,
    detect_trees_vegetation,
    fetch_trees_aerial,
)


def test_latlon_to_tile_xy_known_point():
    # Copenhagen city hall, zoom 18
    x, y = latlon_to_tile_xy(55.6761, 12.5683, zoom=18)
    assert x == 140223
    assert y == 82049


def test_latlon_to_tile_xy_wraps_antimeridian():
    x, y = latlon_to_tile_xy(0.0, 179.9, zoom=1)
    assert x == 1
    assert y == 1


def test_pixel_to_latlon_tile_origin():
    zoom = 18
    tile_x, tile_y = 140223, 82049
    n = 2 ** zoom
    lat, lon = pixel_to_latlon(0, 0, tile_x, tile_y, zoom)
    expected_lon = tile_x / n * 360.0 - 180.0
    expected_lat = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * tile_y / n))))
    assert abs(lat - expected_lat) < 1e-6
    assert abs(lon - expected_lon) < 1e-6


def test_pixel_to_latlon_roundtrip():
    zoom = 18
    tile_x, tile_y = 140223, 82049
    lat, lon = pixel_to_latlon(100, 150, tile_x, tile_y, zoom)
    x2, y2 = latlon_to_tile_xy(lat, lon, zoom)
    assert x2 == tile_x
    assert y2 == tile_y


def _make_fake_tile_bytes(color=(34, 139, 34)) -> bytes:
    """Return PNG bytes for a solid-color 256x256 tile."""
    img = Image.new("RGB", (256, 256), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_zoom_for_scale():
    assert zoom_for_scale(1000) == 18
    assert zoom_for_scale(5000) == 17


def test_fetch_esri_tiles_stitches_correctly():
    lat0, lon0 = 55.6761, 12.5683
    radius_m = 200.0
    zoom = 18

    fake_tile = _make_fake_tile_bytes()

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.content = fake_tile

    with patch("tree_detection.requests.get", return_value=mock_resp) as mock_get:
        img, tile_x_min, tile_y_min, z = fetch_esri_tiles(lat0, lon0, radius_m, zoom)

    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"
    assert img.width >= 256
    assert img.height >= 256
    assert z == zoom
    assert mock_get.called


def test_pixels_to_local_center_pixel():
    zoom = 18
    lat0, lon0 = 55.6761, 12.5683
    tile_x_min, tile_y_min = latlon_to_tile_xy(lat0, lon0, zoom)
    pts = pixels_to_local([(128, 128)], tile_x_min, tile_y_min, zoom, lat0, lon0)
    x_m, y_m = pts[0]
    # Pixel (128, 128) of the tile containing (lat0, lon0) should be near origin
    assert abs(x_m) < 150
    assert abs(y_m) < 150


def test_merge_trees_keeps_all_when_far_apart():
    osm = [(0.0, 0.0), (100.0, 0.0)]
    aerial = [(50.0, 0.0), (200.0, 0.0)]
    merged = merge_trees(osm, aerial, dedup_radius=5.0)
    assert len(merged) == 4


def test_merge_trees_deduplicates_close_points():
    osm = [(0.0, 0.0)]
    aerial = [(3.0, 0.0)]  # within 5 m
    merged = merge_trees(osm, aerial, dedup_radius=5.0)
    assert len(merged) == 1
    assert merged[0] == (0.0, 0.0)


def test_merge_trees_empty_aerial():
    osm = [(10.0, 20.0)]
    merged = merge_trees(osm, [], dedup_radius=5.0)
    assert merged == [(10.0, 20.0)]


def test_merge_trees_empty_osm():
    aerial = [(10.0, 20.0)]
    merged = merge_trees([], aerial, dedup_radius=5.0)
    assert merged == [(10.0, 20.0)]


def _make_tree_image(size: int = 256) -> Image.Image:
    """
    Synthetic image with one clear dark-green textured blob in the centre.
    Mimics a tree crown at satellite zoom 18 (dark, saturated, slightly noisy green).
    """
    arr = np.full((size, size, 3), (180, 180, 180), dtype=np.uint8)  # grey background
    rng = np.random.default_rng(42)
    cy, cx = size // 2, size // 2
    radius = 20
    for y in range(size):
        for x in range(size):
            if (x - cx) ** 2 + (y - cy) ** 2 < radius ** 2:
                # Dark saturated green with texture noise (±25 gives std≈14 > threshold 12)
                noise = int(rng.integers(-25, 25))
                arr[y, x] = (max(0, 30 + noise), max(0, 80 + noise), max(0, 20 + noise))
    return Image.fromarray(arr, "RGB")


def test_detect_trees_vegetation_finds_single_crown():
    image = _make_tree_image(256)
    centers = detect_trees_vegetation(image)
    assert len(centers) >= 1
    # The detected crown should be near the centre of the image
    cx, cy = 128, 128
    assert any(abs(px - cx) < 30 and abs(py - cy) < 30 for px, py in centers)


def test_detect_trees_vegetation_no_detections_on_grey():
    grey = Image.new("RGB", (256, 256), (128, 128, 128))
    centers = detect_trees_vegetation(grey)
    assert centers == []


def test_fetch_trees_aerial_end_to_end():
    lat0, lon0 = 55.6761, 12.5683
    radius_m = 300.0
    scale = 1000

    # Use a uniform dark-green tile so vegetation mask fires and returns detections
    fake_tile_bytes = _make_fake_tile_bytes(color=(30, 90, 20))

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.content = fake_tile_bytes

    with patch("tree_detection.requests.get", return_value=mock_resp):
        trees = fetch_trees_aerial(lat0, lon0, radius_m, scale)

    assert isinstance(trees, list)
    for x_m, y_m in trees:
        assert isinstance(x_m, float)
        assert isinstance(y_m, float)


def test_fetch_trees_aerial_falls_back_on_error():
    lat0, lon0 = 55.6761, 12.5683
    with patch("tree_detection.requests.get", side_effect=Exception("network error")):
        trees = fetch_trees_aerial(lat0, lon0, 300.0, 1000)
    assert trees == []
