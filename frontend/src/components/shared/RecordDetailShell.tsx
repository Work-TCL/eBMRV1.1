"use client";

import { useState, type ReactNode } from "react";
import { ApiError } from "@/lib/api";
import { PageHead } from "@/components/ui/PageHead";
import { Card } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { LinkButton } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { FactGrid } from "@/components/ui/FactGrid";
import { WorkflowStatePill } from "@/components/ui/StatePill";

/** Shared frame for any regulated-record detail page: title with a live workflow-state pill, a back
 * link, the transition buttons, and the record's fact header. Body content (tabs, JSON panels,
 * evidence) is passed as `children`.
 *
 * Generalised from the WP-05 `QmsDetailShell` (which now re-exports this). */
export function RecordDetailShell({
  recordNumber,
  state,
  subtitle,
  backHref,
  backLabel,
  actions,
  facts,
  loading,
  error,
  children,
}: {
  recordNumber: ReactNode;
  /** Workflow state string — rendered through `WorkflowStatePill`. Omit to hide the pill. */
  state?: string;
  subtitle?: ReactNode;
  backHref: string;
  backLabel: string;
  actions?: ReactNode;
  facts: ReactNode;
  loading: boolean;
  error: string | null;
  children: ReactNode;
}) {
  if (error) {
    return (
      <div>
        <PageHead title={backLabel} />
        <Banner tone="critical" title="Could not load this record">
          {error}
        </Banner>
        <LinkButton href={backHref} variant="secondary">
          <Icon name="arrow-left" /> Back to {backLabel.toLowerCase()}
        </LinkButton>
      </div>
    );
  }

  if (loading) {
    return <PageHead title={backLabel} subtitle="Loading…" />;
  }

  return (
    <div>
      <PageHead
        title={
          <span className="flex items-center gap-3">
            {recordNumber} {state !== undefined && <WorkflowStatePill state={state} />}
          </span>
        }
        subtitle={subtitle}
        action={
          <div className="flex gap-2 flex-wrap">
            <LinkButton href={backHref} variant="secondary">
              <Icon name="arrow-left" /> Back
            </LinkButton>
            {actions}
          </div>
        }
      />
      <Card pad className="mb-4">
        <FactGrid>{facts}</FactGrid>
      </Card>
      {children}
    </div>
  );
}

/** Submission plumbing shared by every transition form: busy flag, error surfacing in the codebase's
 * `CODE: message` convention, and refresh-on-success. Keeps each action form to its own fields. */
export function useCommand(onDone: () => void) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  return { busy, error, setError, run };
}
