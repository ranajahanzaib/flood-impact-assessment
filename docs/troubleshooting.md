# Troubleshooting & Operational Guide

## 1. Environment & Geospatial Dependencies

### Python GDAL / Rasterio issues

The platform uses pre-compiled standard binary wheels for Rasterio 1.4+ and PyOgrio 0.13+ on macOS Apple Silicon and Linux x86_64.
If installing manually outside `uv`:

```bash
brew install gdal
pip install rasterio geopandas
```

### PyTorch Device Acceleration

Hardware acceleration is detected dynamically in `ml/models/base.py`:

- **NVIDIA GPU**: CUDA enabled automatically if drivers present.
- **Apple Silicon (M1/M2/M3/M4)**: Apple MPS (Metal Performance Shaders) enabled automatically.
- **Standard Host**: CPU fallback with optimized multi-threaded vectorized operations.

---

## 2. Common Verification Checks

### Port Conflicts

- Backend defaults to port `8000` (`http://127.0.0.1:8000`).
- Frontend Next.js defaults to port `3000` (`http://localhost:3000`).

To change ports:

```bash
# Backend on port 8080
.venv/bin/uvicorn services.api.main:app --port 8080

# Frontend on port 3001
cd apps/web && pnpm run dev -- -p 3001
```

### Test Suite Execution

To verify full system integrity:

```bash
make test
```

All 21 automated tests covering ingestion, spatial grids, permanent water separation, infrastructure intersection, ML adapters, and API endpoints should pass.
