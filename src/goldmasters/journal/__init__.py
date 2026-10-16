"""Immutable decision journal: snapshot writer plus append-only outcomes."""

from src.goldmasters.journal.store import (
    append_outcome,
    read_outcomes,
    read_snapshot,
    write_snapshot,
)

__all__ = [
    "append_outcome",
    "read_outcomes",
    "read_snapshot",
    "write_snapshot",
]
