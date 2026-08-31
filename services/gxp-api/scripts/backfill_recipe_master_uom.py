"""SG-146 (remainder, module 4 of 8) backfill CLI for `ebmr.gxp_recipe_version.batch_size_uom_id` and
`ebmr.gxp_recipe_parameter.uom_id` (migration `0051`).

Safe to run repeatedly (idempotent, MIG-FR-008). With no production UOM master data seeded anywhere in
this baseline (SG-146), running this against an environment with no released `rules.gxp_uom` rows yet
is expected to report 0 matched, which is correct behaviour, not a failure.

Usage: python scripts/backfill_recipe_master_uom.py [--batch-size N]
"""

import argparse
import asyncio

from app.core.db import SessionLocal
from app.modules.recipe_master.uom_backfill import backfill_recipe_parameters, backfill_recipe_versions


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
    await _run("gxp_recipe_version", backfill_recipe_versions, batch_size)
    await _run("gxp_recipe_parameter", backfill_recipe_parameters, batch_size)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    asyncio.run(main(args.batch_size))
