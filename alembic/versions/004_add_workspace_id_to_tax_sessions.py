"""004 - add workspace_id bridge column to tax_sessions

Compatibility bridge for workspace-scoped access while preserving legacy sessions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_add_workspace_id_to_tax_sessions"
down_revision: Union[str, None] = "003_add_auth_and_workspaces"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tax_sessions", sa.Column("workspace_id", sa.String(length=36), nullable=True))
    op.create_index("ix_tax_sessions_workspace_id", "tax_sessions", ["workspace_id"], unique=False)
    op.create_foreign_key(
        "fk_tax_sessions_workspace_id_tax_workspaces",
        "tax_sessions",
        "tax_workspaces",
        ["workspace_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_tax_sessions_workspace_id_tax_workspaces", "tax_sessions", type_="foreignkey")
    op.drop_index("ix_tax_sessions_workspace_id", table_name="tax_sessions")
    op.drop_column("tax_sessions", "workspace_id")
