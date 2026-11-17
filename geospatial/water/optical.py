import numpy as np


def compute_ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """
    Normalized Difference Water Index (McFeeters, 1996):
    NDWI = (Green - NIR) / (Green + NIR)
    """
    numerator = green.astype(np.float32) - nir.astype(np.float32)
    denominator = green.astype(np.float32) + nir.astype(np.float32) + 1e-7
    ndwi = numerator / denominator
    return np.clip(ndwi, -1.0, 1.0)

def compute_mndwi(green: np.ndarray, swir: np.ndarray) -> np.ndarray:
    """
    Modified Normalized Difference Water Index (Xu, 2006):
    MNDWI = (Green - SWIR) / (Green + SWIR)
    More effective than NDWI in urban and built-up areas.
    """
    numerator = green.astype(np.float32) - swir.astype(np.float32)
    denominator = green.astype(np.float32) + swir.astype(np.float32) + 1e-7
    mndwi = numerator / denominator
    return np.clip(mndwi, -1.0, 1.0)

def detect_clouds_and_shadows(
    blue: np.ndarray,
    green: np.ndarray,
    red: np.ndarray,
    nir: np.ndarray,
    swir: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """
    Heuristic cloud and shadow mask when Scene Classification Layer (SCL) is absent.
    Clouds: High reflectance across all visible bands and SWIR.
    Shadows: Low reflectance across all bands, especially NIR.
    """
    # Scale to 0-1 if in 0-10000 range
    scale = 10000.0 if np.nanmax(green) > 2.0 else 1.0
    b = blue / scale
    g = green / scale
    r = red / scale
    n = nir / scale

    # Clouds are bright in visible wavelengths
    cloud_brightness = (b + g + r) / 3.0
    cloud_mask = cloud_brightness > 0.35

    # Cloud shadow
    shadow_mask = (n < 0.08) & (g < 0.08) & (r < 0.08)

    return cloud_mask, shadow_mask

def detect_water_s2(
    green: np.ndarray,
    nir: np.ndarray,
    swir: np.ndarray | None = None,
    blue: np.ndarray | None = None,
    red: np.ndarray | None = None,
    ndwi_threshold: float = 0.0,
    mndwi_threshold: float = 0.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Detects water in Sentinel-2 optical imagery.
    
    Returns:
        (water_prob, water_mask, validity_mask):
        water_prob: float array in [0, 1]
        water_mask: boolean array (True = water)
        validity_mask: boolean array (False = cloud / shadow / obscured)
    """
    ndwi = compute_ndwi(green, nir)

    if swir is not None:
        mndwi = compute_mndwi(green, swir)
        # Combined index gives strong water signal
        index_val = 0.4 * ndwi + 0.6 * mndwi
        threshold = 0.4 * ndwi_threshold + 0.6 * mndwi_threshold
    else:
        index_val = ndwi
        threshold = ndwi_threshold

    # Sigmoidal mapping to probability
    scale = 0.15
    water_prob = 1.0 / (1.0 + np.exp(-(index_val - threshold) / scale))

    # Cloud and shadow masking
    if blue is not None and red is not None:
        cloud_mask, shadow_mask = detect_clouds_and_shadows(blue, green, red, nir, swir)
        obscured_mask = cloud_mask | shadow_mask
        validity_mask = ~obscured_mask
        # Cloud/shadow areas should NOT be treated as confident dry land!
        water_prob[obscured_mask] = 0.5  # maximum uncertainty
    else:
        validity_mask = np.ones_like(water_prob, dtype=bool)

    water_mask = (water_prob >= 0.5) & validity_mask
    return water_prob, water_mask, validity_mask
