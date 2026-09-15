"""Structured logging -- Document 43 EDGE-FR-028 ("Structured logs, metrics and traces use correlation
IDs and redact credentials/raw secrets").
"""

from __future__ import annotations

import json
import logging
import re
from contextvars import ContextVar

_correlation_id: ContextVar[str | None] = ContextVar("edge_correlation_id", default=None)

_REDACT_PATTERNS = [
    re.compile(r'("?(?:password|token|secret|bearer_token|reauth_password|credential)"?\s*[:=]\s*")[^"]*(")', re.IGNORECASE),
]


def set_correlation_id(correlation_id: str | None) -> None:
    _correlation_id.set(correlation_id)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def redact(text: str) -> str:
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub(r"\1***REDACTED***\2", text)
    return text


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = redact(record.getMessage())
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "correlation_id": get_correlation_id(),
        }
        if record.exc_info:
            payload["exc_info"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    root = logging.getLogger("edge")
    root.setLevel(level)
    root.handlers = [handler]
    root.propagate = False