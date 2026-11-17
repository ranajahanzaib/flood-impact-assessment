import geopandas as gpd
import numpy as np
import rasterio
import shapely.geometry
from rasterio.features import shapes

from geospatial.flood.permanent import (
    CLASS_NEW_INUNDATION,
    CLASS_PERMANENT_WATER,
    CLASS_RECEDED_WATER,
)

CLASS_NAMES = {
    CLASS_PERMANENT_WATER: "preexisting_water",
    CLASS_NEW_INUNDATION: "new_inundation",
    CLASS_RECEDED_WATER: "receded_water",
}

def polygonize_flood_mask(
    classification_raster: np.ndarray,
    transform: rasterio.Affine,
    crs: str,
    min_area_m2: float = 100.0,
    target_classes: list[int] | None = None
) -> gpd.GeoDataFrame:
    """
    Converts a classified water raster into georeferenced vector polygons.
    Filters out sub-pixel speckle noise smaller than min_area_m2.
    """
    classes_to_extract = target_classes or [CLASS_PERMANENT_WATER, CLASS_NEW_INUNDATION, CLASS_RECEDED_WATER]
    mask = np.isin(classification_raster, classes_to_extract)

    features = []
    # rasterio.features.shapes extracts (geometry, value) pairs
    for geom_dict, val in shapes(classification_raster, mask=mask, transform=transform):
        val_int = int(val)
        if val_int in CLASS_NAMES:
            poly = shapely.geometry.shape(geom_dict)
            if poly.is_valid and not poly.is_empty:
                features.append({
                    "geometry": poly,
                    "class_code": val_int,
                    "class_name": CLASS_NAMES[val_int],
                })

    if not features:
        gdf = gpd.GeoDataFrame(
            columns=["geometry", "class_code", "class_name", "area_m2", "area_ha", "area_km2"],
            crs=crs
        )
        return gdf

    gdf = gpd.GeoDataFrame(features, crs=crs)

    # Reproject to an equal-area projection to compute accurate metric areas
    # Use UTM or standard equal-area EPSG:6933 / EPSG:3857 for local metrics
    if gdf.crs.is_geographic:
        # Reproject to World Cylindrical Equal Area (EPSG:6933) for metric calculation
        gdf_proj = gdf.to_crs(epsg=6933)
        area_m2 = gdf_proj.geometry.area
    else:
        area_m2 = gdf.geometry.area

    gdf["area_m2"] = area_m2
    gdf["area_ha"] = area_m2 / 10000.0
    gdf["area_km2"] = area_m2 / 1000000.0

    # Filter by minimum area threshold
    gdf = gdf[gdf["area_m2"] >= min_area_m2].reset_index(drop=True)
    return gdf
