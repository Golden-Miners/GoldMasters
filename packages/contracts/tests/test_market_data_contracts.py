"""Market bar/quote, precision table and decision contract tests (01-03 Task 2)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from goldmasters_contracts.decision import DecisionRecord
from goldmasters_contracts.enums import (
    Decision,
    Direction,
    QualityStatus,
    Timeframe,
    VolumeType,
)
from goldmasters_contracts.journal import JournalEntry
from goldmasters_contracts.market import MarketBar, MarketQuote
from goldmasters_contracts.precision import PrecisionRow, PrecisionTable
from pydantic import ValidationError

RUN = "run_01890000-0000-7000-8000-000000000001"
DEC = "dec_01890000-0000-7000-8000-000000000002"
JOURNAL = "journal_01890000-0000-7000-8000-000000000003"
T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = datetime(2026, 1, 1, 1, tzinfo=UTC)


def _bar(**overrides: object) -> MarketBar:
    base: dict[str, object] = {
        "instrument_id": "xauusd",
        "provider_id": "mt5",
        "provider_symbol": "XAUUSD",
        "timeframe": Timeframe.H1,
        "bar_open_time": T0,
        "bar_close_time": T1,
        "open": "100.0",
        "high": "102.0",
        "low": "99.0",
        "close": "101.0",
        "volume": None,
        "volume_type": VolumeType.TICK,
        "retrieved_at": T1,
        "source_timezone": "Etc/UTC",
        "quality_status": QualityStatus.NOT_EVALUATED,
        "quality_flags": [],
    }
    base.update(overrides)
    return MarketBar.model_validate(base)


def _decision(**overrides: object) -> DecisionRecord:
    base: dict[str, object] = {
        "decision_id": DEC,
        "run_id": RUN,
        "instrument_id": "xauusd",
        "timeframe": Timeframe.H1,
        "decision": Decision.NO_TRADE,
        "direction": None,
        "created_at": T1,
        "data_as_of": T1,
        "thesis": "no setup",
        "data_quality_status": QualityStatus.NOT_EVALUATED,
        "manual_review_required": True,
    }
    base.update(overrides)
    return DecisionRecord.model_validate(base)


def test_valid_bar_accepted_high_below_max_rejected() -> None:
    _bar()
    with pytest.raises(ValidationError):
        _bar(high="100.5")


def test_low_above_min_non_positive_price_unordered_timestamps_rejected() -> None:
    with pytest.raises(ValidationError):
        _bar(low="100.5")
    with pytest.raises(ValidationError):
        _bar(open="0")
    with pytest.raises(ValidationError):
        _bar(bar_close_time=T0)


def test_bar_without_quality_rejected_not_evaluated_differs_from_healthy() -> None:
    with pytest.raises(ValidationError):
        MarketBar.model_validate(
            {k: v for k, v in _bar().model_dump().items() if k != "quality_status"}
        )
    healthy = {s for s in QualityStatus if s is not QualityStatus.NOT_EVALUATED}
    assert healthy
    assert QualityStatus.NOT_EVALUATED not in healthy


def test_empty_precision_table_answers_unknown() -> None:
    table = PrecisionTable()
    assert table.rows == ()
    result = table.lookup("xauusd", "mt5")
    assert result.status == "unknown"
    assert result.row is None


def test_precision_table_round_trip_and_interval() -> None:
    row = PrecisionRow.model_validate(
        {
            "instrument_id": "xauusd",
            "provider_id": "mt5",
            "tick_size": "0.01",
            "decimals": 2,
            "provider_spec_version": "spec-1",
            "retrieved_at": T1,
            "valid_from": T0,
            "valid_to": T1,
        }
    )
    table = PrecisionTable().with_row(row)
    assert table.lookup("xauusd", "mt5", at=T0).status == "found"
    assert table.lookup("xauusd", "mt5").status == "found"
    assert table.lookup("eurusd", "mt5").status == "unknown"
    assert table.lookup("xauusd", "other").status == "unknown"
    assert (
        table.lookup("xauusd", "mt5", at=datetime(2027, 1, 1, tzinfo=UTC)).status
        == "unknown"
    )


def test_decision_manual_review_and_level_rules() -> None:
    _decision()
    with pytest.raises(ValidationError):
        _decision(manual_review_required=False)
    trade = _decision(
        decision=Decision.TRADE,
        direction=Direction.LONG,
        entry="100.0",
        stop_loss="99.0",
        take_profits=["102.0"],
        risk_reward=Decimal("2.0"),
    )
    assert trade.validated_levels() is not None
    with pytest.raises(ValidationError):
        _decision(decision=Decision.TRADE, direction=Direction.LONG)
    with pytest.raises(ValidationError):
        _decision(entry="100.0")


def test_journal_rejects_mutation() -> None:
    snapshot = _decision()
    entry = JournalEntry.model_validate(
        {
            "journal_id": JOURNAL,
            "decision_id": DEC,
            "run_id": RUN,
            "recorded_at": T1,
            "snapshot": snapshot.model_dump(),
        }
    )
    assert entry.snapshot.decision_id == DEC
    with pytest.raises(ValidationError):
        JournalEntry.model_validate(
            {
                "journal_id": JOURNAL,
                "decision_id": "dec_01890000-0000-7000-8000-000000000009",
                "run_id": RUN,
                "recorded_at": T1,
                "snapshot": snapshot.model_dump(),
            }
        )
    with pytest.raises(ValidationError):
        mutated = entry.model_dump()
        mutated["decision_id"] = "dec_01890000-0000-7000-8000-000000000009"
        JournalEntry.model_validate(mutated)


def test_provider_native_timeframe_and_display_provider_id_rejected() -> None:
    with pytest.raises(ValidationError):
        _bar(timeframe="M99")
    with pytest.raises(ValidationError):
        _bar(provider_id="MetaTrader 5")
    quote = MarketQuote.model_validate(
        {
            "instrument_id": "xauusd",
            "provider_id": "mt5",
            "provider_symbol": "XAUUSD",
            "retrieved_at": T1,
            "quality_status": QualityStatus.NOT_EVALUATED,
        }
    )
    assert quote.spread is None
