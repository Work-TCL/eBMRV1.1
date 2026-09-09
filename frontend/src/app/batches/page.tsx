"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Retired 2026-09-08 (SG-149/SG-173 cutover, project-owner-directed): this page listed the legacy
 * `ebmr.batches` table (`app/modules/batch`), which every dependent module (DDCP, material, equipment,
 * machine_integration) has been retargeted away from onto the authoritative `ebmr.gxp_batch`
 * (`app/modules/batch_execution`, Document 11). The legacy table is now permanently empty — redirect
 * rather than render a page that can only ever show "no batches". */
export default function LegacyBatchesRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/batch-execution");
  }, [router]);
  return null;
}
