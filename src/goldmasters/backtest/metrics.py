"""Deterministic Decimal trade metrics — the only authoritative source (R-05).

Every metric below is computed here, in deterministic code, from Decimal
trade PnLs end to end — no float enters the path (non-Decimal input raises,
never coerces). Each metric carries its definition plus sample size on the
:class:`~goldmasters_contracts.BacktestMetric`, and every definition states
that costs are declared placeholders per D-6.1, so no metric is authoritative
until the operator confirms cost values. **No LLM prose introduces or
recalculates a metric** (T-06-09): reports quote these values, never recompute
them. Cost values stay placeholders per D-6.1 — inputs are net of whatever
costs the caller declared via :mod:`src.goldmasters.backtest.fills`.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from goldmasters_contracts import BacktestMetric

__all__ = [
    "expectancy",
    "max_drawdown",
    "profit_factor",
    "summarize_trades",
    "win_rate",
]

#: Appended to every metric definition: the D-6.1 non-authoritative marker.
_COST_MARKER = "costs placeholder per D-6.1, not authoritative"


def _checked(pnls: Sequence[Decimal]) -> tuple[Decimal, ...]:
    """Fail closed on non-Decimal input — a float must never enter the path."""
    checked = tuple(pnls)
    for pnl in checked:
        if not isinstance(pnl, Decimal):
            raise TypeError(f"trade PnL must be Decimal, got {type(pnl).__name__}")
    return checked


def win_rate(pnls: Sequence[Decimal]) -> Decimal | None:
    """Winners over total as a Decimal fraction; ``None`` when no trades."""
    checked = _checked(pnls)
    if not checked:
        return None
    wins = sum(1 for pnl in checked if pnl > 0)
    return Decimal(wins) / Decimal(len(checked))


def expectancy(pnls: Sequence[Decimal]) -> Decimal | None:
    """Mean net PnL per trade; ``None`` when no trades (never a default)."""
    checked = _checked(pnls)
    if not checked:
        return None
    return sum(checked, Decimal(0)) / Decimal(len(checked))


def profit_factor(pnls: Sequence[Decimal]) -> Decimal | None:
    """Gross profit over gross loss; ``None`` when undefined.

    No losing trades means the ratio is undefined, not infinite — returning
    a number there would invent a result. Empty input is likewise ``None``.
    """
    checked = _checked(pnls)
    gross_profit = sum((pnl for pnl in checked if pnl > 0), Decimal(0))
    gross_loss = sum((-pnl for pnl in checked if pnl < 0), Decimal(0))
    if not checked or gross_loss <= 0:
        return None
    return gross_profit / gross_loss


def max_drawdown(pnls: Sequence[Decimal]) -> Decimal | None:
    """Largest peak-to-trough decline of the cumulative net curve from zero.

    Breakeven trades neither deepen nor heal a drawdown; an all-profit curve
    draws down ``Decimal(0)``. Empty input is ``None``, never zero-as-default.
    """
    checked = _checked(pnls)
    if not checked:
        return None
    peak = Decimal(0)
    equity = Decimal(0)
    worst = Decimal(0)
    for pnl in checked:
        equity += pnl
        if equity > peak:
            peak = equity
        decline = peak - equity
        if decline > worst:
            worst = decline
    return worst


def _metric(name: str, definition: str, value: Decimal | None, sample_size: int) -> BacktestMetric:
    return BacktestMetric(
        name=name,
        definition=f"{definition}; {_COST_MARKER}",
        value=value,
        sample_size=sample_size,
    )


def summarize_trades(pnls: Sequence[Decimal]) -> tuple[BacktestMetric, ...]:
    """All four metrics over one closed-trade vector, Decimal end to end."""
    checked = _checked(pnls)
    count = len(checked)
    return (
        _metric(
            "win_rate",
            "winning trades over total trades as a Decimal fraction",
            win_rate(checked),
            count,
        ),
        _metric(
            "expectancy",
            "mean net PnL per trade (sum over count)",
            expectancy(checked),
            count,
        ),
        _metric(
            "profit_factor",
            "gross profit over gross loss; null when no losing trade defines it",
            profit_factor(checked),
            count,
        ),
        _metric(
            "max_drawdown",
            "largest peak-to-trough decline of the cumulative net curve from zero",
            max_drawdown(checked),
            count,
        ),
    )
