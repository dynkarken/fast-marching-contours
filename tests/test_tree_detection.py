# tests/test_tree_detection.py
import math
import pytest
from tree_detection import latlon_to_tile_xy, pixel_to_latlon


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
    assert abs(lon - expected_lon) < 1e-6


def test_pixel_to_latlon_roundtrip():
    zoom = 18
    tile_x, tile_y = 140223, 82049
    lat, lon = pixel_to_latlon(100, 150, tile_x, tile_y, zoom)
    x2, y2 = latlon_to_tile_xy(lat, lon, zoom)
    assert x2 == tile_x
    assert y2 == tile_y
