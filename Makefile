.PHONY: setup setup-interactive run dev clean clean-all check-gpu setup-backend setup-frontend setup-dirs

setup: setup-dirs setup-backend setup-frontend
	@echo ""
	@echo "Setup complete."
	@echo "  Run 'make check-gpu' to verify GPU compatibility."
	@echo "  Run 'make run' to start the application."

setup-interactive:
	@bash scripts/setup.sh

setup-dirs:
	@mkdir -p data/captures data/predictions data/reports data/cache
	@echo "Data directories created."

setup-backend:
	cd backend && python -m venv .venv && \
	. .venv/bin/activate && \
	pip install -r requirements.txt && \
	playwright install chromium
	@echo ""
	@echo "Backend setup complete."
	@echo "NOTE: TRIBE v2 must be installed separately:"
	@echo "  git clone https://github.com/facebookresearch/tribev2.git"
	@echo "  cd tribev2 && pip install -e ."

setup-frontend:
	cd frontend && npm install
	@echo "Frontend setup complete."

run:
	@echo "Starting backend and frontend..."
	$(MAKE) run-backend & $(MAKE) run-frontend & wait

run-backend:
	cd backend && . .venv/bin/activate && \
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

run-frontend:
	cd frontend && npm run dev

dev: run

clean:
	rm -rf data/captures/* data/predictions/* data/reports/*
	@echo "Cleaned data directories."

clean-all: clean
	rm -rf data/cache/*
	@echo "Cleaned all data including model cache."

check-gpu:
	@cd backend && . .venv/bin/activate && python ../scripts/check_gpu.py
