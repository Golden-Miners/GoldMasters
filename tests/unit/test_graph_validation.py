"""Per-node schema validation: malformed I/O becomes sanitized errors (crit. 4).

Every node boundary re-validates contracts; malformed input yields a
Schema §10 sanitized error and a failed-closed run — never a guess, never
a decision on unvalidated payloads. LLM-shaped slots stay stubs with cause.
"""

from __future__ import annotations

import asyncio

import pytest
from goldmasters_contracts import (
    AgentRunStatus,
    Decision,
    ErrorCode,
    EvidenceStatus,
)

from src.goldmasters.graph.builder import build_graph
from src.goldmasters.graph.nodes import (
    CEO_STUB_CAUSE,
    assemble_decision,
    make_gate_node,
)
from src.goldmasters.strategies.base import StrategyEvaluation
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


def test_malformed_bars_fail_closed_with_sanitized_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Corrupt checkpoint payloads fail at ingest: no trace, no path, terminal."""
    settings = _settings(monkeypatch)
    graph = build_graph(settings)  # type: ignore[arg-type]
    opening = make_opening(settings)  # type: ignore[arg-type]
    corrupted = dict(opening)
    corrupted["bars"] = [{"nope": 1}]  # type: ignore[list-item]

    closing = asyncio.run(run_closing(graph, corrupted))  # type: ignore[arg-type]

    assert closing["fatal"] == "ingest"
    assert closing["agent_statuses"]["ingest"] == AgentRunStatus.ERROR.value
    error = closing["errors"]["ingest"]
    assert error.code == ErrorCode.CONTRACT_VALIDATION_FAILED
    assert error.correlation_id == opening["run_id"]
    assert ".py" not in error.message and "Traceback" not in error.message
    decision = closing["decision"]
    assert decision is not None and decision.decision == Decision.INSUFFICIENT_DATA
    assert decision.entry is None


def test_bogus_evidence_string_fails_gate_node(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Evidence outside the closed enum crashes the gate fatally, never passes."""
    settings = _settings(monkeypatch)
    opening = make_opening(settings)  # type: ignore[arg-type]
    opening["eligible"] = ["trend-following"]
    opening["evidence"] = {"trend-following": "bogus"}

    gate = make_gate_node(settings)  # type: ignore[arg-type]
    update = asyncio.run(gate(opening))

    assert update["fatal"] == "gate"
    assert update["agent_statuses"]["gate"] == AgentRunStatus.ERROR.value


def test_evaluations_are_contract_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Node outputs are Phase 3 contract instances, statuses map the locked table."""
    settings = _settings(monkeypatch)
    graph = build_graph(settings)  # type: ignore[arg-type]
    closing = asyncio.run(run_closing(graph, make_opening(settings)))  # type: ignore[arg-type]

    evaluation = closing["evaluations"]["trend-following"]
    assert isinstance(evaluation, StrategyEvaluation)
    assert evaluation.strategy_id == "trend-following"
    assert evaluation.strategy_version == "1.0.0"
    assert EvidenceStatus(closing["evidence"]["trend-following"]) is EvidenceStatus.VALID


def test_ceo_slot_is_stubbed_with_cause_never_prose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM-shaped synthesis returns unavailable-with-cause; thesis stays factual."""
    settings = _settings(monkeypatch)
    graph = build_graph(settings)  # type: ignore[arg-type]
    closing = asyncio.run(run_closing(graph, make_opening(settings)))  # type: ignore[arg-type]

    decision = closing["decision"]
    assert decision is not None
    assert CEO_STUB_CAUSE in decision.limitations
    assert "gate blocked" in decision.thesis or "passed" in decision.thesis


def test_decision_mapper_rejects_levels_on_non_trade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Assemble-decision keeps non-TRADE records level-free by construction."""
    settings = _settings(monkeypatch)
    graph = build_graph(settings)  # type: ignore[arg-type]
    closing = asyncio.run(run_closing(graph, make_opening(settings)))  # type: ignore[arg-type]

    assert closing["decision"] is not None
    assert closing["decision"].decision in (Decision.NO_TRADE, Decision.INSUFFICIENT_DATA)
    record = assemble_decision(dict(closing))  # type: ignore[arg-type]
    assert record.entry is None and record.stop_loss is None
    assert list(record.take_profits) == [] and record.risk_reward is None
