# Evidence Package & Reproducibility Manifest

Each analysis produces an exportable, self-contained, and reproducible **Evidence Package** (`flood_evidence_<analysis_id>.zip`).

```text
flood-impact-evidence/
├── report.pdf                           # Complete multi-page executive evidence dossier
│
├── rasters/
│   ├── preexisting_water.tif            # Baseline permanent water body raster (COG)
│   ├── maximum_observed_inundation.tif  # Peak candidate new inundation extent (COG)
│   ├── temporal_persistence.tif         # Fraction of valid observations inundated (COG)
│   └── uncertainty.tif                  # Composite uncertainty raster (COG)
│
├── vectors/
│   ├── inundated_regions.gpkg           # Georeferenced flood extent polygons
│   ├── affected_buildings.gpkg          # Building footprints with intersection %
│   ├── affected_roads.gpkg              # Road centerlines with inundated length (m)
│   └── manual_review_regions.gpkg       # Flagged uncertainty polygons
│
├── tables/
│   ├── event_summary.csv                # High-level event metrics
│   └── observation_metrics.csv          # Observation-by-observation metric breakdown
│
├── metadata/
│   ├── event.json                       # Event metadata and bounding box
│   ├── processing_configuration.json    # Exact analysis parameters used
│   ├── provenance.json                  # Sensor metadata, software versions, licenses
│   └── checksums.sha256                 # Cryptographic SHA-256 integrity manifest
│
└── README.md                            # Package documentation and attribution
```

## SHA-256 Cryptographic Verification

Every file in the evidence package is recorded in `metadata/checksums.sha256`. Analysts and auditors can verify that raster files, vector geometries, or metrics have not been modified after processing:

```bash
sha256sum -c metadata/checksums.sha256
```
