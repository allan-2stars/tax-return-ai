"""add field-level encryption columns

Revision ID: 008_field_encryption_columns
Revises: 007_export_metadata_hardening
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "008_field_encryption_columns"
down_revision = "007_export_metadata_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_pages", sa.Column("text_enc", sa.Text(), nullable=True))
    op.add_column("document_pages", sa.Column("encryption_version", sa.String(length=20), nullable=True))
    op.add_column("document_pages", sa.Column("key_version", sa.String(length=40), nullable=True))

    op.add_column("tax_items", sa.Column("description_enc", sa.Text(), nullable=True))
    op.add_column("tax_items", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("tax_items", sa.Column("notes_enc", sa.Text(), nullable=True))
    op.add_column("tax_items", sa.Column("review_reason_enc", sa.Text(), nullable=True))
    op.add_column("tax_items", sa.Column("encryption_version", sa.String(length=20), nullable=True))
    op.add_column("tax_items", sa.Column("key_version", sa.String(length=40), nullable=True))

    op.add_column("classification_results", sa.Column("raw_input_enc", sa.Text(), nullable=True))
    op.add_column("classification_results", sa.Column("raw_output_enc", sa.Text(), nullable=True))
    op.add_column("classification_results", sa.Column("encryption_version", sa.String(length=20), nullable=True))
    op.add_column("classification_results", sa.Column("key_version", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("classification_results", "key_version")
    op.drop_column("classification_results", "encryption_version")
    op.drop_column("classification_results", "raw_output_enc")
    op.drop_column("classification_results", "raw_input_enc")

    op.drop_column("tax_items", "key_version")
    op.drop_column("tax_items", "encryption_version")
    op.drop_column("tax_items", "review_reason_enc")
    op.drop_column("tax_items", "notes_enc")
    op.drop_column("tax_items", "notes")
    op.drop_column("tax_items", "description_enc")

    op.drop_column("document_pages", "key_version")
    op.drop_column("document_pages", "encryption_version")
    op.drop_column("document_pages", "text_enc")

