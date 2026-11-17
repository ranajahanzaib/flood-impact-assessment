# Observation Ingestion & Validation

## 1. Supported Input Data Formats

1. **Raster Imagery**:
   - GeoTIFF (`.tif`, `.tiff`)
   - Cloud-Optimized GeoTIFF (COG)
   - Dimensions $> 0$, valid non-identity geotransform, valid coordinate reference system (`src.crs`).
2. **Vector Layers**:
   - GeoPackage (`.gpkg`)
   - GeoJSON (`.geojson`)
   - Shapefiles (`.shp` within archive)
3. **Dataset Ingestion**:
   - ImpactMesh-Flood zarr / tar archives and sample bundles.

---

## 2. Validation Safeguards

The validator (`geospatial/ingestion/validator.py`) enforces:

- Rejection of unreferenced or unprojected images (identity affine matrices).
- Verification of band counts against sensor specifications (Sentinel-1 requires VV/VH; Sentinel-2 requires optical bands).
- Calculation of SHA-256 cryptographic checksum at ingestion time.
- NoData value registration and propagation.
- Measurement of ground sampling distance ($resolution\_m$).
