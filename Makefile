.PHONY: setup setup-interactive setup-dirs setup-backend setup-frontend setup-tribe prefetch \
        run run-backend run-frontend run-mock dev check-gpu lint clean clean-all

PYTHON ?= python3
VENV := backend/.venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
TRIBE_DIR ?= tribev2

setup: setup-dirs setup-backend setup-frontend
	@echo ""
	@echo "Setup complete."
	@echo "  make check-gpu    verify CUDA / VRAM for TRIBE v2"
	@echo "  make setup-tribe  install Meta's tribev2 package (GPU machines)"
	@echo "  make prefetch     download the fsaverage5 atlas and build the brain mesh"
	@echo "  make run          start backend + frontend"
	@echo "  make run-mock     start with synthetic inference (no GPU needed)"

setup-interactive:
	@bash scripts/setup.sh

setup-dirs:
	@mkdir -p data/captures data/predictions data/reports data/cache
	@test -f .env || cp .env.example .env
	@echo "Data directories ready; .env present."

setup-backend:
	test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt
	$(PY) -m playwright install chromium
	@echo "Backend setup complete."

setup-frontend:
	cd frontend && npm install
	@echo "Frontend setup complete."

setup-tribe:
	test -d $(TRIBE_DIR) || git clone https://github.com/facebookresearch/tribev2.git $(TRIBE_DIR)
	$(PIP) install -e $(TRIBE_DIR)
	@echo "TRIBE v2 installed. Set HF_TOKEN in .env for the text modality (gated Llama-3.2-3B)."

prefetch:
	cd backend && ../$(PY) ../scripts/prefetch_assets.py

run:
	@echo "Starting backend (:8000) and frontend (:3000)..."
	$(MAKE) run-backend & $(MAKE) run-frontend & wait

run-backend:
	cd backend && ../$(PY) main.py

run-frontend:
	cd frontend && npm run dev

run-mock:
	INFERENCE_BACKEND=mock $(MAKE) run

dev: run

check-gpu:
	cd backend && ../$(PY) ../scripts/check_gpu.py

lint:
	cd frontend && npx tsc --noEmit && npx eslint .
	$(PY) -m compileall -q backend

clean:
	rm -rf data/captures/* data/predictions/* data/reports/*
	@echo "Cleaned analysis data."

clean-all: clean
	rm -rf data/cache/*
	@echo "Cleaned model, atlas and mesh caches."
