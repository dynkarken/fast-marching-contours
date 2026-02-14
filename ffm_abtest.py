import os
import skfmm
import numpy as np
from skimage import io
from skimage.filters import gaussian
import matplotlib.pyplot as plt

PRESETS = {
    'A': {'blur': 0.00275, 'contrast': 0.85, 'brightness': 0.10, 'gamma': 1.0, 'desc': 'Current settings'},
    'B': {'blur': 0.00275, 'contrast': 0.95, 'brightness': 0.05, 'gamma': 1.0, 'desc': 'More contrast, less bright'},
    'C': {'blur': 0.00275, 'contrast': 0.75, 'brightness': 0.15, 'gamma': 1.0, 'desc': 'Less contrast, brighter'},
    'D': {'blur': 0.00275, 'contrast': 0.85, 'brightness': 0.10, 'gamma': 0.85, 'desc': 'With gamma darkening'},
    'E': {'blur': 0.00400, 'contrast': 0.80, 'brightness': 0.10, 'gamma': 1.0, 'desc': 'More blur, less contrast'},
    'F': {'blur': 0.00200, 'contrast': 0.90, 'brightness': 0.05, 'gamma': 1.0, 'desc': 'Less blur, subtle processing'},
}

IMAGE_DIR = '/Users/jms/Desktop/portraits'
OUTPUT_DIR = '/Users/jms/Desktop/test_outputs'

images = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
total = len(images) * len(PRESETS)
count = 0

for img_name in sorted(images):
    img_path = os.path.join(IMAGE_DIR, img_name)
    base_name = os.path.splitext(img_name)[0]

    raw = io.imread(img_path, as_gray=True)

    for preset_id, p in PRESETS.items():
        count += 1
        print(f'[{count}/{total}] {base_name} — Preset {preset_id} ({p["desc"]})')

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

        out_path = os.path.join(OUTPUT_DIR, f'{base_name}_{preset_id}.svg')
        plt.savefig(out_path, bbox_inches='tight', pad_inches=0)
        plt.close(fig)

print(f'\nDone! {count} SVGs saved to {OUTPUT_DIR}')
