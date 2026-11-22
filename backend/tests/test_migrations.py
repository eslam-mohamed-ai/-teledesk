import importlib
import os

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from alembic.command import downgrade, upgrade
from alembic.config import Config

import app.config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALEMBIC_INI = os.path.join(ROOT, "backend", "alembic.ini")

EXPECTED_TABLES = [
    "companies",
    "bots",
    "conversations",
    "messages",
    "users",
    "channels",
    "contacts",
    "contact_identities",
    "tags",
    "contact_tags",
    "conversation_tags",
    "attachments",
    "processed_events",
    "invitations",
    "audit_log",
    "internal_notes",
    "canned_replies",
    "contact_field_definitions",
]


def _dsn() -> str | None:
    return os.environ.get("TEST_DATABASE_URL")


def _reload_settings(dsn: str) -> None:
    """Point the running app config (read by alembic env.py) at the test DB."""
    os.environ["DATABASE_URL"] = dsn
    importlib.reload(app.config)


def _alembic_cfg(dsn: str) -> Config:
    _reload_settings(dsn)
    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", dsn)
    return cfg


def _reset_db(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


@pytest.fixture
def alembic_cfg():
    dsn = _dsn()
    if not dsn:
        pytest.fail("TEST_DATABASE_URL is required for migration tests. Run: make test")
    return _alembic_cfg(dsn)


def _tables(engine) -> set[str]:
    return set(inspect(engine).get_table_names())


class TestMigrationFreshDb:
    def test_upgrade_head_creates_all_expected_tables(self, alembic_cfg):
        dsn = _dsn()
        engine = create_engine(dsn)
        _reset_db(engine)
        try:
            upgrade(alembic_cfg, "head")
            tables = _tables(engine)
            for expected in EXPECTED_TABLES:
                assert expected in tables, f"missing table {expected}"
        finally:
            downgrade(alembic_cfg, "base")
            engine.dispose()

    def test_downgrade_base_leaves_empty_schema(self, alembic_cfg):
        dsn = _dsn()
        engine = create_engine(dsn)
        _reset_db(engine)
        try:
            upgrade(alembic_cfg, "head")
            downgrade(alembic_cfg, "base")
            tables = _tables(engine)
            # Only the alembic version bookkeeping should remain conceptually;
            # all application tables must be gone.
            for expected in EXPECTED_TABLES:
                assert expected not in tables, f"table {expected} still present after downgrade"
        finally:
            engine.dispose()


class TestMigrationBackfill:
    def _seed_legacy(self, conn) -> None:
        conn.execute(
            text(
                "INSERT INTO companies (id, name, industry, description, welcome, tone, "
                "reply_language, handoff_on_request, handoff_out_of_scope, "
                "handoff_keywords, handoff_after_two, work_hours, plan, created_at) "
                "VALUES (1, 'Acme', 'retail', '', 'أهلا', 'friendly', 'ar', true, true, "
                "'شكوى', false, '', 'free', now())"
            )
        )
        conn.execute(
            text(
                "INSERT INTO bots (id, company_id, token_encrypted, username, name, "
                "secret, active, connected, created_at) VALUES "
                "(1, 1, 'enc-token', 'bot_acme', 'Acme Bot', 's3cret', true, true, now())"
            )
        )
        conn.execute(
            text(
                "INSERT INTO conversations (id, company_id, bot_id, tg_chat_id, "
                "customer_name, username, lang, status, handoff_reason, note, "
                "last_preview, last_message_at, created_at) VALUES "
                "(1, 1, 1, 100, 'عميل', '', 'ar', 'bot', '', '', '', now(), now()), "
                "(2, 1, 1, 200, 'عميل2', '', 'ar', 'bot', '', '', '', now(), now())"
            )
        )
        conn.execute(
            text(
                "INSERT INTO messages (id, company_id, conversation_id, role, content, "
                "source, flag, unanswered, latency_ms, created_at) VALUES "
                "(1, 1, 1, 'customer', 'مرحبا', NULL, NULL, false, NULL, now()), "
                "(2, 1, 1, 'bot', 'أهلاً بك', NULL, NULL, false, NULL, now())"
            )
        )
        conn.execute(
            text(
                "INSERT INTO users (id, company_id, name, email, password_hash, created_at) "
                "VALUES (1, 1, 'User', 'u@example.test', 'hash', now())"
            )
        )

    def _count(self, conn, table, where=None) -> int:
        sql = f"SELECT COUNT(*) FROM {table}"
        if where:
            sql += f" WHERE {where}"
        return conn.execute(text(sql)).scalar_one()

    def test_backfill_preserves_legacy_data(self, alembic_cfg):
        dsn = _dsn()
        engine = create_engine(dsn)
        _reset_db(engine)
        try:
            # Baseline schema only, then seed legacy Telegram data.
            upgrade(alembic_cfg, "202611220001")
            with engine.begin() as conn:
                self._seed_legacy(conn)

            before_bots = self._count(engine.connect(), "bots")
            before_conversations = self._count(engine.connect(), "conversations")
            before_messages = self._count(engine.connect(), "messages")

            # Run remaining migrations including the backfill (0004).
            upgrade(alembic_cfg, "head")

            with engine.connect() as conn:
                # One channel per bot.
                assert self._count(conn, "channels") == before_bots == 1
                # One contact per distinct (bot_id, tg_chat_id).
                distinct = conn.execute(
                    text("SELECT COUNT(DISTINCT (bot_id, tg_chat_id)) FROM conversations")
                ).scalar_one()
                assert self._count(conn, "contacts") == distinct == 2
                # One identity per contact.
                assert self._count(conn, "contact_identities") == 2
                # Every legacy conversation backfilled with channel + contact.
                orphans = self._count(
                    conn,
                    "conversations",
                    "bot_id IS NOT NULL AND tg_chat_id IS NOT NULL "
                    "AND (channel_id IS NULL OR contact_id IS NULL)",
                )
                assert orphans == 0
                # Every message in a backfilled conversation backfilled.
                msg_orphans = self._count(
                    conn,
                    "messages",
                    "channel_id IS NULL OR direction IS NULL OR sender_type IS NULL "
                    "OR delivery_status IS NULL",
                )
                assert msg_orphans == 0
                # Existing user promoted to owner.
                assert self._count(conn, "users", "role = 'owner'") == 1
                # Legacy data not lost.
                assert self._count(conn, "bots") == before_bots
                assert self._count(conn, "conversations") == before_conversations
                assert self._count(conn, "messages") == before_messages
        finally:
            downgrade(alembic_cfg, "base")
            engine.dispose()

    def test_uniqueness_constraints_enforced(self, alembic_cfg):
        dsn = _dsn()
        engine = create_engine(dsn)
        _reset_db(engine)
        try:
            upgrade(alembic_cfg, "head")
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO channels (company_id, provider, external_id, "
                        "display_name, status, active, created_at, updated_at) "
                        "VALUES (1, 'telegram', 'dup_bot', 'Dup', 'connected', true, now(), now())"
                    )
                )
                # Duplicate (provider, external_id) must be rejected.
                with pytest.raises(IntegrityError):
                    conn.execute(
                        text(
                            "INSERT INTO channels (company_id, provider, external_id, "
                            "display_name, status, active, created_at, updated_at) "
                            "VALUES (1, 'telegram', 'dup_bot', 'Dup2', 'connected', true, now(), now())"
                        )
                    )
                    conn.rollback()
                # Duplicate processed event must be rejected.
                conn.execute(
                    text(
                        "INSERT INTO processed_events (provider, event_id, received_at) "
                        "VALUES ('telegram', 'evt_1', now())"
                    )
                )
                with pytest.raises(IntegrityError):
                    conn.execute(
                        text(
                            "INSERT INTO processed_events (provider, event_id, received_at) "
                            "VALUES ('telegram', 'evt_1', now())"
                        )
                    )
                    conn.rollback()
        finally:
            downgrade(alembic_cfg, "base")
            engine.dispose()
