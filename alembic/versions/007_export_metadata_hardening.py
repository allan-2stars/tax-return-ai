"""007 - export metadata hardening columns
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007_export_metadata_hardening"
down_revision: Union[str, None] = "006_workspace_encrypted_export_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("export_packages", sa.Column("encryption_version", sa.String(length=20), nullable=True))
    op.add_column("export_packages", sa.Column("kdf_params_summary", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("export_packages", "kdf_params_summary")
    op.drop_column("export_packages", "encryption_version")
