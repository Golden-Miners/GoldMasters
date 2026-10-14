"""Local on-disk tracing with no collector (D-30).

Spans append to the repo-local file from `Settings.trace_file_path` via a
`BatchSpanProcessor` + file-backed exporter. Each request span carries the
request's `correlation_id` as an attribute; spans carry request metadata
only — never payload dumps or header bags.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

__all__ = ["configure_tracing", "shutdown_tracing", "start_request_span"]

_provider: TracerProvider | None = None
_stream: Any = None
_current_path: str | None = None


def configure_tracing(trace_file: str) -> None:
    """Install the file-backed tracer provider (append, never truncate).

    Reconfiguring to a different path shuts the previous provider down
    first, so tests and restarts each land spans in the intended file.
    """
    global _provider, _stream, _current_path
    if _provider is not None:
        if _current_path == trace_file:
            return
        shutdown_tracing()
    path = Path(trace_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    _stream = path.open("a", encoding="utf-8")
    provider = TracerProvider(resource=Resource.create({"service.name": "goldmasters-api"}))
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter(out=_stream)))
    # Process-wide singleton: a second call logs a warning and keeps the
    # first provider. Spans here go through `_provider` directly, so every
    # configured file still receives its spans.
    trace.set_tracer_provider(provider)
    _provider = provider
    _current_path = trace_file


def start_request_span(operation: str, correlation_id: str | None) -> Any:
    """Start a request span carrying the correlation ID as an attribute."""
    tracer = (
        _provider.get_tracer("goldmasters_api")
        if _provider is not None
        else trace.get_tracer("goldmasters_api")
    )
    span = tracer.start_span(operation)
    if correlation_id is not None:
        span.set_attribute("correlation_id", correlation_id)
    return span


def shutdown_tracing() -> None:
    """Flush spans and close the trace file."""
    global _provider, _stream, _current_path
    if _provider is not None:
        _provider.force_flush()
        _provider.shutdown()
        _provider = None
    if _stream is not None:
        _stream.close()
        _stream = None
    _current_path = None
