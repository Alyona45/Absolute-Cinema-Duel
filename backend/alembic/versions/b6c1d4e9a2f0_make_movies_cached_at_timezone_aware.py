"""make movies.cached_at timezone-aware

Revision ID: b6c1d4e9a2f0
Revises: 8d91f64c2a11
Create Date: 2026-03-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b6c1d4e9a2f0"
down_revision: Union[str, Sequence[str], None] = "8d91f64c2a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Переводит movies.cached_at в timestamp with time zone."""
    op.alter_column(
        "movies",
        "cached_at",
        existing_type=sa.TIMESTAMP(),
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="cached_at AT TIME ZONE 'UTC'",
        existing_nullable=False,
    )


def downgrade() -> None:
    """Возвращает movies.cached_at в timestamp without time zone."""
    op.alter_column(
        "movies",
        "cached_at",
        existing_type=sa.TIMESTAMP(timezone=True),
        type_=sa.TIMESTAMP(),
        postgresql_using="cached_at AT TIME ZONE 'UTC'",
        existing_nullable=False,
    )
