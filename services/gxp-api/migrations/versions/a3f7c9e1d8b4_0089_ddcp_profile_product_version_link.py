"""0089_ddcp_profile_product_version_link

Revision ID: a3f7c9e1d8b4
Revises: d4f6b8c0e2a5
Create Date: 2026-09-08 00:00:00.000000

SG-175 (product_version_id half, project-owner-directed: "Enforced FK + family derived from product",
chosen over a soft/traceability-only link, a full merge of DDCP Profile into Product Master, or leaving
the gap open). `ddcp.ddcp_profile_version` (Document 54/55/56/57, shared by all 4 DDCP families) had no
foreign key to Product Master's `ebmr.gxp_product_version` at all -- the `/ddcp` page's "Product family"
picker and Product Master's own `manufacturing_profile_code` were two unwired halves of the same
combination-product concept, found while writing the client demo guide's comparison of the two. This adds
the one column that link needs; the command-layer validation that requires and checks it (existence,
`released` state, matching site, and -- only for the two families whose family unambiguously maps to one
Product Master `manufacturing_profile_code` value, PFS/`injectable_ddcp` and Inhalation/`inhalation_ddcp`
-- a matching manufacturing profile) lives in `app/modules/ddcp/commands.py::_assert_product_version_for_profile`,
applied by every family's create-profile command. Additive only; nullable so the handful of pre-existing
demo/test profiles created before this migration are grandfathered rather than rewritten (AG-08) -- every
profile authored after this migration is required by the application layer to carry it.

Autoinjector and Coated device have no corresponding value in Product Master's 5-value
`manufacturing_profile_code` vocabulary at all, so those two families get the FK+released+site checks
only, not a family-match check -- deliberately not guessed (CLAUDE.md #4); the residual half of SG-175
that decision leaves open is documented in the same spec-gap entry.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3f7c9e1d8b4'
down_revision: Union[str, Sequence[str], None] = 'd4f6b8c0e2a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ddcp_profile_version',
        sa.Column('product_version_id', sa.UUID(), nullable=True),
        schema='ddcp',
    )
    op.create_foreign_key(
        'fk_ddcp_profile_version_product_version', 'ddcp_profile_version', 'gxp_product_version',
        ['product_version_id'], ['id'], source_schema='ddcp', referent_schema='ebmr',
    )


def downgrade() -> None:
    op.drop_constraint('fk_ddcp_profile_version_product_version', 'ddcp_profile_version', schema='ddcp', type_='foreignkey')
    op.drop_column('ddcp_profile_version', 'product_version_id', schema='ddcp')
