"""Append-only journal record (Schema.md §6 line 166).

A journal entry wraps an immutable snapshot of a decision. The record itself
is frozen, and its ``decision_id`` must equal the snapshot's — an entry that
would mutate a persisted decision's immutable fields (a mismatched id, or any
post-construction update) is rejected. Corrections create a superseding record
carrying ``supersedes`` plus a ``reason``, never an edit.
"""

from __future__ import annotations

from pydantic import model_validator

from goldmasters_contracts._base import ContractModel, UtcDatetime
from goldmasters_contracts.decision import DecisionRecord
from goldmasters_contracts.ids import DecId, JournalId, RunId

__all__ = ["JournalEntry"]


class JournalEntry(ContractModel):
    """Immutable journal wrapper binding an entry id to a decision snapshot."""

    journal_id: JournalId
    decision_id: DecId
    run_id: RunId
    recorded_at: UtcDatetime
    snapshot: DecisionRecord
    supersedes: DecId | None = None
    reason: str = ""

    @model_validator(mode="after")
    def _validate_binding(self) -> JournalEntry:
        if self.decision_id != self.snapshot.decision_id:
            raise ValueError("journal decision_id must equal the snapshot decision_id")
        if self.run_id != self.snapshot.run_id:
            raise ValueError("journal run_id must equal the snapshot run_id")
        return self
