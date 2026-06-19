# tests/test_tree_detection.py
import math
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
import io
from tree_detection import latlon_to_tile_xy, pixel_to_latlon, fetch_esri_tiles, zoom_for_scale


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
