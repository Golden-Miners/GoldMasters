"""Backtest record plus manifest persistence round-trip (06-02 Task 3).

Against the throwaway per-run migrated database (0003 tables from 06-01):
persist runner-produced BacktestRecord rows plus their dataset manifest row
and re-read them; decimal-as-string form survives, the manifest joins by
dataset_ref, and source hashes round-trip. Fails loudly when the cluster is
unavailable; never skips.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.goldmasters.backtest.persistence import (
    list_records_for_dataset,
    read_backtest_record,
    read_dataset_manifest,
    write_backtest_record,
    write_dataset_manifest,
)
from src.goldmasters.backtest.runner import run_backtest
from tests.unit.agent_fixtures import bars_from_closes, make_ctx
from tests.unit.test_backtest_record import _all_slots, _job

FIXTURE_UP = ["100", "102", "104", "106", "108", "110", "112", "114"]


def _assert_no_floats(node: Any, path: str) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            _assert_no_floats(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _assert_no_floats(value, f"{path}[{index}]")
    else:
        assert not isinstance(node, float), f"{path} stored as JSON number"


def _raw_column(engine: Engine, table: str, column: str, key: str, value: str) -> Any:
    with engine.connect() as connection:
        row = (
            connection.execute(
                text(f"SELECT {column} FROM {table} WHERE {key} = :value"),
                {"value": value},
            )
            .mappings()
            .first()
        )
    assert row is not None
    document = row[column]
    return json.loads(document) if isinstance(document, str) else document


def test_backtest_records_and_manifest_roundtrip(migrated_database: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    job = _job()
    run_id = f"run_{suffix}"
    dataset_ref = f"ds_{suffix}"
    job = job.__class__(
        run_id=run_id,
        dataset_ref=dataset_ref,
        dataset_hash="hash_integration",
        instrument_id=job.instrument_id,
        provider_symbol=job.provider_symbol,
        timeframe=job.timeframe,
        display_timezone=job.display_timezone,
        windows=job.windows,
        code_version=job.code_version,
        gate=job.gate,
        costs=job.costs,
    )
    output = run_backtest(
        bars=bars_from_closes(FIXTURE_UP),
        make_ctx=lambda index, bar: make_ctx(bar_count=index + 1),
        slots=_all_slots()[:3],
        job=job,
    )
    engine = create_engine(migrated_database)
    try:
        assert write_dataset_manifest(engine, output.manifest) == dataset_ref
        run_ids = [write_backtest_record(engine, record) for record in output.records]
        assert len(run_ids) == 3

        for written, run_key in zip(output.records, run_ids, strict=True):
            revived = read_backtest_record(engine, run_key)
            assert revived == written
            assert revived.dataset_ref == dataset_ref

        joined = list_records_for_dataset(engine, dataset_ref)
        assert len(joined) == 3
        assert [record.backtest_run_id for record in joined] == sorted(run_ids)

        manifest = read_dataset_manifest(engine, dataset_ref)
        assert manifest == output.manifest
        assert (
            manifest.source_hashes["bars_sha256"] == (output.manifest.source_hashes["bars_sha256"])
        )
        assert manifest.symbol_mapping == {"xauusd": "XAUUSD"}

        assumptions = _raw_column(
            engine, "backtest_run", "assumptions", "backtest_run_id", run_ids[0]
        )
        metrics = _raw_column(engine, "backtest_run", "metrics", "backtest_run_id", run_ids[0])
        _assert_no_floats(assumptions, "assumptions")
        _assert_no_floats(metrics, "metrics")
        assert assumptions["fill_model"].startswith("next-bar-open")
        assert "PLACEHOLDER" in assumptions["fill_model"]
        assert metrics[0]["value"] == "8"
    finally:
        engine.dispose()


def test_unknown_keys_raise(migrated_database: str) -> None:
    engine = create_engine(migrated_database)
    try:
        try:
            read_backtest_record(engine, "run_missing:strategy_x")
        except KeyError:
            pass
        else:
            raise AssertionError("unknown run id must raise KeyError")
        try:
            read_dataset_manifest(engine, "ds_missing")
        except KeyError:
            pass
        else:
            raise AssertionError("unknown dataset ref must raise KeyError")
    finally:
        engine.dispose()
