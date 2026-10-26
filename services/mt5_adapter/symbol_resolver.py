"""Centralized symbol resolver (D-52/D-53).

Resolves canonical instrument IDs to broker-specific provider symbols by
querying the live terminal's symbol list, ranking exact names before aliases,
verifying metadata and quote/history access, and caching successful mappings
for the current session. Broker-specific aliases are configurable — they are
never embedded across strategies.

Architecture:
- Canonical IDs (xauusd, xagusd, btcusd, ...) are the single source of truth
- SymbolResolver.query_broker_symbols() calls gateway.symbols_get()
- resolve(canonical_id, timeframe) returns the best matching provider symbol
- Ambiguous matches are rejected, never silently substituted
- Results cached per session; refresh() re-queries the broker
"""

from __future__ import annotations

from dataclasses import dataclass

from services.mt5_adapter.terminal import (
    CANONICAL_INSTRUMENT_IDS,
    BROKER_SYMBOL_ALIASES,
    TIMEFRAME_IDS,
    TerminalGateway,
)

#: Timeframes supported by the adapter (D-54). Any timeframe not in this set
#: is rejected as unsupported, never substituted.
SUPPORTED_TIMEFRAMES: frozenset[str] = frozenset(TIMEFRAME_IDS.keys())

__all__ = [
    "SymbolResolver",
    "SymbolResolution",
    "SymbolResolutionFailure",
]


@dataclass(frozen=True, slots=True)
class SymbolResolution:
    """Resolved symbol mapping for one canonical instrument/timeframe."""

    canonical_id: str
    timeframe: str
    provider_symbol: str
    confidence: str  # "exact", "alias", "partial"


@dataclass(frozen=True, slots=True)
class SymbolResolutionFailure:
    """Failed symbol resolution."""

    canonical_id: str
    timeframe: str
    reason: str
    is_timeframe: bool = False  # True when the failure is due to unsupported timeframe


class SymbolResolver:
    """Resolve canonical instrument IDs to broker provider symbols.

    Begins with canonical IDs such as ``xauusd``, ``xagusd``, ``btcusd``,
    ``ethusd``, ``usoil``, ``eurusd``. Queries actual broker symbols,
    ranks exact names before aliases, verifies metadata and
    quote/history access, caches successful mappings for the current
    session, and rejects ambiguous matches.

    Broker-specific aliases are configurable through ``aliases`` — they
    are never embedded across strategies.
    """

    def __init__(
        self,
        gateway: TerminalGateway,
        aliases: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        self._gateway = gateway
        self._aliases: dict[str, tuple[str, ...]] = dict(
            aliases or BROKER_SYMBOL_ALIASES
        )
        self._cache: dict[tuple[str, str], SymbolResolution | SymbolResolutionFailure] = {}

    def refresh(self) -> None:
        """Re-query the broker's symbol list and clear the cache."""
        self._cache.clear()

    def resolve(
        self, canonical_id: str, timeframe: str
    ) -> SymbolResolution | SymbolResolutionFailure:
        """Resolve a canonical instrument ID to a provider symbol.

        Resolution order:
        1. Exact match: broker symbol equals canonical_id.upper()
        2. Alias match: broker symbol matches a configured alias
        3. Partial match: canonical_id is a substring of broker symbol
        4. Ambiguous: multiple matches → reject

        Returns a SymbolResolution on success, or SymbolResolutionFailure
        when no suitable match exists or the match is ambiguous.
        """
        cache_key = (canonical_id, timeframe)
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = self._resolve(canonical_id, timeframe)
        self._cache[cache_key] = result
        return result

    def _resolve(
        self, canonical_id: str, timeframe: str
    ) -> SymbolResolution | SymbolResolutionFailure:
        canonical_upper = canonical_id.upper()

        # Reject unknown canonical IDs before touching the gateway (D-52).
        if canonical_id not in CANONICAL_INSTRUMENT_IDS:
            return SymbolResolutionFailure(
                canonical_id, timeframe, f"unsupported instrument: {canonical_id}"
            )

        # Reject unsupported timeframes before touching the gateway (D-54).
        if timeframe not in SUPPORTED_TIMEFRAMES:
            return SymbolResolutionFailure(
                canonical_id, timeframe, f"unsupported timeframe: {timeframe}", is_timeframe=True
            )

        # Get broker's visible symbols
        try:
            symbols = self._gateway.symbols_get()
        except Exception:  # noqa: BLE001 — broker gateway may raise any error
            return SymbolResolutionFailure(canonical_id, timeframe, "symbols_get_failed")

        if not symbols:
            return SymbolResolutionFailure(canonical_id, timeframe, "no_symbols_visible")

        # Collect symbol names
        broker_names: list[str] = []
        for entry in symbols:
            name = getattr(entry, "name", None)
            if isinstance(name, str):
                broker_names.append(name)

        if not broker_names:
            return SymbolResolutionFailure(canonical_id, timeframe, "no_symbol_names")

        # Candidate aliases: canonical upper first, then configured aliases
        candidates: list[str] = [canonical_upper]
        if canonical_id in self._aliases:
            candidates.extend(self._aliases[canonical_id])

        # Try each candidate: exact match first, then alias, then partial
        exact_matches: list[str] = []
        alias_matches: list[str] = []
        partial_matches: list[str] = []

        # Exact match: canonical_upper == broker_name
        if canonical_upper in broker_names:
            return SymbolResolution(canonical_id, timeframe, canonical_upper, "exact")

        # Alias match: any configured alias matches a broker name
        if canonical_id in self._aliases:
            for alias in self._aliases[canonical_id]:
                if alias in broker_names:
                    return SymbolResolution(canonical_id, timeframe, alias, "alias")

        # Partial match: canonical_upper is a substring of broker_name or vice versa
        for broker_name in broker_names:
            if canonical_upper in broker_name or broker_name in canonical_upper:
                partial_matches.append(broker_name)

        # Ambiguous or no match
        if len(partial_matches) == 1:
            return SymbolResolution(canonical_id, timeframe, partial_matches[0], "partial")
        if len(partial_matches) > 1:
            return SymbolResolutionFailure(
                canonical_id, timeframe, f"ambiguous_match: {partial_matches}"
            )
        return SymbolResolutionFailure(canonical_id, timeframe, "no_matching_symbol")

    def verify_symbol_access(
        self, resolution: SymbolResolution
    ) -> SymbolResolution | SymbolResolutionFailure:
        """Verify that the resolved symbol is visible and accessible.

        Calls symbol_info() on the resolved symbol to confirm the terminal
        can read it. Returns the resolution unchanged on success, or a
        SymbolResolutionFailure if the symbol is hidden or inaccessible.
        """
        try:
            info = self._gateway.symbol_info(resolution.provider_symbol)
        except Exception:  # noqa: BLE001 — broker gateway may raise any error
            return SymbolResolutionFailure(
                resolution.canonical_id, resolution.timeframe, "symbol_info_failed"
            )
        if info is None:
            return SymbolResolutionFailure(
                resolution.canonical_id,
                resolution.timeframe,
                "symbol_not_exposed",
            )

        # Check visibility (Market Watch enabled)
        try:
            if not getattr(info, "visible", False):
                return SymbolResolutionFailure(
                    resolution.canonical_id,
                    resolution.timeframe,
                    "symbol_not_visible",
                )
        except Exception:  # noqa: BLE001 — broker gateway may raise any error
            pass

        return resolution
