"""Deterministic backtest loop over the live path (criteria 2 and 3).

Per bar and per strategy the runner walks the live seam identically:
``evaluate`` with bars-so-far only (``bar_close_time`` cutoff, T-06-05),
then ``evaluate_gate`` as the sole path to TRADE-eligible levels, then
``trade_eligible_levels``. Any non-pass rule verdict forces ``setup_found``
False with null levels via the base validator — the runner never invents
levels. Fills are next-bar open with placeholder costs (D-6.1); every metric
definition states costs are placeholders, so no metric is authoritative.

Only pinned ``1.0.0`` strategies run: ``assert_pinned`` refuses any other
version, and ``PINNED_STRATEGIES`` names exactly the ten approved packages.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from goldmasters_contracts import (
    BacktestMetric,
    BacktestRecord,
    Direction,
    EvidenceStatus,
    MarketBar,
    Timeframe,
)

from src.goldmasters.backtest.fills import (
    FILL_MODEL,
    FillCosts,
    apply_costs,
    fill_at_next_open,
    to_assumptions,
)
from src.goldmasters.backtest.splits import (
    DatasetManifest,
    SplitWindows,
    build_manifest,
    enforce_splits,
)
from src.goldmasters.risk.gate import evaluate_gate, trade_eligible_levels
from src.goldmasters.strategies.base import MarketContext, StrategyEvaluation

__all__ = [
    "BacktestJob",
    "CtxFactory",
    "GatePolicy",
    "PINNED_STRATEGIES",
    "PINNED_STRATEGY_VERSION",
    "RunOutput",
    "StrategySlot",
    "assert_pinned",
    "hash_params",
    "run_backtest",
]

#: Exactly the ten approved agent packages (mirrors the strategy registry test).
PINNED_STRATEGIES: tuple[str, ...] = (
    "agent_01",
    "agent_02",
    "agent_03",
    "agent_04",
    "agent_05",
    "agent_06",
    "agent_07",
    "agent_08",
    "agent_09",
    "agent_10",
)

#: Every pinned strategy ships this version; anything else is refused.
PINNED_STRATEGY_VERSION = "1.0.0"

#: Context per bar step: index plus the just-closed bar (cutoff, never ahead).
CtxFactory = Callable[[int, MarketBar], MarketContext]


@dataclass(frozen=True)
class StrategySlot:
    """One pinned strategy: stamped identity, opaque params, bound evaluate."""

    strategy_id: str
    strategy_version: str
    code_hash: str
    params: object
    evaluate: Callable[[Sequence[MarketBar], MarketContext], StrategyEvaluation]


@dataclass(frozen=True)
class GatePolicy:
    """Explicit gate inputs; ``None`` policy blocks (fail-closed, never defaults)."""

    min_risk_reward_ratio: Decimal | None = None
    max_risk_percent_per_idea: Decimal | None = None
    risk_percent_for_idea: Decimal | None = None
    evidence: Mapping[str, EvidenceStatus] = field(default_factory=dict)


@dataclass(frozen=True)
class BacktestJob:
    """Declared inputs one run is reproducible from (criterion 2)."""

    run_id: str
    dataset_ref: str
    dataset_hash: str
    instrument_id: str
    provider_symbol: str
    timeframe: Timeframe
    display_timezone: str
    windows: SplitWindows
    code_version: str
    gate: GatePolicy = field(default_factory=GatePolicy)
    costs: FillCosts = field(default_factory=FillCosts)


@dataclass(frozen=True)
class RunOutput:
    """One record per strategy plus the single dataset manifest row."""

    records: tuple[BacktestRecord, ...]
    manifest: DatasetManifest


def assert_pinned(slot: StrategySlot) -> StrategySlot:
    """Refuse any strategy that is not a pinned 1.0.0 package."""
    if slot.strategy_version != PINNED_STRATEGY_VERSION:
        raise ValueError(
            f"{slot.strategy_id} version {slot.strategy_version!r} "
            f"is not pinned {PINNED_STRATEGY_VERSION!r}"
        )
    return slot


def hash_params(params: object) -> str:
    """Canonical sha256 over a params object (scope plus operator thresholds)."""
    import dataclasses

    if dataclasses.is_dataclass(params):
        raw = dataclasses.asdict(params)  # type: ignore[arg-type]
        document = json.dumps(raw, sort_keys=True, default=str)
    else:
        document = json.dumps(str(params), sort_keys=True)
    return hashlib.sha256(document.encode("utf-8")).hexdigest()


def _direction_from_levels(evaluation: StrategyEvaluation) -> Direction | None:
    """Infer gate direction from validated levels; equal levels stay blocked."""
    candidate = evaluation.candidate_levels
    if candidate is None:
        return None
    if candidate.stop_loss < candidate.entry:
        return Direction.LONG
    if candidate.entry < candidate.stop_loss:
        return Direction.SHORT
    return None


def _metric(name: str, definition: str, count: int) -> BacktestMetric:
    return BacktestMetric(
        name=name,
        definition=f"{definition}; costs placeholder per D-6.1, not authoritative",
        value=str(count),
        sample_size=count,
    )


def run_backtest(
    *,
    bars: Sequence[MarketBar],
    make_ctx: CtxFactory,
    slots: Sequence[StrategySlot],
    job: BacktestJob,
) -> RunOutput:
    """Run every slot over bars-so-far and build one full record per strategy."""
    if not slots:
        raise ValueError("run_backtest requires at least one strategy slot")
    for slot in slots:
        assert_pinned(slot)
    enforcement = enforce_splits(list(bars), job.windows, job.timeframe)
    if enforcement.out_of_window:
        raise ValueError(
            f"{len(enforcement.out_of_window)} bar(s) fall outside every split "
            "window: out-of-window evaluation refused"
        )
    window_bars = list(enforcement.in_window)
    if not window_bars:
        raise ValueError("no in-window bars to evaluate")
    manifest = build_manifest(
        dataset_ref=job.dataset_ref,
        bars=list(bars),
        symbol_mapping={job.instrument_id: job.provider_symbol},
        enforcement=enforcement,
    )
    generated_at = datetime.now(UTC)
    records: list[BacktestRecord] = []
    for slot in slots:
        records.append(
            _run_slot(
                slot=slot,
                bars=window_bars,
                make_ctx=make_ctx,
                job=job,
                enforcement_flags=list(enforcement.quality_flags),
                missing_periods=len(enforcement.missing_bars),
                generated_at=generated_at,
            )
        )
    return RunOutput(records=tuple(records), manifest=manifest)


def _run_slot(
    *,
    slot: StrategySlot,
    bars: list[MarketBar],
    make_ctx: CtxFactory,
    job: BacktestJob,
    enforcement_flags: list[str],
    missing_periods: int,
    generated_at: datetime,
) -> BacktestRecord:
    setups = 0
    gate_passes = 0
    fills = 0
    errors: list[str] = []
    errors.extend(enforcement_flags)
    for index, bar in enumerate(bars):
        bars_so_far = bars[: index + 1]
        ctx = make_ctx(index, bar)
        evaluation = slot.evaluate(bars_so_far, ctx)
        if not evaluation.setup_found:
            continue
        setups += 1
        direction = _direction_from_levels(evaluation)
        if direction is None:
            errors.append(
                f"bar {bar.bar_close_time.isoformat()}: setup with "
                "indeterminate direction from levels, gate blocked"
            )
            continue
        verdict = evaluate_gate(
            evaluation=evaluation,
            direction=direction,
            regime=ctx.regime,
            quality_status=ctx.quality_status,
            quality_flags=list(ctx.quality_flags),
            evidence=dict(job.gate.evidence),
            conflicts=(),
            min_risk_reward_ratio=job.gate.min_risk_reward_ratio,
            max_risk_percent_per_idea=job.gate.max_risk_percent_per_idea,
            risk_percent_for_idea=job.gate.risk_percent_for_idea,
        )
        levels = trade_eligible_levels(verdict)
        if levels is None:
            continue
        gate_passes += 1
        raw_fill = fill_at_next_open(bars, index)
        if raw_fill is None:
            errors.append(
                f"bar {bar.bar_close_time.isoformat()}: gate passed on the final "
                "bar, no next-bar open — fill skipped, never synthesised"
            )
            continue
        fills += 1
        _net = apply_costs(fill=raw_fill, direction=direction, costs=job.costs)
    metrics = (
        _metric("bars_evaluated", "closed bars evaluated bars-so-far", len(bars)),
        _metric(
            "setups_found",
            "evaluations with setup_found true and candidate levels",
            setups,
        ),
        _metric(
            "gate_passes",
            "setups passing evaluate_gate to TRADE-eligible levels",
            gate_passes,
        ),
        _metric(
            "fills_opened",
            f"gate passes filled at next-bar open ({FILL_MODEL})",
            fills,
        ),
    )
    return BacktestRecord(
        backtest_run_id=f"{job.run_id}:{slot.strategy_id}",
        strategy_id=slot.strategy_id,
        strategy_version=slot.strategy_version,
        dataset_ref=job.dataset_ref,
        dataset_hash=job.dataset_hash,
        instrument_id=job.instrument_id,
        timeframe=job.timeframe,
        start=bars[0].bar_open_time,
        end=bars[-1].bar_close_time,
        timezone=job.display_timezone,  # type: ignore[arg-type]
        data_quality=EvidenceStatus.MISSING
        if missing_periods
        else EvidenceStatus.VALID,
        parameter_hash=hash_params(slot.params),
        assumptions=to_assumptions(job.costs),
        in_sample_start=job.windows.in_sample_start,
        in_sample_end=job.windows.in_sample_end,
        validation_start=job.windows.validation_start,
        validation_end=job.windows.validation_end,
        out_of_sample_start=job.windows.out_of_sample_start,
        out_of_sample_end=job.windows.out_of_sample_end,
        metrics=list(metrics),
        generated_at=generated_at,
        code_version=job.code_version,
        status=EvidenceStatus.VALID,
        errors=errors,
    )
