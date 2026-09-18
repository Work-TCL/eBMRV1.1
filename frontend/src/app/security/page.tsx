"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, canOperateSecurity, newIdempotencyKey, type MutationReceipt } from "@/lib/api";
import { useMe } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { FormConsole } from "@/components/shared/FormConsole";
import { SignedJsonForm } from "@/components/shared/SignedJsonForm";
import { KeyValueRows, buildKvObject, type KvRow } from "@/components/shared/RepeatableFields";

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
  const { me, loading } = useMe();
  const router = useRouter();
  const canOperate = canOperateSecurity(me);

  useEffect(() => {
    if (!loading && !canOperate) router.replace("/batch-execution");
  }, [me, loading, canOperate, router]);

  if (!canOperate) return null;

  return (
    <div>
      <PageHead
        title="Security"
        subtitle="Threat model, identity, privileged access, app/crypto controls, incidents and supply chain."
      />

      <ReadDashboards />
      <ParameterizedReadsCard />
      <RaiseIncidentCard />
      <RegisterVulnerabilityCard />
      <RequestPrivilegedAccessCard />

      <FormConsole
      title="Threat model & risk operations"
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
              {
                name: "impacted_attributes", label: "Impacted attributes", type: "stringList", itemLabel: "Attribute",
                placeholder: "e.g. confidentiality, integrity, availability",
                hint: "Which security attributes this threat impacts (optional).",
              },
              { name: "reason", label: "Reason" },
            ],
          },
          {
            path: "threat-models",
            label: "Create a threat model version",
            fields: [
              { name: "system_version", label: "System version", required: true },
              { name: "methodology_version", label: "Methodology version", required: true },
              { name: "deployment_profile", label: "Deployment profile", required: true },
              { name: "scope", label: "Scope", type: "kv" },
              { name: "assets", label: "Assets", type: "kv" },
              { name: "boundaries", label: "Boundaries", type: "kv" },
              { name: "reason", label: "Reason" },
            ],
          },
          {
            path: "threat-models/{id}/reviews",
            label: "Record a review",
            fields: [
              { name: "id", label: "Threat model version ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "change_id", label: "Change ID", required: true },
              { name: "trigger_type", label: "Trigger type", required: true, placeholder: "e.g. scheduled, architecture_change" },
              { name: "affected_modules", label: "Affected modules", type: "stringList", itemLabel: "Module" },
              { name: "reason", label: "Reason" },
            ],
          },
          {
            path: "threats/{id}/controls",
            label: "Map a control",
            fields: [
              { name: "id", label: "Threat ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "control_code", label: "Control code", required: true },
              { name: "mapping_type", label: "Mapping type", required: true, placeholder: "e.g. preventive, detective, corrective" },
              { name: "implementation_refs", label: "Implementation references", type: "kv" },
              { name: "objective", label: "Objective" },
              { name: "implementation_owner", label: "Implementation owner" },
              { name: "evidence_source", label: "Evidence source" },
              { name: "test_owner", label: "Test owner" },
              { name: "framework_mappings", label: "Framework mappings", type: "kv" },
              { name: "reason", label: "Reason" },
            ],
          },
          {
            path: "threats/{id}/risk-calculations",
            label: "Calculate residual risk",
            fields: [
              { name: "id", label: "Threat ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "risk_stage", label: "Risk stage", required: true, placeholder: "e.g. inherent, residual" },
              { name: "impact_inputs", label: "Impact inputs", type: "kv", required: true },
              { name: "likelihood_inputs", label: "Likelihood inputs", type: "kv", required: true },
              { name: "methodology", label: "Methodology", required: true },
              { name: "rating", label: "Rating", type: "kv", required: true },
              { name: "reason", label: "Reason" },
            ],
          },
          {
            path: "exceptions",
            label: "Raise a security exception",
            fields: [
              { name: "control_or_requirement", label: "Control or requirement", required: true },
              { name: "reason", label: "Reason", type: "textarea", required: true },
              { name: "expiry", label: "Expiry", type: "datetime", required: true },
              { name: "risk_assessment_ref", label: "Risk assessment reference", type: "kv" },
              { name: "compensating_controls", label: "Compensating controls", type: "kv" },
              { name: "remediation_target", label: "Remediation target", type: "kv" },
            ],
          },
        ]}
      />

      <SignedJsonForm
      title="Threat model & risk operations - signed"
        subtitle="Residual risk acceptance and security exception approval now require a Part 11 signature."
        root="/security/v1"
        ops={[
          {
            postPath: "risks/{risk_id}/accept",
            challengePath: "risks/{risk_id}/accept-signature-challenges",
            action: "accept_risk",
            label: "Accept a residual risk",
            about: "Formally accepts the residual risk on a threat's current risk calculation.",
            fields: [
              { name: "risk_id", label: "Risk (threat) ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "rationale", label: "Rationale", type: "textarea", required: true },
              { name: "expiry_review_date", label: "Expiry review date", type: "datetime" },
            ],
          },
          {
            postPath: "exceptions/{exception_id}/approve",
            challengePath: "exceptions/{exception_id}/approval-signature-challenges",
            action: "approve",
            label: "Approve a security exception",
            about: "The approver must be independent of whoever requested the exception.",
            fields: [{ name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" }],
          },
        ]}
      />

      <FormConsole
      title="Identity & session operations"
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
              { name: "subject_id", label: "Subject", type: "userSelect", required: true },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
          {
            path: "identity-providers",
            label: "Register an IdP config",
            fields: [
              { name: "deployment_label", label: "Deployment label", required: true },
              { name: "issuer", label: "Issuer", required: true },
              { name: "protocol", label: "Protocol", required: true, placeholder: "e.g. SAML2, OIDC" },
              { name: "trust_metadata", label: "Trust metadata", type: "kv", required: true },
              { name: "claim_mapping_version", label: "Claim mapping version", required: true },
              { name: "claim_mapping", label: "Claim mapping", type: "kv" },
              { name: "effective_from", label: "Effective from", type: "datetime" },
              { name: "effective_to", label: "Effective to", type: "datetime" },
              { name: "reason", label: "Reason" },
            ],
          },
          {
            path: "identity-providers/{identity_provider_config_id}/mappings",
            label: "Add a federation mapping",
            fields: [
              { name: "identity_provider_config_id", label: "IdP config ID", required: true },
              { name: "user_id", label: "User", type: "userSelect", required: true },
              { name: "issuer", label: "Issuer", required: true },
              { name: "subject", label: "Subject", required: true },
              { name: "claims", label: "Claims", type: "kv" },
              { name: "reason", label: "Reason" },
            ],
          },
          {
            path: "identity-providers/{identity_provider_config_id}/tokens:validate",
            label: "Validate a token",
            fields: [
              { name: "identity_provider_config_id", label: "IdP config ID", required: true },
              { name: "token", label: "Token", type: "textarea", required: true },
              { name: "expected_audience", label: "Expected audience", required: true },
            ],
          },
          {
            path: "service-identities",
            label: "Register a service identity",
            fields: [
              { name: "service_name", label: "Service name", required: true },
              { name: "auth_method", label: "Auth method", required: true, placeholder: "e.g. mtls, jwt" },
              { name: "credential_ref", label: "Credential reference", required: true },
              { name: "site_id", label: "Site ID" },
              { name: "allowed_audiences", label: "Allowed audiences", type: "stringList", itemLabel: "Audience" },
              { name: "allowed_scopes", label: "Allowed scopes", type: "stringList", itemLabel: "Scope" },
              { name: "reason", label: "Reason" },
            ],
          },
          {
            path: "service-identities/{service_identity_id}/revoke",
            label: "Revoke a service identity",
            fields: [
              { name: "service_identity_id", label: "Service identity ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
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
              { name: "decision", label: "Decision", type: "select", required: true, options: [{ value: "APPROVED", label: "Approved" }, { value: "DENIED", label: "Denied" }] },
              { name: "comments", label: "Comments", type: "textarea", required: true },
              { name: "duration_minutes", label: "Duration (minutes)", type: "number", default: "240" },
            ],
          },
          {
            path: "support-sessions",
            label: "Open a support session",
            fields: [
              { name: "grant_id", label: "Grant ID", required: true },
              { name: "support_case_ref", label: "Support case reference", required: true },
              { name: "customer_scope_ref", label: "Customer scope reference" },
              { name: "connection_source", label: "Connection source", type: "kv" },
              { name: "reason", label: "Reason" },
            ],
          },
          {
            path: "break-glass",
            label: "Break-glass access",
            about: "Emergency access outside the normal approval flow - used only when the incident requires it.",
            fields: [
              { name: "requested_role", label: "Requested role", required: true },
              { name: "incident_ref", label: "Incident reference", required: true },
              { name: "reason", label: "Reason", type: "textarea", required: true },
              { name: "duration_minutes", label: "Duration (minutes)", type: "number", default: "60" },
              { name: "scope", label: "Scope", type: "kv" },
            ],
          },
          {
            path: "admin-commands/{command_code}:execute",
            label: "Execute a controlled admin command",
            fields: [
              { name: "command_code", label: "Command code", required: true },
              { name: "privileged_session_id", label: "Privileged session ID", required: true },
              { name: "parameters", label: "Parameters", type: "kv" },
              { name: "reason", label: "Reason" },
            ],
          },
          {
            path: "privileged-sessions/{privileged_session_id}/close",
            label: "Close a privileged session",
            fields: [
              { name: "privileged_session_id", label: "Privileged session ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "outcome", label: "Outcome", required: true, placeholder: "e.g. completed, aborted" },
            ],
          },
          {
            path: "privileged-sessions/{privileged_session_id}/review",
            label: "Review a privileged session",
            fields: [
              { name: "privileged_session_id", label: "Privileged session ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "findings", label: "Findings", type: "textarea", required: true },
              { name: "outcome", label: "Outcome", default: "NO_ISSUES", hint: 'Defaults to "NO_ISSUES" if left blank.' },
            ],
          },
          {
            path: "secrets/{secret_id}/rotate",
            label: "Rotate a secret",
            fields: [
              { name: "secret_id", label: "Secret ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "reason", label: "Reason", type: "textarea", required: true },
              { name: "overlap_minutes", label: "Overlap (minutes)", type: "number", default: "60" },
              { name: "incident_ref", label: "Incident reference" },
            ],
          },
          {
            path: "certificates:issue",
            label: "Issue a certificate",
            fields: [
              { name: "subject_sans", label: "Subject SANs", type: "kv", required: true },
              {
                name: "profile", label: "Profile", type: "select", required: true,
                options: ["SERVICE_MTLS", "EDGE_GATEWAY", "ADMIN", "INTEGRATION"].map((v) => ({ value: v, label: v })),
              },
              { name: "validity_days", label: "Validity (days)", type: "number", required: true },
              { name: "issuer_ref", label: "Issuer reference", required: true },
              { name: "identity_id", label: "Identity ID" },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
          {
            path: "certificates/{certificate_id}/rotate",
            label: "Rotate a certificate",
            fields: [
              { name: "certificate_id", label: "Certificate ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "validity_days", label: "Validity (days)", type: "number", required: true },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
          {
            path: "certificates/{certificate_id}/revoke",
            label: "Revoke a certificate",
            fields: [
              { name: "certificate_id", label: "Certificate ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              {
                name: "revocation_reason", label: "Revocation reason", type: "select", required: true,
                options: ["KEY_COMPROMISE", "CA_COMPROMISE", "AFFILIATION_CHANGED", "SUPERSEDED", "CESSATION_OF_OPERATION", "PRIVILEGE_WITHDRAWN", "UNSPECIFIED"].map((v) => ({ value: v, label: v })),
              },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
          {
            path: "outbound-destinations",
            label: "Register an outbound destination",
            fields: [
              { name: "service_id", label: "Service ID", required: true },
              { name: "schemes_hosts_ports", label: "Schemes / hosts / ports", type: "kv", required: true },
              { name: "purpose", label: "Purpose", required: true },
              { name: "ip_range_rules", label: "IP range rules", type: "kv" },
              {
                name: "redirect_policy", label: "Redirect policy", type: "select", default: "BLOCK",
                options: [{ value: "BLOCK", label: "Block" }, { value: "SAME_HOST", label: "Same host" }, { value: "ALLOWLIST", label: "Allowlist" }],
              },
              { name: "auth_secret_ref", label: "Auth secret reference" },
            ],
          },
          {
            path: "webhook-profiles",
            label: "Register a webhook profile",
            fields: [
              { name: "provider", label: "Provider", required: true },
              { name: "auth_mechanism", label: "Auth mechanism", default: "HMAC_SHA256" },
              { name: "replay_window_seconds", label: "Replay window (seconds)", type: "number", default: "300" },
              { name: "schema_version", label: "Schema version", default: "1.0" },
              { name: "max_body_bytes", label: "Max body size (bytes)", type: "number", default: "1048576" },
              { name: "signing_secret_ref", label: "Signing secret reference" },
            ],
          },
        ]}
      />

      <FormConsole
        title="Incident & supply-chain operations (Docs 67, 68)"
        root="/security/v1"
        ops={[
          {
            path: "incidents/{incident_id}/containment",
            label: "Record a containment action",
            fields: [
              { name: "incident_id", label: "Incident ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "containment_command", label: "Containment command", required: true, placeholder: "e.g. isolate_host, revoke_credentials" },
              { name: "target", label: "Target", type: "kv", required: true },
              { name: "reason", label: "Reason", type: "textarea", required: true },
              { name: "outcome", label: "Outcome", default: "APPLIED" },
            ],
          },
          {
            path: "incidents/{incident_id}/evidence",
            label: "Attach forensic evidence",
            fields: [
              { name: "incident_id", label: "Incident ID", required: true },
              { name: "source", label: "Source", required: true },
              { name: "acquisition_at", label: "Acquired at", type: "datetime", required: true },
              {
                name: "hash_algorithm", label: "Hash algorithm", type: "select", default: "SHA-256",
                options: ["SHA-256", "SHA-384", "SHA-512"].map((v) => ({ value: v, label: v })),
              },
              { name: "digest", label: "Digest", required: true },
              { name: "object_ref", label: "Object reference" },
              { name: "custody_note", label: "Chain-of-custody note", type: "textarea", required: true },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
          {
            path: "incidents/{incident_id}/gxp-impact",
            label: "Assess GxP impact",
            fields: [
              { name: "incident_id", label: "Incident ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              {
                name: "impact_state", label: "Impact state", type: "select", required: true,
                options: [{ value: "NO_IMPACT", label: "No impact" }, { value: "IMPACT_CONFIRMED", label: "Impact confirmed" }],
              },
              { name: "assessment", label: "Assessment", type: "kv", required: true },
              { name: "qms_reference", label: "QMS reference" },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
          {
            path: "incidents/{incident_id}/close",
            label: "Close an incident",
            fields: [
              { name: "incident_id", label: "Incident ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "root_cause", label: "Root cause", type: "textarea", required: true },
              { name: "corrective_actions", label: "Corrective actions", type: "stringList", itemLabel: "Action", required: true },
              { name: "residual_risk", label: "Residual risk", required: true },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
          {
            path: "vulnerabilities/{vulnerability_id}/assess",
            label: "Assess a vulnerability",
            fields: [
              { name: "vulnerability_id", label: "Vulnerability ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              {
                name: "severity", label: "Severity", type: "select", required: true,
                options: ["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((v) => ({ value: v, label: v })),
              },
              { name: "kev_status", label: "Known Exploited Vulnerability", type: "bool", required: true },
              { name: "gxp_impact", label: "GxP impact", type: "kv", required: true },
              { name: "remediation_due", label: "Remediation due", type: "datetime", required: true },
              { name: "assessment", label: "Assessment", type: "kv", required: true },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
          {
            path: "vulnerabilities/{vulnerability_id}/exceptions",
            label: "Grant a vulnerability exception",
            fields: [
              { name: "vulnerability_id", label: "Vulnerability ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "rationale", label: "Rationale", type: "textarea", required: true },
              { name: "compensating_controls", label: "Compensating controls", type: "stringList", itemLabel: "Control", required: true },
              { name: "expiry", label: "Expiry", type: "datetime", required: true },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
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
      <div className="flex flex-wrap items-end gap-3 mt-3">
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

function ParameterizedReadsCard() {
  const [threatModelVersionId, setThreatModelVersionId] = useState("");
  const [deploymentProfile, setDeploymentProfile] = useState("");
  const [releaseId, setReleaseId] = useState("");
  const [result, setResult] = useState<{ label: string; data: unknown } | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(label: string, path: string) {
    setBusy(true);
    setResult(null);
    try {
      setResult({ label, data: await api.get<unknown>(path) });
    } catch (err) {
      setResult({ label, data: { error: err instanceof Error ? err.message : String(err) } });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Control matrix & release security evidence" />
      <div className="grid grid-cols-3 gap-4 mb-3">
        <Field label="Threat model version ID">
          <Input value={threatModelVersionId} onChange={(e) => setThreatModelVersionId(e.target.value)} />
        </Field>
        <Field label="Deployment profile" hint="Optional.">
          <Input value={deploymentProfile} onChange={(e) => setDeploymentProfile(e.target.value)} />
        </Field>
        <Field label="Release ID">
          <Input value={releaseId} onChange={(e) => setReleaseId(e.target.value)} />
        </Field>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="secondary"
          disabled={busy || !threatModelVersionId.trim()}
          onClick={() => {
            const q = new URLSearchParams({ threat_model_version_id: threatModelVersionId.trim() });
            if (deploymentProfile.trim()) q.set("deployment_profile", deploymentProfile.trim());
            run("Control matrix", `/security/v1/control-matrix?${q.toString()}`);
          }}
        >
          <Icon name="search" /> Generate control matrix
        </Button>
        <Button
          variant="secondary"
          disabled={busy || !releaseId.trim()}
          onClick={() => run("Release security evidence", `/security/v1/releases/${encodeURIComponent(releaseId.trim())}/security-evidence`)}
        >
          <Icon name="search" /> Release security evidence
        </Button>
      </div>
      {result && (
        <div className="mt-3">
          <JsonPanel title={result.label} value={result.data} />
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
      setMsg(`Incident opened - ${r.aggregate_id}`);
    } catch (err) {
      setMsg(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
    <CardHeader title="Raise a security incident" />
      <form onSubmit={submit} className="grid grid-cols-2 gap-4 mt-3">
        <Field label="Title" required>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </Field>
        <Field label="Severity" required hint="e.g. LOW, MEDIUM, HIGH, CRITICAL">
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
  const [componentName, setComponentName] = useState("");
  const [componentVersion, setComponentVersion] = useState("");
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
        component: { name: componentName.trim(), version: componentVersion.trim() },
        reason: reason.trim(),
      });
      setMsg(`Registered - ${r.aggregate_id}`);
    } catch (err) {
      setMsg(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
    <CardHeader title="Register a vulnerability" />
      <form onSubmit={submit} className="grid grid-cols-2 gap-4 mt-3">
        <Field label="Vulnerability ID" required hint="e.g. CVE-2026-xxxxx">
          <Input value={vulnId} onChange={(e) => setVulnId(e.target.value)} required />
        </Field>
        <Field label="Source" required hint="e.g. INTERNAL_SCAN, SCA, CONTAINER_SCAN, CUSTOMER_REPORT, RESEARCHER, VENDOR_ADVISORY">
          <Input value={source} onChange={(e) => setSource(e.target.value)} required />
        </Field>
        <Field label="Component name" required>
          <Input value={componentName} onChange={(e) => setComponentName(e.target.value)} required />
        </Field>
        <Field label="Component version">
          <Input value={componentVersion} onChange={(e) => setComponentVersion(e.target.value)} />
        </Field>
        <Field label="Reason" required>
          <Input value={reason} onChange={(e) => setReason(e.target.value)} required />
        </Field>
        <div style={{ gridColumn: "1 / -1" }}>
          {msg && <p className={msg.startsWith("Registered") ? "fs-2 mb-2" : "error-text mb-2"}>{msg}</p>}
          <Button type="submit" variant="secondary" disabled={busy || !vulnId.trim() || !componentName.trim() || !reason.trim()}>
            {busy ? "Registering…" : "Register"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function RequestPrivilegedAccessCard() {
  const [requestedRole, setRequestedRole] = useState("");
  const [scope, setScope] = useState<KvRow[]>([{ key: "site", value: "*" }]);
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
        scope: buildKvObject(scope),
        reason: reason.trim(),
        requested_start: start ? new Date(start).toISOString() : new Date().toISOString(),
        requested_end: end ? new Date(end).toISOString() : new Date(Date.now() + 3600_000).toISOString(),
        ticket_ref: ticketRef.trim() || null,
      });
      setMsg(`Request created - ${r.aggregate_id}. Approve it via the privileged-access operations console.`);
    } catch (err) {
      setMsg(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
    <CardHeader title="Request privileged access" />
      <form onSubmit={submit} className="grid grid-cols-2 gap-4 mt-3">
        <Field label="Requested role" required>
          <Input value={requestedRole} onChange={(e) => setRequestedRole(e.target.value)} required />
        </Field>
        <Field label="Ticket reference">
          <Input value={ticketRef} onChange={(e) => setTicketRef(e.target.value)} />
        </Field>
        <div style={{ gridColumn: "1 / -1" }}>
          <KeyValueRows label="Scope" hint='What this access covers, e.g. "site" → "*" for every site.' value={scope} onChange={setScope} />
        </div>
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
