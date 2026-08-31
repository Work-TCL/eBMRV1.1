"""0025_oos_oot_schema

Revision ID: 9d2f4a6c8e0b
Revises: 3f7a1c9e5b2d
Create Date: 2026-08-24 00:00:00.000000

Document 25 (SPEC-QC-003) -- OOS/OOT Management. Extends the already-built `qc` module (owner service
confirmed by docs/generated/04_DATA_MODEL_CATALOGUE.md for all 5 entities): `oos_record` (DDL-ready, exact
17-column list per §7), `oos_investigation_activity`/`oos_retest_plan`/`oos_resample_plan`/`oot_record`
(prose-only field lists, typed as an ordinary engineering decision -- SG-045's precedent).

Also adds real FK constraints to `qc_result.oos_record_id`/`oot_record_id` -- previously unenforced
nullable columns added in the Document 23 migration in anticipation of this document. Expand-only,
backward compatible (both columns are nullable and all-NULL in dev/test data at this point).

Real gaps NOT built this pass (SG-074 in docs/generated/18_SPEC_GAPS.md): OOS-FR-020/021 (CAPA/Change
Control link -- no column or entity declared anywhere in Document 25's own data model for this), OOS-FR-023/
029/030 (`/reopen`, metrics dashboard, investigation export -- none in Document 25's own §10 API list),
OOS-FR-027 (QA Review package wiring -- cross-module, out of scope this pass), OOS-FR-028 + OOT-FR-006
(release-engine blocker wiring -- cross-module, out of scope this pass), RETEST_LIMIT_REACHED (no numeric
retest-count policy value anywhere in the baseline).

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
Tables in the shared `ebmr` schema. Append-only-vs-mutable privilege split decided per table against the
actual command code in app/modules/qc/commands.py: `oos_investigation_activity` is genuinely append-only
(every write path is an INSERT; no command in this pass updates an existing activity row) -- SELECT/INSERT/
TRUNCATE only. `oos_record`, `oos_retest_plan`, `oos_resample_plan`, `oot_record` all have `state`/`status`/
`version`/other fields updated in place by later commands (e.g. `classify_lab_cause` mutates `oos_record`,
`close_oot` mutates `oot_record`) -- all four get UPDATE too, same discipline the Document 23 `qc_result`
privilege fix established (grant UPDATE only where a real code path actually mutates an already-committed
row, never by default).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9d2f4a6c8e0b'
down_revision: Union[str, Sequence[str], None] = '3f7a1c9e5b2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'oos_record',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('oos_number', sa.String(length=120), nullable=False),
        sa.Column('source_result_id', sa.UUID(), nullable=False),
        sa.Column('sample_id', sa.UUID(), nullable=True),
        sa.Column('test_order_id', sa.UUID(), nullable=True),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('material_lot_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='open'),
        sa.Column('severity', sa.String(length=40), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('hold_status', sa.String(length=40), nullable=True),
        sa.Column('final_classification', sa.String(length=60), nullable=True),
        sa.Column('root_cause_code', sa.String(length=100), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['source_result_id'], ['ebmr.qc_result.id']),
        sa.ForeignKeyConstraint(['sample_id'], ['ebmr.qc_sample.id']),
        sa.ForeignKeyConstraint(['test_order_id'], ['ebmr.qc_test_order.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.gxp_batch.id']),
        sa.ForeignKeyConstraint(['material_lot_id'], ['materials.material_lots.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('oos_number'),
        schema='ebmr',
    )

    op.create_table(
        'oos_investigation_activity',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('oos_record_id', sa.UUID(), nullable=False),
        sa.Column('phase', sa.String(length=40), nullable=False),
        sa.Column('activity_type', sa.String(length=80), nullable=False),
        sa.Column('checklist_item', sa.String(length=200), nullable=True),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('evidence_refs', sa.JSON(), nullable=True),
        sa.Column('investigator_user_id', sa.UUID(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['oos_record_id'], ['ebmr.oos_record.id']),
        sa.ForeignKeyConstraint(['investigator_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_oos_investigation_activity_oos', 'oos_investigation_activity', ['oos_record_id'], schema='ebmr')

    op.create_table(
        'oos_retest_plan',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('oos_record_id', sa.UUID(), nullable=False),
        sa.Column('justification', sa.Text(), nullable=False),
        sa.Column('number_of_retests', sa.Integer(), nullable=False),
        sa.Column('method_ref', sa.String(length=160), nullable=True),
        sa.Column('analyst_criteria', sa.String(length=300), nullable=True),
        sa.Column('instrument_criteria', sa.String(length=300), nullable=True),
        sa.Column('interpretation_rule', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='authorized'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['oos_record_id'], ['ebmr.oos_record.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )

    op.create_table(
        'oos_resample_plan',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('oos_record_id', sa.UUID(), nullable=False),
        sa.Column('scientific_rationale', sa.Text(), nullable=False),
        sa.Column('sampling_plan_ref', sa.String(length=160), nullable=True),
        sa.Column('sampling_plan_version', sa.String(length=40), nullable=True),
        sa.Column('source_ref', sa.String(length=200), nullable=True),
        sa.Column('approver_user_id', sa.UUID(), nullable=True),
        sa.Column('resulting_sample_ids', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='authorized'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['oos_record_id'], ['ebmr.oos_record.id']),
        sa.ForeignKeyConstraint(['approver_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )

    op.create_table(
        'oot_record',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_result_id', sa.UUID(), nullable=False),
        sa.Column('trend_rule_id', sa.UUID(), nullable=True),
        sa.Column('trend_rule_version', sa.String(length=40), nullable=True),
        sa.Column('baseline_ref', sa.String(length=200), nullable=True),
        sa.Column('trigger_details', sa.JSON(), nullable=True),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='open'),
        sa.Column('investigation_notes', sa.Text(), nullable=True),
        sa.Column('impact_assessment', sa.Text(), nullable=True),
        sa.Column('investigation_owner_user_id', sa.UUID(), nullable=True),
        sa.Column('hold_status', sa.String(length=40), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('opened_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['source_result_id'], ['ebmr.qc_result.id']),
        sa.ForeignKeyConstraint(['trend_rule_id'], ['rules.gxp_rule_definition.rule_object_id']),
        sa.ForeignKeyConstraint(['investigation_owner_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )

    op.create_foreign_key(
        'fk_qc_result_oos_record', 'qc_result', 'oos_record', ['oos_record_id'], ['id'],
        source_schema='ebmr', referent_schema='ebmr',
    )
    op.create_foreign_key(
        'fk_qc_result_oot_record', 'qc_result', 'oot_record', ['oot_record_id'], ['id'],
        source_schema='ebmr', referent_schema='ebmr',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.oos_record TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.oos_investigation_activity TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.oos_retest_plan TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.oos_resample_plan TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.oot_record TO {APP_ROLE}")


def downgrade() -> None:
    op.drop_constraint('fk_qc_result_oot_record', 'qc_result', schema='ebmr', type_='foreignkey')
    op.drop_constraint('fk_qc_result_oos_record', 'qc_result', schema='ebmr', type_='foreignkey')
    for table in ('oot_record', 'oos_resample_plan', 'oos_retest_plan', 'oos_investigation_activity', 'oos_record'):
        op.execute(f"REVOKE ALL ON ebmr.{table} FROM {APP_ROLE}")
        op.drop_table(table, schema='ebmr')
