"""Provider adapter registry keyed by provider name."""


from app.channels.base import ChannelAdapter

_REGISTRY: dict[str, type[ChannelAdapter]] = {}


def register(provider: str, adapter_cls: type[ChannelAdapter]) -> None:
    _REGISTRY[provider] = adapter_cls


def get(provider: str) -> type[ChannelAdapter] | None:
    return _REGISTRY.get(provider)


def providers() -> list[str]:
    return sorted(_REGISTRY.keys())


def register_builtin() -> None:
    """Register the builtin Telegram adapter."""
    from app.channels.telegram import TelegramAdapter

    register("telegram", TelegramAdapter)


def autodiscover() -> None:
    """Load entry-point adapters declared under ``teledesk.channels``."""
    try:
        from importlib.metadata import entry_points
    except ImportError:  # pragma: no cover - py<3.8
        return

    try:
        eps = entry_points(group="teledesk.channels")
    except TypeError:  # older importlib.metadata
        eps = entry_points().get("teledesk.channels", [])  # type: ignore[arg-type]

    for ep in eps:
        try:
            cls = ep.load()
        except Exception:
            continue
        if issubclass(cls, ChannelAdapter) and cls is not ChannelAdapter:
            register(ep.name, cls)


def clear() -> None:
    _REGISTRY.clear()
