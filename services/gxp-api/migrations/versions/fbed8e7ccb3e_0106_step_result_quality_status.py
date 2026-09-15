"""0106_step_result_quality_status

Revision ID: fbed8e7ccb3e
Revises: 0f714e883102
Create Date: 2026-09-14 00:00:00.000000

Document 11 (SPEC-EBMR-002) -- BAT-FR-009, SG-048 #009 partial resolution, project-owner-directed. Adds
`quality_status` to `ebmr.gxp_step_result`: the "quality status" half of BAT-FR-009's "Capture typed
value, UOM, source, source timestamp, receive time, actor/device, quality status and applicable rule
result." Computed from `gxp_recipe_parameter.min_value/max_value` (already DDL-ready, no new precision
policy invented) at `record_step_results` time -- 'in_range' | 'out_of_range' | 'not_evaluated' | NULL (no
declared limits). Informational only, never blocks the command: BAT-FR-021 (exception generation), the
mechanism that would act on an out-of-range result, is not built (SG-048 #021) -- rejecting the value
outright here would either destroy real evidence of what actually happened or invent a substitute
exception behavior this pass does not decide. "Applicable rule result" (a real rules-engine evaluation
against RecipeParameter.rule_id/rule_version) is a materially deeper capability than a computed column and
stays open.

`source_type` needs no migration -- it is already a String(40) column (migration db47f27cf18b_0092);
`ALLOWED_RESULT_SOURCE_TYPES` in commands.py now additionally accepts 'device_transcribed' (SG-048 #011
partial resolution, still human-entered, not automated device ingestion) alongside the existing 'manual'.

No existing row rewritten (AG-08) -- nullable, defaults to NULL for every already-captured result.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'fbed8e7ccb3e'
down_revision: Union[str, Sequence[str], None] = '0f714e883102'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'gxp_step_result',
        sa.Column('quality_status', sa.String(length=40), nullable=True),
        schema='ebmr',
    )


def downgrade() -> None:
    op.drop_column('gxp_step_result', 'quality_status', schema='ebmr')
