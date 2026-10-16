"""CEO decision contract: roles as graph nodes, TRADE conjunction, traceability.

Tracer: one bounded news-sentiment role node through the pre-CEO barrier to
the terminal decision. Then all four roles as graph nodes plus the
TRADE-eligibility conjunction: every conjunct independently forces non-TRADE
with null levels. Spine semantics (``check_barrier``,
``check_ceo_required``, ``assemble_decision``) unchanged throughout.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from goldmasters_contracts import (
    AgentRunStatus,
    Decision,
    DecisionRecord,
    EvidenceStatus,
    NewsItem,
)
from pydantic import ValidationError

if TYPE_CHECKING:
    from ollama import ChatResponse

from src.goldmasters.data.news.base import NewsCoverage
from src.goldmasters.graph.barriers import check_barrier, check_ceo_required
from src.goldmasters.graph.builder import build_graph
from src.goldmasters.graph.nodes import assemble_decision
from src.goldmasters.graph.role_nodes import (
    ANALYST_NODE,
    CEO_NODE,
    NEWS_SENTIMENT_NODE,
    RESEARCH_NODE,
    RoleOptions,
)
from src.goldmasters.graph.traceability import log_traceability, report_for_state
from src.goldmasters.risk.gate import trade_eligible_levels
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


class _StubChat:
    """Test-only chat stub: scripted contents, records every call."""

    def __init__(self, script: list[str]) -> None:
        self._script = script
        self.calls: list[dict[str, object]] = []

    async def chat(self, **kwargs: object) -> ChatResponse:
        from ollama import ChatResponse

        self.calls.append(kwargs)
        return ChatResponse(
            message={
                "role": "assistant",
                "content": self._script[min(len(self.calls) - 1, len(self._script) - 1)],
            }
        )


def _news_item() -> NewsItem:
    return NewsItem(
        source_id="wire",
        canonical_url="https://example.invalid/n/1",
        title="Gold steady",
        published_at=None,
        retrieved_at=datetime.now(UTC),
        source_attribution="fixture wire",
        access_method="fixture",
        status=EvidenceStatus.VALID,
    )


def _assert_null_levels(decision: DecisionRecord) -> None:
    """Non-TRADE carries no levels, ever (contract validator pins this)."""
    assert decision.decision != Decision.TRADE
    assert decision.entry is None
    assert decision.stop_loss is None
    assert decision.take_profits == []
    assert decision.risk_reward is None
    assert decision.manual_review_required is True


def test_news_role_failure_blocks_ceo_and_yields_non_trade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failed news node: CEO blocked (no model), barrier breached, null levels."""
    settings = _open(monkeypatch)
    outage = NewsCoverage(
        status=EvidenceStatus.UNAVAILABLE,
        limitations=("news source fixture unreachable: connection refused",),
    )
    graph = build_graph(settings, roles=RoleOptions(news_coverage_fn=lambda _state: outage))
    closing = asyncio.run(run_closing(graph, make_opening(settings)))

    assert closing["agent_statuses"][NEWS_SENTIMENT_NODE] == "insufficient_data"
    assert closing["evidence"][NEWS_SENTIMENT_NODE] == EvidenceStatus.UNAVAILABLE.value

    required = frozenset({NEWS_SENTIMENT_NODE})
    reasons = check_ceo_required(closing["agent_statuses"], required)
    assert reasons == [
        f"ceo blocked: required node {NEWS_SENTIMENT_NODE} is insufficient_data, not ok"
    ]

    assert closing["barrier_passed"] is False
    assert any(NEWS_SENTIMENT_NODE in reason for reason in closing["barrier_reasons"])

    decision = closing["decision"]
    assert decision is not None
    assert decision.decision == Decision.INSUFFICIENT_DATA
    _assert_null_levels(decision)


def test_analyst_parse_failure_forces_non_trade_without_ceo_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Garbage analyst output: INVALID evidence, breach, CEO never consulted."""
    settings = _open(monkeypatch)
    analyst_chat = _StubChat(["not json at all"])
    ceo_chat = _StubChat(['{"thesis": "t", "invalidation": "i"}'])
    graph = build_graph(
        settings,
        roles=RoleOptions(analyst_chat=analyst_chat, analyst_model="fake-model", ceo_chat=ceo_chat),
    )
    closing = asyncio.run(run_closing(graph, make_opening(settings)))

    assert closing["agent_statuses"][ANALYST_NODE] == "insufficient_data"
    assert closing["evidence"][ANALYST_NODE] == EvidenceStatus.INVALID.value
    assert len(analyst_chat.calls) == 1 + settings.graph_node_max_retries  # bounded, then closed

    reasons = check_ceo_required(closing["agent_statuses"], frozenset({ANALYST_NODE}))
    assert reasons == [f"ceo blocked: required node {ANALYST_NODE} is insufficient_data, not ok"]
    assert ceo_chat.calls == []  # the model was never consulted
    assert closing["agent_statuses"][CEO_NODE] == "insufficient_data"

    assert closing["barrier_passed"] is False
    decision = closing["decision"]
    assert decision is not None
    assert decision.decision == Decision.INSUFFICIENT_DATA
    _assert_null_levels(decision)


def test_all_roles_ok_ceo_prose_called_levels_still_from_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy role path: every node ok, CEO drafts text, levels stay gate-owned."""
    settings = _open(monkeypatch)
    coverage = NewsCoverage(status=EvidenceStatus.VALID, items=(_news_item(),))
    analyst_chat = _StubChat(['{"evidence": "bars rose", "reason": "higher closes"}'])
    news_chat = _StubChat(['{"evidence": "steady tone", "reason": "no shock words"}'])
    research_chat = _StubChat(
        ['{"evidence": "cite A", "reason": "matches", "sources": ["https://a.invalid"]}']
    )
    ceo_chat = _StubChat(['{"thesis": "wait", "invalidation": "a close above x"}'])
    graph = build_graph(
        settings,
        roles=RoleOptions(
            news_coverage_fn=lambda _state: coverage,
            news_chat=news_chat,
            news_model="fake-model",
            analyst_chat=analyst_chat,
            analyst_model="fake-model",
            research_question="Is gold up?",
            research_sources_fn=lambda _state: ["https://example.invalid/s"],
            research_chat=research_chat,
            research_model="fake-model",
            ceo_chat=ceo_chat,
            ceo_model="fake-model",
        ),
    )
    closing = asyncio.run(run_closing(graph, make_opening(settings)))

    for node in (ANALYST_NODE, NEWS_SENTIMENT_NODE, RESEARCH_NODE, CEO_NODE):
        assert closing["agent_statuses"][node] == AgentRunStatus.OK.value, node
    assert len(ceo_chat.calls) == 1  # agreement held, exactly one draft
    assert closing["barrier_passed"] is True

    # The gate blocks on Wave-1 "idea risk unknown", so the wired run ends
    # NO_TRADE with nulls: CEO prose touched no level, the gate owns them.
    decision = closing["decision"]
    assert decision is not None
    assert decision.decision == Decision.NO_TRADE
    _assert_null_levels(decision)


def test_conjunction_barrier_breach_forces_non_trade(monkeypatch: pytest.MonkeyPatch) -> None:
    """Conjunct 1: barrier not passed → INSUFFICIENT_DATA, never TRADE."""
    settings = _open(monkeypatch)
    closing = asyncio.run(run_closing(build_graph(settings), make_opening(settings)))

    tampered = dict(closing)
    tampered["barrier_passed"] = False
    tampered["barrier_reasons"] = ["evidence not valid: trend-following"]
    decision = assemble_decision(tampered)  # type: ignore[arg-type]
    assert decision.decision == Decision.INSUFFICIENT_DATA
    _assert_null_levels(decision)


def test_conjunction_gate_levels_null_forces_non_trade(monkeypatch: pytest.MonkeyPatch) -> None:
    """Conjunct 2: verdict absent, or present-but-blocking, yields null levels."""
    settings = _open(monkeypatch)
    closing = asyncio.run(run_closing(build_graph(settings), make_opening(settings)))

    assert closing["gate_verdict"] is not None
    assert trade_eligible_levels(closing["gate_verdict"]) is None  # blocked: no levels

    tampered = dict(closing)
    tampered["gate_verdict"] = None
    decision = assemble_decision(tampered)  # type: ignore[arg-type]
    assert decision.decision == Decision.INSUFFICIENT_DATA
    _assert_null_levels(decision)

    # The untampered closing itself is the blocked-verdict case: complete
    # evidence, gate blocked → NO_TRADE with nulls.
    assert closing["decision"] is not None
    assert closing["decision"].decision == Decision.NO_TRADE
    _assert_null_levels(closing["decision"])


def test_conjunction_stale_evidence_forces_non_trade(monkeypatch: pytest.MonkeyPatch) -> None:
    """Conjunct 5: stale (or any non-VALID) evidence breaches to non-TRADE."""
    settings = _open(monkeypatch)
    closing = asyncio.run(run_closing(build_graph(settings), make_opening(settings)))

    sid = closing["eligible"][0]
    tampered = dict(closing)
    tampered["evidence"] = {**closing["evidence"], sid: EvidenceStatus.STALE.value}
    reasons = check_barrier(tampered)  # type: ignore[arg-type]
    assert any(sid in reason for reason in reasons)

    decision = assemble_decision(tampered)  # type: ignore[arg-type]
    assert decision.decision == Decision.INSUFFICIENT_DATA
    _assert_null_levels(decision)


def test_conjunction_invalid_record_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Conjunct 4: the DecisionRecord validator rejects non-contract records."""
    settings = _open(monkeypatch)
    closing = asyncio.run(run_closing(build_graph(settings), make_opening(settings)))
    assert closing["decision"] is not None
    payload = closing["decision"].model_dump()

    with pytest.raises(ValidationError, match="manual_review_required must be true"):
        DecisionRecord.model_validate({**payload, "manual_review_required": False})

    with pytest.raises(ValidationError, match="a TRADE decision must carry"):
        DecisionRecord.model_validate(
            {**payload, "decision": Decision.TRADE, "decision_id": f"dec_{uuid.uuid4().hex}"}
        )


def test_traceability_percent_counts_only_complete_refs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Criterion 5: measured from refs plus config/version metadata, no target."""
    settings = _open(monkeypatch)
    closing = asyncio.run(run_closing(build_graph(settings), make_opening(settings)))
    assert closing["decision"] is not None
    decision = closing["decision"]
    assert decision.evidence_refs  # the wired run stamps refs from state evidence

    envelopes = {ref: object() for ref in decision.evidence_refs}
    report = report_for_state([decision], envelopes, closing)
    assert (report.total, report.complete, report.percent) == (1, 1, 100.0)
    assert report.incomplete_ids == ()
    assert report.agent_versions == {
        "market_analyst": "0.1.0",
        "news_sentiment": "0.1.0",
        "research": "0.1.0",
        "ceo": "0.1.0",
    }

    ghost = decision.model_copy(
        update={
            "decision_id": f"dec_{uuid.uuid4().hex}",
            "evidence_refs": [*decision.evidence_refs, "ghost-envelope"],
        }
    )
    mixed = report_for_state([decision, ghost], envelopes, closing)
    assert (mixed.total, mixed.complete, mixed.percent) == (2, 1, 50.0)
    assert mixed.incomplete_ids == (ghost.decision_id,)

    line = log_traceability(mixed)
    assert "1/2 complete (50.0%)" in line
    assert ghost.decision_id in line
    with caplog.at_level("INFO", logger="src.goldmasters.graph.traceability"):
        assert log_traceability(mixed) == line
    assert line in caplog.text  # operator-visible via the log, no target set

    # Missing run metadata also counts as incomplete, refs resolving or not.
    unmeta = report_for_state([decision], envelopes, {**closing, "config_hash": ""})  # type: ignore[typeddict-item]
    assert (unmeta.total, unmeta.complete, unmeta.percent) == (1, 0, 0.0)
