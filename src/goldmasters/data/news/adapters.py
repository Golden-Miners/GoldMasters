"""News retrieval adapters for operator-approved sources (D-5.1).

Each adapter implements :class:`NewsSourceAdapter` and is registered in
``SOURCE_REGISTRY``. Adapters are added only after operator approval of
access method + terms.

No live data is fetched at import time; adapters are instantiated and
fetched on demand by :func:`goldmasters.data.news.base.fetch_coverage`.
"""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from goldmasters_contracts.news import InstrumentMapping

from src.goldmasters.data.news.base import (
    NewsSourceAdapter,
    RawNewsPayload,
    register_source,
    canonicalize_url,
    compute_content_hash,
    link_instruments,
    normalize_payload,
)


class GenericRSSFeedAdapter(NewsSourceAdapter):
    """Generic RSS feed adapter.

    Fetches an RSS feed, parses ``<item>`` elements, and returns
    :class:`RawNewsPayload` objects. Fail-closed: on any fetch or parse
    error, returns an empty list rather than synthesizing data.
    """

    def __init__(
        self,
        source_id: str,
        feed_url: str,
        instrument_mappings: Sequence[InstrumentMapping],
    ) -> None:
        self._source_id = source_id
        self._feed_url = feed_url
        self._instrument_mappings = list(instrument_mappings)

    @property
    def source_id(self) -> str:
        return self._source_id

    async def fetch(self) -> list[RawNewsPayload]:
        """Fetch the RSS feed and return raw payloads."""
        try:
            xml_text = await asyncio.to_thread(self._fetch_xml)
        except Exception:
            return []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []
        items = root.findall(".//item")
        payloads: list[RawNewsPayload] = []
        for item in items:
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            description = item.findtext("description") or ""
            pub_date = item.findtext("pubDate")
            payloads.append(
                RawNewsPayload(
                    source_id=self._source_id,
                    url=link,
                    title=title,
                    body=description,
                    published_at=None,
                    retrieved_at=datetime.now(timezone.utc),
                    source_attribution=self._source_id,
                    access_method=self._feed_url,
                )
            )
        return payloads


def _instrument_mappings(instrument_ids: Sequence[str]) -> list[InstrumentMapping]:
    """Build instrument mappings from a list of canonical instrument IDs."""
    return [
        InstrumentMapping(
            instrument_id=instrument_id,
            rationale=f"keyword match on {instrument_id.lower()} in source headline/body",
            confidence_method="keyword match (deterministic, unversioned)",
        )
        for instrument_id in instrument_ids
    ]


# ---------------------------------------------------------------------------
# Operator-approved news sources (D-5.1)
#
# Each entry: source_id, feed_url, instrument_ids
# Sources are registered only after operator approval of access method + terms.
# ---------------------------------------------------------------------------

REGISTERED_SOURCES: list[tuple[str, str, list[str]]] = [
    (
        "reuters_markets",
        "https://www.reuters.com/commodities/rss",
        ["XAUUSD", "XAGUSD"],
    ),
    (
        "coindesk",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        ["BTCUSD", "ETHUSD"],
    ),
    (
        "federal_reserve",
        "https://www.federalreserve.gov/feeds/feeds.htm",
        ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD", "USOUSD"],
    ),
    (
        "ecb",
        "https://www.ecb.europa.eu/home/html/rss.en.html",
        ["EURUSD", "EURGBP", "EURJPY", "XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD"],
    ),
    (
        "bls",
        "https://www.bls.gov/help/hlp_rss.htm",
        ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD", "USOUSD"],
    ),
    (
        "eia",
        "https://www.eia.gov/tools/rssfeeds/",
        ["USOUSD", "XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY"],
    ),
    (
        "cftc",
        "https://www.cftc.gov/RSS/index.htm",
        ["XAUUSD", "XAGUSD", "USOUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"],
    ),
    (
        "fxstreet",
        "https://www.fxstreet.com/",
        ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"],
    ),
]


def _build_adapter(
    source_id: str, feed_url: str, instrument_ids: Sequence[str]
) -> NewsSourceAdapter:
    return GenericRSSFeedAdapter(
        source_id=source_id,
        feed_url=feed_url,
        instrument_mappings=_instrument_mappings(instrument_ids),
    )


# Register each approved source.
for _source_id, _feed_url, _instrument_ids in REGISTERED_SOURCES:
    register_source(
        _source_id,
        _build_adapter(_source_id, _feed_url, _instrument_ids),
    )
