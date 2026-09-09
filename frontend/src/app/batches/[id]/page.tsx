"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Retired 2026-09-08 (SG-149/SG-173 cutover, project-owner-directed): the legacy `ebmr.batches` table
 * this detail page (steps/review/release) read from is now permanently empty — no id under this route
 * can ever resolve to a real record any more. See `/batches/page.tsx`'s own note for the full context. */
export default function LegacyBatchDetailRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/batch-execution");
  }, [router]);
  return null;
}
