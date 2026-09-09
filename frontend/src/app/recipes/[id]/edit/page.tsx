"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Retired 2026-09-08 (SG-149/SG-173 cutover, project-owner-directed) — see `/recipes/page.tsx`'s note.
 * `ebmr.recipes` is now permanently empty, so no id under this route can ever resolve any more. */
export default function LegacyEditRecipeRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/recipe-master");
  }, [router]);
  return null;
}
