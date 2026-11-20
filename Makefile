.PHONY: setup dev run-api run-web test lint typecheck format demo download-data train evaluate docker-up docker-down screenshots

PYTHON ?= .venv/bin/python
UVICORN ?= .venv/bin/uvicorn
PYTEST ?= .venv/bin/pytest
RUFF ?= .venv/bin/ruff
PNPM ?= $(shell PATH="$$(echo $$PATH | tr ':' '\n' | grep -v 'Library/pnpm' | tr '\n' ':')" which pnpm 2>/dev/null || echo pnpm)

setup:
	uv venv .venv --python /opt/homebrew/bin/python3.10 || uv venv .venv
	uv pip install -e ".[dev]"
	cd apps/web && $(PNPM) install

run-api:
	$(UVICORN) services.api.main:app --host 127.0.0.1 --port 8000 --reload

run-web:
	cd apps/web && $(PNPM) run dev

dev:
	@echo "Starting backend and frontend..."
	$(UVICORN) services.api.main:app --host 127.0.0.1 --port 8000 &
	cd apps/web && $(PNPM) run dev

test:
	$(PYTEST) -v

lint:
	$(RUFF) check .
	cd apps/web && $(PNPM) run lint

typecheck:
	cd apps/web && $(PNPM) run typecheck

format:
	$(RUFF) format .

demo:
	$(PYTHON) scripts/demo.py

screenshots:
	$(PYTHON) scripts/generate_screenshots.py

download-data:
	$(PYTHON) -m ml.datasets.impactmesh download --events EMSR548_GER --splits test --max-download-gb 5.0

train:
	@echo "Running adapter verification / training step..."
	$(PYTHON) -c "import torch; from ml.adapters.prithvi import PrithviFloodModel; from ml.training.trainer import FloodModelTrainer, FloodDataset, DataLoader; import numpy as np; m = PrithviFloodModel(); t = FloodModelTrainer(m); d = FloodDataset(np.random.randn(8, 6, 64, 64), np.random.randint(0, 2, (8, 64, 64))); l = DataLoader(d, batch_size=2); res = t.fit(l, l, epochs=1); print('Train result:', res)"

evaluate:
	@echo "Evaluating segmentation metrics on synthetic validation control..."
	$(PYTHON) -c "from ml.evaluation.metrics import compute_segmentation_metrics; import numpy as np; p = np.random.randint(0, 2, (100, 100)); t = np.random.randint(0, 2, (100, 100)); m = compute_segmentation_metrics(p, t); print('Evaluation Metrics:', m)"

docker-up:
	docker compose up -d

docker-down:
	docker compose down
