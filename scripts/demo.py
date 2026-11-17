import datetime
import sys
from pathlib import Path

import numpy as np
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
        status="active"
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
    db.add(Observation(
        id=f"obs_pre_{event_id}",
        event_id=event_id,
        sensor="sentinel-1",
        observation_time=datetime.datetime(2021, 7, 10, 5, 45),
        event_phase="before",
        file_path=str(s1_pre_path),
        bands=["VV", "VH"],
        crs=crs,
        resolution_m=10.0
    ))

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
    db.add(Observation(
        id=f"obs_during_s1_{event_id}",
        event_id=event_id,
        sensor="sentinel-1",
        observation_time=datetime.datetime(2021, 7, 15, 6, 12),
        event_phase="during",
        file_path=str(s1_during_path),
        bands=["VV", "VH"],
        crs=crs,
        resolution_m=10.0
    ))

    # Observation 3: Post-Flood (Sentinel-1 SAR)
    # Partial recession: floodwaters receded from upper valley
    s1_post = np.full((2, height, width), -9.0, dtype=np.float32)
    for x in range(width):
        y_center = int(150 + 40 * np.sin(x / 30.0))
        width_cur = 8 if x < 150 else 18
        s1_post[0, max(0, y_center - width_cur) : min(height, y_center + width_cur + 1), x] = -23.0
        s1_post[1, max(0, y_center - width_cur) : min(height, y_center + width_cur + 1), x] = -27.0

    s1_post_path = demo_dir / "s1_post.tif"
    write_cog(s1_post_path, s1_post, transform, crs)
    db.add(Observation(
        id=f"obs_post_{event_id}",
        event_id=event_id,
        sensor="sentinel-1",
        observation_time=datetime.datetime(2021, 7, 21, 17, 30),
        event_phase="after",
        file_path=str(s1_post_path),
        bands=["VV", "VH"],
        crs=crs,
        resolution_m=10.0
    ))

    db.commit()
    print("Multi-sensor observations registered.")

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
            "probability_threshold": 0.5
        }
    )
    db.add(analysis)
    db.commit()

    print("\nExecuting multi-sensor evidence reconstruction pipeline...")
    run_flood_analysis_pipeline(analysis_id)

    db.refresh(analysis)
    metrics: ImpactMetrics = db.query(ImpactMetrics).filter(ImpactMetrics.analysis_id == analysis_id).first()
    outputs = db.query(GeospatialOutput).filter(GeospatialOutput.analysis_id == analysis_id).all()

    print("\n" + "=" * 80)
    print("RECONSTRUCTION RESULTS & IMPACT METRICS:")
    print("=" * 80)
    print(f"Status: {analysis.status.upper()}")
    print(f"Total Observed Water:       {metrics.total_observed_water_m2 / 1e6:,.2f} km²")
    print(f"Pre-Existing Baseline Water: {metrics.preexisting_water_m2 / 1e6:,.2f} km²")
    print(f"Newly Inundated Land:        {metrics.newly_flooded_m2 / 1e6:,.2f} km²")
    print(f"Observed Receded Extent:     {metrics.receded_flooded_m2 / 1e6:,.2f} km²")
    print(f"Potentially Affected Bldgs:  {metrics.affected_buildings:,} of {metrics.total_buildings:,}")
    print(f"Inundated Road Length:       {metrics.affected_road_meters / 1000.0:,.2f} km of {metrics.total_road_meters / 1000.0:,.2f} km")
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
