"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useRequireAdmin, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { SignedJsonForm } from "@/components/shared/SignedJsonForm";

export default function EdgePage() {
  const { isAdmin } = useRequireAdmin();
  const { siteId } = useSiteId();
  if (!isAdmin) return null;

  return (
    <div>
      <PageHead
        title="Edge gateways"
        subtitle="On-prem edge gateway enrollment, certificate rotation and configuration."
      />

      <Banner tone="info" title="Machine-to-machine operations aren't shown here">
        Observation ingest, health heartbeats and security-event reporting (`POST
        /edge/v1/gateways/{'{gateway_id}'}/observations:batch`, `/health`, `/security-events`) are
        authenticated with a per-gateway service credential issued at enrollment, not a signed-in user
        session - there is nothing this admin console can call for them. They are exercised by the gateway
        itself, not from here.
      </Banner>

      <GetCard
        title="Gateway detail & configuration"
        subtitle="No list-gateways endpoint exists yet (verified: no backend route) - look up a gateway by its ID."
        inputs={[{ name: "gateway_id", label: "Gateway ID" }]}
        endpoints={(v) => [
          { label: "Gateway detail", path: v.gateway_id ? `/edge/v1/gateways/${encodeURIComponent(v.gateway_id)}` : null },
          { label: "Current configuration", path: v.gateway_id ? `/edge/v1/gateways/${encodeURIComponent(v.gateway_id)}/configuration` : null },
        ]}
      />

      <SignedJsonForm
        title="Enroll a gateway"
        subtitle="Consumes a one-time bootstrap token issued out-of-band and issues the gateway's service credential - shown exactly once in the response below."
        root="/edge/v1"
        ops={[
          {
            postPath: "enrollments",
            challengePath: "enrollments/signature-challenges",
            action: "enroll",
            label: "Enroll a new gateway",
            mirrorBodyInChallenge: true,
            about: "The challenge binds to the bootstrap token and fingerprint before any gateway row exists.",
            fields: [
              { name: "bootstrap_token", label: "Bootstrap token", required: true },
              { name: "site_id", label: "Site ID", required: true, hint: `This deployment's site ID: ${siteId ?? "loading…"}` },
              { name: "gateway_fingerprint", label: "Gateway fingerprint", required: true },
              { name: "csr", label: "CSR (optional)", type: "textarea" },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
        ]}
      />

      <SignedJsonForm
        title="Rotate a gateway's certificate"
        subtitle="The signer must be independent of whoever originally enrolled this gateway."
        root="/edge/v1"
        ops={[
          {
            postPath: "gateways/{gateway_id}/certificate-rotation",
            challengePath: "gateways/{gateway_id}/signature-challenges",
            action: "certificate_rotation",
            label: "Rotate certificate",
            fields: [
              { name: "gateway_id", label: "Gateway ID", required: true },
              { name: "expected_version", label: "Expected version", type: "number", required: true, default: "1" },
              { name: "new_fingerprint", label: "New certificate fingerprint", required: true },
              { name: "reason", label: "Reason", type: "textarea", required: true },
            ],
          },
        ]}
      />
    </div>
  );
}

interface GetInput {
  name: string;
  label: string;
  placeholder?: string;
}

/** Local copy of `platform/page.tsx`'s `GetCard` — small enough, and specific enough to each page's own
 * endpoint set, that the existing pattern is to keep it per-page rather than share one component. */
function GetCard({
  title,
  subtitle,
  inputs,
  endpoints,
}: {
  title: string;
  subtitle: string;
  inputs: GetInput[];
  endpoints: (values: Record<string, string>) => { label: string; path: string | null }[];
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<{ label: string; data: unknown } | null>(null);
  const [busy, setBusy] = useState(false);

  const eps = endpoints(values);

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
      <CardHeader title={title} />
      <p className="fs-2 text-muted mb-3">{subtitle}</p>
      {inputs.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-3">
          {inputs.map((i) => (
            <Field key={i.name} label={i.label}>
              <Input
                value={values[i.name] ?? ""}
                onChange={(e) => setValues((c) => ({ ...c, [i.name]: e.target.value }))}
                placeholder={i.placeholder}
              />
            </Field>
          ))}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {eps.map((ep) => (
          <Button key={ep.label} variant="secondary" disabled={busy || !ep.path} onClick={() => ep.path && run(ep.label, ep.path)}>
            <Icon name="search" /> {ep.label}
          </Button>
        ))}
      </div>
      {result && (
        <div className="mt-3">
          <JsonPanel title={result.label} value={result.data} />
        </div>
      )}
    </Card>
  );
}
