import json
import logging

from runtime.observability.logging_setup import StructuredFormatter, get_correlation_id, redact, set_correlation_id


def test_redact_masks_password_and_token_fields():
    text = '{"password": "hunter2", "bearer_token": "sid_abc.def", "note": "ok"}'
    redacted = redact(text)
    assert "hunter2" not in redacted
    assert "sid_abc.def" not in redacted
    assert '"note": "ok"' in redacted


def test_structured_formatter_includes_correlation_id():
    set_correlation_id("corr-123")
    try:
        record = logging.LogRecord("edge.test", logging.INFO, __file__, 1, "hello", None, None)
        formatted = json.loads(StructuredFormatter().format(record))
        assert formatted["correlation_id"] == "corr-123"
        assert formatted["message"] == "hello"
        assert formatted["level"] == "INFO"
    finally:
        set_correlation_id(None)


def test_structured_formatter_redacts_message_content():
    record = logging.LogRecord("edge.test", logging.WARNING, __file__, 1, 'token: "sid_super_secret"', None, None)
    formatted = json.loads(StructuredFormatter().format(record))
    assert "sid_super_secret" not in formatted["message"]


def test_get_correlation_id_defaults_to_none():
    assert get_correlation_id() is None