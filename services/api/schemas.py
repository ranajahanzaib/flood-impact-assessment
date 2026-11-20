from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# --- Event Schemas ---
class FloodEventBase(BaseModel):
    name: str = Field(..., description="Human-readable flood event name")
    description: str | None = None
    country: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    bounds_geojson: Any | None = None


class FloodEventCreate(FloodEventBase):
    id: str | None = None


class FloodEventUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    bounds_geojson: Any | None = None


class FloodEventResponse(FloodEventBase):
    id: str
    status: str
    created_at: datetime
    observation_count: int = 0
    latest_analysis_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Observation Schemas ---
class ObservationBase(BaseModel):
    sensor: str = Field(..., description="sentinel-1, sentinel-2, dem")
    observation_time: datetime
    event_phase: str = Field(..., description="before, during, after")
    source: str = "uploaded"
    bands: list[str] | None = None
    crs: str = "EPSG:4326"
    resolution_m: float | None = None
    nodata: float | None = None


class ObservationResponse(ObservationBase):
    id: str
    event_id: str
    file_path: str
    checksum: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Analysis Configuration & Run Schemas ---
class AnalysisConfigSchema(BaseModel):
    method: str = Field("baseline", description="baseline, prithvi, clay")
    probability_threshold: float = Field(0.5, ge=0.0, le=1.0)
    output_crs: str = "EPSG:4326"
    output_resolution_m: float = 10.0
    area_unit: str = "km2"
    require_before_event: bool = True
    require_during_event: bool = True
    require_after_event: bool = False
    persistence_method: str = "valid_observation_ratio"
    minimum_valid_observations: int = 1
    enable_uncertainty: bool = True
    detect_sensor_disagreement: bool = True
    flag_manual_review: bool = True
    analyze_buildings: bool = True
    analyze_roads: bool = True
    tile_size: int = 512
    batch_size: int = 4


class AnalysisRunCreate(BaseModel):
    config: AnalysisConfigSchema | None = None


class GeospatialOutputResponse(BaseModel):
    id: str
    analysis_id: str
    product_type: str
    file_path: str
    format: str
    observation_id: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImpactMetricsResponse(BaseModel):
    id: str
    analysis_id: str
    total_observed_water_m2: float
    preexisting_water_m2: float
    newly_flooded_m2: float
    persistent_flooded_m2: float
    receded_flooded_m2: float
    uncertain_water_m2: float
    total_buildings: int
    affected_buildings: int
    uncertain_buildings: int
    total_road_meters: float
    affected_road_meters: float
    uncertain_road_meters: float
    metrics_breakdown_json: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class ReviewRegionResponse(BaseModel):
    id: str
    analysis_id: str
    geometry_json: dict[str, Any]
    flag_type: str
    reason: str
    status: str
    reviewer_notes: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewDecisionRequest(BaseModel):
    decision: str = Field(..., description="confirmed_flood, confirmed_dry, dismissed")
    notes: str | None = None


class AnalysisRunResponse(BaseModel):
    id: str
    event_id: str
    status: str
    progress_pct: int
    stage_message: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    config_json: dict[str, Any]
    outputs: list[GeospatialOutputResponse] = []
    metrics: ImpactMetricsResponse | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Infrastructure Schemas ---
class InfrastructureImportRequest(BaseModel):
    source: str = Field("osm", description="osm or uploaded")
    layer_types: list[str] = Field(["buildings", "roads"])
    osm_query_bbox: list[float] | None = None  # [min_lon, min_lat, max_lon, max_lat]


class InfrastructureResponse(BaseModel):
    id: str
    event_id: str
    layer_type: str
    source: str
    file_path: str
    feature_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Report Schemas ---
class ReportGenerateRequest(BaseModel):
    title: str | None = None
    include_map_render: bool = True
    include_provenance: bool = True


class ReportResponse(BaseModel):
    report_id: str
    analysis_id: str
    title: str
    pdf_path: str
    zip_path: str
    created_at: datetime
