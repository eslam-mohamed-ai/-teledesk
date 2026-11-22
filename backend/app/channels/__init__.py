"""Channel adapters: provider boundary for the omnichannel pipeline."""

from app.channels.registry import autodiscover, get, register, providers
from app.channels.telegram import TelegramAdapter

__all__ = ["autodiscover", "get", "register", "providers", "TelegramAdapter"]
