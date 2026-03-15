"""add_short_description_to_movies

Revision ID: 8d91f64c2a11
Revises: fc2ade025b88
Create Date: 2026-03-09 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d91f64c2a11'
down_revision: Union[str, Sequence[str], None] = 'fc2ade025b88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет short_description в таблицу movies."""
    op.add_column('movies', sa.Column('short_description', sa.Text(), nullable=True))


def downgrade() -> None:
    """Удаляет short_description из таблицы movies."""
    op.drop_column('movies', 'short_description')
