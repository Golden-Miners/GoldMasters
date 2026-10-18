"""News retrieval-adapter layer (locked D-5.1)."""

from src.goldmasters.data.news.adapters import register_source as _register_source  # noqa: F401
from src.goldmasters.data.news.base import (
    SOURCE_REGISTRY,
    NewsCoverage,
    NewsSourceAdapter,
    RawNewsPayload,
    canonicalize_url,
    compute_content_hash,
    fetch_coverage,
    link_instruments,
    normalize_payload,
    register_source,
)
from src.goldmasters.data.news.dedup import coverage_counts, deduplicate
from src.goldmasters.data.news.sentiment import assemble_sentiment, is_stale

__all__ = [
    "NewsCoverage",
    "NewsSourceAdapter",
    "RawNewsPayload",
    "SOURCE_REGISTRY",
    "assemble_sentiment",
    "canonicalize_url",
    "compute_content_hash",
    "coverage_counts",
    "deduplicate",
    "fetch_coverage",
    "is_stale",
    "link_instruments",
    "normalize_payload",
    "register_source",
]
