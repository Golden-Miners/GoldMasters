"""Deterministic scoreless sentiment-evidence assembler (locked D-5.2).

Source statements in, auditable evidence out — never a number. The score,
label, and scoring-method fields stay ``None`` until a versioned scoring
method is approved; only deterministic code may ever populate them, never
raw model text (threat model T-05-04). Model-supplied strings arrive via the
``SentimentExtraction`` evidence/reason shape (evidence text only, no scores)
and are stored verbatim into refs/limitations — never reconciled or rewritten
(threat model T-05-05: every source_ref resolves to a persisted NewsItem).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from goldmasters_contracts.news import NewsItem
from goldmasters_contracts.sentiment import SentimentRecord

__all__ = ["assemble_sentiment", "is_stale"]


def assemble_sentiment(
    items: Sequence[NewsItem],
    *,
    instrument_id: str,
    window_start: datetime,
    window_end: datetime,
    created_at: datetime,
    duplicate_policy: str,
    model_version: str,
    conflicts: Sequence[str] = (),
    limitations: Sequence[str] = (),
    outage_note: str | None = None,
) -> SentimentRecord:
    """Assemble one frozen scoreless SentimentRecord from collapsed coverage.

    ``items`` are post-collapse NewsItems (plan 05-01 output, dedup already
    applied). Counts derive from the items themselves, so they cannot drift
    from the refs. Zero items (plan 05-01 outage) yields a valid zero-count
    record whose limitations state the outage — no evidence is synthesized.
    """
    coverage_count = len(items)
    unique_source_count = len({item.source_id for item in items})
    window_note = (
        f"analysis window {window_start.isoformat()} to {window_end.isoformat()}; "
        "evidence outside this window is stale downstream"
    )
    record_limitations = [window_note, *limitations]
    if outage_note is not None:
        record_limitations.append(outage_note)
    for item in items:
        record_limitations.extend(item.limitations)
    return SentimentRecord(
        instrument_id=instrument_id,
        window_start=window_start,
        window_end=window_end,
        created_at=created_at,
        source_refs=[item.canonical_url for item in items],
        evidence_refs=[item.content_hash or item.canonical_url for item in items],
        coverage_count=coverage_count,
        unique_source_count=unique_source_count,
        duplicate_policy=duplicate_policy,
        label=None,
        score=None,
        scoring_method=None,
        scoring_method_version=None,
        conflicts=list(conflicts),
        limitations=record_limitations,
        model_version=model_version,
    )


def is_stale(record: SentimentRecord, as_of: datetime) -> bool:
    """Stale-window boundary: consumed past window_end means stale evidence.

    The barrier already fails runs closed on non-VALID evidence; a stale
    record must therefore be relabelled (or excluded) before it reaches the
    barrier — this predicate is the single place that boundary is computed.
    """
    return as_of > record.window_end
