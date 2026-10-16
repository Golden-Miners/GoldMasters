"""Backtest package: deterministic loop over the live path (Phase 6 Wave 2)."""

from __future__ import annotations

from src.goldmasters.backtest.fills import (
    FILL_MODEL,
    FillCosts,
    apply_costs,
    fill_at_next_open,
    placeholder_costs,
    require_confirmed,
    to_assumptions,
)
from src.goldmasters.backtest.persistence import (
    list_records_for_dataset,
    read_backtest_record,
    read_dataset_manifest,
    write_backtest_record,
    write_dataset_manifest,
)
from src.goldmasters.backtest.runner import (
    PINNED_STRATEGIES,
    PINNED_STRATEGY_VERSION,
    BacktestJob,
    GatePolicy,
    RunOutput,
    StrategySlot,
    hash_params,
    run_backtest,
)
from src.goldmasters.backtest.splits import (
    DatasetManifest,
    SplitEnforcement,
    SplitName,
    SplitWindows,
    bar_times,
    build_manifest,
    classify_bar,
    enforce_splits,
    timeframe_step,
)

__all__ = [
    "BacktestJob",
    "DatasetManifest",
    "FILL_MODEL",
    "FillCosts",
    "GatePolicy",
    "PINNED_STRATEGIES",
    "PINNED_STRATEGY_VERSION",
    "RunOutput",
    "SplitEnforcement",
    "SplitName",
    "SplitWindows",
    "StrategySlot",
    "apply_costs",
    "bar_times",
    "build_manifest",
    "classify_bar",
    "enforce_splits",
    "fill_at_next_open",
    "hash_params",
    "list_records_for_dataset",
    "placeholder_costs",
    "read_backtest_record",
    "read_dataset_manifest",
    "require_confirmed",
    "run_backtest",
    "timeframe_step",
    "to_assumptions",
    "write_backtest_record",
    "write_dataset_manifest",
]
