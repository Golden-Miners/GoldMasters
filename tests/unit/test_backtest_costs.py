"""Cost-application guards: fail-closed cost configuration (06-03).

Placeholder costs ship as None (unconfigured) per D-6.1; they must never silently
become zero-cost backtests. An explicitly configured zero cost (Decimal("0"))
means free trading and is distinct from unconfigured. The fill path must apply
whatever is declared, never silently zero it. ``require_confirmed`` refuses
authoritative use until the operator confirms values.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from goldmasters_contracts import Direction

from src.goldmasters.backtest.fills import (
    FILL_MODEL,
    FillCosts,
    apply_costs,
    placeholder_costs,
    require_confirmed,
    to_assumptions,
)


def _round_trip_loss(*, fill: Decimal, direction: Direction, costs: FillCosts) -> Decimal:
    """FIXTURE zero-edge round trip: enter and exit at the same price."""
    entry = apply_costs(fill=fill, direction=direction, costs=costs)
    exit_side = Direction.SHORT if direction == Direction.LONG else Direction.LONG
    exit_price = apply_costs(fill=fill, direction=exit_side, costs=costs)
    gross = (exit_price - entry) if direction == Direction.LONG else (entry - exit_price)
    return gross - costs.commission - costs.swap


def test_placeholder_costs_are_unconfigured() -> None:
    """Placeholder costs ship with all fields None (unconfigured), not zero."""
    costs = placeholder_costs()
    assert costs.spread is None
    assert costs.commission is None
    assert costs.slippage is None
    assert costs.swap is None
    assert costs.confirmed is False
    assert costs.is_configured() is False


def test_configured_costs_are_configured() -> None:
    """Explicitly configured costs (including zero) report configured=True."""
    costs = FillCosts(
        spread=Decimal("0"),
        commission=Decimal("0"),
        slippage=Decimal("0"),
        swap=Decimal("0"),
        confirmed=True,
    )
    assert costs.is_configured() is True


def test_unconfigured_costs_raise_in_apply_costs() -> None:
    """Unconfigured costs fail closed: apply_costs raises ValueError."""
    costs = placeholder_costs()
    with pytest.raises(ValueError, match="cost values are not configured"):
        apply_costs(fill=Decimal("100"), direction=Direction.LONG, costs=costs)


def test_configured_costs_flow_through_the_same_path() -> None:
    """FIXTURE nonzero costs flow through the fill path, never silently zeroed."""
    costs = FillCosts(
        spread=Decimal("2"),
        commission=Decimal("0"),
        slippage=Decimal("1"),
        swap=Decimal("0"),
        confirmed=True,
    )
    assert costs.is_configured() is True
    loss = _round_trip_loss(fill=Decimal("100"), direction=Direction.LONG, costs=costs)
    # Long pays half-spread + slippage per side: (1 + 1) * 2 = 4.
    assert loss == -(costs.spread + costs.slippage * 2) == Decimal("-4")
    short_loss = _round_trip_loss(fill=Decimal("100"), direction=Direction.SHORT, costs=costs)
    assert short_loss == Decimal("-4")


def test_unconfigured_costs_refused_for_authoritative_use() -> None:
    """require_confirmed rejects unconfigured costs; confirmed zero costs pass."""
    costs = placeholder_costs()
    with pytest.raises(ValueError, match="placeholders"):
        require_confirmed(costs)
    assumptions = to_assumptions(costs)
    assert "PLACEHOLDER" in assumptions.fill_model
    assert assumptions.fill_model == FILL_MODEL
    wire = assumptions.model_dump(mode="json")
    assert wire["spread"] is None
    assert wire["commission"] is None
    assert wire["slippage"] is None
    assert wire["swap"] is None


def test_configured_costs_pass_require_confirmed() -> None:
    """Confirmed costs (including zeros) pass require_confirmed."""
    costs = FillCosts(
        spread=Decimal("0"),
        commission=Decimal("0"),
        slippage=Decimal("0"),
        swap=Decimal("0"),
        confirmed=True,
    )
    assert require_confirmed(costs) is costs
    assumptions = to_assumptions(costs)
    assert assumptions.spread == Decimal("0")
    assert assumptions.commission == Decimal("0")
    assert assumptions.slippage == Decimal("0")
    assert assumptions.swap == Decimal("0")
    wire = assumptions.model_dump(mode="json")
    assert wire["spread"] == "0"
    assert wire["commission"] == "0"
    assert wire["slippage"] == "0"
    assert wire["swap"] == "0"