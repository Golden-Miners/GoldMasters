"""Console API round-trip over real persistence (07-01 Task 4 tracer).

Seeds journal + backtest rows via existing stores, hits each /v1/* endpoint
through the ASGI app, asserts contract-valid JSON + C-09 on missing/empty.
Proves no endpoint returns synthesised data.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from goldmasters_contracts import (
    BacktestAssumptions,
    BacktestMetric,
    BacktestRecord,
    DecisionRecord,
    EvidenceStatus,
    JournalEntry,
    Timeframe,
)
from sqlalchemy import create_engine

from goldmasters_api.app import create_app
from src.goldmasters.backtest.persistence import write_backtest_record
from src.goldmasters.journal.store import write_snapshot

T0 = "2026-01-01T00:00:00Z"
T1 = "2026-01-01T01:00:00Z"


@pytest.fixture()
def console_client(migrated_database: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """ASGI test client wired to the throwaway migrated database."""
    monkeypatch.setenv("GOLDMASTERS_DATABASE_URL", migrated_database)
    with TestClient(create_app()) as client:
        yield client


def _decision(decision_id: str, run_id: str) -> DecisionRecord:
    return DecisionRecord.model_validate_json(
        json.dumps(
            {
                "decision_id": decision_id,
                "run_id": run_id,
                "instrument_id": "xauusd",
                "timeframe": "H1",
                "decision": "TRADE",
                "direction": "long",
                "created_at": T1,
                "data_as_of": T1,
                "strategy_id": "trend-following",
                "strategy_version": "1.0.0",
                "entry": "2680.50",
                "stop_loss": "2670.00",
                "take_profits": ["2700.00"],
                "risk_reward": "2",
                "thesis": "trend continuation with pullback confirmation",
                "evidence_refs": ["bars:xauusd:H1:2026-01-01"],
                "data_quality_status": "ok",
                "manual_review_required": True,
            }
        )
    )


def _backtest_record(run_id: str, dataset_ref: str) -> BacktestRecord:
    return BacktestRecord(
        backtest_run_id=run_id,
        strategy_id="trend-following",
        strategy_version="1.0.0",
        dataset_ref=dataset_ref,
        dataset_hash="hash_123",
        instrument_id="xauusd",
        timeframe=Timeframe.H1,
        start=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        end=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
        timezone="UTC",
        data_quality=EvidenceStatus.VALID,
        parameter_hash="param_hash",
        assumptions=BacktestAssumptions(
            commission="0",
            fill_model="next-bar-open",
            slippage="0",
            spread="0",
        ),
        metrics=[BacktestMetric(name="net_return", definition="net return", sample_size=10, value="0.05")],
        generated_at=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
        code_version="1.0.0",
        status=EvidenceStatus.VALID,
        errors=[],
    )


def test_decisions_returns_seeded_journal_snapshots(
    console_client: TestClient, migrated_database: str
) -> None:
    run_id, decision_id, journal_id = (
        f"run_{uuid.uuid4().hex[:8]}",
        f"dec_{uuid.uuid4().hex[:8]}",
        f"journal_{uuid.uuid4().hex[:8]}",
    )
    entry = JournalEntry(
        journal_id=journal_id,  # type: ignore[arg-type]
        decision_id=decision_id,
        run_id=run_id,
        recorded_at=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
        snapshot=_decision(decision_id, run_id),
    )
    engine = create_engine(migrated_database)
    try:
        write_snapshot(engine, entry)
    finally:
        engine.dispose()

    response = console_client.get("/v1/decisions")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["decision"] == "TRADE"
    assert body[0]["instrument_id"] == "xauusd"


def test_decisions_empty_returns_empty_list(console_client: TestClient) -> None:
    response = console_client.get("/v1/decisions")
    assert response.status_code == 200
    assert response.json() == []


def test_journal_returns_seeded_entries(
    console_client: TestClient, migrated_database: str
) -> None:
    run_id, decision_id, journal_id = (
        f"run_{uuid.uuid4().hex[:8]}",
        f"dec_{uuid.uuid4().hex[:8]}",
        f"journal_{uuid.uuid4().hex[:8]}",
    )
    entry = JournalEntry(
        journal_id=journal_id,  # type: ignore[arg-type]
        decision_id=decision_id,
        run_id=run_id,
        recorded_at=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
        snapshot=_decision(decision_id, run_id),
    )
    engine = create_engine(migrated_database)
    try:
        write_snapshot(engine, entry)
    finally:
        engine.dispose()

    response = console_client.get("/v1/journal")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["journal_id"] == journal_id
    assert body[0]["run_id"] == entry.run_id


def test_backtests_returns_seeded_records(
    console_client: TestClient, migrated_database: str
) -> None:
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    dataset_ref = f"ds_{uuid.uuid4().hex[:8]}"
    record = _backtest_record(run_id, dataset_ref)
    engine = create_engine(migrated_database)
    try:
        write_backtest_record(engine, record)
    finally:
        engine.dispose()

    response = console_client.get("/v1/backtests")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["backtest_run_id"] == run_id
    assert body[0]["strategy_id"] == "trend-following"


def test_news_sentiment_fail_closed_unavailable(console_client: TestClient) -> None:
    response = console_client.get("/v1/news-sentiment")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["items"] == []


def test_agent_runs_explicit_unavailable(console_client: TestClient) -> None:
    response = console_client.get("/v1/agent-runs")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["runs"] == []


def test_model_health_unavailable_when_no_model_configured(
    console_client: TestClient,
) -> None:
    response = console_client.get("/v1/model-health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"


def test_settings_returns_non_secret_config(console_client: TestClient) -> None:
    response = console_client.get("/v1/settings")
    assert response.status_code == 200
    body = response.json()
    assert "bind_host" in body
    assert "provider_api_key" not in body


def test_no_write_endpoints_exist(console_client: TestClient) -> None:
    """Prove no POST/PUT/DELETE endpoint exists on any router."""
    for path in [
        "/v1/decisions",
        "/v1/news-sentiment",
        "/v1/strategies",
        "/v1/backtests",
        "/v1/journal",
        "/v1/agent-runs",
        "/v1/providers",
        "/v1/model-health",
        "/v1/settings",
    ]:
        for method in ["POST", "PUT", "DELETE", "PATCH"]:
            response = console_client.request(method, path)
            assert response.status_code == 405, f"{method} {path} must not exist"
