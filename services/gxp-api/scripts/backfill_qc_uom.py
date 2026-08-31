"""SG-146 (remainder) backfill CLI for `ebmr.qc_sample.sample_uom_id` (migration `b2e7f4a9c3d6`).
`qc_test_definition.uom_id`/`qc_result.uom_id` have no backfill CLI — those tables have no UPDATE grant
(append-only, AG-08), so only rows written after this pass ever get one, via dual-write at creation time.

Safe to run repeatedly (idempotent, MIG-FR-008). With no production UOM master data seeded anywhere in
this baseline (SG-146), running this against an environment with no released `rules.gxp_uom` rows yet
is expected to report 0 matched, which is correct behaviour, not a failure.

Usage: python scripts/backfill_qc_uom.py [--batch-size N]
"""

import argparse
import asyncio

from app.core.db import SessionLocal
from app.modules.qc.uom_backfill import backfill_qc_samples


async def main(batch_size: int) -> None:
    total_processed = total_matched = total_unmatched = 0
    after_id = None
    while True:
        async with SessionLocal() as session:
            async with session.begin():
                result = await backfill_qc_samples(session, batch_size=batch_size, after_id=after_id)
        total_processed += result.processed
        total_matched += result.matched
        total_unmatched += result.unmatched
        if result.processed == 0:
            break
        after_id = result.last_id
    print(f"qc_sample: processed={total_processed} matched={total_matched} unmatched={total_unmatched}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    asyncio.run(main(args.batch_size))
