"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
      router.push("/batches");
    } catch {
      setError("Invalid username or password");
    } finally {
      setBusy(false);
    }
  }

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

        <Card pad>
          <h1 className="fs-6 font-bold mb-1">Sign in</h1>
          <p className="fs-3 text-muted mb-4">Unique identity required by Part 11 — no shared logins.</p>

          <form onSubmit={onSubmit}>
            <Field label="Username" required>
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                required
              />
            </Field>
            <Field label="Password" required error={error}>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </Field>
            <Button type="submit" variant="primary" size="lg" block disabled={busy}>
              <Icon name="lock" /> {busy ? "Signing in…" : "Sign in"}
            </Button>
          </form>
          <p className="hint mt-3">
            Multi-factor verification and session policy are configured per organization.
          </p>
        </Card>

        <p className="fs-2 text-muted mt-4">
          Demo users: operator1, qa.reviewer, qa.releaser — password ChangeMe123!
        </p>
      </div>
    </div>
  );
}
