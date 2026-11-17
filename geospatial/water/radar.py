
import numpy as np
from scipy.ndimage import uniform_filter


def apply_lee_filter(img: np.ndarray, size: int = 5) -> np.ndarray:
    """
    Applies Lee speckle filter on SAR radar imagery.
    """
    img_mean = uniform_filter(img, (size, size))
    img_sqr_mean = uniform_filter(img ** 2, (size, size))
    img_variance = np.maximum(img_sqr_mean - img_mean ** 2, 0)

    overall_variance = np.var(img)
    weights = img_variance / (img_variance + overall_variance + 1e-8)
    return img_mean + weights * (img - img_mean)

def to_decibels(linear_data: np.ndarray) -> np.ndarray:
    """
    Converts linear amplitude / intensity to decibels (dB).
    """
    safe_data = np.clip(linear_data, 1e-7, None)
    return 10.0 * np.log10(safe_data)

def detect_water_s1(
    vv_band: np.ndarray,
    vh_band: np.ndarray | None = None,
    vv_threshold_db: float = -15.0,
    vh_threshold_db: float = -22.0,
    pre_vv_band: np.ndarray | None = None,
    filter_speckle: bool = True
) -> tuple[np.ndarray, np.ndarray]:
    """
    Detects water in Sentinel-1 SAR imagery.
    Water shows specular reflection causing low backscatter.
    
    Returns:
        (water_prob, water_mask):
        water_prob: float array in [0, 1] representing inundation probability
        water_mask: boolean array where True is detected water
    """
    # Ensure inputs in dB scale
    # If mean is positive (e.g. > 100), assume linear digital numbers and convert
    vv_db = vv_band.copy().astype(np.float32)
    if np.nanmean(vv_db) > 1.0:
        vv_db = to_decibels(vv_db)

    if filter_speckle:
        vv_db = apply_lee_filter(vv_db)

    # Sigmoidal mapping centered around threshold
    # Backscatter lower than threshold gives higher water probability
    scale = 2.0
    prob_vv = 1.0 / (1.0 + np.exp((vv_db - vv_threshold_db) / scale))

    if vh_band is not None:
        vh_db = vh_band.copy().astype(np.float32)
        if np.nanmean(vh_db) > 1.0:
            vh_db = to_decibels(vh_db)
        if filter_speckle:
            vh_db = apply_lee_filter(vh_db)
        prob_vh = 1.0 / (1.0 + np.exp((vh_db - vh_threshold_db) / scale))
        # Combined probability (weighted ensemble)
        water_prob = 0.6 * prob_vv + 0.4 * prob_vh
    else:
        water_prob = prob_vv

    # If pre-event observation is available, incorporate backscatter drop
    if pre_vv_band is not None:
        pre_db = pre_vv_band.copy().astype(np.float32)
        if np.nanmean(pre_db) > 1.0:
            pre_db = to_decibels(pre_db)
        if filter_speckle:
            pre_db = apply_lee_filter(pre_db)

        # Inundation causes significant drop in backscatter
        delta_db = pre_db - vv_db  # positive if backscatter dropped
        change_boost = np.clip(delta_db / 6.0, 0.0, 1.0)
        water_prob = np.clip(water_prob * 0.7 + change_boost * 0.3, 0.0, 1.0)

    water_mask = water_prob >= 0.5
    return water_prob, water_mask
