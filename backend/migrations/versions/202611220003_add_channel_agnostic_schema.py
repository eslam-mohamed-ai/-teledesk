"""Add channel-agnostic tables and columns (additive, backwards compatible).

Revision ID: 202611220003
Revises: 202611220002
Create Date: 2026-11-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202611220003"
down_revision: Union[str, None] = "202611220002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _jsonb() -> postgresql.JSONB:
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    # --- New tables -------------------------------------------------------

    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("username", sa.String(length=120), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True),
        sa.Column("credentials_key_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("webhook_secret", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="connected"),
        sa.Column("status_reason", sa.String(length=200), nullable=True),
        sa.Column("last_webhook_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", _jsonb(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name=op.f("channels_company_id_fkey"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("channels_pkey")),
    )
    op.create_index(op.f("ix_channels_company_id"), "channels", ["company_id"])
    op.create_index(op.f("ix_channels_provider"), "channels", ["provider"])

    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("first_name", sa.String(length=120), nullable=True),
        sa.Column("last_name", sa.String(length=120), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("country", sa.String(length=8), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("custom_fields", _jsonb(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merged_into_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name=op.f("contacts_company_id_fkey"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["merged_into_id"], ["contacts.id"],
            name=op.f("contacts_merged_into_id_fkey"), ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("contacts_pkey")),
    )
    op.create_index(op.f("ix_contacts_company_id"), "contacts", ["company_id"])
    op.create_index(
        "ix_contacts_company_id_email",
        "contacts",
        ["company_id", "email"],
        unique=False,
        postgresql_where=sa.text("email IS NOT NULL"),
    )
    op.create_index(
        "ix_contacts_company_id_phone",
        "contacts",
        ["company_id", "phone"],
        unique=False,
        postgresql_where=sa.text("phone IS NOT NULL"),
    )

    op.create_table(
        "contact_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contact_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column("profile_snapshot", _jsonb(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"],
            name=op.f("contact_identities_contact_id_fkey"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"], ["channels.id"],
            name=op.f("contact_identities_channel_id_fkey"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("contact_identities_pkey")),
    )
    op.create_index(op.f("ix_contact_identities_contact_id"), "contact_identities", ["contact_id"])
    op.create_index(op.f("ix_contact_identities_channel_id"), "contact_identities", ["channel_id"])

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name=op.f("tags_company_id_fkey"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("tags_pkey")),
    )
    op.create_index(op.f("ix_tags_company_id"), "tags", ["company_id"])
    op.create_index(op.f("ix_tags_name"), "tags", ["name"], unique=False)

    op.create_table(
        "contact_tags",
        sa.Column("contact_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"],
            name=op.f("contact_tags_contact_id_fkey"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tags.id"],
            name=op.f("contact_tags_tag_id_fkey"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("contact_id", "tag_id", name=op.f("contact_tags_pkey")),
    )

    op.create_table(
        "conversation_tags",
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"],
            name=op.f("conversation_tags_conversation_id_fkey"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tags.id"],
            name=op.f("conversation_tags_tag_id_fkey"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("conversation_id", "tag_id", name=op.f("conversation_tags_pkey")),
    )

    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("mime", sa.String(length=120), nullable=True),
        sa.Column("size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("original_url", sa.String(length=1000), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"], ["messages.id"],
            name=op.f("attachments_message_id_fkey"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("attachments_pkey")),
    )
    op.create_index(op.f("ix_attachments_message_id"), "attachments", ["message_id"])

    op.create_table(
        "processed_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("processed_events_pkey")),
    )
    op.create_index(op.f("ix_processed_events_provider"), "processed_events", ["provider"])
    op.create_index(
        "ix_processed_events_provider_event_id",
        "processed_events",
        ["provider", "event_id"],
        unique=False,
    )

    op.create_table(
        "invitations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="agent"),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name=op.f("invitations_company_id_fkey"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("invitations_pkey")),
    )
    op.create_index(op.f("ix_invitations_company_id"), "invitations", ["company_id"])
    op.create_index(op.f("ix_invitations_email"), "invitations", ["email"], unique=False)
    op.create_index(op.f("ix_invitations_token_hash"), "invitations", ["token_hash"], unique=True)

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target", sa.String(length=200), nullable=True),
        sa.Column("metadata", _jsonb(), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name=op.f("audit_log_company_id_fkey"), ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("audit_log_user_id_fkey"), ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("audit_log_pkey")),
    )
    op.create_index(op.f("ix_audit_log_company_id"), "audit_log", ["company_id"])
    op.create_index(op.f("ix_audit_log_created_at"), "audit_log", ["created_at"])

    op.create_table(
        "internal_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"],
            name=op.f("internal_notes_conversation_id_fkey"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("internal_notes_user_id_fkey"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("internal_notes_pkey")),
    )
    op.create_index(op.f("ix_internal_notes_conversation_id"), "internal_notes", ["conversation_id"])

    op.create_table(
        "canned_replies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("shortcut", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name=op.f("canned_replies_company_id_fkey"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("canned_replies_pkey")),
    )
    op.create_index(op.f("ix_canned_replies_company_id"), "canned_replies", ["company_id"])

    op.create_table(
        "contact_field_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False, server_default="text"),
        sa.Column("required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ask_in_chat", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("prompt_text", sa.String(length=500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"],
            name=op.f("contact_field_definitions_company_id_fkey"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("contact_field_definitions_pkey")),
    )
    op.create_index(op.f("ix_contact_field_definitions_company_id"), "contact_field_definitions", ["company_id"])

    # --- New columns on existing tables (additive, nullable) --------------

    op.add_column(
        "conversations",
        sa.Column("channel_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("contact_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("assignee_user_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("priority", sa.String(length=16), nullable=True, server_default="normal"),
    )
    op.add_column(
        "conversations",
        sa.Column("last_inbound_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("unread_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "conversations",
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("closed_by", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_conversations_channel_id"),
        "conversations",
        ["channel_id"],
    )
    op.create_index(
        op.f("ix_conversations_contact_id"),
        "conversations",
        ["contact_id"],
    )
    op.create_index(
        op.f("ix_conversations_assignee_user_id"),
        "conversations",
        ["assignee_user_id"],
    )
    op.create_index(
        "ix_conversations_company_status_last_message",
        "conversations",
        ["company_id", "status", "last_message_at"],
    )

    op.add_column(
        "messages",
        sa.Column("channel_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("direction", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("sender_type", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("sender_user_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("content_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("external_message_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("delivery_status", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("error_code", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("reply_to_message_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_messages_channel_id"),
        "messages",
        ["channel_id"],
    )
    op.create_index(
        op.f("ix_messages_direction"),
        "messages",
        ["direction"],
    )
    op.create_index(
        op.f("ix_messages_external_message_id"),
        "messages",
        ["external_message_id"],
    )
    op.create_index(
        op.f("ix_messages_sender_user_id"),
        "messages",
        ["sender_user_id"],
    )

    op.add_column(
        "users",
        sa.Column("role", sa.String(length=32), nullable=False, server_default="agent"),
    )
    op.create_index(op.f("ix_users_role"), "users", ["role"])

    # New foreign keys on existing tables.
    op.create_foreign_key(
        op.f("conversations_channel_id_fkey"),
        "conversations", "channels",
        ["channel_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("conversations_contact_id_fkey"),
        "conversations", "contacts",
        ["contact_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("conversations_assignee_user_id_fkey"),
        "conversations", "users",
        ["assignee_user_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("conversations_closed_by_fkey"),
        "conversations", "users",
        ["closed_by"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("messages_channel_id_fkey"),
        "messages", "channels",
        ["channel_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("messages_sender_user_id_fkey"),
        "messages", "users",
        ["sender_user_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("messages_reply_to_message_id_fkey"),
        "messages", "messages",
        ["reply_to_message_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Drop foreign keys added on existing tables first.
    op.drop_constraint(op.f("messages_reply_to_message_id_fkey"), "messages", type_="foreignkey")
    op.drop_constraint(op.f("messages_sender_user_id_fkey"), "messages", type_="foreignkey")
    op.drop_constraint(op.f("messages_channel_id_fkey"), "messages", type_="foreignkey")
    op.drop_constraint(op.f("conversations_closed_by_fkey"), "conversations", type_="foreignkey")
    op.drop_constraint(op.f("conversations_assignee_user_id_fkey"), "conversations", type_="foreignkey")
    op.drop_constraint(op.f("conversations_contact_id_fkey"), "conversations", type_="foreignkey")
    op.drop_constraint(op.f("conversations_channel_id_fkey"), "conversations", type_="foreignkey")

    # Drop new columns from existing tables.
    op.drop_column("users", "role")
    op.drop_column("messages", "reply_to_message_id")
    op.drop_column("messages", "error_message")
    op.drop_column("messages", "error_code")
    op.drop_column("messages", "delivery_status")
    op.drop_column("messages", "external_message_id")
    op.drop_column("messages", "content_type")
    op.drop_column("messages", "sender_user_id")
    op.drop_column("messages", "sender_type")
    op.drop_column("messages", "direction")
    op.drop_column("messages", "channel_id")
    op.drop_column("conversations", "closed_by")
    op.drop_column("conversations", "resolved_at")
    op.drop_column("conversations", "first_response_at")
    op.drop_column("conversations", "unread_count")
    op.drop_column("conversations", "last_inbound_at")
    op.drop_column("conversations", "priority")
    op.drop_column("conversations", "assignee_user_id")
    op.drop_column("conversations", "contact_id")
    op.drop_column("conversations", "channel_id")

    # Drop new tables in reverse dependency order.
    op.drop_table("contact_field_definitions")
    op.drop_table("canned_replies")
    op.drop_table("internal_notes")
    op.drop_table("audit_log")
    op.drop_table("invitations")
    op.drop_table("processed_events")
    op.drop_table("attachments")
    op.drop_table("conversation_tags")
    op.drop_table("contact_tags")
    op.drop_table("tags")
    op.drop_table("contact_identities")
    op.drop_table("contacts")
    op.drop_table("channels")
