"""Cost-application guards: zero-edge loss equals declared costs (06-03 tracer).

Placeholder costs ship as declared zeros per D-6.1; the fill path must apply
whatever is declared, never silently zero it. Zero-edge round trip: gross PnL
0, net loss exactly the declared per-round-trip total. A nonzero FIXTURE cost
set proves the arithmetic; the placeholder set proves fail-closed
(``require_confirmed`` refuses authoritative use until the operator confirms).
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


def test_zero_edge_loss_equals_declared_placeholder_costs() -> None:
    costs = placeholder_costs()
    declared_per_trip = costs.spread + costs.slippage * 2 + costs.commission + costs.swap
    loss = _round_trip_loss(fill=Decimal("100"), direction=Direction.LONG, costs=costs)
    assert loss == -declared_per_trip == Decimal("0")
    assert isinstance(loss, Decimal)


def test_nonzero_fixture_costs_flow_through_the_same_path() -> None:
    """FIXTURE numbers proving the path applies declared values, never zeroes them."""
    costs = FillCosts(
        spread=Decimal("2"),
        commission=Decimal("0"),
        slippage=Decimal("1"),
        swap=Decimal("0"),
        confirmed=True,
    )
    loss = _round_trip_loss(fill=Decimal("100"), direction=Direction.LONG, costs=costs)
    # Long pays half-spread + slippage per side: (1 + 1) * 2 = 4.
    assert loss == -(costs.spread + costs.slippage * 2) == Decimal("-4")
    short_loss = _round_trip_loss(fill=Decimal("100"), direction=Direction.SHORT, costs=costs)
    assert short_loss == Decimal("-4")


def test_placeholder_costs_refused_for_authoritative_use() -> None:
    with pytest.raises(ValueError, match="placeholders"):
        require_confirmed(placeholder_costs())
    assumptions = to_assumptions(placeholder_costs())
    assert "PLACEHOLDER" in assumptions.fill_model
    assert assumptions.fill_model == FILL_MODEL
    wire = assumptions.model_dump(mode="json")
    assert wire["spread"] == str(Decimal("0"))
