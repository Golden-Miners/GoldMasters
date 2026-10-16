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
        document: dict[str, Any] = dict(row)
        document["assumptions"] = _json(document["assumptions"])
        document["metrics"] = _json(document["metrics"])
        document["errors"] = _json(document["errors"])
        document["start"] = _iso(document["start_at"])
        document["end"] = _iso(document["end_at"])
        document["in_sample_start"] = _iso_or_none(document["in_sample_start"])
        document["in_sample_end"] = _iso_or_none(document["in_sample_end"])
        document["validation_start"] = _iso_or_none(document["validation_start"])
        document["validation_end"] = _iso_or_none(document["validation_end"])
        document["out_of_sample_start"] = _iso_or_none(document["out_of_sample_start"])
        document["out_of_sample_end"] = _iso_or_none(document["out_of_sample_end"])
        document["generated_at"] = _iso(document["generated_at"])
        document["instrument_id"] = document.pop("instrument")
        records.append(BacktestRecord.model_validate(document))
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
