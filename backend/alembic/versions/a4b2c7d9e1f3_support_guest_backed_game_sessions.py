"""support guest backed game sessions

Revision ID: a4b2c7d9e1f3
Revises: e5b7c2f1a9d4
Create Date: 2026-03-20 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4b2c7d9e1f3"
down_revision: Union[str, Sequence[str], None] = "e5b7c2f1a9d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("game_sessions", "host_user_id", existing_type=sa.Integer(), nullable=True)

    op.add_column("session_participants", sa.Column("guest_id", sa.String(length=64), nullable=True))
    op.add_column("session_participants", sa.Column("display_name", sa.String(length=64), nullable=True))
    op.add_column(
        "session_participants",
        sa.Column("is_host", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.execute(
        """
        UPDATE session_participants sp
        SET display_name = COALESCE(u.username, u.email)
        FROM users u
        WHERE sp.user_id = u.id
        """
    )
    op.execute(
        """
        UPDATE session_participants sp
        SET is_host = TRUE
        FROM game_sessions gs
        WHERE sp.session_id = gs.id
          AND sp.user_id = gs.host_user_id
        """
    )

    op.alter_column("session_participants", "user_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("session_participants", "display_name", existing_type=sa.String(length=64), nullable=False)

    op.drop_index("session_participants_unique", table_name="session_participants")
    op.create_index(
        "session_participants_user_unique",
        "session_participants",
        ["session_id", "user_id"],
        unique=True,
    )
    op.create_index(
        "session_participants_guest_unique",
        "session_participants",
        ["session_id", "guest_id"],
        unique=True,
    )
    op.create_check_constraint(
        "ck_session_participants_exactly_one_identity",
        "session_participants",
        "(user_id IS NOT NULL AND guest_id IS NULL) OR "
        "(user_id IS NULL AND guest_id IS NOT NULL)",
    )

    op.add_column(
        "session_movies",
        sa.Column("proposed_by_participant_id", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE session_movies sm
        SET proposed_by_participant_id = sp.id
        FROM session_participants sp
        WHERE sp.session_id = sm.session_id
          AND sp.user_id = sm.proposed_by_user_id
        """
    )
    op.alter_column(
        "session_movies",
        "proposed_by_participant_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_session_movies_proposed_by_participant_id",
        "session_movies",
        "session_participants",
        ["proposed_by_participant_id"],
        ["id"],
    )
    op.drop_column("session_movies", "proposed_by_user_id")

    op.alter_column(
        "session_participants",
        "is_host",
        existing_type=sa.Boolean(),
        server_default=None,
    )


def downgrade() -> None:
    op.add_column("session_movies", sa.Column("proposed_by_user_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE session_movies sm
        SET proposed_by_user_id = sp.user_id
        FROM session_participants sp
        WHERE sm.proposed_by_participant_id = sp.id
        """
    )

    op.execute(
        """
        UPDATE game_sessions
        SET winner_session_movie_id = NULL
        WHERE winner_session_movie_id IN (
            SELECT sm.id
            FROM session_movies sm
            JOIN session_participants sp ON sp.id = sm.proposed_by_participant_id
            WHERE sp.user_id IS NULL
        )
        """
    )
    op.execute(
        """
        DELETE FROM session_movies
        WHERE proposed_by_user_id IS NULL
        """
    )
    op.alter_column("session_movies", "proposed_by_user_id", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint(
        "fk_session_movies_proposed_by_participant_id",
        "session_movies",
        type_="foreignkey",
    )
    op.drop_column("session_movies", "proposed_by_participant_id")

    op.execute(
        """
        DELETE FROM session_participants
        WHERE user_id IS NULL
        """
    )
    op.execute(
        """
        DELETE FROM game_sessions
        WHERE host_user_id IS NULL
        """
    )

    op.drop_constraint(
        "ck_session_participants_exactly_one_identity",
        "session_participants",
        type_="check",
    )
    op.drop_index("session_participants_guest_unique", table_name="session_participants")
    op.drop_index("session_participants_user_unique", table_name="session_participants")
    op.create_index("session_participants_unique", "session_participants", ["session_id", "user_id"], unique=True)

    op.alter_column("session_participants", "display_name", existing_type=sa.String(length=64), nullable=True)
    op.alter_column("session_participants", "user_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("session_participants", "is_host")
    op.drop_column("session_participants", "display_name")
    op.drop_column("session_participants", "guest_id")

    op.alter_column("game_sessions", "host_user_id", existing_type=sa.Integer(), nullable=False)
