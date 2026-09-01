"""0081_validation_exception_requested_by

Revision ID: e1a2b3c4d5e6
Revises: d4f8b1e6c9a3
Create Date: 2026-09-01 00:00:00.000000

SG-167 resolution (Document 106 rows 162/164/165): `validation.validation_exception` gains
`requested_by_user_id`, used to enforce "MUST be independent of the requester" on the now-resolved
`create`/`triage`/`retest_plan` Approved signatures (signer role: QA Releaser). Same
`requested_by_user_id`-vs-signing-actor pattern already used by `material_*`, `supplier_qualification`
and `lims_*` tables.

**Expand-only** -- one nullable column added to an existing table, no backfill needed (the table has no
production rows predating this pass; any pre-existing test fixtures simply keep it NULL, which is fine
since they are not production evidence). No other table/schema touched. Reversible: `downgrade()` drops
the column.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'd4f8b1e6c9a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "validation_exception",
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="validation",
    )


def downgrade() -> None:
    op.drop_column("validation_exception", "requested_by_user_id", schema="validation")
