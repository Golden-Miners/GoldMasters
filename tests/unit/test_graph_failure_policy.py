"""Failure policy: critical failure → INSUFFICIENT_DATA/NO_TRADE (crit. 6).

Failure-injection proofs that no path constructs an unqualified TRADE:
critical stage failures terminate as INSUFFICIENT_DATA, gate-blocked runs
with complete evidence terminate as NO_TRADE, and the TRADE constructor
fires only on a passed GateVerdict carrying validated levels. T0411-partial:
typed I/O, version stamps, timeout, and failure status per built node.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

import httpx
import pytest
from goldmasters_contracts import AgentRunStatus, Decision, Direction, EvidenceStatus

from src.goldmasters.graph.barriers import check_barrier
from src.goldmasters.graph.builder import build_graph
from src.goldmasters.graph.nodes import assemble_decision, code_versions
from src.goldmasters.risk.gate import evaluate_gate
from tests.unit.graph_fixtures import (
    AGENT_01_NUMERICS,
    AGENT_01_SCOPE,
    OPEN_RISK,
    apply_clean_env,
    make_opening,
    make_settings,
    run_closing,
)

#: FIXTURE per-idea risk, test-supplied (no producer exists in Wave 1): well
#: under the OPEN_RISK ceiling, so the gate's only remaining check passes.
FIXTURE_IDEA_RISK = Decimal("1.0")


def _settings(monkeypatch: pytest.MonkeyPatch, **overrides: object) -> object:
    apply_clean_env(monkeypatch)
    base: dict[str, object] = {**AGENT_01_SCOPE, **AGENT_01_NUMERICS, **OPEN_RISK}
    base.update(overrides)
    return make_settings(**base)


def test_agent_crash_terminates_as_insufficient_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A crashing strategy agent breaches the barrier — never a silent skip."""
    import src.goldmasters.strategies.agent_01 as agent_01

    def _boom(*args: object, **kwargs: object) -> object:
        raise RuntimeError("FIXTURE transport collapse")

    monkeypatch.setattr(agent_01, "evaluate", _boom)
    settings = _settings(monkeypatch)
    graph = build_graph(settings)  # type: ignore[arg-type]
    closing = asyncio.run(run_closing(graph, make_opening(settings)))  # type: ignore[arg-type]

    assert closing["agent_statuses"]["trend-following"] == AgentRunStatus.ERROR.value
    assert closing["barrier_passed"] is False
    decision = closing["decision"]
    assert decision is not None and decision.decision == Decision.INSUFFICIENT_DATA
    assert decision.entry is None
    assert closing["errors"]["trend-following"].correlation_id == closing["run_id"]


def test_agent_transient_error_recorded_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Agent-level transients record fail-closed; the node stays the retry unit.

    The evaluate node catches per-agent errors for partial-failure semantics,
    so a crashing agent is recorded (not re-run). Node-level ``RetryPolicy``
    stays armed for raising nodes — proven by the select-level test below —
    and its ``retry_on`` covers exactly this exception (D-4.2).
    """
    import src.goldmasters.strategies.agent_01 as agent_01
    from src.goldmasters.graph.builder import _retry_policy  # noqa: PLC2701

    attempts = 0

    def _flaky(*args: object, **kwargs: object) -> object:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("FIXTURE connect reset")

    monkeypatch.setattr(agent_01, "evaluate", _flaky)
    settings = _settings(monkeypatch, graph_node_max_retries=1)
    policy = _retry_policy(settings)  # type: ignore[arg-type]
    assert isinstance(httpx.ConnectError("x"), tuple(policy.retry_on or ()))

    graph = build_graph(settings)  # type: ignore[arg-type]
    closing = asyncio.run(run_closing(graph, make_opening(settings)))  # type: ignore[arg-type]

    assert attempts == 1, "recorded once — the node, not the agent, is retried"
    assert closing["agent_statuses"]["trend-following"] == AgentRunStatus.ERROR.value
    decision = closing["decision"]
    assert decision is not None and decision.decision == Decision.INSUFFICIENT_DATA


def test_node_transient_error_retries_per_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A raising node retries transient errors per policy, then fails visibly."""
    import src.goldmasters.graph.nodes as nodes

    attempts = 0

    def _flaky(*args: object, **kwargs: object) -> object:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("FIXTURE select transport reset")

    monkeypatch.setattr(nodes, "eligible_agents", _flaky)
    settings = _settings(monkeypatch, graph_node_max_retries=1)
    graph = build_graph(settings)  # type: ignore[arg-type]
    opening = make_opening(settings)  # type: ignore[arg-type]

    with pytest.raises(httpx.ConnectError):
        asyncio.run(run_closing(graph, opening))

    assert attempts == 2, "1 initial attempt + 1 configured retry (D-4.2)"


def test_gate_crash_terminates_as_insufficient_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A crashed gate skips to the terminal mapper — INSUFFICIENT_DATA, no levels."""
    import src.goldmasters.graph.nodes as nodes

    def _boom(*args: object, **kwargs: object) -> object:
        raise RuntimeError("FIXTURE gate collapse")

    monkeypatch.setattr(nodes, "evaluate_gate", _boom)
    settings = _settings(monkeypatch)
    graph = build_graph(settings)  # type: ignore[arg-type]
    closing = asyncio.run(run_closing(graph, make_opening(settings)))  # type: ignore[arg-type]

    assert closing["fatal"] == "gate"
    assert closing["agent_statuses"]["gate"] == AgentRunStatus.ERROR.value
    decision = closing["decision"]
    assert decision is not None and decision.decision == Decision.INSUFFICIENT_DATA
    assert any("fatal stage failure: gate" in reason for reason in decision.reasons_for_rejection)


def test_agent_without_data_yields_insufficient_not_no_trade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Below-min_bars is MISSING evidence: the run cannot claim NO_TRADE."""
    settings = _settings(monkeypatch, strategy_agent_01_min_bars=50)
    graph = build_graph(settings)  # type: ignore[arg-type]
    closing = asyncio.run(run_closing(graph, make_opening(settings)))  # type: ignore[arg-type]

    assert closing["agent_statuses"]["trend-following"] == AgentRunStatus.INSUFFICIENT_DATA.value
    assert closing["evidence"]["trend-following"] == "missing"
    assert closing["barrier_passed"] is False
    decision = closing["decision"]
    assert decision is not None and decision.decision == Decision.INSUFFICIENT_DATA


def test_passed_gate_builds_trade_with_validated_levels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sole path to TRADE: passed verdict + gate-validated levels + intact barrier."""

    settings = _settings(monkeypatch)
    graph = build_graph(settings)  # type: ignore[arg-type]
    closing = asyncio.run(run_closing(graph, make_opening(settings)))  # type: ignore[arg-type]

    evaluation = closing["evaluations"]["trend-following"]
    assert evaluation.setup_found and evaluation.candidate_levels is not None
    verdict = evaluate_gate(
        evaluation=evaluation,
        direction=Direction.LONG,
        regime=closing["market_context"].regime,
        quality_status=closing["market_context"].quality_status,
        quality_flags=list(closing["market_context"].quality_flags),
        evidence={key: EvidenceStatus(value) for key, value in closing["evidence"].items()},
        conflicts=list(closing["conflicts"]),
        min_risk_reward_ratio=Decimal("0.01"),
        max_risk_percent_per_idea=Decimal("100.0"),
        risk_percent_for_idea=FIXTURE_IDEA_RISK,
    )
    assert verdict.passed is True  # the only shape that may become TRADE

    tampered = dict(closing)
    tampered["gate_verdict"] = verdict.model_copy(update={"conflicts": list(closing["conflicts"])})
    assert check_barrier(tampered) == []  # type: ignore[arg-type]
    tampered["barrier_passed"] = True
    decision = assemble_decision(tampered)  # type: ignore[arg-type]

    assert decision.decision == Decision.TRADE
    assert decision.direction == Direction.LONG
    assert decision.strategy_id == "trend-following"
    assert decision.strategy_version == "1.0.0"
    assert decision.entry is not None and decision.stop_loss is not None
    assert len(decision.take_profits) > 0 and decision.risk_reward is not None
    assert decision.manual_review_required is True


def test_t0411_partial_version_timeout_status_per_node(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every built node: version stamps, bounded policy, honest failure status."""
    import src.goldmasters.strategies.agent_01 as agent_01

    stamps = code_versions()
    assert len(stamps) == 10
    assert stamps["trend-following"] == f"1.0.0@{agent_01.CODE_HASH}"

    settings = _settings(monkeypatch)
    graph = build_graph(settings)  # type: ignore[arg-type]
    closing = asyncio.run(run_closing(graph, make_opening(settings)))  # type: ignore[arg-type]

    statuses = closing["agent_statuses"]
    assert statuses["trend-following"] == AgentRunStatus.OK.value
    assert statuses["time-series-momentum"] == AgentRunStatus.SKIPPED.value  # disabled row
    for node in ("ingest", "select", "evaluate", "gate", "barrier", "finalize"):
        AgentRunStatus(statuses[node])  # closed enum, no magic strings
        assert node in closing["node_times"]
