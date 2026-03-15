"""merge alembic heads

Revision ID: 77ec4585da6f
Revises: a18c8f04e2b1, b6c1d4e9a2f0
Create Date: 2026-03-11 00:13:21.030113

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '77ec4585da6f'
down_revision: Union[str, Sequence[str], None] = ('a18c8f04e2b1', 'b6c1d4e9a2f0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
