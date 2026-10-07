"use client";

import { useSearchParams } from "next/navigation";
import { LinkButton } from "@/components/ui/Button";

/** Shown on /admin/company, /admin/sites, /admin/users and /admin/roles when reached from the
 * onboarding wizard (`?from=onboarding`) or its home-page resumable checklist, so the admin has a way
 * back without using browser Back. None of those four pages factor their forms into separate
 * components, so the wizard links out to the real page rather than re-embedding its form -- this is
 * the one small addition each of them needs for that. Renders nothing otherwise. */
export function OnboardingReturnLink() {
  const from = useSearchParams().get("from");
  if (from !== "onboarding") return null;
  return (
    <LinkButton href="/onboarding" variant="secondary" size="sm">
      ← Back to setup
    </LinkButton>
  );
}
