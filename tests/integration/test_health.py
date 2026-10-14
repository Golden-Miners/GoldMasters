"""API skeleton health surface tests (01-08 Tasks 1-2: surface + loopback guard)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from goldmasters_api.app import assert_loopback, create_app


def test_health_returns_five_chain_fields() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["version"], str) and body["version"]
    assert isinstance(body["contract_schema_version"], str) and body["contract_schema_version"]
    assert isinstance(body["config_hash"], str) and body["config_hash"]
    assert isinstance(body["database"]["reachable"], bool)


def test_loopback_guard_accepts_loopback() -> None:
    assert_loopback("127.0.0.1")
    assert_loopback("::1")
    assert_loopback("localhost")


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10", "::"])
def test_loopback_guard_refuses_non_loopback(host: str) -> None:
    with pytest.raises(ValueError, match=host.replace(".", r"\.")):
        assert_loopback(host)


def test_non_loopback_bind_host_fails_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOLDMASTERS_BIND_HOST", "0.0.0.0")
    application = create_app()
    with pytest.raises(ValueError, match="0.0.0.0"), TestClient(application):
        pass  # startup must raise, never serve

