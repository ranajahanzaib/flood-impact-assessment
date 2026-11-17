from typing import Any

import numpy as np
import rasterio
from pyproj import CRS, Transformer

from geospatial.flood.permanent import (
    CLASS_NEW_INUNDATION,
    CLASS_NODATA,
    CLASS_PERMANENT_WATER,
    CLASS_RECEDED_WATER,
)


def compute_raster_pixel_area_m2(transform: rasterio.Affine, crs_str: str, bounds: list[float]) -> float:
    """
    Computes true ground surface area per pixel in square meters.
    If CRS is projected in meters, simply dx * dy.
    If CRS is geographic (degrees), reprojects center cell to equal-area projection.
    """
    crs = CRS.from_string(crs_str)
    dx = abs(transform.a)
    dy = abs(transform.e)

    if crs.is_projected:
        return float(dx * dy)

    # For geographic CRS (e.g., EPSG:4326), compute metric area at the bounding box centroid
    min_lon, min_lat, max_lon, max_lat = bounds
    center_lon = (min_lon + max_lon) / 2.0
    center_lat = (min_lat + max_lat) / 2.0

    # Project a 1-pixel box centered at the centroid to EPSG:6933 (Equal Area)
    transformer = Transformer.from_crs(crs, "EPSG:6933", always_xy=True)
    x0, y0 = transformer.transform(center_lon - dx / 2.0, center_lat - dy / 2.0)
    x1, y1 = transformer.transform(center_lon + dx / 2.0, center_lat + dy / 2.0)
    pixel_area = abs(x1 - x0) * abs(y1 - y0)
    return float(pixel_area)

def calculate_impact_areas(
    classification_raster: np.ndarray,
    transform: rasterio.Affine,
    crs_str: str,
    bounds: list[float],
    uncertainty_mask: np.ndarray = None
) -> dict[str, Any]:
    """
    Calculates scientifically sound area metrics in m², hectares, and km².
    """
    pixel_area_m2 = compute_raster_pixel_area_m2(transform, crs_str, bounds)

    total_valid_pixels = int(np.sum(classification_raster != CLASS_NODATA))
    perm_pixels = int(np.sum(classification_raster == CLASS_PERMANENT_WATER))
    new_inundation_pixels = int(np.sum((classification_raster == CLASS_NEW_INUNDATION) | (classification_raster == CLASS_RECEDED_WATER)))
    receded_pixels = int(np.sum(classification_raster == CLASS_RECEDED_WATER))
    total_water_pixels = perm_pixels + new_inundation_pixels

    uncertain_pixels = int(np.sum(uncertainty_mask)) if uncertainty_mask is not None else 0

    return {
        "pixel_area_m2": pixel_area_m2,
        "total_valid_area_km2": (total_valid_pixels * pixel_area_m2) / 1e6,
        "total_water_m2": total_water_pixels * pixel_area_m2,
        "total_water_ha": (total_water_pixels * pixel_area_m2) / 10000.0,
        "total_water_km2": (total_water_pixels * pixel_area_m2) / 1e6,
        "preexisting_water_m2": perm_pixels * pixel_area_m2,
        "preexisting_water_ha": (perm_pixels * pixel_area_m2) / 10000.0,
        "preexisting_water_km2": (perm_pixels * pixel_area_m2) / 1e6,
        "newly_flooded_m2": new_inundation_pixels * pixel_area_m2,
        "newly_flooded_ha": (new_inundation_pixels * pixel_area_m2) / 10000.0,
        "newly_flooded_km2": (new_inundation_pixels * pixel_area_m2) / 1e6,
        "receded_m2": receded_pixels * pixel_area_m2,
        "receded_km2": (receded_pixels * pixel_area_m2) / 1e6,
        "uncertain_water_m2": uncertain_pixels * pixel_area_m2,
        "uncertain_water_km2": (uncertain_pixels * pixel_area_m2) / 1e6,
    }
