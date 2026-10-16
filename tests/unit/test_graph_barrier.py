"""Pre-CEO validation barrier: deterministic gate before any decision (crit. 3).

Disagreements ride verbatim into ``conflicts``; the barrier checks they
survive the gate node untouched, and fails closed on anything unvalidated.
"""

from __future__ import annotations

import asyncio

import pytest
from goldmasters_contracts import AgentRunStatus, Decision

from src.goldmasters.graph.barriers import check_barrier, make_barrier_node
from src.goldmasters.graph.builder import build_graph
from tests.unit.graph_fixtures import (
    AGENT_01_NUMERICS,
    AGENT_01_SCOPE,
    OPEN_RISK,
    apply_clean_env,
    make_opening,
    make_settings,
    run_closing,
)


def _open(monkeypatch: pytest.MonkeyPatch) -> object:
    apply_clean_env(monkeypatch)
    return make_settings(**AGENT_01_SCOPE, **AGENT_01_NUMERICS, **OPEN_RISK)


def test_complete_run_passes_barrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: validated evidence, healthy quality, verdict, verbatim conflicts."""
    settings = _open(monkeypatch)
    graph = build_graph(settings)
    closing = asyncio.run(run_closing(graph, make_opening(settings)))

    assert check_barrier(closing) == []
    assert closing["barrier_passed"] is True
    assert closing["decision"] is not None
    assert closing["decision"].conflicts == closing["conflicts"]


def test_missing_verdict_fails_barrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No verdict, no decision — the barrier fails before the mapper runs."""
    settings = _open(monkeypatch)
    opening = make_opening(settings)
    reasons = check_barrier(opening)
    assert any("no gate verdict" in reason for reason in reasons)


def test_invalid_evidence_fails_barrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A crashed agent's INVALID evidence breaches, naming the agent."""
    settings = _open(monkeypatch)
    graph = build_graph(settings)
    closing = asyncio.run(run_closing(graph, make_opening(settings)))

    tampered = dict(closing)
    tampered["evidence"] = {**closing["evidence"], "trend-following": "invalid"}
    reasons = check_barrier(tampered)  # type: ignore[arg-type]
    assert any("trend-following" in reason for reason in reasons)

    barrier = make_barrier_node()
    update = asyncio.run(barrier(tampered))  # type: ignore[arg-type]
    assert update["barrier_passed"] is False


def test_unhealthy_quality_fails_barrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stale/flagged data never reaches a decision, even with a passed gate."""
    from goldmasters_contracts import QualityStatus

    settings = _open(monkeypatch)
    graph = build_graph(settings)
    closing = asyncio.run(run_closing(graph, make_opening(settings)))

    tampered = dict(closing)
    ctx = closing["market_context"].model_copy(update={"quality_status": QualityStatus.STALE})
    tampered["market_context"] = ctx
    reasons = check_barrier(tampered)  # type: ignore[arg-type]
    assert any("quality" in reason for reason in reasons)


def test_reconciled_conflicts_fail_barrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A gate that drops or rewrites conflicts breaches — verbatim or nothing."""
    settings = _open(monkeypatch)
    graph = build_graph(settings)
    closing = asyncio.run(run_closing(graph, make_opening(settings)))
    assert closing["conflicts"], "setup candidate must seed a conflict entry"

    tampered = dict(closing)
    verdict = closing["gate_verdict"]
    assert verdict is not None
    tampered["gate_verdict"] = verdict.model_copy(update={"conflicts": ["merged summary"]})
    reasons = check_barrier(tampered)  # type: ignore[arg-type]
    assert any("verbatim" in reason for reason in reasons)


def test_barrier_breach_maps_to_insufficient_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Breach precedence: even a passed gate cannot outrank a failed barrier."""
    from src.goldmasters.graph.nodes import assemble_decision

    settings = _open(monkeypatch)
    graph = build_graph(settings)
    closing = asyncio.run(run_closing(graph, make_opening(settings)))

    tampered = dict(closing)
    tampered["barrier_passed"] = False
    tampered["barrier_reasons"] = ["evidence not valid: trend-following"]
    decision = assemble_decision(tampered)  # type: ignore[arg-type]
    assert decision.decision == Decision.INSUFFICIENT_DATA
    assert decision.entry is None
    assert any("evidence not valid" in reason for reason in decision.reasons_for_rejection)
    assert AgentRunStatus(closing["agent_statuses"]["barrier"]) is AgentRunStatus.OK
