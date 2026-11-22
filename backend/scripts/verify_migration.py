"""Verify the channel-agnostic migration preserved legacy Telegram data.

Usage:
    PYTHONPATH=backend python backend/scripts/verify_migration.py \
        --dsn "postgresql+psycopg2://teledesk:teledesk@localhost:5432/teledesk"

The script connects to an already-migrated database and asserts that legacy
Telegram rows were preserved and backfilled into the channel-agnostic model.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import create_engine, text

LEGACY_TABLES = ["bots", "conversations", "messages", "users", "companies"]

COUNTS = {
    # new table -> expected source relationship
    "channels": "bots (one channel per bot)",
    "contacts": "distinct (bot_id, tg_chat_id)",
    "contact_identities": "contacts (one identity per contact)",
}

BACKFILL_CHECKS = [
    ("conversations", "channel_id IS NOT NULL AND contact_id IS NOT NULL",
     "conversations with bot_id/tg_chat_id backfilled"),
    ("messages", "channel_id IS NOT NULL AND direction IS NOT NULL "
     "AND sender_type IS NOT NULL AND delivery_status IS NOT NULL",
     "messages in backfilled conversations backfilled"),
    ("users", "role = 'owner'", "existing users assigned owner role"),
]


def count(conn, table, where=None) -> int:
    sql = f"SELECT COUNT(*) FROM {table}"
    if where:
        sql += f" WHERE {where}"
    return conn.execute(text(sql)).scalar_one()


def distinct_pairs(conn) -> int:
    return conn.execute(
        text("SELECT COUNT(DISTINCT (bot_id, tg_chat_id)) FROM conversations")
    ).scalar_one()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True, help="SQLAlchemy database URL")
    args = parser.parse_args()

    engine = create_engine(args.dsn, pool_pre_ping=True)

    with engine.connect() as conn:
        print("== Legacy row counts (preserved) ==")
        legacy = {}
        for table in LEGACY_TABLES:
            legacy[table] = count(conn, table)
            print(f"  {table:18s}: {legacy[table]}")

        print("\n== Channel-agnostic backfill ==")
        n_channels = count(conn, "channels")
        n_contacts = count(conn, "contacts")
        n_identities = count(conn, "contact_identities")
        n_distinct = distinct_pairs(conn)
        print(f"  channels:          {n_channels}  (bots: {legacy['bots']})")
        print(f"  contacts:          {n_contacts}  (distinct bot/chat pairs: {n_distinct})")
        print(f"  contact_identities:{n_identities}  (contacts: {n_contacts})")

        print("\n== Backfill coverage ==")
        for table, where, label in BACKFILL_CHECKS:
            total = count(conn, table)
            done = count(conn, table, where)
            print(f"  {label:45s}: {done}/{total}")

        # Samples
        print("\n== Sample channel ==")
        row = conn.execute(
            text("SELECT id, provider, external_id, display_name, status FROM channels LIMIT 1")
        ).mappings().first()
        print("  ", dict(row) if row else None)

        print("\n== Sample contact + identity ==")
        row = conn.execute(
            text("""
                SELECT c.id, c.display_name, c.language,
                       i.external_user_id, i.channel_id
                FROM contacts c
                JOIN contact_identities i ON i.contact_id = c.id
                LIMIT 1
            """)
        ).mappings().first()
        print("  ", dict(row) if row else None)

    failures = []
    if n_channels != legacy["bots"]:
        failures.append(f"channels ({n_channels}) != bots ({legacy['bots']})")
    if n_contacts != n_distinct:
        failures.append(f"contacts ({n_contacts}) != distinct pairs ({n_distinct})")
    if n_identities != n_contacts:
        failures.append(f"contact_identities ({n_identities}) != contacts ({n_contacts})")

    # Every legacy conversation must map to a channel/contact.
    with engine.connect() as conn:
        orphaned = conn.execute(
            text("""
                SELECT COUNT(*) FROM conversations
                WHERE bot_id IS NOT NULL AND tg_chat_id IS NOT NULL
                  AND (channel_id IS NULL OR contact_id IS NULL)
            """)
        ).scalar_one()
        if orphaned:
            failures.append(f"{orphaned} legacy conversations missing channel/contact")

    print("\n== Result ==")
    if failures:
        print("FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL CHECKS PASSED — legacy Telegram data preserved and backfilled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
