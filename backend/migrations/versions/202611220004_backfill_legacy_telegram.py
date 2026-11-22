"""Backfill legacy Telegram data into channel-agnostic tables.

Revision ID: 202611220004
Revises: 202611220003
Create Date: 2026-11-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202611220004"
down_revision: Union[str, None] = "202611220003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Providers allowed by the domain model. Telegram is the only one seeded here.
TELEGRAM_PROVIDER = "telegram"


def _conn():
    return op.get_bind()


def upgrade() -> None:
    bind = _conn()

    # 1. One telegram channel per existing bot.
    #    external_id is the bot username (unique on bots), which safely and
    #    globally identifies the provider account without cross-tenant clashes.
    bind.execute(
        sa.text(
            """
            INSERT INTO channels (
                company_id, provider, external_id, display_name, username,
                credentials_encrypted, credentials_key_version, webhook_secret,
                status, status_reason, active, created_at, updated_at
            )
            SELECT
                b.company_id,
                :provider,
                b.username,
                b.name,
                b.username,
                b.token_encrypted,
                1,
                b.secret,
                CASE WHEN b.connected THEN 'connected' ELSE 'disconnected' END,
                NULL,
                b.active,
                b.created_at,
                b.created_at
            FROM bots b
            """
        ),
        {"provider": TELEGRAM_PROVIDER},
    )

    # 2. One contact per distinct (bot_id, tg_chat_id) conversation participant.
    bind.execute(
        sa.text(
            """
            INSERT INTO contacts (
                company_id, display_name, first_name, language,
                custom_fields, created_at, last_seen_at
            )
            SELECT DISTINCT
                c.company_id,
                c.customer_name,
                c.customer_name,
                c.lang,
                jsonb_build_object(
                    'telegram_username', c.username,
                    'telegram_chat_id', c.tg_chat_id::text,
                    'source', 'telegram'
                ),
                c.created_at,
                c.last_message_at
            FROM conversations c
            WHERE c.tg_chat_id IS NOT NULL
            """
        )
    )

    # 3. Contact -> channel identity (external_user_id = tg_chat_id as text).
    bind.execute(
        sa.text(
            """
            INSERT INTO contact_identities (contact_id, channel_id, external_user_id, profile_snapshot)
            SELECT
                con.id,
                ch.id,
                c.tg_chat_id::text,
                jsonb_build_object(
                    'customer_name', c.customer_name,
                    'username', c.username,
                    'lang', c.lang,
                    'bot_id', c.bot_id
                )
            FROM conversations c
            JOIN contacts con
              ON con.company_id = c.company_id
             AND (con.custom_fields->>'telegram_chat_id')::bigint = c.tg_chat_id
             AND con.custom_fields->>'source' = 'telegram'
            JOIN channels ch
              ON ch.provider = :provider
             AND ch.external_id = (
                 SELECT b.username FROM bots b WHERE b.id = c.bot_id
             )
            WHERE c.tg_chat_id IS NOT NULL
            GROUP BY con.id, ch.id, c.tg_chat_id, c.customer_name, c.username, c.lang, c.bot_id
            """
        ),
        {"provider": TELEGRAM_PROVIDER},
    )

    # 4. Backfill conversations.channel_id / contact_id from their bot/chat.
    bind.execute(
        sa.text(
            """
            UPDATE conversations c
            SET channel_id = ch.id,
                contact_id = con.id
            FROM channels ch
            JOIN contacts con
              ON con.company_id = c.company_id
             AND (con.custom_fields->>'telegram_chat_id')::bigint = c.tg_chat_id
             AND con.custom_fields->>'source' = 'telegram'
            WHERE c.bot_id IS NOT NULL
              AND c.tg_chat_id IS NOT NULL
              AND ch.provider = :provider
              AND ch.external_id = (
                  SELECT b.username FROM bots b WHERE b.id = c.bot_id
              )
              AND (c.channel_id IS NULL OR c.contact_id IS NULL)
            """
        ),
        {"provider": TELEGRAM_PROVIDER},
    )

    # 5. Backfill messages.channel_id / direction / sender_type / delivery_status.
    bind.execute(
        sa.text(
            """
            UPDATE messages m
            SET channel_id = c.channel_id,
                direction = CASE m.role
                    WHEN 'customer' THEN 'inbound'
                    WHEN 'bot' THEN 'outbound'
                    WHEN 'agent' THEN 'outbound'
                    ELSE 'outbound'
                END,
                sender_type = CASE m.role
                    WHEN 'customer' THEN 'contact'
                    WHEN 'bot' THEN 'ai'
                    WHEN 'agent' THEN 'agent'
                    ELSE 'system'
                END,
                delivery_status = 'delivered'
            FROM conversations c
            WHERE m.conversation_id = c.id
              AND c.channel_id IS NOT NULL
              AND (m.channel_id IS NULL OR m.direction IS NULL OR m.sender_type IS NULL)
            """
        )
    )

    # 6. Existing users were the account owners; assign the owner role.
    bind.execute(
        sa.text(
            """
            UPDATE users
            SET role = 'owner'
            WHERE role IS DISTINCT FROM 'owner'
            """
        )
    )


def downgrade() -> None:
    bind = _conn()

    # Reverse the message/conversation/user backfill first (clear FKs).
    bind.execute(
        sa.text(
            """
            UPDATE messages m
            SET channel_id = NULL,
                direction = NULL,
                sender_type = NULL,
                sender_user_id = NULL,
                delivery_status = NULL,
                external_message_id = NULL
            FROM conversations c
            WHERE m.conversation_id = c.id
              AND c.bot_id IS NOT NULL
              AND c.channel_id IS NOT NULL
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE conversations
            SET channel_id = NULL,
                contact_id = NULL
            WHERE bot_id IS NOT NULL
              AND channel_id IS NOT NULL
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE users
            SET role = 'agent'
            WHERE role = 'owner'
            """
        )
    )

    # Remove backfilled channel-agnostic reference data.
    # Deleting channels cascades to contact_identities (channel_id FK cascade).
    bind.execute(
        sa.text(
            "DELETE FROM contact_identities ci USING channels ch "
            "WHERE ci.channel_id = ch.id AND ch.provider = :provider"
        ),
        {"provider": TELEGRAM_PROVIDER},
    )
    bind.execute(
        sa.text(
            "DELETE FROM channels WHERE provider = :provider"
        ),
        {"provider": TELEGRAM_PROVIDER},
    )
    # Drop contacts that were only linked to the removed telegram identities.
    bind.execute(
        sa.text(
            "DELETE FROM contacts con WHERE NOT EXISTS ("
            "    SELECT 1 FROM contact_identities ci WHERE ci.contact_id = con.id"
            ")"
        )
    )
