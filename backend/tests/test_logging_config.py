import logging
import sys

from app.logging_config import JsonFormatter, RedactionFilter


def _record(message, exc_info=None):
    return logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=exc_info,
    )


def test_redacts_credentials_from_messages():
    record = _record(
        "request /bot123:BOT_SECRET/sendMessage?access_token=ACCESS_SECRET "
        "Authorization: Bearer AUTH_SECRET Authorization: Basic BASIC_SECRET "
        "password=PASSWORD_SECRET app secret=APP_SECRET "
        "postgresql://user:URL_PASSWORD@database/app"
    )

    RedactionFilter().filter(record)
    output = JsonFormatter().format(record)

    for secret in (
        "BOT_SECRET",
        "ACCESS_SECRET",
        "AUTH_SECRET",
        "BASIC_SECRET",
        "PASSWORD_SECRET",
        "APP_SECRET",
        "URL_PASSWORD",
    ):
        assert secret not in output
    assert "[REDACTED]" in output


def test_redacts_credentials_from_exception_text():
    try:
        raise RuntimeError(
            "request failed for /bot123:BOT_SECRET/sendMessage "
            "with access_token=ACCESS_SECRET"
        )
    except RuntimeError:
        exception_info = sys.exc_info()

    record = _record("Telegram request failed", exception_info)
    RedactionFilter().filter(record)
    output = JsonFormatter().format(record)

    assert "BOT_SECRET" not in output
    assert "ACCESS_SECRET" not in output
    assert "RuntimeError" in output
