"""Fail-closed risk/validation gate: the sole path to TRADE-eligible levels.

Enforcement order per 03-RESEARCH.md Pattern 3: level ordering, configured
risk limits (``GOLDMASTERS_`` settings, fail-closed), data quality, required
evidence completeness. Malformed *inputs* raise via contract constructors;
policy *failures* return ``passed=False`` with ``reasons_for_rejection``
strings that flow into ``DecisionRecord``. Conflicting evidence is preserved
on the verdict (flows to ``DecisionRecord.conflicts``), never reconciled
silently. The CEO cannot bypass this gate (Rules §2.5): TRADE-eligible levels
leave only through :func:`trade_eligible_levels` on a passed verdict.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Annotated

from goldmasters_contracts import (
    ContractModel,
    Direction,
    EvidenceStatus,
    Levels,
    QualityStatus,
    TrendRegime,
)
from pydantic import Field, model_validator

from src.goldmasters.risk.levels import validate_level_ordering
from src.goldmasters.strategies.base import StrategyEvaluation

__all__ = [
    "GateVerdict",
    "PositiveDecimal",
    "evaluate_gate",
    "trade_eligible_levels",
]

#: Risk-limit argument form: finite and positive (settings floats arrive via
#: ``Decimal(str(value))`` at the call site — no float enters the level path).
PositiveDecimal = Annotated[Decimal, Field(gt=0)]


class GateVerdict(ContractModel):
    """Gate outcome: pass carries validated levels, block carries reasons.

    Invariants: a passed verdict must carry levels and no rejection reasons; a
    blocked verdict must carry at least one reason and no levels — a blocked
    candidate can never be a qualified trade.
    """

    passed: bool
    reasons_for_rejection: list[str] = Field(default_factory=list)
    levels: Levels | None = None
    conflicts: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_pass_block_split(self) -> GateVerdict:
        if self.passed and (self.levels is None or self.reasons_for_rejection):
            raise ValueError("a passed verdict must carry levels and no rejection reasons")
        if not self.passed and (not self.reasons_for_rejection or self.levels is not None):
            raise ValueError("a blocked verdict must carry reasons and no levels")
        return self


def evaluate_gate(
    *,
    evaluation: StrategyEvaluation,
    direction: Direction,
    regime: TrendRegime,
    quality_status: QualityStatus,
    quality_flags: Sequence[QualityStatus] = (),
    evidence: Mapping[str, EvidenceStatus] | None = None,
    conflicts: Sequence[str] = (),
    min_risk_reward_ratio: Decimal | None,
    max_risk_percent_per_idea: Decimal | None,
    risk_percent_for_idea: Decimal | None,
) -> GateVerdict:
    """Run the gate in enforcement order; fail-closed on every check.

    Policy arguments arrive from ``GOLDMASTERS_`` settings as ``Decimal`` (or
    ``None`` when unset — unset policy blocks, never defaults). ``evidence``
    maps each required evidence key to its :class:`EvidenceStatus`; every entry
    must be ``VALID``. ``conflicts`` are preserved verbatim for
    ``DecisionRecord.conflicts``.
    """
    reasons: list[str] = []
    if regime == TrendRegime.UNKNOWN:
        reasons.append("unknown regime: no setup is classified, candidate blocked")
    candidate = evaluation.candidate_levels
    if not evaluation.setup_found or candidate is None:
        reasons.append("no setup: a rule failed (or is unknown), levels stay null")
    else:
        ordering_reasons = validate_level_ordering(
            direction=direction,
            entry=candidate.entry,
            stop_loss=candidate.stop_loss,
            take_profits=candidate.take_profits,
        )
        reasons.extend(f"ordering: {reason}" for reason in ordering_reasons)
        if min_risk_reward_ratio is None:
            reasons.append("risk policy unset: GOLDMASTERS_MIN_RISK_REWARD_RATIO is required")
        elif candidate.risk_reward < min_risk_reward_ratio:
            reasons.append(
                f"risk_reward {candidate.risk_reward} below configured minimum "
                f"{min_risk_reward_ratio}"
            )
        if max_risk_percent_per_idea is None:
            reasons.append("risk policy unset: GOLDMASTERS_MAX_RISK_PERCENT_PER_IDEA is required")
        elif risk_percent_for_idea is None:
            reasons.append("idea risk unknown: risk percent must be computed, never guessed")
        elif risk_percent_for_idea > max_risk_percent_per_idea:
            reasons.append(
                f"idea risk {risk_percent_for_idea}% exceeds configured maximum "
                f"{max_risk_percent_per_idea}%"
            )
    if quality_status != QualityStatus.OK or len(quality_flags) > 0:
        reasons.append(
            f"data quality not healthy: status={quality_status.value}, "
            f"flags={[flag.value for flag in quality_flags]}"
        )
    if not evidence:
        reasons.append("evidence incomplete: required evidence set is missing or empty")
    else:
        invalid = sorted(key for key, status in evidence.items() if status != EvidenceStatus.VALID)
        if invalid:
            reasons.extend(f"evidence not valid: {key}" for key in invalid)
    if reasons:
        return GateVerdict(
            passed=False,
            reasons_for_rejection=reasons,
            conflicts=list(conflicts),
        )
    assert candidate is not None  # noqa: S101 — setup_found True guarantees levels
    return GateVerdict(passed=True, levels=candidate, conflicts=list(conflicts))


def trade_eligible_levels(verdict: GateVerdict) -> Levels | None:
    """The sole path to TRADE-eligible levels: non-``None`` only when passed.

    A blocked verdict yields ``None``, and a ``TRADE`` ``DecisionRecord``
    requires complete levels — so nothing reaches a decision unvalidated.
    """
    if not verdict.passed:
        return None
    return verdict.levels
