"""Read-only market endpoints over the MT5 adapter (Phase 2; D-55).

``GET /v1/market/bars`` and ``GET /v1/market/quote`` return contract-valid
``MarketBar``/``MarketQuote`` JSON. No POST, no parameters beyond
instrument/timeframe/count, loopback-only unchanged (D-34). A retrieval that
is stale, disconnected, missing, unsupported, or malformed maps to the
sanitized C-09 error object (retryable only for transient reads, per
``RETRYABLE_CODES``); last-known bars are never served as fresh (D-50).
"""

from __future__ import annotations

import uuid
from typing import cast

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from goldmasters_contracts import (
    ErrorCode,
    ErrorPayload,
    MarketBar,
    MarketQuote,
    QualityStatus,
)
from starlette import status

from goldmasters_api.middleware import current_correlation_id
from services.mt5_adapter.adapter import AdapterFailure, Mt5Adapter, ProviderKind
from services.mt5_adapter.validation import verdict_for_bars

__all__ = ["router"]

router = APIRouter(prefix="/v1/market")

#: Failure codes that read as a bad request rather than a provider outage.
_BAD_REQUEST_CODES: frozenset[ErrorCode] = frozenset(
    {ErrorCode.UNSUPPORTED_INSTRUMENT, ErrorCode.UNSUPPORTED_TIMEFRAME}
)

#: Batch verdicts that fail a served batch, with their C-09 codes.
_VERDICT_CODES: dict[QualityStatus, ErrorCode] = {
    QualityStatus.STALE: ErrorCode.CONFIG_INVALID,
    QualityStatus.MALFORMED: ErrorCode.CONFIG_INVALID,
    QualityStatus.DISCONNECTED: ErrorCode.INTERNAL_ERROR,
    QualityStatus.MISSING_HISTORY: ErrorCode.CONFIG_INVALID,
    QualityStatus.UNSUPPORTED: ErrorCode.CONFIG_INVALID,
}


def _adapter_from(request: Request) -> Mt5Adapter:
    """Build the request adapter from app state (cheap, stateless).

    Uses the persistent TerminalManager and SymbolResolver stored on app
    state — individual reads never call initialize()/shutdown().
    """
    settings = request.app.state.settings
    return Mt5Adapter(
        request.app.state.mt5_terminal_manager,
        request.app.state.mt5_symbol_resolver,
        server_timezone=settings.mt5_server_timezone,
        retry_attempts=settings.mt5_retry_attempts,
        retry_delay_ms=settings.mt5_retry_delay_ms,
        bars_count=settings.mt5_bars_count,
        bar_stale_closed_bars=settings.bar_stale_closed_bars,
        bar_stale_grace_seconds=settings.bar_stale_grace_seconds,
        quote_overlap_seconds=settings.quote_stale_seconds_overlap,
        quote_major_seconds=settings.quote_stale_seconds_major,
        quote_asia_seconds=settings.quote_stale_seconds_asia,
        quote_offhours_seconds=settings.quote_stale_seconds_offhours,
        session_overlap_utc=settings.session_overlap_utc,
        session_major_utc=settings.session_major_utc,
        session_asia_utc=settings.session_asia_utc,
        weekend_close_utc=settings.weekend_close_utc,
        daily_break_utc=settings.daily_break_utc,
    )


def _failure_response(failure: AdapterFailure) -> JSONResponse:
    """Render an adapter failure as a sanitized C-09 body with a mapped status."""
    if failure.code in _BAD_REQUEST_CODES:
        http_status = status.HTTP_400_BAD_REQUEST
    elif failure.code.retryable:
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        http_status = status.HTTP_502_BAD_GATEWAY
    body = ErrorPayload(
        code=failure.code,
        message=failure.message,
        retryable=failure.code.retryable,
        correlation_id=current_correlation_id() or uuid.uuid4().hex,
        details=None,
    )
    return JSONResponse(status_code=http_status, content=body.model_dump(mode="json"))


def _verdict_failure(bars: tuple[MarketBar, ...]) -> AdapterFailure | None:
    """Fail a served batch whose worst condition is stale or malformed."""
    verdict = verdict_for_bars(bars)
    if verdict is None:
        return None
    code = _VERDICT_CODES.get(verdict, ErrorCode.CONFIG_INVALID)
    return AdapterFailure(
        code, cast(ProviderKind, verdict.value), f"retrieval is {verdict.value}, not servable"
    )


@router.get("/bars", response_model=None)
def read_bars(
    request: Request,
    instrument_id: str = "xauusd",
    timeframe: str = "H1",
    count: int | None = None,
) -> list[MarketBar] | JSONResponse:
    """Closed bars for an explicitly selected instrument/timeframe."""
    result = _adapter_from(request).get_bars(instrument_id, timeframe, count=count)
    if isinstance(result, AdapterFailure):
        return _failure_response(result)
    verdict = _verdict_failure(result)
    if verdict is not None:
        return _failure_response(verdict)
    return list(result)


@router.get("/quote", response_model=None)
def read_quote(request: Request, instrument_id: str = "xauusd") -> MarketQuote | JSONResponse:
    """Latest bid/ask tick for an explicitly selected instrument."""
    result = _adapter_from(request).get_latest_quote(instrument_id)
    if isinstance(result, AdapterFailure):
        return _failure_response(result)
    if result.quality_status != QualityStatus.OK:
        code = _VERDICT_CODES.get(result.quality_status, ErrorCode.CONFIG_INVALID)
        return _failure_response(
            AdapterFailure(
                code,
                cast(ProviderKind, result.quality_status.value),
                f"quote is {result.quality_status.value}",
            )
        )
    return result
