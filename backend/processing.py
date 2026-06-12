"""Image → contour line art via the Fast Marching Method.

Pipeline:
  1. Grayscale, downscale to working resolution, tone adjustments (per preset).
  2. FMM travel time from a centre seed with speed = luminance:
     dark areas are "slow", so evenly spaced time contours bunch together
     in shadows and spread out in highlights.
  3. Smooth the travel-time field, trace level sets with marching squares
     (skimage.find_contours) — no matplotlib involved.
  4. Per contour: drop specks, Douglas-Peucker simplify, emit as smooth
     Catmull-Rom splines in a clean plotter-style SVG.
"""

import io

import numpy as np
import skfmm
from skimage import io as skio
from skimage.filters import gaussian
from skimage.measure import approximate_polygon, find_contours
from skimage.transform import resize

PRESETS = {
    'A': {'blur': 0.00275, 'contrast': 0.85, 'brightness': 0.10, 'gamma': 1.0,
          'levels': 280, 'field_smooth': 1.5, 'desc': 'balanced · default settings'},
    'B': {'blur': 0.00275, 'contrast': 0.95, 'brightness': 0.05, 'gamma': 1.0,
          'levels': 280, 'field_smooth': 1.5, 'desc': 'high contrast, low brightness'},
    'C': {'blur': 0.00275, 'contrast': 0.75, 'brightness': 0.15, 'gamma': 1.0,
          'levels': 240, 'field_smooth': 2.0, 'desc': 'low contrast, brighter, calmer'},
    'D': {'blur': 0.00275, 'contrast': 0.85, 'brightness': 0.10, 'gamma': 0.85,
          'levels': 280, 'field_smooth': 1.5, 'desc': 'gamma darkening applied'},
    'E': {'blur': 0.00400, 'contrast': 0.80, 'brightness': 0.10, 'gamma': 1.0,
          'levels': 220, 'field_smooth': 2.5, 'desc': 'heavy blur, soft flowing lines'},
    'F': {'blur': 0.00200, 'contrast': 0.90, 'brightness': 0.05, 'gamma': 1.0,
          'levels': 340, 'field_smooth': 1.0, 'desc': 'sharp, dense, fine detail'},
}

WORK_MAX = 1200        # FMM working resolution (longest side)
MIN_CONTOUR_PX = 14    # discard contours shorter than this (working px)
SIMPLIFY_TOL = 0.6     # Douglas-Peucker tolerance (working px)
STROKE_W = 1.0         # stroke width (working px, scaled to output)
INK = 'rgb(49,43,43)'


def _polyline_length(pts: np.ndarray) -> float:
    return float(np.sum(np.hypot(np.diff(pts[:, 0]), np.diff(pts[:, 1]))))


def _catmull_path(pts: np.ndarray, scale: float) -> str:
    """Catmull-Rom spline through pts ((y, x) rows), emitted as SVG cubic Béziers.

    Closed contours (first point == last point) are wrapped periodically and
    closed with Z so there is no visible seam.
    """
    closed = bool(np.allclose(pts[0], pts[-1])) and len(pts) > 3
    if closed:
        pts = pts[:-1]
    n = len(pts)

    def fmt(v: float) -> str:
        return f'{v * scale:.1f}'

    def P(i: int) -> np.ndarray:
        if closed:
            return pts[i % n]
        return pts[min(max(i, 0), n - 1)]

    if n < 3:
        d = f'M{fmt(pts[0][1])} {fmt(pts[0][0])}'
        for p in pts[1:]:
            d += f' L{fmt(p[1])} {fmt(p[0])}'
        return d

    d = f'M{fmt(pts[0][1])} {fmt(pts[0][0])}'
    last = n if closed else n - 1
    for i in range(last):
        p0, p1, p2, p3 = P(i - 1), P(i), P(i + 1), P(i + 2)
        c1 = p1 + (p2 - p0) / 6.0
        c2 = p2 - (p3 - p1) / 6.0
        d += (f' C{fmt(c1[1])} {fmt(c1[0])} {fmt(c2[1])} {fmt(c2[0])}'
              f' {fmt(p2[1])} {fmt(p2[0])}')
    if closed:
        d += ' Z'
    return d


def _emit_svg(paths: list, scale: float, out_w: int, out_h: int) -> str:
    body = '\n'.join(f'<path d="{_catmull_path(p, scale)}"/>' for p in paths)
    stroke = STROKE_W * scale
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg width="{out_w}px" height="{out_h}px" viewBox="0 0 {out_w} {out_h}" '
        'xmlns="http://www.w3.org/2000/svg">\n'
        f'<!-- style: contours (FMM) | shapes: {len(paths)} -->\n'
        f'<g style="fill:none;stroke:{INK};stroke-width:{stroke:.2f};'
        'stroke-linecap:round;stroke-linejoin:round;">\n'
        f'{body}\n</g>\n</svg>'
    )


def process_image(image_bytes: bytes, preset_id: str) -> str:
    p = PRESETS[preset_id]

    raw = skio.imread(io.BytesIO(image_bytes), as_gray=True).astype(np.float64)
    orig_h, orig_w = raw.shape

    r = min(1.0, WORK_MAX / max(orig_h, orig_w))
    if r < 1.0:
        image = resize(raw, (round(orig_h * r), round(orig_w * r)), anti_aliasing=True)
    else:
        image = raw.copy()

    image = gaussian(image, sigma=p['blur'] * min(image.shape))
    mean = image.mean()
    image = mean + (image - mean) * p['contrast']
    image = np.clip(image + p['brightness'], 0, 1)
    if p['gamma'] != 1.0:
        image = np.clip(image, 0, 1) ** (1 / p['gamma'])

    # Travel time from centre seed; clamp speed away from 0 so no region
    # becomes unreachable (which previously created blown-out pockets).
    speed = np.clip(image, 0.02, 1.0)
    phi = np.ones_like(image)
    phi[image.shape[0] // 2, image.shape[1] // 2] = 0
    T = np.asarray(skfmm.travel_time(phi, speed))

    # Smoothing the field is what makes the lines calm and flowing.
    T = gaussian(T, sigma=p['field_smooth'])

    finite = T[np.isfinite(T)]
    lo = float(finite.min())
    hi = float(np.percentile(finite, 99.5))
    if hi <= lo:
        hi = float(finite.max())
    levels = np.linspace(lo, hi, int(p['levels']))[1:]

    h, w = image.shape
    scale = orig_w / w

    paths = []
    for lv in levels:
        for contour in find_contours(T, lv):
            if _polyline_length(contour) < MIN_CONTOUR_PX:
                continue
            simplified = approximate_polygon(contour, tolerance=SIMPLIFY_TOL)
            if len(simplified) < 2:
                continue
            paths.append(simplified)

    return _emit_svg(paths, scale, orig_w, orig_h)
