"""0109_correction_removal_chain_signatures

Revision ID: fc212b616386
Revises: 164abb1a20dc
Create Date: 2026-09-14 00:00:00.000000

Document 60 (SPEC-PM-003) -- SG-160 partial resolution, project-owner-directed. Document 106 rows 129/130
("Authorized corrector + independent approver", count 2, "Corrector and approver MUST differ", reason
mandatory) apply to the correction/removal assessment-creation and reportability-decision actions.

SG-160's own text claimed "no multi-signature ceremony mechanism exists anywhere in this codebase" --
that was already false when written: `app/modules/vault/commands.py::complete_correction()` implements
exactly this via `signature_service.enforce_chain_signer_policy()` + `chain_signatures_so_far()` (SG-035
pair 4, RESOLVED 2026-09-11), for the identical "Authorized corrector + independent approver" language
(Document 106 row 1). This migration adds the two columns needed to reuse that exact mechanism for
Document 60's own two actions, mirroring `vault.gxp_record_correction.approved_by_signatures`'s shape
verbatim rather than inventing a new one.

Nullable/default-empty-list, additive (AG-08, MIG-FR-004 expand step) -- no existing row rewritten.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'fc212b616386'
down_revision: Union[str, Sequence[str], None] = '164abb1a20dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'correction_removal_regulatory_record',
        sa.Column('assessment_approval_signatures', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        schema='postmarket',
    )
    op.add_column(
        'correction_removal_regulatory_record',
        sa.Column('decision_approval_signatures', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        schema='postmarket',
    )


def downgrade() -> None:
    op.drop_column('correction_removal_regulatory_record', 'decision_approval_signatures', schema='postmarket')
    op.drop_column('correction_removal_regulatory_record', 'assessment_approval_signatures', schema='postmarket')
