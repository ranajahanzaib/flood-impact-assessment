import geopandas as gpd
import numpy as np
import pytest
import shapely.geometry
from rasterio.transform import from_origin

from geospatial.flood.extent import polygonize_flood_mask
from geospatial.flood.permanent import (
    CLASS_NEW_INUNDATION,
    CLASS_NO_WATER,
    CLASS_NODATA,
    CLASS_PERMANENT_WATER,
    CLASS_RECEDED_WATER,
    separate_permanent_and_flood_water,
)
from geospatial.flood.persistence import calculate_temporal_persistence
from geospatial.infrastructure.intersection import analyze_building_impact, analyze_road_impact
from geospatial.metrics.area import calculate_impact_areas
from geospatial.uncertainty.signals import (
    build_composite_uncertainty,
    detect_sensor_disagreement,
)
from geospatial.water.optical import compute_ndwi, detect_water_s2
from geospatial.water.radar import detect_water_s1


def test_s1_radar_water_detection():
    # Synthetic radar backscatter scene
    # High backscatter = land (~ -8 dB)
    # Low specular backscatter = water (~ -20 dB)
    vv = np.full((50, 50), -8.0, dtype=np.float32)
    vv[10:30, 10:30] = -22.0  # water pond

    prob, mask = detect_water_s1(vv, vv_threshold_db=-15.0, filter_speckle=True)
    assert prob.shape == (50, 50)
    assert mask.shape == (50, 50)
    assert np.all(mask[10:30, 10:30] == True)
    assert np.all(mask[0:5, 0:5] == False)
    assert prob[20, 20] > 0.8
    assert prob[0, 0] < 0.2

def test_s2_optical_water_indices():
    # Green and NIR bands
    green = np.full((20, 20), 0.2, dtype=np.float32)
    nir = np.full((20, 20), 0.4, dtype=np.float32)

    # Water has high green reflectance and low NIR absorption
    green[5:15, 5:15] = 0.35
    nir[5:15, 5:15] = 0.05

    ndwi = compute_ndwi(green, nir)
    assert np.all(ndwi[5:15, 5:15] > 0.4)  # Strong water signal
    assert np.all(ndwi[0:4, 0:4] < 0.0)    # Vegetation / soil signal

    prob, mask, valid = detect_water_s2(green, nir, ndwi_threshold=0.0)
    assert np.all(mask[5:15, 5:15] == True)
    assert np.all(mask[0:4, 0:4] == False)

def test_permanent_vs_newly_flooded_separation():
    # Grid: 40x40
    # Region 1 (10:20, 10:20): Pre-existing permanent lake (water before AND during)
    # Region 2 (25:35, 25:35): Newly inundated flood (dry before, water during, dry after)
    # Region 3 (0:10, 0:10): Never flooded
    # Region 4 (30:40, 0:10): Cloud obscured during event (invalid)

    pre_water = np.zeros((40, 40), dtype=bool)
    pre_water[10:20, 10:20] = True
    pre_valid = np.ones((40, 40), dtype=bool)

    during_water = np.zeros((40, 40), dtype=bool)
    during_water[10:20, 10:20] = True  # permanent lake still water
    during_water[25:35, 25:35] = True  # new flood extent

    during_valid = np.ones((40, 40), dtype=bool)
    during_valid[30:40, 0:10] = False  # cloud obscured

    post_water = np.zeros((40, 40), dtype=bool)
    post_water[10:20, 10:20] = True  # permanent lake remains
    post_valid = np.ones((40, 40), dtype=bool)

    class_raster, new_inundation = separate_permanent_and_flood_water(
        pre_water_mask=pre_water,
        pre_valid_mask=pre_valid,
        during_water_mask=during_water,
        during_valid_mask=during_valid,
        post_water_mask=post_water,
        post_valid_mask=post_valid
    )

    # Permanent lake must be classified as CLASS_PERMANENT_WATER
    assert np.all(class_raster[10:20, 10:20] == CLASS_PERMANENT_WATER)
    assert not np.any(new_inundation[10:20, 10:20])

    # Newly flooded land that later receded must be CLASS_RECEDED_WATER
    assert np.all(class_raster[25:35, 25:35] == CLASS_RECEDED_WATER)
    assert np.all(new_inundation[25:35, 25:35] == True)

    # Cloud obscured region must be CLASS_NODATA
    assert np.all(class_raster[30:40, 0:10] == CLASS_NODATA)

    # Unflooded land must be CLASS_NO_WATER
    assert np.all(class_raster[0:5, 15:25] == CLASS_NO_WATER)

def test_temporal_persistence():
    obs1 = np.zeros((20, 20), dtype=bool)
    obs1[5:15, 5:15] = True
    obs2 = np.zeros((20, 20), dtype=bool)
    obs2[5:15, 5:15] = True
    obs3 = np.zeros((20, 20), dtype=bool)
    obs3[5:10, 5:15] = True  # receded in lower half

    valid = [np.ones((20, 20), dtype=bool)] * 3
    res = calculate_temporal_persistence([obs1, obs2, obs3], valid, ["t1", "t2", "t3"])

    # Upper half flooded in all 3 obs -> persistence ratio = 1.0
    assert np.allclose(res["persistence_ratio"][5:10, 5:15], 1.0)
    # Lower half flooded in 2 of 3 obs -> persistence ratio = 2/3 ~ 0.667
    assert np.allclose(res["persistence_ratio"][10:15, 5:15], 2.0 / 3.0, atol=1e-3)
    # Unflooded area -> 0.0
    assert np.all(res["persistence_ratio"][0:4, 0:4] == 0.0)

def test_polygonization_and_area_metrics():
    # Raster transform: 10m pixel size in projected coordinates
    transform = from_origin(500000, 4000000, 10, 10)
    crs = "EPSG:32632"  # UTM Zone 32N in meters

    class_raster = np.zeros((100, 100), dtype=np.uint8)
    # 20x20 pixel square of newly inundated land = 400 pixels * 100 m² = 40,000 m² = 4 ha = 0.04 km²
    class_raster[20:40, 20:40] = CLASS_NEW_INUNDATION

    gdf = polygonize_flood_mask(class_raster, transform, crs, min_area_m2=100.0)
    assert not gdf.empty
    assert len(gdf) == 1
    assert gdf.iloc[0]["class_name"] == "new_inundation"
    assert pytest.approx(gdf.iloc[0]["area_m2"], rel=1e-2) == 40000.0
    assert pytest.approx(gdf.iloc[0]["area_ha"], rel=1e-2) == 4.0
    assert pytest.approx(gdf.iloc[0]["area_km2"], rel=1e-2) == 0.04

    # Calculate impact areas
    metrics = calculate_impact_areas(
        class_raster, transform, crs, [500000, 3999000, 501000, 4000000]
    )
    assert pytest.approx(metrics["newly_flooded_m2"], rel=1e-2) == 40000.0
    assert pytest.approx(metrics["newly_flooded_km2"], rel=1e-2) == 0.04

def test_infrastructure_impact_intersections():
    # Create synthetic flood polygon: (0, 0) to (100, 100) in meters
    flood_poly = shapely.geometry.box(0, 0, 100, 100)
    flood_gdf = gpd.GeoDataFrame(
        [{"geometry": flood_poly, "class_name": "new_inundation"}],
        crs="EPSG:3857"
    )

    # Building 1: Fully inside flood polygon (50% to 100% inundated)
    b1 = shapely.geometry.box(10, 10, 30, 30) # 20x20 = 400 m²
    # Building 2: Outside flood polygon
    b2 = shapely.geometry.box(200, 200, 220, 220)
    # Building 3: Partial intersection (half inside, half outside)
    b3 = shapely.geometry.box(90, 10, 110, 30)

    buildings_gdf = gpd.GeoDataFrame([
        {"id": "b1", "geometry": b1},
        {"id": "b2", "geometry": b2},
        {"id": "b3", "geometry": b3},
    ], crs="EPSG:3857")

    res_bldg, stats_b = analyze_building_impact(buildings_gdf, flood_gdf)
    assert stats_b["total_buildings"] == 3
    assert stats_b["affected_buildings"] == 2  # b1 and b3
    assert res_bldg.loc[res_bldg["id"] == "b1", "intersect_pct"].values[0] == 100.0
    assert res_bldg.loc[res_bldg["id"] == "b2", "affected"].values[0] == False
    assert pytest.approx(res_bldg.loc[res_bldg["id"] == "b3", "intersect_pct"].values[0], rel=1e-2) == 50.0

    # Road 1: Line crossing flood polygon (total 200m, 100m inundated)
    r1 = shapely.geometry.LineString([(-50, 50), (150, 50)])
    # Road 2: Outside flood
    r2 = shapely.geometry.LineString([(200, 50), (300, 50)])

    roads_gdf = gpd.GeoDataFrame([
        {"id": "r1", "geometry": r1},
        {"id": "r2", "geometry": r2},
    ], crs="EPSG:3857")

    res_roads, stats_r = analyze_road_impact(roads_gdf, flood_gdf)
    assert stats_r["affected_segments_count"] == 1
    assert pytest.approx(stats_r["affected_road_meters"], rel=1e-2) == 100.0
    assert pytest.approx(res_roads.loc[res_roads["id"] == "r1", "inundated_length_m"].values[0], rel=1e-2) == 100.0

def test_uncertainty_and_sensor_disagreement():
    # S1 detects water (prob = 0.9), S2 detects dry land (prob = 0.1)
    s1_prob = np.full((10, 10), 0.9, dtype=np.float32)
    s2_prob = np.full((10, 10), 0.1, dtype=np.float32)
    s2_valid = np.ones((10, 10), dtype=bool)

    disagree_mag, has_disagree = detect_sensor_disagreement(s1_prob, s2_prob, s2_valid)
    assert np.all(has_disagree == True)
    assert np.allclose(disagree_mag, 0.8, atol=1e-3)

    uncert_raster, high_uncert = build_composite_uncertainty(
        water_prob=s1_prob,
        valid_mask=s2_valid,
        sensor_disagreement=disagree_mag
    )
    assert np.all(high_uncert == True)
    assert np.allclose(uncert_raster, 0.8, atol=1e-3)
