"""add selected movie to session participants

Revision ID: e5b7c2f1a9d4
Revises: d1a4e5f6b7c8
Create Date: 2026-03-18 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5b7c2f1a9d4"
down_revision: Union[str, Sequence[str], None] = "d1a4e5f6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_participants",
        sa.Column("selected_session_movie_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_session_participants_selected_session_movie_id",
        "session_participants",
        "session_movies",
        ["selected_session_movie_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_session_participants_selected_session_movie_id",
        "session_participants",
        type_="foreignkey",
    )
    op.drop_column("session_participants", "selected_session_movie_id")
