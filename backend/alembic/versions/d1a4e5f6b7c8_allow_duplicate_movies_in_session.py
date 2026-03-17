"""allow duplicate movies in session

Revision ID: d1a4e5f6b7c8
Revises: c3f9a6d7b2e1
Create Date: 2026-03-17 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d1a4e5f6b7c8"
down_revision: Union[str, Sequence[str], None] = "c3f9a6d7b2e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Разрешает повторное предложение одного и того же фильма в рамках сессии."""
    op.drop_index("session_movies_unique", table_name="session_movies")


def downgrade() -> None:
    """Возвращает запрет на повторное предложение одного и того же фильма в сессии."""
    op.create_index(
        "session_movies_unique",
        "session_movies",
        ["session_id", "movie_id"],
        unique=True,
    )
