"""add unlock capabilities and key epoch

Revision ID: 011_unlock_capability_and_epoch
Revises: 010_dek_wrapped_key_hierarchy
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa


revision = "011_unlock_capability_and_epoch"
down_revision = "010_dek_wrapped_key_hierarchy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("unlock_epoch", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("auth_sessions", sa.Column("key_epoch", sa.Integer(), nullable=False, server_default="1"))

    op.create_table(
        "unlock_capabilities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("auth_session_id", sa.String(length=36), nullable=False),
        sa.Column("session_token_hash", sa.String(length=255), nullable=False),
        sa.Column("key_epoch", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["auth_session_id"], ["auth_sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_unlock_capabilities_token_hash", "unlock_capabilities", ["session_token_hash"], unique=True)
    op.create_index("ix_unlock_capabilities_user", "unlock_capabilities", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_unlock_capabilities_user", table_name="unlock_capabilities")
    op.drop_index("ix_unlock_capabilities_token_hash", table_name="unlock_capabilities")
    op.drop_table("unlock_capabilities")
    op.drop_column("auth_sessions", "key_epoch")
    op.drop_column("users", "unlock_epoch")
