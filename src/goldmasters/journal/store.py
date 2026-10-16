"""Append-only journal store: immutable snapshots plus outcome rows (D-6.2).

A snapshot is a validated ``JournalEntry`` INSERTed once and never touched
again — this module exposes no mutation or removal function. Outcomes are new
rows keyed by ``decision_id``. A correction is a new snapshot carrying
``supersedes`` plus a reason, never an edit of the original.

Retention and backup are operator-owned with safe defaults (D-6.4): this
module implements no retention, expiry, or backup policy and changes no
deployment. Rows link to runs by ``run_id`` only; the Phase 4 run log is
never extended here.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from goldmasters_contracts.journal import JournalEntry
from sqlalchemy import text
from sqlalchemy.engine import Engine

__all__ = [
    "append_outcome",
    "read_outcomes",
    "read_snapshot",
    "write_snapshot",
]

_OUTCOME_REQUIRED = frozenset({"observation_id", "decision_id", "observed_at", "observed", "pnl"})


def _assert_string_decimals(node: Any, path: str) -> None:
    """Reject JSON numbers so stored JSONB holds decimal strings, not floats."""
    if isinstance(node, Mapping):
        for key, value in node.items():
            _assert_string_decimals(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _assert_string_decimals(value, f"{path}[{index}]")
    elif isinstance(node, float):
        raise ValueError(f"{path} must be a decimal string, not a JSON number")


def write_snapshot(engine: Engine, entry: JournalEntry) -> str:
    """Validate and INSERT a journal snapshot; return its journal id."""
    if not isinstance(entry, JournalEntry):
        raise TypeError(f"entry must be a JournalEntry, got {type(entry).__name__}")
    journal_id: str = entry.journal_id
    document = entry.model_dump(mode="json")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO journal_entry "
                "(journal_id, decision_id, run_id, recorded_at, snapshot) "
                "VALUES (:journal_id, :decision_id, :run_id, :recorded_at, :snapshot)"
            ),
            {
                "journal_id": journal_id,
                "decision_id": entry.decision_id,
                "run_id": entry.run_id,
                "recorded_at": entry.recorded_at,
                "snapshot": json.dumps(document),
            },
        )
    return journal_id


def append_outcome(engine: Engine, observation: Mapping[str, Any]) -> str:
    """Validate and INSERT one outcome row; the snapshot row is never touched."""
    if not isinstance(observation, Mapping):
        raise TypeError(f"observation must be a mapping, got {type(observation).__name__}")
    missing = sorted(key for key in _OUTCOME_REQUIRED if key not in observation)
    if missing:
        raise ValueError(f"observation missing required fields: {', '.join(missing)}")
    observed = observation["observed"]
    pnl = observation["pnl"]
    if not isinstance(observed, Mapping):
        raise ValueError("observation 'observed' must be a mapping of levels/exit")
    if not isinstance(pnl, Mapping):
        raise ValueError("observation 'pnl' must be a mapping of pnl terms")
    observed_at = observation["observed_at"]
    if not isinstance(observed_at, datetime) or observed_at.tzinfo is None:
        raise ValueError("observation 'observed_at' must be a timezone-aware datetime")
    _assert_string_decimals(observed, "observed")
    _assert_string_decimals(pnl, "pnl")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO outcome_observation "
                "(outcome_id, decision_id, observed_at, observed, pnl, supersedes, reason) "
                "VALUES (:outcome_id, :decision_id, :observed_at, "
                ":observed, :pnl, :supersedes, :reason)"
            ),
            {
                "outcome_id": observation["observation_id"],
                "decision_id": observation["decision_id"],
                "observed_at": observed_at,
                "observed": json.dumps(dict(observed)),
                "pnl": json.dumps(dict(pnl)),
                "supersedes": observation.get("supersedes"),
                "reason": observation.get("reason", ""),
            },
        )
    outcome_id = observation["observation_id"]
    if not isinstance(outcome_id, str):
        raise ValueError("observation 'observation_id' must be a string")
    return outcome_id


def read_snapshot(engine: Engine, journal_id: str) -> JournalEntry:
    """Re-read a snapshot by journal id, re-validated through the contract."""
    with engine.connect() as connection:
        row = (
            connection.execute(
                text("SELECT snapshot FROM journal_entry WHERE journal_id = :journal_id"),
                {"journal_id": journal_id},
            )
            .mappings()
            .first()
        )
    if row is None:
        raise KeyError(f"unknown journal_id {journal_id!r}")
    document = row["snapshot"]
    if isinstance(document, str):
        return JournalEntry.model_validate_json(document)
    return JournalEntry.model_validate_json(json.dumps(document))


def read_outcomes(engine: Engine, decision_id: str) -> list[dict[str, Any]]:
    """Return every outcome row for a decision, oldest first."""
    with engine.connect() as connection:
        rows = (
            connection.execute(
                text(
                    "SELECT outcome_id, decision_id, observed_at, observed, pnl, "
                    "supersedes, reason FROM outcome_observation "
                    "WHERE decision_id = :decision_id ORDER BY observed_at"
                ),
                {"decision_id": decision_id},
            )
            .mappings()
            .all()
        )
    outcomes: list[dict[str, Any]] = []
    for row in rows:
        observed = row["observed"]
        pnl = row["pnl"]
        outcomes.append(
            {
                "observation_id": row["outcome_id"],
                "decision_id": row["decision_id"],
                "observed_at": row["observed_at"],
                "observed": json.loads(observed) if isinstance(observed, str) else observed,
                "pnl": json.loads(pnl) if isinstance(pnl, str) else pnl,
                "supersedes": row["supersedes"],
                "reason": row["reason"],
            }
        )
    return outcomes
