"""CEO decision contract: roles as graph nodes, TRADE conjunction, traceability.

Tracer first: one bounded news-sentiment role node through the pre-CEO
barrier to the terminal decision. A failed role node blocks CEO prose with
no model call and ends non-TRADE with null levels — spine semantics
(``check_barrier``, ``check_ceo_required``, ``assemble_decision``) unchanged.
"""

from __future__ import annotations

import asyncio

from goldmasters_contracts import Decision, EvidenceStatus

from src.goldmasters.data.news.base import NewsCoverage
from src.goldmasters.graph.barriers import check_ceo_required
from src.goldmasters.graph.builder import build_graph
from src.goldmasters.graph.role_nodes import NEWS_SENTIMENT_NODE
from tests.unit.graph_fixtures import (
    AGENT_01_NUMERICS,
    AGENT_01_SCOPE,
    OPEN_RISK,
    apply_clean_env,
    make_opening,
    make_settings,
    run_closing,
)


def _open(monkeypatch: object) -> object:
    apply_clean_env(monkeypatch)  # type: ignore[arg-type]
    return make_settings(**AGENT_01_SCOPE, **AGENT_01_NUMERICS, **OPEN_RISK)  # type: ignore[arg-type]


def test_news_role_failure_blocks_ceo_and_yields_non_trade(monkeypatch: object) -> None:
    """Failed news node: CEO blocked (no model), barrier breached, null levels."""
    settings = _open(monkeypatch)
    outage = NewsCoverage(
        status=EvidenceStatus.UNAVAILABLE,
        limitations=("news source fixture unreachable: connection refused",),
    )
    graph = build_graph(settings, news_coverage_fn=lambda _state: outage)  # type: ignore[arg-type]
    closing = asyncio.run(run_closing(graph, make_opening(settings)))  # type: ignore[arg-type]

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
    assert decision.entry is None
    assert decision.stop_loss is None
    assert decision.take_profits == []
    assert decision.risk_reward is None
    assert decision.manual_review_required is True
