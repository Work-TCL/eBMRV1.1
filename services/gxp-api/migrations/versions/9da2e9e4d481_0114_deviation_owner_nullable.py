"""0114_deviation_owner_nullable

Revision ID: 9da2e9e4d481
Revises: 6eacd4d13145
Create Date: 2026-09-18 00:00:00.000000

Auto-deviation-creation fix (docs/testing/demo-gujarati/08 §8.8 item 2), project-owner-directed
2026-09-18: an in-process out-of-range result now automatically opens a DeviationRecord instead of
staying purely informational. The project owner explicitly chose "auto-create in OPEN state, unassigned
owner" over auto-assigning an owner -- `qms.deviation_record.owner_subject_id` was NOT NULL, which that
choice can't satisfy without this column becoming nullable. `investigator_subject_id` on the same table
was already nullable and already gets assigned later, at Investigation -- this brings owner_subject_id
to the same "assigned by a human during the normal workflow, not forced at creation" shape.

Relaxing a NOT NULL constraint is additive/backward-compatible (MIG-FR-015 "constraints introduced
safely" applies in the other direction here -- removing one, not adding one); no existing row is
rewritten.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9da2e9e4d481'
down_revision: Union[str, Sequence[str], None] = '6eacd4d13145'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'deviation_record', 'owner_subject_id',
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True, schema='qms',
    )


def downgrade() -> None:
    op.alter_column(
        'deviation_record', 'owner_subject_id',
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False, schema='qms',
    )
