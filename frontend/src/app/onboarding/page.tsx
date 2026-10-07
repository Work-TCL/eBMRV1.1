"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError, newIdempotencyKey, ONBOARDING_DISMISSED_EVENT, type MutationReceipt } from "@/lib/api";
import { useOnboardingStatus, useRequireAdmin } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button, LinkButton } from "@/components/ui/Button";
import { Stepper, StepItem, type StepMarkerState } from "@/components/ui/Stepper";

interface WizardStepDef {
  key: "company" | "sites" | "users" | "roles";
  number: number;
  title: string;
  meta: string;
  href: string;
  done: (status: { company_done: boolean; sites_done: boolean; users_done: boolean; roles_done: boolean }) => boolean;
}

const STEPS: WizardStepDef[] = [
  { key: "company", number: 1, title: "Company", meta: "Confirm your company's name.", href: "/admin/company", done: (s) => s.company_done },
  { key: "sites", number: 2, title: "Sites", meta: "Add the manufacturing facilities you operate.", href: "/admin/sites", done: (s) => s.sites_done },
  { key: "users", number: 3, title: "Users", meta: "Create accounts for the people who'll use this system.", href: "/admin/users", done: (s) => s.users_done },
  { key: "roles", number: 4, title: "Roles", meta: "Assign each user a role at a site.", href: "/admin/roles", done: (s) => s.roles_done },
];

export default function OnboardingPage() {
  const { isAdmin } = useRequireAdmin();
  const { status, loading } = useOnboardingStatus();
  const router = useRouter();
  const [dismissBusy, setDismissBusy] = useState(false);
  const [dismissError, setDismissError] = useState<string | null>(null);

  if (!isAdmin) return null;

  async function onSkip() {
    setDismissBusy(true);
    setDismissError(null);
    try {
      await api.post<MutationReceipt>("/onboarding/dismiss", { idempotency_key: newIdempotencyKey() });
      window.dispatchEvent(new Event(ONBOARDING_DISMISSED_EVENT));
      router.push("/home");
    } catch (err) {
      setDismissError(err instanceof ApiError ? err.message : "Failed to skip onboarding");
    } finally {
      setDismissBusy(false);
    }
  }

  // Reaching this page directly after everything is already done (e.g. a stale bookmark) -- show a
  // plain completion state instead of the step list, rather than looping back through AuthGuard.
  if (!loading && status?.all_done) {
    return (
      <div>
        <PageHead title="Setup complete" subtitle="Company, sites, users and roles are all set up." />
        <Card pad>
          <p className="mb-3">Nothing left to do here — you can head back to the app.</p>
          <LinkButton href="/home" variant="primary">
            Go to home
          </LinkButton>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHead
        title="Let's get set up"
        subtitle="A few things to confirm before your team starts using this system. You can skip this and come back later."
      />

      <Card pad>
        <CardHeader title="Setup steps" meta={loading ? undefined : `${STEPS.filter((s) => status && s.done(status)).length} of ${STEPS.length} done`} />
        {loading || !status ? (
          <p className="text-muted">Loading…</p>
        ) : (
          <Stepper horizontal>
            {STEPS.map((step) => {
              const done = step.done(status);
              const state: StepMarkerState = done ? "completed" : "available";
              return (
                <StepItem
                  key={step.key}
                  state={state}
                  number={step.number}
                  icon={done ? "check" : undefined}
                  title={step.title}
                  meta={step.meta}
                  action={
                    <LinkButton href={`${step.href}?from=onboarding`} variant={done ? "secondary" : "primary"} size="sm">
                      {done ? "Review" : "Set up"}
                    </LinkButton>
                  }
                />
              );
            })}
          </Stepper>
        )}

        {dismissError && <p className="error-text mt-3">{dismissError}</p>}

        <div className="flex justify-end mt-4">
          <Button type="button" variant="secondary" onClick={onSkip} disabled={dismissBusy}>
            {dismissBusy ? "Skipping…" : "Skip for now"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
