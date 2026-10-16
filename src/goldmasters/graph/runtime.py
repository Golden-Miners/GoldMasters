"""Ollama runtime binding: endpoint, discovery, health, run record (D-4.1).

Discovery only — no model name, capability, hardware, or context window is
ever assumed (T0004 open). Health is reachable plus the operator-configured
model present; a model absent after bounded retries fails closed to
``INSUFFICIENT_DATA`` — no silent fallback. All calls are ``async``; the
httpx timeout from settings is defense-in-depth under ``TimeoutPolicy``.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import httpx
from goldmasters_api.settings import Settings
from goldmasters_contracts import ContractModel, ErrorCode, ErrorPayload
from ollama import AsyncClient, ChatResponse
from pydantic import ValidationError

__all__ = [
    "DiscoveredModel",
    "Discovery",
    "ModelHealth",
    "build_client",
    "check_health",
    "discover",
    "generate",
    "resolve_model",
    "run_model_record",
]

#: Transient transport only — parity with the graph RetryPolicy in
#: ``builder._retry_policy`` plus refused/reset connections (``ConnectionError``
#: is what a refused loopback endpoint raises outside httpx wrapping).
#: Validation and policy outcomes never retry.
TRANSIENT_ERRORS = (httpx.TimeoutException, httpx.ConnectError, ConnectionError)


@dataclasses.dataclass(frozen=True)
class DiscoveredModel:
    """One server-reported model: measured id plus digest, nothing inferred.

    Fields stay ``None`` when the server leaves them blank — absence is
    recorded, never filled in.
    """

    model: str | None
    digest: str | None


@dataclasses.dataclass(frozen=True)
class Discovery:
    """Run-start ``list()`` outcome: reachability plus measured inventory."""

    reachable: bool
    models: tuple[DiscoveredModel, ...]
    attempts: int
    error: ErrorPayload | None


@dataclasses.dataclass(frozen=True)
class ModelHealth:
    """Reachable plus the operator-configured model present (criterion 5)."""

    expected: str | None
    present: bool
    reachable: bool


def _sanitized_error(
    node: str, run_id: str, exc: BaseException, *, code: ErrorCode
) -> ErrorPayload:
    """Schema §10 error: stable code, no secrets/paths/traces, run-bound id."""
    return ErrorPayload(
        code=code,
        message=f"{type(exc).__name__} in graph node {node}",
        retryable=code == ErrorCode.INTERNAL_ERROR,
        correlation_id=run_id,
        details=None,
    )


def build_client(settings: Settings) -> AsyncClient:
    """Official client on the declared endpoint; httpx timeout backs TimeoutPolicy."""
    return AsyncClient(host=settings.ollama_host, timeout=settings.graph_node_timeout_seconds)


def _attempts(settings: Settings) -> int:
    """Total tries: first attempt plus the locked retry budget (D-4.2)."""
    return 1 + settings.graph_node_max_retries


async def discover(
    settings: Settings, client: AsyncClient, *, run_id: str, node: str
) -> Discovery:
    """``list()`` at run start with bounded transient-only retries.

    Never assumes a name, capability, or context window — the inventory is
    whatever the server reports. Exhausted transport yields an unreachable
    discovery carrying a sanitized error, never an exception.
    """
    attempts = _attempts(settings)
    tried = 0
    while True:
        tried += 1
        try:
            response = await client.list()
            return Discovery(
                reachable=True,
                models=tuple(
                    DiscoveredModel(model=entry.model, digest=entry.digest)
                    for entry in response.models
                ),
                attempts=tried,
                error=None,
            )
        except TRANSIENT_ERRORS as exc:
            if tried >= attempts:
                return Discovery(
                    reachable=False,
                    models=(),
                    attempts=tried,
                    error=_sanitized_error(node, run_id, exc, code=ErrorCode.INTERNAL_ERROR),
                )
        except Exception as exc:  # noqa: BLE001 — boundary sanitizer, never a guess
            return Discovery(
                reachable=False,
                models=(),
                attempts=tried,
                error=_sanitized_error(node, run_id, exc, code=ErrorCode.INTERNAL_ERROR),
            )


def check_health(settings: Settings, discovery: Discovery) -> ModelHealth:
    """Reachable plus the expected model present; ``None`` expected never matches."""
    expected = settings.ollama_model
    present = (
        discovery.reachable
        and expected is not None
        and any(entry.model == expected for entry in discovery.models)
    )
    return ModelHealth(expected=expected, present=present, reachable=discovery.reachable)


def resolve_model(
    settings: Settings, discovery: Discovery, *, run_id: str, node: str
) -> str | ErrorPayload:
    """The model id to call, or a sanitized error failing the run closed.

    Unreachable server, no expected model configured (T0004 open), or the
    expected id missing from the measured inventory all return an error —
    callers record ``INSUFFICIENT_DATA``, never a silent fallback model.
    """
    health = check_health(settings, discovery)
    if health.present and health.expected is not None:
        return health.expected
    if not discovery.reachable and discovery.error is not None:
        return discovery.error
    return ErrorPayload(
        code=ErrorCode.INTERNAL_ERROR,
        message=f"expected model unavailable in graph node {node}",
        retryable=False,
        correlation_id=run_id,
        details=None,
    )


def run_model_record(
    settings: Settings, discovery: Discovery, health: ModelHealth
) -> dict[str, Any]:
    """Measured run metadata for criterion 5: ids, availability, test status.

    Every value is observed (settings, ``list()`` output, health check) —
    availability is measured, never assumed.
    """
    available = sorted(entry.model for entry in discovery.models if entry.model is not None)
    digest = next(
        (
            entry.digest
            for entry in discovery.models
            if entry.model is not None and entry.model == health.expected
        ),
        None,
    )
    return {
        "endpoint": settings.ollama_host,
        "expected_model": health.expected,
        "reachable": health.reachable,
        "model_present": health.present,
        "available_models": available,
        "model_digest": digest,
        "discovery_attempts": discovery.attempts,
    }


async def generate[T: ContractModel](
    settings: Settings,
    client: AsyncClient,
    *,
    model: str,
    messages: list[dict[str, str]],
    response_model: type[T],
    run_id: str,
    node: str,
) -> tuple[T | None, ErrorPayload | None]:
    """One schema-pinned generation: ``format=`` schema, temperature 0.

    Returns the validated model or a sanitized error — raw model text never
    leaves this function unvalidated. Transport and parse failures share one
    bounded attempt budget, then fail closed.
    """
    attempts = _attempts(settings)
    tried = 0
    while True:
        tried += 1
        try:
            response = await client.chat(
                model=model,
                messages=messages,
                format=response_model.model_json_schema(),
                options={"temperature": 0},
            )
            if not isinstance(response, ChatResponse):  # noqa: S101 — stream never asked
                raise TypeError(f"unexpected chat response: {type(response).__name__}")
            # A missing content block validates as empty: the schema rejects
            # it below, so absence fails closed instead of raising here.
            return response_model.model_validate_json(response.message.content or ""), None
        except TRANSIENT_ERRORS as exc:
            if tried >= attempts:
                return None, _sanitized_error(
                    node, run_id, exc, code=ErrorCode.INTERNAL_ERROR
                )
        except ValidationError as exc:
            # Untrusted until model_validate_json passes: bounded retry, then
            # a deterministic rejection — never a filled-in guess.
            if tried >= attempts:
                return None, _sanitized_error(
                    node, run_id, exc, code=ErrorCode.CONTRACT_VALIDATION_FAILED
                )
        except Exception as exc:  # noqa: BLE001 — boundary sanitizer, never a guess
            return None, _sanitized_error(node, run_id, exc, code=ErrorCode.INTERNAL_ERROR)
