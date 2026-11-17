from typing import Any

import geopandas as gpd
import numpy as np


def analyze_building_impact(
    buildings_gdf: gpd.GeoDataFrame,
    flood_gdf: gpd.GeoDataFrame,
    uncertainty_gdf: gpd.GeoDataFrame = None
) -> tuple[gpd.GeoDataFrame, dict[str, Any]]:
    """
    Overlays building footprints with flood inundation polygons.
    Computes exact intersection area and percentage for each building.
    
    Terminology: 'potentially affected buildings' (not 'damaged' or 'destroyed').
    """
    if buildings_gdf.empty or flood_gdf.empty:
        empty_res = buildings_gdf.copy()
        empty_res["affected"] = False
        empty_res["intersect_area_m2"] = 0.0
        empty_res["intersect_pct"] = 0.0
        empty_res["is_uncertain"] = False
        return empty_res, {
            "total_buildings": len(buildings_gdf),
            "affected_buildings": 0,
            "uncertain_buildings": 0,
            "mean_intersection_pct": 0.0,
        }

    # Ensure consistent projection
    if buildings_gdf.crs != flood_gdf.crs:
        buildings_gdf = buildings_gdf.to_crs(flood_gdf.crs)

    # Convert to equal-area projection for metric calculations
    target_crs = flood_gdf.crs
    if target_crs.is_geographic:
        b_proj = buildings_gdf.to_crs(epsg=6933)
        f_proj = flood_gdf.to_crs(epsg=6933)
    else:
        b_proj = buildings_gdf.copy()
        f_proj = flood_gdf.copy()

    # Calculate original building footprint area
    b_proj["building_area_m2"] = b_proj.geometry.area

    # Union all candidate new inundation polygons to prevent double-counting across overlapping polygons
    flood_union = f_proj.unary_union

    # Intersect
    b_proj["intersect_geom"] = b_proj.geometry.intersection(flood_union)
    b_proj["intersect_area_m2"] = b_proj["intersect_geom"].area
    b_proj["intersect_pct"] = (b_proj["intersect_area_m2"] / np.maximum(b_proj["building_area_m2"], 1e-6)) * 100.0
    b_proj["intersect_pct"] = np.clip(b_proj["intersect_pct"], 0.0, 100.0)

    # Any building with > 5% footprint intersection is counted as potentially affected
    b_proj["affected"] = b_proj["intersect_pct"] >= 5.0

    # Uncertainty check
    b_proj["is_uncertain"] = False
    if uncertainty_gdf is not None and not uncertainty_gdf.empty:
        u_proj = uncertainty_gdf.to_crs(b_proj.crs)
        u_union = u_proj.unary_union
        b_proj["is_uncertain"] = b_proj.geometry.intersects(u_union) & b_proj["affected"]

    affected_count = int(b_proj["affected"].sum())
    uncertain_count = int(b_proj["is_uncertain"].sum())
    mean_pct = float(b_proj[b_proj["affected"]]["intersect_pct"].mean()) if affected_count > 0 else 0.0

    # Prepare return GDF in original CRS
    result_gdf = buildings_gdf.copy()
    result_gdf["affected"] = b_proj["affected"].values
    result_gdf["intersect_area_m2"] = b_proj["intersect_area_m2"].values
    result_gdf["intersect_pct"] = b_proj["intersect_pct"].values
    result_gdf["is_uncertain"] = b_proj["is_uncertain"].values

    stats = {
        "total_buildings": len(buildings_gdf),
        "affected_buildings": affected_count,
        "uncertain_buildings": uncertain_count,
        "mean_intersection_pct": round(mean_pct, 2)
    }

    return result_gdf, stats


def analyze_road_impact(
    roads_gdf: gpd.GeoDataFrame,
    flood_gdf: gpd.GeoDataFrame,
    uncertainty_gdf: gpd.GeoDataFrame = None
) -> tuple[gpd.GeoDataFrame, dict[str, Any]]:
    """
    Overlays road networks with flood inundation polygons.
    Splits line features to compute the exact inundated road length in meters.
    """
    if roads_gdf.empty or flood_gdf.empty:
        empty_res = roads_gdf.copy()
        empty_res["inundated_length_m"] = 0.0
        empty_res["inundated_pct"] = 0.0
        empty_res["is_affected"] = False
        return empty_res, {
            "total_road_meters": 0.0,
            "total_road_km": 0.0,
            "affected_road_meters": 0.0,
            "affected_road_km": 0.0,
            "affected_pct": 0.0,
            "affected_segments_count": 0
        }

    # Project to metric equal area
    if roads_gdf.crs.is_geographic:
        r_proj = roads_gdf.to_crs(epsg=6933)
        f_proj = flood_gdf.to_crs(epsg=6933)
    else:
        r_proj = roads_gdf.copy()
        f_proj = flood_gdf.to_crs(roads_gdf.crs)

    r_proj["total_length_m"] = r_proj.geometry.length
    flood_union = f_proj.unary_union

    # Intersect line geometries with the flood polygon union
    r_proj["intersect_geom"] = r_proj.geometry.intersection(flood_union)
    r_proj["inundated_length_m"] = r_proj["intersect_geom"].length
    r_proj["inundated_pct"] = (r_proj["inundated_length_m"] / np.maximum(r_proj["total_length_m"], 1e-6)) * 100.0
    r_proj["is_affected"] = r_proj["inundated_length_m"] > 5.0  # at least 5 meters inundated

    total_meters = float(r_proj["total_length_m"].sum())
    affected_meters = float(r_proj["inundated_length_m"].sum())
    affected_segments = int(r_proj["is_affected"].sum())

    result_gdf = roads_gdf.copy()
    result_gdf["inundated_length_m"] = r_proj["inundated_length_m"].values
    result_gdf["inundated_pct"] = r_proj["inundated_pct"].values
    result_gdf["is_affected"] = r_proj["is_affected"].values

    stats = {
        "total_road_meters": round(total_meters, 1),
        "total_road_km": round(total_meters / 1000.0, 2),
        "affected_road_meters": round(affected_meters, 1),
        "affected_road_km": round(affected_meters / 1000.0, 2),
        "affected_pct": round((affected_meters / max(total_meters, 1e-6)) * 100.0, 2),
        "affected_segments_count": affected_segments
    }

    return result_gdf, stats
