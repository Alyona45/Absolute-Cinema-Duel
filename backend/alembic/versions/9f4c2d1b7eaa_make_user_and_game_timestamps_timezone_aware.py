"""make user and game timestamps timezone-aware

Revision ID: 9f4c2d1b7eaa
Revises: 77ec4585da6f
Create Date: 2026-03-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f4c2d1b7eaa"
down_revision: Union[str, Sequence[str], None] = "77ec4585da6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Переводит user/auth/game timestamps в timestamp with time zone."""
    op.alter_column(
        "users",
        "created_at",
        existing_type=sa.TIMESTAMP(),
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
        existing_nullable=False,
    )
    op.alter_column(
        "auth_sessions",
        "expires_at",
        existing_type=sa.TIMESTAMP(),
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="expires_at AT TIME ZONE 'UTC'",
        existing_nullable=False,
    )
    op.alter_column(
        "game_sessions",
        "started_at",
        existing_type=sa.TIMESTAMP(),
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="started_at AT TIME ZONE 'UTC'",
        existing_nullable=False,
    )
    op.alter_column(
        "game_sessions",
        "finished_at",
        existing_type=sa.TIMESTAMP(),
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="finished_at AT TIME ZONE 'UTC'",
        existing_nullable=True,
    )


def downgrade() -> None:
    """Возвращает user/auth/game timestamps в timestamp without time zone."""
    op.alter_column(
        "game_sessions",
        "finished_at",
        existing_type=sa.TIMESTAMP(timezone=True),
        type_=sa.TIMESTAMP(),
        postgresql_using="finished_at AT TIME ZONE 'UTC'",
        existing_nullable=True,
    )
    op.alter_column(
        "game_sessions",
        "started_at",
        existing_type=sa.TIMESTAMP(timezone=True),
        type_=sa.TIMESTAMP(),
        postgresql_using="started_at AT TIME ZONE 'UTC'",
        existing_nullable=False,
    )
    op.alter_column(
        "auth_sessions",
        "expires_at",
        existing_type=sa.TIMESTAMP(timezone=True),
        type_=sa.TIMESTAMP(),
        postgresql_using="expires_at AT TIME ZONE 'UTC'",
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "created_at",
        existing_type=sa.TIMESTAMP(timezone=True),
        type_=sa.TIMESTAMP(),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
        existing_nullable=False,
    )
