"""Logging redaction tests (01-09 Task 1): rendered lines are clean JSON."""

from __future__ import annotations

import json

import pytest
import structlog
from goldmasters_api.logging import REDACTED, configure_logging
from pydantic import SecretStr


@pytest.fixture(autouse=True)
def _logging() -> None:
    configure_logging("INFO")
    structlog.contextvars.clear_contextvars()


def _lines(capsys: pytest.CaptureFixture[str]) -> list[str]:
    out = capsys.readouterr().out
    return [line for line in out.splitlines() if line.strip()]


def test_log_line_is_json_with_required_keys(capsys: pytest.CaptureFixture[str]) -> None:
    structlog.contextvars.bind_contextvars(correlation_id="test-id-1")
    structlog.get_logger().info("hello")
    lines = _lines(capsys)
    assert lines, "no rendered log line captured"
    record = json.loads(lines[-1])
    for key in ("event", "level", "timestamp", "correlation_id"):
        assert key in record, key
    assert record["correlation_id"] == "test-id-1"


def test_bound_secret_never_rendered(capsys: pytest.CaptureFixture[str]) -> None:
    structlog.get_logger().info("login", password=SecretStr("bound-secret-1"))
    blob = "\n".join(_lines(capsys))
    assert "bound-secret-1" not in blob
    assert REDACTED in blob


def test_sensitive_key_names_redacted(capsys: pytest.CaptureFixture[str]) -> None:
    structlog.get_logger().info(
        "call", password="hunter2", api_key="AKIA-XYZ", nested={"token": "tok-1"}
    )
    blob = "\n".join(_lines(capsys))
    assert "hunter2" not in blob
    assert "AKIA-XYZ" not in blob
    assert "tok-1" not in blob
    assert REDACTED in blob


def test_secretstr_value_redacted_under_innocuous_key(
    capsys: pytest.CaptureFixture[str],
) -> None:
    structlog.get_logger().info("note", memo=SecretStr("innocuous-key-secret"))
    blob = "\n".join(_lines(capsys))
    assert "innocuous-key-secret" not in blob
    assert REDACTED in blob


def test_nested_secret_redacted(capsys: pytest.CaptureFixture[str]) -> None:
    structlog.get_logger().info(
        "payload", body={"items": [{"authorization": "Bearer abc"}], "other": 1}
    )
    blob = "\n".join(_lines(capsys))
    assert "Bearer abc" not in blob
    assert REDACTED in blob


def test_configure_logging_idempotent(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    first = structlog.get_config()["processors"]
    configure_logging("INFO")
    second = structlog.get_config()["processors"]
    assert len(first) == len(second)
    structlog.get_logger().info("once")
    assert len(_lines(capsys)) == 1, "record rendered more than once"
