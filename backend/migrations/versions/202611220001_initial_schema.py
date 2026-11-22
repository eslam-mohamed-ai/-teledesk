"""Initial schema baseline.

Revision ID: 202611220001
Revises:
Create Date: 2026-11-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector


revision: str = "202611220001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("industry", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("welcome", sa.Text(), nullable=False),
        sa.Column("tone", sa.String(length=20), nullable=False),
        sa.Column("reply_language", sa.String(length=10), nullable=False),
        sa.Column("handoff_on_request", sa.Boolean(), nullable=False),
        sa.Column("handoff_out_of_scope", sa.Boolean(), nullable=False),
        sa.Column("handoff_keywords", sa.Text(), nullable=False),
        sa.Column("handoff_after_two", sa.Boolean(), nullable=False),
        sa.Column("work_hours", sa.String(length=200), nullable=False),
        sa.Column("plan", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("companies_pkey")),
    )
    op.create_table(
        "bots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("token_encrypted", sa.String(length=500), nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("secret", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("connected", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("bots_company_id_fkey"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("bots_pkey")),
        sa.UniqueConstraint("username", name=op.f("bots_username_key")),
    )
    op.create_index(
        op.f("ix_bots_company_id"),
        "bots",
        ["company_id"],
        unique=False,
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error", sa.String(length=300), nullable=False),
        sa.Column("storage_key", sa.String(length=400), nullable=False),
        sa.Column("uses", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("documents_company_id_fkey"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("documents_pkey")),
    )
    op.create_index(
        op.f("ix_documents_company_id"),
        "documents",
        ["company_id"],
        unique=False,
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=300), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("users_company_id_fkey"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("users_pkey")),
    )
    op.create_index(
        op.f("ix_users_email"),
        "users",
        ["email"],
        unique=True,
    )
    op.create_index(
        op.f("ix_users_company_id"),
        "users",
        ["company_id"],
        unique=False,
    )
    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("chunks_company_id_fkey"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("chunks_document_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("chunks_pkey")),
    )
    op.create_index(
        op.f("ix_chunks_company_id"),
        "chunks",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_chunks_document_id"),
        "chunks",
        ["document_id"],
        unique=False,
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("bot_id", sa.Integer(), nullable=False),
        sa.Column("tg_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_name", sa.String(length=200), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("lang", sa.String(length=5), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("handoff_reason", sa.String(length=200), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("last_preview", sa.String(length=200), nullable=False),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bot_id"],
            ["bots.id"],
            name=op.f("conversations_bot_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("conversations_company_id_fkey"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("conversations_pkey")),
    )
    op.create_index(
        op.f("ix_conversations_company_id"),
        "conversations",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversations_tg_chat_id"),
        "conversations",
        ["tg_chat_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversations_bot_id"),
        "conversations",
        ["bot_id"],
        unique=False,
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=250), nullable=True),
        sa.Column("flag", sa.String(length=20), nullable=True),
        sa.Column("unanswered", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("messages_company_id_fkey"),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("messages_conversation_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("messages_pkey")),
    )
    op.create_index(
        op.f("ix_messages_company_id"),
        "messages",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_messages_conversation_id"),
        "messages",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_messages_created_at"),
        "messages",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("chunks")
    op.drop_table("users")
    op.drop_table("documents")
    op.drop_table("bots")
    op.drop_table("companies")
