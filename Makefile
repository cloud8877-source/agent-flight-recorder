.PHONY: setup dev collector web demo db-init lint venv test regression policy-test prod-up storage-test

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

venv:
	test -d $(VENV) || python3 -m venv $(VENV)

setup: venv
	corepack enable
	pnpm install
	$(PIP) install -e apps/collector -e packages/sdk-python -e packages/cli

db-init: venv
	mkdir -p data
	AFR_DATABASE_PATH=./data/afr.db $(PYTHON) -c "import asyncio; from collector.db import init_db; asyncio.run(init_db())"

collector: venv
	AFR_DATABASE_PATH=./data/afr.db $(VENV)/bin/uvicorn collector.main:app --app-dir apps/collector/src --host 0.0.0.0 --port 4318 --reload

web:
	pnpm --filter @agent-flight-recorder/web dev

demo: venv
	AFR_ENDPOINT=http://localhost:4318 $(PYTHON) examples/support-refund-agent/main.py

dev:
	docker compose -f infra/docker-compose.yml up --build

lint:
	pnpm lint
	pnpm --filter @agent-flight-recorder/node run lint

e2e: venv
	chmod +x scripts/e2e.sh
	./scripts/e2e.sh

test: venv
	chmod +x scripts/regression.sh
	./scripts/regression.sh

regression: test

policy-test: venv
	chmod +x scripts/policy-e2e.sh
	./scripts/policy-e2e.sh

prod-up:
	docker compose -f infra/docker-compose.prod.yml up --build

storage-test: venv
	chmod +x scripts/storage-e2e.sh
	./scripts/storage-e2e.sh