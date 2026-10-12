"""The event-to-permission mapping -- deliberately the *only* file a future workflow (a 4th, 5th, ...
aggregate type) needs to touch to get notifications "for free": add one `WorkflowNotificationSpec` to
`WORKFLOW_SPECS` naming its NATS aggregate subject, its pending states (state name -> the RBAC permission
code that gates the next command on it, per that module's own router -- see each module's
`evaluate_policy(action="...")` call sites), and a loader that reads the aggregate's own authoritative
table for its current state/site/label/link/last-touched-by. Nothing in `consumer.py` or `service.py`
is state-machine-specific; both are driven entirely by this registry.

Scope, narrowed then generalized (project-owner-directed):
  Pass 1 -- Batch Record Release, Deviation disposition + close, CAPA plan + close,
    Document Release/Pending-Signature (release_scope, deviation_record, capa_record,
    controlled_document_version).
  Pass 2 -- the rest of QMS's own signature-gated cross-role handoffs (NCR disposition/verification/
    close, Complaint reportability/close, Change Control approval/close, SCAR review/close, Field Action
    approval/close, Internal Audit close, Risk acceptance) plus QC/Material (OOS disposition/close, OOT
    close, Material Lot release, Supplier Qualification approval).
  Pass 3 (found via a real user report -- a material specification draft sat with no releaser
    notification) -- the three master-data draft-authoring modules share the identical
    draft -> [under_review ->] released pattern with an author != releaser signature gate, and none of
    them were in Pass 1/2's scope even though they are exactly this registry's shape: Material
    Specification release, Product Master release, Recipe Master release.
  Pass 4 (client gap-analysis Phase 4, 2026-10-05 -- a new equipment_asset.approve_calibration step was
    added with no reviewer notification) -- equipment_asset, keyed on the purpose-built
    `calibration_status` column rather than the asset's own overloaded `state`, since a calibration
    pending review ("pending_approval") has no relationship to the qualification/maintenance states
    `state` otherwise tracks. No SIGNATURE_POLICY_FLOOR row exists for "approve_calibration" (checked
    scripts/seed.py: only "hold"/"retire" have equipment_asset rows), so signature_record_type/
    signature_action are left None -- the same no-signature-pointer precedent risk_record's
    "risk.accept" category already set above.
Not covered: everything outside these ~19 aggregate types (validation, DDCP, postmarket, security
incidents, and more each have their own signature-gated actions Document 106 lists -- see
scripts/seed.py's SIGNATURE_POLICY_FLOOR for the full ~150-row catalogue) -- extending further means the
same per-module due diligence this file's history already shows, not a bulk guess.

Not every signature-gated action fits this registry's "one discrete pending state" model -- risk_record's
periodic/triggered `review_risk()` was deliberately left out (see its own WorkflowNotificationSpec note
below): it runs from the risk's normal long-lived ACCEPTED state, not a transient "waiting" state, so
notifying on it would either fire for every accepted risk indefinitely or need a due-date mechanism like
the separate Reminders feature (app/modules/dashboard/service.py), not a workflow-handoff one.

SG-214 (docs/generated/18_SPEC_GAPS.md) originally flagged that audience resolution read only the RBAC
permission code, not the (possibly narrower) `signature.signature_policy.required_role_id` -- resolved by
`PendingStateRule.signature_record_type`/`signature_action` below: when set, `service.py`'s audience
resolution additionally narrows to actors who hold that policy's *current* required role, read live from
`signature.signature_policy` (never a role name hardcoded in this file), so the notification audience can
never drift from what Document 106 policy data actually requires to complete the action.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Awaitable, Callable, NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent
from app.modules.batch_execution.models import Batch, BatchStep, StepResult, StepResultCorrection
from app.modules.ddcp.models import ConstituentHandoff, DdcpProfileVersion
from app.modules.equipment.aseptic_models import AsepticOperation
from app.modules.equipment.cleaning_models import CleaningExecution
from app.modules.equipment.em_models import EmExcursion, EmSampleOrReading
from app.modules.equipment.models import EquipmentAsset
from app.modules.equipment.sterilization_models import ProcessCycle
from app.modules.erp.models import ErpExternalMapping, ErpMappingConflict
from app.modules.machine_integration.models import SignalMapping
from app.modules.material.models import (
    DispensingOrder, InventoryAdjustmentRequest, InventoryReservation, Material, MaterialLot, MaterialReceipt,
)
from app.modules.material_specification.models import MaterialSpecificationVersion
from app.modules.postmarket.reportability_models import RegulatoryReport
from app.modules.product_master.models import ProductVersion
from app.modules.qa_review.models import QaReviewPackage
from app.modules.qc.models import OosRecord, OotRecord, QcResultCorrection, QcSample, QcTestOrder, QcTestSpecification
from app.modules.qms.capa_models import CapaRecord
from app.modules.qms.change_models import ChangeControl
from app.modules.qms.complaint_models import ComplaintRecord
from app.modules.qms.document_models import ControlledDocument, ControlledDocumentVersion
from app.modules.qms.field_action_models import FieldAction
from app.modules.qms.internal_audit_models import AuditFinding, InternalAudit
from app.modules.qms.models import DeviationRecord
from app.modules.qms.ncr_models import NonconformanceRecord
from app.modules.qms.quality_metrics_models import QualityMetricDefinition, QualityMetricSnapshot
from app.modules.qms.risk_models import RiskRecord
from app.modules.qms.scar_models import ScarRecord
from app.modules.qms.training_models import TrainingAssignment
from app.modules.recipe_master.models import RecipeFamily, RecipeVersion
from app.modules.release.models import ReleaseScope
from app.modules.rules.models import RuleDefinition, UnitOfMeasure
from app.modules.security.incident_models import SecurityIncident
from app.modules.security.privileged_access_models import PrivilegedAccessRequest, PrivilegedSession
from app.modules.supplier_quality.models import SupplierQualification
from app.modules.validation.models import (
    DataIntegrityTestProfile, DrQualificationExecution, FunctionRiskAssessment, InterfaceValidationProfile,
    IqExecution, IqProtocol, OqExecution, PeriodicValidationReview, SecurityQualificationSuite,
    ValidationException, ValidationMasterPlan, ValidationTestDefinition,
)
from app.modules.validation.models_wp14 import (
    MigrationRun, MigrationValidationPlan, PqScenario, ValidatedReleaseAuthorization, ValidationSummaryReport,
)
from app.modules.yield_reconciliation.models import ManufacturingCalculation, ReconciliationRecord


class EntitySnapshot(NamedTuple):
    state: str
    # None for the handful of aggregates that are themselves not site-scoped in the real authorization
    # path (see models.py's site_id docstring) -- never a guessed site.
    site_id: uuid.UUID | None
    entity_label: str
    link_path: str
    # Whoever's own audit trail last touched this aggregate -- the SoD-nudge exclusion (see models.py).
    last_actor_id: uuid.UUID | None


@dataclass(frozen=True)
class PendingStateRule:
    category: str
    required_permission_code: str
    # SG-214 fix: the (record_type, action) `signature.signature_policy` reads for this exact transition
    # -- the same pair the real command handler passes to `resolve_signature_requirement()`. When set,
    # `service.py::list_visible_notifications()` narrows the RBAC-permission audience above to only
    # actors who *also* hold the policy's current `required_role_id`, read live from the same table the
    # write path itself reads (never a role name hardcoded here) -- so the notification audience tracks a
    # signature-policy edit automatically, with no drift possible between the two. `None` for a category
    # with no signature policy (nothing to narrow against).
    signature_record_type: str | None = None
    signature_action: str | None = None


@dataclass(frozen=True)
class WorkflowNotificationSpec:
    aggregate_type: str
    nats_subject: str
    pending_states: dict[str, PendingStateRule]
    loader: Callable[[AsyncSession, uuid.UUID], Awaitable["EntitySnapshot | None"]]
    list_all_ids: Callable[[AsyncSession], Awaitable[list[uuid.UUID]]]

    @property
    def categories(self) -> dict[str, PendingStateRule]:
        """Every category this aggregate type can ever raise, keyed by category name -- used to know
        which *other* categories to resolve when the aggregate is no longer in their pending state
        (`service.py::sync_notification`)."""
        return {rule.category: rule for rule in self.pending_states.values()}


# Every loader below reads with `populate_existing=True`. In production this is a no-op (the real
# consumer/rebuild callers use a fresh `SessionLocal()` per message/run, so the identity map never has a
# stale copy to begin with) -- but any caller that reuses one long-lived session across an external
# mutation (a test driving state through the HTTP `client` while also holding `db`, discovered exactly
# this way while adding OOS/OOT test coverage) would otherwise get a cached, stale row back from
# `session.get()` instead of this loader's whole point: the aggregate's *current* truth. Cheap and always
# correct, so applied everywhere rather than only where a caller happens to need it today.
async def _last_actor(session: AsyncSession, *, aggregate_type: str, aggregate_id: uuid.UUID) -> uuid.UUID | None:
    return await session.scalar(
        select(AuditEvent.actor_id)
        .where(AuditEvent.aggregate_type == aggregate_type, AuditEvent.aggregate_id == aggregate_id)
        .order_by(AuditEvent.occurred_at.desc())
        .limit(1)
    )


async def _load_release_scope(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    scope = await session.get(ReleaseScope, entity_id, populate_existing=True)
    if scope is None:
        return None
    batch = await session.get(Batch, scope.batch_id, populate_existing=True)
    label = f"Batch {batch.batch_number}" if batch is not None else f"Release scope {scope.id}"
    last_actor = await _last_actor(session, aggregate_type="release_scope", aggregate_id=entity_id)
    return EntitySnapshot(
        state=scope.state, site_id=scope.site_id, entity_label=label,
        link_path=f"/release?scope_id={scope.id}", last_actor_id=last_actor,
    )


async def _list_release_scope_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ReleaseScope.id))).scalars().all())


async def _load_deviation(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    deviation = await session.get(DeviationRecord, entity_id, populate_existing=True)
    if deviation is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="deviation_record", aggregate_id=entity_id)
    return EntitySnapshot(
        state=deviation.state, site_id=deviation.site_id, entity_label=f"Deviation {deviation.deviation_number}",
        link_path=f"/deviations/{deviation.id}", last_actor_id=last_actor,
    )


async def _list_deviation_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(DeviationRecord.id))).scalars().all())


async def _load_capa(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    capa = await session.get(CapaRecord, entity_id, populate_existing=True)
    if capa is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="capa_record", aggregate_id=entity_id)
    return EntitySnapshot(
        state=capa.state, site_id=capa.site_id, entity_label=f"CAPA {capa.capa_number}",
        link_path=f"/capa/{capa.id}", last_actor_id=last_actor,
    )


async def _list_capa_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(CapaRecord.id))).scalars().all())


async def _load_document_version(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    version = await session.get(ControlledDocumentVersion, entity_id, populate_existing=True)
    if version is None:
        return None
    document = await session.get(ControlledDocument, version.document_id, populate_existing=True)
    if document is None:
        return None
    label = f"{document.document_code} v{version.version_label}"
    last_actor = await _last_actor(session, aggregate_type="controlled_document_version", aggregate_id=entity_id)
    return EntitySnapshot(
        state=version.state, site_id=document.site_id, entity_label=label,
        link_path=f"/documents/{document.document_code}", last_actor_id=last_actor,
    )


async def _list_document_version_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ControlledDocumentVersion.id))).scalars().all())


async def _load_ncr(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    ncr = await session.get(NonconformanceRecord, entity_id, populate_existing=True)
    if ncr is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="nonconformance_record", aggregate_id=entity_id)
    return EntitySnapshot(
        state=ncr.state, site_id=ncr.site_id, entity_label=f"NCR {ncr.ncr_number}",
        link_path=f"/nonconformances/{ncr.id}", last_actor_id=last_actor,
    )


async def _list_ncr_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(NonconformanceRecord.id))).scalars().all())


async def _load_complaint(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    complaint = await session.get(ComplaintRecord, entity_id, populate_existing=True)
    if complaint is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="complaint_record", aggregate_id=entity_id)
    return EntitySnapshot(
        state=complaint.state, site_id=complaint.site_id, entity_label=f"Complaint {complaint.complaint_number}",
        link_path=f"/complaints/{complaint.id}", last_actor_id=last_actor,
    )


async def _list_complaint_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ComplaintRecord.id))).scalars().all())


async def _load_change_control(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    change = await session.get(ChangeControl, entity_id, populate_existing=True)
    if change is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="change_control", aggregate_id=entity_id)
    return EntitySnapshot(
        state=change.state, site_id=change.site_id, entity_label=f"Change {change.change_number}",
        link_path=f"/changes/{change.id}", last_actor_id=last_actor,
    )


async def _list_change_control_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ChangeControl.id))).scalars().all())


async def _load_scar(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    scar = await session.get(ScarRecord, entity_id, populate_existing=True)
    if scar is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="scar_record", aggregate_id=entity_id)
    # /supplier-cases/[id] is keyed by the parent case, not the SCAR sub-resource -- it renders the case
    # detail view with the SCAR's own actions embedded (frontend/src/app/supplier-cases/[id]/page.tsx).
    return EntitySnapshot(
        state=scar.state, site_id=scar.site_id, entity_label=f"SCAR {scar.scar_number}",
        link_path=f"/supplier-cases/{scar.case_id}", last_actor_id=last_actor,
    )


async def _list_scar_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ScarRecord.id))).scalars().all())


async def _load_field_action(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    field_action = await session.get(FieldAction, entity_id, populate_existing=True)
    if field_action is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="field_action", aggregate_id=entity_id)
    return EntitySnapshot(
        state=field_action.state, site_id=field_action.site_id, entity_label=f"Field Action {field_action.action_number}",
        link_path=f"/field-actions/{field_action.id}", last_actor_id=last_actor,
    )


async def _list_field_action_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(FieldAction.id))).scalars().all())


async def _load_internal_audit(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    audit = await session.get(InternalAudit, entity_id, populate_existing=True)
    if audit is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="internal_audit", aggregate_id=entity_id)
    return EntitySnapshot(
        state=audit.state, site_id=audit.site_id, entity_label=f"Internal Audit {audit.audit_number}",
        link_path=f"/audits/{audit.id}", last_actor_id=last_actor,
    )


async def _list_internal_audit_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(InternalAudit.id))).scalars().all())


async def _load_risk(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    risk = await session.get(RiskRecord, entity_id, populate_existing=True)
    if risk is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="risk_record", aggregate_id=entity_id)
    return EntitySnapshot(
        state=risk.state, site_id=risk.site_id, entity_label=f"Risk {risk.risk_number}",
        link_path=f"/risks/{risk.id}", last_actor_id=last_actor,
    )


async def _list_risk_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(RiskRecord.id))).scalars().all())


async def _load_oos(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    oos = await session.get(OosRecord, entity_id, populate_existing=True)
    if oos is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="oos_record", aggregate_id=entity_id)
    # OosRecord.site_id is itself a nullable column (app/modules/qc/models.py) -- an unset one flows
    # through as EntitySnapshot.site_id=None, the same "any site" audience path oot_record/
    # supplier_qualification use, not a guessed value.
    return EntitySnapshot(
        state=oos.state, site_id=oos.site_id, entity_label=f"OOS {oos.oos_number}",
        link_path=f"/quality/oos?oos_id={oos.id}", last_actor_id=last_actor,
    )


async def _list_oos_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(OosRecord.id))).scalars().all())


async def _load_oot(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    oot = await session.get(OotRecord, entity_id, populate_existing=True)
    if oot is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="oot_record", aggregate_id=entity_id)
    # OotRecord has no site_id column at all (app/modules/qc/models.py) and no human-readable number
    # either -- and, per that page's own documented limitation, "no OOT browse/detail read in this
    # deployment" (frontend/src/app/quality/oos/page.tsx OotCard docstring), so there is no id-specific
    # page to deep-link to; this links to the tool that hosts the OOT close action.
    return EntitySnapshot(
        state=oot.state, site_id=None, entity_label=f"OOT record {str(oot.id)[:8]}",
        link_path="/quality/oos", last_actor_id=last_actor,
    )


async def _list_oot_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(OotRecord.id))).scalars().all())


async def _load_material_lot(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    lot = await session.get(MaterialLot, entity_id, populate_existing=True)
    if lot is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="material_lot", aggregate_id=entity_id)
    # /material-lots is a flat list page with no id-driven detail route, but its own search box already
    # filters by internal_lot server-side (app/modules/material/router.py) -- `?q=<internal_lot>`
    # (DataTable's own `initialQuery` prop, frontend/src/components/ui/DataTable.tsx) pre-fills it so the
    # reader lands straight on this lot instead of an empty list.
    return EntitySnapshot(
        state=lot.status, site_id=lot.site_id, entity_label=f"Lot {lot.internal_lot}",
        link_path=f"/material-lots?q={lot.internal_lot}", last_actor_id=last_actor,
    )


async def _list_material_lot_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(MaterialLot.id))).scalars().all())


async def _load_supplier_qualification(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    from app.modules.supplier_quality.models import Supplier, SupplierSite

    qualification = await session.get(SupplierQualification, entity_id, populate_existing=True)
    if qualification is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="supplier_qualification", aggregate_id=entity_id)
    supplier_row = (
        await session.execute(
            select(Supplier.id, Supplier.legal_name)
            .join(SupplierSite, SupplierSite.supplier_id == Supplier.id)
            .where(SupplierSite.id == qualification.supplier_site_id)
        )
    ).first()
    label = f"Supplier qualification -- {supplier_row.legal_name}" if supplier_row else f"Supplier qualification {qualification.id}"
    # Client follow-up (2026-10-06): the supplier detail view moved from a modal keyed by a `?supplier_id=`
    # query param to its own route, frontend/src/app/suppliers/[id]/page.tsx -- link straight to it.
    link_path = f"/suppliers/{supplier_row.id}" if supplier_row else "/suppliers"
    # SupplierQualification carries no site_id of its own (only supplier_site_id), and the real
    # `evaluate_policy(action="supplier_qualification.approve", site_id=None)` call site (commands.py)
    # already treats this as platform-wide, not site-scoped -- site_id=None here matches that exactly,
    # not a guess.
    return EntitySnapshot(
        state=qualification.status, site_id=None, entity_label=label,
        link_path=link_path, last_actor_id=last_actor,
    )


async def _list_supplier_qualification_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(SupplierQualification.id))).scalars().all())


async def _load_material_spec_version(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    version = await session.get(MaterialSpecificationVersion, entity_id, populate_existing=True)
    if version is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="material_specification_version", aggregate_id=entity_id)
    label = f"Material Spec {version.material_spec_business_id} v{version.version_no}"
    # material_specification/router.py's release endpoint calls evaluate_policy(..., site_id=None) --
    # "material_spec.release" held at any site suffices, the same platform-wide precedent
    # supplier_qualification/oos_record already set (their own notes above) -- not a guess.
    return EntitySnapshot(
        state=version.lifecycle_state, site_id=None, entity_label=label,
        link_path=f"/material-specifications?material_spec_version_id={version.id}", last_actor_id=last_actor,
    )


async def _list_material_spec_version_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(MaterialSpecificationVersion.id))).scalars().all())


async def _load_qc_test_specification(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    spec = await session.get(QcTestSpecification, entity_id, populate_existing=True)
    if spec is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="qc_test_specification", aggregate_id=entity_id)
    label = f"QC Spec {spec.spec_code} v{spec.version_no}"
    # qc/router.py's release endpoint calls evaluate_policy(..., site_id=None) -- same platform-wide
    # precedent as material_specification_version above (qc_test_specification has no site_id column
    # either), not a guess.
    return EntitySnapshot(
        state=spec.status, site_id=None, entity_label=label,
        link_path=f"/qc/specifications/{spec.id}", last_actor_id=last_actor,
    )


async def _list_qc_test_specification_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(QcTestSpecification.id))).scalars().all())


async def _load_product_version(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    version = await session.get(ProductVersion, entity_id, populate_existing=True)
    if version is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="product_version", aggregate_id=entity_id)
    label = f"Product {version.product_business_id} v{version.version_no}"
    # product_master/router.py's release endpoint calls evaluate_policy(..., site_id=None) -- same
    # platform-wide precedent as material_specification_version above, not a guess.
    return EntitySnapshot(
        state=version.lifecycle_state, site_id=None, entity_label=label,
        link_path=f"/product-master?product_version_id={version.id}", last_actor_id=last_actor,
    )


async def _list_product_version_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ProductVersion.id))).scalars().all())


async def _load_recipe_version(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    version = await session.get(RecipeVersion, entity_id, populate_existing=True)
    if version is None:
        return None
    family = await session.get(RecipeFamily, version.recipe_family_id, populate_existing=True)
    label = f"Recipe {family.recipe_code} v{version.version_no}" if family is not None else f"Recipe version {version.id}"
    last_actor = await _last_actor(session, aggregate_type="recipe_version", aggregate_id=entity_id)
    # recipe_master/router.py's release endpoint calls evaluate_policy(..., site_id=None) -- same
    # platform-wide precedent as material_specification_version/product_version above, not a guess.
    return EntitySnapshot(
        state=version.lifecycle_state, site_id=None, entity_label=label,
        link_path=f"/recipe-master?recipe_version_id={version.id}", last_actor_id=last_actor,
    )


async def _list_recipe_version_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(RecipeVersion.id))).scalars().all())


async def _load_equipment_asset(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    asset = await session.get(EquipmentAsset, entity_id, populate_existing=True)
    if asset is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="equipment_asset", aggregate_id=entity_id)
    # calibration_status, not state -- see this file's module docstring (Pass 4).
    return EntitySnapshot(
        state=asset.calibration_status or "", site_id=asset.site_id, entity_label=f"Equipment {asset.equipment_code}",
        link_path=f"/equipment/{asset.id}", last_actor_id=last_actor,
    )


async def _list_equipment_asset_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(EquipmentAsset.id))).scalars().all())


async def _load_cleaning_execution(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    execution = await session.get(CleaningExecution, entity_id, populate_existing=True)
    if execution is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="cleaning_execution", aggregate_id=entity_id)
    return EntitySnapshot(
        # cleaning/page.tsx reads this exact `?execution_id=` query param on mount (deep link wired
        # the same session this notification category was added, so the two match on purpose).
        state=execution.state, site_id=execution.site_id, entity_label=f"Cleaning {str(execution.id)[:8]}",
        link_path=f"/cleaning?execution_id={execution.id}", last_actor_id=last_actor,
    )


async def _list_cleaning_execution_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(CleaningExecution.id))).scalars().all())


async def _load_process_cycle(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    cycle = await session.get(ProcessCycle, entity_id, populate_existing=True)
    if cycle is None:
        return None
    asset = await session.get(EquipmentAsset, cycle.equipment_id, populate_existing=True)
    equipment_code = asset.equipment_code if asset is not None else str(cycle.equipment_id)[:8]
    last_actor = await _last_actor(session, aggregate_type="process_cycle", aggregate_id=entity_id)
    return EntitySnapshot(
        # sterilization/page.tsx reads this exact `?cycle_id=` query param on mount (deep link wired the
        # same session this notification category was added, same pattern as cleaning_execution above).
        state=cycle.state, site_id=cycle.site_id, entity_label=f"{cycle.process_type} cycle - {equipment_code}",
        link_path=f"/sterilization?cycle_id={cycle.id}", last_actor_id=last_actor,
    )


async def _list_process_cycle_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ProcessCycle.id))).scalars().all())


# =====================================================================================================
# Added gap-closure pass (client request, 2026-10-08): every entry below follows the exact same
# "genuine cross-user handoff" test the 22 entries above already apply -- a different permission-holder
# must act to clear the pending state, not just the same qualified performer finishing their own work.
# Candidates that turned out to be single-actor actions (e.g. batch_step.complete, equipment_asset.retire,
# fill_operation.start/complete, vault_object.release, lims_sample.cancel, every AI-governance action) were
# investigated and deliberately left out, same discipline as this file's own pre-existing risk_record note.
# `equipment_asset`'s own `state` column (hold/return_to_service) is also deliberately NOT added here: that
# aggregate_type key already exists above keyed on the *different* `calibration_status` column, and this
# registry's one-loader-one-state-string shape has no way to track two independent pending dimensions on
# the same aggregate without a real design change -- filed as a SPEC_GAP rather than guessed.
# =====================================================================================================


async def _load_step_result_correction(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    correction = await session.get(StepResultCorrection, entity_id, populate_existing=True)
    if correction is None:
        return None
    result = await session.get(StepResult, correction.original_result_id, populate_existing=True)
    step = await session.get(BatchStep, result.step_id, populate_existing=True) if result is not None else None
    batch = await session.get(Batch, step.batch_id, populate_existing=True) if step is not None else None
    label = (
        f"Correction -- step {step.recipe_step_code}, batch {batch.batch_number}"
        if step is not None and batch is not None else f"Step result correction {str(correction.id)[:8]}"
    )
    last_actor = await _last_actor(session, aggregate_type="step_result_correction", aggregate_id=entity_id)
    return EntitySnapshot(
        state=correction.status, site_id=batch.site_id if batch is not None else None, entity_label=label,
        link_path=f"/batch-execution/{batch.id}" if batch is not None else "/batch-execution", last_actor_id=last_actor,
    )


async def _list_step_result_correction_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(StepResultCorrection.id))).scalars().all())


async def _load_qa_review_package(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    package = await session.get(QaReviewPackage, entity_id, populate_existing=True)
    if package is None:
        return None
    batch = await session.get(Batch, package.batch_id, populate_existing=True)
    label = f"QA Review -- Batch {batch.batch_number}" if batch is not None else f"QA Review package {package.id}"
    last_actor = await _last_actor(session, aggregate_type="qa_review_package", aggregate_id=entity_id)
    return EntitySnapshot(
        state=package.state, site_id=package.site_id, entity_label=label,
        link_path="/qa-review", last_actor_id=last_actor,
    )


async def _list_qa_review_package_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(QaReviewPackage.id))).scalars().all())


async def _load_em_sample_or_reading(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    sample = await session.get(EmSampleOrReading, entity_id, populate_existing=True)
    if sample is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="em_sample_or_reading", aggregate_id=entity_id)
    return EntitySnapshot(
        state=sample.state, site_id=sample.site_id, entity_label=f"EM {sample.monitoring_type} sample {str(sample.id)[:8]}",
        link_path="/em", last_actor_id=last_actor,
    )


async def _list_em_sample_or_reading_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(EmSampleOrReading.id))).scalars().all())


async def _load_em_excursion(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    excursion = await session.get(EmExcursion, entity_id, populate_existing=True)
    if excursion is None:
        return None
    # EmExcursion has no state/status column (em_models.py) -- "pending impact assessment" is a
    # synthetic state derived from the nullable impact_assessed_at sentinel, same "read a derived signal,
    # not a raw state column" precedent as equipment_asset's own calibration_status loader above.
    state = "IMPACT_PENDING" if excursion.impact_assessed_at is None else "ASSESSED"
    last_actor = await _last_actor(session, aggregate_type="em_excursion", aggregate_id=entity_id)
    return EntitySnapshot(
        state=state, site_id=excursion.site_id, entity_label=f"EM excursion {str(excursion.id)[:8]}",
        link_path="/em", last_actor_id=last_actor,
    )


async def _list_em_excursion_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(EmExcursion.id))).scalars().all())


async def _load_aseptic_operation(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    operation = await session.get(AsepticOperation, entity_id, populate_existing=True)
    if operation is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="aseptic_operation", aggregate_id=entity_id)
    return EntitySnapshot(
        state=operation.state, site_id=operation.site_id, entity_label=f"Aseptic operation {str(operation.id)[:8]}",
        link_path="/aseptic", last_actor_id=last_actor,
    )


async def _list_aseptic_operation_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(AsepticOperation.id))).scalars().all())


async def _load_qc_test_order(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    order = await session.get(QcTestOrder, entity_id, populate_existing=True)
    if order is None:
        return None
    sample = await session.get(QcSample, order.sample_id, populate_existing=True)
    label = f"Test order -- sample {sample.sample_number}" if sample is not None else f"Test order {str(order.id)[:8]}"
    last_actor = await _last_actor(session, aggregate_type="qc_test_order", aggregate_id=entity_id)
    return EntitySnapshot(
        state=order.state, site_id=None, entity_label=label,
        link_path=f"/qc/samples/{order.sample_id}", last_actor_id=last_actor,
    )


async def _list_qc_test_order_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(QcTestOrder.id))).scalars().all())


async def _load_qc_result_correction(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    correction = await session.get(QcResultCorrection, entity_id, populate_existing=True)
    if correction is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="qc_result_correction", aggregate_id=entity_id)
    # No id-specific detail page exists for this record (same "no page to deep-link to" precedent as
    # oot_record above) -- the approval form on /qc takes a manually-typed correction id.
    return EntitySnapshot(
        state=correction.status, site_id=None, entity_label=f"QC result correction {str(correction.id)[:8]}",
        link_path="/qc", last_actor_id=last_actor,
    )


async def _list_qc_result_correction_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(QcResultCorrection.id))).scalars().all())


async def _load_material_receipt(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    receipt = await session.get(MaterialReceipt, entity_id, populate_existing=True)
    if receipt is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="material_receipt", aggregate_id=entity_id)
    # /material-receipts has no `?q=` deep-link wiring yet (unlike /material-lots) -- same "page exists,
    # id-specific pre-filter does not" limitation already true of several other entries below.
    return EntitySnapshot(
        state=receipt.state, site_id=receipt.site_id, entity_label=f"Receipt {receipt.receipt_number}",
        link_path="/material-receipts", last_actor_id=last_actor,
    )


async def _list_material_receipt_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(MaterialReceipt.id))).scalars().all())


async def _load_inventory_reservation(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    reservation = await session.get(InventoryReservation, entity_id, populate_existing=True)
    if reservation is None:
        return None
    material = await session.get(Material, reservation.material_id, populate_existing=True)
    label = f"FEFO override -- {material.code}" if material is not None else f"Inventory reservation {str(reservation.id)[:8]}"
    last_actor = await _last_actor(session, aggregate_type="inventory_reservation", aggregate_id=entity_id)
    return EntitySnapshot(
        state=reservation.status, site_id=reservation.site_id, entity_label=label,
        link_path="/inventory", last_actor_id=last_actor,
    )


async def _list_inventory_reservation_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(InventoryReservation.id))).scalars().all())


async def _load_inventory_adjustment_request(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    request = await session.get(InventoryAdjustmentRequest, entity_id, populate_existing=True)
    if request is None:
        return None
    lot = await session.get(MaterialLot, request.material_lot_id, populate_existing=True)
    label = f"Inventory adjustment -- lot {lot.internal_lot}" if lot is not None else f"Inventory adjustment {str(request.id)[:8]}"
    last_actor = await _last_actor(session, aggregate_type="inventory_adjustment_request", aggregate_id=entity_id)
    return EntitySnapshot(
        state=request.status, site_id=request.site_id, entity_label=label,
        link_path="/inventory", last_actor_id=last_actor,
    )


async def _list_inventory_adjustment_request_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(InventoryAdjustmentRequest.id))).scalars().all())


async def _load_dispensing_order(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    order = await session.get(DispensingOrder, entity_id, populate_existing=True)
    if order is None:
        return None
    material = await session.get(Material, order.material_id, populate_existing=True)
    batch = await session.get(Batch, order.batch_id, populate_existing=True)
    label = (
        f"Dispensing order -- {material.code} (Batch {batch.batch_number})"
        if material is not None and batch is not None else f"Dispensing order {str(order.id)[:8]}"
    )
    last_actor = await _last_actor(session, aggregate_type="dispensing_order", aggregate_id=entity_id)
    return EntitySnapshot(
        state=order.state, site_id=order.site_id, entity_label=label,
        link_path="/dispensing", last_actor_id=last_actor,
    )


async def _list_dispensing_order_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(DispensingOrder.id))).scalars().all())


async def _load_ddcp_profile_version(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    profile = await session.get(DdcpProfileVersion, entity_id, populate_existing=True)
    if profile is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="ddcp_profile_version", aggregate_id=entity_id)
    return EntitySnapshot(
        state=profile.state, site_id=profile.site_id, entity_label=f"DDCP Profile {profile.profile_code} v{profile.version}",
        link_path="/ddcp", last_actor_id=last_actor,
    )


async def _list_ddcp_profile_version_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(DdcpProfileVersion.id))).scalars().all())


async def _load_constituent_handoff(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    handoff = await session.get(ConstituentHandoff, entity_id, populate_existing=True)
    if handoff is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="constituent_handoff", aggregate_id=entity_id)
    label = f"Constituent handoff {handoff.from_constituent} -> {handoff.to_constituent}"
    return EntitySnapshot(
        state=handoff.state, site_id=handoff.site_id, entity_label=label,
        link_path=f"/ddcp?batch_id={handoff.batch_id}", last_actor_id=last_actor,
    )


async def _list_constituent_handoff_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ConstituentHandoff.id))).scalars().all())


async def _load_rule(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    rule = await session.get(RuleDefinition, entity_id, populate_existing=True)
    if rule is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="rule", aggregate_id=entity_id)
    # RuleDefinition has no site_id column (org-wide rule catalogue) -- same platform-wide precedent as
    # material_specification_version/product_version/recipe_version above.
    return EntitySnapshot(
        state=rule.status, site_id=None, entity_label=f"Rule {rule.rule_id} v{rule.semantic_version}",
        link_path="/rules", last_actor_id=last_actor,
    )


async def _list_rule_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(RuleDefinition.rule_object_id))).scalars().all())


async def _load_uom(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    uom = await session.get(UnitOfMeasure, entity_id, populate_existing=True)
    if uom is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="uom", aggregate_id=entity_id)
    return EntitySnapshot(
        state=uom.status, site_id=None, entity_label=f"UOM {uom.code} v{uom.version}",
        link_path="/rules", last_actor_id=last_actor,
    )


async def _list_uom_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(UnitOfMeasure.uom_id))).scalars().all())


async def _load_manufacturing_calculation(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    calc = await session.get(ManufacturingCalculation, entity_id, populate_existing=True)
    if calc is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="manufacturing_calculation", aggregate_id=entity_id)
    return EntitySnapshot(
        state=calc.state, site_id=calc.site_id, entity_label=f"{calc.calculation_type} calculation {str(calc.id)[:8]}",
        link_path="/yield", last_actor_id=last_actor,
    )


async def _list_manufacturing_calculation_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ManufacturingCalculation.id))).scalars().all())


async def _load_reconciliation_record(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    record = await session.get(ReconciliationRecord, entity_id, populate_existing=True)
    if record is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="reconciliation_record", aggregate_id=entity_id)
    return EntitySnapshot(
        state=record.state, site_id=record.site_id, entity_label=f"{record.reconciliation_type} reconciliation {str(record.id)[:8]}",
        link_path="/yield", last_actor_id=last_actor,
    )


async def _list_reconciliation_record_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ReconciliationRecord.id))).scalars().all())


async def _load_privileged_access_request(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    request = await session.get(PrivilegedAccessRequest, entity_id, populate_existing=True)
    if request is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="privileged_access_request", aggregate_id=entity_id)
    return EntitySnapshot(
        state=request.state, site_id=None, entity_label=f"Privileged access request ({request.requested_role})",
        link_path="/security", last_actor_id=last_actor,
    )


async def _list_privileged_access_request_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(PrivilegedAccessRequest.id))).scalars().all())


async def _load_privileged_session(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    privileged_session = await session.get(PrivilegedSession, entity_id, populate_existing=True)
    if privileged_session is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="privileged_session", aggregate_id=entity_id)
    return EntitySnapshot(
        state=privileged_session.state, site_id=None,
        entity_label=f"Privileged session ({privileged_session.session_type})",
        link_path="/security", last_actor_id=last_actor,
    )


async def _list_privileged_session_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(PrivilegedSession.id))).scalars().all())


async def _load_security_incident(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    incident = await session.get(SecurityIncident, entity_id, populate_existing=True)
    if incident is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="security_incident", aggregate_id=entity_id)
    return EntitySnapshot(
        state=incident.state, site_id=None, entity_label=f"Security Incident {incident.incident_number}",
        link_path="/security", last_actor_id=last_actor,
    )


async def _list_security_incident_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(SecurityIncident.id))).scalars().all())


async def _load_regulatory_report(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    report = await session.get(RegulatoryReport, entity_id, populate_existing=True)
    if report is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="regulatory_report", aggregate_id=entity_id)
    return EntitySnapshot(
        state=report.state, site_id=report.site_id, entity_label=f"Regulatory report v{report.report_version}",
        link_path="/postmarket", last_actor_id=last_actor,
    )


async def _list_regulatory_report_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(RegulatoryReport.id))).scalars().all())


async def _load_signal_mapping(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    mapping = await session.get(SignalMapping, entity_id, populate_existing=True)
    if mapping is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="signal_mapping", aggregate_id=entity_id)
    return EntitySnapshot(
        state=mapping.lifecycle_state, site_id=mapping.site_id,
        entity_label=f"Signal mapping {mapping.mapping_key} v{mapping.version}",
        link_path="/machine-integration", last_actor_id=last_actor,
    )


async def _list_signal_mapping_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(SignalMapping.id))).scalars().all())


async def _load_erp_external_mapping(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    mapping = await session.get(ErpExternalMapping, entity_id, populate_existing=True)
    if mapping is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="erp_external_mapping", aggregate_id=entity_id)
    # ErpExternalMapping carries no site_id of its own; the owning ErpInstance's is nullable (an
    # org-wide instance), so site_id=None here is the honest "not necessarily site-scoped" value rather
    # than a guessed join -- same precedent as supplier_qualification/material_spec_version above.
    return EntitySnapshot(
        state=mapping.mapping_status, site_id=None,
        entity_label=f"ERP mapping {mapping.entity_type}:{mapping.external_id}",
        link_path="/integrations/erp", last_actor_id=last_actor,
    )


async def _list_erp_external_mapping_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ErpExternalMapping.id))).scalars().all())


async def _load_erp_mapping_conflict(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    conflict = await session.get(ErpMappingConflict, entity_id, populate_existing=True)
    if conflict is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="erp_mapping_conflict", aggregate_id=entity_id)
    return EntitySnapshot(
        state=conflict.status, site_id=None, entity_label=f"ERP mapping conflict ({conflict.field_name})",
        link_path="/integrations/erp", last_actor_id=last_actor,
    )


async def _list_erp_mapping_conflict_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ErpMappingConflict.id))).scalars().all())


async def _load_training_assignment(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    assignment = await session.get(TrainingAssignment, entity_id, populate_existing=True)
    if assignment is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="training_assignment", aggregate_id=entity_id)
    return EntitySnapshot(
        state=assignment.state, site_id=assignment.site_id, entity_label=f"Training assignment {str(assignment.id)[:8]}",
        link_path="/training", last_actor_id=last_actor,
    )


async def _list_training_assignment_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(TrainingAssignment.id))).scalars().all())


async def _load_audit_finding(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    finding = await session.get(AuditFinding, entity_id, populate_existing=True)
    if finding is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="audit_finding", aggregate_id=entity_id)
    return EntitySnapshot(
        state=finding.state, site_id=finding.site_id, entity_label=f"Audit finding {finding.finding_number}",
        link_path=f"/audits/{finding.audit_id}", last_actor_id=last_actor,
    )


async def _list_audit_finding_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(AuditFinding.id))).scalars().all())


async def _load_quality_metric_definition(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    definition = await session.get(QualityMetricDefinition, entity_id, populate_existing=True)
    if definition is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="quality_metric_definition", aggregate_id=entity_id)
    return EntitySnapshot(
        state=definition.state, site_id=definition.site_id, entity_label=f"Quality metric {definition.metric_code}",
        link_path="/quality-metrics", last_actor_id=last_actor,
    )


async def _list_quality_metric_definition_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(QualityMetricDefinition.id))).scalars().all())


async def _load_quality_metric_snapshot(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    snapshot = await session.get(QualityMetricSnapshot, entity_id, populate_existing=True)
    if snapshot is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="quality_metric_snapshot", aggregate_id=entity_id)
    return EntitySnapshot(
        state=snapshot.state, site_id=snapshot.site_id, entity_label=f"Quality metric snapshot {str(snapshot.id)[:8]}",
        link_path="/quality-metrics", last_actor_id=last_actor,
    )


async def _list_quality_metric_snapshot_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(QualityMetricSnapshot.id))).scalars().all())


# ---- Validation (WP-12/WP-14) -- none of this module's record types were previously registered. Every
# /validation page here is a generic forms console with no per-record detail route or `?id=` deep-link
# convention (unlike cleaning/sterilization/etc.), so every link_path below lands on the bare module page
# rather than a pre-filtered row -- a real frontend gap, not something a registry loader can supply.


async def _load_validation_master_plan(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    plan = await session.get(ValidationMasterPlan, entity_id, populate_existing=True)
    if plan is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="validation_master_plan", aggregate_id=entity_id)
    return EntitySnapshot(
        state=plan.state, site_id=plan.site_id, entity_label=f"VMP {plan.plan_number}",
        link_path="/validation", last_actor_id=last_actor,
    )


async def _list_validation_master_plan_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ValidationMasterPlan.id))).scalars().all())


async def _load_function_risk_assessment(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    row = await session.get(FunctionRiskAssessment, entity_id, populate_existing=True)
    if row is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="function_risk_assessment", aggregate_id=entity_id)
    return EntitySnapshot(
        state=row.state, site_id=None, entity_label=f"Function risk {row.function_ref} v{row.function_version}",
        link_path="/validation", last_actor_id=last_actor,
    )


async def _list_function_risk_assessment_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(FunctionRiskAssessment.id))).scalars().all())


async def _load_validation_test_definition(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    row = await session.get(ValidationTestDefinition, entity_id, populate_existing=True)
    if row is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="validation_test_definition", aggregate_id=entity_id)
    return EntitySnapshot(
        state=row.state, site_id=None, entity_label=f"Validation test {row.test_code} v{row.version}",
        link_path="/validation", last_actor_id=last_actor,
    )


async def _list_validation_test_definition_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ValidationTestDefinition.id))).scalars().all())


async def _load_pq_scenario(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    row = await session.get(PqScenario, entity_id, populate_existing=True)
    if row is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="pq_scenario", aggregate_id=entity_id)
    return EntitySnapshot(
        state=row.state, site_id=row.site_id, entity_label=f"PQ scenario {row.scenario_number}",
        link_path="/validation", last_actor_id=last_actor,
    )


async def _list_pq_scenario_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(PqScenario.id))).scalars().all())


async def _load_migration_run(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    run = await session.get(MigrationRun, entity_id, populate_existing=True)
    if run is None:
        return None
    plan = await session.get(MigrationValidationPlan, run.plan_id, populate_existing=True)
    label = f"Migration run #{run.run_number} ({plan.plan_number})" if plan is not None else f"Migration run {str(run.id)[:8]}"
    last_actor = await _last_actor(session, aggregate_type="migration_run", aggregate_id=entity_id)
    return EntitySnapshot(
        state=run.state, site_id=plan.site_id if plan is not None else None, entity_label=label,
        link_path="/validation", last_actor_id=last_actor,
    )


async def _list_migration_run_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(MigrationRun.id))).scalars().all())


async def _load_validation_summary_report(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    report = await session.get(ValidationSummaryReport, entity_id, populate_existing=True)
    if report is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="validation_summary_report", aggregate_id=entity_id)
    return EntitySnapshot(
        state=report.state, site_id=report.site_id, entity_label=f"VSR {report.report_number} ({report.release_ref})",
        link_path="/validation", last_actor_id=last_actor,
    )


async def _list_validation_summary_report_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ValidationSummaryReport.id))).scalars().all())


async def _load_periodic_validation_review(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    row = await session.get(PeriodicValidationReview, entity_id, populate_existing=True)
    if row is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="periodic_validation_review", aggregate_id=entity_id)
    label = f"Periodic validation review ({row.release_ref}, {row.period_start.date()}-{row.period_end.date()})"
    return EntitySnapshot(
        state=row.state, site_id=None, entity_label=label,
        link_path="/validation", last_actor_id=last_actor,
    )


async def _list_periodic_validation_review_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(PeriodicValidationReview.id))).scalars().all())


async def _load_validated_release_authorization(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    row = await session.get(ValidatedReleaseAuthorization, entity_id, populate_existing=True)
    if row is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="validated_release_authorization", aggregate_id=entity_id)
    return EntitySnapshot(
        state=row.state, site_id=row.site_id, entity_label=f"Release authorization {row.authorization_number}",
        link_path="/validation/go-live", last_actor_id=last_actor,
    )


async def _list_validated_release_authorization_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ValidatedReleaseAuthorization.id))).scalars().all())


async def _load_data_integrity_test_profile(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    profile = await session.get(DataIntegrityTestProfile, entity_id, populate_existing=True)
    if profile is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="data_integrity_test_profile", aggregate_id=entity_id)
    return EntitySnapshot(
        state=profile.state, site_id=None, entity_label=f"Data integrity profile ({profile.data_class})",
        link_path="/validation", last_actor_id=last_actor,
    )


async def _list_data_integrity_test_profile_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(DataIntegrityTestProfile.id))).scalars().all())


async def _load_interface_validation_profile(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    profile = await session.get(InterfaceValidationProfile, entity_id, populate_existing=True)
    if profile is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="interface_validation_profile", aggregate_id=entity_id)
    return EntitySnapshot(
        state=profile.state, site_id=None, entity_label=f"Interface profile ({profile.provider_or_device})",
        link_path="/validation", last_actor_id=last_actor,
    )


async def _list_interface_validation_profile_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(InterfaceValidationProfile.id))).scalars().all())


async def _load_security_qualification_suite(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    suite = await session.get(SecurityQualificationSuite, entity_id, populate_existing=True)
    if suite is None:
        return None
    last_actor = await _last_actor(session, aggregate_type="security_qualification_suite", aggregate_id=entity_id)
    return EntitySnapshot(
        state=suite.state, site_id=None, entity_label=f"Security qualification suite ({suite.release_ref})",
        link_path="/validation", last_actor_id=last_actor,
    )


async def _list_security_qualification_suite_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(SecurityQualificationSuite.id))).scalars().all())


# IQ/OQ/DR execution rows have no column that distinguishes "approved" from "awaiting approval" --
# `status` stays PASS/FAIL forever and only `approved_by_user_id` changes (commands_iq.py/commands_oq.py/
# commands_dr.py). Same "derive the real signal, don't guess a raw column" precedent as em_excursion and
# equipment_asset.calibration_status above: the synthetic "PENDING_APPROVAL" sentinel never collides with
# a real status value, and resolves correctly the moment approved_by_user_id is set.


async def _load_iq_execution(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    row = await session.get(IqExecution, entity_id, populate_existing=True)
    if row is None:
        return None
    protocol = await session.get(IqProtocol, row.protocol_id, populate_existing=True)
    state = "APPROVED" if row.approved_by_user_id is not None else (
        "PENDING_APPROVAL" if row.status in ("PASS", "FAIL") else row.status
    )
    label = f"IQ execution {str(row.id)[:8]} (protocol {protocol.environment})" if protocol is not None else f"IQ execution {str(row.id)[:8]}"
    last_actor = await _last_actor(session, aggregate_type="iq_execution", aggregate_id=entity_id)
    return EntitySnapshot(
        state=state, site_id=protocol.site_id if protocol is not None else None, entity_label=label,
        link_path="/validation", last_actor_id=last_actor,
    )


async def _list_iq_execution_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(IqExecution.id))).scalars().all())


async def _load_oq_execution(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    row = await session.get(OqExecution, entity_id, populate_existing=True)
    if row is None:
        return None
    state = "APPROVED" if row.approved_by_user_id is not None else "PENDING_APPROVAL"
    last_actor = await _last_actor(session, aggregate_type="oq_execution", aggregate_id=entity_id)
    return EntitySnapshot(
        state=state, site_id=None, entity_label=f"OQ execution {str(row.id)[:8]}",
        link_path="/validation", last_actor_id=last_actor,
    )


async def _list_oq_execution_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(OqExecution.id))).scalars().all())


async def _load_dr_qualification_execution(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    row = await session.get(DrQualificationExecution, entity_id, populate_existing=True)
    if row is None:
        return None
    # FAIL can never be approved (commands_dr.py rejects it outright) -- only a PASS awaits approval.
    state = "APPROVED" if row.approved_by_user_id is not None else ("PENDING_APPROVAL" if row.status == "PASS" else row.status)
    last_actor = await _last_actor(session, aggregate_type="dr_qualification_execution", aggregate_id=entity_id)
    return EntitySnapshot(
        state=state, site_id=None, entity_label=f"DR qualification execution {str(row.id)[:8]}",
        link_path="/validation", last_actor_id=last_actor,
    )


async def _list_dr_qualification_execution_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(DrQualificationExecution.id))).scalars().all())


async def _load_validation_exception(session: AsyncSession, entity_id: uuid.UUID) -> EntitySnapshot | None:
    row = await session.get(ValidationException, entity_id, populate_existing=True)
    if row is None:
        return None
    # `disposition="OPEN"` means both "needs triage" and, once triaged, "needs disposition" --
    # triage_exception() never changes `disposition` (commands_exception.py), so the real signal is
    # whether triaged_by_user_id has been set yet. Same derived-signal precedent as the IQ/OQ/DR loaders
    # above. Any non-OPEN disposition is terminal for this registry's purposes.
    if row.disposition != "OPEN":
        state = row.disposition
    elif row.triaged_by_user_id is None:
        state = "NEEDS_TRIAGE"
    else:
        state = "NEEDS_DISPOSITION"
    last_actor = await _last_actor(session, aggregate_type="validation_exception", aggregate_id=entity_id)
    return EntitySnapshot(
        state=state, site_id=None, entity_label=f"Validation exception ({row.exception_type}, {row.severity})",
        link_path="/validation", last_actor_id=last_actor,
    )


async def _list_validation_exception_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list((await session.execute(select(ValidationException.id))).scalars().all())


WORKFLOW_SPECS: dict[str, WorkflowNotificationSpec] = {
    "release_scope": WorkflowNotificationSpec(
        aggregate_type="release_scope",
        nats_subject="gxp.v1.release_scope.>",
        pending_states={
            # release/models.py ALLOWED_TRANSITIONS: "eligible" is the state release_scope_decision()
            # (POST .../release, permission "release.release") acts on next.
            "eligible": PendingStateRule(
                category="batch_release_pending", required_permission_code="release.release",
                signature_record_type="release_scope", signature_action="release",
            ),
        },
        loader=_load_release_scope,
        list_all_ids=_list_release_scope_ids,
    ),
    "deviation_record": WorkflowNotificationSpec(
        aggregate_type="deviation_record",
        nats_subject="gxp.v1.deviation_record.>",
        pending_states={
            # qms/commands.py disposition_deviation(): entered from IMPACT_ASSESSMENT, permission
            # "qms_deviation.disposition".
            "IMPACT_ASSESSMENT": PendingStateRule(
                category="deviation_disposition_pending", required_permission_code="qms_deviation.disposition",
                signature_record_type="deviation_record", signature_action="disposition",
            ),
            # qms/commands.py close_deviation(): entered from DISPOSITION, permission "qms_deviation.close".
            "DISPOSITION": PendingStateRule(
                category="deviation_close_pending", required_permission_code="qms_deviation.close",
                signature_record_type="deviation_record", signature_action="close",
            ),
        },
        loader=_load_deviation,
        list_all_ids=_list_deviation_ids,
    ),
    "capa_record": WorkflowNotificationSpec(
        aggregate_type="capa_record",
        nats_subject="gxp.v1.capa_record.>",
        pending_states={
            # capa_commands.py plan_capa(): entered from OPEN, permission "capa.plan".
            "OPEN": PendingStateRule(
                category="capa_plan_pending", required_permission_code="capa.plan",
                signature_record_type="capa_record", signature_action="plan",
            ),
            # capa_commands.py close_capa(): entered from EFFECTIVENESS_REVIEW, permission "capa.close".
            "EFFECTIVENESS_REVIEW": PendingStateRule(
                category="capa_close_pending", required_permission_code="capa.close",
                signature_record_type="capa_record", signature_action="close",
            ),
        },
        loader=_load_capa,
        list_all_ids=_list_capa_ids,
    ),
    "controlled_document_version": WorkflowNotificationSpec(
        aggregate_type="controlled_document_version",
        nats_subject="gxp.v1.controlled_document_version.>",
        pending_states={
            # document_commands.py release_draft(): entered from REVIEW, permission "document.release".
            # (The event_type string this aggregate publishes under, "DocumentVersionReleased", is reused
            # for create/submit/release alike -- this registry never keys off event_type for exactly that
            # reason; see consumer.py's docstring.)
            "REVIEW": PendingStateRule(
                category="document_release_pending", required_permission_code="document.release",
                signature_record_type="controlled_document_version", signature_action="release",
            ),
        },
        loader=_load_document_version,
        list_all_ids=_list_document_version_ids,
    ),
    "nonconformance_record": WorkflowNotificationSpec(
        aggregate_type="nonconformance_record",
        nats_subject="gxp.v1.nonconformance_record.>",
        pending_states={
            # ncr_commands.py disposition_ncr(): entered from EVALUATION, permission "ncr.disposition".
            "EVALUATION": PendingStateRule(
                category="ncr_disposition_pending", required_permission_code="ncr.disposition",
                signature_record_type="nonconformance_record", signature_action="disposition",
            ),
            # ncr_commands.py verify_ncr(): entered from any of the 5 disposition-outcome states, all
            # equally "awaiting verification" (ncr_models.py NCR_ALLOWED_TRANSITIONS treats them as
            # interchangeable -- each allows the same next-state set), permission "ncr.verify".
            **{
                state: PendingStateRule(
                    category="ncr_verification_pending", required_permission_code="ncr.verify",
                    signature_record_type="nonconformance_record", signature_action="verify",
                )
                for state in ("REWORK", "REPAIR", "RETURN", "SCRAP", "USE_AS_IS")
            },
            # ncr_commands.py close_ncr(): entered from VERIFICATION, permission "ncr.close".
            "VERIFICATION": PendingStateRule(
                category="ncr_close_pending", required_permission_code="ncr.close",
                signature_record_type="nonconformance_record", signature_action="close",
            ),
        },
        loader=_load_ncr,
        list_all_ids=_list_ncr_ids,
    ),
    "complaint_record": WorkflowNotificationSpec(
        aggregate_type="complaint_record",
        nats_subject="gxp.v1.complaint_record.>",
        pending_states={
            # complaint_commands.py assess_reportability(): entered from NO_INVESTIGATION_JUSTIFIED or
            # REPORTABILITY_ASSESSMENT, permission "complaint.reportability".
            **{
                state: PendingStateRule(
                    category="complaint_reportability_pending", required_permission_code="complaint.reportability",
                    signature_record_type="complaint_record", signature_action="reportability",
                )
                for state in ("NO_INVESTIGATION_JUSTIFIED", "REPORTABILITY_ASSESSMENT")
            },
            # complaint_commands.py close_complaint(): entered from RESPONSE, permission "complaint.close".
            "RESPONSE": PendingStateRule(
                category="complaint_close_pending", required_permission_code="complaint.close",
                signature_record_type="complaint_record", signature_action="close",
            ),
        },
        loader=_load_complaint,
        list_all_ids=_list_complaint_ids,
    ),
    "change_control": WorkflowNotificationSpec(
        aggregate_type="change_control",
        nats_subject="gxp.v1.change_control.>",
        pending_states={
            # change_commands.py approve_change() (non-emergency path): entered from IMPACT_ASSESSMENT,
            # permission "change.approve".
            "IMPACT_ASSESSMENT": PendingStateRule(
                category="change_approval_pending", required_permission_code="change.approve",
                signature_record_type="change_control", signature_action="approve",
            ),
            # change_commands.py close_change(): entered from EFFECTIVE, permission "change.close".
            "EFFECTIVE": PendingStateRule(
                category="change_close_pending", required_permission_code="change.close",
                signature_record_type="change_control", signature_action="close",
            ),
        },
        loader=_load_change_control,
        list_all_ids=_list_change_control_ids,
    ),
    "scar_record": WorkflowNotificationSpec(
        aggregate_type="scar_record",
        nats_subject="gxp.v1.scar_record.>",
        pending_states={
            # scar_commands.py review_scar(): entered from SUPPLIER_RESPONSE, permission "scar.review".
            "SUPPLIER_RESPONSE": PendingStateRule(
                category="scar_review_pending", required_permission_code="scar.review",
                signature_record_type="scar_record", signature_action="review",
            ),
            # scar_commands.py close_scar(): entered from EFFECTIVENESS, permission "scar.close".
            "EFFECTIVENESS": PendingStateRule(
                category="scar_close_pending", required_permission_code="scar.close",
                signature_record_type="scar_record", signature_action="close",
            ),
        },
        loader=_load_scar,
        list_all_ids=_list_scar_ids,
    ),
    "field_action": WorkflowNotificationSpec(
        aggregate_type="field_action",
        nats_subject="gxp.v1.field_action.>",
        pending_states={
            # field_action_commands.py approve_field_action(): entered from REGULATORY_DECISION, permission
            # "field_action.approve".
            "REGULATORY_DECISION": PendingStateRule(
                category="field_action_approval_pending", required_permission_code="field_action.approve",
                signature_record_type="field_action", signature_action="approve",
            ),
            # field_action_commands.py close_field_action(): entered from EFFECTIVENESS (the one state not
            # already blocked by its own closure guard), permission "field_action.close".
            "EFFECTIVENESS": PendingStateRule(
                category="field_action_close_pending", required_permission_code="field_action.close",
                signature_record_type="field_action", signature_action="close",
            ),
        },
        loader=_load_field_action,
        list_all_ids=_list_field_action_ids,
    ),
    "internal_audit": WorkflowNotificationSpec(
        aggregate_type="internal_audit",
        nats_subject="gxp.v1.internal_audit.>",
        pending_states={
            # internal_audit_commands.py close_internal_audit(): entered from FINDINGS_OPEN, permission
            # "internal_audit.close".
            "FINDINGS_OPEN": PendingStateRule(
                category="internal_audit_close_pending", required_permission_code="internal_audit.close",
                signature_record_type="internal_audit", signature_action="close",
            ),
        },
        loader=_load_internal_audit,
        list_all_ids=_list_internal_audit_ids,
    ),
    "risk_record": WorkflowNotificationSpec(
        aggregate_type="risk_record",
        nats_subject="gxp.v1.risk_record.>",
        pending_states={
            # risk_commands.py accept_risk(): entered from RESIDUAL_ASSESSMENT, permission "risk.accept".
            # No signature pointer -- accept_risk() has no resolve_signature_requirement() call at all
            # (confirmed by reading risk_commands.py; only review_risk() does, and that action has no
            # discrete "pending" state distinguishable from risk_record's normal long-lived ACCEPTED state,
            # so it is deliberately not modeled here -- see this file's own note below).
            "RESIDUAL_ASSESSMENT": PendingStateRule(
                category="risk_acceptance_pending", required_permission_code="risk.accept",
            ),
        },
        loader=_load_risk,
        list_all_ids=_list_risk_ids,
    ),
    "oos_record": WorkflowNotificationSpec(
        aggregate_type="oos_record",
        nats_subject="gxp.v1.oos_record.>",
        pending_states={
            # qc/commands.py approve_disposition(): entered from "final_disposition", permission
            # "oos_record.disposition". (Lowercase snake_case states -- oos_record uses a different state
            # vocabulary than the QMS modules above.)
            "final_disposition": PendingStateRule(
                category="oos_disposition_pending", required_permission_code="oos_record.disposition",
                signature_record_type="oos_record", signature_action="disposition",
            ),
            # qc/commands.py close_oos(): entered from "qa_approval", permission "oos_record.close".
            "qa_approval": PendingStateRule(
                category="oos_close_pending", required_permission_code="oos_record.close",
                signature_record_type="oos_record", signature_action="close",
            ),
        },
        loader=_load_oos,
        list_all_ids=_list_oos_ids,
    ),
    "oot_record": WorkflowNotificationSpec(
        aggregate_type="oot_record",
        nats_subject="gxp.v1.oot_record.>",
        pending_states={
            # qc/commands.py close_oot(): entered from "open", permission "oot_record.close".
            "open": PendingStateRule(
                category="oot_close_pending", required_permission_code="oot_record.close",
                signature_record_type="oot_record", signature_action="close",
            ),
        },
        loader=_load_oot,
        list_all_ids=_list_oot_ids,
    ),
    "material_lot": WorkflowNotificationSpec(
        aggregate_type="material_lot",
        nats_subject="gxp.v1.material_lot.>",
        pending_states={
            # material/commands.py release_material_lot() (_disposition_material_lot_v2, decision=
            # "released"): PRE_DISPOSITION_LOT_STATES also allows quarantine/sampling/testing/retest_due,
            # but only "qc_disposition_pending" -- the state the model itself names for this -- is treated
            # as the actual handoff point here (those earlier states represent the lot still moving through
            # QC, not yet actually sitting there awaiting a release/reject call in the ordinary flow).
            # permission "material_lot.release" (reject is a real alternative outcome, same "only the
            # release/go path" precedent release_scope's own single "release.release" category already
            # set for its own release/hold/reject trio).
            "qc_disposition_pending": PendingStateRule(
                category="material_lot_release_pending", required_permission_code="material_lot.release",
                signature_record_type="material_lot", signature_action="release",
            ),
        },
        loader=_load_material_lot,
        list_all_ids=_list_material_lot_ids,
    ),
    "supplier_qualification": WorkflowNotificationSpec(
        aggregate_type="supplier_qualification",
        nats_subject="gxp.v1.supplier_qualification.>",
        pending_states={
            # supplier_quality/commands.py approve_qualification(): entered from "requested" or
            # "in_review", permission "supplier_qualification.approve".
            **{
                state: PendingStateRule(
                    category="supplier_qualification_approval_pending",
                    required_permission_code="supplier_qualification.approve",
                    signature_record_type="supplier_qualification", signature_action="approve",
                )
                for state in ("requested", "in_review")
            },
        },
        loader=_load_supplier_qualification,
        list_all_ids=_list_supplier_qualification_ids,
    ),
    "material_specification_version": WorkflowNotificationSpec(
        aggregate_type="material_specification_version",
        nats_subject="gxp.v1.material_specification_version.>",
        pending_states={
            # material_specification/commands.py release_material_spec_version(): the version is created
            # directly into "draft" (no separate submit step in this module, unlike product/recipe below)
            # and stays there until released, permission "material_spec.release".
            "draft": PendingStateRule(
                category="material_spec_release_pending", required_permission_code="material_spec.release",
                signature_record_type="material_specification_version", signature_action="release",
            ),
        },
        loader=_load_material_spec_version,
        list_all_ids=_list_material_spec_version_ids,
    ),
    "qc_test_specification": WorkflowNotificationSpec(
        aggregate_type="qc_test_specification",
        nats_subject="gxp.v1.qc_test_specification.>",
        pending_states={
            # qc/commands.py create_test_specification_draft(): created directly into "draft" (no separate
            # submit step, same treatment as material_specification_version above), stays there until
            # release_test_specification(), permission "qc_test_specification.release".
            "draft": PendingStateRule(
                category="qc_test_specification_release_pending",
                required_permission_code="qc_test_specification.release",
                signature_record_type="qc_test_specification", signature_action="release",
            ),
        },
        loader=_load_qc_test_specification,
        list_all_ids=_list_qc_test_specification_ids,
    ),
    "product_version": WorkflowNotificationSpec(
        aggregate_type="product_version",
        nats_subject="gxp.v1.product_version.>",
        pending_states={
            # product_master/commands.py release_product_version(): entered from "under_review" (reached
            # via submit_draft(), permission "product.submit"), permission "product.release".
            "under_review": PendingStateRule(
                category="product_release_pending", required_permission_code="product.release",
                signature_record_type="product_version", signature_action="release",
            ),
        },
        loader=_load_product_version,
        list_all_ids=_list_product_version_ids,
    ),
    "recipe_version": WorkflowNotificationSpec(
        aggregate_type="recipe_version",
        nats_subject="gxp.v1.recipe_version.>",
        pending_states={
            # recipe_master/commands.py release_recipe_version(): entered from "under_review" (reached via
            # submit_draft()), permission "recipe.release".
            "under_review": PendingStateRule(
                category="recipe_release_pending", required_permission_code="recipe.release",
                signature_record_type="recipe_version", signature_action="release",
            ),
        },
        loader=_load_recipe_version,
        list_all_ids=_list_recipe_version_ids,
    ),
    "equipment_asset": WorkflowNotificationSpec(
        aggregate_type="equipment_asset",
        nats_subject="gxp.v1.equipment_asset.>",
        pending_states={
            # equipment/commands.py record_calibration() creation branch: a passing calibration sets
            # asset.calibration_status = "pending_approval" (not yet reviewed), resolved by the same
            # command's approval branch, permission "equipment_asset.approve_calibration".
            "pending_approval": PendingStateRule(
                category="equipment_calibration_approval_pending",
                required_permission_code="equipment_asset.approve_calibration",
            ),
        },
        loader=_load_equipment_asset,
        list_all_ids=_list_equipment_asset_ids,
    ),
    "cleaning_execution": WorkflowNotificationSpec(
        aggregate_type="cleaning_execution",
        nats_subject="gxp.v1.cleaning_execution.>",
        pending_states={
            # cleaning_commands.py complete_cleaning() transitions CLEANING -> CLEANING_VERIFICATION;
            # verify_cleaning() is the next command, state-guarded to that state, permission
            # "cleaning_execution.verify" -- same independent-verifier shape as em_sample_or_reading's
            # "review" (not itself registered here, but an identical RBAC pattern).
            "CLEANING_VERIFICATION": PendingStateRule(
                category="cleaning_verification_pending", required_permission_code="cleaning_execution.verify",
                signature_record_type="cleaning_execution", signature_action="verify",
            ),
            # verify_cleaning() sets state=HOLD + requires_deviation=True on a "fail" result -- nothing
            # else in this module can resolve that; the actionable next step is someone opening a
            # deviation ("qms_deviation.create"), so that's the permission this category gates on,
            # same "pending state -> the permission that would resolve it" shape as every other category
            # in this registry. A "pass" result reaches CLEAN instead, which is terminal (not listed
            # here) -- nothing is pending, same reasoning as every other terminal state in this file.
            "HOLD": PendingStateRule(
                category="cleaning_requires_deviation", required_permission_code="qms_deviation.create",
            ),
        },
        loader=_load_cleaning_execution,
        list_all_ids=_list_cleaning_execution_ids,
    ),
    "process_cycle": WorkflowNotificationSpec(
        aggregate_type="process_cycle",
        nats_subject="gxp.v1.process_cycle.>",
        pending_states={
            # sterilization_commands.py record_cycle_data() leaves a normally-completed cycle in
            # REVIEW_PENDING, or escalates straight to HOLD on a controller-reported critical_alarm;
            # review_cycle() accepts review from either state (state-guarded identically), so both share
            # one category -- same multi-state-group shape as NCR's REWORK/REPAIR/RETURN/SCRAP/USE_AS_IS
            # above. Permission "process_cycle.review".
            **{
                state: PendingStateRule(
                    category="sterilization_review_pending", required_permission_code="process_cycle.review",
                    signature_record_type="process_cycle", signature_action="review",
                )
                for state in ("REVIEW_PENDING", "HOLD")
            },
            # review_cycle() sets state=FAILED + requires_deviation=True on a "reject" decision -- nothing
            # else in this module can resolve that; the actionable next step is someone opening a
            # deviation, same "pending state -> the permission that would resolve it" shape as
            # cleaning_execution's own HOLD -> qms_deviation.create category above. An "accept" reaches
            # ACCEPTED instead, which is terminal (not listed here).
            "FAILED": PendingStateRule(
                category="sterilization_requires_deviation", required_permission_code="qms_deviation.create",
            ),
        },
        loader=_load_process_cycle,
        list_all_ids=_list_process_cycle_ids,
    ),
    "step_result_correction": WorkflowNotificationSpec(
        aggregate_type="step_result_correction",
        nats_subject="gxp.v1.step_result_correction.>",
        pending_states={
            # batch_execution/commands.py approve_step_result_correction(): entered at request time
            # ("requested"), SoD-enforced in code (requester != approver), permission "batch_step.correct".
            "requested": PendingStateRule(
                category="batch_step_correction_pending", required_permission_code="batch_step.correct",
                signature_record_type="batch_step_result", signature_action="correct",
            ),
        },
        loader=_load_step_result_correction,
        list_all_ids=_list_step_result_correction_ids,
    ),
    "qa_review_package": WorkflowNotificationSpec(
        aggregate_type="qa_review_package",
        nats_subject="gxp.v1.qa_review_package.>",
        pending_states={
            # qa_review/commands.py complete_review_package(): entered at creation ("READY_FOR_REVIEW")
            # or re-entered on reopen ("REOPENED"), permission "qa_review.execute" (QA Reviewer only --
            # the Operator/Supervisor roles that drive the batch itself do not hold it). This is the real
            # mechanism behind "batch review" -- the seeded "batch.review" RBAC permission is never
            # actually checked anywhere in code (confirmed by repo-wide grep); Batch itself has no review
            # transition at all.
            **{
                state: PendingStateRule(
                    category="qa_review_pending", required_permission_code="qa_review.execute",
                    signature_record_type="qa_review_package", signature_action="complete",
                )
                for state in ("READY_FOR_REVIEW", "REOPENED")
            },
        },
        loader=_load_qa_review_package,
        list_all_ids=_list_qa_review_package_ids,
    ),
    "em_sample_or_reading": WorkflowNotificationSpec(
        aggregate_type="em_sample_or_reading",
        nats_subject="gxp.v1.em_sample_or_reading.>",
        pending_states={
            # em_commands.py review_em_result(): entered from RESULT_PENDING (record_em_result()),
            # SoD-enforced in code (reviewer != performer, SIG-FR-018), permission "em_sample.review".
            "RESULT_PENDING": PendingStateRule(
                category="em_review_pending", required_permission_code="em_sample.review",
                signature_record_type="em_sample_or_reading", signature_action="review",
            ),
        },
        loader=_load_em_sample_or_reading,
        list_all_ids=_list_em_sample_or_reading_ids,
    ),
    "em_excursion": WorkflowNotificationSpec(
        aggregate_type="em_excursion",
        nats_subject="gxp.v1.em_excursion.>",
        pending_states={
            # em_commands.py record_excursion_impact(): unsigned (no Document 106 row), permission
            # "em_excursion.impact" held only by the QA-Reviewer-class role, not the EM technician/
            # analyst who triggered the excursion via record_em_result().
            "IMPACT_PENDING": PendingStateRule(
                category="em_excursion_impact_pending", required_permission_code="em_excursion.impact",
            ),
        },
        loader=_load_em_excursion,
        list_all_ids=_list_em_excursion_ids,
    ),
    "aseptic_operation": WorkflowNotificationSpec(
        aggregate_type="aseptic_operation",
        nats_subject="gxp.v1.aseptic_operation.>",
        pending_states={
            # aseptic_commands.py start_operation(): entered at creation ("PREPARATION"), permission
            # "aseptic_operation.start" -- held only by Aseptic Supervisor (seed.py's own comment:
            # "Aseptic Supervisor authorizes start -- Document 106 row 113's 'Production Supervisor or
            # qualified issuer'"), never by Aseptic Operator (who holds create/intervention/event/
            # complete instead). Client-confirmed genuine cross-role handoff, 2026-10-09.
            "PREPARATION": PendingStateRule(
                category="aseptic_start_pending", required_permission_code="aseptic_operation.start",
                signature_record_type="aseptic_operation", signature_action="start",
            ),
            # aseptic_commands.py record_intervention()/record_event(): either can set state=HOLD +
            # requires_deviation=True, and nothing in this module ever clears it -- complete_operation()
            # explicitly refuses while requires_deviation is true. Same "the actionable next step is
            # opening a deviation" shape as cleaning_execution's own HOLD category and process_cycle's
            # own FAILED category above.
            "HOLD": PendingStateRule(
                category="aseptic_requires_deviation", required_permission_code="qms_deviation.create",
            ),
        },
        loader=_load_aseptic_operation,
        list_all_ids=_list_aseptic_operation_ids,
    ),
    "qc_test_order": WorkflowNotificationSpec(
        aggregate_type="qc_test_order",
        nats_subject="gxp.v1.qc_test_order.>",
        pending_states={
            # qc/commands.py review_test_order(): entered from "analyst_complete" (complete_test_order()),
            # SoD-enforced in code (reviewer != assigned_analyst_id), permission "qc_test_order.review".
            "analyst_complete": PendingStateRule(
                category="qc_test_order_review_pending", required_permission_code="qc_test_order.review",
                signature_record_type="qc_test_order", signature_action="review",
            ),
        },
        loader=_load_qc_test_order,
        list_all_ids=_list_qc_test_order_ids,
    ),
    "qc_result_correction": WorkflowNotificationSpec(
        aggregate_type="qc_result_correction",
        nats_subject="gxp.v1.qc_result_correction.>",
        pending_states={
            # qc/commands.py approve_result_correction(): entered at request time ("requested"),
            # SoD-enforced in code (approver != requester), permission "qc_result.correct". The signature
            # policy's own record_type is "qc_result" (not "qc_result_correction") -- the exact pair
            # resolve_signature_requirement() is called with.
            "requested": PendingStateRule(
                category="qc_result_correction_pending", required_permission_code="qc_result.correct",
                signature_record_type="qc_result", signature_action="correct",
            ),
        },
        loader=_load_qc_result_correction,
        list_all_ids=_list_qc_result_correction_ids,
    ),
    "material_receipt": WorkflowNotificationSpec(
        aggregate_type="material_receipt",
        nats_subject="gxp.v1.material_receipt.>",
        pending_states={
            # material/commands.py disposition_held_receipt(): entered from "discrepancy_hold"
            # (Client Topic 4, SG-... 2026-10-02), permission "material_receipt.disposition".
            "discrepancy_hold": PendingStateRule(
                category="material_receipt_disposition_pending", required_permission_code="material_receipt.disposition",
                signature_record_type="material_receipt", signature_action="disposition",
            ),
        },
        loader=_load_material_receipt,
        list_all_ids=_list_material_receipt_ids,
    ),
    "inventory_reservation": WorkflowNotificationSpec(
        aggregate_type="inventory_reservation",
        nats_subject="gxp.v1.inventory_reservation.>",
        pending_states={
            # material/commands.py approve_reservation_override(): entered at creation of a non-FEFO
            # override request ("override_pending", Client Topic 8 / SG-083), permission
            # "inventory_reservation.approve_override". A parallel "reject_override" permission also
            # resolves this same state (reject_reservation_override()) -- modeling only the forward/
            # approve path, same "only the release/approve path, not its reject sibling" precedent as
            # material_lot.release/supplier_qualification.approve/oos_record.disposition above.
            "override_pending": PendingStateRule(
                category="inventory_override_pending", required_permission_code="inventory_reservation.approve_override",
                signature_record_type="inventory_reservation", signature_action="approve_override",
            ),
        },
        loader=_load_inventory_reservation,
        list_all_ids=_list_inventory_reservation_ids,
    ),
    "inventory_adjustment_request": WorkflowNotificationSpec(
        aggregate_type="inventory_adjustment_request",
        nats_subject="gxp.v1.inventory_adjustment_request.>",
        pending_states={
            # material/commands.py approve_adjustment_request(): entered at creation ("requested",
            # Document 106 row 55), permission "inventory_adjustment_request.approve". Same
            # "forward path only" precedent as inventory_reservation above re: the parallel "reject"
            # permission.
            "requested": PendingStateRule(
                category="inventory_adjustment_approval_pending", required_permission_code="inventory_adjustment_request.approve",
                signature_record_type="inventory_adjustment_request", signature_action="approve",
            ),
        },
        loader=_load_inventory_adjustment_request,
        list_all_ids=_list_inventory_adjustment_request_ids,
    ),
    "dispensing_order": WorkflowNotificationSpec(
        aggregate_type="dispensing_order",
        nats_subject="gxp.v1.dispensing_order.>",
        pending_states={
            # material/commands.py verify_dispensing() (via _dispensing_sign): entered from "started",
            # SoD-enforced in code (verifier != performed_by_user_id), permission "dispensing_order.verify".
            "started": PendingStateRule(
                category="dispensing_verification_pending", required_permission_code="dispensing_order.verify",
                signature_record_type="dispensing_order", signature_action="verify",
            ),
        },
        loader=_load_dispensing_order,
        list_all_ids=_list_dispensing_order_ids,
    ),
    "ddcp_profile_version": WorkflowNotificationSpec(
        aggregate_type="ddcp_profile_version",
        nats_subject="gxp.v1.ddcp_profile_version.>",
        pending_states={
            # ddcp/commands.py release_injectable_profile_version() (shared by all 4 DDCP product-type
            # routers): entered at creation ("DRAFT"), permission "ddcp_profile.release" (QA Releaser --
            # "DDCP Engineer", who authors, does not hold it; SG-148 Client Topic 12).
            "DRAFT": PendingStateRule(
                category="ddcp_profile_release_pending", required_permission_code="ddcp_profile.release",
                signature_record_type="ddcp_profile_version", signature_action="release",
            ),
        },
        loader=_load_ddcp_profile_version,
        list_all_ids=_list_ddcp_profile_version_ids,
    ),
    "constituent_handoff": WorkflowNotificationSpec(
        aggregate_type="constituent_handoff",
        nats_subject="gxp.v1.constituent_handoff.>",
        pending_states={
            # ddcp/inhalation_commands.py decide_constituent_handoff(): entered at creation ("PENDING"),
            # permission "ddcp_constituent.decide" (SG-148 Client Topic 12).
            "PENDING": PendingStateRule(
                category="constituent_handoff_pending", required_permission_code="ddcp_constituent.decide",
                signature_record_type="constituent_handoff", signature_action="decide",
            ),
        },
        loader=_load_constituent_handoff,
        list_all_ids=_list_constituent_handoff_ids,
    ),
    "rule": WorkflowNotificationSpec(
        aggregate_type="rule",
        nats_subject="gxp.v1.rule.>",
        pending_states={
            # rules/commands.py release_rule(): entered from "validated" (draft -> validated -> release),
            # permission "rules.release" (QA Releaser -- "Process Engineer", who holds "rules.author",
            # does not hold it).
            "validated": PendingStateRule(
                category="rule_release_pending", required_permission_code="rules.release",
                signature_record_type="rule", signature_action="release",
            ),
        },
        loader=_load_rule,
        list_all_ids=_list_rule_ids,
    ),
    "uom": WorkflowNotificationSpec(
        aggregate_type="uom",
        nats_subject="gxp.v1.uom.>",
        pending_states={
            # rules/uom_commands.py release_uom(): entered at creation ("draft"), permission
            # "rules.release" (same QA-Releaser-only permission rule.release reuses).
            "draft": PendingStateRule(
                category="uom_release_pending", required_permission_code="rules.release",
                signature_record_type="uom", signature_action="release",
            ),
        },
        loader=_load_uom,
        list_all_ids=_list_uom_ids,
    ),
    "manufacturing_calculation": WorkflowNotificationSpec(
        aggregate_type="manufacturing_calculation",
        nats_subject="gxp.v1.manufacturing_calculation.>",
        pending_states={
            # yield_reconciliation/commands.py verify_record(): entered from "CALCULATED" or
            # "OUT_OF_LIMIT", SoD-enforced in code (verifier != evaluated_by_user_id, SIG-FR-018),
            # permission "reconciliation.verify".
            **{
                state: PendingStateRule(
                    category="manufacturing_calculation_verification_pending", required_permission_code="reconciliation.verify",
                    signature_record_type="manufacturing_calculation", signature_action="verify",
                )
                for state in ("CALCULATED", "OUT_OF_LIMIT")
            },
        },
        loader=_load_manufacturing_calculation,
        list_all_ids=_list_manufacturing_calculation_ids,
    ),
    "reconciliation_record": WorkflowNotificationSpec(
        aggregate_type="reconciliation_record",
        nats_subject="gxp.v1.reconciliation_record.>",
        pending_states={
            # Same shared verify_record() dispatch as manufacturing_calculation above, for the other
            # record kind. Entered from "ACCEPTABLE" or "OUT_OF_TOLERANCE".
            **{
                state: PendingStateRule(
                    category="reconciliation_verification_pending", required_permission_code="reconciliation.verify",
                    signature_record_type="reconciliation_record", signature_action="verify",
                )
                for state in ("ACCEPTABLE", "OUT_OF_TOLERANCE")
            },
        },
        loader=_load_reconciliation_record,
        list_all_ids=_list_reconciliation_record_ids,
    ),
    "privileged_access_request": WorkflowNotificationSpec(
        aggregate_type="privileged_access_request",
        nats_subject="gxp.v1.privileged_access_request.>",
        pending_states={
            # privileged_access_commands.py approve_privileged_access(): entered at creation
            # ("PENDING_APPROVAL"), SoD-enforced in code (approver != subject_id), permission
            # "privileged_access.approve".
            "PENDING_APPROVAL": PendingStateRule(
                category="privileged_access_approval_pending", required_permission_code="privileged_access.approve",
                signature_record_type="privileged_access_request", signature_action="approve",
            ),
        },
        loader=_load_privileged_access_request,
        list_all_ids=_list_privileged_access_request_ids,
    ),
    "privileged_session": WorkflowNotificationSpec(
        aggregate_type="privileged_session",
        nats_subject="gxp.v1.privileged_session.>",
        pending_states={
            # privileged_access_commands.py close_privileged_session(): entered at open ("ACTIVE"),
            # SoD-enforced in code (closer != opened_by, except the documented break-glass self-close
            # exception), permission "privileged_session.close".
            "ACTIVE": PendingStateRule(
                category="privileged_session_close_pending", required_permission_code="privileged_session.close",
                signature_record_type="privileged_session", signature_action="close",
            ),
        },
        loader=_load_privileged_session,
        list_all_ids=_list_privileged_session_ids,
    ),
    "security_incident": WorkflowNotificationSpec(
        aggregate_type="security_incident",
        nats_subject="gxp.v1.security_incident.>",
        pending_states={
            # incident_commands.py close_incident(): reachable once state="GXP_IMPACT_ASSESSED" (set by
            # record_gxp_impact()) and containment_actions is non-empty, SoD-enforced in code (closer !=
            # owner_subject_id), permission "security_incident.close".
            "GXP_IMPACT_ASSESSED": PendingStateRule(
                category="security_incident_close_pending", required_permission_code="security_incident.close",
                signature_record_type="security_incident", signature_action="close",
            ),
        },
        loader=_load_security_incident,
        list_all_ids=_list_security_incident_ids,
    ),
    "regulatory_report": WorkflowNotificationSpec(
        aggregate_type="regulatory_report",
        nats_subject="gxp.v1.regulatory_report.>",
        pending_states={
            # reportability_commands.py approve_regulatory_report(): entered at creation ("DRAFT"),
            # permission "regulatory_report.approve" -- held only by QA Releaser, a different role than
            # "Postmarket Regulatory Affairs" (which holds create/followup/generate_payload/submit).
            # Document 106/seed.py's "SG-157 fails closed" note for this action is stale -- the policy
            # row is actually seeded and resolves (confirmed by reading seed.py directly).
            "DRAFT": PendingStateRule(
                category="regulatory_report_approval_pending", required_permission_code="regulatory_report.approve",
                signature_record_type="regulatory_report", signature_action="approve",
            ),
        },
        loader=_load_regulatory_report,
        list_all_ids=_list_regulatory_report_ids,
    ),
    "signal_mapping": WorkflowNotificationSpec(
        aggregate_type="signal_mapping",
        nats_subject="gxp.v1.signal_mapping.>",
        pending_states={
            # machine_integration/commands.py release_signal_mapping(): entered from "draft" or "tested",
            # SoD-enforced in code (releaser != drafted_by_user_id), permission "signal_mapping.release".
            **{
                state: PendingStateRule(
                    category="signal_mapping_release_pending", required_permission_code="signal_mapping.release",
                    signature_record_type="signal_mapping", signature_action="release",
                )
                for state in ("draft", "tested")
            },
        },
        loader=_load_signal_mapping,
        list_all_ids=_list_signal_mapping_ids,
    ),
    "erp_external_mapping": WorkflowNotificationSpec(
        aggregate_type="erp_external_mapping",
        nats_subject="gxp.v1.erp_external_mapping.>",
        pending_states={
            # erp/commands.py approve_master_mapping(): entered from "PROPOSED" (or re-entered from
            # "SUSPENDED"), permission "erp_mapping.approve". Unsigned (signature_required=False, SG-122)
            # -- same "no signature pointer, still a real RBAC-gated pending queue" precedent as
            # risk_record.accept/equipment_asset.approve_calibration above.
            **{
                state: PendingStateRule(category="erp_mapping_approval_pending", required_permission_code="erp_mapping.approve")
                for state in ("PROPOSED", "SUSPENDED")
            },
        },
        loader=_load_erp_external_mapping,
        list_all_ids=_list_erp_external_mapping_ids,
    ),
    "erp_mapping_conflict": WorkflowNotificationSpec(
        aggregate_type="erp_mapping_conflict",
        nats_subject="gxp.v1.erp_mapping_conflict.>",
        pending_states={
            # erp/commands.py resolve_master_conflict(): entered at creation ("OPEN"), permission
            # "erp_mapping.resolve_conflict". Unsigned, same precedent as erp_external_mapping above.
            "OPEN": PendingStateRule(category="erp_mapping_conflict_pending", required_permission_code="erp_mapping.resolve_conflict"),
        },
        loader=_load_erp_mapping_conflict,
        list_all_ids=_list_erp_mapping_conflict_ids,
    ),
    "training_assignment": WorkflowNotificationSpec(
        aggregate_type="training_assignment",
        nats_subject="gxp.v1.training_assignment.>",
        pending_states={
            # training_commands.py assess_assignment(): entered from "ASSESSMENT_PENDING"
            # (complete_assignment(), when the requirement requires assessment), SoD-enforced in code
            # (assessor disqualified when == assignment.subject_id), permission
            # "training.assignment.assess".
            "ASSESSMENT_PENDING": PendingStateRule(
                category="training_assessment_pending", required_permission_code="training.assignment.assess",
                signature_record_type="training_assignment", signature_action="assess",
            ),
        },
        loader=_load_training_assignment,
        list_all_ids=_list_training_assignment_ids,
    ),
    "audit_finding": WorkflowNotificationSpec(
        aggregate_type="audit_finding",
        nats_subject="gxp.v1.audit_finding.>",
        pending_states={
            # internal_audit_commands.py verify_finding(): entered from "RESPONSE_SUBMITTED"
            # (respond_to_finding()), permission "internal_audit.finding.verify". A sub-entity of
            # internal_audit, not covered by that aggregate's own "close" category above.
            "RESPONSE_SUBMITTED": PendingStateRule(
                category="audit_finding_verification_pending", required_permission_code="internal_audit.finding.verify",
                signature_record_type="audit_finding", signature_action="verify",
            ),
        },
        loader=_load_audit_finding,
        list_all_ids=_list_audit_finding_ids,
    ),
    "quality_metric_definition": WorkflowNotificationSpec(
        aggregate_type="quality_metric_definition",
        nats_subject="gxp.v1.quality_metric_definition.>",
        pending_states={
            # quality_metrics_commands.py release_metric_definition(): entered at creation ("DRAFT"),
            # permission "quality_metric.definition.release".
            "DRAFT": PendingStateRule(
                category="quality_metric_release_pending", required_permission_code="quality_metric.definition.release",
                signature_record_type="quality_metric_definition", signature_action="release",
            ),
        },
        loader=_load_quality_metric_definition,
        list_all_ids=_list_quality_metric_definition_ids,
    ),
    "quality_metric_snapshot": WorkflowNotificationSpec(
        aggregate_type="quality_metric_snapshot",
        nats_subject="gxp.v1.quality_metric_snapshot.>",
        pending_states={
            # quality_metrics_commands.py freeze_management_review_package(): entered at calculation
            # ("COMPLETE"), permission "quality_metric.management_review".
            "COMPLETE": PendingStateRule(
                category="quality_metric_management_review_pending", required_permission_code="quality_metric.management_review",
                signature_record_type="quality_metric_snapshot", signature_action="management_review",
            ),
        },
        loader=_load_quality_metric_snapshot,
        list_all_ids=_list_quality_metric_snapshot_ids,
    ),
    "validation_master_plan": WorkflowNotificationSpec(
        aggregate_type="validation_master_plan",
        nats_subject="gxp.v1.validation_master_plan.>",
        pending_states={
            "DRAFT": PendingStateRule(
                category="validation_plan_release_pending", required_permission_code="validation.plan.release",
                signature_record_type="validation_master_plan", signature_action="release",
            ),
        },
        loader=_load_validation_master_plan,
        list_all_ids=_list_validation_master_plan_ids,
    ),
    "function_risk_assessment": WorkflowNotificationSpec(
        aggregate_type="function_risk_assessment",
        nats_subject="gxp.v1.function_risk_assessment.>",
        pending_states={
            "DRAFT": PendingStateRule(
                category="function_risk_approval_pending", required_permission_code="validation.function_risk.approve",
                signature_record_type="function_risk_assessment", signature_action="approve",
            ),
        },
        loader=_load_function_risk_assessment,
        list_all_ids=_list_function_risk_assessment_ids,
    ),
    "validation_test_definition": WorkflowNotificationSpec(
        aggregate_type="validation_test_definition",
        nats_subject="gxp.v1.validation_test_definition.>",
        pending_states={
            "DRAFT": PendingStateRule(
                category="validation_test_definition_approval_pending", required_permission_code="validation.test_definition.approve",
                signature_record_type="validation_test_definition", signature_action="approve",
            ),
        },
        loader=_load_validation_test_definition,
        list_all_ids=_list_validation_test_definition_ids,
    ),
    "pq_scenario": WorkflowNotificationSpec(
        aggregate_type="pq_scenario",
        nats_subject="gxp.v1.pq_scenario.>",
        pending_states={
            # commands_pq.py approve_pq_scenario(): entered from "IN_EXECUTION" or
            # "READY_FOR_ACCEPTANCE", SoD-enforced in code (approver != authored_by_user_id, Document
            # 106 row 151), permission "validation.pq.approve".
            **{
                state: PendingStateRule(
                    category="pq_scenario_approval_pending", required_permission_code="validation.pq.approve",
                    signature_record_type="pq_scenario", signature_action="approve",
                )
                for state in ("IN_EXECUTION", "READY_FOR_ACCEPTANCE")
            },
        },
        loader=_load_pq_scenario,
        list_all_ids=_list_pq_scenario_ids,
    ),
    "migration_run": WorkflowNotificationSpec(
        aggregate_type="migration_run",
        nats_subject="gxp.v1.migration_run.>",
        pending_states={
            # commands_migration.py approve_migration_run(): entered from "COMPLETED", SoD-enforced in
            # code (approver != the migration plan's own author, Document 106 row 153), permission
            # "validation.migration.approve".
            "COMPLETED": PendingStateRule(
                category="migration_run_approval_pending", required_permission_code="validation.migration.approve",
                signature_record_type="migration_run", signature_action="approve",
            ),
        },
        loader=_load_migration_run,
        list_all_ids=_list_migration_run_ids,
    ),
    "validation_summary_report": WorkflowNotificationSpec(
        aggregate_type="validation_summary_report",
        nats_subject="gxp.v1.validation_summary_report.>",
        pending_states={
            # commands_vsr.py approve_validation_summary(): entered at generation ("DRAFT"),
            # SoD-enforced in code (approver != recommendation_by_user_id, VSR-FR-014), permission
            # "validation.vsr.approve".
            "DRAFT": PendingStateRule(
                category="vsr_approval_pending", required_permission_code="validation.vsr.approve",
                signature_record_type="validation_summary_report", signature_action="approve",
            ),
        },
        loader=_load_validation_summary_report,
        list_all_ids=_list_validation_summary_report_ids,
    ),
    "periodic_validation_review": WorkflowNotificationSpec(
        aggregate_type="periodic_validation_review",
        nats_subject="gxp.v1.periodic_validation_review.>",
        pending_states={
            # commands_periodic.py decide_periodic_review(): entered at creation ("DRAFT"),
            # SoD-enforced in code (decider != performed_by_user_id), permission
            # "validation.periodic_review.decide". Note the signature action string is "decision", not
            # "decide" -- the exact pair commands_periodic.py's own resolve_signature() call uses.
            "DRAFT": PendingStateRule(
                category="periodic_validation_review_decision_pending", required_permission_code="validation.periodic_review.decide",
                signature_record_type="periodic_validation_review", signature_action="decision",
            ),
        },
        loader=_load_periodic_validation_review,
        list_all_ids=_list_periodic_validation_review_ids,
    ),
    "validated_release_authorization": WorkflowNotificationSpec(
        aggregate_type="validated_release_authorization",
        nats_subject="gxp.v1.validated_release_authorization.>",
        pending_states={
            # commands_vsr.py verify_deployment_against_validation_release(): entered from "AUTHORIZED",
            # SoD-enforced in code (checker independent of every production_performer_user_ids entry),
            # permission "validation.release_auth.deployment_check". ("authorize" itself is a signed
            # CREATE, not a pending-state resolution -- deliberately not modeled here.)
            "AUTHORIZED": PendingStateRule(
                category="release_auth_deployment_check_pending", required_permission_code="validation.release_auth.deployment_check",
                signature_record_type="validated_release_authorization", signature_action="deployment_check",
            ),
        },
        loader=_load_validated_release_authorization,
        list_all_ids=_list_validated_release_authorization_ids,
    ),
    "data_integrity_test_profile": WorkflowNotificationSpec(
        aggregate_type="data_integrity_test_profile",
        nats_subject="gxp.v1.data_integrity_test_profile.>",
        pending_states={
            # commands_integrity.py approve_data_integrity_profile(): "EFFECTIVE" is both the initial and
            # the only pre-approval value (no intermediate "tests done" marker exists), so this notifies
            # from creation rather than from a later readiness point -- a real, if early, signal, not a
            # guess (same tradeoff this category's own research explicitly surfaced).
            "EFFECTIVE": PendingStateRule(
                category="data_integrity_profile_approval_pending", required_permission_code="validation.data_integrity.approve",
                signature_record_type="data_integrity_test_profile", signature_action="approve",
            ),
        },
        loader=_load_data_integrity_test_profile,
        list_all_ids=_list_data_integrity_test_profile_ids,
    ),
    "interface_validation_profile": WorkflowNotificationSpec(
        aggregate_type="interface_validation_profile",
        nats_subject="gxp.v1.interface_validation_profile.>",
        pending_states={
            # commands_interface.py approve_interface_profile(): same "EFFECTIVE from creation" shape as
            # data_integrity_test_profile above.
            "EFFECTIVE": PendingStateRule(
                category="interface_profile_approval_pending", required_permission_code="validation.interface.approve",
                signature_record_type="interface_validation_profile", signature_action="approve",
            ),
        },
        loader=_load_interface_validation_profile,
        list_all_ids=_list_interface_validation_profile_ids,
    ),
    "security_qualification_suite": WorkflowNotificationSpec(
        aggregate_type="security_qualification_suite",
        nats_subject="gxp.v1.security_qualification_suite.>",
        pending_states={
            # commands_security.py approve_security_qualification(): same "notifies from creation" shape
            # as data_integrity_test_profile/interface_validation_profile above -- "PLANNED" is the only
            # pre-approval value; the real gate is a findings-blocker check, not a state transition.
            "PLANNED": PendingStateRule(
                category="security_qualification_approval_pending", required_permission_code="validation.security.approve",
                signature_record_type="security_qualification_suite", signature_action="approve",
            ),
        },
        loader=_load_security_qualification_suite,
        list_all_ids=_list_security_qualification_suite_ids,
    ),
    "iq_execution": WorkflowNotificationSpec(
        aggregate_type="iq_execution",
        nats_subject="gxp.v1.iq_execution.>",
        pending_states={
            # commands_iq.py approve_iq_execution(): synthetic "PENDING_APPROVAL" (see _load_iq_execution
            # docstring above) covers both PASS and FAIL, since Document 106 row 148 allows approving
            # either (SoD-enforced in code: approver != performer_user_id).
            "PENDING_APPROVAL": PendingStateRule(
                category="iq_execution_approval_pending", required_permission_code="validation.iq.approve",
                signature_record_type="iq_execution", signature_action="approve",
            ),
        },
        loader=_load_iq_execution,
        list_all_ids=_list_iq_execution_ids,
    ),
    "oq_execution": WorkflowNotificationSpec(
        aggregate_type="oq_execution",
        nats_subject="gxp.v1.oq_execution.>",
        pending_states={
            # commands_oq.py approve_oq_execution(): synthetic "PENDING_APPROVAL" (see
            # _load_oq_execution above) -- the command gates purely on approved_by_user_id being unset,
            # not on any status value.
            "PENDING_APPROVAL": PendingStateRule(
                category="oq_execution_approval_pending", required_permission_code="validation.oq.approve",
                signature_record_type="oq_execution", signature_action="approve",
            ),
        },
        loader=_load_oq_execution,
        list_all_ids=_list_oq_execution_ids,
    ),
    "dr_qualification_execution": WorkflowNotificationSpec(
        aggregate_type="dr_qualification_execution",
        nats_subject="gxp.v1.dr_qualification_execution.>",
        pending_states={
            # commands_dr.py approve_dr_execution(): synthetic "PENDING_APPROVAL" (see
            # _load_dr_qualification_execution above) -- only a PASS is ever approvable, a FAIL is
            # rejected outright by the command itself.
            "PENDING_APPROVAL": PendingStateRule(
                category="dr_qualification_approval_pending", required_permission_code="validation.dr.approve",
                signature_record_type="dr_qualification_execution", signature_action="approve",
            ),
        },
        loader=_load_dr_qualification_execution,
        list_all_ids=_list_dr_qualification_execution_ids,
    ),
    "validation_exception": WorkflowNotificationSpec(
        aggregate_type="validation_exception",
        nats_subject="gxp.v1.validation_exception.>",
        pending_states={
            # commands_exception.py triage_exception()/disposition_exception(): synthetic
            # NEEDS_TRIAGE/NEEDS_DISPOSITION states (see _load_validation_exception above) -- disposition
            # stays "OPEN" through triage, so a raw-column read cannot tell the two pending steps apart.
            # Both SoD-enforced in code (actor != requested_by_user_id / != triaged_by_user_id).
            "NEEDS_TRIAGE": PendingStateRule(
                category="validation_exception_triage_pending", required_permission_code="validation.exception.triage",
                signature_record_type="validation_exception", signature_action="triage",
            ),
            "NEEDS_DISPOSITION": PendingStateRule(
                category="validation_exception_disposition_pending", required_permission_code="validation.exception.disposition",
                signature_record_type="validation_exception", signature_action="disposition",
            ),
        },
        loader=_load_validation_exception,
        list_all_ids=_list_validation_exception_ids,
    ),
}

# category -> its rule, across every aggregate type -- `service.py::list_visible_notifications()` needs
# this to find a notification's signature-policy pointer (if any) from its stored `category` alone.
# Category names are unique by construction (each is written once above); a collision here is a
# programming error in this file, not a runtime condition to handle gracefully.
RULE_BY_CATEGORY: dict[str, PendingStateRule] = {
    rule.category: rule for spec in WORKFLOW_SPECS.values() for rule in spec.categories.values()
}
