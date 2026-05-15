.PHONY: up up-team down migrate verify test seed-demo export-demo validate-schema new-migration lint format

# ── Start / Stop ─────────────────────────────────────────────────────────────
up:
	docker compose -f docker-compose.sqlite.yml up -d

up-team:
	docker compose -f docker-compose.postgres.yml up -d

down:
	docker compose -f docker-compose.sqlite.yml down
	docker compose -f docker-compose.postgres.yml down 2>/dev/null || true

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
	alembic upgrade head

new-migration:
	@test -n "$(name)" || (echo "Usage: make new-migration name=describe_change" && exit 1)
	alembic revision --autogenerate -m "$(name)"

# ── Verification (required before every commit) ───────────────────────────────
verify: lint validate-schema test
	@echo "✓ verify passed"

test:
	pytest tests/ -q --tb=short

lint:
	ruff check app/ tests/ scripts/
	ruff format --check app/ tests/ scripts/

format:
	ruff format app/ tests/ scripts/

# ── Schema validation ─────────────────────────────────────────────────────────
validate-schema:
	python skills/tax-return-specialist/scripts/validate_tax_analysis.py \
		skills/tax-return-specialist/schemas/tax_analysis_output.schema.json \
		skills/tax-return-specialist/examples/example-analysis-output.json
	python skills/tax-document-ingestion/scripts/validate_ingestion_json.py \
		skills/tax-document-ingestion/schemas/document_ingestion.schema.json \
		skills/tax-document-ingestion/templates/ingestion_result.example.json
	python skills/tax-compliance-review/scripts/validate_compliance_review_json.py \
		skills/tax-compliance-review/schemas/compliance_review.schema.json \
		skills/tax-compliance-review/examples/compliance_review.example.json
	@echo "✓ all schemas valid"

# ── Demo data ─────────────────────────────────────────────────────────────────
seed-demo:
	python scripts/seed_demo.py

export-demo:
	python scripts/export_demo.py
