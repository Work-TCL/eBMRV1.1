"""0103_erp_instance_service_actor

Revision ID: c3f7a9d2b6e4
Revises: b8d3e6f1a2c9
Create Date: 2026-09-14 00:00:00.000000

WP-11 Stage 4 (ADR-0011, SG-183): the first real ERP integration consumer
(`app/modules/erp/consumer.py`) calls `queue_erp_command()`, which writes a real audit row and therefore
needs an `actor_user_id` -- a live background NATS consumer has no human actor to supply. Adds
`erp.erp_instances.service_actor_user_id`, mirroring the identical stand-in `lims_instance.
service_actor_user_id` already uses ("stands in for a dedicated machine-identity model, which does not
exist anywhere in this codebase" -- SG-070 / LIMS-FR-013; `lims_instance.py`'s own docstring cites this as
"SG-067", which is actually a different, unrelated NCR gap -- SG-070 is the correct number, verified
against docs/generated/18_SPEC_GAPS.md directly rather than trusting that pre-existing citation):
applying an already-reviewed pattern to a sibling integration module, not inventing a new one.

Nullable (MIG-FR-004 expand step): existing `ErpInstance` rows (including the live demo DB's) have no
natural "who provisioned this" actor to backfill from, so this does not force a value onto them. An
instance with `service_actor_user_id IS NULL` is simply not eligible for the automated consumer path yet
-- `erp/consumer.py` treats that the same as "no ERP instance configured for this site" and skips.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3f7a9d2b6e4'
down_revision: Union[str, Sequence[str], None] = 'b8d3e6f1a2c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('erp_instances', sa.Column('service_actor_user_id', sa.UUID(), nullable=True), schema='erp')
    op.create_foreign_key(
        'fk_erp_instances_service_actor_user_id',
        'erp_instances', 'users',
        ['service_actor_user_id'], ['id'],
        source_schema='erp', referent_schema='iam',
    )


def downgrade() -> None:
    op.drop_constraint('fk_erp_instances_service_actor_user_id', 'erp_instances', schema='erp', type_='foreignkey')
    op.drop_column('erp_instances', 'service_actor_user_id', schema='erp')