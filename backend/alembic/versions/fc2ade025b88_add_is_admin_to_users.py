"""add_is_admin_to_users

Revision ID: fc2ade025b88
Revises: 46ed37c0b404
Create Date: 2026-03-05 18:18:35.797129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc2ade025b88'
down_revision: Union[str, Sequence[str], None] = '46ed37c0b404'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Применяет миграцию: добавляет колонку is_admin в таблицу users."""
    # server_default='false' нужен, чтобы существующие строки получили значение по умолчанию
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Откатывает миграцию: удаляет колонку is_admin из таблицы users."""
    op.drop_column('users', 'is_admin')
