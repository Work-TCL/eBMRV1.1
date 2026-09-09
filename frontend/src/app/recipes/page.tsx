"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Retired 2026-09-08 (SG-149/SG-173 cutover, project-owner-directed): this page's legacy `ebmr.recipes`
 * table only ever existed to support the legacy batch flow (`app/modules/batch`), which is retired in
 * favor of `/batch-execution` (Document 11's `gxp_batch`, real Recipe Master versions). `ebmr.recipes` is
 * now permanently empty — redirect to the real, regulated Recipe Master instead. */
export default function LegacyRecipesRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/recipe-master");
  }, [router]);
  return null;
}
