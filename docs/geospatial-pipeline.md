# Geospatial Processing Pipeline

The geospatial processing engine is modular, fully typed, and tested. It transforms heterogeneous satellite scenes into georeferenced flood impact evidence.

```mermaid
flowchart LR
    A[Satellite Scenes] --> B[Validator]
    B --> C[Spatial Harmonization]
    C --> D[Physical Indices & Inference]
    D --> E[Permanent Water Separation]
    E --> F[Temporal Persistence Tracking]
    F --> G[Vector Polygonization]
    G --> H[Infrastructure Intersection]
    H --> I[Evidence Package Export]
```

---

## 1. Preprocessing Specifications

### 1.1 Sentinel-1 SAR (Synthetic Aperture Radar)

- **Bands**: VV (Vertical-transmit / Vertical-receive) and VH (Cross-polarization).
- **Speckle Mitigation**: Enhanced Lee filter using local 5x5 window variance to remove radar speckle while preserving water body boundaries.
- **Backscatter Representation**: Converted to decibels ($dB = 10 \cdot \log_{10}(\text{intensity})$).
- **Physical Signature**: Calm standing water acts as a specular reflector, scattering the radar pulses away from the sensor. Backscatter thresholds are typically $VV < -15.0\text{ dB}$ and $VH < -22.0\text{ dB}$.

### 1.2 Sentinel-2 Optical

- **Bands**: B02 (Blue), B03 (Green), B04 (Red), B08/B8A (Near Infrared), B11 (SWIR1), B12 (SWIR2).
- **Indices Computed**:
  $$\text{NDWI} = \frac{\text{Green} - \text{NIR}}{\text{Green} + \text{NIR}}$$
  $$\text{MNDWI} = \frac{\text{Green} - \text{SWIR1}}{\text{Green} + \text{SWIR1}}$$
- **Cloud & Shadow Masking**: Unobscured pixels are separated from clouds and cloud shadows. Cloud-obscured pixels are explicitly marked as unobserved/invalid and never treated as dry land.

### 1.3 Digital Elevation Model (DEM)

- **Topographic Constraints**: Slope in degrees is computed via 3x3 Sobel gradient filtering.
- Floodwaters cannot stand statically on steep mountain ridges ($> 7^\circ$). Candidate water detections on steep terrain are attenuated to eliminate false-positive mountain shadow detections.

---

## 2. Common Spatial Grid Harmonization

All participating observations (Sentinel-1, Sentinel-2, DEM, vector layers) are aligned to an identical target raster grid:

- Target CRS: Configurable (default `EPSG:4326` or equal-area projected grid).
- Continuous channels (radar backscatter, optical reflectance, DEM elevation) are resampled via bilinear interpolation.
- Discrete masks (water labels, validity masks) are resampled strictly using nearest-neighbor interpolation to prevent categorical corruption.
