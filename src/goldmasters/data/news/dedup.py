"""Deterministic news dedup (criterion 2, RESEARCH section 2).

Policy (recommended rules, pinned here):

1. Exact collapse: equal ``canonical_url`` -> one item, earliest
   ``retrieved_at`` kept, every collapsed retrieval noted in ``limitations``.
2. Near-duplicate collapse: equal non-null ``content_hash`` across different
   URLs (wire re-posts) -> one item, earliest ``retrieved_at`` kept, every
   carrying ``source_id`` listed in ``limitations``.
"""

from __future__ import annotations

from collections.abc import Sequence

from goldmasters_contracts.news import NewsItem

__all__ = ["coverage_counts", "deduplicate"]


def _merge_into(kept: NewsItem, dropped: NewsItem, reason: str) -> NewsItem:
    """Fold one collapsed duplicate's provenance into the kept item."""
    extra = (
        f"{reason}: retrieved_at={dropped.retrieved_at.isoformat()} source_id={dropped.source_id}"
    )
    attributions = [kept.source_attribution]
    if dropped.source_attribution not in attributions:
        attributions.append(dropped.source_attribution)
    return kept.model_copy(
        update={
            "limitations": [*kept.limitations, extra],
            "source_attribution": "; ".join(attributions),
        }
    )


def deduplicate(items: Sequence[NewsItem]) -> list[NewsItem]:
    """Collapse exact + near-duplicate items, preserving attribution."""
    by_url: dict[str, NewsItem] = {}
    for item in items:
        prior = by_url.get(item.canonical_url)
        if prior is None:
            by_url[item.canonical_url] = item
        else:
            kept, dropped = (
                (prior, item) if prior.retrieved_at <= item.retrieved_at else (item, prior)
            )
            by_url[item.canonical_url] = _merge_into(kept, dropped, "duplicate retrieval collapsed")
    by_hash: dict[str, NewsItem] = {}
    collapsed: list[NewsItem] = []
    for item in by_url.values():
        if item.content_hash is None:
            collapsed.append(item)
            continue
        prior = by_hash.get(item.content_hash)
        if prior is None:
            by_hash[item.content_hash] = item
            collapsed.append(item)
        else:
            kept, dropped = (
                (prior, item) if prior.retrieved_at <= item.retrieved_at else (item, prior)
            )
            merged = _merge_into(kept, dropped, f"near-duplicate {item.content_hash} collapsed")
            by_hash[item.content_hash] = merged
            collapsed[collapsed.index(prior)] = merged
    return collapsed


def coverage_counts(items: Sequence[NewsItem]) -> tuple[int, int]:
    """Return (coverage_count, unique_source_count) after collapse."""
    sources = {item.source_id for item in items}
    return (len(items), len(sources))
