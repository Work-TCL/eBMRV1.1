"use client";

import { useEffect, useState, type ReactNode } from "react";
import { api, ApiError, newIdempotencyKey } from "@/lib/api";
import { Modal } from "@/components/ui/Modal";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";

/** Arguments handed to the caller's `onSign`: everything a signed mutation endpoint in this codebase
 * expects on its body, already assembled. The caller adds the domain fields and picks the URL. */
export interface SignaturePayload {
  challenge_id: string;
  reauth_password: string;
  idempotency_key: string;
  reason: string | null;
}

/**
 * The Part 11 signature step, centralised.
 *
 * The kernel's signed-mutation contract (see `material-lots` / `dispensing`): `POST {challengePath}
 * {action}` returns `{ challenge_id, meaning? }`, then the mutation body carries `challenge_id` +
 * `reauth_password`. This modal owns the challenge request, the fresh-step-up password field, the
 * acknowledgement text and error surfacing; the caller owns the actual mutation via `onSign`.
 */
export function SignatureCeremony({
  open,
  onClose,
  onDone,
  challengePath,
  action,
  challengeBody,
  title,
  summary,
  submitLabel = "Sign & submit",
  submitVariant = "primary",
  reason = "none",
  extraFields,
  disabled,
  onSign,
}: {
  open: boolean;
  onClose: () => void;
  /** Called after a successful sign — usually reloads the record. */
  onDone: () => void;
  /** e.g. `/material-lots/${id}/signature-challenges`. */
  challengePath: string;
  /** The action name the challenge endpoint keys the policy lookup on. Sent as `{ action }` unless
   * `challengeBody` is given. */
  action: string;
  /** Overrides the challenge request body when the endpoint expects something other than `{ action }`
   * (e.g. yield/reconciliation's `{ record_kind }`). */
  challengeBody?: Record<string, unknown>;
  title: ReactNode;
  /** What the signer is about to attest to — rendered in an info banner above the password field. */
  summary: ReactNode;
  submitLabel?: string;
  submitVariant?: "primary" | "success" | "danger";
  /** Whether a reason/comment is collected and whether it blocks submit. */
  reason?: "none" | "optional" | "required";
  /** Domain inputs specific to this action, rendered between the summary and the reason field. */
  extraFields?: ReactNode;
  /** Extra caller-side guard (e.g. a required domain field is empty). */
  disabled?: boolean;
  onSign: (payload: SignaturePayload) => Promise<unknown>;
}) {
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [meaning, setMeaning] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [reasonText, setReasonText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    // Clear any challenge from a previous open before requesting a fresh one — this is the effect's
    // own reset, matching the fetch-effect pattern used in DataTable / useApiResource.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setChallengeId(null);
    setMeaning(null);
    setError(null);
    api
      .post<{ challenge_id: string; meaning?: string }>(challengePath, challengeBody ?? { action })
      .then((c) => {
        if (cancelled) return;
        setChallengeId(c.challenge_id);
        setMeaning(c.meaning ?? null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not request a signature challenge"
        );
      });
    return () => {
      cancelled = true;
    };
    // challengeBody is compared by value (callers often pass a fresh object literal).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, challengePath, action, JSON.stringify(challengeBody ?? null)]);

  async function confirm() {
    if (!challengeId) return;
    setBusy(true);
    setError(null);
    try {
      await onSign({
        challenge_id: challengeId,
        reauth_password: password,
        idempotency_key: newIdempotencyKey(),
        reason: reasonText.trim() || null,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Signature failed");
    } finally {
      setBusy(false);
    }
  }

  const blocked =
    busy || !challengeId || !password || disabled || (reason === "required" && !reasonText.trim());

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button variant={submitVariant} onClick={confirm} disabled={blocked}>
            {busy ? "Signing…" : submitLabel}
          </Button>
        </>
      }
    >
      <Banner tone="info" title={meaning ? `Signature meaning: ${meaning}` : "Electronic signature"}>
        {summary}
      </Banner>

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

      <p className="fs-2 text-muted mb-2">
        Fresh authentication is required to sign — re-enter your password (21 CFR Part 11 step-up).
        This signature is attributable to you and bound to this record and version.
      </p>
      <Field label="Password" required>
        <Input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
          autoComplete="current-password"
        />
      </Field>

      {error && <p className="error-text mt-3">{error}</p>}
    </Modal>
  );
}

/** For screens that interleave many domain fields with the signature (e.g. dispensing step forms):
 * requests the challenge on mount and hands back the id + meaning + any error. The caller renders its
 * own form and includes `challenge_id` + `reauth_password` on the mutation body. */
export function useSignatureChallenge(challengePath: string, action: string, ready = true) {
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [meaning, setMeaning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    api
      .post<{ challenge_id: string; meaning?: string }>(challengePath, { action })
      .then((c) => {
        if (cancelled) return;
        setChallengeId(c.challenge_id);
        setMeaning(c.meaning ?? null);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not request a signature challenge"
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [challengePath, action, ready]);

  return { challengeId, meaning, error };
}
