# Contributing to Flood Impact Assessment

Thank you for your interest in contributing to the **Flood Impact Assessment** platform! We welcome contributions from geospatial specialists, remote sensing engineers, machine learning researchers, GIS professionals, and full-stack developers.

This document outlines the development workflow, code conventions, testing protocols, and submission processes.

---

## 1. Code of Conduct

All contributors and participants agree to abide by our [Code of Conduct](./CODE_OF_CONDUCT.md). Please report any violations through GitHub Security Advisories or by contacting the project team.

---

## 2. Getting Started

### Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: 18.x or 20.x
- **Package Managers**: `uv` (recommended for fast Python virtual environments) and `pnpm`
- **Geospatial Libraries**: GDAL, GEOS, and PROJ (handled automatically via standard pre-compiled wheels for Rasterio and PyOgrio on macOS and Linux)
- **Optional**: Docker & Docker Compose (for running PostgreSQL/PostGIS and Redis)

### Fork and Local Setup

1. Fork the repository on GitHub and clone your fork locally:

   ```bash
   git clone https://github.com/<your-username>/flood-impact-assessment.git
   cd flood-impact-assessment
   ```

2. Initialize your virtual environment and install both backend and frontend dependencies:

   ```bash
   make setup
   ```

   _Alternatively, using manual commands:_

   ```bash
   # Python setup
   uv venv .venv
   source .venv/bin/activate
   uv pip install -e ".[dev]"

   # Frontend setup
   cd apps/web && pnpm install && cd ../..
   ```

3. Run the complete demonstration workflow to ensure everything is operating properly:
   ```bash
   make demo
   ```

---

## 3. Local Development

### Running the Services

- **Backend API** (FastAPI on `http://127.0.0.1:8000`):
  ```bash
  make run-api
  ```
- **Frontend App** (Next.js 14 on `http://localhost:3000`):
  ```bash
  make run-web
  ```
- **Unified Dev Mode**:
  ```bash
  make dev
  ```

### Optional PostGIS & Redis Environment

If testing against PostgreSQL/PostGIS rather than the default local SQLite database:

```bash
make docker-up
```

Set `DATABASE_URL` in your `.env` file:

```env
DATABASE_URL=postgresql://postgres:postgrespassword@localhost:5432/flood_impact
```

---

## 4. Code Standards and Formatting

We adhere strictly to automated styling and typing standards:

- **Python**:
  - Code formatting and linting are enforced by **Ruff**.
  - All new public functions, classes, and methods should contain clear type annotations.
  - Scientific computations must adhere to metric equal-area coordinates (e.g. `EPSG:6933` / local UTM) rather than degree-based approximations.

  ```bash
  make format   # Automatically formats Python code
  make lint     # Runs Ruff linter checks
  ```

- **Frontend (TypeScript / Next.js)**:
  - Strictly typed with TypeScript (`npx tsc --noEmit`).
  - Next.js ESLint conventions (`next lint`).
  - Styled with Tailwind CSS classes; no inline style hacks where Tailwind utility classes suffice.
  ```bash
  make typecheck
  ```

---

## 5. Testing Requirements

All contributions must include relevant automated unit or integration tests. Pull requests will not be merged if test suites or linters fail.

Run the full suite of automated tests:

```bash
make test
```

### Test Suite Structure

- `tests/test_geospatial.py`: SAR Lee speckle filtering, optical indices, DEM constraints, target grid harmonization, area computations.
- `tests/test_flood_pipeline.py`: End-to-end flood event reconstruction, persistence tracking, infrastructure exposure overlays, uncertainty estimation.
- `tests/test_dataset.py`: ImpactMesh-Flood downloader, split hierarchies, checksum verifications.
- `tests/test_ml.py`: Foundation model adapters, segmentation head, Brier/ECE calibration, tiled inference.
- `tests/test_api.py`: FastAPI endpoints, event management, review queues, report generation, ZIP packaging.

---

## 6. Pull Request Workflow

1. **Create a Feature Branch**:

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

2. **Commit Your Changes**:
   Write descriptive commit messages following the Conventional Commits specification:

   ```text
   feat(geospatial): add adaptive thresholding for flooded forest SAR backscatter
   fix(api): correct bounding box serialization for multi-polygon events
   docs(uncertainty): clarify entropy calibration methodology
   ```

3. **Verify Locally Before Pushing**:
   Ensure all checks pass cleanly:

   ```bash
   make lint
   make typecheck
   make test
   ```

4. **Submit a Pull Request**:
   - Push to your fork and submit a PR to `main`.
   - Provide a concise summary of changes, motivation, and test evidence in the PR template.
   - Link any related GitHub issues (`Fixes #123`).

---

## 7. Community & Questions

For general questions, architectural discussions, or collaboration inquiries, feel free to open a [GitHub Discussion](https://github.com/ranajahanzaib/flood-impact-assessment/discussions) or create an issue.
