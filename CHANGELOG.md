# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-17

### Initial Release — Multi-Sensor Flood Impact Evidence Platform

Initial public release of the **Flood Impact Assessment** platform, a production-grade open-source system designed to reconstruct, measure, and document the impact of flood events using multi-sensor satellite observations.

#### Geospatial Processing Engine

- **Multi-Sensor Ingestion**: Support for Sentinel-1 dual-polarization SAR (VV/VH), Sentinel-2 optical multispectral imagery, and Copernicus DEM elevation rasters with CRS and geotransform validation.
- **Sensor Preprocessing**:
  - Sentinel-1 Lee speckle filtering (adaptive windowed variance), decibel conversion, and dual-polarization water thresholding.
  - Sentinel-2 optical spectral indices (NDWI, MNDWI) with cloud and shadow masking.
  - DEM slope calculation with terrain-based false-positive suppression (preventing water detection on steep slopes).
- **Target Grid Harmonization**: Multi-sensor reprojection to aligned rasters with categorical nearest-neighbor vs. continuous bilinear resampling safeguards.
- **Baseline Water Separation**: Isolation of pre-existing permanent water bodies (rivers, lakes, reservoirs) to prevent false attribution of flood impact.
- **Flood Extent & Temporal Persistence**: Reconstruction of maximum candidate flood extent and temporal persistence raster indicating inundation fraction over time.
- **Equal-Area Metrics**: Geodesic and equal-area (`EPSG:6933` / UTM) metric computations for inundation, permanent water, and receded areas in square kilometers.
- **Infrastructure Impact Overlays**:
  - Building footprint analysis with area intersection percentage and high-uncertainty flags.
  - Road network analysis calculating exact inundated center-line length in meters per segment.
- **Composite Uncertainty Estimation**:
  - Pixel-level model prediction entropy $H(p)$.
  - Multi-sensor radar vs optical disagreement mapping.
  - Cloud and shadow contamination penalties.
  - Contiguous high-uncertainty region polygonization into an automated verification queue.

#### Machine Learning & Model Adapters

- **Model Adapter Architecture**: Abstract `ModelAdapter` interface supporting diverse foundation models.
- **Adapters**:
  - `BaselineWaterAdapter`: Deterministic physical rules engine requiring zero downloaded weights.
  - `PrithviAdapter`: Adapts IBM-NASA `Prithvi-EO-2.0-300M` 3D ViT embeddings with a lightweight `FloodSegmentationHead`.
  - `ClayAdapter`: Adaptable interface for tokenized multi-sensor foundation models.
- **Tiled Windowed Inference**: Overlapping spatial patch processing with cosine weight blending for arbitrary raster dimensions and low memory footprint.
- **Training & Probability Calibration**: Full PyTorch training loop supporting Dice + BCE loss, Brier score evaluation, and Expected Calibration Error (ECE) across 10 confidence bins.

#### Evidence Dossiers & Packaging

- **Executive PDF Report**: Multi-page report via ReportLab containing executive summary, methodology, exposure metrics tables, and georeferenced raster thumbnails.
- **Georeferenced ZIP Evidence Package**:
  - Cloud-Optimized GeoTIFFs (baseline water, maximum flood extent, temporal persistence, uncertainty).
  - OGC GeoPackage vector layers (inundated regions, affected buildings, affected roads, review regions).
  - Machine-readable CSV summaries and JSON metadata (event, processing parameters, provenance).
  - Cryptographic `checksums.sha256` integrity manifest for complete reproducibility.

#### REST API & Backend

- **FastAPI Backend**:
  - Event management and spatial query endpoints (`/api/events`).
  - Observation metadata and ingestion (`/api/observations`).
  - Multi-sensor analysis triggers and status polling (`/api/analysis`).
  - Dynamic COG raster and vector tile inspection endpoints (`/api/outputs`).
  - Interactive manual review submission and resolution (`/api/review`).
  - PDF and ZIP evidence package download endpoints.
- **Dual Database Support**: SQLite for instant zero-dependency local development, PostgreSQL with PostGIS extension for enterprise multi-user deployments.

#### Web Application

- **Next.js 14 Workspace**:
  - Interactive MapLibre GL geospatial map viewer with multi-layer toggles (observations, flood extent, persistence, infrastructure, uncertainty).
  - Temporal phase controls (Before, During, After satellite views).
  - Side-by-side swipe comparison mode between pre-flood baseline and peak inundation.
  - Real-time exposure KPI dashboard (total flooded $km^2$, building counts, road length $km$).
  - Interactive manual verification modal allowing analysts to inspect flagged anomalies, submit review decisions, and attach notes.

#### Dataset Tooling

- **ImpactMesh-Flood CLI**: Selective event-partitioned downloader with split filters, download quotas, integrity checksum validation, and local caching.

#### Developer Experience

- Complete Makefile tooling (`setup`, `test`, `lint`, `typecheck`, `demo`, `docker-up`).
- 21 automated tests covering geospatial algorithms, ML adapters, pipelines, and API routes.
