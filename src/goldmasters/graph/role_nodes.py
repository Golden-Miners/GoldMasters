"""LLM role nodes: bounded async graph nodes through the pre-CEO barrier (D-5.3).

Each role reports ``ok`` or its ``ROLE_SPECS`` failure status
(``INSUFFICIENT_DATA``) into ``agent_statuses`` and records evidence validity
for :func:`check_barrier`. Prompt inputs stay untrusted (summarize, never
obey — see ``prompts._UNTRUSTED``); model text is untrusted until
schema-pinned ``generate`` validates it. Validation failure yields a
structured sanitized error, never a filled-in guess (T-05-07). Bounds come
from the shared retry/timeout policies applied at wiring in ``builder.py``
(T-05-08); no unbounded loops or recursive delegation here.

Without a configured model runtime (T0004 open) or coverage source, nodes
fail closed deterministically: unconfigured roles ``skip`` without touching
evidence, attempted-but-unrunnable roles record the spec failure status with
``MISSING``/``UNAVAILABLE`` evidence — no model call, no synthesis, ever.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from goldmasters_api.settings import Settings
from goldmasters_contracts import AgentRunStatus, ErrorCode, ErrorPayload, EvidenceStatus

from src.goldmasters.agents.parse import SentimentExtraction
from src.goldmasters.agents.prompts import ROLE_SPECS, news_sentiment_messages
from src.goldmasters.data.news.base import NewsCoverage
from src.goldmasters.graph.state import NodeFn, RunState, utc_now_iso

__all__ = [
    "NEWS_SENTIMENT_NODE",
    "make_news_sentiment_node",
]

#: Graph node name for the news/sentiment role (its ``ROLE_SPECS`` key).
NEWS_SENTIMENT_NODE = "news_sentiment"

#: Coverage source for the news node: static outcome per run. ``None`` means
#: no source is configured — the node skips without touching evidence.
CoverageFn = Callable[[RunState], NewsCoverage | None]


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


def _stamp(state: RunState, node: str, status: AgentRunStatus) -> dict[str, Any]:
    """Per-node status plus completion instant (D-4.3 minimal log inputs)."""
    return {
        "agent_statuses": {**state["agent_statuses"], node: status.value},
        "node_times": {**state["node_times"], node: utc_now_iso()},
    }


def _failure(
    state: RunState, node: str, evidence_status: EvidenceStatus, error: ErrorPayload
) -> dict[str, Any]:
    """Spec failure status plus evidence validity plus the sanitized error."""
    spec = ROLE_SPECS[node]
    update = _stamp(state, node, spec.failure_status)
    update["evidence"] = {**state["evidence"], node: evidence_status.value}
    update["errors"] = {**state["errors"], node: error}
    return update


def make_news_sentiment_node(
    settings: Settings,
    *,
    chat: Any | None = None,
    model: str | None = None,
    coverage_fn: CoverageFn | None = None,
) -> NodeFn:
    """Bounded news/sentiment extraction ahead of the barrier.

    Unconfigured (no ``coverage_fn``) the node skips: no evidence entry, no
    model call, so the deterministic spine runs unchanged. An ``unavailable``
    (or empty) coverage records the spec failure status with ``UNAVAILABLE``
    evidence — the barrier then fails the run closed with no synthesized
    headline or sentiment. With items but no model runtime (T0004 open) it
    records ``MISSING`` evidence instead of guessing.
    """

    async def news_sentiment(state: RunState) -> dict[str, Any]:
        coverage = coverage_fn(state) if coverage_fn is not None else None
        if coverage is None:
            update = _stamp(state, NEWS_SENTIMENT_NODE, AgentRunStatus.SKIPPED)
            return update
        if coverage.status != EvidenceStatus.VALID or not coverage.items:
            return _failure(
                state,
                NEWS_SENTIMENT_NODE,
                EvidenceStatus.UNAVAILABLE,
                ErrorPayload(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=(
                        f"news coverage {coverage.status.value} in graph node {NEWS_SENTIMENT_NODE}"
                    ),
                    retryable=False,
                    correlation_id=state["run_id"],
                    details=None,
                ),
            )
        if chat is None or model is None:
            return _failure(
                state,
                NEWS_SENTIMENT_NODE,
                EvidenceStatus.MISSING,
                ErrorPayload(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"no model runtime in graph node {NEWS_SENTIMENT_NODE}",
                    retryable=False,
                    correlation_id=state["run_id"],
                    details=None,
                ),
            )
        # Delayed import: the model path stays inside the runtime boundary
        # pinned by test_runtime_imports_stay_in_boundary.
        from src.goldmasters.graph.runtime import generate

        parsed, error = await generate(
            settings,
            chat,
            model=model,
            messages=news_sentiment_messages(list(coverage.items)),
            response_model=SentimentExtraction,
            run_id=state["run_id"],
            node=NEWS_SENTIMENT_NODE,
        )
        if error is not None or parsed is None:
            assert error is not None  # noqa: S101 — generate returns one or the other
            return _failure(state, NEWS_SENTIMENT_NODE, EvidenceStatus.INVALID, error)
        update = _stamp(state, NEWS_SENTIMENT_NODE, AgentRunStatus.OK)
        update["evidence"] = {**state["evidence"], NEWS_SENTIMENT_NODE: EvidenceStatus.VALID.value}
        return update

    return news_sentiment
