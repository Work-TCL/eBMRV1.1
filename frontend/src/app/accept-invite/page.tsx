"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, ApiError, login as apiLogin, type MutationReceipt } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

// Client gap-analysis Phase 1 (2026-10-05): the public landing page for an emailed invite link
// (`POST /auth/accept-invite`). Deliberately unauthenticated, same AuthGuard treatment as /login.
function AcceptInviteForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [username, setUsername] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!token) {
      setError("This link is missing its invite token — ask your administrator to resend it.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    setBusy(true);
    try {
      await api.post<MutationReceipt>("/auth/accept-invite", { token, password });
      setDone(true);
      // The accept-invite response intentionally carries no username (CTR-FR-018 keeps secrets/PII
      // minimal in that response) -- ask for it here so the user can sign in immediately rather than
      // forcing a second trip through /login with nothing pre-filled.
      if (username) {
        try {
          await apiLogin(username, password);
          router.push("/home");
          return;
        } catch {
          // Fall through to the manual "go to sign in" prompt below.
        }
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "This invite link is invalid or has expired.");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <Card pad>
        <h1 className="fs-6 font-bold mb-1">Account activated</h1>
        <p className="hint mb-3">Your password is set. Sign in to continue.</p>
        <Button variant="primary" size="lg" block onClick={() => router.push("/login")}>
          Go to sign in
        </Button>
      </Card>
    );
  }

  return (
    <Card pad>
      <h1 className="fs-6 font-bold mb-1">Set your password</h1>
      <p className="hint mb-3">
        An administrator invited you to eBMR. Set a password to activate your account.
      </p>
      <form onSubmit={onSubmit}>
        <Field label="Username" hint="The username your administrator assigned you (usually your email).">
          <Input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </Field>
        <Field label="Password" required>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
        </Field>
        <Field label="Confirm password" required error={error}>
          <Input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            minLength={8}
          />
        </Field>
        <Button type="submit" variant="primary" size="lg" block disabled={busy}>
          <Icon name="lock" /> {busy ? "Activating…" : "Set password and continue"}
        </Button>
      </form>
    </Card>
  );
}

export default function AcceptInvitePage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "var(--space-6)",
        background: "var(--surface-page)",
      }}
    >
      <div id="main" style={{ maxWidth: 420, width: "100%" }}>
        <div className="flex items-center gap-3 mb-6">
          <div className="sidebar-mark">
            <Icon name="layers" />
          </div>
          <span className="fs-6 font-bold">eBMR</span>
        </div>
        <Suspense fallback={null}>
          <AcceptInviteForm />
        </Suspense>
      </div>
    </div>
  );
}
