"""0003: backtest_run + dataset_manifest tables — declared provenance (D-6.3).

Bars are referenced by hash/ref only and never stored here; source files are
hashed and referenced via ``source_hashes``. Costs stay placeholders until the
operator confirms them (D-6.1) — the columns carry whatever was declared.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_backtest"
down_revision = "0002_journal_outcome"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_run",
        sa.Column("backtest_run_id", sa.Text, primary_key=True),
        sa.Column("strategy_id", sa.Text, nullable=False),
        sa.Column("strategy_version", sa.Text, nullable=False),
        sa.Column("dataset_ref", sa.Text, nullable=False),
        sa.Column("dataset_hash", sa.Text, nullable=False),
        sa.Column("instrument", sa.Text, nullable=False),
        sa.Column("timeframe", sa.Text, nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.Text, nullable=False),
        sa.Column("data_quality", sa.Text, nullable=False),
        sa.Column("parameter_hash", sa.Text, nullable=False),
        sa.Column("assumptions", postgresql.JSONB, nullable=False),
        sa.Column("in_sample_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("in_sample_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validation_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validation_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("out_of_sample_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("out_of_sample_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics", postgresql.JSONB, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("code_version", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("errors", postgresql.JSONB, nullable=False),
    )
    op.create_index("ix_backtest_run_strategy_id", "backtest_run", ["strategy_id"])
    op.create_table(
        "dataset_manifest",
        sa.Column("dataset_ref", sa.Text, primary_key=True),
        sa.Column("range_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("range_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol_mapping", postgresql.JSONB, nullable=False),
        sa.Column("quality_report", postgresql.JSONB, nullable=False),
        sa.Column("excluded_periods", postgresql.JSONB, nullable=False),
        sa.Column("source_hashes", postgresql.JSONB, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("dataset_manifest")
    op.drop_index("ix_backtest_run_strategy_id", table_name="backtest_run")
    op.drop_table("backtest_run")
