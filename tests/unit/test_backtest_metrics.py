"""Deterministic Decimal metrics with a hand-verifiable 5-trade ledger (06-03 Task 1).

FIXTURE ledger (hand-computed, independent of the implementation):
trades ``[+10, -5, +20, -10, +5]`` give wins 3/5 = 0.6, sum 20 so expectancy
4, gross profit 35 over gross loss 15 so profit factor 35/15, and cumulative
curve ``[10, 5, 25, 15, 20]`` whose peak-to-trough declines are ``[0, 5, 0,
10, 5]`` so max drawdown 10. Only ``backtest/metrics.py`` output is
authoritative (R-05); this file asserts equality against the hand ledger.
"""

from __future__ import annotations

import pathlib
from decimal import Decimal

import pytest

from src.goldmasters.backtest.metrics import (
    expectancy,
    max_drawdown,
    profit_factor,
    summarize_trades,
    win_rate,
)

#: FIXTURE 5-trade hand ledger: labelled test vector, never live data.
FIXTURE_TRADES = (Decimal(10), Decimal(-5), Decimal(20), Decimal(-10), Decimal(5))

#: Hand-computed expectations, written as literals — not via the module.
EXPECTED_WIN_RATE = Decimal(3) / Decimal(5)
EXPECTED_EXPECTANCY = Decimal(20) / Decimal(5)
EXPECTED_PROFIT_FACTOR = Decimal(35) / Decimal(15)
EXPECTED_MAX_DRAWDOWN = Decimal(10)


def test_hand_ledger_matches_code_output() -> None:
    assert win_rate(FIXTURE_TRADES) == EXPECTED_WIN_RATE
    assert expectancy(FIXTURE_TRADES) == EXPECTED_EXPECTANCY
    assert profit_factor(FIXTURE_TRADES) == EXPECTED_PROFIT_FACTOR
    assert max_drawdown(FIXTURE_TRADES) == EXPECTED_MAX_DRAWDOWN


def test_hand_ledger_literals_are_exact() -> None:
    """The hand ledger itself: no hidden rounding behind the expectations."""
    assert EXPECTED_WIN_RATE == Decimal("0.6")
    assert EXPECTED_EXPECTANCY == Decimal("4")
    assert EXPECTED_MAX_DRAWDOWN == Decimal(10)
    assert EXPECTED_PROFIT_FACTOR * Decimal(15) == Decimal(35)


def test_outputs_are_decimal_end_to_end() -> None:
    for value in (
        win_rate(FIXTURE_TRADES),
        expectancy(FIXTURE_TRADES),
        profit_factor(FIXTURE_TRADES),
        max_drawdown(FIXTURE_TRADES),
    ):
        assert isinstance(value, Decimal)


def test_non_decimal_input_raises_instead_of_coercing() -> None:
    with pytest.raises(TypeError, match="must be Decimal"):
        win_rate([0.6])  # type: ignore[list-item]
    with pytest.raises(TypeError, match="must be Decimal"):
        expectancy([4])  # type: ignore[list-item]


def test_empty_vector_yields_null_never_default() -> None:
    assert win_rate(()) is None
    assert expectancy(()) is None
    assert profit_factor(()) is None
    assert max_drawdown(()) is None


def test_profit_factor_without_losers_is_null_not_infinite() -> None:
    assert profit_factor((Decimal(10), Decimal(5))) is None


def test_all_profit_curve_draws_down_zero() -> None:
    assert max_drawdown((Decimal(10), Decimal(5))) == Decimal(0)


def test_summarize_carries_definition_plus_sample_size() -> None:
    metrics = summarize_trades(FIXTURE_TRADES)
    assert [metric.name for metric in metrics] == [
        "win_rate",
        "expectancy",
        "profit_factor",
        "max_drawdown",
    ]
    values = [metric.value for metric in metrics]
    assert values == [
        EXPECTED_WIN_RATE,
        EXPECTED_EXPECTANCY,
        EXPECTED_PROFIT_FACTOR,
        EXPECTED_MAX_DRAWDOWN,
    ]
    for metric in metrics:
        assert metric.sample_size == 5
        assert "placeholder per D-6.1" in metric.definition
    wire = [metric.model_dump(mode="json") for metric in metrics]
    assert wire[0]["value"] == str(EXPECTED_WIN_RATE)
    assert wire[3]["value"] == str(EXPECTED_MAX_DRAWDOWN)
    empty = summarize_trades(())
    assert all(metric.value is None and metric.sample_size == 0 for metric in empty)


def test_no_float_in_metrics_source() -> None:
    # Scoped to this plan's module: persistence.py legitimately names `float`
    # in an isinstance guard that *rejects* JSON numbers from the wire form,
    # and assert_decimal_only globs directories (a file path would pass
    # vacuously), so the AST walk is inlined here for the single file.
    import ast

    tree = ast.parse(pathlib.Path("src/goldmasters/backtest/metrics.py").read_text())
    found = [
        node
        for node in ast.walk(tree)
        if (isinstance(node, ast.Constant) and isinstance(node.value, float))
        or (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float")
        or (isinstance(node, ast.Name) and node.id == "float")
    ]
    assert not found, "float in the metric path"
