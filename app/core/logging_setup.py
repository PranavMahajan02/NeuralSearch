"""Logging: JSON lines in production, text in development; every record carries
the request id and passes through the secret redactor.

configure_logging() is called once at import of app.main and also covers the
uvicorn loggers (their access log contains query strings such as OAuth codes).
"""

import json
import logging
import sys
from contextvars import ContextVar

from app.core.clock import utcnow
from app.scheduler.errors import redact_secrets

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


class RedactingFilter(logging.Filter):
    """Redacts tokens/secrets in the final message and stamps the request id.
    Tracebacks are redacted by the formatters (exc_info stays intact for other handlers)."""

    def filter(self, record: logging.LogRecord) -> bool:

        try:
            message = record.getMessage()
        except Exception:  # a broken format string must not kill logging
            message = str(record.msg)

        record.msg = redact_secrets(message)
        record.args = None
        record.request_id = request_id_var.get()

        return True


class TextFormatter(logging.Formatter):
    def formatException(self, ei) -> str:

        return redact_secrets(super().formatException(ei))


class JsonFormatter(TextFormatter):
    def format(self, record: logging.LogRecord) -> str:

        entry = {
            "ts": utcnow().isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False)


TEXT_FORMAT = "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"


def build_handler(log_format: str) -> logging.Handler:

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RedactingFilter())
    handler.setFormatter(JsonFormatter() if log_format == "json" else TextFormatter(TEXT_FORMAT))
    return handler


def configure_logging(log_format: str, level: str = "INFO") -> None:

    handler = build_handler(log_format)

    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())

    # uvicorn installs its own handlers: route them through ours instead.
    for name in _UVICORN_LOGGERS:
        logger = logging.getLogger(name)
        logger.handlers[:] = []
        logger.propagate = True
