"""0002: journal_entry + outcome_observation tables — immutable snapshots (D-6.2).

Snapshots are INSERT-only: the store module exposes no mutation path, and
corrections are new rows carrying ``supersedes`` plus a reason. Retention and
backup stay operator-owned (D-6.4); this migration adds no policy.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_journal_outcome"
down_revision = "0001_contract_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "journal_entry",
        sa.Column("journal_id", sa.Text, primary_key=True),
        sa.Column("decision_id", sa.Text, nullable=False),
        sa.Column("run_id", sa.Text, nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot", postgresql.JSONB, nullable=False),
    )
    op.create_index("ix_journal_entry_decision_id", "journal_entry", ["decision_id"])
    op.create_index("ix_journal_entry_run_id", "journal_entry", ["run_id"])
    op.create_table(
        "outcome_observation",
        sa.Column("outcome_id", sa.Text, primary_key=True),
        sa.Column("decision_id", sa.Text, nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed", postgresql.JSONB, nullable=False),
        sa.Column("pnl", postgresql.JSONB, nullable=False),
        sa.Column("supersedes", sa.Text, nullable=True),
        sa.Column("reason", sa.Text, nullable=False, server_default=""),
    )
    op.create_index(
        "ix_outcome_observation_decision_id", "outcome_observation", ["decision_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_outcome_observation_decision_id", table_name="outcome_observation")
    op.drop_table("outcome_observation")
    op.drop_index("ix_journal_entry_run_id", table_name="journal_entry")
    op.drop_index("ix_journal_entry_decision_id", table_name="journal_entry")
    op.drop_table("journal_entry")
