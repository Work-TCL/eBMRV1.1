"""Seed the live dev environment with a realistic spread of demo data across every stage, so the app
looks like a working system rather than an empty shell when someone clicks through it. Goes through the
real command handlers (not raw ORM writes) so audit/outbox/signature rows are genuine, same discipline as
the pytest fixtures.
"""

import asyncio
import uuid
from decimal import Decimal


from app.core.db import SessionLocal
from app.core.security import verify_password  # noqa: F401 (sanity import)
from app.modules.batch.commands import (
    CompleteStepCommand,
    CreateBatchCommand,
    IssueBatchCommand,
    ReleaseBatchCommand,
    ReviewBatchCommand,
    StartStepCommand,
    SubmitForReviewCommand,
    batch_record_hash,
    complete_step,
    create_batch,
    issue_batch,
    release_batch,
    review_batch,
    start_step,
    submit_for_review,
)
from app.modules.batch.models import Batch, BatchStep
from app.modules.iam.models import Site, User
from app.modules.material.commands import (
    CreateMaterialCommand,
    DispositionMaterialLotCommand,
    IssueMaterialToBatchCommand,
    ReceiveMaterialLotCommand,
    create_material,
    disposition_material_lot,
    issue_material_to_batch,
    lot_record_hash,
    receive_material_lot,
)
from app.modules.material.models import MaterialLot
from app.modules.product.commands import CreateProductCommand, create_product
from app.modules.recipe.commands import CreateRecipeCommand, RecipeStepInput, create_recipe
from app.modules.signature import service as signature_service
from sqlalchemy import select

PASSWORD = "ChangeMe123!"


def idem() -> str:
    return str(uuid.uuid4())


async def get_user_id(session, username: str) -> uuid.UUID:
    user = (await session.execute(select(User).where(User.username == username))).scalar_one()
    return user.id


async def sign(session, *, actor_user_id, record_type, record_id, record_version, record_hash, meaning):
    challenge = await signature_service.create_challenge(
        session,
        user_id=actor_user_id,
        record_type=record_type,
        record_id=record_id,
        record_version=record_version,
        record_hash=record_hash,
        meaning=meaning,
    )
    return challenge.id


async def main() -> None:
    async with SessionLocal() as session:
        site = (await session.execute(select(Site))).scalars().first()
        site_id = site.id
        operator_id = await get_user_id(session, "operator1")
        reviewer_id = await get_user_id(session, "qa.reviewer")
        releaser_id = await get_user_id(session, "qa.releaser")
        qc_id = await get_user_id(session, "qc.reviewer")
        await session.commit()  # close the autobegin transaction from the reads above

        # ---- Products -------------------------------------------------------------------------
        async with session.begin():
            ibu_id = (
                await create_product(
                    session,
                    CreateProductCommand(idempotency_key=idem(), site_id=site_id, code="IBU-200", name="Ibuprofen 200mg Tablets"),
                    operator_id,
                )
            ).aggregate_id
        async with session.begin():
            pcm_id = (
                await create_product(
                    session,
                    CreateProductCommand(idempotency_key=idem(), site_id=site_id, code="PCM-500", name="Paracetamol 500mg Tablets"),
                    operator_id,
                )
            ).aggregate_id
        async with session.begin():
            amx2_id = (
                await create_product(
                    session,
                    CreateProductCommand(idempotency_key=idem(), site_id=site_id, code="AMX-250", name="Amoxicillin 250mg Capsules"),
                    operator_id,
                )
            ).aggregate_id

        # ---- Recipes ----------------------------------------------------------------------------
        async def make_recipe(product_id, steps):
            async with session.begin():
                return (
                    await create_recipe(
                        session,
                        CreateRecipeCommand(idempotency_key=idem(), product_id=product_id, version=1, steps=steps),
                        operator_id,
                    )
                ).aggregate_id

        ibu_recipe = await make_recipe(
            ibu_id,
            [
                RecipeStepInput(step_number=1, name="Dispense API", requires_signature=False),
                RecipeStepInput(step_number=2, name="Granulate", requires_signature=False),
                RecipeStepInput(step_number=3, name="Compress Tablets", requires_signature=True, signature_meaning="Performed"),
            ],
        )
        pcm_recipe = await make_recipe(
            pcm_id,
            [
                RecipeStepInput(step_number=1, name="Dispense API", requires_signature=False),
                RecipeStepInput(step_number=2, name="Blend", requires_signature=True, signature_meaning="Performed"),
                RecipeStepInput(step_number=3, name="Compress Tablets", requires_signature=False),
            ],
        )
        amx2_recipe = await make_recipe(
            amx2_id,
            [
                RecipeStepInput(step_number=1, name="Dispense API", requires_signature=False),
                RecipeStepInput(step_number=2, name="Blend", requires_signature=True, signature_meaning="Performed"),
                RecipeStepInput(step_number=3, name="Encapsulate & Polish", requires_signature=False),
            ],
        )

        # ---- Materials + lots ---------------------------------------------------------------------
        async def make_material(code, name, uom):
            async with session.begin():
                return (
                    await create_material(
                        session,
                        CreateMaterialCommand(idempotency_key=idem(), site_id=site_id, code=code, name=name, uom=uom),
                        operator_id,
                    )
                ).aggregate_id

        ibu_api_id = await make_material("API-IBU", "Ibuprofen (API)", "kg")
        mcc_id = await make_material("MCC-01", "Microcrystalline Cellulose (Excipient)", "kg")

        async def receive_lot(material_id, internal_lot, qty):
            async with session.begin():
                return (
                    await receive_material_lot(
                        session,
                        ReceiveMaterialLotCommand(
                            idempotency_key=idem(),
                            material_id=material_id,
                            site_id=site_id,
                            internal_lot=internal_lot,
                            received_quantity=Decimal(qty),
                            uom="kg",
                        ),
                        operator_id,
                    )
                ).aggregate_id

        ibu_lot_id = await receive_lot(ibu_api_id, "LOT-2026-0102", "180.000000")
        mcc_lot_id = await receive_lot(mcc_id, "LOT-2026-0088", "500.000000")
        # A second, still-in-quarantine lot the QC Reviewer can act on live.
        pending_lot_id = await receive_lot(ibu_api_id, "LOT-2026-0115", "90.000000")

        async def disposition(lot_id, decision, actor_id):
            async with session.begin():
                lot = await session.get(MaterialLot, lot_id)
                challenge_id = await sign(
                    session,
                    actor_user_id=actor_id,
                    record_type="material_lot",
                    record_id=lot.id,
                    record_version=lot.version,
                    record_hash=lot_record_hash(lot),
                    meaning="Disposition",
                )
                await disposition_material_lot(
                    session,
                    DispositionMaterialLotCommand(
                        idempotency_key=idem(),
                        lot_id=lot_id,
                        expected_version=lot.version,
                        decision=decision,
                        challenge_id=challenge_id,
                        reauth_password=PASSWORD,
                    ),
                    actor_id,
                    site_id,
                )

        await disposition(ibu_lot_id, "released", qc_id)
        await disposition(mcc_lot_id, "released", qc_id)
        # LOT-2026-0115 deliberately left in quarantine for a live demo of the QC action.

        # ---- Batch 1: Ibuprofen, still in execution --------------------------------------------
        async with session.begin():
            ibu_batch_id = (
                await create_batch(
                    session,
                    CreateBatchCommand(
                        idempotency_key=idem(),
                        site_id=site_id,
                        product_id=ibu_id,
                        recipe_id=ibu_recipe,
                        recipe_version=1,
                        batch_number="IBU-2026-031",
                        target_quantity=Decimal("200.000000"),
                        uom="kg",
                    ),
                    operator_id,
                )
            ).aggregate_id
        async with session.begin():
            await issue_batch(
                session,
                IssueBatchCommand(idempotency_key=idem(), batch_id=ibu_batch_id, expected_version=1),
                operator_id,
            )
        # Start step 1 and leave it in progress — a batch mid-execution for the demo.
        async with session.begin():
            steps = (
                await session.execute(
                    select(BatchStep).join(Batch).where(Batch.id == ibu_batch_id).order_by(BatchStep.recipe_step_id)
                )
            ).scalars().all()
        step1 = next(s for s in steps if s.status == "ready")
        async with session.begin():
            await start_step(
                session,
                StartStepCommand(idempotency_key=idem(), batch_id=ibu_batch_id, expected_version=2, batch_step_id=step1.id),
                operator_id,
                site_id,
            )

        async with session.begin():
            await issue_material_to_batch(
                session,
                IssueMaterialToBatchCommand(
                    idempotency_key=idem(),
                    lot_id=ibu_lot_id,
                    expected_version=2,
                    batch_id=ibu_batch_id,
                    batch_step_id=step1.id,
                    quantity=Decimal("22.400000"),
                ),
                operator_id,
                site_id,
            )

        # ---- Batch 2: Paracetamol, fully executed, awaiting QA review ---------------------------
        async with session.begin():
            pcm_batch_id = (
                await create_batch(
                    session,
                    CreateBatchCommand(
                        idempotency_key=idem(),
                        site_id=site_id,
                        product_id=pcm_id,
                        recipe_id=pcm_recipe,
                        recipe_version=1,
                        batch_number="PCM-2026-058",
                        target_quantity=Decimal("300.000000"),
                        uom="kg",
                    ),
                    operator_id,
                )
            ).aggregate_id
        async with session.begin():
            await issue_batch(
                session, IssueBatchCommand(idempotency_key=idem(), batch_id=pcm_batch_id, expected_version=1), operator_id
            )

        # Walk steps in recipe order by re-querying "ready" each time.
        for _ in range(3):
            async with session.begin():
                ready = (
                    await session.execute(
                        select(BatchStep).where(BatchStep.batch_id == pcm_batch_id, BatchStep.status == "ready")
                    )
                ).scalar_one()
                batch = await session.get(Batch, pcm_batch_id)
                await start_step(
                    session,
                    StartStepCommand(idempotency_key=idem(), batch_id=pcm_batch_id, expected_version=batch.version, batch_step_id=ready.id),
                    operator_id,
                    site_id,
                )
            async with session.begin():
                step_row = await session.get(BatchStep, ready.id)
                batch = await session.get(Batch, pcm_batch_id)
                from app.modules.recipe.models import RecipeStep

                recipe_step = await session.get(RecipeStep, step_row.recipe_step_id)
                challenge_id = None
                if recipe_step.requires_signature:
                    challenge_id = await sign(
                        session,
                        actor_user_id=operator_id,
                        record_type="batch",
                        record_id=batch.id,
                        record_version=batch.version,
                        record_hash=batch_record_hash(batch),
                        meaning=recipe_step.signature_meaning,
                    )
                await complete_step(
                    session,
                    CompleteStepCommand(
                        idempotency_key=idem(),
                        batch_id=pcm_batch_id,
                        expected_version=batch.version,
                        batch_step_id=ready.id,
                        data={},
                        challenge_id=challenge_id,
                        reauth_password=PASSWORD if challenge_id else None,
                    ),
                    operator_id,
                    site_id,
                )

        async with session.begin():
            batch = await session.get(Batch, pcm_batch_id)
            await submit_for_review(
                session,
                SubmitForReviewCommand(idempotency_key=idem(), batch_id=pcm_batch_id, expected_version=batch.version),
                operator_id,
            )
        # Left at qa_review — a live "needs your review" item for the demo.

        # ---- Batch 3: second Amoxicillin batch, just planned ------------------------------------
        async with session.begin():
            await create_batch(
                session,
                CreateBatchCommand(
                    idempotency_key=idem(),
                    site_id=site_id,
                    product_id=amx2_id,
                    recipe_id=amx2_recipe,
                    recipe_version=1,
                    batch_number="AMX-2026-015",
                    target_quantity=Decimal("80.000000"),
                    uom="kg",
                ),
                operator_id,
            )

        print("Seeded:")
        print(" products: IBU-200, PCM-500, AMX-250 (plus existing AMX-500)")
        print(" material lots: LOT-2026-0102 (released), LOT-2026-0088 (released), LOT-2026-0115 (quarantine, live QC action available)")
        print(" batches: IBU-2026-031 (in_execution), PCM-2026-058 (qa_review, live review/release available), AMX-2026-015 (planned)")


asyncio.run(main())
