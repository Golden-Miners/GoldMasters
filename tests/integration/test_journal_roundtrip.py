"""Journal immutability, append-only outcomes, and restart survival (06-01).

Against a throwaway per-run database (fail loudly, never skip, when the
cluster is unavailable): snapshots re-read equal, outcomes never touch the
snapshot row, corrections arrive as new rows via supersedes plus reason, the
store module exposes no mutation path, and records survive a fresh
connection. Cost values are not asserted here.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from goldmasters_contracts import DecisionRecord, JournalEntry
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.goldmasters.journal import store as journal_store
from src.goldmasters.journal.store import (
    append_outcome,
    read_outcomes,
    read_snapshot,
    write_snapshot,
)

T0 = "2026-01-01T00:00:00Z"
T1 = "2026-01-01T01:00:00Z"
T2 = "2026-01-01T02:00:00Z"


def _prefixed(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4()}"


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
                "evidence_refs": ["bars:xauusd:H1:2026-01-01", "regime:uptrend:v1"],
                "data_quality_status": "ok",
                "manual_review_required": True,
            }
        )
    )


def _entry(journal_id: str, decision: DecisionRecord) -> JournalEntry:
    return JournalEntry(
        journal_id=journal_id,  # type: ignore[arg-type]
        decision_id=decision.decision_id,
        run_id=decision.run_id,
        recorded_at=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
        snapshot=decision,
    )


def _observation(observation_id: str, decision_id: str) -> dict[str, Any]:
    return {
        "observation_id": observation_id,
        "decision_id": decision_id,
        "observed_at": datetime(2026, 1, 1, 2, 0, tzinfo=UTC),
        "observed": {"exit_price": "2700.00", "exit_kind": "take-profit-1"},
        "pnl": {"gross": "19.50", "commission": "0.00", "net": "19.50"},
    }


def _assert_no_floats(node: Any, path: str) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            _assert_no_floats(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _assert_no_floats(value, f"{path}[{index}]")
    else:
        assert not isinstance(node, float), f"{path} stored as JSON number"


def _snapshot_row(engine: Engine, journal_id: str) -> dict[str, Any]:
    with engine.connect() as connection:
        row = (
            connection.execute(
                text(
                    "SELECT journal_id, decision_id, run_id, recorded_at, snapshot "
                    "FROM journal_entry WHERE journal_id = :journal_id"
                ),
                {"journal_id": journal_id},
            )
            .mappings()
            .first()
        )
    assert row is not None
    return dict(row)


def test_snapshot_reread_equals_written(migrated_database: str) -> None:
    engine = create_engine(migrated_database)
    try:
        run_id, decision_id, journal_id = (
            _prefixed("run_"),
            _prefixed("dec_"),
            _prefixed("journal_"),
        )
        entry = _entry(journal_id, _decision(decision_id, run_id))
        assert write_snapshot(engine, entry) == journal_id

        revived = read_snapshot(engine, journal_id)
        assert revived == entry
        assert revived.snapshot.evidence_refs == [
            "bars:xauusd:H1:2026-01-01",
            "regime:uptrend:v1",
        ]

        raw = _snapshot_row(engine, journal_id)
        document = raw["snapshot"]
        if isinstance(document, str):
            document = json.loads(document)
        _assert_no_floats(document, "snapshot")
        assert document["snapshot"]["entry"] == "2680.50"
        assert document["snapshot"]["take_profits"] == ["2700.00"]
    finally:
        engine.dispose()


def test_outcome_append_leaves_snapshot_unchanged(migrated_database: str) -> None:
    engine = create_engine(migrated_database)
    try:
        run_id, decision_id, journal_id = (
            _prefixed("run_"),
            _prefixed("dec_"),
            _prefixed("journal_"),
        )
        write_snapshot(engine, _entry(journal_id, _decision(decision_id, run_id)))
        before = _snapshot_row(engine, journal_id)

        outcome_id = f"outcome_{uuid.uuid4().hex}"
        assert append_outcome(engine, _observation(outcome_id, decision_id)) == outcome_id

        after = _snapshot_row(engine, journal_id)
        assert after == before

        outcomes = read_outcomes(engine, decision_id)
        assert len(outcomes) == 1
        assert outcomes[0]["observed"] == {
            "exit_price": "2700.00",
            "exit_kind": "take-profit-1",
        }
        assert outcomes[0]["pnl"]["net"] == "19.50"
    finally:
        engine.dispose()


def test_supersedes_correction_creates_new_row(migrated_database: str) -> None:
    engine = create_engine(migrated_database)
    try:
        run_id, decision_id = _prefixed("run_"), _prefixed("dec_")
        original_id, correction_id = _prefixed("journal_"), _prefixed("journal_")
        write_snapshot(engine, _entry(original_id, _decision(decision_id, run_id)))
        before = _snapshot_row(engine, original_id)

        correction = JournalEntry(
            journal_id=correction_id,  # type: ignore[arg-type]
            decision_id=decision_id,
            run_id=run_id,
            recorded_at=datetime(2026, 1, 1, 3, 0, tzinfo=UTC),
            snapshot=_decision(decision_id, run_id),
            supersedes=decision_id,  # type: ignore[arg-type]
            reason="thesis revised after evidence review",
        )
        write_snapshot(engine, correction)

        assert _snapshot_row(engine, original_id) == before
        revived = read_snapshot(engine, correction_id)
        assert revived.supersedes == decision_id
        assert revived.reason == "thesis revised after evidence review"

        with engine.connect() as connection:
            count = connection.execute(
                text("SELECT COUNT(*) FROM journal_entry WHERE decision_id = :decision_id"),
                {"decision_id": decision_id},
            ).scalar()
        assert count == 2
    finally:
        engine.dispose()


def test_store_exposes_no_mutation_path() -> None:
    assert set(journal_store.__all__) == {
        "write_snapshot",
        "append_outcome",
        "read_snapshot",
        "read_outcomes",
    }
    for name in journal_store.__all__:
        lowered = name.lower()
        assert "update" not in lowered and "delete" not in lowered
    source = Path(journal_store.__file__ or "").read_text(encoding="utf-8")
    for token in ("UPDATE ", "DELETE ", "DROP "):
        assert token not in source, "store module must not contain " + token.strip()


def test_records_survive_fresh_connection(migrated_database: str) -> None:
    run_id, decision_id, journal_id = (
        _prefixed("run_"),
        _prefixed("dec_"),
        _prefixed("journal_"),
    )
    entry = _entry(journal_id, _decision(decision_id, run_id))
    observation = _observation(f"outcome_{uuid.uuid4().hex}", decision_id)

    first = create_engine(migrated_database)
    try:
        write_snapshot(first, entry)
        append_outcome(first, observation)
    finally:
        first.dispose()

    # Fresh engine = fresh connections, the closest a test gets to a restart.
    second = create_engine(migrated_database)
    try:
        assert read_snapshot(second, journal_id) == entry
        outcomes = read_outcomes(second, decision_id)
        assert len(outcomes) == 1
        assert outcomes[0]["observation_id"] == observation["observation_id"]
    finally:
        second.dispose()


def test_outcome_rejects_float_decimals(migrated_database: str) -> None:
    engine = create_engine(migrated_database)
    try:
        decision_id = _prefixed("dec_")
        bad = _observation(f"outcome_{uuid.uuid4().hex}", decision_id)
        bad["pnl"] = {"net": 19.50}
        try:
            append_outcome(engine, bad)
        except ValueError:
            pass
        else:
            raise AssertionError("float pnl must be rejected")
        assert read_outcomes(engine, decision_id) == []
    finally:
        engine.dispose()
