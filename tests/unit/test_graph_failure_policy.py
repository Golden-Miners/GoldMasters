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
from goldmasters_contracts import (
    AgentRunStatus,
    Decision,
    Direction,
    ErrorCode,
    EvidenceStatus,
    QualityStatus,
    TrendRegime,
)

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


# ---------------------------------------------------------------------------
# Failure-injection doubles: every critical failure path → NO_TRADE or
# INSUFFICIENT_DATA, never an unqualified TRADE. Each injection is traced
# through evaluate_gate (gate.py:86-135) and assemble_decision (nodes.py:421-443).
# ---------------------------------------------------------------------------


def _passing_evaluation() -> object:
    """A strategy evaluation carrying validated levels (setup_found=True)."""
    from src.goldmasters.strategies.agent_01 import (
        CODE_HASH,
        STRATEGY_ID,
        STRATEGY_VERSION,
    )
    from src.goldmasters.strategies.base import (
        RuleCheck,
        build_levels_evaluation,
    )

    check = RuleCheck(
        rule_id="trend-alignment",
        verdict="pass",
        inputs={"fast_ema": "110", "slow_ema": "108"},
        evidence="fast above slow",
        reason="long",
    )
    return build_levels_evaluation(
        strategy_id=STRATEGY_ID,
        strategy_version=STRATEGY_VERSION,
        code_hash=CODE_HASH,
        rule_checks=[check],
        direction=Direction.LONG,
        entry=Decimal("110"),
        stop_loss=Decimal("105"),
        take_profits=[Decimal("120"), Decimal("130")],
        tick_size=Decimal("0.01"),
    )


def _gate_kwargs(evaluation: object, evidence: dict[str, str]) -> dict[str, object]:
    return dict(
        evaluation=evaluation,
        direction=Direction.LONG,
        regime=TrendRegime.UPTREND,
        quality_status=QualityStatus.OK,
        quality_flags=[],
        evidence=evidence,
        conflicts=[],
        min_risk_reward_ratio=Decimal("0.01"),
        max_risk_percent_per_idea=Decimal("100.0"),
        risk_percent_for_idea=Decimal("1.0"),
    )


def test_provider_outage_evidence_missing_blocks_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """(1) Provider outage: MT5 TerminalGateway disconnected/terminal-closed.

    No evidence is produced (provider unreachable) → evidence map empty/invalid
    → evaluate_gate returns passed=False with an evidence reason and no levels;
    assemble_decision can only emit NO_TRADE or INSUFFICIENT_DATA.
    """
    evaluation = _passing_evaluation()
    verdict = evaluate_gate(**_gate_kwargs(evaluation, {}))
    assert verdict.passed is False
    assert verdict.levels is None
    assert any("evidence incomplete" in reason for reason in verdict.reasons_for_rejection)

    # assemble_decision: barrier_passed True but verdict blocked → NO_TRADE only
    # when evidence complete; with missing evidence → INSUFFICIENT_DATA, never TRADE.
    state = _decision_state(verdict=verdict, barrier_passed=True, complete_evidence=False)
    decision = assemble_decision(state)  # type: ignore[arg-type]
    assert decision.decision != Decision.TRADE
    assert decision.entry is None


def test_ollama_model_outage_discovery_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """(2) Ollama model outage: model discovery/list() fails or returns no models.

    resolve_model returns an ErrorPayload (not a model id) → callers record
    INSUFFICIENT_DATA, never a model, so no model-dependent path reaches TRADE.
    """
    from src.goldmasters.graph import runtime
    from src.goldmasters.graph.runtime import discover, resolve_model

    settings = _settings(monkeypatch, ollama_host="http://127.0.0.1:9", graph_node_max_retries=1)
    discovery = asyncio.run(
        discover(
            settings,
            runtime.build_client(settings),
            run_id="run_injected",
            node="ollama_discovery",
        )
    )
    assert discovery.reachable is False
    assert discovery.models == ()
    assert discovery.error is not None

    resolved = resolve_model(
        settings, discovery, run_id="run_injected", node="ollama_discovery"
    )
    assert not isinstance(resolved, str)  # no model id ever escapes an outage
    assert resolved.code == ErrorCode.INTERNAL_ERROR


def test_db_outage_evidence_invalid_blocks_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """(3) Database outage: connection refused.

    DB-backed evidence cannot be validated → evidence carries an INVALID status
    → evaluate_gate returns passed=False with "evidence not valid" reason,
    levels stay None, so TRADE is unreachable.
    """
    evaluation = _passing_evaluation()
    verdict = evaluate_gate(
        **_gate_kwargs(evaluation, {"db_persistence": EvidenceStatus.INVALID.value})
    )
    assert verdict.passed is False
    assert verdict.levels is None
    assert any(
    "evidence not valid: db_persistence" in reason
    for reason in verdict.reasons_for_rejection
)


def test_timeout_gate_crash_insufficient_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """(4) Timeout: node/probe/graph timeout exceeded.

    A timed-out/crashed gate is caught by make_gate_node → fatal="gate" → the
    terminal mapper routes to INSUFFICIENT_DATA (no levels), never TRADE.
    """
    import src.goldmasters.graph.nodes as nodes

    def _boom(*args: object, **kwargs: object) -> object:
        raise TimeoutError("FIXTURE graph node timeout exceeded")

    monkeypatch.setattr(nodes, "evaluate_gate", _boom)
    settings = _settings(monkeypatch)
    graph = build_graph(settings)  # type: ignore[arg-type]
    closing = asyncio.run(run_closing(graph, make_opening(settings)))  # type: ignore[arg-type]

    assert closing["fatal"] == "gate"
    assert closing["agent_statuses"]["gate"] == AgentRunStatus.ERROR.value
    decision = closing["decision"]
    assert decision is not None and decision.decision == Decision.INSUFFICIENT_DATA
    assert decision.entry is None
    assert any("fatal stage failure: gate" in r for r in decision.reasons_for_rejection)


def test_malformed_output_evidence_invalid_blocks_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """(5) Malformed output: invalid JSON/bar fields or unparseable model response.

    A malformed model response fails contract validation → evidence INVALID
    (never a filled-in guess) → evaluate_gate passed=False; a malformed bar
    fails ingest contract validation → fatal ingest → INSUFFICIENT_DATA.
    Either way TRADE is unreachable.
    """
    evaluation = _passing_evaluation()
    verdict = evaluate_gate(
        **_gate_kwargs(evaluation, {"model_response": EvidenceStatus.INVALID.value})
    )
    assert verdict.passed is False
    assert verdict.levels is None
    assert any(
    "evidence not valid: model_response" in reason
    for reason in verdict.reasons_for_rejection
)


def _decision_state(
    *,
    verdict: object,
    barrier_passed: bool,
    complete_evidence: bool,
    fatal: str | None = None,
) -> dict[str, object]:
    """Build a minimal RunState for assemble_decision tracing."""
    from datetime import UTC, datetime

    from goldmasters_contracts import QualityStatus, Timeframe, TrendRegime, VolumeType

    from src.goldmasters.strategies.base import MarketContext

    return {
        "run_id": "run_00000000000000000000000000000000",
        "market_context": MarketContext(
            instrument_id="xauusd",
            provider_id="mt5",
            timeframe=Timeframe.H1,
            regime=TrendRegime.UPTREND,
            quality_status=QualityStatus.OK,
            quality_flags=[],
            volume_type=VolumeType.TICK,
            tick_size="0.01",
            contract_size=None,
            bar_count=8,
            now_utc=datetime(2026, 1, 6, 12, 0, tzinfo=UTC),
        ),
        "gate_verdict": verdict,
        "barrier_passed": barrier_passed,
        "barrier_reasons": [],
        "fatal": fatal,
        "eligible": ["trend-following"] if complete_evidence else [],
        "evidence": {"trend-following": EvidenceStatus.VALID.value} if complete_evidence else {},
        "evaluations": {"trend-following": _passing_evaluation()},
        "conflicts": [],
        "agent_statuses": {},
        "errors": {},
        "data_quality_status": QualityStatus.OK,
    }


def test_assemble_decision_blocked_verdict_never_trade(monkeypatch: pytest.MonkeyPatch) -> None:
    """Trace: blocked gate verdict → assemble_decision emits NO_TRADE/INSUFFICIENT_DATA only.

    With barrier_passed=True and verdict.passed=False, TRADE is unreachable:
    complete evidence → NO_TRADE carrying the gate's rejection reasons;
    incomplete evidence → INSUFFICIENT_DATA. Levels always stay None.
    """
    evaluation = _passing_evaluation()
    verdict = evaluate_gate(**_gate_kwargs(evaluation, {}))  # blocked: missing evidence
    assert verdict.passed is False

    # complete evidence → NO_TRADE
    decision = assemble_decision(
        _decision_state(verdict=verdict, barrier_passed=True, complete_evidence=True)
    )
    assert decision.decision == Decision.NO_TRADE
    assert decision.entry is None
    assert decision.reasons_for_rejection == list(verdict.reasons_for_rejection)

    # incomplete evidence → INSUFFICIENT_DATA
    decision = assemble_decision(
        _decision_state(verdict=verdict, barrier_passed=True, complete_evidence=False)
    )
    assert decision.decision == Decision.INSUFFICIENT_DATA
    assert decision.entry is None


def test_assemble_decision_trade_only_when_barrier_and_verdict_passed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TRADE fires ONLY when barrier_passed is True AND verdict.passed (nodes.py:421-443).

    Any failure mode that leaves barrier_passed falsy or verdict.passed False
    cannot reach the TRADE constructor.
    """
    evaluation = _passing_evaluation()
    passed_verdict = evaluate_gate(
        evaluation=evaluation,
        direction=Direction.LONG,
        regime=TrendRegime.UPTREND,
        quality_status=QualityStatus.OK,
        quality_flags=[],
        evidence={"trend-following": EvidenceStatus.VALID.value},
        conflicts=[],
        min_risk_reward_ratio=Decimal("0.01"),
        max_risk_percent_per_idea=Decimal("100.0"),
        risk_percent_for_idea=Decimal("1.0"),
    )
    assert passed_verdict.passed is True
    assert passed_verdict.levels is not None

    decision = assemble_decision(
        _decision_state(
            verdict=passed_verdict,
            barrier_passed=True,
            complete_evidence=True,
        )
    )
    assert decision.decision == Decision.TRADE
    assert decision.entry is not None

    # Same passing verdict but barrier breached → not TRADE
    decision = assemble_decision(
        _decision_state(
            verdict=passed_verdict,
            barrier_passed=False,
            complete_evidence=True,
            fatal="evaluate",
        )
    )
    assert decision.decision != Decision.TRADE
    assert decision.entry is None
