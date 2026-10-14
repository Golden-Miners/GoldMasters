"""API skeleton health surface tests (01-08 Task 1: surface)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from goldmasters_api.app import create_app


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
