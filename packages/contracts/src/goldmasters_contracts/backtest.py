"""Backtest record contract (Schema.md §9 lines 209-220).

Metrics are calculated in deterministic code; the record carries them with
their definitions and sample size, plus the full assumption set a report
must show. Any report without its run and dataset reference is not
representable here — both are required fields.
"""

from __future__ import annotations

from pydantic import Field

from goldmasters_contracts._base import (
    ContractModel,
    IanaTimezone,
    PriceStr,
    UtcDatetime,
)
from goldmasters_contracts.enums import EvidenceStatus, Timeframe

__all__ = ["BacktestAssumptions", "BacktestMetric", "BacktestRecord"]


class BacktestAssumptions(ContractModel):
    """Spread/commission/slippage/fill assumptions a report must show."""

    spread: PriceStr
    commission: PriceStr
    slippage: PriceStr
    fill_model: str


class BacktestMetric(ContractModel):
    """One metric with its definition and sample size."""

    name: str
    definition: str
    value: PriceStr | None = None
    sample_size: int = Field(ge=0)


class BacktestRecord(ContractModel):
    """Schema.md §9 backtest record, field for field."""

    backtest_run_id: str
    strategy_id: str
    strategy_version: str
    dataset_ref: str
    dataset_hash: str
    instrument_id: str
    timeframe: Timeframe
    start: UtcDatetime
    end: UtcDatetime
    timezone: IanaTimezone
    data_quality: EvidenceStatus
    parameter_hash: str
    assumptions: BacktestAssumptions
    in_sample_start: UtcDatetime | None = None
    in_sample_end: UtcDatetime | None = None
    validation_start: UtcDatetime | None = None
    validation_end: UtcDatetime | None = None
    out_of_sample_start: UtcDatetime | None = None
    out_of_sample_end: UtcDatetime | None = None
    metrics: list[BacktestMetric] = Field(default_factory=list)
    generated_at: UtcDatetime
    code_version: str
    status: EvidenceStatus
    errors: list[str] = Field(default_factory=list)
