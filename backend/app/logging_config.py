import json
import logging
import re
import traceback
from datetime import datetime, timezone

from app.request_context import request_id_context


_BOT_TOKEN_PATH = re.compile(r"(?i)(/bot)[^/\s?#]+(/)")
_AUTHORIZATION = re.compile(
    r"(?i)\bauthorization\b(\s*[:=]\s*)(?:[a-z]+\s+)?[^\s,;]+"
)
_URL_PASSWORD = re.compile(r"(?i)(://[^:/@\s]+:)[^@\s]+(@)")
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]+=*")
_SECRET_ASSIGNMENT = re.compile(
    r"""(?ix)
    \b(access[_-]?token|app[\s_-]?secret|client[\s_-]?secret|
       verify[_-]?token|password|token)\b
    (\s*[:=]\s*)
    (?:"[^"]*"|'[^']*'|[^&\s,;]+)
    """
)


def redact_sensitive_data(value: str) -> str:
    value = _BOT_TOKEN_PATH.sub(r"\1[REDACTED]\2", value)
    value = _AUTHORIZATION.sub(r"authorization\1[REDACTED]", value)
    value = _URL_PASSWORD.sub(r"\1[REDACTED]\2", value)
    value = _BEARER.sub("Bearer [REDACTED]", value)
    return _SECRET_ASSIGNMENT.sub(r"\1\2[REDACTED]", value)


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)

        record.msg = redact_sensitive_data(message)
        record.args = ()

        if record.exc_info:
            record.exc_text = redact_sensitive_data(
                "".join(traceback.format_exception(*record.exc_info))
            )
            record.exc_info = None
        elif record.exc_text:
            record.exc_text = redact_sensitive_data(record.exc_text)

        if record.stack_info:
            record.stack_info = redact_sensitive_data(record.stack_info)

        record.request_id = request_id_context.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_text:
            payload["exception"] = record.exc_text
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        root.addHandler(logging.StreamHandler())

    loggers = [root]
    loggers.extend(
        logger
        for logger in logging.root.manager.loggerDict.values()
        if isinstance(logger, logging.Logger)
    )
    for logger in loggers:
        for handler in logger.handlers:
            if not any(
                isinstance(item, RedactionFilter)
                for item in handler.filters
            ):
                handler.addFilter(RedactionFilter())
            handler.setFormatter(JsonFormatter())
