"""Candidate levels: code-computed entry/stop/targets, Decimal R:R, ordering (D-3.3).

Levels are computed here, in deterministic code, never authored by a model
(Rules §3.5): the caller supplies rule-derived prices, this module quantizes
them to tick via :func:`conventions.quantize_to_tick` (never re-implemented),
validates standard-mirror ordering (long ``stop < entry < tp1 < tp2…``; short
mirrors), and recomputes ``risk_reward`` in :class:`~decimal.Decimal` from the
validated levels — a claimed value from strategy output is cross-checked, never
trusted. Anything unknown or invalid yields ``None`` (null-when-unknown, never
a default level); the gate treats ``None`` as blocked.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from goldmasters_contracts import Direction, Levels

from src.goldmasters.domain.conventions import quantize_to_tick
from src.goldmasters.strategies.base import RuleCheck

__all__ = [
    "build_candidate_levels",
    "compute_risk_reward",
    "validate_level_ordering",
]


def compute_risk_reward(*, entry: Decimal, stop_loss: Decimal, first_target: Decimal) -> Decimal:
    """Reward-to-risk from validated levels, Decimal end to end (D-3.3).

    ``reward = |tp1 - entry|``, ``risk = |entry - stop|``; both must be
    positive (ordering validation guarantees this — this guard is unreachable
    on a validated path and exists so a zero distance can never divide).
    """
    risk = abs(entry - stop_loss)
    reward = abs(first_target - entry)
    if risk <= 0 or reward <= 0:
        raise ValueError(f"non-positive risk ({risk}) or reward ({reward}) — order first")
    return reward / risk


def validate_level_ordering(
    *,
    direction: Direction,
    entry: Decimal,
    stop_loss: Decimal,
    take_profits: Sequence[Decimal],
) -> list[str]:
    """Standard-mirror ordering check (D-3.3); empty list means valid.

    Long: ``stop < entry < tp1 < tp2 …``. Short mirrors:
    ``… tp2 < tp1 < entry < stop``. Any other direction (neutral/unknown) or
    any violation returns reason strings; an empty target list is a violation.
    """
    if direction == Direction.LONG:
        if not stop_loss < entry:
            return ["long ordering violated: stop_loss must be below entry"]
    elif direction == Direction.SHORT:
        if not entry < stop_loss:
            return ["short ordering violated: stop_loss must be above entry"]
    else:
        return [f"unknown direction {direction.value!r}: no ordering defined, levels stay null"]
    if len(take_profits) == 0:
        return ["at least one take-profit is required"]
    reasons: list[str] = []
    previous = entry
    if direction == Direction.SHORT:
        for index, target in enumerate(take_profits, start=1):
            if not target < previous:
                reasons.append(
                    f"short ordering violated: tp{index} must be below entry/tp{index - 1}"
                )
            previous = target
    else:
        for index, target in enumerate(take_profits, start=1):
            if not previous < target:
                reasons.append(
                    f"long ordering violated: tp{index} must be above entry/tp{index - 1}"
                )
            previous = target
    return reasons


def build_candidate_levels(
    *,
    direction: Direction,
    rule_checks: Sequence[RuleCheck],
    entry: Decimal,
    stop_loss: Decimal,
    take_profits: Sequence[Decimal],
    tick_size: Decimal,
    claimed_risk_reward: Decimal | None = None,
) -> Levels | None:
    """Quantize, order-validate, and recompute R:R; ``None`` when unknown (D-3.3).

    Consumes the strategy ``rule_checks`` (any non-``pass`` verdict means no
    setup — mirrors the :class:`StrategyEvaluation` no-escape clause) and
    :func:`conventions.quantize_to_tick` for every level. ``risk_reward`` is
    recomputed from the validated quantized levels; a ``claimed_risk_reward``
    that differs means tampering-or-bug and yields ``None``. Ordering is
    validated on the quantized values, so a level that drifts across another
    under quantization is caught, not shipped.
    """
    if any(check.verdict != "pass" for check in rule_checks):
        return None
    if not isinstance(tick_size, Decimal):
        raise TypeError("tick_size must be Decimal (Decimal-only price path)")
    quantized_entry = quantize_to_tick(entry, tick_size)
    quantized_stop = quantize_to_tick(stop_loss, tick_size)
    quantized_targets = [quantize_to_tick(target, tick_size) for target in take_profits]
    if validate_level_ordering(
        direction=direction,
        entry=quantized_entry,
        stop_loss=quantized_stop,
        take_profits=quantized_targets,
    ):
        return None
    risk_reward = compute_risk_reward(
        entry=quantized_entry,
        stop_loss=quantized_stop,
        first_target=quantized_targets[0],
    )
    if claimed_risk_reward is not None and claimed_risk_reward != risk_reward:
        return None
    return Levels(
        entry=quantized_entry,
        stop_loss=quantized_stop,
        take_profits=quantized_targets,
        risk_reward=risk_reward,
    )
