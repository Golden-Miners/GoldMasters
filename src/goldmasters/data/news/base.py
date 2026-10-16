"""News retrieval-adapter interface (locked D-5.1).

One async fetch method per source behind the :class:`NewsSourceAdapter`
protocol, plus the empty operator-gated registry. No live source is wired:
entries appear here only after operator approval of access method + terms.

Security notes (threat model T-05-01..T-05-03):

- Titles/bodies cross the source-feed boundary untrusted and are stored
  verbatim into :class:`NewsItem` — never rewritten, executed, or "cleaned".
- ``source_attribution`` + ``access_method`` are the per-source terms audit
  trail; store/republish only within those terms.
- Identity derives from the single pinned canonicalization rule below;
  dedup keys come from canonical form only, never the raw URL.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from goldmasters_contracts.enums import EvidenceStatus
from goldmasters_contracts.news import InstrumentMapping, NewsItem

__all__ = [
    "NewsCoverage",
    "NewsSourceAdapter",
    "RawNewsPayload",
    "SOURCE_REGISTRY",
    "canonicalize_url",
    "compute_content_hash",
    "fetch_coverage",
    "link_instruments",
    "normalize_payload",
    "register_source",
]

#: Query params stripped by canonicalization: analytics/click trackers carry
#: no identity, so two URLs differing only by these are the same article.
#: Pinned rule (D-5.1): lowercase scheme/host, drop these params, drop the
#: single trailing slash (except the root path, which keeps exactly "/").
_TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "fbclid",
        "gclid",
        "msclkid",
        "mc_cid",
        "mc_eid",
        "ref",
        "referrer",
    }
)

#: Keywords linking a payload to XAUUSD. Deliberately narrow: a missed link
#: only drops an instrument mapping, while a loose link fabricates evidence.
_XAU_KEYWORDS = frozenset({"gold", "xauusd", "xau"})


def canonicalize_url(url: str) -> str:
    """Pin the single canonical URL rule: lower scheme/host, strip trackers.

    Trailing-slash rule: exactly one trailing slash is removed, except the
    root path which normalizes to "/". Query params in ``_TRACKING_PARAMS``
    (plus any ``utm_*``) are dropped; the rest keep first-seen order.
    """
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = parts.hostname.lower() if parts.hostname else ""
    if parts.port:
        host = f"{host}:{parts.port}"
    netloc = host
    if parts.username:
        auth = parts.username
        if parts.password:
            auth = f"{auth}:{parts.password}"
        netloc = f"{auth}@{host}"
    path = parts.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")
    query = urlencode(
        [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k.lower() not in _TRACKING_PARAMS and not k.lower().startswith("utm_")
        ]
    )
    return urlunsplit((scheme, netloc, path, query, ""))


def compute_content_hash(canonical_url: str, title: str, body: str) -> str:
    """Hash canonical_url + title + body: dedup key #2 for cross-URL reposts."""
    digest = hashlib.sha256()
    digest.update(canonical_url.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(title.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(body.encode("utf-8"))
    return digest.hexdigest()


@dataclass(frozen=True)
class RawNewsPayload:
    """Untrusted pre-contract payload from one source fetch.

    ``published_at`` is the verbatim source timestamp, ``None`` when the
    source timestamp is missing or unreliable — never backfilled from
    ``retrieved_at``. ``retrieved_at`` is the adapter clock at fetch.
    """

    source_id: str
    url: str
    title: str
    body: str
    published_at: datetime | None
    retrieved_at: datetime
    source_attribution: str
    access_method: str


class NewsSourceAdapter(Protocol):
    """One async fetch per approved source; raw payloads out, nothing else."""

    @property
    def source_id(self) -> str:
        """Stable per-source identifier (registry key)."""
        ...

    async def fetch(self) -> list[RawNewsPayload]:
        """Return raw source payloads; raise or return [] on outage."""
        ...


#: Operator-gated registry: source_id -> adapter class. Ships EMPTY (D-5.1);
#: entries are added only after operator approves access method + terms.
SOURCE_REGISTRY: dict[str, type[NewsSourceAdapter]] = {}


def register_source(source_id: str, adapter_cls: type[NewsSourceAdapter]) -> None:
    """Add one operator-approved source to the registry."""
    SOURCE_REGISTRY[source_id] = adapter_cls


def link_instruments(title: str, body: str) -> list[InstrumentMapping]:
    """Keyword link to XAUUSD; the frozen contract needs rationale + method."""
    haystack = f"{title}\n{body}".lower()
    hits = sorted(kw for kw in _XAU_KEYWORDS if kw in haystack)
    if not hits:
        return []
    return [
        InstrumentMapping(
            instrument_id="XAUUSD",
            rationale=f"keyword match on {', '.join(hits)} in source headline/body",
            confidence_method="keyword match (deterministic, unversioned)",
        )
    ]


def normalize_payload(payload: RawNewsPayload) -> NewsItem:
    """Build a frozen NewsItem: verbatim title, verbatim published_at."""
    canonical = canonicalize_url(payload.url)
    return NewsItem(
        source_id=payload.source_id,
        canonical_url=canonical,
        title=payload.title,
        published_at=payload.published_at,
        retrieved_at=payload.retrieved_at,
        content_hash=compute_content_hash(canonical, payload.title, payload.body),
        instrument_mappings=link_instruments(payload.title, payload.body),
        source_attribution=payload.source_attribution,
        access_method=payload.access_method,
        status=EvidenceStatus.VALID,
        limitations=[],
    )


@dataclass(frozen=True)
class NewsCoverage:
    """One fetch outcome: items on success, empty + unavailable on outage."""

    status: EvidenceStatus
    items: tuple[NewsItem, ...] = ()
    limitations: tuple[str, ...] = ()


async def fetch_coverage(adapter: NewsSourceAdapter) -> NewsCoverage:
    """Fail-closed fetch (D-5.1): outage yields unavailable, zero items.

    No headline or sentiment is ever synthesized here — an unreachable or
    empty source produces status + limitations text only.
    """
    try:
        payloads = await adapter.fetch()
    except Exception as exc:  # noqa: BLE001 -- outage is fail-closed by design (D-5.1)
        return NewsCoverage(
            status=EvidenceStatus.UNAVAILABLE,
            limitations=(f"news source {adapter.source_id} unreachable: {exc}",),
        )
    if not payloads:
        return NewsCoverage(
            status=EvidenceStatus.UNAVAILABLE,
            limitations=(
                f"news source {adapter.source_id} returned no payloads; coverage unavailable",
            ),
        )
    return NewsCoverage(
        status=EvidenceStatus.VALID,
        items=tuple(normalize_payload(p) for p in payloads),
    )
