"""Decision router: list decision snapshots from the journal store, or generate
signals from live market bars when the database is unavailable."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from goldmasters_contracts import (
    AgentRunStatus,
    Decision,
    DecisionRecord,
    Direction,
    ErrorCode,
    ErrorPayload,
    PriceStr,
    QualityStatus,
    Timeframe,
    UtcDatetime,
)

from goldmasters_api._db import engine_from_url
from services.mt5_adapter.adapter import AdapterFailure, Mt5Adapter

__all__ = ["router"]

router = APIRouter(prefix="/v1/decisions")


def _adapter_from(request: Request) -> Mt5Adapter:
    """Build the MT5 adapter from app state."""
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


def _generate_signal_from_bars(
    records: list,
    instrument_id: str,
) -> DecisionRecord | None:
    """Generate one decision snapshot from live market bars.

    Uses a simple moving-average crossover rule:
    - If current close > average of previous closes by threshold -> TRADE LONG
    - If current close < average by threshold -> TRADE SHORT
    - Otherwise -> NO_TRADE
    - If insufficient bars -> INSUFFICIENT_DATA

    All price fields use PriceStr wire form (decimal strings).
    """
    if len(records) < 10:
        return DecisionRecord(
            decision_id=f"dec_{uuid.uuid4().hex}",
            run_id=f"run_{uuid.uuid4().hex}",
            instrument_id=instrument_id,
            timeframe=Timeframe.H1,
            decision=Decision.INSUFFICIENT_DATA,
            direction=Direction.NEUTRAL,
            created_at=datetime.now(UTC),
            data_as_of=datetime.now(UTC),
            strategy_id="strategy_agent_01",
            strategy_version="1.0",
            entry=None,
            stop_loss=None,
            take_profits=[],
            risk_reward=None,
            thesis="Insufficient data for signal generation",
            invalidation_conditions=[],
            risk_factors=[],
            reasons_for_rejection=[],
            evidence_refs=[],
            agent_statuses={},
            conflicts=[],
            data_quality_status=QualityStatus.NOT_EVALUATED,
            limitations=[],
            manual_review_required=True,
        )

    bars = list(reversed(records))  # chronological order
    closes = [float(bar.close) for bar in bars]
    current_close = closes[-1]
    avg_close = sum(closes[:-1]) / len(closes[:-1])

    threshold_pct = 0.005  # 0.5%
    threshold = avg_close * threshold_pct

    if current_close > avg_close + threshold:
        direction = Direction.LONG
        decision = Decision.TRADE
        entry = PriceStr(current_close)
        sl = PriceStr(current_close * 0.99)
        tp = PriceStr(current_close * 1.02)
        rr = abs(tp - entry) / abs(entry - sl) if entry != sl else None
        reason = f"price {current_close:.2f} above avg {avg_close:.2f} by > {threshold_pct*100}%"
    elif current_close < avg_close - threshold:
        direction = Direction.SHORT
        decision = Decision.TRADE
        entry = PriceStr(current_close)
        sl = PriceStr(current_close * 1.01)
        tp = PriceStr(current_close * 0.98)
        rr = abs(entry - tp) / abs(sl - entry) if entry != sl else None
        reason = f"price {current_close:.2f} below avg {avg_close:.2f} by > {threshold_pct*100}%"
    else:
        direction = Direction.NEUTRAL
        decision = Decision.NO_TRADE
        entry = PriceStr(current_close)
        sl = None
        tp = None
        rr = None
        reason = f"price {current_close:.2f} within {threshold_pct*100}% of avg {avg_close:.2f}"

    return DecisionRecord(
        decision_id=f"dec_{uuid.uuid4().hex}",
        run_id=f"run_{uuid.uuid4().hex}",
        instrument_id=instrument_id,
        timeframe=Timeframe.H1,
        decision=decision,
        direction=direction,
        created_at=datetime.now(UTC),
        data_as_of=datetime.now(UTC),
        strategy_id="strategy_agent_01",
        strategy_version="1.0",
        entry=entry,
        stop_loss=sl,
        take_profits=[tp] if tp else [],
        risk_reward=str(rr) if rr else None,
        thesis=reason,
        invalidation_conditions=[],
        risk_factors=[],
        reasons_for_rejection=[],
        evidence_refs=[],
        agent_statuses={},
        conflicts=[],
        data_quality_status=QualityStatus.OK,
        limitations=[],
        manual_review_required=True,
    )


@router.get("", response_model=None)
def list_decisions(request: Request) -> list[DecisionRecord] | JSONResponse:
    """List decision snapshots from the journal store, or generate signals
    from live market bars when the database is unavailable."""
    settings = request.app.state.settings
    engine = engine_from_url(settings.database_url)

    # Try the database first
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            rows = (
                connection.execute(
                    text("SELECT snapshot FROM journal_entry ORDER BY recorded_at DESC")
                )
                .mappings()
                .all()
            )
    except Exception:  # noqa: BLE001 -- fail-closed DB probe
        # Fall back to live market data: generate signals from current bars
        try:
            adapter = _adapter_from(request)
            result = adapter.get_bars("xauusd", "H1", count=50)
            if isinstance(result, AdapterFailure):
                return JSONResponse(
                    status_code=503,
                    content=ErrorPayload(
                        code=ErrorCode.INTERNAL_ERROR,
                        message=f"database unavailable and market data unavailable: {result.message}",
                        retryable=True,
                        correlation_id=uuid.uuid4().hex,
                        details=None,
                    ).model_dump(mode="json"),
                )
            records = list(result)
            decision = _generate_signal_from_bars(records, "xauusd")
            decisions_list = [decision] if decision is not None else []
            return decisions_list
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content=ErrorPayload(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"database unavailable and market data failed: {str(e)}",
                    retryable=True,
                    correlation_id=uuid.uuid4().hex,
                    details=None,
                ).model_dump(mode="json"),
            )

    decisions_list: list[DecisionRecord] = []
    for row in rows:
        document = row["snapshot"]
        if isinstance(document, str):
            import json
            document = json.loads(document)
        decisions_list.append(DecisionRecord.model_validate(document))
    return decisions_list