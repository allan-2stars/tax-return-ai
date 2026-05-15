"""005 - add review_status to tax_items

Backwards-compatible status column for workspace-first review workflow.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005_add_review_status_to_tax_items"
down_revision: Union[str, None] = "004_add_workspace_id_to_tax_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tax_items",
        sa.Column("review_status", sa.String(length=30), nullable=False, server_default="needs_review"),
    )
    op.execute(
        "UPDATE tax_items "
        "SET review_status = CASE "
        "WHEN needs_review = 1 THEN 'needs_review' "
        "ELSE 'confirmed' END"
    )
    op.create_index("ix_tax_items_review_status", "tax_items", ["review_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tax_items_review_status", table_name="tax_items")
    op.drop_column("tax_items", "review_status")
