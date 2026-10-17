"""Read-only backtests router: list backtest records from persistence."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from goldmasters_contracts import BacktestRecord, ErrorCode, ErrorPayload
from sqlalchemy import text
from starlette import status

from goldmasters_api._db import engine_from_url

__all__ = ["router"]

router = APIRouter(prefix="/v1/backtests")

_SELECT = (
    "SELECT backtest_run_id, strategy_id, strategy_version, dataset_ref, "
    "dataset_hash, instrument, timeframe, start_at, end_at, timezone, "
    "data_quality, parameter_hash, assumptions, in_sample_start, in_sample_end, "
    "validation_start, validation_end, out_of_sample_start, out_of_sample_end, "
    "metrics, generated_at, code_version, status, errors "
    "FROM backtest_run ORDER BY backtest_run_id"
)


@router.get("", response_model=None)
def list_backtests(request: Request) -> list[BacktestRecord] | JSONResponse:
    """List all backtest records, oldest first."""
    settings = request.app.state.settings
    engine = engine_from_url(settings.database_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(text(_SELECT)).mappings().all()
    except Exception:  # noqa: BLE001 — fail-closed DB probe
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorPayload(
                code=ErrorCode.INTERNAL_ERROR,
                message="database unavailable",
                retryable=True,
                correlation_id=uuid.uuid4().hex,
                details=None,
            ).model_dump(mode="json"),
        )
    finally:
        engine.dispose()

    records: list[BacktestRecord] = []
    for row in rows:
        document: dict[str, Any] = {
            "backtest_run_id": row["backtest_run_id"],
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
        records.append(BacktestRecord.model_validate_json(json.dumps(document)))
    return records


def _json(node: Any) -> Any:
    if isinstance(node, str):
        return json.loads(node)
    return node


def _iso(moment: Any) -> str:
    if isinstance(moment, str):
        return moment
    from datetime import datetime

    if isinstance(moment, datetime):
        return moment.isoformat()
    raise TypeError(f"expected datetime or ISO string, got {type(moment).__name__}")


def _iso_or_none(moment: Any) -> str | None:
    if moment is None:
        return None
    return _iso(moment)
