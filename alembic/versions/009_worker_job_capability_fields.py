"""add worker job capability fields

Revision ID: 009_worker_job_capability_fields
Revises: 008_field_encryption_columns
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa


revision = "009_worker_job_capability_fields"
down_revision = "008_field_encryption_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("workspace_id", sa.String(length=36), nullable=True))
    op.add_column("jobs", sa.Column("user_id", sa.String(length=36), nullable=True))
    op.add_column("jobs", sa.Column("requires_encryption", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.add_column("jobs", sa.Column("capability_token_hash", sa.String(length=64), nullable=True))
    op.add_column("jobs", sa.Column("capability_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("payload", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("lease_owner", sa.String(length=80), nullable=True))
    op.add_column("jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))

    op.create_foreign_key("fk_jobs_workspace_id", "jobs", "tax_workspaces", ["workspace_id"], ["id"])
    op.create_foreign_key("fk_jobs_user_id", "jobs", "users", ["user_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_jobs_user_id", "jobs", type_="foreignkey")
    op.drop_constraint("fk_jobs_workspace_id", "jobs", type_="foreignkey")
    op.drop_column("jobs", "attempt_count")
    op.drop_column("jobs", "heartbeat_at")
    op.drop_column("jobs", "lease_expires_at")
    op.drop_column("jobs", "lease_owner")
    op.drop_column("jobs", "payload")
    op.drop_column("jobs", "capability_expires_at")
    op.drop_column("jobs", "capability_token_hash")
    op.drop_column("jobs", "requires_encryption")
    op.drop_column("jobs", "user_id")
    op.drop_column("jobs", "workspace_id")

