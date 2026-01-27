"""add token_count to knowledge_chunks

Revision ID: 73487033ba80
Revises: 91c308d04d24
Create Date: 2026-01-26 18:16:11.679748+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "73487033ba80"
down_revision: str | None = "91c308d04d24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "knowledge_chunks",
        sa.Column("token_count", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("knowledge_chunks", "token_count")
