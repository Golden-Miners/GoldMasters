"""Graph state slice: one end-to-end deterministic run (tracer, D-4.1).

Proves the bounded path input → gate → terminal decision against real
Phase 3 code with zero model dependency, and pins the D-4.3 minimal run log.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from goldmasters_api.settings import hash_effective_config
from goldmasters_contracts import AgentRunStatus, Decision
from pydantic import ValidationError

from src.goldmasters.graph.builder import build_graph, initial_state
from src.goldmasters.graph.state import MINIMAL_LOG_KEYS, RunState, run_log
from tests.unit.agent_fixtures import bars_from_closes, make_ctx
from tests.unit.graph_fixtures import (
    AGENT_01_NUMERICS,
    AGENT_01_SCOPE,
    FIXTURE_FLAT_CLOSES,
    FIXTURE_SETUP_CLOSES,
    OPEN_RISK,
    apply_clean_env,
    make_opening,
    make_settings,
    run_closing,
)


def _graph(monkeypatch: pytest.MonkeyPatch) -> object:
    apply_clean_env(monkeypatch)
    return build_graph(make_settings(**AGENT_01_SCOPE, **AGENT_01_NUMERICS, **OPEN_RISK))


def test_setup_candidate_runs_end_to_end_to_no_trade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Agent-01 setup → gate blocks on uncomputed idea risk → terminal NO_TRADE."""
    graph = _graph(monkeypatch)
    settings = make_settings(**AGENT_01_SCOPE, **AGENT_01_NUMERICS, **OPEN_RISK)
    closing = asyncio.run(run_closing(graph, make_opening(settings)))

    assert closing["fatal"] is None
    assert closing["barrier_passed"] is True
    verdict = closing["gate_verdict"]
    assert verdict is not None and not verdict.passed
    assert any("idea risk unknown" in reason for reason in verdict.reasons_for_rejection)
    assert list(verdict.conflicts) == closing["conflicts"]  # verbatim preservation
    decision = closing["decision"]
    assert decision is not None
    assert decision.decision == Decision.NO_TRADE
    assert decision.entry is None  # non-TRADE carries no levels, validator-enforced
    assert decision.manual_review_required is True
    assert closing["agent_statuses"]["trend-following"] == AgentRunStatus.OK.value


def test_flat_bars_run_end_to_end_to_no_trade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chop bars → no setup from any eligible agent → terminal NO_TRADE."""
    apply_clean_env(monkeypatch)
    settings = make_settings(**AGENT_01_SCOPE, **AGENT_01_NUMERICS, **OPEN_RISK)
    graph = build_graph(settings)
    closing = asyncio.run(
        run_closing(graph, make_opening(settings, closes=FIXTURE_FLAT_CLOSES))
    )

    assert closing["fatal"] is None
    assert closing["barrier_passed"] is True
    assert closing["agent_statuses"]["trend-following"] == AgentRunStatus.NO_SETUP.value
    decision = closing["decision"]
    assert decision is not None and decision.decision == Decision.NO_TRADE
    assert any("no setup" in reason for reason in decision.reasons_for_rejection)


def test_run_log_is_minimal_and_pinned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-4.3: the log carries ids, timestamps and per-node status — nothing else."""
    graph = _graph(monkeypatch)
    settings = make_settings(**AGENT_01_SCOPE, **AGENT_01_NUMERICS, **OPEN_RISK)
    closing = asyncio.run(run_closing(graph, make_opening(settings)))

    log = run_log(closing)
    assert set(log) == set(MINIMAL_LOG_KEYS)
    assert log["run_id"] == closing["run_id"]
    assert log["input_ref"] == closing["input_ref"]
    assert log["config_hash"] == hash_effective_config(settings)
    assert len(log["code_versions"]) == 10
    for node, status in log["node_statuses"].items():
        AgentRunStatus(status)  # verbatim members only, no magic strings
        assert node in log["node_times"]


def test_initial_state_validates_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed input fails at assembly (caller error), deterministically hashed."""
    apply_clean_env(monkeypatch)
    settings = make_settings()
    run_id = f"run_{uuid.uuid4()}"
    bars = bars_from_closes(FIXTURE_SETUP_CLOSES)
    ctx = make_ctx()

    opening = initial_state(run_id=run_id, bars=bars, ctx=ctx, settings=settings)
    assert opening["config_hash"] == hash_effective_config(settings)
    assert len(opening["code_versions"]) == 10
    reopened: RunState = initial_state(
        run_id=f"run_{uuid.uuid4()}", bars=bars, ctx=ctx, settings=settings
    )
    assert reopened["input_ref"] == opening["input_ref"]  # snapshot hash is stable

    with pytest.raises(ValidationError):
        initial_state(run_id=f"run_{uuid.uuid4()}", bars=[{"nope": 1}], ctx=ctx, settings=settings)  # type: ignore[list-item]
    with pytest.raises(ValidationError):
        initial_state(run_id="not-a-uuid", bars=bars, ctx=ctx, settings=settings)
