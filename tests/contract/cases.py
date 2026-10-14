"""Golden conformance cases: the shared definition of "accepted" (D-06/D-07).

This module is imported by `tests/contract/test_conformance.py` (this plan)
and by plan 06's persistence round-trip, so both agree on what "accepted"
means. Phase 8 re-runs it unchanged.

`SCHEMA_MD_EXAMPLES` transcribes Schema.md's two JSON examples verbatim; the
strings in them describe formats, not real values (Schema.md says so itself),
so each entry carries explicit `substitutions` applied before validation.
"""

from __future__ import annotations

from typing import Any

import goldmasters_contracts as contracts
from pydantic import BaseModel

RUN = "run_01890000-0000-7000-8000-000000000001"
DEC = "dec_01890000-0000-7000-8000-000000000002"
JOURNAL = "journal_01890000-0000-7000-8000-000000000003"
UUID = "01890000-0000-7000-8000-000000000000"
T0 = "2026-01-01T00:00:00Z"
T1 = "2026-01-01T01:00:00Z"

CONTRACT_MODELS: dict[str, type[BaseModel]] = {
    "envelope": contracts.Envelope,
    "market": contracts.MarketBar,
    "quote": contracts.MarketQuote,
    "precision": contracts.PrecisionTable,
    "decision": contracts.DecisionRecord,
    "journal": contracts.JournalEntry,
    "news": contracts.NewsItem,
    "sentiment": contracts.SentimentRecord,
    "backtest": contracts.BacktestRecord,
    "error": contracts.ErrorPayload,
}

#: (contract name, verbatim Schema.md document, substitutions to real values).
SCHEMA_MD_EXAMPLES: list[tuple[str, dict[str, Any], dict[str, Any]]] = [
    (
        "envelope",
        {
            "schema_version": "1.0",
            "run_id": "UUID",
            "agent_name": "trend_agent",
            "agent_version": "semver-or-commit-reference",
            "status": "ok",
            "created_at": "ISO-8601-with-timezone",
            "as_of": "ISO-8601-with-timezone-or-null",
            "input_refs": [],
            "evidence_refs": [],
            "limitations": [],
            "error": None,
            "result": {},
        },
        {"run_id": RUN, "created_at": T0, "as_of": None},
    ),
    (
        "error",
        {
            "code": "STABLE_MACHINE_READABLE_CODE",
            "message": "Sanitized user-facing description",
            "retryable": False,
            "correlation_id": "UUID",
            "details": None,
        },
        {"code": "CONTRACT_VALIDATION_FAILED", "correlation_id": UUID},
    ),
]

DECISION_DOC: dict[str, Any] = {
    "decision_id": DEC,
    "run_id": RUN,
    "instrument_id": "xauusd",
    "timeframe": "H1",
    "decision": "NO_TRADE",
    "direction": None,
    "created_at": T1,
    "data_as_of": T1,
    "thesis": "no setup",
    "data_quality_status": "not_evaluated",
    "manual_review_required": True,
}

CONTRACT_ACCEPTED_CASES: dict[str, dict[str, Any]] = {
    "envelope": {
        "schema_version": "1.0",
        "run_id": RUN,
        "agent_name": "trend_agent",
        "agent_version": "1.0.0",
        "status": "ok",
        "created_at": T0,
        "as_of": None,
        "input_refs": [],
        "evidence_refs": [],
        "limitations": [],
        "error": None,
        "result": {},
    },
    "market": {
        "instrument_id": "xauusd",
        "provider_id": "mt5",
        "provider_symbol": "XAUUSD",
        "timeframe": "H1",
        "bar_open_time": T0,
        "bar_close_time": T1,
        "open": "100.0",
        "high": "102.0",
        "low": "99.0",
        "close": "101.0",
        "volume": None,
        "volume_type": "tick",
        "retrieved_at": T1,
        "source_timezone": "Etc/UTC",
        "quality_status": "not_evaluated",
        "quality_flags": [],
    },
    "quote": {
        "instrument_id": "xauusd",
        "provider_id": "mt5",
        "provider_symbol": "XAUUSD",
        "retrieved_at": T1,
        "quality_status": "not_evaluated",
    },
    "precision": {"rows": []},
    "decision": dict(DECISION_DOC),
    "journal": {
        "journal_id": JOURNAL,
        "decision_id": DEC,
        "run_id": RUN,
        "recorded_at": T1,
        "snapshot": dict(DECISION_DOC),
    },
    "news": {
        "source_id": "reuters",
        "canonical_url": "https://example.com/gold-1",
        "title": "Gold steady",
        "published_at": T0,
        "retrieved_at": T1,
        "content_hash": "abc123",
        "source_attribution": "Example News",
        "access_method": "rss",
        "status": "valid",
    },
    "sentiment": {
        "instrument_id": "xauusd",
        "window_start": T0,
        "window_end": T1,
        "created_at": T1,
        "coverage_count": 3,
        "unique_source_count": 2,
        "duplicate_policy": "collapse-by-canonical-url",
    },
    "backtest": {
        "backtest_run_id": RUN,
        "strategy_id": "trend-breakout",
        "strategy_version": "1.0.0",
        "dataset_ref": "xauusd-h1-2025",
        "dataset_hash": "def456",
        "instrument_id": "xauusd",
        "timeframe": "H1",
        "start": T0,
        "end": T1,
        "timezone": "Etc/UTC",
        "data_quality": "valid",
        "parameter_hash": "p789",
        "assumptions": {
            "spread": "0.35",
            "commission": "0.00",
            "slippage": "0.10",
            "fill_model": "next-open",
        },
        "generated_at": T1,
        "code_version": "1.0.0",
        "status": "valid",
    },
    "error": {
        "code": "CONTRACT_VALIDATION_FAILED",
        "message": "Rejected contract validation.",
        "retryable": False,
        "correlation_id": UUID,
        "details": None,
    },
}


def _mutated(
    contract: str, reason: str, delete: list[str] | None = None, **changes: Any
) -> tuple[str, str, dict[str, Any]]:
    """Copy the accepted case, delete `delete` keys, then apply `changes`."""
    import copy

    document = copy.deepcopy(CONTRACT_ACCEPTED_CASES[contract])
    for key in delete or []:
        del document[key]
    document.update(changes)
    return (contract, reason, document)


CONTRACT_REJECTED_CASES: list[tuple[str, str, dict[str, Any]]] = [
    # Wrong enum member, per contract.
    _mutated("envelope", "wrong-enum-status", status="flying"),
    _mutated("market", "wrong-enum-timeframe", timeframe="M99"),
    _mutated("market", "wrong-enum-quality", quality_status="healthy"),
    _mutated("decision", "wrong-enum-decision", decision="BUY"),
    _mutated("news", "wrong-enum-status", status="viral"),
    _mutated("backtest", "wrong-enum-timeframe", timeframe="century"),
    _mutated("error", "wrong-enum-code", code="SOMETHING_BROKE"),
    # Missing required field.
    _mutated("envelope", "missing-agent_name", delete=["agent_name"]),
    _mutated("market", "missing-provider_id", delete=["provider_id"]),
    _mutated("quote", "missing-retrieved_at", delete=["retrieved_at"]),
    _mutated("decision", "missing-thesis", delete=["thesis"]),
    _mutated("journal", "missing-snapshot", delete=["snapshot"]),
    _mutated("news", "missing-title", delete=["title"]),
    _mutated("sentiment", "missing-window_start", delete=["window_start"]),
    _mutated("backtest", "missing-dataset_ref", delete=["dataset_ref"]),
    _mutated("error", "missing-message", delete=["message"]),
    # Null where not nullable.
    _mutated("market", "null-open", open=None),
    _mutated("decision", "null-thesis", thesis=None),
    _mutated("news", "null-source_id", source_id=None),
    # Infinite value.
    _mutated("market", "infinite-open", open="Infinity"),
    _mutated("market", "infinite-high", high="NaN"),
    # Price as JSON number, not Decimal string.
    _mutated("market", "float-open", open=100.0),
    _mutated("backtest", "float-spread", assumptions={"spread": 0.35}),
    # Unknown extra field.
    _mutated("envelope", "extra-field", bogus_field="x"),
    _mutated("market", "extra-field", bogus_field="x"),
    _mutated("quote", "extra-field", bogus_field="x"),
    _mutated("precision", "extra-field", bogus_field="x"),
    _mutated("decision", "extra-field", bogus_field="x"),
    _mutated("journal", "extra-field", bogus_field="x"),
    _mutated("news", "extra-field", bogus_field="x"),
    _mutated("sentiment", "extra-field", bogus_field="x"),
    _mutated("backtest", "extra-field", bogus_field="x"),
    _mutated("error", "extra-field", bogus_field="x"),
    # Named Schema.md invariant violations.
    _mutated("market", "ohlc-high-below-max", high="100.5"),
    _mutated("market", "ohlc-low-above-min", low="100.5"),
    _mutated("market", "non-positive-price", open="0"),
    _mutated("market", "unordered-timestamps", bar_close_time=T0),
    _mutated("market", "quality-omitted", delete=["quality_status"]),
    _mutated("decision", "manual-review-false", manual_review_required=False),
    _mutated(
        "decision",
        "trade-without-levels",
        decision="TRADE",
        direction="long",
    ),
    _mutated(
        "journal", "snapshot-id-mismatch", decision_id="dec_01890000-0000-7000-8000-000000000009"
    ),
    _mutated("envelope", "unknown-major", schema_version="3.0"),
    _mutated("envelope", "wrong-prefix-run_id", run_id="dec_01890000-0000-7000-8000-000000000002"),
    _mutated("market", "display-name-provider", provider_id="MetaTrader 5"),
    _mutated(
        "sentiment",
        "score-out-of-bounds",
        score=1.5,
        scoring_method="m",
        scoring_method_version="1",
    ),
    _mutated("precision", "extra-field-status", status="found"),
]

__all__ = [
    "CONTRACT_ACCEPTED_CASES",
    "CONTRACT_MODELS",
    "CONTRACT_REJECTED_CASES",
    "SCHEMA_MD_EXAMPLES",
]
