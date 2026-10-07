"use client";

import { useState } from "react";
import { useApiResource } from "@/lib/hooks";
import { Icon } from "@/components/ui/Icon";

// Client requirement #4 (Expiry / Retest / Important Date Reminders). Backed by
// GET /dashboard/v1/reminders (app/modules/dashboard/router.py) -- a pure read-side aggregate over
// material lot expiry/retest, equipment calibration/maintenance/qualification due dates, and supplier
// qualification expiry. Lives in the Topbar (every page) rather than a dedicated dashboard page, since
// this app has no landing/dashboard page today (logged-in users go straight to /batch-execution) and a
// page nobody navigates to would defeat the point of a proactive reminder.
interface Reminder {
  category: string;
  entity_type: string;
  entity_id: string;
  site_id: string | null;
  label: string;
  due_date: string;
  days_remaining: number;
}

const CATEGORY_LABEL: Record<string, string> = {
  material_lot_expiry: "Material lot expiry",
  material_lot_retest: "Material lot retest",
  equipment_calibration: "Equipment calibration due",
  equipment_maintenance: "Equipment maintenance due",
  equipment_qualification: "Equipment qualification expiry",
  supplier_qualification: "Supplier qualification expiry",
};

export function RemindersBell() {
  const [open, setOpen] = useState(false);
  const { data } = useApiResource<Reminder[]>("/dashboard/v1/reminders?within_days=30");
  const reminders = data ?? [];
  const count = reminders.length;
  const overdueCount = reminders.filter((r) => r.days_remaining < 0).length;

  if (count === 0) return null;

  return (
    <div style={{ position: "relative" }}>
      <button
        className="btn-icon btn-ghost"
        onClick={() => setOpen((v) => !v)}
        aria-label={`${count} reminder${count === 1 ? "" : "s"} coming due`}
        style={{ position: "relative" }}
      >
        <Icon name="bell" />
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
            background: overdueCount > 0 ? "var(--status-critical-solid)" : "var(--status-warning-solid)",
          }}
        >
          {count}
        </span>
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
              Coming due (next 30 days)
            </div>
            {reminders.map((r) => (
              <div
                key={`${r.entity_type}-${r.entity_id}-${r.category}`}
                style={{
                  padding: "var(--space-3) var(--space-4)",
                  borderBottom: "1px solid var(--border-hairline)",
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "var(--space-3)",
                }}
              >
                <div>
                  <div style={{ fontSize: "var(--fs-2)", fontWeight: 600 }}>{r.label}</div>
                  <div className="hint">{CATEGORY_LABEL[r.category] ?? r.category}</div>
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
        </>
      )}
    </div>
  );
}
