"""Backtest record plus manifest persistence (Phase 6 Wave 2, Task 3).

Stores runner-produced ``BacktestRecord`` rows and their dataset-manifest row
against the 0003 tables with parameterized SQL only (T-06-01). Decimals travel
as strings end to end — stored JSONB must contain no JSON numbers (T-06-04).
Manifests join to records by ``dataset_ref``; ``backtest_run_id`` is the
per-strategy run key ``{run_id}:{strategy_id}``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from goldmasters_contracts import BacktestRecord
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.goldmasters.backtest.splits import DatasetManifest

__all__ = [
    "list_records_for_dataset",
    "read_backtest_record",
    "read_dataset_manifest",
    "write_backtest_record",
    "write_dataset_manifest",
]


def _assert_string_decimals(node: Any, path: str) -> None:
    if isinstance(node, Mapping):
        for key, value in node.items():
            _assert_string_decimals(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _assert_string_decimals(value, f"{path}[{index}]")
    elif isinstance(node, float):
        raise ValueError(f"{path} must be a decimal string, not a JSON number")


def write_backtest_record(engine: Engine, record: BacktestRecord) -> str:
    """INSERT one backtest record; return its run id."""
    if not isinstance(record, BacktestRecord):
        raise TypeError(f"record must be a BacktestRecord, got {type(record).__name__}")
    assumptions = record.assumptions.model_dump(mode="json")
    metrics = [metric.model_dump(mode="json") for metric in record.metrics]
    _assert_string_decimals(assumptions, "assumptions")
    _assert_string_decimals(metrics, "metrics")
    run_id: str = record.backtest_run_id
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO backtest_run "
                "(backtest_run_id, strategy_id, strategy_version, dataset_ref, "
                "dataset_hash, instrument, timeframe, start_at, end_at, timezone, "
                "data_quality, parameter_hash, assumptions, in_sample_start, "
                "in_sample_end, validation_start, validation_end, "
                "out_of_sample_start, out_of_sample_end, metrics, generated_at, "
                "code_version, status, errors) "
                "VALUES (:backtest_run_id, :strategy_id, :strategy_version, "
                ":dataset_ref, :dataset_hash, :instrument, :timeframe, :start_at, "
                ":end_at, :timezone, :data_quality, :parameter_hash, :assumptions, "
                ":in_sample_start, :in_sample_end, :validation_start, "
                ":validation_end, :out_of_sample_start, :out_of_sample_end, "
                ":metrics, :generated_at, :code_version, :status, :errors)"
            ),
            {
                "backtest_run_id": run_id,
                "strategy_id": record.strategy_id,
                "strategy_version": record.strategy_version,
                "dataset_ref": record.dataset_ref,
                "dataset_hash": record.dataset_hash,
                "instrument": record.instrument_id,
                "timeframe": record.timeframe.value,
                "start_at": record.start,
                "end_at": record.end,
                "timezone": record.timezone,
                "data_quality": record.data_quality.value,
                "parameter_hash": record.parameter_hash,
                "assumptions": json.dumps(assumptions),
                "in_sample_start": record.in_sample_start,
                "in_sample_end": record.in_sample_end,
                "validation_start": record.validation_start,
                "validation_end": record.validation_end,
                "out_of_sample_start": record.out_of_sample_start,
                "out_of_sample_end": record.out_of_sample_end,
                "metrics": json.dumps(metrics),
                "generated_at": record.generated_at,
                "code_version": record.code_version,
                "status": record.status.value,
                "errors": json.dumps(list(record.errors)),
            },
        )
    return run_id


def read_backtest_record(engine: Engine, backtest_run_id: str) -> BacktestRecord:
    """Re-read one record by run id, re-validated through the contract."""
    with engine.connect() as connection:
        row = (
            connection.execute(
                text(
                    "SELECT strategy_id, strategy_version, dataset_ref, "
                    "dataset_hash, instrument, timeframe, start_at, end_at, "
                    "timezone, data_quality, parameter_hash, assumptions, "
                    "in_sample_start, in_sample_end, validation_start, "
                    "validation_end, out_of_sample_start, out_of_sample_end, "
                    "metrics, generated_at, code_version, status, errors "
                    "FROM backtest_run WHERE backtest_run_id = :backtest_run_id"
                ),
                {"backtest_run_id": backtest_run_id},
            )
            .mappings()
            .first()
        )
    if row is None:
        raise KeyError(f"unknown backtest_run_id {backtest_run_id!r}")
    return _record_from_row(backtest_run_id, dict(row))


def list_records_for_dataset(engine: Engine, dataset_ref: str) -> list[BacktestRecord]:
    """Every record joined to one manifest by ``dataset_ref`` (D-6.3)."""
    with engine.connect() as connection:
        rows = (
            connection.execute(
                text(
                    "SELECT backtest_run_id, strategy_id, strategy_version, "
                    "dataset_ref, dataset_hash, instrument, timeframe, start_at, "
                    "end_at, timezone, data_quality, parameter_hash, assumptions, "
                    "in_sample_start, in_sample_end, validation_start, "
                    "validation_end, out_of_sample_start, out_of_sample_end, "
                    "metrics, generated_at, code_version, status, errors "
                    "FROM backtest_run WHERE dataset_ref = :dataset_ref "
                    "ORDER BY backtest_run_id"
                ),
                {"dataset_ref": dataset_ref},
            )
            .mappings()
            .all()
        )
    return [_record_from_row(str(row["backtest_run_id"]), dict(row)) for row in rows]


def _record_from_row(backtest_run_id: str, row: dict[str, Any]) -> BacktestRecord:
    document = {
        "backtest_run_id": backtest_run_id,
        "strategy_id": row["strategy_id"],
        "strategy_version": row["strategy_version"],
        "dataset_ref": row["dataset_ref"],
        "dataset_hash": row["dataset_hash"],
        "instrument_id": row["instrument"],
        "timeframe": row["timeframe"],
        "start": _iso(row["start_at"]),
        "end": _iso(row["end_at"]),
        "timezone": row["timezone"],
        "data_quality": row["data_quality"],
        "parameter_hash": row["parameter_hash"],
        "assumptions": _json(row["assumptions"]),
        "in_sample_start": _iso_or_none(row["in_sample_start"]),
        "in_sample_end": _iso_or_none(row["in_sample_end"]),
        "validation_start": _iso_or_none(row["validation_start"]),
        "validation_end": _iso_or_none(row["validation_end"]),
        "out_of_sample_start": _iso_or_none(row["out_of_sample_start"]),
        "out_of_sample_end": _iso_or_none(row["out_of_sample_end"]),
        "metrics": _json(row["metrics"]),
        "generated_at": _iso(row["generated_at"]),
        "code_version": row["code_version"],
        "status": row["status"],
        "errors": _json(row["errors"]),
    }
    # Strict contract: re-validate through JSON so str/enum/datetime/Decimal
    # coercion matches the write path (same pattern as journal store re-read).
    return BacktestRecord.model_validate_json(json.dumps(document))


def write_dataset_manifest(engine: Engine, manifest: DatasetManifest) -> str:
    """INSERT one manifest row keyed by ``dataset_ref``; return the ref."""
    if not isinstance(manifest, DatasetManifest):
        raise TypeError(f"manifest must be a DatasetManifest, got {type(manifest).__name__}")
    ref: str = manifest.dataset_ref
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO dataset_manifest "
                "(dataset_ref, range_start, range_end, symbol_mapping, "
                "quality_report, excluded_periods, source_hashes) "
                "VALUES (:dataset_ref, :range_start, :range_end, :symbol_mapping, "
                ":quality_report, :excluded_periods, :source_hashes)"
            ),
            {
                "dataset_ref": ref,
                "range_start": manifest.range_start,
                "range_end": manifest.range_end,
                "symbol_mapping": json.dumps(manifest.symbol_mapping),
                "quality_report": json.dumps(manifest.quality_report),
                "excluded_periods": json.dumps(
                    [dict(period) for period in manifest.excluded_periods]
                ),
                "source_hashes": json.dumps(manifest.source_hashes),
            },
        )
    return ref


def read_dataset_manifest(engine: Engine, dataset_ref: str) -> DatasetManifest:
    """Re-read one manifest row by dataset ref."""
    with engine.connect() as connection:
        row = (
            connection.execute(
                text(
                    "SELECT range_start, range_end, symbol_mapping, quality_report, "
                    "excluded_periods, source_hashes FROM dataset_manifest "
                    "WHERE dataset_ref = :dataset_ref"
                ),
                {"dataset_ref": dataset_ref},
            )
            .mappings()
            .first()
        )
    if row is None:
        raise KeyError(f"unknown dataset_ref {dataset_ref!r}")
    return DatasetManifest(
        dataset_ref=dataset_ref,
        range_start=row["range_start"],
        range_end=row["range_end"],
        symbol_mapping=dict(_json(row["symbol_mapping"])),
        quality_report={k: str(v) for k, v in _json(row["quality_report"]).items()},
        excluded_periods=tuple(
            {k: str(v) for k, v in period.items()} for period in _json(row["excluded_periods"])
        ),
        source_hashes={k: str(v) for k, v in _json(row["source_hashes"]).items()},
    )


def _iso(moment: Any) -> str:
    if isinstance(moment, str):
        return moment
    if isinstance(moment, datetime):
        return moment.isoformat()
    raise TypeError(f"expected datetime or ISO string, got {type(moment).__name__}")


def _iso_or_none(moment: Any) -> str | None:
    if moment is None:
        return None
    return _iso(moment)


def _json(node: Any) -> Any:
    if isinstance(node, str):
        return json.loads(node)
    return node
