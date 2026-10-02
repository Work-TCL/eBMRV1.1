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
Not covered: everything outside these ~18 aggregate types (validation, DDCP, postmarket, security
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
from app.modules.batch_execution.models import Batch
from app.modules.material.models import MaterialLot
from app.modules.material_specification.models import MaterialSpecificationVersion
from app.modules.product_master.models import ProductVersion
from app.modules.qc.models import OosRecord, OotRecord, QcTestSpecification
from app.modules.qms.capa_models import CapaRecord
from app.modules.qms.change_models import ChangeControl
from app.modules.qms.complaint_models import ComplaintRecord
from app.modules.qms.document_models import ControlledDocument, ControlledDocumentVersion
from app.modules.qms.field_action_models import FieldAction
from app.modules.qms.internal_audit_models import InternalAudit
from app.modules.qms.models import DeviationRecord
from app.modules.qms.ncr_models import NonconformanceRecord
from app.modules.qms.risk_models import RiskRecord
from app.modules.qms.scar_models import ScarRecord
from app.modules.recipe_master.models import RecipeFamily, RecipeVersion
from app.modules.release.models import ReleaseScope
from app.modules.supplier_quality.models import SupplierQualification


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
        link_path=f"/documents?document_code={document.document_code}", last_actor_id=last_actor,
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
    # /suppliers already opens a supplier's detail modal on a row click, keyed by supplier id
    # (frontend/src/app/suppliers/page.tsx `selected` state) -- `?supplier_id=<id>` deep-links straight
    # into that same modal instead of the bare list.
    link_path = f"/suppliers?supplier_id={supplier_row.id}" if supplier_row else "/suppliers"
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
}

# category -> its rule, across every aggregate type -- `service.py::list_visible_notifications()` needs
# this to find a notification's signature-policy pointer (if any) from its stored `category` alone.
# Category names are unique by construction (each is written once above); a collision here is a
# programming error in this file, not a runtime condition to handle gracefully.
RULE_BY_CATEGORY: dict[str, PendingStateRule] = {
    rule.category: rule for spec in WORKFLOW_SPECS.values() for rule in spec.categories.values()
}
