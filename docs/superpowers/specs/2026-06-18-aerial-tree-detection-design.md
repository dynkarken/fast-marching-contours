# Aerial Tree Detection for Husportræt

**Date:** 2026-06-18
**Status:** Approved

## Problem

OSM `natural=tree` data is sparse globally. Most trees in residential and urban areas are not mapped. The poster should show all visible trees within the poster frame, not just the few OSM contributors have tagged.

## Solution

Detect tree crowns from ESRI World Imagery satellite tiles using DeepForest, a purpose-built Python library for tree crown detection from aerial RGB imagery. Results are merged with OSM trees and fed into the existing SVG rendering pipeline unchanged.

## Architecture

New module `tree_detection.py` (imported by `husportræt.py`) with three responsibilities:

1. **Tile fetching** — download ESRI World Imagery XYZ tiles covering the poster bounding box, stitch into a single PIL Image, compute a pixel→local-meters geotransform
2. **Tree detection** — run DeepForest on the stitched image, extract bounding box centers
3. **Coord conversion + merge** — convert pixel centers to local (x_m, y_m), deduplicate against OSM trees (5 m radius threshold)

## Details

### Tile source
`https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`
No API key required. Zoom level 18 (~0.6 m/pixel) for 1:1000; zoom 17 (~1.2 m/pixel) for 1:5000. Both resolutions are sufficient to resolve individual tree crowns.

### Bounding box
Derived from `lat`, `lon`, `radius_m` (same value already computed in `generate_from_address`). Converted to Web Mercator tile coordinates using standard slippy-map math.

### DeepForest
- `deepforest.main.deepforest()` with pretrained weights (downloaded once, cached by the library)
- Input: stitched RGB image as a NumPy array
- Output: DataFrame with columns `xmin, ymin, xmax, ymax, score, label`
- Tree center: `((xmin+xmax)/2, (ymin+ymax)/2)` in pixels

### Geotransform
The stitched image has a known top-left corner in Web Mercator meters and a known meters-per-pixel scale. Converting a pixel `(px, py)` to local map coords:
```
merc_x = tile_origin_x + px * m_per_px
merc_y = tile_origin_y - py * m_per_px
x_m, y_m = merc_to_local(merc_x, merc_y, lat0, lon0)
```
Local coords use the same equirectangular approximation as the rest of `husportræt.py`.

### Deduplication
Any aerial-detected tree within 5 m of an existing OSM tree point is dropped. OSM data is authoritative where present (it may include species tags in the future).

### Integration point
`generate_from_address` in `husportræt.py`:
```python
osm_trees = [...]           # existing, from parse_osm
aerial_trees = fetch_trees_aerial(lat, lon, radius_m, scale)
trees = merge_trees(osm_trees, aerial_trees)
```
`generate_svg` and all downstream rendering are unchanged.

## Dependencies added
- `deepforest` (includes PyTorch CPU, ~500 MB on first download)
- `Pillow` (already likely present; make explicit)

Added to `backend/requirements.txt`.

## Performance
- Tile fetch: ~1–3s (parallel downloads)
- DeepForest inference on CPU: ~10–25s for a 1:1000 poster area (~3000×3000 px image)
- Total added latency: ~15–30s per generation

For 1:5000 the image covers a larger area but at lower zoom, so pixel count is similar.

## Error handling
- If tile fetch fails (network error, HTTP error): log warning, fall back to OSM-only trees
- If DeepForest inference fails: same fallback
- Fallback is transparent to the user — poster still generates, just with fewer trees

## Files changed
| File | Change |
|---|---|
| `tree_detection.py` (new) | Tile fetch, detection, coord conversion, merge |
| `husportræt.py` | Import and call `fetch_trees_aerial` + `merge_trees` in `generate_from_address` |
| `backend/requirements.txt` | Add `deepforest`, `Pillow` |
