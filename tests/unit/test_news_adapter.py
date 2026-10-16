"""News adapter tracer (05-01): stub fetch, outage path, dedup pins.

The stub adapter is a test-only double — it lives in this file, never in
``src/`` (no mock data outside tests, per AGENTS.md).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from goldmasters_contracts.enums import EvidenceStatus

from src.goldmasters.data.news.base import (
    SOURCE_REGISTRY,
    NewsCoverage,
    RawNewsPayload,
    canonicalize_url,
    fetch_coverage,
)
from src.goldmasters.data.news.dedup import coverage_counts, deduplicate

T1 = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
T2 = datetime(2026, 10, 15, 12, 5, tzinfo=UTC)

TITLE_A = "Gold holds gains as traders eye data"
TITLE_B = "XAUUSD slips in thin trade"


class StubAdapter:
    """Test-only double returning two fixed raw payloads."""

    source_id = "stub-wire"

    async def fetch(self) -> list[RawNewsPayload]:
        return [
            RawNewsPayload(
                source_id=self.source_id,
                url="https://Example.COM/news/gold-rally?utm_source=rss&x=1",
                title=TITLE_A,
                body="Gold futures held gains.",
                published_at=T1,
                retrieved_at=T2,
                source_attribution="Stub Wire",
                access_method="test-double",
            ),
            RawNewsPayload(
                source_id=self.source_id,
                url="https://example.com/news/xau-slip",
                title=TITLE_B,
                body="Spot slipped.",
                published_at=None,  # unreliable timestamp: stays None
                retrieved_at=T2,
                source_attribution="Stub Wire",
                access_method="test-double",
            ),
        ]


class RaisingAdapter:
    source_id = "stub-dead"

    async def fetch(self) -> list[RawNewsPayload]:
        raise ConnectionError("dns failure")


class EmptyAdapter:
    source_id = "stub-empty"

    async def fetch(self) -> list[RawNewsPayload]:
        return []


def test_tracer_stub_fetch_yields_two_valid_items() -> None:
    coverage = asyncio.run(fetch_coverage(StubAdapter()))
    assert coverage.status is EvidenceStatus.VALID
    assert len(coverage.items) == 2
    first, second = coverage.items
    # Criterion 1: every attribution field populated, title verbatim.
    assert first.title == TITLE_A
    assert first.canonical_url == "https://example.com/news/gold-rally?x=1"
    assert first.source_id == "stub-wire"
    assert first.source_attribution == "Stub Wire"
    assert first.access_method == "test-double"
    assert first.content_hash is not None
    # published_at passes through verbatim, including None (never a fallback).
    assert first.published_at == T1
    assert second.title == TITLE_B
    assert second.published_at is None
    assert second.retrieved_at == T2
    # Contract-required mapping strings name the linking method.
    assert first.instrument_mappings
    for mapping in first.instrument_mappings:
        assert mapping.rationale
        assert "keyword match" in mapping.confidence_method


def test_registry_ships_empty_pending_operator_approval() -> None:
    assert SOURCE_REGISTRY == {}


def test_canonicalization_pins_tracking_and_case_rules() -> None:
    assert (
        canonicalize_url("HTTPS://Example.COM/a/?utm_medium=x&b=2&utm_source=y")
        == "https://example.com/a?b=2"
    )
    assert canonicalize_url("https://example.com/a/") == "https://example.com/a"
    assert canonicalize_url("https://example.com") == "https://example.com/"


def test_outage_yields_unavailable_with_no_synthesized_content() -> None:
    for adapter in (RaisingAdapter(), EmptyAdapter()):
        coverage: NewsCoverage = asyncio.run(fetch_coverage(adapter))  # type: ignore[arg-type]
        assert coverage.status is EvidenceStatus.UNAVAILABLE
        assert coverage.items == ()
        assert coverage.limitations, "outage cause must be stated"
        blob = " ".join(coverage.limitations)
        assert TITLE_A not in blob and TITLE_B not in blob
        assert "sentiment" not in blob.lower()


def test_dedup_collapses_with_attribution_preserved() -> None:
    coverage = asyncio.run(fetch_coverage(StubAdapter()))
    first = coverage.items[0]
    dup = first.model_copy(
        update={
            "retrieved_at": T2 + timedelta(minutes=1),
            "source_attribution": "Second Wire",
        }
    )
    collapsed = deduplicate([first, dup])
    assert len(collapsed) == 1
    kept = collapsed[0]
    assert kept.retrieved_at == T2  # earliest wins
    assert "Second Wire" in kept.source_attribution
    assert kept.limitations, "collapsed retrieval must be noted"


def test_near_duplicate_repost_collapses_across_urls() -> None:
    coverage = asyncio.run(fetch_coverage(StubAdapter()))
    first, second = coverage.items
    repost = second.model_copy(
        update={
            "canonical_url": "https://mirror.example/repost-xau",
            "content_hash": first.content_hash,
            "source_id": "stub-mirror",
        }
    )
    collapsed = deduplicate([first, repost])
    assert len(collapsed) == 1
    assert "stub-mirror" in collapsed[0].limitations[-1]
    count, unique = coverage_counts(collapsed)
    assert (count, unique) == (1, 1)
    assert unique <= count


def test_published_at_never_replaced_by_retrieved_at() -> None:
    coverage = asyncio.run(fetch_coverage(StubAdapter()))
    collapsed = deduplicate(list(coverage.items))
    by_title = {item.title: item for item in collapsed}
    assert by_title[TITLE_B].published_at is None
    assert by_title[TITLE_B].retrieved_at == T2
