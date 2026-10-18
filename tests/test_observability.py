"""Structured logging contract: formatter shapes, ids and lazy setup."""
from __future__ import annotations

import json
import logging
import sys

from easylpac import observability


def _record():
    return logging.LogRecord(
        "easylpac.test", logging.INFO, __file__, 42, "hello %s", ("world",), None
    )


def _record_with_traceback():
    try:
        raise ValueError("boom")
    except ValueError:
        return logging.LogRecord(
            "easylpac.test", logging.ERROR, __file__, 1, "failed", (), sys.exc_info()
        )


def test_json_formatter_emits_one_object_with_correlation_fields():
    payload = json.loads(observability._JsonFormatter().format(_record()))
    assert payload["level"] == "INFO"
    assert payload["logger"] == "easylpac.test"
    assert payload["message"] == "hello world"
    assert payload["service"] == "easylpac"
    assert payload["request_id"] == observability.request_id()


def test_json_formatter_serialises_a_traceback():
    payload = json.loads(observability._JsonFormatter().format(_record_with_traceback()))
    assert "ValueError: boom" in payload["exception"]


def test_text_formatter_renders_a_single_line():
    line = observability._TextFormatter().format(_record())
    assert "level=info" in line
    assert "logger=easylpac.test" in line
    assert "msg='hello world'" in line


def test_text_formatter_appends_the_traceback():
    line = observability._TextFormatter().format(_record_with_traceback())
    assert "ValueError: boom" in line


def test_request_ids_can_be_pinned_and_generated():
    assert observability.set_request_id("abc") == "abc"
    assert observability.request_id() == "abc"
    generated = observability.set_request_id(None)
    assert len(generated) == 32
    assert observability.request_id() == generated


def test_new_request_id_is_unique():
    assert observability.new_request_id() != observability.new_request_id()


def test_log_event_carries_the_event_name(capsys):
    observability.configure_logging("INFO", json_output=True)
    observability.log_event(observability.get_logger("easylpac.test"), "thing_happened", n=1)
    line = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["event"] == "thing_happened"
    assert payload["n"] == 1


def test_configure_logging_reads_log_json_from_the_environment(monkeypatch):
    monkeypatch.setenv("LOG_JSON", "0")
    observability.configure_logging("INFO", json_output=None)
    assert isinstance(logging.getLogger().handlers[-1].formatter, observability._TextFormatter)

    monkeypatch.setenv("LOG_JSON", "yes")
    observability.configure_logging("INFO", json_output=None)
    assert isinstance(logging.getLogger().handlers[-1].formatter, observability._JsonFormatter)


def test_get_logger_configures_logging_on_first_use(monkeypatch):
    monkeypatch.setattr(observability, "_CONFIGURED", False)
    logger = observability.get_logger("easylpac.lazy")
    assert isinstance(logger, logging.Logger)
    assert observability._CONFIGURED is True


def test_stdout_handler_flush_tolerates_a_stream_without_flush(monkeypatch):
    handler = observability._StdoutHandler()
    monkeypatch.setattr(observability.sys, "stdout", object())
    handler.flush()
