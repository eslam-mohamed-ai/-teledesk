"""Provider metadata registry.

The Channels page is driven entirely by this registry. To add a provider, add
one entry here; the frontend renders it from ``GET /api/channels/providers``
without any page edits. ``available`` controls whether the provider can be
connected today (WhatsApp/Instagram ship as "coming soon").
"""

from __future__ import annotations

from typing import Any

PROVIDER_METADATA: list[dict[str, Any]] = [
    {
        "id": "telegram",
        "label": "Telegram",
        "available": True,
        "coming_soon": False,
        "description": "Connect a Telegram bot token to receive messages.",
        "fields": [
            {"key": "bot_token", "label": "Bot token", "type": "password", "required": True},
        ],
    },
    {
        "id": "messenger",
        "label": "Messenger",
        "available": True,
        "coming_soon": False,
        "description": "Connect a Meta page and access token.",
        "fields": [
            {"key": "page_id", "label": "Page ID", "type": "text", "required": True},
            {"key": "page_access_token", "label": "Page access token", "type": "password", "required": True},
        ],
    },
    {
        "id": "whatsapp",
        "label": "WhatsApp",
        "available": False,
        "coming_soon": True,
        "description": "WhatsApp Business Cloud API support is on the roadmap.",
        "fields": [],
    },
    {
        "id": "instagram",
        "label": "Instagram",
        "available": False,
        "coming_soon": True,
        "description": "Instagram messaging support is on the roadmap.",
        "fields": [],
    },
]


def providers() -> list[dict[str, Any]]:
    """Return provider metadata in display order."""
    return [dict(item, fields=[dict(f) for f in item.get("fields", [])]) for item in PROVIDER_METADATA]