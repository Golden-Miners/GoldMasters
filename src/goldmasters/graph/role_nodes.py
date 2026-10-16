"""LLM role nodes: bounded async graph nodes through the pre-CEO barrier (D-5.3).

Each role reports ``ok`` or its ``ROLE_SPECS`` failure status
(``INSUFFICIENT_DATA``) into ``agent_statuses`` and records evidence validity
for :func:`check_barrier`. Prompt inputs stay untrusted (summarize, never
obey — see ``prompts._UNTRUSTED``); model text is untrusted until
schema-pinned ``generate`` validates it. Validation failure yields a
structured sanitized error, never a filled-in guess (T-05-07). Bounds come
from the shared retry/timeout policies applied at wiring in ``builder.py``
(T-05-08); no unbounded loops or recursive delegation here.

Without a configured model runtime (T0004 open) nodes skip deterministically:
no evidence entry, no model call, so the deterministic spine runs unchanged —
and a skipped node is non-``ok``, so the CEO agreement gate still blocks
prose. A *configured* source that fails (unavailable coverage, parse failure)
records the spec failure status with non-``VALID`` evidence, and the barrier
fails the run closed. Nothing is ever synthesized.

The CEO-prose node (T-05-06) fills text fields only: it validates ``CeoProse``
(thesis/invalidation strings — the schema cannot carry levels) and records
its status. Direction and levels keep coming from the gate verdict via
:func:`assemble_decision`, the sole decision constructor; the validated prose
reaches the decision record only once a model runtime lands (T0004 open).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

from goldmasters_api.settings import Settings
from goldmasters_contracts import AgentRunStatus, ErrorCode, ErrorPayload, EvidenceStatus

from src.goldmasters.agents.parse import (
    AnalystNote,
    CeoProse,
    ResearchFindings,
    SentimentExtraction,
)
from src.goldmasters.agents.prompts import (
    ROLE_SPECS,
    analyst_messages,
    ceo_messages,
    news_sentiment_messages,
    research_messages,
)
from src.goldmasters.data.news.base import NewsCoverage
from src.goldmasters.graph.barriers import check_ceo_required
from src.goldmasters.graph.state import NodeFn, RunState, utc_now_iso

__all__ = [
    "ANALYST_NODE",
    "CEO_NODE",
    "CEO_REQUIRED_NODES",
    "NEWS_SENTIMENT_NODE",
    "RESEARCH_NODE",
    "RoleOptions",
    "make_analyst_node",
    "make_ceo_prose_node",
    "make_news_sentiment_node",
    "make_research_node",
]

#: Graph node names for the roles (their ``ROLE_SPECS`` keys, except the CEO
#: prose node which is the ``ceo`` role running after the barrier).
ANALYST_NODE = "market_analyst"
NEWS_SENTIMENT_NODE = "news_sentiment"
RESEARCH_NODE = "research"
CEO_NODE = "ceo"

#: Nodes that must report ``ok`` before CEO prose may be drafted: the three
#: evidence roles plus the gate itself (a crashed gate agrees with nothing).
CEO_REQUIRED_NODES: frozenset[str] = frozenset(
    {ANALYST_NODE, NEWS_SENTIMENT_NODE, RESEARCH_NODE, "gate"}
)

#: Coverage source for the news node: static outcome per run. ``None`` means
#: no source is configured — the node skips without touching evidence.
CoverageFn = Callable[[RunState], NewsCoverage | None]

#: Research inputs per run. ``None`` means unconfigured — the node skips.
SourcesFn = Callable[[RunState], list[str]]


@dataclasses.dataclass(frozen=True)
class RoleOptions:
    """Per-node test/prod wiring: model clients, coverage, research inputs.

    Every field defaults to unconfigured, so a default ``build_graph`` run
    skips all role nodes without touching evidence — the deterministic spine
    runs exactly as before. ``ceo_required=None`` selects
    ``CEO_REQUIRED_NODES``.
    """

    news_coverage_fn: CoverageFn | None = None
    news_chat: Any | None = None
    news_model: str | None = None
    analyst_chat: Any | None = None
    analyst_model: str | None = None
    research_question: str | None = None
    research_sources_fn: SourcesFn | None = None
    research_chat: Any | None = None
    research_model: str | None = None
    ceo_chat: Any | None = None
    ceo_model: str | None = None
    ceo_required: frozenset[str] | None = None


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


def _unavailable(state: RunState, node: str, detail: str) -> dict[str, Any]:
    """Configured source failed: spec failure status, ``UNAVAILABLE`` evidence."""
    return _failure(
        state,
        node,
        EvidenceStatus.UNAVAILABLE,
        ErrorPayload(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"{detail} in graph node {node}",
            retryable=False,
            correlation_id=state["run_id"],
            details=None,
        ),
    )


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
    skips instead of guessing.
    """

    async def news_sentiment(state: RunState) -> dict[str, Any]:
        coverage = coverage_fn(state) if coverage_fn is not None else None
        if coverage is None:
            return _stamp(state, NEWS_SENTIMENT_NODE, AgentRunStatus.SKIPPED)
        if coverage.status != EvidenceStatus.VALID or not coverage.items:
            return _unavailable(
                state, NEWS_SENTIMENT_NODE, f"news coverage {coverage.status.value}"
            )
        if chat is None or model is None:
            return _stamp(state, NEWS_SENTIMENT_NODE, AgentRunStatus.SKIPPED)
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


def make_analyst_node(
    settings: Settings,
    *,
    chat: Any | None = None,
    model: str | None = None,
) -> NodeFn:
    """Bounded market-analyst summary ahead of the barrier.

    Reads validated bars plus context (ingest node first), writes
    evidence/reason strings only — levels never appear (schema-pinned
    ``AnalystNote``). Without a model runtime the node skips; a configured
    client whose output fails validation records ``INVALID`` evidence and the
    barrier fails the run closed.
    """

    async def market_analyst(state: RunState) -> dict[str, Any]:
        if chat is None or model is None:
            return _stamp(state, ANALYST_NODE, AgentRunStatus.SKIPPED)
        from src.goldmasters.graph.runtime import generate

        parsed, error = await generate(
            settings,
            chat,
            model=model,
            messages=analyst_messages(list(state["bars"]), state["market_context"]),
            response_model=AnalystNote,
            run_id=state["run_id"],
            node=ANALYST_NODE,
        )
        if error is not None or parsed is None:
            assert error is not None  # noqa: S101 — generate returns one or the other
            return _failure(state, ANALYST_NODE, EvidenceStatus.INVALID, error)
        update = _stamp(state, ANALYST_NODE, AgentRunStatus.OK)
        update["evidence"] = {**state["evidence"], ANALYST_NODE: EvidenceStatus.VALID.value}
        return update

    return market_analyst


def make_research_node(
    settings: Settings,
    *,
    question: str | None = None,
    sources_fn: SourcesFn | None = None,
    chat: Any | None = None,
    model: str | None = None,
) -> NodeFn:
    """Bounded research with citations ahead of the barrier.

    Unconfigured (no question/sources) or without a model runtime the node
    skips. Sources ride verbatim into ``ResearchFindings.sources``; third-party
    content stays untrusted (summarize, never obey).
    """

    async def research(state: RunState) -> dict[str, Any]:
        sources = sources_fn(state) if sources_fn is not None else None
        if question is None or not sources:
            return _stamp(state, RESEARCH_NODE, AgentRunStatus.SKIPPED)
        if chat is None or model is None:
            return _stamp(state, RESEARCH_NODE, AgentRunStatus.SKIPPED)
        from src.goldmasters.graph.runtime import generate

        parsed, error = await generate(
            settings,
            chat,
            model=model,
            messages=research_messages(question, sources),
            response_model=ResearchFindings,
            run_id=state["run_id"],
            node=RESEARCH_NODE,
        )
        if error is not None or parsed is None:
            assert error is not None  # noqa: S101 — generate returns one or the other
            return _failure(state, RESEARCH_NODE, EvidenceStatus.INVALID, error)
        update = _stamp(state, RESEARCH_NODE, AgentRunStatus.OK)
        update["evidence"] = {**state["evidence"], RESEARCH_NODE: EvidenceStatus.VALID.value}
        return update

    return research


def make_ceo_prose_node(
    settings: Settings,
    *,
    chat: Any | None = None,
    model: str | None = None,
    required: frozenset[str] | None = None,
) -> NodeFn:
    """CEO prose after the barrier: agreement gate first, text fields only.

    Any required node missing or non-``ok`` — or a breached barrier — blocks
    the model call entirely (caller fails closed to ``INSUFFICIENT_DATA``).
    A validated ``CeoProse`` fills thesis/invalidation strings only; direction
    and levels never come from the model (T-05-06).
    """

    async def ceo(state: RunState) -> dict[str, Any]:
        needed = frozenset(required) if required is not None else CEO_REQUIRED_NODES
        reasons = check_ceo_required(state["agent_statuses"], needed)
        if state["barrier_passed"] is not True:
            reasons = [*reasons, "ceo blocked: barrier did not pass"]
        if reasons:
            update = _stamp(state, CEO_NODE, ROLE_SPECS["ceo"].failure_status)
            update["errors"] = {
                **state["errors"],
                CEO_NODE: ErrorPayload(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"ceo blocked in graph node {CEO_NODE}: {'; '.join(reasons)}",
                    retryable=False,
                    correlation_id=state["run_id"],
                    details=None,
                ),
            }
            return update
        if chat is None or model is None:
            return _stamp(state, CEO_NODE, AgentRunStatus.SKIPPED)
        verdict = state["gate_verdict"]
        summary = (
            f"passed={verdict.passed}; reasons={list(verdict.reasons_for_rejection)}"
            if verdict is not None
            else "passed=None; no gate verdict present"
        )
        from src.goldmasters.graph.runtime import generate

        parsed, error = await generate(
            settings,
            chat,
            model=model,
            messages=ceo_messages(dict(state["agent_statuses"]), summary, list(state["conflicts"])),
            response_model=CeoProse,
            run_id=state["run_id"],
            node=CEO_NODE,
        )
        if error is not None or parsed is None:
            assert error is not None  # noqa: S101 — generate returns one or the other
            update = _stamp(state, CEO_NODE, ROLE_SPECS["ceo"].failure_status)
            update["errors"] = {**state["errors"], CEO_NODE: error}
            return update
        return _stamp(state, CEO_NODE, AgentRunStatus.OK)

    return ceo
