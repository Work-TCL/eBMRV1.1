"use client";

import { useState, type ReactNode } from "react";
import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Banner } from "@/components/ui/Banner";
import { Field } from "@/components/ui/Field";

/**
 * A single unsigned regulated transition: a button that opens a confirmation modal (optionally with a
 * structured reason), submits, surfaces the `CODE: message` error, and reloads on success.
 *
 * For transitions that require a Part 11 signature, use `SignatureCeremony` instead.
 */
export function WorkflowActionButton({
  label,
  title,
  summary,
  confirmLabel,
  variant = "secondary",
  confirmVariant,
  reason = "none",
  extraFields,
  disabled,
  onConfirm,
  onDone,
}: {
  label: ReactNode;
  title: ReactNode;
  /** What this action will do — shown in the modal. */
  summary: ReactNode;
  confirmLabel?: string;
  variant?: "primary" | "secondary" | "ghost" | "danger" | "success";
  confirmVariant?: "primary" | "secondary" | "ghost" | "danger" | "success";
  reason?: "none" | "optional" | "required";
  /** Domain inputs for this action, rendered under the summary. */
  extraFields?: ReactNode;
  disabled?: boolean;
  /** Runs the mutation. Receives the trimmed reason (or null). Throw to surface an error. */
  onConfirm: (reason: string | null) => Promise<unknown>;
  onDone: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [reasonText, setReasonText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function close() {
    if (busy) return;
    setOpen(false);
    setReasonText("");
    setError(null);
  }

  async function run() {
    setBusy(true);
    setError(null);
    try {
      await onConfirm(reasonText.trim() || null);
      setOpen(false);
      setReasonText("");
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  const blocked = busy || disabled || (reason === "required" && !reasonText.trim());

  return (
    <>
      <Button variant={variant} onClick={() => setOpen(true)} disabled={disabled}>
        {label}
      </Button>
      <Modal
        open={open}
        onClose={close}
        title={title}
        footer={
          <>
            <Button variant="secondary" onClick={close} disabled={busy}>
              Cancel
            </Button>
            <Button variant={confirmVariant ?? variant} onClick={run} disabled={blocked}>
              {busy ? "Working…" : confirmLabel ?? "Confirm"}
            </Button>
          </>
        }
      >
        <Banner tone="info">{summary}</Banner>
        {extraFields}
        {reason !== "none" && (
          <Field
            label="Reason / comment"
            required={reason === "required"}
            hint={reason === "optional" ? "Recorded in the audit trail." : undefined}
          >
            <textarea
              className="input"
              rows={2}
              value={reasonText}
              onChange={(e) => setReasonText(e.target.value)}
            />
          </Field>
        )}
        {error && <p className="error-text mt-3">{error}</p>}
      </Modal>
    </>
  );
}
