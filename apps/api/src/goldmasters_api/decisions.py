"""Read-only decisions router: list decision snapshots from the journal store."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from goldmasters_contracts import DecisionRecord, ErrorCode, ErrorPayload
from sqlalchemy import text
from starlette import status

from goldmasters_api._db import engine_from_url

__all__ = ["router"]

router = APIRouter(prefix="/v1/decisions")


@router.get("", response_model=None)
def list_decisions(request: Request) -> list[DecisionRecord] | JSONResponse:
    """List all decision snapshots from the journal store, newest first."""
    settings = request.app.state.settings
    engine = engine_from_url(settings.database_url)
    try:
        with engine.connect() as connection:
            rows = (
                connection.execute(
                    text("SELECT snapshot FROM journal_entry ORDER BY recorded_at DESC")
                )
                .mappings()
                .all()
            )
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

    decisions: list[DecisionRecord] = []
    for row in rows:
        document = row["snapshot"]
        if isinstance(document, str):
            document = json.loads(document)
        decisions.append(DecisionRecord.model_validate(document))
    return decisions
