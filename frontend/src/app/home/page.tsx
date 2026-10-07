"use client";

import { useEffect } from "react";
import { api, isAdminAnywhere } from "@/lib/api";
import { useApiResource, useMe, useOnboardingStatus } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/Table";
import { Icon } from "@/components/ui/Icon";
import { LinkButton } from "@/components/ui/Button";
import { Stepper, StepItem } from "@/components/ui/Stepper";

// Resumable onboarding checklist (client gap-analysis follow-up, 2026-10-06): shown only once an admin
// has explicitly skipped the wizard (AuthGuard's OnboardingGate redirects there otherwise) and only
// until all four steps are genuinely done -- same `useOnboardingStatus()` the wizard page itself reads.
const ONBOARDING_STEPS = [
  { key: "company", title: "Company", href: "/admin/company", done: (s: { company_done: boolean }) => s.company_done },
  { key: "sites", title: "Sites", href: "/admin/sites", done: (s: { sites_done: boolean }) => s.sites_done },
  { key: "users", title: "Users", href: "/admin/users", done: (s: { users_done: boolean }) => s.users_done },
  { key: "roles", title: "Roles", href: "/admin/roles", done: (s: { roles_done: boolean }) => s.roles_done },
] as const;

function OnboardingChecklistCard() {
  const { me } = useMe();
  const { status } = useOnboardingStatus();
  if (!isAdminAnywhere(me) || !status || !status.dismissed_at || status.all_done) return null;
  const remaining = ONBOARDING_STEPS.filter((s) => !s.done(status));
  return (
    <Card pad>
      <CardHeader title="Finish setting up" meta={`${ONBOARDING_STEPS.length - remaining.length} of ${ONBOARDING_STEPS.length} done`} />
      <Stepper>
        {remaining.map((s, i) => (
          <StepItem
            key={s.key}
            state="available"
            number={i + 1}
            title={s.title}
            action={
              <LinkButton href={`${s.href}?from=onboarding`} variant="secondary" size="sm">
                Set up
              </LinkButton>
            }
          />
        ))}
      </Stepper>
    </Card>
  );
}

// Landing page for every signed-in role, replacing the old "everyone lands on /batch-execution"
// default. Both lists below read the exact same endpoints the Topbar bells (WorkflowActionsBell /
// RemindersBell) already poll -- this page is a second, larger-format view onto that same data, not
// a new source of truth. Types/label maps are intentionally duplicated from those two components
// rather than imported, per the instruction that this be a placement/composition change only and
// not touch their data logic.

interface WorkflowAction {
  id: string;
  category: string;
  entity_label: string;
  link_path: string;
  opened_at: string;
  read: boolean;
}

interface WorkflowActionsResponse {
  items: WorkflowAction[];
  unread_count: number;
}

const WORKFLOW_CATEGORY_LABEL: Record<string, string> = {
  batch_release_pending: "Ready for release decision",
  deviation_disposition_pending: "Disposition needed",
  deviation_close_pending: "Ready for QA closure",
  capa_plan_pending: "CAPA plan needed",
  capa_close_pending: "Ready for QA closure",
  document_release_pending: "Ready for release",
  ncr_disposition_pending: "Disposition needed",
  ncr_verification_pending: "Verification needed",
  ncr_close_pending: "Ready for QA closure",
  complaint_reportability_pending: "Reportability assessment needed",
  complaint_close_pending: "Ready for QA closure",
  change_approval_pending: "Approval needed",
  change_close_pending: "Ready for closure",
  scar_review_pending: "Internal review needed",
  scar_close_pending: "Ready for closure",
  field_action_approval_pending: "Approval needed",
  field_action_close_pending: "Ready for closure",
  internal_audit_close_pending: "Ready for closure",
  risk_acceptance_pending: "Acceptance needed",
  oos_disposition_pending: "Disposition needed",
  oos_close_pending: "Ready for closure",
  oot_close_pending: "Ready for closure",
  material_lot_release_pending: "Ready for release decision",
  supplier_qualification_approval_pending: "Approval needed",
  material_spec_release_pending: "Ready for release",
  product_release_pending: "Ready for release",
  recipe_release_pending: "Ready for release",
  equipment_calibration_approval_pending: "Calibration review needed",
};

interface Reminder {
  category: string;
  entity_type: string;
  entity_id: string;
  label: string;
  due_date: string;
  days_remaining: number;
}

const REMINDER_CATEGORY_LABEL: Record<string, string> = {
  material_lot_expiry: "Material lot expiry",
  material_lot_retest: "Material lot retest",
  equipment_calibration: "Equipment calibration due",
  equipment_maintenance: "Equipment maintenance due",
  equipment_qualification: "Equipment qualification expiry",
  supplier_qualification: "Supplier qualification expiry",
};

export default function HomePage() {
  const { me } = useMe();
  const actions = useApiResource<WorkflowActionsResponse>("/dashboard/v1/workflow-actions");
  const reminders = useApiResource<Reminder[]>("/dashboard/v1/reminders?within_days=30");

  useEffect(() => {
    const id = setInterval(() => actions.reload(), 30_000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload identity is stable per useApiResource call, same interval pattern as WorkflowActionsBell.
  }, []);

  const actionItems = actions.data?.items ?? [];
  const reminderItems = reminders.data ?? [];

  const markRead = async (id: string) => {
    try {
      await api.post(`/dashboard/v1/workflow-actions/${id}/read`);
      actions.reload();
    } catch {
      // Advisory-only read state; a failed mark-as-read is not worth surfacing an error for.
    }
  };

  return (
    <div>
      <PageHead
        title={me ? `Welcome back, ${me.username}` : "Welcome back"}
        subtitle="What needs your attention, and what's coming due."
      />

      <div className="flex flex-col gap-4">
        <OnboardingChecklistCard />

        <Card pad>
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                <Icon name="inbox" /> Needs my action
              </span>
            }
            meta={actionItems.length > 0 ? `${actions.data?.unread_count ?? 0} unread` : undefined}
          />
          {actions.loading ? (
            <p className="hint">Loading…</p>
          ) : actionItems.length === 0 ? (
            <EmptyState icon="check">Nothing waiting on you right now.</EmptyState>
          ) : (
            <div>
              {actionItems.map((item) => (
                <a
                  key={item.id}
                  href={item.link_path}
                  onClick={() => {
                    if (!item.read) void markRead(item.id);
                  }}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "var(--space-3)",
                    padding: "var(--space-3) 0",
                    borderBottom: "1px solid var(--border-hairline)",
                    color: "inherit",
                    textDecoration: "none",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "var(--fs-3)", fontWeight: 600 }}>{item.entity_label}</div>
                    <div className="hint">{WORKFLOW_CATEGORY_LABEL[item.category] ?? item.category}</div>
                  </div>
                  {!item.read && (
                    <span
                      aria-label="unread"
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: 999,
                        background: "var(--status-info-solid, #2563eb)",
                        flexShrink: 0,
                      }}
                    />
                  )}
                </a>
              ))}
            </div>
          )}
        </Card>

        <Card pad>
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                <Icon name="bell" /> Coming due
              </span>
            }
            meta="next 30 days"
          />
          {reminders.loading ? (
            <p className="hint">Loading…</p>
          ) : reminderItems.length === 0 ? (
            <EmptyState icon="calendar">Nothing coming due in the next 30 days.</EmptyState>
          ) : (
            <div>
              {reminderItems.map((r) => (
                <div
                  key={`${r.entity_type}-${r.entity_id}-${r.category}`}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "var(--space-3)",
                    padding: "var(--space-3) 0",
                    borderBottom: "1px solid var(--border-hairline)",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "var(--fs-3)", fontWeight: 600 }}>{r.label}</div>
                    <div className="hint">{REMINDER_CATEGORY_LABEL[r.category] ?? r.category}</div>
                  </div>
                  <div
                    style={{
                      fontSize: "var(--fs-1)",
                      fontWeight: 700,
                      whiteSpace: "nowrap",
                      color: r.days_remaining < 0 ? "var(--status-critical-solid)" : "var(--status-warning-solid)",
                    }}
                  >
                    {r.days_remaining < 0
                      ? `${-r.days_remaining}d overdue`
                      : r.days_remaining === 0
                        ? "Due today"
                        : `in ${r.days_remaining}d`}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* "Recent activity" section deliberately omitted: the only cross-module recent-events read
            endpoint that exists (GET /audit/v1/search) is gated on the `audit.review` permission, which
            most roles (Operator, most Supervisors, etc.) don't hold -- it's an audit-reviewer tool, not a
            general activity feed, and showing it only to some roles while omitting it for others would be
            a worse landing page than not having it. Nothing else in app/modules/audit or
            app/modules/dashboard is shaped for a general "what just happened" feed. Left as a possible
            follow-up if a real per-user activity feed is wanted later. */}
      </div>
    </div>
  );
}
