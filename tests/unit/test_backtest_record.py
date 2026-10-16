"""Backtest record completeness plus the all-10 live-seam run (06-02 Task 2).

Strategy params below are the FIXTURE builders from each agent's own unit
test (``tests/unit/test_agent_*.py``) — labelled fixture thresholds, never
operator thresholds. A record without its run plus dataset reference is
unrepresentable, and every assumption field (including the placeholder-cost
fill model) is present on every runner-produced record.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TypeVar

import pytest
from goldmasters_contracts import (
    BacktestRecord,
    Direction,
    EvidenceStatus,
    MarketBar,
    QualityStatus,
    Timeframe,
    TrendRegime,
    VolumeType,
)
from pydantic import ValidationError

from src.goldmasters.backtest.fills import (
    FILL_MODEL,
    apply_costs,
    fill_at_next_open,
    placeholder_costs,
    require_confirmed,
)
from src.goldmasters.backtest.runner import (
    PINNED_STRATEGIES,
    BacktestJob,
    GatePolicy,
    StrategySlot,
    assert_pinned,
    hash_params,
    run_backtest,
)
from src.goldmasters.backtest.splits import SplitWindows
from src.goldmasters.strategies import agent_01 as pkg_01
from src.goldmasters.strategies import agent_02 as pkg_02
from src.goldmasters.strategies import agent_03 as pkg_03
from src.goldmasters.strategies import agent_04 as pkg_04
from src.goldmasters.strategies import agent_05 as pkg_05
from src.goldmasters.strategies import agent_06 as pkg_06
from src.goldmasters.strategies import agent_07 as pkg_07
from src.goldmasters.strategies import agent_08 as pkg_08
from src.goldmasters.strategies import agent_09 as pkg_09
from src.goldmasters.strategies import agent_10 as pkg_10
from src.goldmasters.strategies.agent_01 import Agent01Params
from src.goldmasters.strategies.agent_02 import Agent02Params
from src.goldmasters.strategies.agent_03 import Agent03Params
from src.goldmasters.strategies.agent_04 import Agent04Params
from src.goldmasters.strategies.agent_05 import Agent05Params
from src.goldmasters.strategies.agent_06 import Agent06Params
from src.goldmasters.strategies.agent_07 import Agent07Params
from src.goldmasters.strategies.agent_08 import Agent08Params
from src.goldmasters.strategies.agent_09 import Agent09Params
from src.goldmasters.strategies.agent_10 import Agent10Params
from src.goldmasters.strategies.base import MarketContext
from tests.unit.agent_fixtures import bars_from_closes, make_ctx

T0 = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
FIXTURE_UP = ["100", "102", "104", "106", "108", "110", "112", "114"]


def _slot(module: object, params: object) -> StrategySlot:
    evaluate = getattr(module, "evaluate")
    return StrategySlot(
        strategy_id=str(getattr(module, "STRATEGY_ID")),
        strategy_version=str(getattr(module, "STRATEGY_VERSION")),
        code_hash=str(getattr(module, "CODE_HASH")),
        params=params,
        evaluate=lambda bars, ctx: evaluate(bars, ctx, params),
    )


def _scope(regimes: tuple[TrendRegime, ...]) -> dict[str, object]:
    return {
        "enabled": True,
        "instruments": ("xauusd",),
        "timeframes": (Timeframe.H1,),
        "regimes": regimes,
    }


_P = TypeVar("_P")


def _params(cls: type[_P], **fields: object) -> _P:
    """One ignore for all FIXTURE builders (values copied from per-agent tests)."""
    return cls(**fields)  # type: ignore[call-arg]


def _all_slots() -> list[StrategySlot]:
    up_down = (TrendRegime.UPTREND, TrendRegime.DOWNTREND)
    full = (TrendRegime.UPTREND, TrendRegime.DOWNTREND, TrendRegime.RANGE)
    return [
        _slot(pkg_01, _params(Agent01Params, **_scope(up_down), min_bars=6,
                              fast_period=3, slow_period=5, htf_timeframe="H4",
                              adx_min=Decimal("0.1"), confirm_bars=2)),
        _slot(pkg_02, _params(Agent02Params, **_scope(up_down), min_bars=6,
                              lookbacks=(2, 4), entry_threshold=Decimal("0.005"),
                              vol_lookback=3, max_hold_bars=8, expiry_bars=3)),
        _slot(pkg_03, _params(Agent03Params, **_scope(up_down), min_bars=7,
                              channel_bars=5, buffer_ticks=2, confirm_bars=2,
                              exit_bars=5)),
        _slot(pkg_04, _params(Agent04Params, **_scope(up_down), min_bars=7,
                              vol_lookback=3, compression_pctile=Decimal("0.5"),
                              confirm_bars=2)),
        _slot(pkg_05, _params(Agent05Params, **_scope(up_down), min_bars=6,
                              trend_period=5, pullback_ma=3, confirm_bars=2,
                              expiry_bars=3)),
        _slot(pkg_06, _params(Agent06Params, **_scope(up_down), min_bars=6,
                              session_name="london", session_tz="UTC",
                              range_minutes=120, buffer_ticks=2,
                              expiry_minutes=480, max_spread_ticks=5)),
        _slot(pkg_07, _params(Agent07Params, **_scope(full), min_bars=6,
                              basis_period=5, band_width=Decimal("1.0"),
                              z_min=Decimal("1.0"), rsi_period=5,
                              rsi_extreme=Decimal("30"), confirm_bars=1)),
        _slot(pkg_08, _params(Agent08Params, **_scope(full), min_bars=6,
                              session_name="london", session_tz="UTC",
                              band_sigmas=Decimal("1.0"), min_volume_bars=5)),
        _slot(pkg_09, _params(Agent09Params, **_scope(full), min_bars=6,
                              swing_bars=1, equal_tol_ticks=2, sweep_tol_ticks=2,
                              disp_body_min_atr=Decimal("1.0"), expiry_bars=5)),
        _slot(pkg_10, _params(Agent10Params, enabled=True,
                              instruments=("xauusd", "eurusd", "btcusd", "usoil"),
                              timeframes=(Timeframe.H1,), regimes=full,
                              min_bars=6, max_data_age_hours=Decimal("24"),
                              min_history_points=50)),
    ]


def _job() -> BacktestJob:
    return BacktestJob(
        run_id="run_fixture",
        dataset_ref="ds_fixture",
        dataset_hash="hash_fixture",
        instrument_id="xauusd",
        provider_symbol="XAUUSD",
        timeframe=Timeframe.H1,
        display_timezone="UTC",
        windows=SplitWindows(
            in_sample_start=T0,
            in_sample_end=T0 + timedelta(hours=12),
            validation_start=T0 + timedelta(hours=12),
            validation_end=T0 + timedelta(hours=13),
            out_of_sample_start=T0 + timedelta(hours=13),
            out_of_sample_end=T0 + timedelta(hours=14),
        ),
        code_version="test",
        gate=GatePolicy(
            min_risk_reward_ratio=Decimal("1"),
            max_risk_percent_per_idea=Decimal("2"),
            risk_percent_for_idea=Decimal("1"),
            evidence={"bars": EvidenceStatus.VALID,
                      "precision": EvidenceStatus.VALID},
        ),
        costs=placeholder_costs(),
    )


def _single_record() -> BacktestRecord:
    return run_backtest(
        bars=bars_from_closes(FIXTURE_UP),
        make_ctx=lambda index, bar: make_ctx(bar_count=index + 1),
        slots=_all_slots()[:1],
        job=_job(),
    ).records[0]


def test_record_without_run_and_dataset_ref_unrepresentable() -> None:
    document = _single_record().model_dump(mode="json")
    del document["backtest_run_id"]
    del document["dataset_ref"]
    with pytest.raises(ValidationError):
        BacktestRecord.model_validate(document)
    with pytest.raises(ValidationError):
        BacktestRecord.model_validate({})


def test_runner_record_carries_every_assumption_field() -> None:
    record = _single_record()
    assumptions = record.assumptions.model_dump(mode="json")
    assert set(assumptions) == {"spread", "commission", "slippage", "fill_model"}
    assert "PLACEHOLDER" in assumptions["fill_model"]
    assert assumptions["fill_model"] == FILL_MODEL
    assert record.backtest_run_id == "run_fixture:trend-following"
    assert record.dataset_ref == "ds_fixture"
    assert record.dataset_hash == "hash_fixture"
    assert record.strategy_version == "1.0.0"
    assert len(record.parameter_hash) == 64
    assert record.timezone == "UTC"
    assert record.timeframe == Timeframe.H1
    assert record.in_sample_start is not None
    assert record.validation_start is not None
    assert record.out_of_sample_start is not None
    assert record.code_version == "test"
    assert {metric.name for metric in record.metrics} == {
        "bars_evaluated",
        "setups_found",
        "gate_passes",
        "fills_opened",
    }
    for metric in record.metrics:
        assert "placeholder" in metric.definition
        assert str(metric.value) == str(metric.sample_size)


def test_all_ten_pinned_strategies_run_live_seam() -> None:
    slots = _all_slots()
    assert len(PINNED_STRATEGIES) == 10
    output = run_backtest(
        bars=bars_from_closes(FIXTURE_UP),
        make_ctx=lambda index, bar: make_ctx(bar_count=index + 1),
        slots=slots,
        job=_job(),
    )
    assert len(output.records) == 10
    for slot, record in zip(slots, output.records, strict=True):
        assert record.strategy_version == "1.0.0"
        assert record.backtest_run_id == f"run_fixture:{slot.strategy_id}"
        assert record.dataset_ref == output.manifest.dataset_ref == "ds_fixture"
        assert "PLACEHOLDER" in record.assumptions.fill_model
    by_id = {record.strategy_id: record for record in output.records}
    assert by_id["trend-following"].metrics[1].sample_size >= 1
    assert by_id["carry-term-structure"].metrics[1].sample_size == 0
    assert output.manifest.source_hashes["bars_sha256"]
    assert output.manifest.symbol_mapping == {"xauusd": "XAUUSD"}


def test_unpinned_version_refused() -> None:
    slot = _all_slots()[0]
    drifted = StrategySlot(
        strategy_id=slot.strategy_id,
        strategy_version="2.0.0",
        code_hash=slot.code_hash,
        params=slot.params,
        evaluate=slot.evaluate,
    )
    with pytest.raises(ValueError, match="not pinned"):
        assert_pinned(drifted)
    with pytest.raises(ValueError, match="not pinned"):
        run_backtest(
            bars=bars_from_closes(FIXTURE_UP),
            make_ctx=lambda index, bar: make_ctx(bar_count=index + 1),
            slots=[drifted],
            job=_job(),
        )


def test_out_of_window_bars_refuse_evaluation() -> None:
    stray = MarketBar(
        instrument_id="xauusd",
        provider_id="mt5",
        provider_symbol="XAUUSD",
        timeframe=Timeframe.H1,
        bar_open_time=datetime(2025, 12, 31, 12, 0, tzinfo=UTC),
        bar_close_time=datetime(2025, 12, 31, 13, 0, tzinfo=UTC),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal(10),
        volume_type=VolumeType.TICK,
        retrieved_at=datetime(2025, 12, 31, 13, 0, tzinfo=UTC),
        source_timezone="UTC",
        quality_status=QualityStatus.OK,
    )
    with pytest.raises(ValueError, match="out-of-window evaluation refused"):
        run_backtest(
            bars=[stray, *bars_from_closes(FIXTURE_UP)],
            make_ctx=lambda index, bar: make_ctx(bar_count=index + 1),
            slots=_all_slots()[:1],
            job=_job(),
        )


def test_fill_next_open_and_fail_closed_costs() -> None:
    bars = bars_from_closes(FIXTURE_UP)
    assert fill_at_next_open(bars, 0) == Decimal(str(bars[1].open))
    assert fill_at_next_open(bars, len(bars) - 1) is None
    with pytest.raises(ValueError, match="outside"):
        fill_at_next_open(bars, len(bars))
    with pytest.raises(ValueError, match="placeholders"):
        require_confirmed(placeholder_costs())
    net = apply_costs(
        fill=Decimal("100"), direction=Direction.LONG, costs=placeholder_costs()
    )
    assert net == Decimal("100")


def test_parameter_hash_stable_and_sensitive() -> None:
    first = _all_slots()[0].params
    assert hash_params(first) == hash_params(first)
    assert hash_params(first) != hash_params(_all_slots()[1].params)


def test_ctx_factory_threads_bar_cutoff() -> None:
    """Runner passes bars-so-far only: the ctx cutoff never sees the future."""
    seen: list[tuple[int, MarketBar]] = []

    def _factory(index: int, bar: MarketBar) -> MarketContext:
        seen.append((index, bar))
        return make_ctx(bar_count=index + 1)

    bars = bars_from_closes(FIXTURE_UP[:7])
    run_backtest(bars=bars, make_ctx=_factory, slots=_all_slots()[:1], job=_job())
    assert [index for index, _ in seen] == list(range(7))
