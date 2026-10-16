"""Graph bounds: async nodes, config-driven retry/timeout, capped fan-out (crit. 2)."""

from __future__ import annotations

import asyncio
import inspect

import httpx
import pytest
from goldmasters_contracts import AgentRunStatus
from langgraph.types import RetryPolicy, TimeoutPolicy
from pydantic import ValidationError

from src.goldmasters.graph.barriers import make_barrier_node
from src.goldmasters.graph.builder import build_graph
from src.goldmasters.graph.nodes import (
    make_evaluate_node,
    make_finalize_node,
    make_gate_node,
    make_ingest_node,
    make_select_node,
)
from tests.unit.graph_fixtures import (
    AGENT_01_NUMERICS,
    AGENT_01_SCOPE,
    OPEN_RISK,
    apply_clean_env,
    make_opening,
    make_settings,
    run_closing,
)


def _settings(monkeypatch: pytest.MonkeyPatch, **overrides: object) -> object:
    apply_clean_env(monkeypatch)
    base: dict[str, object] = {**AGENT_01_SCOPE, **AGENT_01_NUMERICS, **OPEN_RISK}
    base.update(overrides)
    return make_settings(**base)


def test_all_nodes_are_async(monkeypatch: pytest.MonkeyPatch) -> None:
    """TimeoutPolicy is async-only: every node must be ``async def`` (Pitfall 1)."""
    settings = _settings(monkeypatch)
    for factory in (
        make_ingest_node(),
        make_select_node(settings),  # type: ignore[arg-type]
        make_evaluate_node(settings),  # type: ignore[arg-type]
        make_gate_node(settings),  # type: ignore[arg-type]
        make_barrier_node(),
        make_finalize_node(),
    ):
        assert inspect.iscoroutinefunction(factory)


def test_retry_policy_is_transient_only_and_config_driven(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2 retries from settings; transport errors only — never validation/policy."""
    from src.goldmasters.graph.builder import _retry_policy  # noqa: PLC2701

    settings = _settings(monkeypatch, graph_node_max_retries=2)
    policy = _retry_policy(settings)  # type: ignore[arg-type]
    assert isinstance(policy, RetryPolicy)
    assert policy.max_attempts == 3  # 1 initial + 2 retries (D-4.2)
    assert set(policy.retry_on or ()) == {httpx.TimeoutException, httpx.ConnectError}

    scoped = _settings(monkeypatch, graph_node_max_retries=0)
    assert _retry_policy(scoped).max_attempts == 1  # type: ignore[arg-type]


def test_timeout_policy_comes_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """60s locked default, operator-overridable, invalid fails at startup."""
    from src.goldmasters.graph.builder import _timeout  # noqa: PLC2701

    settings = _settings(monkeypatch)
    policy = _timeout(settings)  # type: ignore[arg-type]
    assert isinstance(policy, TimeoutPolicy)
    assert policy.run_timeout == 60.0

    faster = _settings(monkeypatch, graph_node_timeout_seconds=5.0)
    assert _timeout(faster).run_timeout == 5.0  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        _settings(monkeypatch, graph_node_timeout_seconds=-1.0)
    with pytest.raises(ValidationError):
        _settings(monkeypatch, graph_node_max_retries=-1)


def test_fan_out_is_exactly_the_eligible_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Node count assert: one evaluation per eligible agent, no more."""
    settings = _settings(monkeypatch)
    graph = build_graph(settings)  # type: ignore[arg-type]
    closing = asyncio.run(
        run_closing(graph, make_opening(settings))  # type: ignore[arg-type]
    )

    assert closing["eligible"] == ["trend-following"]
    evaluated = [
        sid
        for sid in closing["eligible"]
        if sid in closing["evaluations"] or closing["agent_statuses"].get(sid) == "error"
    ]
    assert len(evaluated) == len(closing["eligible"]) == 1
    assert closing["fatal"] is None


def test_max_concurrency_from_config_still_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit concurrency cap serializes without stranding the run."""
    settings = _settings(monkeypatch, graph_max_concurrency=1)
    graph = build_graph(settings)  # type: ignore[arg-type]
    closing = asyncio.run(
        run_closing(
            graph,
            make_opening(settings),  # type: ignore[arg-type]
            max_concurrency=settings.graph_max_concurrency,  # type: ignore[union-attr]
        )
    )
    assert closing["decision"] is not None
    assert closing["agent_statuses"]["finalize"] == AgentRunStatus.OK.value
