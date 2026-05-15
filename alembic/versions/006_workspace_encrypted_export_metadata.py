"""006 - workspace encrypted export metadata columns
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006_workspace_encrypted_export_metadata"
down_revision: Union[str, None] = "005_add_review_status_to_tax_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("export_packages", sa.Column("workspace_id", sa.String(length=36), nullable=True))
    op.add_column("export_packages", sa.Column("filename", sa.String(length=255), nullable=True))
    op.add_column("export_packages", sa.Column("status", sa.String(length=30), nullable=False, server_default="ready"))
    op.add_column("export_packages", sa.Column("encrypted", sa.Boolean(), nullable=False, server_default=sa.sql.false()))
    op.add_column("export_packages", sa.Column("kdf", sa.String(length=40), nullable=True))
    op.add_column("export_packages", sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("export_packages", sa.Column("file_size", sa.Integer(), nullable=True))
    op.add_column("export_packages", sa.Column("sha256", sa.String(length=64), nullable=True))
    op.add_column("export_packages", sa.Column("document_count", sa.Integer(), nullable=True))
    op.add_column("export_packages", sa.Column("blocking_reasons", sa.Text(), nullable=True))
    op.add_column("export_packages", sa.Column("storage_path", sa.String(length=512), nullable=True))

    op.create_foreign_key(
        "fk_export_packages_workspace_id_tax_workspaces",
        "export_packages",
        "tax_workspaces",
        ["workspace_id"],
        ["id"],
    )
    op.create_index("ix_export_packages_workspace_id", "export_packages", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_export_packages_workspace_id", table_name="export_packages")
    op.drop_constraint("fk_export_packages_workspace_id_tax_workspaces", "export_packages", type_="foreignkey")
    op.drop_column("export_packages", "storage_path")
    op.drop_column("export_packages", "blocking_reasons")
    op.drop_column("export_packages", "document_count")
    op.drop_column("export_packages", "sha256")
    op.drop_column("export_packages", "file_size")
    op.drop_column("export_packages", "downloaded_at")
    op.drop_column("export_packages", "kdf")
    op.drop_column("export_packages", "encrypted")
    op.drop_column("export_packages", "status")
    op.drop_column("export_packages", "filename")
    op.drop_column("export_packages", "workspace_id")
