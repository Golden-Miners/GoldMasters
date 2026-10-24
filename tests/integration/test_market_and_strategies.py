"""Phase 2 integration tests: Market Data and Provider Selection.

Tests real API behavior against the running FastAPI server:

- Market bars endpoint fails closed when MT5 terminal is unavailable (503)
- Strategies endpoint returns all 10 agents, all disabled
- Endpoints return proper schema shapes per Schema.md

No invented data: all assertions are against real API responses. When the
MT5 terminal is not running, the market bars endpoint returns a structured
failure — never invented OHLC values.

Run: uv run pytest tests/integration/test_market_and_strategies.py -x -q
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from goldmasters_api.app import create_app


@pytest.fixture(autouse=True)
def _database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Required key since 01-10: point the suite at an unreachable localhost DB."""
    monkeypatch.setenv(
        "GOLDMASTERS_DATABASE_URL",
        "postgresql+psycopg://127.0.0.1:5432/goldmasters",
    )


@pytest.fixture()
def client() -> TestClient:
    with TestClient(create_app()) as client:
        yield client


def test_market_bars_endpoint_fails_closed_when_mt5_unavailable(
    client: TestClient,
) -> None:
    """MT5 terminal is not running, so /v1/market/bars must fail closed.

    Expected: HTTP 503 with C-09 error payload:
      - code: INTERNAL_ERROR
      - message: "mt5 terminal is not reachable"
      - retryable: true
      - correlation_id: non-empty
      - details: null
    """
    response = client.get("/v1/market/bars?instrument_id=xauusd&timeframe=H1")
    assert response.status_code == 503, response.text

    body = response.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert body["message"] == "mt5 terminal is not reachable"
    assert body["retryable"] is True
    assert body["correlation_id"]  # non-empty correlation ID
    assert body["details"] is None


def test_market_bars_endpoint_no_fabricated_data(client: TestClient) -> None:
    """Bars endpoint never returns synthesized data when MT5 is down."""
    response = client.get("/v1/market/bars?instrument_id=xauusd&timeframe=H1&count=10")
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "INTERNAL_ERROR"
    # No bar array in failure response
    assert "bars" not in body


def test_strategies_endpoint_all_agents_disabled(client: TestClient) -> None:
    """All 10 strategy agents are configured disabled by default."""
    response = client.get("/v1/strategies")
    assert response.status_code == 200, response.text

    agents = response.json()
    assert len(agents) == 10

    for agent in agents:
        assert agent["enabled"] is False
        assert agent["agent_id"].startswith("agent_")
        assert agent["instruments"] == []
        assert agent["timeframes"] == []
        assert agent["regimes"] == []
        assert agent["min_bars"] is None


def test_strategies_endpoint_unique_agent_ids(client: TestClient) -> None:
    """Each strategy has a unique agent_id."""
    response = client.get("/v1/strategies")
    agents = response.json()

    agent_ids = [a["agent_id"] for a in agents]
    assert len(set(agent_ids)) == len(agent_ids)  # all unique

    for i in range(1, 11):
        assert f"agent_{i:02d}" in agent_ids


def test_strategies_endpoint_contract_schema(client: TestClient) -> None:
    """Strategy response matches Schema.md contract shape."""
    response = client.get("/v1/strategies")
    agents = response.json()

    for agent in agents:
        assert set(agent.keys()) == {
            "agent_id",
            "enabled",
            "instruments",
            "timeframes",
            "regimes",
            "min_bars",
        }
        assert isinstance(agent["enabled"], bool)
        assert isinstance(agent["instruments"], list)
        assert isinstance(agent["timeframes"], list)
        assert isinstance(agent["regimes"], list)
        assert agent["min_bars"] is None or isinstance(agent["min_bars"], int)
