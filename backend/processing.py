import io

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import skfmm
from skimage import io as skio
from skimage.filters import gaussian

PRESETS = {
    'A': {'blur': 0.00275, 'contrast': 0.85, 'brightness': 0.10, 'gamma': 1.0, 'desc': 'Current settings'},
    'B': {'blur': 0.00275, 'contrast': 0.95, 'brightness': 0.05, 'gamma': 1.0, 'desc': 'More contrast, less bright'},
    'C': {'blur': 0.00275, 'contrast': 0.75, 'brightness': 0.15, 'gamma': 1.0, 'desc': 'Less contrast, brighter'},
    'D': {'blur': 0.00275, 'contrast': 0.85, 'brightness': 0.10, 'gamma': 0.85, 'desc': 'With gamma darkening'},
    'E': {'blur': 0.00400, 'contrast': 0.80, 'brightness': 0.10, 'gamma': 1.0, 'desc': 'More blur, less contrast'},
    'F': {'blur': 0.00200, 'contrast': 0.90, 'brightness': 0.05, 'gamma': 1.0, 'desc': 'Less blur, subtle processing'},
}


def process_image(image_bytes: bytes, preset_id: str) -> str:
    p = PRESETS[preset_id]

    raw = skio.imread(io.BytesIO(image_bytes), as_gray=True)
    image = raw.copy()
    image = gaussian(image, sigma=p['blur'] * min(image.shape))

    mean = image.mean()
    image = mean + (image - mean) * p['contrast']
    image = np.clip(image + p['brightness'], 0, 1)

    if p['gamma'] != 1.0:
        image = np.clip(image, 0, 1) ** (1 / p['gamma'])

    phi = np.ones_like(image)
    shape = phi.shape
    phi[shape[0] // 2, shape[1] // 2] = 0
    T = skfmm.travel_time(phi, image)

    finite_T_values = T[np.isfinite(T)]
    min_T_actual = np.min(finite_T_values)
    max_T_actual = np.max(finite_T_values)
    sensible_max_T = np.percentile(finite_T_values, 99.99)
    if sensible_max_T <= min_T_actual:
        sensible_max_T = max_T_actual
    contour_levels = np.linspace(min_T_actual, sensible_max_T, 300)

    h, w = image.shape
    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)
    ax.contour(T, levels=contour_levels, colors='black')
    ax.invert_yaxis()
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_xlim(0, w - 1)
    ax.set_ylim(h - 1, 0)

    svg_buffer = io.BytesIO()
    plt.savefig(svg_buffer, format='svg', bbox_inches='tight', pad_inches=0)
    plt.close(fig)

    svg_buffer.seek(0)
    return svg_buffer.read().decode('utf-8')
