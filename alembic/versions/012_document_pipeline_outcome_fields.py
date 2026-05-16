"""add extraction/classification outcome fields on documents

Revision ID: 012_document_pipeline_outcome_fields
Revises: 011_unlock_capability_and_epoch
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa


revision = "012_document_pipeline_outcome_fields"
down_revision = "011_unlock_capability_and_epoch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("extraction_status", sa.String(length=30), nullable=True))
    op.add_column("documents", sa.Column("extraction_text_length", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("classification_status", sa.String(length=30), nullable=True))
    op.add_column("documents", sa.Column("classification_provider", sa.String(length=50), nullable=True))
    op.add_column("documents", sa.Column("classification_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "classification_error")
    op.drop_column("documents", "classification_provider")
    op.drop_column("documents", "classification_status")
    op.drop_column("documents", "extraction_text_length")
    op.drop_column("documents", "extraction_status")

