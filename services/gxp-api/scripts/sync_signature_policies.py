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
from scripts.seed import SIGNATURE_POLICY_FLOOR


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

    print(
        f"signature policies: {created} created, {updated} updated, "
        f"{skipped} skipped (role not in this deployment), {len(SIGNATURE_POLICY_FLOOR)} total in floor"
    )


if __name__ == "__main__":
    asyncio.run(sync())
