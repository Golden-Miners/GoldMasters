"""Leakage plus timestamp-alignment guards: one strategy, five bars (06-03 tracer).

Honesty slice: 5-bar FIXTURE through the splits gate, one stub strategy
evaluate with bars-so-far only, the real ``evaluate_gate``, next-bar-open
placeholder-cost fill, and Decimal metrics. Leakage probe: a future spike
planted on bar N+1 leaves the bar-N evaluation and fill untouched.
Alignment: a signal is attributed to the next bar, never the signal bar, on
UTC boundaries. Each guard fails when its assumption is violated.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from decimal import Decimal

from goldmasters_contracts import Direction, EvidenceStatus, MarketBar, Timeframe

from src.goldmasters.backtest.fills import apply_costs, fill_at_next_open, placeholder_costs
from src.goldmasters.backtest.metrics import summarize_trades
from src.goldmasters.backtest.splits import SplitWindows, enforce_splits
from src.goldmasters.risk.gate import evaluate_gate, trade_eligible_levels
from src.goldmasters.strategies.base import (
    MarketContext,
    RuleCheck,
    StrategyEvaluation,
    build_levels_evaluation,
)
from tests.unit.agent_fixtures import T0, bars_from_closes, make_ctx

#: FIXTURE 5-bar rising vector: labelled test data, never live data.
FIXTURE_CLOSES = ["100", "102", "104", "106", "108"]
#: Future spike planted on bar N+1 (index 3) for the leakage probe.
SPIKE_CLOSE = "1000"
SIGNAL_INDEX = 2


def _windows() -> SplitWindows:
    return SplitWindows(
        in_sample_start=T0,
        in_sample_end=T0 + timedelta(hours=12),
        validation_start=T0 + timedelta(hours=12),
        validation_end=T0 + timedelta(hours=13),
        out_of_sample_start=T0 + timedelta(hours=13),
        out_of_sample_end=T0 + timedelta(hours=14),
    )


def _stub_evaluate(
    bars_so_far: Sequence[MarketBar], ctx: MarketContext, seen: list[int]
) -> StrategyEvaluation:
    """FIXTURE signal logic: LONG when the last two closes rise, else no setup."""
    seen.append(len(bars_so_far))
    rising = (
        len(bars_so_far) >= 3
        and bars_so_far[-1].close > bars_so_far[-2].close > bars_so_far[-3].close
    )
    if not rising:
        return build_levels_evaluation(
            strategy_id="honesty-stub",
            strategy_version="1.0.0",
            code_hash="stub",
            rule_checks=[
                RuleCheck(
                    rule_id="rise",
                    verdict="fail",
                    inputs={},
                    evidence="no rise",
                    reason="FIXTURE: last two closes did not rise",
                )
            ],
            direction=Direction.LONG,
            entry=Decimal(0),
            stop_loss=Decimal(0),
            take_profits=[Decimal(0)],
            tick_size=Decimal("0.01"),
        )
    close = Decimal(str(bars_so_far[-1].close))
    return build_levels_evaluation(
        strategy_id="honesty-stub",
        strategy_version="1.0.0",
        code_hash="stub",
        rule_checks=[
            RuleCheck(
                rule_id="rise",
                verdict="pass",
                inputs={"close": str(close)},
                evidence="FIXTURE rise",
                reason="FIXTURE: last two closes rose",
            )
        ],
        direction=Direction.LONG,
        entry=close,
        stop_loss=close - Decimal(10),
        take_profits=[close + Decimal(20)],
        tick_size=Decimal("0.01"),
    )


def _run_slice(bars: list[MarketBar]) -> dict[str, object]:
    """One honest pass: splits gate, bars-so-far evaluate, gate, fill, metrics."""
    enforcement = enforce_splits(bars, _windows(), Timeframe.H1)
    assert not enforcement.out_of_window
    assert not enforcement.missing_bars
    seen: list[int] = []
    signal_index: int | None = None
    fill: Decimal | None = None
    for index, _bar in enumerate(bars):
        bars_so_far = bars[: index + 1]
        evaluation = _stub_evaluate(bars_so_far, make_ctx(bar_count=index + 1), seen)
        if not evaluation.setup_found:
            continue
        verdict = evaluate_gate(
            evaluation=evaluation,
            direction=Direction.LONG,
            regime=make_ctx().regime,
            quality_status=make_ctx().quality_status,
            quality_flags=[],
            evidence={"bars": EvidenceStatus.VALID},
            conflicts=(),
            min_risk_reward_ratio=Decimal("1"),
            max_risk_percent_per_idea=Decimal("2"),
            risk_percent_for_idea=Decimal("1"),
        )
        if trade_eligible_levels(verdict) is None:
            continue
        signal_index = index
        fill = fill_at_next_open(bars, index)
        break
    assert signal_index is not None and fill is not None
    costs = placeholder_costs()
    net_fill = apply_costs(fill=fill, direction=Direction.LONG, costs=costs)
    exit_open = Decimal(str(bars[-1].open))  # FIXTURE exit rule: last bar open
    pnl = exit_open - net_fill
    (win_metric,) = [metric for metric in summarize_trades((pnl,)) if metric.name == "win_rate"]
    return {
        "signal_index": signal_index,
        "fill": fill,
        "pnl": pnl,
        "bars_seen": seen,
        "win_rate": win_metric.value,
    }


def test_slice_signals_then_fills_next_bar_in_decimal() -> None:
    bars = bars_from_closes(FIXTURE_CLOSES)
    result = _run_slice(bars)
    assert result["signal_index"] == SIGNAL_INDEX
    # Next-bar open, never the signal bar open: 104 vs 102.
    assert result["fill"] == Decimal(str(bars[SIGNAL_INDEX + 1].open)) == Decimal("104")
    assert result["fill"] != Decimal(str(bars[SIGNAL_INDEX].open))
    # FIXTURE exit at last-bar open 106: hand PnL 106 - 104 = 2.
    assert result["pnl"] == Decimal("2")
    assert isinstance(result["pnl"], Decimal)
    assert result["win_rate"] == Decimal(1)
    assert result["bars_seen"] == [1, 2, 3]


def test_future_spike_leaves_signal_bar_evaluation_untouched() -> None:
    clean = bars_from_closes(FIXTURE_CLOSES)
    spiked_closes = FIXTURE_CLOSES[:3] + [SPIKE_CLOSE, "108"]
    spiked = bars_from_closes(spiked_closes)
    clean_result = _run_slice(clean)
    # Evaluation at the signal bar sees bars-so-far only: identical prefix.
    seen_clean: list[int] = []
    seen_spiked: list[int] = []
    clean_eval = _stub_evaluate(clean[:3], make_ctx(bar_count=3), seen_clean)
    spiked_eval = _stub_evaluate(spiked[:3], make_ctx(bar_count=3), seen_spiked)
    assert clean_eval == spiked_eval
    assert clean_eval.setup_found
    # The fill uses the next-bar *open* (104): the spiked close (1000) cannot move it.
    assert fill_at_next_open(spiked, SIGNAL_INDEX) == Decimal("104")
    assert clean_result["signal_index"] == SIGNAL_INDEX


def test_signal_attributed_to_next_bar_on_utc_boundaries() -> None:
    bars = bars_from_closes(FIXTURE_CLOSES)
    result = _run_slice(bars)
    index = result["signal_index"]
    assert isinstance(index, int)
    signal_bar = bars[index]
    fill_bar = bars[index + 1]
    assert signal_bar.bar_open_time is not None and signal_bar.bar_close_time is not None
    assert fill_bar.bar_open_time is not None
    # Contiguous H1 bars: fill opens exactly when the signal bar closes (UTC).
    assert fill_bar.bar_open_time == signal_bar.bar_close_time
    assert fill_bar.bar_open_time.tzinfo is not None
    assert fill_bar.bar_open_time.utcoffset() == timedelta(0)
    # A signal on the final bar has no next open: reported, never synthesised.
    assert fill_at_next_open(bars, len(bars) - 1) is None
