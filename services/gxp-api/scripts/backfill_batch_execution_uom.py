"""SG-146 (remainder, module 4 of 8) backfill CLI for `ebmr.gxp_batch.target_uom_id` (migration `0051`).

Safe to run repeatedly (idempotent, MIG-FR-008). With no production UOM master data seeded anywhere in
this baseline (SG-146), running this against an environment with no released `rules.gxp_uom` rows yet
is expected to report 0 matched, which is correct behaviour, not a failure.

Usage: python scripts/backfill_batch_execution_uom.py [--batch-size N]
"""

import argparse
import asyncio

from app.core.db import SessionLocal
from app.modules.batch_execution.uom_backfill import backfill_batches


async def main(batch_size: int) -> None:
    total_processed = total_matched = total_unmatched = 0
    after_id = None
    while True:
        async with SessionLocal() as session:
            async with session.begin():
                result = await backfill_batches(session, batch_size=batch_size, after_id=after_id)
        total_processed += result.processed
        total_matched += result.matched
        total_unmatched += result.unmatched
        if result.processed == 0:
            break
        after_id = result.last_id
    print(f"gxp_batch: processed={total_processed} matched={total_matched} unmatched={total_unmatched}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    asyncio.run(main(args.batch_size))
