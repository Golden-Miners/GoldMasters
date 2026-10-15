"""Shared builders for the strategy-agent per-agent test lists (3.2-3.5).

Test-only support: FIXTURE_-labelled closed-bar vectors, eligible-context
builders, and the Decimal-only source scan. No backtest code, no historical
metrics — vector fixtures only (03.1-RESEARCH.md per-agent test list).
"""

from __future__ import annotations

import ast
import pathlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from goldmasters_contracts import (
    MarketBar,
    QualityStatus,
    Timeframe,
    TrendRegime,
    VolumeType,
)

from src.goldmasters.strategies.base import MarketContext

T0 = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)


def make_bar(
    *,
    close: str,
    high: str | None = None,
    low: str | None = None,
    open_: str | None = None,
    index: int = 0,
    volume: str = "10",
) -> MarketBar:
    """One closed H1 bar; wicks default to one point beyond body extremes."""
    close_d = Decimal(close)
    open_d = Decimal(open_) if open_ is not None else close_d
    high_d = Decimal(high) if high is not None else max(open_d, close_d) + Decimal(1)
    low_d = Decimal(low) if low is not None else min(open_d, close_d) - Decimal(1)
    moment = T0 + timedelta(hours=index)
    return MarketBar(
        instrument_id="xauusd",
        provider_id="mt5",
        provider_symbol="XAUUSD",
        timeframe=Timeframe.H1,
        bar_open_time=moment,
        bar_close_time=moment + timedelta(hours=1),
        open=open_d,
        high=high_d,
        low=low_d,
        close=close_d,
        volume=Decimal(volume),
        volume_type=VolumeType.TICK,
        retrieved_at=moment + timedelta(hours=1),
        source_timezone="UTC",
        quality_status=QualityStatus.OK,
    )


def bars_from_closes(closes: list[str]) -> list[MarketBar]:
    """Gap-free ramp: each open equals the previous close (no-gap baseline)."""
    bars: list[MarketBar] = []
    previous: str | None = None
    for index, close in enumerate(closes):
        bars.append(make_bar(close=close, open_=previous or close, index=index))
        previous = close
    return bars


def make_ctx(
    *,
    regime: TrendRegime = TrendRegime.UPTREND,
    tick_size: str | None = "0.01",
    instrument_id: str = "xauusd",
    timeframe: Timeframe = Timeframe.H1,
    bar_count: int = 12,
) -> MarketContext:
    """Eligible-context default; overrides drive the NOT_APPLICABLE branches."""
    return MarketContext(
        instrument_id=instrument_id,
        provider_id="mt5",
        timeframe=timeframe,
        regime=regime,
        quality_status=QualityStatus.OK,
        quality_flags=[],
        volume_type=VolumeType.TICK,
        tick_size=tick_size,
        contract_size=None,
        bar_count=bar_count,
        now_utc=datetime(2026, 1, 6, 12, 0, tzinfo=UTC),
    )


def assert_decimal_only(package_dir: pathlib.Path) -> None:
    """No float in the rule path: rejects float literals and float() calls."""
    for source_file in sorted(package_dir.glob("*.py")):
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                raise AssertionError(f"float literal in {source_file.name}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "float", f"float() call in {source_file.name}"
            if isinstance(node, ast.Name):
                assert node.id != "float", f"float name in {source_file.name}"
