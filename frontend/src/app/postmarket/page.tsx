"use client";

import { useState } from "react";
import { api, ApiError, holdsAnyRole, newIdempotencyKey, type Me, type MutationReceipt } from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { FormConsole } from "@/components/shared/FormConsole";

const canWork = (me: Me | null) => holdsAnyRole(me, ["Admin", "QA Reviewer", "QA Releaser"]);

export default function PostmarketPage() {
  const { me } = useMe();

  return (
    <div>
      <PageHead
        title="Postmarket"
        subtitle="Documents 58–60 — safety cases, signal management, the regulatory reporting clock and Part 4 obligations."
      />

      <DashboardCards />

      {canWork(me) && <CreateSafetyCaseCard />}
      {canWork(me) && <ReportabilityCard />}

      {canWork(me) && (
        <>
          <FormConsole
            title="Safety case & signal operations (Doc 58)"
            root="/postmarket/v1"
            ops={[
              {
                path: "safety-cases/{case_id}/classifications",
                label: "Classify a safety case",
                about: "Records the clinical / device / seriousness classification and expectedness.",
                fields: [
                  { name: "case_id", label: "Safety case ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "constituent_attribution", label: "Constituent attribution", type: "select", options: [
                    { value: "DRUG", label: "Drug" }, { value: "DEVICE", label: "Device" }, { value: "COMBINATION", label: "Combination" }] },
                  { name: "rationale", label: "Rationale", type: "textarea", required: true },
                  { name: "classification", label: "Classification detail (JSON)", type: "json" },
                ],
              },
              { path: "safety-cases/{case_id}/duplicate-candidates", label: "List probable duplicates", method: "GET",
                fields: [{ name: "case_id", label: "Safety case ID", required: true }] },
              { path: "safety-cases/{case_id}/followups", label: "Add a follow-up (JSON)" },
              { path: "signals", label: "Open a safety signal (JSON)" },
              { path: "signals/{signal_id}/assessments", label: "Assess a signal (JSON)" },
              { path: "sources", label: "Register a postmarket source (JSON)" },
              { path: "safety-cases/{case_id}/duplicate-links", label: "Link duplicate cases (JSON)" },
              { path: "surveillance-metrics:calculate", label: "Calculate a surveillance metric (JSON)" },
              { path: "signal-rules:evaluate", label: "Evaluate signal rules (JSON)" },
              { path: "signals/{signal_id}/escalations", label: "Escalate a signal (JSON)" },
              { path: "periodic-datasets:freeze", label: "Freeze a periodic safety dataset (JSON)" },
            ]}
          />

          <FormConsole
            title="Regulatory reporting operations (Doc 59)"
            root="/regulatory/v1"
            ops={[
              {
                path: "tracks/{track_id}/decisions",
                label: "Decide reportability",
                about: "Records the reportable / not-reportable decision for one report type and its rationale.",
                fields: [
                  { name: "track_id", label: "Track ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                  { name: "decision", label: "Decision", type: "select", required: true, options: [
                    { value: "REPORTABLE", label: "Reportable" }, { value: "NOT_REPORTABLE", label: "Not reportable" }, { value: "PENDING", label: "Pending" }] },
                  { name: "rationale", label: "Rationale", type: "textarea", required: true },
                ],
              },
              {
                path: "reports/{report_id}/approve",
                label: "Approve a report",
                fields: [
                  { name: "report_id", label: "Report ID", required: true },
                  { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
                ],
              },
              { path: "tracks/{track_id}/deadline:calculate", label: "Calculate a regulatory deadline (JSON)" },
              { path: "tracks/{track_id}/reports", label: "Build a regulatory report (JSON)" },
              { path: "reports/{report_id}/payloads:generate", label: "Generate a submission payload (JSON)" },
              { path: "reports/{report_id}/submissions", label: "Submit a report (JSON)" },
              { path: "submissions/{attempt_id}/acknowledgements", label: "Record an acknowledgement / rejection (JSON)" },
              { path: "reports/{report_id}/followups", label: "Create a follow-up report task (JSON)" },
              { path: "cases/{case_id}/part4-deduplication:evaluate", label: "Evaluate Part 4 same-event dedup (JSON)" },
              { path: "audit-packages:freeze", label: "Freeze an inspection audit package (JSON)" },
            ]}
          />

          <FormConsole
            title="Part 4 obligations (Doc 60)"
            root="/postmarket/v1"
            ops={[
              { path: "field-alerts", label: "Raise a field alert obligation (JSON)" },
              { path: "obligations/{obligation_id}/legal-hold", label: "Apply / lift a legal hold (JSON)" },
              { path: "applicant-relationships", label: "Register an applicant/constituent relationship (JSON)" },
              { path: "cases/{case_id}/part4-sharing:evaluate", label: "Evaluate Part 4 sharing (JSON)" },
              { path: "sharing/{share_id}/package", label: "Build a sharing package (JSON)" },
              { path: "sharing/{share_id}/record-sent", label: "Record a package sent (JSON)" },
              { path: "field-actions/{field_action_id}/correction-removal-assessment", label: "Correction/removal assessment (JSON)" },
              { path: "correction-removal/{record_id}/decision", label: "Correction/removal decision (JSON)" },
              { path: "field-alerts/{obligation_id}/decision", label: "Field alert decision (JSON)" },
              { path: "bpdr-tracks", label: "Open a BPDR track (JSON)" },
              { path: "periodic-cycles:generate", label: "Generate periodic safety cycles (JSON)" },
              { path: "periodic-cycles/{cycle_id}/dataset:freeze", label: "Freeze a periodic cycle dataset (JSON)" },
              { path: "fda-requests", label: "Log an FDA request / correspondence (JSON)" },
              { path: "obligations/{obligation_id}/deadline-overrides", label: "Override an obligation deadline (JSON)" },
              { path: "retention:calculate", label: "Calculate retention basis (JSON)" },
            ]}
          />
        </>
      )}
    </div>
  );
}

function DashboardCards() {
  const [dashboard, setDashboard] = useState<unknown>(undefined);
  const [calendar, setCalendar] = useState<unknown>(undefined);

  async function load() {
    setDashboard(await api.get<unknown>(`/postmarket/v1/dashboard`).catch((e) => ({ error: String(e) })));
    setCalendar(await api.get<unknown>(`/postmarket/v1/regulatory-calendar`).catch((e) => ({ error: String(e) })));
  }

  return (
    <Card pad className="mb-4">
      <div className="flex justify-between items-center">
        <CardHeader title="Signal dashboard & regulatory calendar" />
        <Button variant="secondary" onClick={load}>
          <Icon name="refresh" /> Load
        </Button>
      </div>
      {dashboard !== undefined && (
        <div className="mt-3">
          <JsonPanel title="Signal dashboard" value={dashboard} />
        </div>
      )}
      {calendar !== undefined && (
        <div className="mt-3">
          <JsonPanel title="Unified regulatory calendar" value={calendar} />
        </div>
      )}
    </Card>
  );
}

function CreateSafetyCaseCard() {
  const { siteId } = useSiteId();
  const [f, setF] = useState({
    safety_case_number: "",
    source_record_type: "complaint",
    source_record_id: "",
    source_record_version: "1",
    company_initial_receipt_at: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newId, setNewId] = useState<string | null>(null);

  function set(k: keyof typeof f, v: string) {
    setF((c) => ({ ...c, [k]: v }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNewId(null);
    try {
      const receipt = await api.post<MutationReceipt>(`/postmarket/v1/safety-cases`, {
        idempotency_key: newIdempotencyKey(),
        ...(siteId ? { site_id: siteId } : {}),
        safety_case_number: f.safety_case_number.trim(),
        source_record_type: f.source_record_type.trim(),
        source_record_id: f.source_record_id.trim(),
        source_record_version: Number(f.source_record_version),
        company_initial_receipt_at: f.company_initial_receipt_at
          ? new Date(f.company_initial_receipt_at).toISOString()
          : null,
      });
      setNewId(receipt.aggregate_id);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Open a safety case" />
      <form onSubmit={submit} className="grid grid-cols-2 gap-4 mt-3">
        <Field label="Safety case number" required>
          <Input value={f.safety_case_number} onChange={(e) => set("safety_case_number", e.target.value)} required />
        </Field>
        <Field label="Source record type" required>
          <Input value={f.source_record_type} onChange={(e) => set("source_record_type", e.target.value)} required />
        </Field>
        <Field label="Source record ID" required>
          <Input value={f.source_record_id} onChange={(e) => set("source_record_id", e.target.value)} required />
        </Field>
        <Field label="Source record version" required>
          <Input type="number" value={f.source_record_version} onChange={(e) => set("source_record_version", e.target.value)} required />
        </Field>
        <Field label="Company initial receipt at" hint="Starts the regulatory clock.">
          <Input type="datetime-local" value={f.company_initial_receipt_at} onChange={(e) => set("company_initial_receipt_at", e.target.value)} />
        </Field>
        <div style={{ gridColumn: "1 / -1" }}>
          {error && <p className="error-text mb-2">{error}</p>}
          {newId && (
            <Banner tone="ok" title="Safety case opened">
              Case ID <span className="tabular">{newId}</span>
            </Banner>
          )}
          <Button type="submit" variant="primary" disabled={busy || !f.safety_case_number.trim() || !f.source_record_id.trim()}>
            {busy ? "Opening…" : "Open safety case"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function ReportabilityCard() {
  const { siteId } = useSiteId();
  const [safetyCaseId, setSafetyCaseId] = useState("");
  const [tracks, setTracks] = useState('[\n  { "report_type_code": "", "report_type_version": "", "application_context": "", "rule_version": "" }\n]');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function createTracks(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      await api.post<MutationReceipt>(`/regulatory/v1/cases/${safetyCaseId.trim()}/reportability-tracks`, {
        idempotency_key: newIdempotencyKey(),
        ...(siteId ? { site_id: siteId } : {}),
        safety_case_id: safetyCaseId.trim(),
        tracks: JSON.parse(tracks),
      });
      setMsg("Reportability tracks created. Use the regulatory operations console below to calculate deadlines and record decisions.");
    } catch (err) {
      if (err instanceof SyntaxError) setMsg(`Invalid JSON: ${err.message}`);
      else setMsg(err instanceof ApiError ? `${err.code}: ${err.message}` : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card pad className="mb-4">
      <CardHeader title="Reportability workbench" />
      <p className="fs-2 text-muted mb-3">
        Document 59 — open the reportability tracks for a safety case (one per applicable report type). The
        regulatory clock, decision and report build then run per track in the operations console below.
      </p>
      <form onSubmit={createTracks}>
        <Field label="Safety case ID" required>
          <Input value={safetyCaseId} onChange={(e) => setSafetyCaseId(e.target.value)} required style={{ maxWidth: 360 }} />
        </Field>
        <Field label="Tracks (JSON array)" hint="[{report_type_code, report_type_version, application_context, rule_version}]">
          <textarea className="input" rows={5} value={tracks} onChange={(e) => setTracks(e.target.value)} spellCheck={false} />
        </Field>
        {msg && <p className={msg.startsWith("Reportability") ? "fs-2 mt-2" : "error-text mt-2"}>{msg}</p>}
        <Button type="submit" variant="primary" disabled={busy || !safetyCaseId.trim()} className="mt-2">
          {busy ? "Creating…" : "Create reportability tracks"}
        </Button>
      </form>
    </Card>
  );
}
