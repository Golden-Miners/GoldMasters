"""GoldMasters shared contracts.

This module is the single import surface for the ``goldmasters-contracts``
distribution: every contract module and :data:`CONTRACT_VERSION` is re-exported
here so consumers (the API, the TypeScript type generator, and later phases)
import one name rather than reaching into submodules. Plans 03 and 11 extend the
barrel as they add contracts; it is never replaced.
"""

from __future__ import annotations

__all__ = ["CONTRACT_VERSION"]

# The contract-layer version shared by every contract (Schema.md §1; D-02/D-23).
# It is a ``major.minor`` string: a reader accepts any ``1.x`` and rejects an
# unknown major, so a document written at ``1.0`` stays readable and replayable
# by a later ``1.x`` build.
CONTRACT_VERSION = "1.0"
