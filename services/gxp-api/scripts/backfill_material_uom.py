"""SG-146 (remainder, module 3 of 8) backfill CLI for the nine mutable `materials` schema UOM columns
(migration `c5f1a8d3e7b4`). `inventory_transactions`/`weighing_readings`/`material_consumptions`/
`material_returns` have no UPDATE grant (append-only, AG-08) and get no backfill CLI — only rows written
after this pass ever get a `uom_id`, via dual-write at creation time.

Safe to run repeatedly (idempotent, MIG-FR-008). With no production UOM master data seeded anywhere in
this baseline (SG-146), running this against an environment with no released `rules.gxp_uom` rows yet
is expected to report 0 matched, which is correct behaviour, not a failure.

Usage: python scripts/backfill_material_uom.py [--batch-size N]
"""

import argparse
import asyncio

from app.core.db import SessionLocal
from app.modules.material.uom_backfill import BACKFILL_TARGETS, backfill_table


async def _run(label: str, model, uom_field: str, uom_id_field: str, batch_size: int) -> None:
    total_processed = total_matched = total_unmatched = 0
    after_id = None
    while True:
        async with SessionLocal() as session:
            async with session.begin():
                result = await backfill_table(
                    session, model, uom_field, uom_id_field, batch_size=batch_size, after_id=after_id
                )
        total_processed += result.processed
        total_matched += result.matched
        total_unmatched += result.unmatched
        if result.processed == 0:
            break
        after_id = result.last_id
    print(f"{label}: processed={total_processed} matched={total_matched} unmatched={total_unmatched}")


async def main(batch_size: int) -> None:
    for label, model, uom_field, uom_id_field in BACKFILL_TARGETS:
        await _run(label, model, uom_field, uom_id_field, batch_size)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    asyncio.run(main(args.batch_size))
