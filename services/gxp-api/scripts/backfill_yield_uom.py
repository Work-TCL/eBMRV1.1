"""SG-146 (remainder) backfill CLI — MIG-FR-014's "counts/checks before/after" evidence for the
`ebmr.manufacturing_calculations.uom_id`/`ebmr.reconciliation_records.uom_id` expand step (migration
`a4d9e6c2f8b1`).

Safe to run repeatedly (idempotent, MIG-FR-008): already-matched rows are skipped, and an unresolved
`uom` string is left NULL and reported as unmatched rather than guessed. There is deliberately no
production UOM master data seeded anywhere in this baseline (a specific UOM/factor is a content
decision, not a schema one — SG-146) — running this against an environment with no released `rules.
gxp_uom` rows yet is expected to report 0 matched, 100% unmatched, which is correct behaviour, not a
failure.

Usage: python scripts/backfill_yield_uom.py [--batch-size N]
"""

import argparse
import asyncio

from app.core.db import SessionLocal
from app.modules.yield_reconciliation.uom_backfill import (
    backfill_manufacturing_calculations,
    backfill_reconciliation_records,
)


async def _run(label: str, backfill_fn, batch_size: int) -> None:
    total_processed = total_matched = total_unmatched = 0
    after_id = None
    while True:
        async with SessionLocal() as session:
            async with session.begin():
                result = await backfill_fn(session, batch_size=batch_size, after_id=after_id)
        total_processed += result.processed
        total_matched += result.matched
        total_unmatched += result.unmatched
        if result.processed == 0:
            break
        after_id = result.last_id
    print(f"{label}: processed={total_processed} matched={total_matched} unmatched={total_unmatched}")


async def main(batch_size: int) -> None:
    await _run("manufacturing_calculations", backfill_manufacturing_calculations, batch_size)
    await _run("reconciliation_records", backfill_reconciliation_records, batch_size)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    asyncio.run(main(args.batch_size))
