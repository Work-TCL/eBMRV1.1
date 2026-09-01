"use client";

import { useState } from "react";
import { api, ApiError, newIdempotencyKey, type MutationReceipt } from "@/lib/api";
import { useRequireAdmin } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { FormConsole } from "@/components/shared/FormConsole";

// Parameter-less GET dashboards. (Control matrix is per-threat-model — it lives in the threat-model
// console below, not here.)
const READS = [
  { label: "API security inventory", path: "/security/v1/api-inventory" },
  { label: "Crypto health", path: "/security/v1/crypto-health" },
  { label: "Network flows", path: "/security/v1/network-flows" },
  { label: "Deployment security profile", path: "/security/v1/deployment-security-profile" },
  { label: "MFA requirement", path: "/security/v1/mfa-requirement" },
];

export default function SecurityPage() {
  const { isAdmin } = useRequireAdmin();
  if (!isAdmin) return null;

  return (
    <div>
      <PageHead
        title="Security"
        subtitle="Documents 61–68 — threat model, identity, privileged access, app/crypto controls, incidents and supply chain."
      />

      <ReadDashboards />
      <RaiseIncidentCard />
      <RegisterVulnerabilityCard />
      <RequestPrivilegedAccessCard />

      <FormConsole
        title="Threat model & risk operations (Doc 61)"
        root="/security/v1"
        ops={[
          {
            path: "threats",
            label: "Add a threat",
            about: "Registers one threat against a threat-model version, with its abuse case.",
            fields: [
              { name: "threat_model_version_id", label: "Threat model version ID", required: true },
              { name: "asset_or_boundary", label: "Asset or trust boundary", required: true },
              { name: "threat_type", label: "Threat type", type: "select", options: ["SPOOFING", "TAMPERING", "REPUDIATION", "INFO_DISCLOSURE", "DENIAL_OF_SERVICE", "ELEVATION_OF_PRIVILEGE"].map((v) => ({ value: v, label: v })) },
              { name: "abuse_case", label: "Abuse case", type: "textarea", required: true },
              { name: "impacted_attributes", label: "Impacted attributes (JSON array)", type: "json" },
              { name: "reason", label: "Reason" },
            ],
          },
          { path: "risks/{id}/accept", label: "Accept a residual risk (JSON)" },
          { path: "threat-models", label: "Create a threat model version (JSON)" },
          { path: "threat-models/{id}/reviews", label: "Record a review (JSON)" },
          { path: "threats/{id}/controls", label: "Map a control (JSON)" },
          { path: "threats/{id}/risk-calculations", label: "Calculate residual risk (JSON)" },
          { path: "exceptions", label: "Raise a security exception (JSON)" },
        ]}
      />

      <FormConsole
        title="Identity & session operations (Doc 62)"
        root="/security/v1"
        ops={[
          {
            path: "sessions/{id}/revoke",
            label: "Revoke a session",
            fields: [
              { name: "id", label: "Session ID", required: true },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
          {
            path: "sessions:revoke-all",
            label: "Revoke all sessions for a subject",
            fields: [
              { name: "subject_id", label: "Subject ID", required: true },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
          { path: "identity-providers", label: "Register an IdP config (JSON)" },
          { path: "identity-providers/{id}/mappings", label: "Add a federation mapping (JSON)" },
          { path: "identity-providers/{id}/tokens:validate", label: "Validate a token (JSON)" },
          { path: "service-identities", label: "Register a service identity (JSON)" },
          { path: "service-identities/{id}/revoke", label: "Revoke a service identity (JSON)" },
        ]}
      />

      <FormConsole
        title="Privileged access & crypto operations (Docs 63, 65)"
        root="/security/v1"
        ops={[
          {
            path: "privileged-access/requests/{id}/approve",
            label: "Approve a privileged-access request",
            fields: [
              { name: "id", label: "Request ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
          { path: "support-sessions", label: "Open a support session" },
          { path: "break-glass", label: "Break-glass access" },
          { path: "admin-commands/{command_code}:execute", label: "Execute a controlled admin command" },
          { path: "privileged-sessions/{id}/close", label: "Close a privileged session" },
          { path: "privileged-sessions/{id}/review", label: "Review a privileged session" },
          { path: "secrets/{id}/rotate", label: "Rotate a secret" },
          { path: "certificates:issue", label: "Issue a certificate" },
          { path: "certificates/{id}/rotate", label: "Rotate a certificate" },
          { path: "certificates/{id}/revoke", label: "Revoke a certificate" },
          { path: "outbound-destinations", label: "Register an outbound destination" },
          { path: "webhook-profiles", label: "Register a webhook profile" },
        ]}
      />

      <FormConsole
        title="Incident & supply-chain operations (Docs 67, 68)"
        root="/security/v1"
        ops={[
          { path: "incidents/{id}/containment", label: "Record a containment action" },
          { path: "incidents/{id}/evidence", label: "Attach forensic evidence" },
          { path: "incidents/{id}/gxp-impact", label: "Assess GxP impact" },
          { path: "incidents/{id}/close", label: "Close an incident" },
          { path: "vulnerabilities/{id}/assess", label: "Assess a vulnerability" },
          { path: "vulnerabilities/{id}/exceptions", label: "Grant a vulnerability exception" },
        ]}
      />
    </div>
  );
}

function ReadDashboards() {
  const [which, setWhich] = useState(0);
  const [data, setData] = useState<unknown>(undefined);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setData(await api.get<unknown>(READS[which].path).catch((e) => ({ error: String(e) })));
    setBusy(false);
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Security dashboards" />
      <div className="flex items-end gap-3 mt-3">
        <Field label="Dashboard">
          <Select value={which} onChange={(e) => setWhich(Number(e.target.value))}>
            {READS.map((r, i) => (
              <option key={r.path} value={i}>
                {r.label}
              </option>
            ))}
          </Select>
        </Field>
        <Button variant="secondary" onClick={load} disabled={busy}>
          {busy ? "Loading…" : "Load"}
        </Button>
      </div>
      {data !== undefined && (
        <div className="mt-3">
          <JsonPanel title={READS[which].label} value={data} />
        </div>
      )}
    </Card>
  );
}

function RaiseIncidentCard() {
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState("high");
  const [detectedAt, setDetectedAt] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      const r = await api.post<MutationReceipt>(`/security/v1/incidents`, {
        idempotency_key: newIdempotencyKey(),
        title: title.trim(),
        severity: severity.trim(),
        detected_at: detectedAt ? new Date(detectedAt).toISOString() : new Date().toISOString(),
        reason: reason.trim(),
      });
      setMsg(`Incident opened — ${r.aggregate_id}`);
    } catch (err) {
      setMsg(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Raise a security incident (Doc 67)" />
      <form onSubmit={submit} className="grid grid-cols-2 gap-4 mt-3">
        <Field label="Title" required>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </Field>
        <Field label="Severity" required>
          <Input value={severity} onChange={(e) => setSeverity(e.target.value)} required />
        </Field>
        <Field label="Detected at" hint="Defaults to now.">
          <Input type="datetime-local" value={detectedAt} onChange={(e) => setDetectedAt(e.target.value)} />
        </Field>
        <Field label="Reason" required>
          <Input value={reason} onChange={(e) => setReason(e.target.value)} required />
        </Field>
        <div style={{ gridColumn: "1 / -1" }}>
          {msg && <p className={msg.startsWith("Incident") ? "fs-2 mb-2" : "error-text mb-2"}>{msg}</p>}
          <Button type="submit" variant="danger" disabled={busy || !title.trim() || !reason.trim()}>
            {busy ? "Opening…" : "Open incident"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function RegisterVulnerabilityCard() {
  const [vulnId, setVulnId] = useState("");
  const [source, setSource] = useState("NVD");
  const [component, setComponent] = useState('{ "name": "", "version": "" }');
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      const r = await api.post<MutationReceipt>(`/security/v1/vulnerabilities`, {
        idempotency_key: newIdempotencyKey(),
        vulnerability_id: vulnId.trim(),
        source: source.trim(),
        component: JSON.parse(component),
        reason: reason.trim(),
      });
      setMsg(`Registered — ${r.aggregate_id}`);
    } catch (err) {
      if (err instanceof SyntaxError) setMsg(`Invalid JSON: ${err.message}`);
      else setMsg(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Register a vulnerability (Doc 68)" />
      <form onSubmit={submit} className="grid grid-cols-2 gap-4 mt-3">
        <Field label="Vulnerability ID" required hint="e.g. CVE-2026-xxxxx">
          <Input value={vulnId} onChange={(e) => setVulnId(e.target.value)} required />
        </Field>
        <Field label="Source" required>
          <Input value={source} onChange={(e) => setSource(e.target.value)} required />
        </Field>
        <Field label="Component (JSON)" required>
          <textarea className="input" rows={2} value={component} onChange={(e) => setComponent(e.target.value)} spellCheck={false} />
        </Field>
        <Field label="Reason" required>
          <Input value={reason} onChange={(e) => setReason(e.target.value)} required />
        </Field>
        <div style={{ gridColumn: "1 / -1" }}>
          {msg && <p className={msg.startsWith("Registered") ? "fs-2 mb-2" : "error-text mb-2"}>{msg}</p>}
          <Button type="submit" variant="secondary" disabled={busy || !vulnId.trim() || !reason.trim()}>
            {busy ? "Registering…" : "Register"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function RequestPrivilegedAccessCard() {
  const [requestedRole, setRequestedRole] = useState("");
  const [scope, setScope] = useState('{ "site": "*" }');
  const [reason, setReason] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [ticketRef, setTicketRef] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      const r = await api.post<MutationReceipt>(`/security/v1/privileged-access/requests`, {
        idempotency_key: newIdempotencyKey(),
        requested_role: requestedRole.trim(),
        scope: JSON.parse(scope),
        reason: reason.trim(),
        requested_start: start ? new Date(start).toISOString() : new Date().toISOString(),
        requested_end: end ? new Date(end).toISOString() : new Date(Date.now() + 3600_000).toISOString(),
        ticket_ref: ticketRef.trim() || null,
      });
      setMsg(`Request created — ${r.aggregate_id}. Approve it via the privileged-access operations console.`);
    } catch (err) {
      if (err instanceof SyntaxError) setMsg(`Invalid JSON: ${err.message}`);
      else setMsg(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Request privileged access (Doc 63)" />
      <form onSubmit={submit} className="grid grid-cols-2 gap-4 mt-3">
        <Field label="Requested role" required>
          <Input value={requestedRole} onChange={(e) => setRequestedRole(e.target.value)} required />
        </Field>
        <Field label="Ticket reference">
          <Input value={ticketRef} onChange={(e) => setTicketRef(e.target.value)} />
        </Field>
        <Field label="Scope (JSON)" required>
          <textarea className="input" rows={2} value={scope} onChange={(e) => setScope(e.target.value)} spellCheck={false} />
        </Field>
        <Field label="Reason" required>
          <Input value={reason} onChange={(e) => setReason(e.target.value)} required />
        </Field>
        <Field label="Requested start" hint="Defaults to now.">
          <Input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} />
        </Field>
        <Field label="Requested end" hint="Defaults to +1h.">
          <Input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
        </Field>
        <div style={{ gridColumn: "1 / -1" }}>
          {msg && <p className={msg.startsWith("Request created") ? "fs-2 mb-2" : "error-text mb-2"}>{msg}</p>}
          <Button type="submit" variant="primary" disabled={busy || !requestedRole.trim() || !reason.trim()}>
            {busy ? "Requesting…" : "Request access"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
