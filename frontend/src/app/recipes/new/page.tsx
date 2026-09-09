"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Retired 2026-09-08 (SG-149/SG-173 cutover, project-owner-directed) — see `/recipes/page.tsx`'s note. */
export default function LegacyNewRecipeRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/recipe-master");
  }, [router]);
  return null;
}
