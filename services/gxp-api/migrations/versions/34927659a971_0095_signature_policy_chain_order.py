"""0095_signature_policy_chain_order

Revision ID: 34927659a971
Revises: 14b9076c5412
Create Date: 2026-09-11 00:00:00.000000

SG-035 pair 4 (`record_correction/complete`), RESOLVED 2026-09-11, project-owner-directed
(PHASE_3_DEFERRED_DECISIONS.md item D). Document 106 section 5's `sig_policy` data model defines
`signature_count` (already present since migration `b270544f6fb0`/0005) *and* `signature_order`
("jsonb NULL -- ordered signer classes when count > 1") for a genuine multi-signature ordered chain
(SIGP-FR-007). The implemented `SignaturePolicy` model has never carried `signature_order` -- every
row seeded so far is `signature_count=1`, so the column was never needed until Document 106 section 9
row 1 ("Authorized corrector + independent approver", count 2, "Corrector and approver MUST differ")
became the first ratified count>1 point. Nullable and additive: every existing row's `signature_order`
stays NULL (meaning "the single `required_role_id` column already names the one signer class"),
matching `signature_count=1`'s existing behaviour exactly. See `app/modules/signature/service.py`
`enforce_chain_signer_policy()` for how a non-NULL value (a JSON list of signer-class role names, one
per 1-indexed chain position) is resolved at runtime.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '34927659a971'
down_revision: Union[str, Sequence[str], None] = '14b9076c5412'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'signature_policies',
        sa.Column('signature_order', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema='signature',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('signature_policies', 'signature_order', schema='signature')