.PHONY: setup run dev clean check-gpu setup-backend setup-frontend

setup: setup-backend setup-frontend
	@echo "Setup complete. Run 'make run' to start."

setup-backend:
	cd backend && python -m venv .venv && \
	. .venv/bin/activate && \
	pip install -r requirements.txt && \
	playwright install chromium
	@echo "Backend setup complete."

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
	cd backend && . .venv/bin/activate && python ../scripts/check_gpu.py
