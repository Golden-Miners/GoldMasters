"""Shared indicator math contract (03.1-01 Task 2): Decimal-only, deterministic.

Uses ``FIXTURE_``-labelled vectors for determinism: hand-computed exact
expectations, insufficient-data ``None`` branches, and Decimal-only
assertions. Indicator functions take only the bars they may read, so
full-series indicators cannot leak future bars into earlier indexes.
"""

from __future__ import annotations

import ast
import pathlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from goldmasters_contracts import MarketBar, QualityStatus, Timeframe, VolumeType


def _fixture_bar(moment: datetime, close: Decimal) -> MarketBar:
    return MarketBar(
        instrument_id="xauusd",
        provider_id="mt5",
        provider_symbol="XAUUSD",
        timeframe=Timeframe.H1,
        bar_open_time=moment,
        bar_close_time=moment + timedelta(hours=1),
        open=close,
        high=close + Decimal("1"),
        low=close - Decimal("1"),
        close=close,
        volume=Decimal(10),
        volume_type=VolumeType.TICK,
        retrieved_at=moment + timedelta(hours=1),
        source_timezone="UTC",
        quality_status=QualityStatus.OK,
    )


def _fixture_series(closes: list[str]) -> list[MarketBar]:
    moment = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
    return [
        _fixture_bar(moment + timedelta(hours=i), Decimal(price))
        for i, price in enumerate(closes)
    ]


#: Closes 100, 102, 101, 103 with high = close + 1, low = close - 1.
FIXTURE_ATR_EMA_BARS = _fixture_series(["100", "102", "101", "103"])

#: Closes 100, 102, 101 (changes +2, -1).
FIXTURE_GAIN_LOSS_BARS = _fixture_series(["100", "102", "101"])


def test_average_true_range_is_exact_decimal_mean() -> None:
    from src.goldmasters.domain.indicators import average_true_range

    # True ranges: bar1 max(2, 3, 1) = 3; bar2 max(2, 0, 2) = 2;
    # bar3 max(2, 3, 1) = 3. Last two average (2 + 3) / 2 = 2.5.
    result = average_true_range(FIXTURE_ATR_EMA_BARS, period=2)
    assert result == Decimal("2.5")
    assert isinstance(result, Decimal)


def test_average_true_range_none_when_short() -> None:
    from src.goldmasters.domain.indicators import average_true_range

    assert average_true_range(FIXTURE_ATR_EMA_BARS, period=4) is None


def test_ema_close_is_exact_decimal() -> None:
    from src.goldmasters.domain.indicators import ema_close

    # Seed (100 + 102 + 101) / 3 = 101; k = 2 / 4 = 0.5;
    # 103 * 0.5 + 101 * 0.5 = 102.
    result = ema_close(FIXTURE_ATR_EMA_BARS, period=3)
    assert result == Decimal("102")
    assert isinstance(result, Decimal)


def test_ema_close_none_when_short() -> None:
    from src.goldmasters.domain.indicators import ema_close

    assert ema_close(FIXTURE_ATR_EMA_BARS, period=5) is None


def test_average_gain_and_loss_are_exact_decimals() -> None:
    from src.goldmasters.domain.indicators import average_gain, average_loss

    # Changes +2, -1: gain (2 + 0) / 2 = 1; loss (0 + 1) / 2 = 0.5.
    gain = average_gain(FIXTURE_GAIN_LOSS_BARS, period=2)
    loss = average_loss(FIXTURE_GAIN_LOSS_BARS, period=2)
    assert gain == Decimal("1")
    assert loss == Decimal("0.5")
    assert isinstance(gain, Decimal)
    assert isinstance(loss, Decimal)


def test_average_gain_loss_none_when_short() -> None:
    from src.goldmasters.domain.indicators import average_gain, average_loss

    assert average_gain(FIXTURE_GAIN_LOSS_BARS, period=3) is None
    assert average_loss(FIXTURE_GAIN_LOSS_BARS, period=3) is None


def test_indicators_are_deterministic() -> None:
    from src.goldmasters.domain.indicators import (
        average_gain,
        average_loss,
        average_true_range,
        ema_close,
    )

    assert average_true_range(FIXTURE_ATR_EMA_BARS, period=2) == average_true_range(
        FIXTURE_ATR_EMA_BARS, period=2
    )
    assert ema_close(FIXTURE_ATR_EMA_BARS, period=3) == ema_close(
        FIXTURE_ATR_EMA_BARS, period=3
    )
    assert average_gain(FIXTURE_GAIN_LOSS_BARS, period=2) == average_gain(
        FIXTURE_GAIN_LOSS_BARS, period=2
    )
    assert average_loss(FIXTURE_GAIN_LOSS_BARS, period=2) == average_loss(
        FIXTURE_GAIN_LOSS_BARS, period=2
    )


def test_indicator_periods_reject_non_positive() -> None:
    from src.goldmasters.domain.indicators import (
        average_gain,
        average_loss,
        average_true_range,
        ema_close,
    )

    for function in (average_true_range, ema_close, average_gain, average_loss):
        for bad in (0, -1, True):
            with pytest.raises(ValueError, match="positive int"):
                function(FIXTURE_ATR_EMA_BARS, period=bad)  # type: ignore[arg-type]


def test_indicators_reject_malformed_bars() -> None:
    from src.goldmasters.domain.indicators import average_true_range

    with pytest.raises(ValueError, match="at least one closed bar"):
        average_true_range([], period=2)
    with pytest.raises(TypeError, match="must be MarketBar"):
        average_true_range(["not-a-bar"], period=2)  # type: ignore[list-item]


def test_indicators_module_has_no_float_path() -> None:
    """Decimal-only rule path: no float literal or float() call in indicators.py."""
    path = (
        pathlib.Path(__file__).resolve().parents[2]
        / "src"
        / "goldmasters"
        / "domain"
        / "indicators.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    floats = [node for node in ast.walk(tree) if isinstance(node, ast.Constant)]
    assert not [node for node in floats if isinstance(node.value, float)]
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "float"
    ]
    assert not calls
