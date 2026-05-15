"""add DEK wrapped-key hierarchy fields on users

Revision ID: 010_dek_wrapped_key_hierarchy
Revises: 009_worker_job_capability_fields
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa


revision = "010_dek_wrapped_key_hierarchy"
down_revision = "009_worker_job_capability_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("encrypted_dek_by_password", sa.String(length=4096), nullable=True))
    op.add_column("users", sa.Column("encrypted_dek_by_recovery", sa.String(length=4096), nullable=True))
    op.add_column("users", sa.Column("dek_version", sa.String(length=40), nullable=True))
    op.add_column("users", sa.Column("dek_wrapping_metadata", sa.String(length=4096), nullable=True))
    op.add_column("users", sa.Column("dek_created_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("dek_rotated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "dek_rotated_at")
    op.drop_column("users", "dek_created_at")
    op.drop_column("users", "dek_wrapping_metadata")
    op.drop_column("users", "dek_version")
    op.drop_column("users", "encrypted_dek_by_recovery")
    op.drop_column("users", "encrypted_dek_by_password")

