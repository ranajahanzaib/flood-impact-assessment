from typing import Any

import numpy as np
import rasterio
import shapely.geometry
from rasterio.features import shapes


def compute_binary_entropy(prob: np.ndarray) -> np.ndarray:
    """
    Computes normalized Shannon entropy for binary probabilities.
    Range: [0, 1]. Maximum at prob=0.5 (maximum uncertainty).
    """
    p = np.clip(prob, 1e-6, 1.0 - 1e-6)
    entropy = - (p * np.log2(p) + (1.0 - p) * np.log2(1.0 - p))
    return np.clip(entropy, 0.0, 1.0)

def detect_sensor_disagreement(
    s1_water_prob: np.ndarray,
    s2_water_prob: np.ndarray,
    s2_valid_mask: np.ndarray,
    disagreement_threshold: float = 0.4
) -> tuple[np.ndarray, np.ndarray]:
    """
    Identifies regions where Sentinel-1 SAR and Sentinel-2 optical disagree.
    e.g. S1 radar suggests water while S2 optical suggests dry land (or vice versa).
    """
    # Only evaluate disagreement where optical is not cloud-obscured
    disagreement_magnitude = np.abs(s1_water_prob - s2_water_prob)
    disagreement_magnitude[~s2_valid_mask] = 0.0

    has_disagreement = (disagreement_magnitude >= disagreement_threshold) & s2_valid_mask
    return disagreement_magnitude, has_disagreement

def build_composite_uncertainty(
    water_prob: np.ndarray,
    valid_mask: np.ndarray,
    sensor_disagreement: np.ndarray | None = None,
    observation_gap_mask: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """
    Builds composite uncertainty raster combining:
    - Model prediction entropy (high near threshold 0.5)
    - Observation validity (cloud / no-data)
    - Multi-sensor disagreement
    - Temporal observation gaps
    
    Returns:
        (uncertainty_raster, high_uncertainty_mask):
        uncertainty_raster: float array in [0, 1]
        high_uncertainty_mask: boolean array (uncertainty >= 0.6)
    """
    # 1. Model prediction entropy
    entropy = compute_binary_entropy(water_prob)

    # 2. Start composite
    uncertainty = 0.5 * entropy

    # 3. Incorporate sensor disagreement
    if sensor_disagreement is not None:
        uncertainty = np.maximum(uncertainty, sensor_disagreement)

    # 4. Observation gaps add moderate uncertainty
    if observation_gap_mask is not None:
        uncertainty = np.where(observation_gap_mask, np.maximum(uncertainty, 0.6), uncertainty)

    # 5. Invalid / cloud-contaminated pixels have maximum uncertainty (1.0)
    uncertainty[~valid_mask] = 1.0

    high_uncertainty_mask = uncertainty >= 0.6
    return uncertainty.astype(np.float32), high_uncertainty_mask

def extract_manual_review_regions(
    uncertainty_raster: np.ndarray,
    transform: rasterio.Affine,
    crs: str,
    sensor_disagreement_mask: np.ndarray | None = None,
    min_pixels: int = 16
) -> list[dict[str, Any]]:
    """
    Extracts contiguous spatial clusters requiring manual review by human analyst.
    """
    flag_mask = (uncertainty_raster >= 0.65)
    if not np.any(flag_mask):
        return []

    review_regions = []
    for geom_dict, val in shapes(flag_mask.astype(np.uint8), mask=flag_mask, transform=transform):
        poly = shapely.geometry.shape(geom_dict)
        if poly.is_valid and not poly.is_empty:
            # Estimate pixel count by bounding box area / pixel area
            pixel_area = abs(transform.a * transform.e)
            est_pixels = poly.area / pixel_area
            if est_pixels >= min_pixels:
                # Determine reason
                reason = "High prediction entropy and classification uncertainty"
                flag_type = "high_entropy"

                # Check if sensor disagreement intersects
                review_regions.append({
                    "geometry": shapely.geometry.mapping(poly),
                    "flag_type": flag_type,
                    "reason": reason,
                    "estimated_pixels": int(est_pixels),
                })

    return review_regions
