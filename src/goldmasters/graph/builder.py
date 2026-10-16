"""Graph assembly: bounds from settings, nodes from nodes.py, edges (D-4.1).

Wiring only — every number comes from Phase 3 code or ``GOLDMASTERS_GRAPH_*``
settings. Per-node ``RetryPolicy`` covers transient transport only;
``TimeoutPolicy`` caps each async node; the checkpointer is ``InMemorySaver``
with ``thread_id=run_id`` for this slice (durable resume arrives with the
model runtime).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import httpx
from goldmasters_api.settings import Settings, hash_effective_config
from goldmasters_contracts import MarketBar, RunId
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy, TimeoutPolicy
from pydantic import TypeAdapter

from src.goldmasters.graph import edges
from src.goldmasters.graph.barriers import make_barrier_node
from src.goldmasters.graph.nodes import (
    code_versions,
    make_evaluate_node,
    make_finalize_node,
    make_gate_node,
    make_ingest_node,
    make_select_node,
)
from src.goldmasters.graph.role_nodes import (
    ANALYST_NODE,
    CEO_NODE,
    NEWS_SENTIMENT_NODE,
    RESEARCH_NODE,
    RoleOptions,
    make_analyst_node,
    make_ceo_prose_node,
    make_news_sentiment_node,
    make_research_node,
)
from src.goldmasters.graph.state import RunState, compute_input_ref
from src.goldmasters.strategies.base import MarketContext

__all__ = ["build_graph", "initial_state", "run_to_decision"]

_BAR_ADAPTER = TypeAdapter(list[MarketBar])
_RUN_ADAPTER = TypeAdapter(RunId)


def initial_state(
    *,
    run_id: str,
    bars: Any,
    ctx: Any,
    settings: Settings,
) -> RunState:
    """Assemble and validate the opening state (contract constructors first).

    Raises ``ValidationError`` on a non-``run_<uuid>`` id or malformed
    bars/context — caller errors, never run outcomes.
    """
    valid_run_id = str(_RUN_ADAPTER.validate_python(run_id))  # run_<uuid> binding
    valid_bars = _BAR_ADAPTER.validate_python(list(bars))
    valid_ctx = ctx if isinstance(ctx, MarketContext) else MarketContext.model_validate(ctx)
    return RunState(
        run_id=valid_run_id,
        input_ref=compute_input_ref(valid_bars, valid_ctx),
        config_hash=hash_effective_config(settings),
        code_versions=code_versions(),
        agent_statuses={},
        evidence={},
        conflicts=[],
        evaluations={},
        gate_verdict=None,
        barrier_passed=None,
        barrier_reasons=[],
        decision=None,
        errors={},
        fatal=None,
        eligible=[],
        bars=valid_bars,
        market_context=valid_ctx,
        started_at=datetime.now(UTC).isoformat(),
        node_times={},
    )


def _retry_policy(settings: Settings) -> RetryPolicy:
    """Transient transport only — validation and policy outcomes never retry."""
    return RetryPolicy(
        max_attempts=1 + settings.graph_node_max_retries,
        retry_on=(httpx.TimeoutException, httpx.ConnectError),
    )


def _timeout(settings: Settings) -> TimeoutPolicy:
    """Per-node wall-clock cap; async-only, so every node is ``async def``."""
    return TimeoutPolicy(run_timeout=settings.graph_node_timeout_seconds)


def _route_after_gate_through_roles(state: RunState) -> str:
    """Spine-preserving hop: barrier-bound flows pass the role nodes first.

    Delegates to :func:`edges.route_after_gate` and only remaps its
    ``BARRIER`` outcome through the role chain — fatal skips to ``FINALIZE``
    unchanged, and unconfigured role nodes skip without touching evidence,
    so the deterministic spine runs as before.
    """
    routed = edges.route_after_gate(state)
    if routed == edges.BARRIER:
        return ANALYST_NODE
    return routed


def build_graph(settings: Settings, *, roles: RoleOptions | None = None) -> Any:
    """Assemble the bounded deterministic graph over validated node factories."""
    options = roles if roles is not None else RoleOptions()
    retry = _retry_policy(settings)
    timeout = _timeout(settings)
    builder = StateGraph(RunState)
    builder.add_node(edges.INGEST, make_ingest_node(), retry_policy=retry, timeout=timeout)
    builder.add_node(edges.SELECT, make_select_node(settings), retry_policy=retry, timeout=timeout)
    builder.add_node(
        edges.EVALUATE, make_evaluate_node(settings), retry_policy=retry, timeout=timeout
    )
    builder.add_node(edges.GATE, make_gate_node(settings), retry_policy=retry, timeout=timeout)
    builder.add_node(
        ANALYST_NODE,
        make_analyst_node(settings, chat=options.analyst_chat, model=options.analyst_model),
        retry_policy=retry,
        timeout=timeout,
    )
    builder.add_node(
        NEWS_SENTIMENT_NODE,
        make_news_sentiment_node(
            settings,
            chat=options.news_chat,
            model=options.news_model,
            coverage_fn=options.news_coverage_fn,
        ),
        retry_policy=retry,
        timeout=timeout,
    )
    builder.add_node(
        RESEARCH_NODE,
        make_research_node(
            settings,
            question=options.research_question,
            sources_fn=options.research_sources_fn,
            chat=options.research_chat,
            model=options.research_model,
        ),
        retry_policy=retry,
        timeout=timeout,
    )
    builder.add_node(edges.BARRIER, make_barrier_node(), retry_policy=retry, timeout=timeout)
    builder.add_node(
        CEO_NODE,
        make_ceo_prose_node(
            settings,
            chat=options.ceo_chat,
            model=options.ceo_model,
            required=options.ceo_required,
        ),
        retry_policy=retry,
        timeout=timeout,
    )
    builder.add_node(edges.FINALIZE, make_finalize_node(), retry_policy=retry, timeout=timeout)
    builder.add_edge(START, edges.INGEST)
    builder.add_conditional_edges(edges.INGEST, edges.route_after_ingest)
    builder.add_edge(edges.SELECT, edges.EVALUATE)
    builder.add_conditional_edges(edges.EVALUATE, edges.route_after_evaluate)
    builder.add_conditional_edges(edges.GATE, _route_after_gate_through_roles)
    builder.add_edge(ANALYST_NODE, NEWS_SENTIMENT_NODE)
    builder.add_edge(NEWS_SENTIMENT_NODE, RESEARCH_NODE)
    builder.add_edge(RESEARCH_NODE, edges.BARRIER)
    builder.add_edge(edges.BARRIER, CEO_NODE)
    builder.add_edge(CEO_NODE, edges.FINALIZE)
    builder.add_edge(edges.FINALIZE, END)
    return builder.compile(checkpointer=InMemorySaver())


async def run_to_decision(
    graph: Any,
    opening: RunState,
    *,
    max_concurrency: int | None = None,
) -> RunState:
    """Invoke one run bound to ``thread_id=run_id``; returns the closing state."""
    config: dict[str, Any] = {"configurable": {"thread_id": opening["run_id"]}}
    if max_concurrency is not None:
        config["max_concurrency"] = max_concurrency
    closing = await graph.ainvoke(opening, config)
    if not isinstance(closing, dict):
        raise TypeError(f"graph returned non-mapping state: {type(closing).__name__}")
    return cast(RunState, closing)
