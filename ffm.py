import skfmm
import numpy as np
from skimage import io
from skimage.filters import gaussian
import matplotlib.pyplot as plt

image = io.imread('myimg.jpg', as_gray=True)  # Load image as grayscale
blur_sigma = 0.00275 * min(image.shape)  # 0.275% of the smallest dimension
image = gaussian(image, sigma=blur_sigma)
mean = image.mean()
image = mean + (image - mean) * 0.855  # Contrast
image = np.clip(image + 0.09, 0, 1)  # Brightness

phi = np.ones_like(image)  # Initialize the level set function
shape = phi.shape
phi[shape[0] // 2, shape[1] // 2] = 0  # set the image center as starting point
T = skfmm.travel_time(phi, image)  # Compute the travel time using the Fast Marching Method
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
plt.savefig('output.svg', bbox_inches='tight', pad_inches=0)
