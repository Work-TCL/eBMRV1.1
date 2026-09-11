"""Idempotently sync the Document 106 signature-policy floor into an already-seeded deployment.

`scripts.seed` also upserts `signature.signature_policies` from `SIGNATURE_POLICY_FLOOR`, but only as
part of a run that unconditionally creates a fresh organization, site and demo-user set -- so it cannot
be re-run against a live database just to pick up a new/changed policy row. This script is the narrow,
re-runnable half, same precedent as `sync_permissions.py`: it upserts existing rows by
(record_type, action) and creates any that are missing, resolving `required_role_id` against roles that
already exist in this deployment. Never deletes a row -- unlike `sync_permissions.py`'s role grants,
removing a signature-policy row would flip a resolved action back to fail-closed (SIGNATURE_POLICY_UNRESOLVED)
for every actor, which is exactly the failure mode AG-07/SIG-FR-004 exist to prevent by accident.

Run with: .venv/bin/python -m scripts.sync_signature_policies
"""

import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.modules.iam.models import Role
from app.modules.signature.models import SignaturePolicy
from scripts.seed import SIGNATURE_POLICY_CHAIN_FLOOR, SIGNATURE_POLICY_FLOOR


async def sync() -> None:
    created = updated = skipped = 0
    async with SessionLocal() as session:
        async with session.begin():
            for record_type, action, meaning, role_name, independent, sig_required, reason_required in SIGNATURE_POLICY_FLOOR:
                required_role_id = None
                if role_name:
                    role = (await session.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
                    if role is None:
                        # A role this deployment hasn't created yet -- inert, not an error, same
                        # treatment as sync_permissions.py's own "role not in this deployment" skip.
                        skipped += 1
                        continue
                    required_role_id = role.id

                existing = (
                    await session.execute(
                        select(SignaturePolicy).where(
                            SignaturePolicy.record_type == record_type, SignaturePolicy.action == action
                        )
                    )
                ).scalar_one_or_none()
                if existing is None:
                    session.add(
                        SignaturePolicy(
                            record_type=record_type,
                            action=action,
                            meaning=meaning,
                            required_role_id=required_role_id,
                            requires_independent_signer=independent,
                            signature_required=sig_required,
                            reason_required=reason_required,
                            policy_source="PLATFORM_FLOOR",
                        )
                    )
                    created += 1
                else:
                    if (
                        existing.meaning,
                        existing.required_role_id,
                        existing.requires_independent_signer,
                        existing.signature_required,
                        existing.reason_required,
                    ) != (meaning, required_role_id, independent, sig_required, reason_required):
                        updated += 1
                    existing.meaning = meaning
                    existing.required_role_id = required_role_id
                    existing.requires_independent_signer = independent
                    existing.signature_required = sig_required
                    existing.reason_required = reason_required

            # SG-035 pair 4 (record_correction/complete), RESOLVED 2026-09-11 (PHASE_3_DEFERRED_
            # DECISIONS.md item D). Every named role in signature_order must already exist in this
            # deployment, same "skip, don't error" precedent as the single-role loop above -- if any
            # position's role is missing, the whole chain row is skipped rather than partially applied.
            for record_type, action, meaning, signature_count, signature_order, reason_required in SIGNATURE_POLICY_CHAIN_FLOOR:
                missing_role = False
                for role_name in signature_order:
                    if role_name and (await session.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none() is None:
                        missing_role = True
                        break
                if missing_role:
                    skipped += 1
                    continue

                existing = (
                    await session.execute(
                        select(SignaturePolicy).where(
                            SignaturePolicy.record_type == record_type, SignaturePolicy.action == action
                        )
                    )
                ).scalar_one_or_none()
                if existing is None:
                    session.add(
                        SignaturePolicy(
                            record_type=record_type,
                            action=action,
                            meaning=meaning,
                            required_role_id=None,
                            requires_independent_signer=True,
                            signature_required=True,
                            signature_count=signature_count,
                            signature_order=signature_order,
                            reason_required=reason_required,
                            policy_source="PLATFORM_FLOOR",
                        )
                    )
                    created += 1
                else:
                    if (
                        existing.meaning,
                        existing.signature_count,
                        existing.signature_order,
                        existing.reason_required,
                    ) != (meaning, signature_count, signature_order, reason_required):
                        updated += 1
                    existing.meaning = meaning
                    existing.required_role_id = None
                    existing.requires_independent_signer = True
                    existing.signature_required = True
                    existing.signature_count = signature_count
                    existing.signature_order = signature_order
                    existing.reason_required = reason_required

    total = len(SIGNATURE_POLICY_FLOOR) + len(SIGNATURE_POLICY_CHAIN_FLOOR)
    print(
        f"signature policies: {created} created, {updated} updated, "
        f"{skipped} skipped (role not in this deployment), {total} total in floor"
    )


if __name__ == "__main__":
    asyncio.run(sync())
