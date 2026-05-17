"""add movieco tournament tables

Revision ID: f18b9a3c6d12
Revises: a4b2c7d9e1f3
Create Date: 2026-03-22 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f18b9a3c6d12"
down_revision = "a4b2c7d9e1f3"
branch_labels = None
depends_on = None


tournamentroomstatus = sa.Enum("LOBBY", "RUNNING", "FINISHED", name="tournamentroomstatus")


def upgrade() -> None:
    op.create_table(
        "tournament_test_presets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("criteria_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "tournament_rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invite_code", sa.String(length=12), nullable=False, unique=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("host_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("preset_id", sa.Integer(), sa.ForeignKey("tournament_test_presets.id"), nullable=True),
        sa.Column("bracket_size", sa.Integer(), nullable=False),
        sa.Column("status", tournamentroomstatus, nullable=False, server_default="LOBBY"),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("winner_movie_id", sa.Integer(), sa.ForeignKey("movies.id"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "tournament_participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("tournament_rooms.id"), nullable=False),
        sa.Column("user_key", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_host", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("joined_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("room_id", "user_key", name="uq_tournament_participants_room_user_key"),
    )
    op.create_index("idx_tournament_participants_room", "tournament_participants", ["room_id"])

    op.create_table(
        "tournament_votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("tournament_rooms.id"), nullable=False),
        sa.Column("participant_id", sa.Integer(), sa.ForeignKey("tournament_participants.id"), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("match_no", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "participant_id",
            "round_no",
            "match_no",
            name="uq_tournament_votes_participant_round_match",
        ),
    )
    op.create_index(
        "idx_tournament_votes_room_round_match",
        "tournament_votes",
        ["room_id", "round_no", "match_no"],
    )


def downgrade() -> None:
    op.drop_index("idx_tournament_votes_room_round_match", table_name="tournament_votes")
    op.drop_table("tournament_votes")

    op.drop_index("idx_tournament_participants_room", table_name="tournament_participants")
    op.drop_table("tournament_participants")

    op.drop_table("tournament_rooms")
    op.drop_table("tournament_test_presets")
