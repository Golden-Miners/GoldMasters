"""Strategy framework: evaluate(bars, ctx) vocabulary every approved agent speaks.

This module is the vocabulary every approved strategy speaks — and the
constraint none can evade. The hard rule is encoded in
:class:`StrategyEvaluation`: any rule verdict other than ``pass`` (``fail``
*or* ``unknown``) means no setup and null levels, enforced by a Pydantic
validator so no future strategy package can emit levels on a failed rule.

Extended in phase 3.1 (03.1-RESEARCH.md locked shape): agents evaluate
``(bars, ctx)`` where ``ctx`` is a :class:`MarketContext` carrying regime,
quality, volume type, tick/contract size, bar count and clock — never price
data. Agent outcomes map through the adapter to exactly one of
``SETUP_FOUND | NO_SETUP | INSUFFICIENT_DATA | NOT_APPLICABLE`` with the
locked gate-input table (only ``SETUP_FOUND`` reaches the gate;
``NOT_APPLICABLE`` maps to ``AgentRunStatus.skipped`` with no new enum
member). The :class:`EligibilityRule` matrix selects which agents run; an
empty instrument list means none, never all. No approved agent packages ship
in this phase — each agent phase adds one package and extends the registry
test. ``STRATEGY_VERSION`` is semver and is bumped on any rule change.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from decimal import Decimal
from typing import Literal, Protocol, runtime_checkable

from goldmasters_contracts import (
    AgentRunStatus,
    ContractModel,
    Direction,
    Levels,
    MarketBar,
    PriceStr,
    ProviderId,
    QualityFlag,
    QualityStatus,
    Timeframe,
    TrendRegime,
    UtcDatetime,
    VolumeType,
)
from pydantic import Field, model_validator

__all__ = [
    "AdapterStatus",
    "EligibilityRule",
    "EligibilityVerdict",
    "MarketContext",
    "RuleCheck",
    "RuleVerdict",
    "Strategy",
    "StrategyEvaluation",
    "adapter_feeds_gate",
    "adapter_run_status",
    "build_adapter_evaluation",
    "build_evaluation",
    "build_levels_evaluation",
    "eligible_agents",
    "hash_rule_source",
    "meets_min_bars",
]

#: One verdict per rule: pass, fail, or unknown (Schema.md §8).
RuleVerdict = Literal["pass", "fail", "unknown"]


def hash_rule_source(source: str) -> str:
    """Integrity label over a rule text (hashlib stdlib; not tamper-proofing)."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


class RuleCheck(ContractModel):
    """One rule's evidence: ID, verdict, observed inputs, trace, reason."""

    rule_id: str = Field(min_length=1)
    verdict: RuleVerdict
    inputs: dict[str, str] = Field(default_factory=dict)
    evidence: str
    reason: str


class StrategyEvaluation(ContractModel):
    """A strategy evaluation: setup flag plus per-rule evidence (Schema.md §8).

    Invariants (the no-escape clause): any non-``pass`` verdict forces
    ``setup_found=False`` with null levels; a ``True`` setup must carry
    candidate levels produced by defined rules.
    """

    strategy_id: str = Field(min_length=1)
    strategy_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    code_hash: str = Field(min_length=1)
    setup_found: bool
    rule_checks: list[RuleCheck] = Field(min_length=1)
    candidate_levels: Levels | None = None
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_no_setup_on_fail(self) -> StrategyEvaluation:
        blocked = any(check.verdict != "pass" for check in self.rule_checks)
        if blocked and (self.setup_found or self.candidate_levels is not None):
            raise ValueError("any rule fail/unknown means no setup and null levels")
        if self.setup_found and self.candidate_levels is None:
            raise ValueError("a found setup must carry candidate levels from defined rules")
        if not self.setup_found and self.candidate_levels is not None:
            raise ValueError("no setup must carry null levels")
        return self


def build_evaluation(
    *,
    strategy_id: str,
    strategy_version: str,
    code_hash: str,
    rule_checks: Sequence[RuleCheck],
    candidate_levels: Levels | None = None,
    limitations: Sequence[str] = (),
) -> StrategyEvaluation:
    """Build a stamped evaluation; the invariants are enforced on construction."""
    return StrategyEvaluation(
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        code_hash=code_hash,
        setup_found=all(check.verdict == "pass" for check in rule_checks)
        and candidate_levels is not None,
        rule_checks=list(rule_checks),
        candidate_levels=candidate_levels,
        limitations=list(limitations),
    )


class MarketContext(ContractModel):
    """Non-price evaluation context every agent receives alongside bars.

    Carries regime (eligibility + rule branching), quality (fail-closed
    without re-validating), ``volume_type`` (never relabel tick as
    exchange), tick/contract size, bar count and clock. ``tick_size`` and
    ``contract_size`` are decimal strings; ``None`` means unknown
    precision/provenance so the caller skips alignment, never a default.
    No price or volume data lives here — bars remain the sole price input.
    """

    instrument_id: str = Field(min_length=1)
    provider_id: ProviderId
    timeframe: Timeframe
    regime: TrendRegime
    quality_status: QualityStatus
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    volume_type: VolumeType
    tick_size: PriceStr | None = None
    contract_size: PriceStr | None = None
    bar_count: int = Field(ge=0)
    now_utc: UtcDatetime


#: Agent outcome vocabulary: exactly one per evaluation (03.1-RESEARCH.md).
AdapterStatus = Literal["SETUP_FOUND", "NO_SETUP", "INSUFFICIENT_DATA", "NOT_APPLICABLE"]

#: Locked adapter → run-status mapping. NOT_APPLICABLE maps to the verbatim
#: ``skipped`` member; AgentRunStatus gains no new member (closed enum, D-23).
_ADAPTER_RUN_STATUS: dict[AdapterStatus, AgentRunStatus] = {
    "SETUP_FOUND": AgentRunStatus.OK,
    "NO_SETUP": AgentRunStatus.NO_SETUP,
    "INSUFFICIENT_DATA": AgentRunStatus.INSUFFICIENT_DATA,
    "NOT_APPLICABLE": AgentRunStatus.SKIPPED,
}

#: Locked gate-input table: only SETUP_FOUND reaches ``evaluate_gate``.
_ADAPTER_GATE_INPUT: dict[AdapterStatus, bool] = {
    "SETUP_FOUND": True,
    "NO_SETUP": False,
    "INSUFFICIENT_DATA": False,
    "NOT_APPLICABLE": False,
}


def adapter_run_status(status: AdapterStatus) -> AgentRunStatus:
    """Map an adapter outcome to its locked ``AgentRunStatus`` member."""
    return _ADAPTER_RUN_STATUS[status]


def adapter_feeds_gate(status: AdapterStatus) -> bool:
    """True only for ``SETUP_FOUND`` — every other outcome never reaches the gate."""
    return _ADAPTER_GATE_INPUT[status]


def build_adapter_evaluation(
    *,
    status: AdapterStatus,
    strategy_id: str,
    strategy_version: str,
    code_hash: str,
    rule_checks: Sequence[RuleCheck],
    candidate_levels: Levels | None = None,
    limitations: Sequence[str] = (),
) -> tuple[StrategyEvaluation, AgentRunStatus]:
    """Build the evaluation for an adapter outcome plus its run status.

    Only ``SETUP_FOUND`` may carry levels — any other status forces null
    levels through :func:`build_evaluation`, so all four states satisfy the
    untouched no-escape validator. The rule checks stay authoritative for
    the evaluation; ``status`` drives run-status routing and gate input.
    """
    evaluation = build_evaluation(
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        code_hash=code_hash,
        rule_checks=rule_checks,
        candidate_levels=candidate_levels if status == "SETUP_FOUND" else None,
        limitations=limitations,
    )
    return evaluation, adapter_run_status(status)


class EligibilityRule(ContractModel):
    """One matrix row: who runs where, with settings-driven values.

    ``instruments`` holds canonical ids; an empty list means none, never
    "all" by default. ``regimes`` lists the regimes the agent evaluates
    in; others yield ``NOT_APPLICABLE``. Below ``min_bars`` the agent still
    runs and reports ``INSUFFICIENT_DATA`` — bars never exclude, only scope
    does (see :func:`meets_min_bars`).
    """

    strategy_id: str = Field(min_length=1)
    enabled: bool
    instruments: list[str] = Field(default_factory=list)
    timeframes: list[Timeframe] = Field(default_factory=list)
    regimes: list[TrendRegime] = Field(default_factory=list)
    min_bars: int = Field(ge=1)


#: Per-agent matrix verdict consumed by the Phase 4 supervisor.
EligibilityVerdict = Literal["eligible", "not_applicable", "disabled"]


def meets_min_bars(rule: EligibilityRule, bar_count: int) -> bool:
    """True when the bar count reaches the row minimum; below means INSUFFICIENT_DATA."""
    return bar_count >= rule.min_bars


def eligible_agents(
    matrix: Sequence[EligibilityRule], ctx: MarketContext
) -> dict[str, EligibilityVerdict]:
    """Select agents by enabled, instruments, timeframes and regimes.

    A disabled row yields ``disabled``; any scope mismatch (instrument,
    timeframe, regime — including an empty instrument list, which means
    none) yields ``not_applicable``. Bar count never excludes here: below
    ``min_bars`` the agent reports ``INSUFFICIENT_DATA`` at evaluate time.
    """
    verdicts: dict[str, EligibilityVerdict] = {}
    for rule in matrix:
        if not rule.enabled:
            verdicts[rule.strategy_id] = "disabled"
        elif (
            ctx.instrument_id not in rule.instruments
            or ctx.timeframe not in rule.timeframes
            or ctx.regime not in rule.regimes
        ):
            verdicts[rule.strategy_id] = "not_applicable"
        else:
            verdicts[rule.strategy_id] = "eligible"
    return verdicts


def build_levels_evaluation(
    *,
    strategy_id: str,
    strategy_version: str,
    code_hash: str,
    rule_checks: Sequence[RuleCheck],
    direction: Direction,
    entry: Decimal,
    stop_loss: Decimal,
    take_profits: Sequence[Decimal],
    tick_size: Decimal,
    claimed_risk_reward: Decimal | None = None,
    limitations: Sequence[str] = (),
) -> StrategyEvaluation:
    """Route rule-derived prices through ``risk.levels`` into an evaluation.

    Levels flow through :func:`risk.levels.build_candidate_levels` so
    quantization, ordering and R:R recompute stay centralized; agents never
    construct levels directly. The import is function-local because
    ``risk.levels`` itself imports this module for ``RuleCheck``.
    """
    from src.goldmasters.risk.levels import build_candidate_levels

    return build_evaluation(
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        code_hash=code_hash,
        rule_checks=rule_checks,
        candidate_levels=build_candidate_levels(
            direction=direction,
            rule_checks=rule_checks,
            entry=entry,
            stop_loss=stop_loss,
            take_profits=take_profits,
            tick_size=tick_size,
            claimed_risk_reward=claimed_risk_reward,
        ),
        limitations=limitations,
    )


@runtime_checkable
class Strategy(Protocol):
    """What every approved strategy package implements (D-3.1)."""

    STRATEGY_ID: str
    STRATEGY_VERSION: str
    CODE_HASH: str

    def evaluate(self, bars: Sequence[MarketBar], ctx: MarketContext) -> StrategyEvaluation:
        """Evaluate closed bars in context; never emit levels on a failed rule."""
        ...
