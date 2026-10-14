"""Correlation ID + on-disk trace tests (01-09 Task 2)."""

from __future__ import annotations

import pathlib

import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from goldmasters_api.middleware import CorrelationIdMiddleware, current_correlation_id
from goldmasters_api.tracing import configure_tracing, shutdown_tracing


def _test_app() -> FastAPI:
    application = FastAPI()
    application.add_middleware(CorrelationIdMiddleware)

    @application.get("/ping")
    def ping() -> dict[str, str]:
        return {"correlation_id": current_correlation_id() or "missing"}

    return application


def test_two_requests_get_different_ids() -> None:
    with TestClient(_test_app()) as client:
        first = client.get("/ping").json()["correlation_id"]
        second = client.get("/ping").json()["correlation_id"]
    assert first != second
    assert first != "missing"


def test_response_header_matches_log_id() -> None:
    structlog.contextvars.clear_contextvars()
    with TestClient(_test_app()) as client:
        response = client.get("/ping")
    assert response.headers["X-Correlation-ID"] == response.json()["correlation_id"]


def test_inbound_header_not_adopted() -> None:
    with TestClient(_test_app()) as client:
        response = client.get("/ping", headers={"X-Correlation-ID": "forged-id"})
    assert response.json()["correlation_id"] != "forged-id"
    assert response.headers["X-Correlation-ID"] != "forged-id"


def test_context_cleared_after_response() -> None:
    with TestClient(_test_app()):
        pass
    assert current_correlation_id() is None


def test_span_written_to_trace_file(tmp_path: pathlib.Path) -> None:
    trace_file = tmp_path / "traces.jsonl"
    configure_tracing(str(trace_file))
    try:
        with TestClient(_test_app()) as client:
            response = client.get("/ping")
        correlation_id = response.json()["correlation_id"]
    finally:
        shutdown_tracing()
    content = trace_file.read_text(encoding="utf-8")
    assert correlation_id in content
