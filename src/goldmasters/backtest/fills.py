"""Next-bar-open fills with placeholder costs (D-6.1, T-06-07).

Fill is at the next bar's open; a signal on the final bar has no next open
and is reported, never filled. Costs (spread, commission, slippage, swap) are
fail-closed settings: they ship as declared placeholders and stay
placeholders until the operator confirms values. **No metric derived through
this module is authoritative before that confirmation** — the fill-model
string on every record and every metric definition says so.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from goldmasters_contracts import BacktestAssumptions, Direction, MarketBar

__all__ = [
    "FILL_MODEL",
    "FillCosts",
    "apply_costs",
    "fill_at_next_open",
    "placeholder_costs",
    "require_confirmed",
    "to_assumptions",
]

#: Declared on every record; the PLACEHOLDER marker is the T-06-07 mitigation.
FILL_MODEL = (
    "next-bar-open; costs PLACEHOLDER pending operator confirmation (D-6.1); "
    "no metric authoritative until confirmed"
)


@dataclass(frozen=True)
class FillCosts:
    """Cost settings; ``confirmed`` flips only when the operator confirms values."""

    spread: str = "0"
    commission: str = "0"
    slippage: str = "0"
    swap: str = "0"
    confirmed: bool = False


def placeholder_costs() -> FillCosts:
    """The only cost set this phase may use: declared placeholders, unconfirmed."""
    return FillCosts()


def require_confirmed(costs: FillCosts) -> FillCosts:
    """Fail closed: authoritative use raises until the operator confirms values."""
    if not costs.confirmed:
        raise ValueError(
            "cost values are placeholders (D-6.1); operator confirmation required"
        )
    return costs


def to_assumptions(costs: FillCosts) -> BacktestAssumptions:
    """Carry the declared (placeholder) costs onto the record assumptions."""
    return BacktestAssumptions(
        spread=costs.spread,
        commission=costs.commission,
        slippage=costs.slippage,
        fill_model=FILL_MODEL,
    )


def fill_at_next_open(
    bars: Sequence[MarketBar], signal_index: int
) -> Decimal | None:
    """Next-bar open price, or ``None`` when the signal sits on the final bar."""
    ordered = list(bars)
    if signal_index < 0 or signal_index >= len(ordered):
        raise ValueError(f"signal_index {signal_index} outside 0..{len(ordered) - 1}")
    if signal_index + 1 >= len(ordered):
        return None
    return Decimal(str(ordered[signal_index + 1].open))


def apply_costs(*, fill: Decimal, direction: Direction, costs: FillCosts) -> Decimal:
    """Adjust a fill against the declared spread/slippage in Decimal.

    Long pays up (half-spread plus slippage); short mirrors. Commission and
    swap are per-trade terms carried on the assumptions, not the price.
    With placeholder zeros this is the identity — the math stays so any
    operator-confirmed value flows through the same path.
    """
    half_spread = Decimal(costs.spread) / 2 + Decimal(costs.slippage)
    if direction == Direction.LONG:
        return fill + half_spread
    if direction == Direction.SHORT:
        return fill - half_spread
    raise ValueError(f"unknown direction {direction.value!r}: no fill price defined")
