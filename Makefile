.PHONY: up down logs backend-shell frontend-shell test migrate revision verify lint format

# Detect docker compose command (v2 vs v1)
DC = $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

# ── Start / Stop ─────────────────────────────────────────────────────────────
up:
	$(DC) up -d --build
	# Wait for backend to be ready
	@sleep 3
	@echo "Services started."

down:
	$(DC) down

logs:
	$(DC) logs -f

# ── Shell access ──────────────────────────────────────────────────────────────
backend-shell:
	$(DC) exec backend sh || $(DC) exec backend bash

frontend-shell:
	$(DC) exec frontend sh || $(DC) exec frontend bash

frontend-dev:
	$(DC) logs -f frontend

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
	$(DC) exec -w /app backend alembic upgrade head
	# docker compose exec -w /app backend env PYTHONPATH=. alembic upgrade head

revision:
	@test -n "$(name)" || (echo "Usage: make revision name=describe_change" && exit 1)
	$(DC) exec -w /app backend alembic revision --autogenerate -m "$(name)"

new-migration:
	@test -n "$(name)" || (echo "Usage: make new-migration name=describe_change" && exit 1)
	$(DC) exec -w /app backend alembic revision -m "$(name)"

reset-db:
	rm -f data/taxapp.db
	$(DC) exec backend alembic upgrade head

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	$(DC) exec backend pytest tests/ -q --tb=short -x

test-coverage:
	$(DC) exec backend pytest tests/ -q --tb=short --cov=app --cov-report=term-missing

test-providers:
	$(DC) exec backend python tests/test_providers.py

test-jobs:
	$(DC) exec backend python -m pytest tests/test_job_service.py -q --tb=short -x

test-frontend:
	$(DC) exec frontend npm test

# ── Demo data ─────────────────────────────────────────────────────────────────
seed-demo:
	$(DC) exec -w /app backend python scripts/seed_demo.py

export-demo:
	$(DC) exec -w /app backend python scripts/export_demo.py

# ── Verification (lint + schema + tests) ──────────────────────────────────────
verify: lint validate-schema test test-frontend
	@echo "✓ verify passed"

lint:
	$(DC) exec backend ruff check app/ tests/ scripts/ || true
	$(DC) exec backend ruff format --check app/ tests/ scripts/ || true

format:
	$(DC) exec backend ruff format app/ tests/ scripts/

test-count:
	@$(DC) exec backend pytest tests/ --collect-only -q 2>&1 | tail -1

test-all: test test-frontend validate-schema
	@echo "✓ all tests passed"

validate-schema:
	$(DC) exec backend python \
		skills/tax-return-specialist/scripts/validate_tax_analysis.py \
			skills/tax-return-specialist/schemas/tax_analysis_output.schema.json \
			skills/tax-return-specialist/examples/example-analysis-output.json
	$(DC) exec backend python \
		skills/tax-document-ingestion/scripts/validate_ingestion_json.py \
			skills/tax-document-ingestion/schemas/document_ingestion.schema.json \
			skills/tax-document-ingestion/templates/ingestion_result.example.json
	$(DC) exec backend python \
		skills/tax-compliance-review/scripts/validate_compliance_review_json.py \
			skills/tax-compliance-review/schemas/compliance_review.schema.json \
			skills/tax-compliance-review/examples/compliance_review.example.json
	@echo "✓ all schemas valid"
