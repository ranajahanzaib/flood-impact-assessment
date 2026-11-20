import datetime
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely.geometry
from rasterio.transform import from_origin

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from geospatial.raster.cog import write_cog
from ml.datasets.impactmesh import SAMPLE_EVENTS
from services.api.config import settings
from services.api.database import SessionLocal, init_db
from services.api.models import (
    AnalysisRun,
    FloodEvent,
    GeospatialOutput,
    ImpactMetrics,
    InfrastructureDataset,
    Observation,
)
from services.worker.pipelines.analysis_pipeline import run_flood_analysis_pipeline


def seed_demo_event():
    print("\n" + "=" * 80)
    print("FLOOD IMPACT ASSESSMENT — DEMONSTRATION WORKFLOW")
    print("=" * 80)
    print("Initializing demonstration with ImpactMesh-Flood benchmark event:")

    event_meta = SAMPLE_EVENTS["EMSR548_GER"]
    print(f"Event: {event_meta['name']} ({event_meta['country']})")
    print(f"Catalog ID: {event_meta['event_id']} (Split: {event_meta['split'].upper()})")
    print("Attribution: IBM, DLR, and ESA Φ-lab (CC BY 4.0) / Copernicus EMS")
    print("-" * 80)

    init_db()
    db = SessionLocal()

    event_id = event_meta["event_id"]
    # Check if exists
    existing = db.query(FloodEvent).filter(FloodEvent.id == event_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    ev = FloodEvent(
        id=event_id,
        name=event_meta["name"],
        country=event_meta["country"],
        description=(
            "Historic July 2021 flash floods along the Ahr Valley. Catastrophic rainfall produced "
            "extreme peak river discharges and inundation across residential river valleys."
        ),
        start_date=datetime.datetime(2021, 7, 14, 0, 0),
        end_date=datetime.datetime(2021, 7, 20, 0, 0),
        bounds_geojson=event_meta["bounds"],
        status="active",
    )
    db.add(ev)
    db.commit()

    # Generate synthetic Sentinel-1 and Sentinel-2 georeferenced raster products
    demo_dir = settings.DATA_DIR / "demo" / event_id
    demo_dir.mkdir(parents=True, exist_ok=True)

    width, height = 300, 300
    transform = from_origin(event_meta["bounds"][0], event_meta["bounds"][3], 0.001, 0.001)
    crs = "EPSG:4326"

    print("Generating georeferenced multi-sensor observation scenes...")

    # Observation 1: Before Event (Sentinel-1 SAR)
    # Ahr river baseline water body (sinuous channel)
    s1_pre = np.full((2, height, width), -9.0, dtype=np.float32)
    for x in range(width):
        y_center = int(150 + 40 * np.sin(x / 30.0))
        s1_pre[0, max(0, y_center - 3) : min(height, y_center + 4), x] = -24.0
        s1_pre[1, max(0, y_center - 3) : min(height, y_center + 4), x] = -28.0

    s1_pre_path = demo_dir / "s1_pre.tif"
    write_cog(s1_pre_path, s1_pre, transform, crs)
    db.add(
        Observation(
            id=f"obs_pre_{event_id}",
            event_id=event_id,
            sensor="sentinel-1",
            observation_time=datetime.datetime(2021, 7, 10, 5, 45),
            event_phase="before",
            file_path=str(s1_pre_path),
            bands=["VV", "VH"],
            crs=crs,
            resolution_m=10.0,
        )
    )

    # Observation 2: Peak Flood (Sentinel-1 SAR)
    # Channel expands dramatically + floodplain inundation
    s1_during = np.full((2, height, width), -9.0, dtype=np.float32)
    for x in range(width):
        y_center = int(150 + 40 * np.sin(x / 30.0))
        # Flood extent spans 30-40 pixels across valley floor
        s1_during[0, max(0, y_center - 18) : min(height, y_center + 19), x] = -22.5
        s1_during[1, max(0, y_center - 18) : min(height, y_center + 19), x] = -26.5

    s1_during_path = demo_dir / "s1_during.tif"
    write_cog(s1_during_path, s1_during, transform, crs)
    db.add(
        Observation(
            id=f"obs_during_s1_{event_id}",
            event_id=event_id,
            sensor="sentinel-1",
            observation_time=datetime.datetime(2021, 7, 15, 6, 12),
            event_phase="during",
            file_path=str(s1_during_path),
            bands=["VV", "VH"],
            crs=crs,
            resolution_m=10.0,
        )
    )

    # Observation 3: Peak Flood (Sentinel-2 Optical)
    # Bands: B02 (Blue), B03 (Green), B04 (Red), B08 (NIR)
    # Water: High Green (~0.2), Low NIR (~0.03) -> High NDWI
    # Land: Moderate Green (~0.1), High NIR (~0.45) -> Low NDWI
    # Cloud patch in upper right quadrant: Bright visible (~0.65)
    s2_during = np.zeros((4, height, width), dtype=np.float32)
    s2_during[0] = 0.08  # B02 Blue land
    s2_during[1] = 0.12  # B03 Green land
    s2_during[2] = 0.09  # B04 Red land
    s2_during[3] = 0.42  # B08 NIR land

    for x in range(width):
        y_center = int(150 + 40 * np.sin(x / 30.0))
        y_min = max(0, y_center - 16)
        y_max = min(height, y_center + 17)
        s2_during[0, y_min:y_max, x] = 0.12
        s2_during[1, y_min:y_max, x] = 0.22
        s2_during[2, y_min:y_max, x] = 0.08
        s2_during[3, y_min:y_max, x] = 0.02

    # Introduce localized cloud obstruction & shadow creating sensor disagreement
    s2_during[:, :80, 210:290] = 0.65  # Cloud
    s2_during[3, 80:110, 210:260] = 0.04  # Cloud shadow

    s2_during_path = demo_dir / "s2_during.tif"
    write_cog(s2_during_path, s2_during, transform, crs)
    db.add(
        Observation(
            id=f"obs_during_s2_{event_id}",
            event_id=event_id,
            sensor="sentinel-2",
            observation_time=datetime.datetime(2021, 7, 15, 11, 4),
            event_phase="during",
            file_path=str(s2_during_path),
            bands=["B02", "B03", "B04", "B08"],
            crs=crs,
            resolution_m=10.0,
        )
    )

    # Observation 4: Post-Flood (Sentinel-1 SAR)
    # Partial recession: floodwaters receded from upper valley
    s1_post = np.full((2, height, width), -9.0, dtype=np.float32)
    for x in range(width):
        y_center = int(150 + 40 * np.sin(x / 30.0))
        width_cur = 8 if x < 150 else 18
        s1_post[0, max(0, y_center - width_cur) : min(height, y_center + width_cur + 1), x] = -23.0
        s1_post[1, max(0, y_center - width_cur) : min(height, y_center + width_cur + 1), x] = -27.0

    s1_post_path = demo_dir / "s1_post.tif"
    write_cog(s1_post_path, s1_post, transform, crs)
    db.add(
        Observation(
            id=f"obs_post_{event_id}",
            event_id=event_id,
            sensor="sentinel-1",
            observation_time=datetime.datetime(2021, 7, 21, 17, 30),
            event_phase="after",
            file_path=str(s1_post_path),
            bands=["VV", "VH"],
            crs=crs,
            resolution_m=10.0,
        )
    )

    # Generate realistic infrastructure: Buildings and Roads
    print("Generating georeferenced infrastructure layers (OSM buildings and road network)...")
    building_features = []
    road_features = []

    origin_x, origin_y = event_meta["bounds"][0], event_meta["bounds"][3]

    # Cluster buildings in 3 settlement clusters along the valley
    towns = [
        ("Ahrweiler", 40, 100, 50),
        ("Bad Neuenahr", 130, 190, 70),
        ("Sinzig", 220, 280, 60),
    ]

    bldg_id = 1
    for town_name, x_start, x_end, bldg_density in towns:
        for _ in range(bldg_density):
            bx = np.random.uniform(x_start, x_end)
            # Center near valley floor with scatter
            y_base = 150 + 40 * np.sin(bx / 30.0)
            by = np.random.normal(y_base, 25)
            by = np.clip(by, 10, height - 10)

            # Convert to lon/lat
            lon = origin_x + bx * 0.001
            lat = origin_y - by * 0.001
            size = 0.00018  # ~20m footprint
            poly = shapely.geometry.box(
                lon - size / 2, lat - size / 2, lon + size / 2, lat + size / 2
            )
            building_features.append(
                {
                    "geometry": poly,
                    "osm_id": str(100000 + bldg_id),
                    "type": "residential" if bldg_id % 4 != 0 else "commercial",
                    "name": f"{town_name} Structure {bldg_id}",
                }
            )
            bldg_id += 1

    # Scattered rural buildings
    for _ in range(80):
        bx = np.random.uniform(10, width - 10)
        by = np.random.uniform(20, height - 20)
        lon = origin_x + bx * 0.001
        lat = origin_y - by * 0.001
        size = 0.00015
        poly = shapely.geometry.box(lon - size / 2, lat - size / 2, lon + size / 2, lat + size / 2)
        building_features.append(
            {
                "geometry": poly,
                "osm_id": str(100000 + bldg_id),
                "type": "farm",
                "name": f"Rural Property {bldg_id}",
            }
        )
        bldg_id += 1

    bldgs_gdf = gpd.GeoDataFrame(building_features, crs=crs)
    bldgs_path = demo_dir / "buildings.gpkg"
    bldgs_gdf.to_file(bldgs_path, driver="GPKG", layer="buildings")

    db.add(
        InfrastructureDataset(
            id=f"infra_bldgs_{event_id}",
            event_id=event_id,
            layer_type="buildings",
            source="osm",
            file_path=str(bldgs_path),
            feature_count=len(bldgs_gdf),
        )
    )

    # Road network: Primary valley highway B266 + crossing bridges + connecting residential streets
    # 1. Main Valley Arterial (B266)
    pts_b266 = []
    for x in range(0, width, 5):
        y_val = 150 + 40 * np.sin(x / 30.0) + 12.0  # Runs slightly north of river channel
        pts_b266.append((origin_x + x * 0.001, origin_y - y_val * 0.001))
    road_features.append(
        {
            "geometry": shapely.geometry.LineString(pts_b266),
            "osm_id": "90001",
            "type": "primary",
            "name": "Bundesstraße B266",
        }
    )

    # 2. Secondary valley road (southern bank)
    pts_south = []
    for x in range(0, width, 6):
        y_val = 150 + 40 * np.sin(x / 30.0) - 14.0  # Runs south of river channel
        pts_south.append((origin_x + x * 0.001, origin_y - y_val * 0.001))
    road_features.append(
        {
            "geometry": shapely.geometry.LineString(pts_south),
            "osm_id": "90002",
            "type": "secondary",
            "name": "L83 Talstraße",
        }
    )

    # 3. Crossing bridges across the Ahr river valley
    for bridge_idx, bx in enumerate([50, 110, 160, 210, 260], start=1):
        y_center = 150 + 40 * np.sin(bx / 30.0)
        p1 = (origin_x + bx * 0.001, origin_y - (y_center - 35) * 0.001)
        p2 = (origin_x + bx * 0.001, origin_y - (y_center + 35) * 0.001)
        road_features.append(
            {
                "geometry": shapely.geometry.LineString([p1, p2]),
                "osm_id": str(91000 + bridge_idx),
                "type": "secondary",
                "name": f"Ahr Valley Bridge {bridge_idx} ({['Ahrweiler', 'Bad Neuenahr West', 'Bad Neuenahr Center', 'Heppingen', 'Sinzig'][bridge_idx - 1]})",
            }
        )

    # 4. Town residential streets
    for street_idx, (tname, x1, x2, _) in enumerate(towns, start=1):
        for s in range(5):
            sx = np.random.uniform(x1, x2)
            sy = 150 + 40 * np.sin(sx / 30.0)
            p1 = (origin_x + sx * 0.001, origin_y - (sy - 20) * 0.001)
            p2 = (origin_x + (sx + 15) * 0.001, origin_y - (sy + 18) * 0.001)
            road_features.append(
                {
                    "geometry": shapely.geometry.LineString([p1, p2]),
                    "osm_id": str(92000 + street_idx * 10 + s),
                    "type": "residential",
                    "name": f"{tname} Local Route {s + 1}",
                }
            )

    roads_gdf = gpd.GeoDataFrame(road_features, crs=crs)
    roads_path = demo_dir / "roads.gpkg"
    roads_gdf.to_file(roads_path, driver="GPKG", layer="roads")

    db.add(
        InfrastructureDataset(
            id=f"infra_roads_{event_id}",
            event_id=event_id,
            layer_type="roads",
            source="osm",
            file_path=str(roads_path),
            feature_count=len(roads_gdf),
        )
    )

    db.commit()
    print("Multi-sensor observations & infrastructure datasets registered.")

    # Trigger analysis pipeline
    analysis_id = f"demo_anl_{event_id}"
    analysis = AnalysisRun(
        id=analysis_id,
        event_id=event_id,
        status="pending",
        config_json={
            "method": "baseline",
            "output_crs": "EPSG:4326",
            "output_resolution_m": 10.0,
            "probability_threshold": 0.5,
        },
    )
    db.add(analysis)
    db.commit()

    print("\nExecuting multi-sensor evidence reconstruction pipeline...")
    run_flood_analysis_pipeline(analysis_id)

    db.refresh(analysis)
    metrics: ImpactMetrics = (
        db.query(ImpactMetrics).filter(ImpactMetrics.analysis_id == analysis_id).first()
    )
    outputs = db.query(GeospatialOutput).filter(GeospatialOutput.analysis_id == analysis_id).all()

    print("\n" + "=" * 80)
    print("RECONSTRUCTION RESULTS & IMPACT METRICS:")
    print("=" * 80)
    print(f"Status: {analysis.status.upper()}")
    print(f"Total Observed Water:       {metrics.total_observed_water_m2 / 1e6:,.2f} km²")
    print(f"Pre-Existing Baseline Water: {metrics.preexisting_water_m2 / 1e6:,.2f} km²")
    print(f"Newly Inundated Land:        {metrics.newly_flooded_m2 / 1e6:,.2f} km²")
    print(f"Observed Receded Extent:     {metrics.receded_flooded_m2 / 1e6:,.2f} km²")
    print(
        f"Potentially Affected Bldgs:  {metrics.affected_buildings:,} of {metrics.total_buildings:,}"
    )
    print(
        f"Inundated Road Length:       {metrics.affected_road_meters / 1000.0:,.2f} km of {metrics.total_road_meters / 1000.0:,.2f} km"
    )
    print(f"Uncertainty Area:            {metrics.uncertain_water_m2 / 1e6:,.2f} km²")
    print("-" * 80)
    print("Generated Artifacts:")
    for o in outputs:
        print(f" - [{o.format.upper()}] {o.product_type}: {o.file_path}")
    print("=" * 80)
    print("\nTo inspect the event interactively in the web application:")
    print("1. Start backend: make run-api")
    print("2. Start frontend: make run-web")
    print(f"3. Open: http://localhost:3000/events/{event_id}")
    print("=" * 80 + "\n")

    db.close()


if __name__ == "__main__":
    seed_demo_event()

if __name__ == "__main__":
    seed_demo_event()
