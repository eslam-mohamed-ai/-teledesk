"""Add indexes for conversation listings and message history.

Revision ID: 202611220002
Revises: 202611220001
Create Date: 2026-11-22
"""

from typing import Sequence, Union

from alembic import op


revision: str = "202611220002"
down_revision: Union[str, None] = "202611220001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_conversations_company_id_last_message_at",
        "conversations",
        ["company_id", "last_message_at"],
        unique=False,
    )
    op.create_index(
        "ix_messages_conversation_id_created_at",
        "messages",
        ["conversation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_messages_conversation_id_created_at",
        table_name="messages",
    )
    op.drop_index(
        "ix_conversations_company_id_last_message_at",
        table_name="conversations",
    )
