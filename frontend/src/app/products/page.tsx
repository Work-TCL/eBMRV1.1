"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Retired 2026-09-08 (SG-149/SG-173 cutover, project-owner-directed): this page's legacy `ebmr.products`
 * table only ever existed to support the legacy batch flow (`app/modules/batch`), which is retired in
 * favor of `/batch-execution` (Document 11's `gxp_batch`, real Product Master/Recipe Master versions).
 * `ebmr.products` is now permanently empty — redirect to the real, regulated Product Master instead. */
export default function LegacyProductsRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/product-master");
  }, [router]);
  return null;
}
