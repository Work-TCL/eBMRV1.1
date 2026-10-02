"use client";

import { useEffect, useState } from "react";
import { useApiResource } from "@/lib/hooks";
import { api } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";

// Workflow Handoff Notifications (project-owner-directed) -- "it's your turn to act" notifications for
// role-dependent handoffs (a draft one person created that another role now needs to act on), backed by
// GET /dashboard/v1/workflow-actions (app/modules/notifications + app/modules/dashboard/router.py). This
// list is already filtered server-side to exactly what the signed-in actor's current roles/site let them
// act on -- everyone sees only their own queue, never a raw firehose. Distinct from RemindersBell (date-
// driven, visible to everyone, no per-user state): these are role-targeted and track per-viewer read state.
interface WorkflowAction {
  id: string;
  aggregate_type: string;
  category: string;
  site_id: string;
  entity_label: string;
  link_path: string;
  opened_at: string;
  read: boolean;
}

interface WorkflowActionsResponse {
  items: WorkflowAction[];
  unread_count: number;
}

// Falls back to the raw category string (still readable, e.g. "scar_review_pending") for any category
// added to app/modules/notifications/registry.py without a label added here -- never hides a real
// notification just because this map hasn't caught up yet.
const CATEGORY_LABEL: Record<string, string> = {
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
};

const POLL_INTERVAL_MS = 30_000;

export function WorkflowActionsBell() {
  const [open, setOpen] = useState(false);
  const { data, reload } = useApiResource<WorkflowActionsResponse>("/dashboard/v1/workflow-actions");

  useEffect(() => {
    const id = setInterval(() => reload(), POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [reload]);

  const items = data?.items ?? [];
  const unreadCount = data?.unread_count ?? 0;

  if (items.length === 0) return null;

  const markRead = async (id: string) => {
    try {
      await api.post(`/dashboard/v1/workflow-actions/${id}/read`);
      reload();
    } catch {
      // Advisory-only read state; a failed mark-as-read is not worth surfacing an error for.
    }
  };

  return (
    <div style={{ position: "relative" }}>
      <button
        className="btn-icon btn-ghost"
        onClick={() => setOpen((v) => !v)}
        aria-label={`${items.length} workflow action${items.length === 1 ? "" : "s"} waiting on you`}
        style={{ position: "relative" }}
      >
        <Icon name="inbox" />
        {unreadCount > 0 && (
          <span
            style={{
              position: "absolute",
              top: -2,
              right: -2,
              minWidth: 16,
              height: 16,
              borderRadius: 999,
              fontSize: 10,
              fontWeight: 700,
              color: "#fff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "0 3px",
              background: "var(--status-info-solid, #2563eb)",
            }}
          >
            {unreadCount}
          </span>
        )}
      </button>

      {open && (
        <>
          <div style={{ position: "fixed", inset: 0, zIndex: 39 }} onClick={() => setOpen(false)} />
          <div
            style={{
              position: "absolute",
              top: "calc(100% + 8px)",
              right: 0,
              width: 380,
              maxHeight: 420,
              overflowY: "auto",
              background: "var(--surface-card)",
              border: "1px solid var(--border-hairline)",
              borderRadius: "var(--radius-2, 8px)",
              boxShadow: "0 8px 24px rgba(0,0,0,0.16)",
              zIndex: 40,
            }}
          >
            <div
              style={{
                padding: "var(--space-3) var(--space-4)",
                borderBottom: "1px solid var(--border-hairline)",
                fontWeight: 600,
              }}
            >
              Waiting on you
            </div>
            {items.map((item) => (
              <a
                key={item.id}
                href={item.link_path}
                onClick={() => {
                  if (!item.read) markRead(item.id);
                  setOpen(false);
                }}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "var(--space-3)",
                  padding: "var(--space-3) var(--space-4)",
                  borderBottom: "1px solid var(--border-hairline)",
                  color: "inherit",
                  textDecoration: "none",
                }}
              >
                <div>
                  <div style={{ fontSize: "var(--fs-2)", fontWeight: 600 }}>{item.entity_label}</div>
                  <div className="hint">{CATEGORY_LABEL[item.category] ?? item.category}</div>
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
        </>
      )}
    </div>
  );
}
