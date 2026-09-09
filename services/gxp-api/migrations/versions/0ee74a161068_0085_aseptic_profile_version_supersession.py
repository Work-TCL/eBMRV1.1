"""0085_aseptic_profile_version_supersession

Revision ID: 0ee74a161068
Revises: a1b3c5d7e9f2
Create Date: 2026-09-07 00:00:00.000000

SG-176 follow-up (Document 40/SPEC-EQP-003) -- `aseptic_profile_version` gained a create endpoint
(2026-09-07) but no update/delete, matching every other versioned regulated master-data record in this
codebase (Product Master, Recipe Master, etc.): a RELEASED row's content is never edited or removed, it is
superseded by a new version. This migration adds the one column that pattern needs -- a nullable
self-referential FK recording which prior version a new row supersedes (VLT-FR-007 "amendment/superseding
version referencing original"). Additive only; no existing row is rewritten (AG-08).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0ee74a161068'
down_revision: Union[str, Sequence[str], None] = 'a1b3c5d7e9f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'aseptic_profile_versions',
        sa.Column('supersedes_profile_version_id', sa.UUID(), nullable=True),
        schema='equipment',
    )
    op.create_foreign_key(
        'fk_aseptic_profile_versions_supersedes', 'aseptic_profile_versions', 'aseptic_profile_versions',
        ['supersedes_profile_version_id'], ['id'], source_schema='equipment', referent_schema='equipment',
    )


def downgrade() -> None:
    op.drop_constraint('fk_aseptic_profile_versions_supersedes', 'aseptic_profile_versions', schema='equipment', type_='foreignkey')
    op.drop_column('aseptic_profile_versions', 'supersedes_profile_version_id', schema='equipment')
