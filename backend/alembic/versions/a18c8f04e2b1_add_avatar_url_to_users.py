"""add_avatar_url_to_users

Revision ID: a18c8f04e2b1
Revises: 8d91f64c2a11
Create Date: 2026-03-09 15:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a18c8f04e2b1'
down_revision: Union[str, Sequence[str], None] = '8d91f64c2a11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет avatar_url в users."""
    op.add_column('users', sa.Column('avatar_url', sa.Text(), nullable=True))


def downgrade() -> None:
    """Удаляет avatar_url из users."""
    op.drop_column('users', 'avatar_url')
