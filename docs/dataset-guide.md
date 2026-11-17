# ImpactMesh-Flood Dataset Guide

## 1. Dataset Overview

- **Repository**: `ibm-esa-geospatial/ImpactMesh-Flood`
- **Authors**: IBM, DLR (German Aerospace Center), ESA Φ-lab
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Annotations**: Copernicus Emergency Management Service (EMS) verified flood delineations
- **Total Release Size**: ~329 GB across 206 global flood events and 24,578 samples.

---

## 2. Partitioning and Data Leakage Safeguards

The platform strictly respects the official event-level split hierarchy to prevent spatial and temporal data leakage:

| Split               | Event Count | Sample Patches | Intended Purpose                                          |
| :------------------ | :---------- | :------------- | :-------------------------------------------------------- |
| **Train**           | 158         | 19,448         | Model adaptation & parameter estimation                   |
| **Validation**      | 22          | 2,171          | Hyperparameter tuning and model checkpoint selection      |
| **Test**            | 21          | 2,959          | Benchmark evaluation on held-out observations             |
| **Held-Out Events** | 5           | 562            | Generalization evaluation on entirely unseen flood events |

### Selective Acquisition CLI

To avoid saturating storage with 329 GB of unneeded data, use the selective download tool:

```bash
# List available events
python -m ml.datasets.impactmesh list-events --split test

# Download specific event within storage budget
python -m ml.datasets.impactmesh download \
  --events EMSR548_GER \
  --splits test \
  --max-download-gb 5.0
```
