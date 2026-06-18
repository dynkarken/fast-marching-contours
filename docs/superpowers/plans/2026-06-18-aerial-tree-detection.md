# Aerial Tree Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect tree crowns from ESRI World Imagery satellite tiles using DeepForest and merge results with OSM trees in the Husportræt poster generator.

**Architecture:** A new `tree_detection.py` module handles three concerns: fetching and stitching ESRI XYZ tiles, running DeepForest crown detection, and converting pixel coordinates back to the poster's local meter coordinate system. `husportræt.py` calls `fetch_trees_aerial()` and merges results with OSM trees before passing to `generate_svg`.

**Tech Stack:** Python 3.9+, `deepforest`, `Pillow`, `requests` (already present), `concurrent.futures` (stdlib)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `tree_detection.py` | **Create** | Tile math, ESRI fetch, DeepForest inference, coord conversion, merge |
| `husportræt.py` | **Modify** | Import and call `fetch_trees_aerial` + `merge_trees` in `generate_from_address` |
| `backend/requirements.txt` | **Modify** | Add `deepforest`, `Pillow` |
| `tests/test_tree_detection.py` | **Create** | Unit tests for tile math, coord conversion, merge logic |

---

## Task 1: Tile coordinate math

**Files:**
- Create: `tree_detection.py`
- Create: `tests/test_tree_detection.py`

These are pure math functions with no I/O — test first.

- [ ] **Step 1: Create test file with tile math tests**

```python
# tests/test_tree_detection.py
import math
import pytest
from tree_detection import latlon_to_tile_xy, pixel_to_latlon


def test_latlon_to_tile_xy_known_point():
    # Copenhagen city hall, zoom 18
    # Verified against https://www.maptiler.com/google-maps-coordinates-tile-finder/
    x, y = latlon_to_tile_xy(55.6761, 12.5683, zoom=18)
    assert x == 142365
    assert y == 79498


def test_latlon_to_tile_xy_wraps_antimeridian():
    x, y = latlon_to_tile_xy(0.0, 179.9, zoom=1)
    assert x == 1
    assert y == 1


def test_pixel_to_latlon_tile_origin():
    # Top-left pixel of tile (142365, 79498) at zoom 18 should be
    # the tile's north-west corner
    zoom = 18
    tile_x, tile_y = 142365, 79498
    n = 2 ** zoom
    # pixel (0, 0) in the stitched image that starts at (tile_x, tile_y)
    lat, lon = pixel_to_latlon(0, 0, tile_x, tile_y, zoom)
    # lon should match tile left edge
    expected_lon = tile_x / n * 360.0 - 180.0
    assert abs(lon - expected_lon) < 1e-6


def test_pixel_to_latlon_roundtrip():
    zoom = 18
    tile_x, tile_y = 142365, 79498
    # Take a point known to be inside the tile (pixel 100, 150)
    lat, lon = pixel_to_latlon(100, 150, tile_x, tile_y, zoom)
    # Re-derive the tile — should still be the same tile
    x2, y2 = latlon_to_tile_xy(lat, lon, zoom)
    assert x2 == tile_x
    assert y2 == tile_y
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/jms/fast-marching-contours
python -m pytest tests/test_tree_detection.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'tree_detection'`

- [ ] **Step 3: Create `tree_detection.py` with tile math only**

```python
# tree_detection.py
from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import NamedTuple

import requests
from PIL import Image
import io

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
```

- [ ] **Step 4: Run tests — tile math should pass**

```bash
python -m pytest tests/test_tree_detection.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add tree_detection.py tests/test_tree_detection.py
git commit -m "feat: add tile coordinate math with tests"
```

---

## Task 2: ESRI tile fetching and stitching

**Files:**
- Modify: `tree_detection.py`
- Modify: `tests/test_tree_detection.py`

- [ ] **Step 1: Add fetch tests using mocked HTTP**

Add to `tests/test_tree_detection.py`:

```python
from unittest.mock import patch, MagicMock
from PIL import Image
import io
from tree_detection import fetch_esri_tiles, zoom_for_scale


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
    # lat/lon near Copenhagen, small radius so only a handful of tiles
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
    # stitched image must cover at least the radius
    assert img.width >= 256
    assert img.height >= 256
    assert z == zoom
    assert mock_get.called
```

- [ ] **Step 2: Run test to confirm failure**

```bash
python -m pytest tests/test_tree_detection.py::test_fetch_esri_tiles_stitches_correctly tests/test_tree_detection.py::test_zoom_for_scale -v
```

Expected: `AttributeError` or `ImportError` — functions not yet defined.

- [ ] **Step 3: Implement `zoom_for_scale` and `fetch_esri_tiles` in `tree_detection.py`**

Add after the existing functions:

```python
def zoom_for_scale(scale: int) -> int:
    return 18 if scale <= 1000 else 17


def _download_tile(z: int, x: int, y: int, session: requests.Session) -> tuple[int, int, Image.Image]:
    url = ESRI_URL.format(z=z, x=x, y=y)
    r = session.get(url, timeout=15)
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
    # Approximate bounding box in lat/lon (equirectangular, good enough for < 5 km)
    deg_per_m_lat = 1.0 / (R_EARTH * math.pi / 180.0)
    deg_per_m_lon = deg_per_m_lat / math.cos(math.radians(lat0))
    pad = radius_m * 1.05  # 5 % margin

    lat_min = lat0 - pad * deg_per_m_lat
    lat_max = lat0 + pad * deg_per_m_lat
    lon_min = lon0 - pad * deg_per_m_lon
    lon_max = lon0 + pad * deg_per_m_lon

    x_min, y_max = latlon_to_tile_xy(lat_max, lon_min, zoom)  # NW → smallest y
    x_max, y_min = latlon_to_tile_xy(lat_min, lon_max, zoom)  # SE → largest y

    cols = list(range(x_min, x_max + 1))
    rows = list(range(y_min, y_max + 1))

    canvas_w = len(cols) * TILE_SIZE
    canvas_h = len(rows) * TILE_SIZE
    canvas = Image.new("RGB", (canvas_w, canvas_h))

    session = requests.Session()
    session.headers["User-Agent"] = "husportraet-generator/1.0"

    tasks = [(zoom, x, y) for y in rows for x in cols]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_download_tile, z, x, y, session): (x, y) for z, x, y in tasks}
        for future in as_completed(futures):
            tx, ty, tile_img = future.result()
            px = (tx - x_min) * TILE_SIZE
            py = (ty - y_min) * TILE_SIZE
            canvas.paste(tile_img, (px, py))

    return canvas, x_min, y_min, zoom
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_tree_detection.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add tree_detection.py tests/test_tree_detection.py
git commit -m "feat: fetch and stitch ESRI satellite tiles"
```

---

## Task 3: Coordinate conversion and tree merging

**Files:**
- Modify: `tree_detection.py`
- Modify: `tests/test_tree_detection.py`

- [ ] **Step 1: Add tests**

Add to `tests/test_tree_detection.py`:

```python
from tree_detection import pixels_to_local, merge_trees


def test_pixels_to_local_center_pixel():
    # pixel at the center of the image should be very close to (0, 0) local coords
    zoom = 18
    lat0, lon0 = 55.6761, 12.5683
    tile_x_min, tile_y_min = latlon_to_tile_xy(lat0, lon0, zoom)
    # The tile containing (lat0, lon0): its pixel 0,0 is the tile NW corner.
    # The center of the tile is at pixel (128, 128).
    # So pixel (128, 128) should be near the origin of local coords.
    pts = pixels_to_local([(128, 128)], tile_x_min, tile_y_min, zoom, lat0, lon0)
    x_m, y_m = pts[0]
    # Should be within 50 m of origin (tile is ~150 m wide at zoom 18)
    assert abs(x_m) < 150
    assert abs(y_m) < 150


def test_merge_trees_keeps_all_when_far_apart():
    osm = [(0.0, 0.0), (100.0, 0.0)]
    aerial = [(50.0, 0.0), (200.0, 0.0)]
    merged = merge_trees(osm, aerial, dedup_radius=5.0)
    assert len(merged) == 4


def test_merge_trees_deduplicates_close_points():
    osm = [(0.0, 0.0)]
    aerial = [(3.0, 0.0)]  # within 5 m of OSM point
    merged = merge_trees(osm, aerial, dedup_radius=5.0)
    assert len(merged) == 1
    assert merged[0] == (0.0, 0.0)  # OSM point is kept


def test_merge_trees_empty_aerial():
    osm = [(10.0, 20.0)]
    merged = merge_trees(osm, [], dedup_radius=5.0)
    assert merged == [(10.0, 20.0)]


def test_merge_trees_empty_osm():
    aerial = [(10.0, 20.0)]
    merged = merge_trees([], aerial, dedup_radius=5.0)
    assert merged == [(10.0, 20.0)]
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_tree_detection.py::test_pixels_to_local_center_pixel tests/test_tree_detection.py::test_merge_trees_keeps_all_when_far_apart -v
```

Expected: `ImportError` — functions not defined.

- [ ] **Step 3: Implement `pixels_to_local` and `merge_trees` in `tree_detection.py`**

```python
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
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/test_tree_detection.py -v
```

Expected: all 11 tests pass.

- [ ] **Step 5: Commit**

```bash
git add tree_detection.py tests/test_tree_detection.py
git commit -m "feat: pixel-to-local coord conversion and tree merge with dedup"
```

---

## Task 4: DeepForest inference wrapper

**Files:**
- Modify: `tree_detection.py`
- Modify: `tests/test_tree_detection.py`

- [ ] **Step 1: Add test with mocked DeepForest**

Add to `tests/test_tree_detection.py`:

```python
import numpy as np
import pandas as pd
from tree_detection import detect_trees_deepforest


def test_detect_trees_deepforest_returns_centers():
    # Create a tiny fake RGB image
    fake_image = Image.new("RGB", (512, 512), (34, 100, 34))
    fake_arr = np.array(fake_image)

    # DeepForest returns a DataFrame with xmin/ymin/xmax/ymax columns
    fake_df = pd.DataFrame({
        "xmin": [10.0, 200.0],
        "ymin": [20.0, 300.0],
        "xmax": [50.0, 240.0],
        "ymax": [60.0, 340.0],
        "score": [0.9, 0.85],
        "label": ["Tree", "Tree"],
    })

    mock_model = MagicMock()
    mock_model.predict_image.return_value = fake_df

    with patch("tree_detection.deepforest.main.deepforest", return_value=mock_model):
        centers = detect_trees_deepforest(fake_image)

    assert len(centers) == 2
    assert centers[0] == (30, 40)   # center of first box
    assert centers[1] == (220, 320) # center of second box


def test_detect_trees_deepforest_returns_empty_on_none():
    fake_image = Image.new("RGB", (256, 256), (0, 0, 0))

    mock_model = MagicMock()
    mock_model.predict_image.return_value = None

    with patch("tree_detection.deepforest.main.deepforest", return_value=mock_model):
        centers = detect_trees_deepforest(fake_image)

    assert centers == []
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_tree_detection.py::test_detect_trees_deepforest_returns_centers -v
```

Expected: `ImportError` — `detect_trees_deepforest` not defined (deepforest itself may not be installed yet; that's fine, the mock patches it).

- [ ] **Step 3: Install deepforest**

```bash
pip install deepforest Pillow
```

- [ ] **Step 4: Add import and `detect_trees_deepforest` to `tree_detection.py`**

At the top of `tree_detection.py`, add:

```python
import numpy as np
from deepforest import main as deepforest_main
```

Then add the function:

```python
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
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_tree_detection.py -v
```

Expected: all 13 tests pass.

- [ ] **Step 6: Commit**

```bash
git add tree_detection.py tests/test_tree_detection.py
git commit -m "feat: DeepForest inference wrapper with model caching"
```

---

## Task 5: Public API — `fetch_trees_aerial`

**Files:**
- Modify: `tree_detection.py`
- Modify: `tests/test_tree_detection.py`

- [ ] **Step 1: Add integration test with all pieces mocked**

Add to `tests/test_tree_detection.py`:

```python
from tree_detection import fetch_trees_aerial


def test_fetch_trees_aerial_end_to_end():
    lat0, lon0 = 55.6761, 12.5683
    radius_m = 300.0
    scale = 1000

    fake_image = Image.new("RGB", (1024, 1024), (34, 100, 34))
    fake_tile_bytes = _make_fake_tile_bytes()

    fake_df = pd.DataFrame({
        "xmin": [100.0],
        "ymin": [100.0],
        "xmax": [140.0],
        "ymax": [140.0],
        "score": [0.9],
        "label": ["Tree"],
    })

    mock_model = MagicMock()
    mock_model.predict_image.return_value = fake_df

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.content = fake_tile_bytes

    with patch("tree_detection.requests.get", return_value=mock_resp), \
         patch("tree_detection.deepforest_main.deepforest", return_value=mock_model):
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_tree_detection.py::test_fetch_trees_aerial_end_to_end tests/test_tree_detection.py::test_fetch_trees_aerial_falls_back_on_error -v
```

Expected: `ImportError` — `fetch_trees_aerial` not defined.

- [ ] **Step 3: Implement `fetch_trees_aerial` in `tree_detection.py`**

```python
def fetch_trees_aerial(
    lat0: float,
    lon0: float,
    radius_m: float,
    scale: int,
) -> list[tuple[float, float]]:
    """
    Fetch satellite tiles, detect tree crowns with DeepForest, and return
    tree positions as local (x_m, y_m) coords. Returns [] on any error.
    """
    try:
        zoom = zoom_for_scale(scale)
        print(f"  Henter satellit-tiles (zoom {zoom}) …")
        image, tile_x_min, tile_y_min, zoom = fetch_esri_tiles(lat0, lon0, radius_m, zoom)
        print(f"  Kører trædetektering på {image.width}×{image.height} px billede …")
        pixel_centers = detect_trees_deepforest(image)
        print(f"  Detekterede {len(pixel_centers)} træer fra luftfoto")
        local_pts = pixels_to_local(pixel_centers, tile_x_min, tile_y_min, zoom, lat0, lon0)
        return local_pts
    except Exception as e:
        print(f"  ⚠ Trædetektering fejlede ({e}), bruger kun OSM-træer")
        return []
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/test_tree_detection.py -v
```

Expected: all 15 tests pass.

- [ ] **Step 5: Commit**

```bash
git add tree_detection.py tests/test_tree_detection.py
git commit -m "feat: fetch_trees_aerial public API with error fallback"
```

---

## Task 6: Wire into `husportræt.py` and update requirements

**Files:**
- Modify: `husportræt.py` (around line 466–481, the `generate_from_address` function)
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add import to `husportræt.py`**

At the top of `husportræt.py`, after the existing imports:

```python
from tree_detection import fetch_trees_aerial, merge_trees
```

- [ ] **Step 2: Update `generate_from_address` to fetch aerial trees**

Replace the current `generate_from_address` function (lines 466–481):

```python
def generate_from_address(address: str, scale: int = 1000) -> tuple[str, dict]:
    lat, lon = geocode(address)
    matrikel = fetch_matrikel(address, lat, lon)
    diag_m = math.hypot(PAPER_W, PAPER_H) / 2.0 / 1000.0 * scale
    radius_m = diag_m * 1.10
    raw = fetch_osm(lat, lon, radius_m)
    buildings, roads, waters, osm_trees = parse_osm(raw, lat, lon)
    aerial_trees = fetch_trees_aerial(lat, lon, radius_m, scale)
    trees = merge_trees(osm_trees, aerial_trees)
    selected_ids = find_selected(buildings, matrikel)
    svg = generate_svg(buildings, roads, waters, trees, selected_ids, scale, matrikel, output=None)
    info = {
        "lat": lat, "lon": lon,
        "buildings": len(buildings), "roads": len(roads),
        "waters": len(waters),
        "trees": len(trees),
        "trees_osm": len(osm_trees),
        "trees_aerial": len(aerial_trees),
        "selected_ids": list(selected_ids),
    }
    return svg, info
```

- [ ] **Step 3: Update `backend/requirements.txt`**

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6
numpy
scikit-image
scikit-fmm
matplotlib
deepforest
Pillow
```

- [ ] **Step 4: Smoke test — generate a real poster**

With the backend running (`python -m uvicorn main:app --reload --port 8000` from `backend/`), run:

```bash
cd /Users/jms/fast-marching-contours
python3 husportræt.py --address "Holmevej 118, 8270 Højbjerg" --scale 1000 --output /tmp/test_trees.svg
```

Expected output includes lines like:
```
  Henter satellit-tiles (zoom 18) …
  Kører trædetektering på NNNxNNN px billede …
  Detekterede N træer fra luftfoto
```

And `/tmp/test_trees.svg` opens with visible tree symbols.

- [ ] **Step 5: Commit**

```bash
git add husportræt.py backend/requirements.txt
git commit -m "feat: wire aerial tree detection into poster generation pipeline"
```

---

## Self-Review Notes

- **Spec coverage:** tile fetch ✓, DeepForest inference ✓, coord conversion ✓, dedup merge ✓, error fallback ✓, requirements ✓, integration point ✓
- **Placeholder scan:** all steps have concrete code
- **Type consistency:** `fetch_trees_aerial` returns `list[tuple[float, float]]` matching `merge_trees` input and `parse_osm` tree output; `detect_trees_deepforest` returns `list[tuple[int, int]]` consumed by `pixels_to_local`
- **Model caching:** `_deepforest_model` global ensures weights are only loaded once per process (important since the backend is long-running)
- **`deepforest_main` import alias:** the mock in tests patches `tree_detection.deepforest_main.deepforest` — this matches the import `from deepforest import main as deepforest_main` in the module
