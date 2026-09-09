"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Retired 2026-09-08 (SG-149/SG-173 cutover, project-owner-directed): batch creation now happens on
 * `/batch-execution` ("New batch"), which creates the authoritative `ebmr.gxp_batch` record against
 * real released Product Master / Recipe Master versions (real dropdowns, not this page's old free
 * `/products`/`/recipes` picker). See `/batches/page.tsx`'s own note for the full context. */
export default function LegacyNewBatchRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/batch-execution");
  }, [router]);
  return null;
}
