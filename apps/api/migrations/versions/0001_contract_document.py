"""0001: contract_document table — validated JSONB plus promoted columns (D-07).

The document/promotion split is the one-way D-07 decision: changing it after
records exist requires a data migration and re-validation of stored payloads.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_contract_documents"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contract_document",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("run_id", sa.Text, nullable=True),
        sa.Column("agent_name", sa.Text, nullable=True),
        sa.Column("instrument_id", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("status", sa.Text, nullable=True),
        sa.Column("document", postgresql.JSONB, nullable=False),
    )
    op.create_index("ix_contract_document_run_id", "contract_document", ["run_id"])
    op.create_index(
        "ix_contract_document_instrument_id", "contract_document", ["instrument_id"]
    )
    op.create_index("ix_contract_document_created_at", "contract_document", ["created_at"])
    op.create_index("ix_contract_document_status", "contract_document", ["status"])


def downgrade() -> None:
    op.drop_index("ix_contract_document_status", table_name="contract_document")
    op.drop_index("ix_contract_document_created_at", table_name="contract_document")
    op.drop_index("ix_contract_document_instrument_id", table_name="contract_document")
    op.drop_index("ix_contract_document_run_id", table_name="contract_document")
    op.drop_table("contract_document")
