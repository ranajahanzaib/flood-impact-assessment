import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class FloodEvent(Base):
    __tablename__ = "flood_events"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    bounds_geojson = Column(JSON, nullable=True)  # [min_lon, min_lat, max_lon, max_lat] or GeoJSON geometry
    country = Column(String(100), nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(32), default="active")

    observations = relationship("Observation", back_populates="event", cascade="all, delete-orphan")
    analyses = relationship("AnalysisRun", back_populates="event", cascade="all, delete-orphan")
    infrastructure = relationship("InfrastructureDataset", back_populates="event", cascade="all, delete-orphan")


class Observation(Base):
    __tablename__ = "observations"

    id = Column(String(64), primary_key=True, index=True)
    event_id = Column(String(64), ForeignKey("flood_events.id"), nullable=False, index=True)
    sensor = Column(String(32), nullable=False)  # sentinel-1, sentinel-2, dem
    observation_time = Column(DateTime, nullable=False, index=True)
    event_phase = Column(String(16), nullable=False)  # before, during, after
    file_path = Column(String(512), nullable=False)
    source = Column(String(128), default="uploaded")  # impactmesh, copernicus, upload
    bands = Column(JSON, nullable=True)  # e.g. ["VV", "VH"] or ["B02", "B03", "B04", "B08", "B11", "B12"]
    crs = Column(String(32), nullable=False, default="EPSG:4326")
    resolution_m = Column(Float, nullable=True)
    nodata = Column(Float, nullable=True)
    checksum = Column(String(64), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    event = relationship("FloodEvent", back_populates="observations")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(String(64), primary_key=True, index=True)
    event_id = Column(String(64), ForeignKey("flood_events.id"), nullable=False, index=True)
    status = Column(String(32), default="pending", index=True)  # pending, running, completed, failed, cancelled
    config_json = Column(JSON, nullable=False)
    progress_pct = Column(Integer, default=0)
    stage_message = Column(String(255), default="Initialized")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    log_text = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    event = relationship("FloodEvent", back_populates="analyses")
    outputs = relationship("GeospatialOutput", back_populates="analysis", cascade="all, delete-orphan")
    metrics = relationship("ImpactMetrics", back_populates="analysis", uselist=False, cascade="all, delete-orphan")
    review_regions = relationship("ReviewRegion", back_populates="analysis", cascade="all, delete-orphan")


class GeospatialOutput(Base):
    __tablename__ = "geospatial_outputs"

    id = Column(String(64), primary_key=True, index=True)
    analysis_id = Column(String(64), ForeignKey("analysis_runs.id"), nullable=False, index=True)
    product_type = Column(String(64), nullable=False)
    # e.g. water_mask, new_inundation, preexisting_water, persistence, recession, uncertainty,
    # flooded_polygons, affected_buildings, affected_roads
    file_path = Column(String(512), nullable=False)
    format = Column(String(16), nullable=False)  # cog, gpkg, geojson, csv, png
    observation_id = Column(String(64), nullable=True)  # if per-observation
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    analysis = relationship("AnalysisRun", back_populates="outputs")


class ImpactMetrics(Base):
    __tablename__ = "impact_metrics"

    id = Column(String(64), primary_key=True, index=True)
    analysis_id = Column(String(64), ForeignKey("analysis_runs.id"), nullable=False, unique=True, index=True)
    total_observed_water_m2 = Column(Float, default=0.0)
    preexisting_water_m2 = Column(Float, default=0.0)
    newly_flooded_m2 = Column(Float, default=0.0)
    persistent_flooded_m2 = Column(Float, default=0.0)
    receded_flooded_m2 = Column(Float, default=0.0)
    uncertain_water_m2 = Column(Float, default=0.0)

    # Infrastructure counts
    total_buildings = Column(Integer, default=0)
    affected_buildings = Column(Integer, default=0)
    uncertain_buildings = Column(Integer, default=0)
    total_road_meters = Column(Float, default=0.0)
    affected_road_meters = Column(Float, default=0.0)
    uncertain_road_meters = Column(Float, default=0.0)

    metrics_breakdown_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    analysis = relationship("AnalysisRun", back_populates="metrics")


class ReviewRegion(Base):
    __tablename__ = "review_regions"

    id = Column(String(64), primary_key=True, index=True)
    analysis_id = Column(String(64), ForeignKey("analysis_runs.id"), nullable=False, index=True)
    geometry_json = Column(JSON, nullable=False)  # GeoJSON polygon
    flag_type = Column(String(64), nullable=False)  # sensor_disagreement, high_entropy, cloud_shadow, observation_gap
    reason = Column(Text, nullable=False)
    status = Column(String(32), default="pending", index=True)  # pending, confirmed_flood, confirmed_dry, dismissed
    reviewer_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    analysis = relationship("AnalysisRun", back_populates="review_regions")


class InfrastructureDataset(Base):
    __tablename__ = "infrastructure_datasets"

    id = Column(String(64), primary_key=True, index=True)
    event_id = Column(String(64), ForeignKey("flood_events.id"), nullable=False, index=True)
    layer_type = Column(String(32), nullable=False)  # buildings, roads
    source = Column(String(64), nullable=False)  # osm, user_upload
    file_path = Column(String(512), nullable=False)
    feature_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    event = relationship("FloodEvent", back_populates="infrastructure")
