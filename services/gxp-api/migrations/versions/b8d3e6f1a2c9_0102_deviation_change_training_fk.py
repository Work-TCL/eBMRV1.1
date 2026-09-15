"""0102_deviation_change_training_fk

Revision ID: b8d3e6f1a2c9
Revises: a4e9c2f6b1d8
Create Date: 2026-09-12 00:00:00.000000

SG-060 gap resolution (Document 26, WP-05 pass). `qms.deviation_record.change_control_required`/
`training_required` were flag+rationale only "because no Change Control or training/qualification-action
entity exists anywhere in this codebase to link to" -- both now exist (`qms.change_control`, Document 29;
`qms.training_assignment`, Document 31), built in a later pass than Document 26's own. Adds the two
nullable FK columns the flags were always meant to eventually carry; the flag/rationale fields are
untouched (additive only, MIG-FR-004 expand step).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8d3e6f1a2c9'
down_revision: Union[str, Sequence[str], None] = 'a4e9c2f6b1d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('deviation_record', sa.Column('change_control_id', sa.UUID(), nullable=True), schema='qms')
    op.create_foreign_key(
        'fk_deviation_record_change_control_id',
        'deviation_record', 'change_control',
        ['change_control_id'], ['id'],
        source_schema='qms', referent_schema='qms',
    )
    op.add_column('deviation_record', sa.Column('training_assignment_id', sa.UUID(), nullable=True), schema='qms')
    op.create_foreign_key(
        'fk_deviation_record_training_assignment_id',
        'deviation_record', 'training_assignment',
        ['training_assignment_id'], ['id'],
        source_schema='qms', referent_schema='qms',
    )


def downgrade() -> None:
    op.drop_constraint('fk_deviation_record_training_assignment_id', 'deviation_record', schema='qms', type_='foreignkey')
    op.drop_column('deviation_record', 'training_assignment_id', schema='qms')
    op.drop_constraint('fk_deviation_record_change_control_id', 'deviation_record', schema='qms', type_='foreignkey')
    op.drop_column('deviation_record', 'change_control_id', schema='qms')
