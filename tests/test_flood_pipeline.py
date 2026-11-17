import datetime
import uuid
from pathlib import Path

import numpy as np
import pytest
from rasterio.transform import from_origin

from geospatial.raster.cog import write_cog
from services.api.database import SessionLocal, init_db
from services.api.models import (
    AnalysisRun,
    FloodEvent,
    GeospatialOutput,
    ImpactMetrics,
    Observation,
)
from services.worker.pipelines.analysis_pipeline import run_flood_analysis_pipeline


@pytest.fixture
def synthetic_flood_event_fixtures(tmp_path):
    """
    Creates synthetic georeferenced satellite scenes for a complete flood lifecycle:
    - Before: permanent lake (x: 20-40, y: 20-40)
    - During (S1): permanent lake + new flood (x: 50-80, y: 50-80)
    - During (S2): optical scene confirming flood + slight cloud in corner
    - After: flood receded
    """
    init_db()
    db = SessionLocal()

    event_id = f"test_ev_{uuid.uuid4().hex[:8]}"
    bounds = [7.0, 50.0, 7.1, 50.1]
    ev = FloodEvent(
        id=event_id,
        name="Test Synthetic Event",
        country="Testland",
        bounds_geojson=bounds,
        status="active"
    )
    db.add(ev)
    db.commit()

    # Grid parameters
    width, height = 100, 100
    transform = from_origin(7.0, 50.1, 0.001, 0.001)
    crs = "EPSG:4326"

    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # 1. Before Event Observation (Sentinel-1 SAR)
    # Permanent lake at [20:40, 20:40]
    s1_pre = np.full((2, height, width), -10.0, dtype=np.float32)
    s1_pre[0, 20:40, 20:40] = -24.0  # VV
    s1_pre[1, 20:40, 20:40] = -28.0  # VH
    pre_path = fixtures_dir / "s1_pre.tif"
    write_cog(pre_path, s1_pre, transform, crs)

    db.add(Observation(
        id=f"obs_pre_{event_id}",
        event_id=event_id,
        sensor="sentinel-1",
        observation_time=datetime.datetime(2021, 7, 10, 6, 0),
        event_phase="before",
        file_path=str(pre_path),
        bands=["VV", "VH"],
        crs=crs,
        resolution_m=10.0
    ))

    # 2. During Event Observation (Sentinel-1 SAR)
    # Permanent lake [20:40, 20:40] + New Flood [50:80, 50:80]
    s1_during = np.full((2, height, width), -10.0, dtype=np.float32)
    s1_during[0, 20:40, 20:40] = -24.0
    s1_during[1, 20:40, 20:40] = -28.0
    s1_during[0, 50:80, 50:80] = -22.0  # newly flooded
    s1_during[1, 50:80, 50:80] = -26.0
    during_s1_path = fixtures_dir / "s1_during.tif"
    write_cog(during_s1_path, s1_during, transform, crs)

    db.add(Observation(
        id=f"obs_during_s1_{event_id}",
        event_id=event_id,
        sensor="sentinel-1",
        observation_time=datetime.datetime(2021, 7, 15, 6, 0),
        event_phase="during",
        file_path=str(during_s1_path),
        bands=["VV", "VH"],
        crs=crs,
        resolution_m=10.0
    ))

    # 3. During Event Observation (Sentinel-2 Optical)
    # 4 bands: B02, B03 (Green), B04 (Red), B08 (NIR)
    s2_during = np.full((4, height, width), 0.25, dtype=np.float32)
    s2_during[3] = 0.45  # high NIR over vegetation
    # Water: high green, low NIR
    s2_during[1, 20:40, 20:40] = 0.35
    s2_during[3, 20:40, 20:40] = 0.05
    s2_during[1, 50:80, 50:80] = 0.35
    s2_during[3, 50:80, 50:80] = 0.05
    during_s2_path = fixtures_dir / "s2_during.tif"
    write_cog(during_s2_path, s2_during, transform, crs)

    db.add(Observation(
        id=f"obs_during_s2_{event_id}",
        event_id=event_id,
        sensor="sentinel-2",
        observation_time=datetime.datetime(2021, 7, 16, 10, 30),
        event_phase="during",
        file_path=str(during_s2_path),
        bands=["B02", "B03", "B04", "B08"],
        crs=crs,
        resolution_m=10.0
    ))

    # 4. After Event Observation (Sentinel-1 SAR)
    # Flood receded from [50:80, 50:80], lake remains
    s1_post = np.full((2, height, width), -10.0, dtype=np.float32)
    s1_post[0, 20:40, 20:40] = -24.0
    s1_post[1, 20:40, 20:40] = -28.0
    post_path = fixtures_dir / "s1_post.tif"
    write_cog(post_path, s1_post, transform, crs)

    db.add(Observation(
        id=f"obs_post_{event_id}",
        event_id=event_id,
        sensor="sentinel-1",
        observation_time=datetime.datetime(2021, 7, 22, 6, 0),
        event_phase="after",
        file_path=str(post_path),
        bands=["VV", "VH"],
        crs=crs,
        resolution_m=10.0
    ))

    db.commit()
    db.close()

    return event_id

def test_full_analysis_pipeline_execution(synthetic_flood_event_fixtures):
    event_id = synthetic_flood_event_fixtures
    db = SessionLocal()

    analysis_id = f"test_anl_{uuid.uuid4().hex[:8]}"
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

    # Execute pipeline synchronously
    run_flood_analysis_pipeline(analysis_id)

    # Check status and outputs
    db.refresh(analysis)
    assert analysis.status == "completed"
    assert analysis.progress_pct == 100

    # Verify metrics
    metrics: ImpactMetrics = db.query(ImpactMetrics).filter(ImpactMetrics.analysis_id == analysis_id).first()
    assert metrics is not None
    assert metrics.newly_flooded_m2 > 0.0
    assert metrics.preexisting_water_m2 > 0.0
    assert metrics.receded_flooded_m2 > 0.0
    # Newly inundated should be distinct from pre-existing water
    assert metrics.newly_flooded_m2 != metrics.preexisting_water_m2

    # Verify geospatial outputs generated
    outputs = db.query(GeospatialOutput).filter(GeospatialOutput.analysis_id == analysis_id).all()
    output_types = [o.product_type for o in outputs]
    assert "flood_classification" in output_types
    assert "new_inundation" in output_types
    assert "persistence" in output_types
    assert "uncertainty" in output_types
    assert "pdf_report" in output_types
    assert "evidence_package" in output_types

    # Verify physical file existence
    pdf_out = next(o for o in outputs if o.product_type == "pdf_report")
    assert Path(pdf_out.file_path).exists()
    assert Path(pdf_out.file_path).stat().st_size > 1000  # valid PDF generated

    zip_out = next(o for o in outputs if o.product_type == "evidence_package")
    assert Path(zip_out.file_path).exists()
    assert Path(zip_out.file_path).stat().st_size > 1000  # valid ZIP generated

    db.close()
