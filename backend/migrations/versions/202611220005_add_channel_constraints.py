"""Add constraints to channel-agnostic schema.

Revision ID: 202611220005
Revises: 202611220004
Create Date: 2026-11-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202611220005"
down_revision: Union[str, None] = "202611220004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Named check constraints so they can be dropped deterministically on downgrade.
CHECKS = {
    "channels": [
        ("channels_provider_check", "provider IN ('telegram','messenger','whatsapp','instagram','dummy-for-tests')"),
        ("channels_status_check", "status IN ('connected','disconnected','error','token_expired')"),
    ],
    "contacts": [
        ("contacts_status_check", "status IN ('active','inactive','blocked','merged')"),
    ],
    "contact_identities": [],
    "conversations": [
        ("conversations_priority_check", "priority IN ('low','normal','high','urgent')"),
    ],
    "messages": [
        ("messages_direction_check", "direction IN ('inbound','outbound')"),
        ("messages_sender_type_check", "sender_type IN ('contact','ai','agent','system')"),
        ("messages_content_type_check", "content_type IN ('text','image','file','audio','video','location','postback','system')"),
        ("messages_delivery_status_check", "delivery_status IN ('queued','sent','delivered','read','failed')"),
    ],
    "users": [
        ("users_role_check", "role IN ('owner','admin','agent')"),
    ],
}


def _check_name(table: str, logical: str) -> str:
    return op.f(f"{table}_{logical}")


def upgrade() -> None:
    # --- Unique constraints ----------------------------------------------

    op.create_unique_constraint(
        op.f("channels_provider_external_id_key"),
        "channels",
        ["provider", "external_id"],
    )
    op.create_unique_constraint(
        op.f("contact_identities_channel_external_user_key"),
        "contact_identities",
        ["channel_id", "external_user_id"],
    )
    op.create_index(
        op.f("messages_channel_external_message_id_key"),
        "messages",
        ["channel_id", "external_message_id"],
        unique=True,
        postgresql_where=sa.text("external_message_id IS NOT NULL"),
    )
    op.create_unique_constraint(
        op.f("processed_events_provider_event_id_key"),
        "processed_events",
        ["provider", "event_id"],
    )

    # --- Check constraints -----------------------------------------------

    for table, checks in CHECKS.items():
        for logical, condition in checks:
            op.create_check_constraint(
                _check_name(table, logical),
                table,
                condition,
            )


def downgrade() -> None:
    # Drop check constraints (reverse order within each table not required).
    for table in reversed(list(CHECKS.keys())):
        for logical, _ in CHECKS[table]:
            op.drop_constraint(
                _check_name(table, logical),
                table,
                type_="check",
            )

    # Drop unique constraints / partial unique index.
    op.drop_constraint(
        op.f("processed_events_provider_event_id_key"),
        "processed_events",
        type_="unique",
    )
    op.drop_index(
        op.f("messages_channel_external_message_id_key"),
        table_name="messages",
    )
    op.drop_constraint(
        op.f("contact_identities_channel_external_user_key"),
        "contact_identities",
        type_="unique",
    )
    op.drop_constraint(
        op.f("channels_provider_external_id_key"),
        "channels",
        type_="unique",
    )
