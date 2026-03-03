"""create tables for users, auth_sessions, movies, etc.

Revision ID: 46ed37c0b404
Revises:
Create Date: 2026-03-03 23:17:11.995309

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46ed37c0b404'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1) users first, because many tables reference it
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=False)

    # 2) base tables without cyclic FK issues
    op.create_table(
        'genres',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('idx_genres_name', 'genres', ['name'], unique=False)

    op.create_table(
        'movies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('kinopoisk_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('poster_url', sa.String(length=1024), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('runtime', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('cached_at', sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('kinopoisk_id')
    )
    op.create_index('idx_movies_kinopoisk_id', 'movies', ['kinopoisk_id'], unique=True)

    # create game_sessions without FK to session_movies yet (cycle break)
    op.create_table(
        'game_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('host_user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=True),
        sa.Column('winner_session_movie_id', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('finished_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['host_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_game_sessions_host_user_id', 'game_sessions', ['host_user_id'], unique=False)

    # now session_movies can reference game_sessions and users
    op.create_table(
        'session_movies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('movie_id', sa.Integer(), nullable=False),
        sa.Column('proposed_by_user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['movie_id'], ['movies.id']),
        sa.ForeignKeyConstraint(['proposed_by_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['session_id'], ['game_sessions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('session_movies_unique', 'session_movies', ['session_id', 'movie_id'], unique=True)

    # add deferred FK after both tables exist
    op.create_foreign_key(
        'fk_game_sessions_winner_session_movie_id',
        'game_sessions',
        'session_movies',
        ['winner_session_movie_id'],
        ['id']
    )

    op.create_table(
        'auth_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_auth_sessions_user_id', 'auth_sessions', ['user_id'], unique=False)
    op.create_index('refresh_token_hash_unique', 'auth_sessions', ['refresh_token_hash'], unique=True)

    op.create_table(
        'movie_genres',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('movie_id', sa.Integer(), nullable=False),
        sa.Column('genre_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['genre_id'], ['genres.id']),
        sa.ForeignKeyConstraint(['movie_id'], ['movies.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('movie_genres_unique', 'movie_genres', ['movie_id', 'genre_id'], unique=True)

    op.create_table(
        'session_participants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['game_sessions.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('session_participants_unique', 'session_participants', ['session_id', 'user_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('session_participants_unique', table_name='session_participants')
    op.drop_table('session_participants')

    op.drop_index('movie_genres_unique', table_name='movie_genres')
    op.drop_table('movie_genres')

    op.drop_index('refresh_token_hash_unique', table_name='auth_sessions')
    op.drop_index('idx_auth_sessions_user_id', table_name='auth_sessions')
    op.drop_table('auth_sessions')

    op.drop_constraint('fk_game_sessions_winner_session_movie_id', 'game_sessions', type_='foreignkey')
    op.drop_index('session_movies_unique', table_name='session_movies')
    op.drop_table('session_movies')

    op.drop_index('idx_game_sessions_host_user_id', table_name='game_sessions')
    op.drop_table('game_sessions')

    op.drop_index('idx_movies_kinopoisk_id', table_name='movies')
    op.drop_table('movies')

    op.drop_index('idx_genres_name', table_name='genres')
    op.drop_table('genres')

    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
