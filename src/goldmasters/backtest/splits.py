"""Split enforcement plus dataset-manifest provenance (D-6.3, criterion 3).

Boundaries are UTC datetimes; the display timezone is the record's
``IanaTimezone`` label only and never affects classification (DST-safe by
construction — a boundary crossing a DST switch classifies by UTC instant).
Every bar is classified into in-sample, validation, or out-of-sample from the
``BacktestRecord`` windows; a bar whose close falls outside every window is
rejected, never silently dropped. Missing bars go to the quality report plus
the excluded-period list — synthesis is rejected (R-01, T-06-06).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

from goldmasters_contracts import MarketBar, Timeframe

__all__ = [
    "DatasetManifest",
    "SplitEnforcement",
    "SplitName",
    "SplitWindows",
    "build_manifest",
    "classify_bar",
    "enforce_splits",
    "timeframe_step",
]

#: Window a bar close falls into; ``None`` from ``classify_bar`` means rejected.
SplitName = Literal["in_sample", "validation", "out_of_sample"]


@dataclass(frozen=True)
class SplitWindows:
    """IS/VS/OOS boundaries as UTC datetimes plus a display-only IANA label."""

    in_sample_start: datetime
    in_sample_end: datetime
    validation_start: datetime
    validation_end: datetime
    out_of_sample_start: datetime
    out_of_sample_end: datetime
    display_timezone: str = "UTC"

    def __post_init__(self) -> None:
        for name in (
            "in_sample_start",
            "in_sample_end",
            "validation_start",
            "validation_end",
            "out_of_sample_start",
            "out_of_sample_end",
        ):
            moment = getattr(self, name)
            if not isinstance(moment, datetime) or moment.tzinfo is None:
                raise ValueError(f"{name} must be a timezone-aware datetime")
        pairs = (
            ("in_sample_start", "in_sample_end"),
            ("validation_start", "validation_end"),
            ("out_of_sample_start", "out_of_sample_end"),
        )
        for start_name, end_name in pairs:
            if getattr(self, start_name) >= getattr(self, end_name):
                raise ValueError(f"{start_name} must precede {end_name}")


@dataclass(frozen=True)
class SplitEnforcement:
    """Outcome of gating one bar vector through ``SplitWindows``."""

    in_window: tuple[MarketBar, ...]
    out_of_window: tuple[MarketBar, ...]
    missing_bars: tuple[dict[str, str], ...]
    duplicates: tuple[MarketBar, ...]
    excluded_periods: tuple[dict[str, str], ...]
    quality_flags: tuple[str, ...]


@dataclass(frozen=True)
class DatasetManifest:
    """Provenance row for one backtest dataset (D-6.3).

    Bars are referenced by hash only and never stored here; the manifest joins
    to ``BacktestRecord`` rows by ``dataset_ref``. A silently dropped source
    fails the persistence test — every input bar is either in-window,
    rejected into ``quality_report``, or reported in ``excluded_periods``.
    """

    dataset_ref: str
    range_start: datetime
    range_end: datetime
    symbol_mapping: dict[str, str] = field(default_factory=dict)
    quality_report: dict[str, str] = field(default_factory=dict)
    excluded_periods: tuple[dict[str, str], ...] = ()
    source_hashes: dict[str, str] = field(default_factory=dict)


def timeframe_step(timeframe: Timeframe) -> timedelta:
    """Expected bar-to-bar step for gap detection; MN1 refuses (calendar months vary)."""
    token = timeframe.value
    if token.startswith("M") and token[1:].isdigit() and token != "MN1":
        return timedelta(minutes=int(token[1:]))
    if token.startswith("H") and token[1:].isdigit():
        return timedelta(hours=int(token[1:]))
    if token == "D1":
        return timedelta(days=1)
    if token == "W1":
        return timedelta(weeks=1)
    raise ValueError(f"gap detection unsupported for timeframe {token!r}")


def classify_bar(moment: datetime, windows: SplitWindows) -> SplitName | None:
    """Classify one UTC instant; ``None`` means out-of-window (rejected)."""
    if moment.tzinfo is None:
        raise ValueError("classify_bar requires a timezone-aware instant")
    if windows.in_sample_start <= moment < windows.in_sample_end:
        return "in_sample"
    if windows.validation_start <= moment < windows.validation_end:
        return "validation"
    if windows.out_of_sample_start <= moment < windows.out_of_sample_end:
        return "out_of_sample"
    return None


def enforce_splits(
    bars: Sequence[MarketBar],
    windows: SplitWindows,
    timeframe: Timeframe,
) -> SplitEnforcement:
    """Gate bars through the windows; report gaps, never synthesise them."""
    step = timeframe_step(timeframe)
    ordered = list(bars)
    seen: set[str] = set()
    unique: list[MarketBar] = []
    duplicates: list[MarketBar] = []
    for bar in ordered:
        key = bar.bar_open_time.isoformat()
        if key in seen:
            duplicates.append(bar)
            continue
        seen.add(key)
        unique.append(bar)
    for first, second in zip(unique, unique[1:], strict=False):
        if second.bar_open_time <= first.bar_open_time:
            raise ValueError("bars must arrive in strictly increasing open-time order")
    in_window: list[MarketBar] = []
    out_of_window: list[MarketBar] = []
    for bar in unique:
        if classify_bar(bar.bar_close_time, windows) is None:
            out_of_window.append(bar)
        else:
            in_window.append(bar)
    missing: list[dict[str, str]] = []
    excluded: list[dict[str, str]] = []
    for first, second in zip(unique, unique[1:], strict=False):
        delta = second.bar_open_time - first.bar_open_time
        if delta > step:
            skipped = max(round(delta / step) - 1, 1)
            missing.append(
                {
                    "gap_start": first.bar_close_time.isoformat(),
                    "gap_end": second.bar_open_time.isoformat(),
                    "bars_skipped": str(skipped),
                }
            )
            excluded.append(
                {
                    "start": first.bar_close_time.isoformat(),
                    "end": second.bar_open_time.isoformat(),
                    "reason": f"missing data: {skipped} {timeframe.value} bar(s) absent, never synthesised",
                }
            )
    flags: list[str] = []
    if missing:
        flags.append(f"gap: {len(missing)} missing-data period(s) reported, none filled")
    if duplicates:
        flags.append(f"duplicate: {len(duplicates)} repeated open-time bar(s) excluded")
    if out_of_window:
        flags.append(f"out-of-window: {len(out_of_window)} bar(s) rejected")
    return SplitEnforcement(
        in_window=tuple(in_window),
        out_of_window=tuple(out_of_window),
        missing_bars=tuple(missing),
        duplicates=tuple(duplicates),
        excluded_periods=tuple(excluded),
        quality_flags=tuple(flags),
    )


def _canonical_bar(bar: MarketBar) -> str:
    document = {
        "instrument_id": bar.instrument_id,
        "provider_id": str(bar.provider_id),
        "provider_symbol": bar.provider_symbol,
        "timeframe": str(bar.timeframe),
        "bar_open_time": bar.bar_open_time.isoformat(),
        "bar_close_time": bar.bar_close_time.isoformat(),
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
        "volume": str(bar.volume),
    }
    return json.dumps(document, sort_keys=True)


def build_manifest(
    *,
    dataset_ref: str,
    bars: Sequence[MarketBar],
    symbol_mapping: dict[str, str],
    enforcement: SplitEnforcement,
    producer: str = "goldmasters.backtest",
) -> DatasetManifest:
    """Hash the input bars and bind the split report to one manifest row."""
    ordered = list(bars)
    if not ordered:
        raise ValueError("cannot build a manifest for an empty bar vector")
    digest = hashlib.sha256()
    for bar in ordered:
        digest.update(_canonical_bar(bar).encode("utf-8"))
    return DatasetManifest(
        dataset_ref=dataset_ref,
        range_start=ordered[0].bar_open_time,
        range_end=ordered[-1].bar_close_time,
        symbol_mapping=dict(symbol_mapping),
        quality_report={
            "bars_total": str(len(ordered)),
            "bars_in_window": str(len(enforcement.in_window)),
            "bars_out_of_window": str(len(enforcement.out_of_window)),
            "missing_periods": str(len(enforcement.missing_bars)),
            "duplicates": str(len(enforcement.duplicates)),
            "quality_flags": "; ".join(enforcement.quality_flags) or "clean",
        },
        excluded_periods=enforcement.excluded_periods,
        source_hashes={"bars_sha256": digest.hexdigest(), "producer": producer},
    )
