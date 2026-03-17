"""add invite code to game sessions

Revision ID: c3f9a6d7b2e1
Revises: 9f4c2d1b7eaa
Create Date: 2026-03-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3f9a6d7b2e1"
down_revision: Union[str, Sequence[str], None] = "9f4c2d1b7eaa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет invite_code для игровых сессий."""
    op.add_column(
        "game_sessions",
        sa.Column("invite_code", sa.String(length=12), nullable=True),
    )

    op.execute(
        """
        UPDATE game_sessions
        SET invite_code = upper(substr(md5(id::text || started_at::text), 1, 12))
        WHERE invite_code IS NULL
        """
    )

    op.alter_column(
        "game_sessions",
        "invite_code",
        existing_type=sa.String(length=12),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_game_sessions_invite_code",
        "game_sessions",
        ["invite_code"],
    )


def downgrade() -> None:
    """Удаляет invite_code у игровых сессий."""
    op.drop_constraint(
        "uq_game_sessions_invite_code",
        "game_sessions",
        type_="unique",
    )
    op.drop_column("game_sessions", "invite_code")
