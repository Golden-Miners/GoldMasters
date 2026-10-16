"""Scoreless sentiment-evidence pins (05-02, locked D-5.2).

Criterion 3: window, evidence refs, coverage counts, duplicate policy,
conflicts, limitations, model version — with the score field left
unpopulated until a versioned scoring method is approved.

Fixtures below are test-only NewsItems built directly (no live data, no
model calls); they live in this file, never in ``src/``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from goldmasters_contracts.enums import EvidenceStatus
from goldmasters_contracts.news import NewsItem
from goldmasters_contracts.sentiment import SCORE_MAX, SCORE_MIN, SentimentRecord
from pydantic import ValidationError

from src.goldmasters.data.news.dedup import coverage_counts
from src.goldmasters.data.news.sentiment import assemble_sentiment, is_stale

T1 = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
T2 = datetime(2026, 10, 15, 12, 5, tzinfo=UTC)
W0 = datetime(2026, 10, 15, 11, 0, tzinfo=UTC)
W1 = datetime(2026, 10, 15, 13, 0, tzinfo=UTC)

POLICY = "collapse by canonical_url, then content_hash; earliest retrieved_at kept"
MODEL = "sentiment-assembler-0.1.0"


def _item(
    source: str,
    url: str,
    title: str,
    limitations: list[str] | None = None,
) -> NewsItem:
    return NewsItem(
        source_id=source,
        canonical_url=url,
        title=title,
        published_at=T1,
        retrieved_at=T2,
        content_hash=f"hash-{url}",
        instrument_mappings=[],
        source_attribution=f"{source} attribution",
        access_method="test-double",
        status=EvidenceStatus.VALID,
        limitations=list(limitations or []),
    )


def _three_from_two() -> list[NewsItem]:
    return [
        _item("wire-a", "https://example.com/gold-rally", "Gold holds gains"),
        _item("wire-a", "https://example.com/xau-slip", "XAUUSD slips in thin trade"),
        _item("wire-b", "https://mirror.example/gold-rally", "Gold holds gains"),
    ]


def _assemble(
    items: list[NewsItem],
    conflicts: list[str] | None = None,
    limitations: list[str] | None = None,
    outage_note: str | None = None,
) -> SentimentRecord:
    return assemble_sentiment(
        items,
        instrument_id="XAUUSD",
        window_start=W0,
        window_end=W1,
        created_at=T2,
        duplicate_policy=POLICY,
        model_version=MODEL,
        conflicts=conflicts or [],
        limitations=limitations or [],
        outage_note=outage_note,
    )


def test_tracer_three_items_two_sources_yield_valid_scoreless_record() -> None:
    record = _assemble(_three_from_two())
    assert isinstance(record, SentimentRecord)  # frozen contract validates
    assert record.coverage_count == 3
    assert record.unique_source_count == 2
    assert record.score is None
    assert record.label is None
    assert record.window_start == W0 and record.window_end == W1
    assert record.duplicate_policy == POLICY
    assert record.model_version == MODEL
    # Every contributing item appears in both ref lists (T-05-05 exhaustive).
    assert record.source_refs == [
        "https://example.com/gold-rally",
        "https://example.com/xau-slip",
        "https://mirror.example/gold-rally",
    ]
    assert len(record.evidence_refs) == 3
    count, unique = coverage_counts(_three_from_two())
    assert (record.coverage_count, record.unique_source_count) == (count, unique)


def test_score_absence_gate_rejects_any_populated_score() -> None:
    record = _assemble(_three_from_two())
    assert record.score is None
    assert record.scoring_method is None
    assert record.scoring_method_version is None
    # The frozen contract — not the assembler — rejects out-of-range scores
    # (never clamped) and method-less scores.
    def _with(**overrides: object) -> SentimentRecord:
        return SentimentRecord.model_validate({**record.model_dump(), **overrides})

    with pytest.raises(ValidationError):
        _with(score=SCORE_MAX + 0.5)
    with pytest.raises(ValidationError):
        _with(score=SCORE_MIN - 0.5)
    with pytest.raises(ValidationError):
        _with(score=0.5, scoring_method=None, scoring_method_version=None)


def test_outage_yields_valid_zero_count_record_with_no_synthesized_evidence() -> None:
    record = _assemble([], outage_note="news source stub-wire unreachable: dns failure")
    assert isinstance(record, SentimentRecord)
    assert record.coverage_count == 0
    assert record.unique_source_count == 0
    assert record.source_refs == [] and record.evidence_refs == []
    assert record.score is None
    blob = " ".join(record.limitations)
    assert "unreachable" in blob  # outage stated, nothing invented
    assert "Gold holds gains" not in blob


def test_stale_window_boundary_consumed_past_window_end() -> None:
    record = _assemble(_three_from_two())
    assert not is_stale(record, W1)  # boundary itself is still current
    assert is_stale(record, datetime(2026, 10, 15, 13, 0, 1, tzinfo=UTC))


def test_conflicts_preserved_verbatim_never_reconciled() -> None:
    first = "wire-a: gold holds gains on data hopes"
    second = "wire-b: gold slips in thin trade"
    record = _assemble(_three_from_two(), conflicts=[first, second])
    assert record.conflicts == [first, second]


def test_per_item_caveats_land_in_limitations() -> None:
    items = [
        _item("wire-a", "https://example.com/a", "Gold steady", ["paywall-truncated"]),
        _item("wire-b", "https://example.com/b", "Gold dips", ["machine-translated"]),
    ]
    record = _assemble(items)
    blob = " ".join(record.limitations)
    assert "paywall-truncated" in blob
    assert "machine-translated" in blob
    assert W0.isoformat() in blob and W1.isoformat() in blob  # window self-describing


def test_source_statements_separate_from_model_interpretation() -> None:
    record = _assemble(_three_from_two())
    dump = record.model_dump()
    # Source statements live only in refs; interpretation only in label/score.
    for url in record.source_refs:
        assert url not in (record.label, record.model_version)
    assert set(dump) >= {
        "source_refs",
        "evidence_refs",
        "label",
        "score",
        "model_version",
    }


def test_unique_sources_never_exceed_coverage() -> None:
    for n in (0, 1, 3):
        record = _assemble(_three_from_two()[:n])
        assert record.unique_source_count <= record.coverage_count
