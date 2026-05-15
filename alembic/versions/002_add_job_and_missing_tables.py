"""002 — Add document_pages, jobs, classification_results, review_actions, export_packages

Tables:
  - document_pages (per-page OCR results)
  - jobs (async job tracking)
  - classification_results (raw AI classification output)
  - review_actions (user confirm/correct events — append-only)
  - export_packages (generated review package metadata)

Migration type: forward-only (no downgrade — data loss risk on these tables).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_add_job_and_missing_tables"
down_revision: Union[str, None] = "001_initial_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── document_pages ───────────────────────────────────────────────────
    op.create_table(
        "document_pages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36),
                  sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("ocr_method", sa.String(30), nullable=True,
                  comment="pdfplumber / tesseract / identity"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )

    # ── jobs ─────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36),
                  sa.ForeignKey("tax_sessions.id"), nullable=True),
        sa.Column("document_id", sa.String(36),
                  sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("job_type", sa.String(30), nullable=False,
                  comment="ingestion / ocr / classification / export / compliance_review"),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default="queued",
                  comment="queued / running / succeeded / failed / cancelled / retrying"),
        sa.Column("progress", sa.Float(), nullable=True),
        sa.Column("progress_message", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )

    # ── classification_results ───────────────────────────────────────────
    op.create_table(
        "classification_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36),
                  sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("session_id", sa.String(36),
                  sa.ForeignKey("tax_sessions.id"), nullable=False),
        sa.Column("provider_name", sa.String(30), nullable=False,
                  comment="anthropic / openai / mock"),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("raw_output", sa.Text(), nullable=True),
        sa.Column("parsed_output", sa.Text(), nullable=True,
                  comment="Validated JSON output"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.sql.true()),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )

    # ── review_actions ───────────────────────────────────────────────────
    op.create_table(
        "review_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36),
                  sa.ForeignKey("tax_sessions.id"), nullable=False),
        sa.Column("tax_item_id", sa.String(36),
                  sa.ForeignKey("tax_items.id"), nullable=True),
        sa.Column("action_type", sa.String(30), nullable=False,
                  comment="user_confirmed / user_corrected / user_excluded / agent_reviewed"),
        sa.Column("previous_status", sa.String(30), nullable=True),
        sa.Column("new_status", sa.String(30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.String(50), nullable=True,
                  server_default="user"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )

    # ── export_packages ──────────────────────────────────────────────────
    op.create_table(
        "export_packages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36),
                  sa.ForeignKey("tax_sessions.id"), nullable=False),
        sa.Column("format", sa.String(20), nullable=False,
                  server_default="json",
                  comment="json / csv / pdf"),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Float(), nullable=True),
        sa.Column("total_taxable", sa.Float(), nullable=True),
        sa.Column("compliance_score", sa.String(10), nullable=True,
                  comment="low / medium / high"),
        sa.Column("export_data", sa.Text(), nullable=True,
                  comment="Full JSON export payload"),
        sa.Column("exported_by", sa.String(50), nullable=True,
                  server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop all five tables in reverse dependency order."""
    op.drop_table("export_packages")
    op.drop_table("review_actions")
    op.drop_table("classification_results")
    op.drop_table("jobs")
    op.drop_table("document_pages")
