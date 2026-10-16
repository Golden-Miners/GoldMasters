"""Read-only journal router: list journal entries from the journal store."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from goldmasters_contracts import DecisionRecord, ErrorCode, ErrorPayload, JournalEntry
from sqlalchemy import text
from starlette import status

from goldmasters_api._db import engine_from_url

__all__ = ["router"]

router = APIRouter(prefix="/v1/journal")


@router.get("", response_model=None)
def list_journal(request: Request) -> list[JournalEntry] | JSONResponse:
    """List all journal entries, newest first."""
    settings = request.app.state.settings
    engine = engine_from_url(settings.database_url)
    try:
        with engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        "SELECT journal_id, decision_id, run_id, recorded_at, snapshot "
                        "FROM journal_entry ORDER BY recorded_at DESC"
                    )
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

    entries: list[JournalEntry] = []
    for row in rows:
        snapshot = row["snapshot"]
        if isinstance(snapshot, str):
            snapshot = json.loads(snapshot)
        decision = DecisionRecord.model_validate(snapshot)
        entries.append(
            JournalEntry(
                journal_id=row["journal_id"],
                decision_id=row["decision_id"],
                run_id=row["run_id"],
                recorded_at=row["recorded_at"],
                snapshot=decision,
            )
        )
    return entries
