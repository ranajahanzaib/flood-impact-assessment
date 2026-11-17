
import numpy as np
from scipy.ndimage import sobel


def compute_slope_degrees(dem: np.ndarray, cell_size_m: float = 10.0) -> np.ndarray:
    """
    Computes terrain slope in degrees using 3x3 Sobel gradient operator.
    """
    dem_f = dem.astype(np.float32)
    # Sobel filter approximates dx and dy across 8 grid cells
    dz_dx = sobel(dem_f, axis=1) / (8.0 * cell_size_m)
    dz_dy = sobel(dem_f, axis=0) / (8.0 * cell_size_m)

    slope_rad = np.arctan(np.sqrt(dz_dx ** 2 + dz_dy ** 2))
    slope_deg = np.degrees(slope_rad)
    return slope_deg

def apply_topographic_constraint(
    water_prob: np.ndarray,
    dem: np.ndarray,
    cell_size_m: float = 10.0,
    max_flood_slope_deg: float = 7.0
) -> tuple[np.ndarray, np.ndarray]:
    """
    Applies topographic physics constraints.
    Floodwaters do not stand statically on steep terrain.
    Attenuates water probability on slopes steeper than max_flood_slope_deg.
    """
    slope = compute_slope_degrees(dem, cell_size_m)
    # Attenuation factor: 1.0 on flat ground, scales smoothly to 0.0 on steep hillsides
    slope_attenuation = np.clip(1.0 - (slope - max_flood_slope_deg) / 5.0, 0.0, 1.0)

    constrained_prob = water_prob * slope_attenuation
    return constrained_prob, slope
