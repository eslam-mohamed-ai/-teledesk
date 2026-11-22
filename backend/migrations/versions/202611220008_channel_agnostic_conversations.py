"""Make legacy Telegram-specific conversation columns nullable.

Channel-agnostic conversations (Messenger, WhatsApp, ...) have no Telegram bot
or numeric chat id. Existing Telegram rows keep their values, so history is
preserved.

Revision ID: 202611220008
Revises: 202611220007
Create Date: 2026-11-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202611220008"
down_revision: Union[str, None] = "202611220007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "conversations",
        "bot_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "conversations",
        "tg_chat_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )


def downgrade() -> None:
    # Cannot restore NOT NULL if non-Telegram conversations exist; this is
    # intentional: the omnichannel schema is forward-only.
    op.alter_column(
        "conversations",
        "tg_chat_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
    op.alter_column(
        "conversations",
        "bot_id",
        existing_type=sa.Integer(),
        nullable=False,
    )