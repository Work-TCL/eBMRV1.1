"use client";

import { useEffect, useState } from "react";
import { api, ApiError, newIdempotencyKey, type MutationReceipt, type Organization } from "@/lib/api";
import { useRequireAdmin } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

export default function CompanyAdminPage() {
  const { isAdmin } = useRequireAdmin();

  const [org, setOrg] = useState<Organization | null>(null);
  const [orgName, setOrgName] = useState("");
  const [orgError, setOrgError] = useState<string | null>(null);
  const [orgOk, setOrgOk] = useState(false);
  const [orgBusy, setOrgBusy] = useState(false);

  useEffect(() => {
    api.get<Organization>("/organization").then((o) => {
      setOrg(o);
      setOrgName(o.name);
    });
  }, []);

  if (!isAdmin) return null;

  async function onSaveOrg(e: React.FormEvent) {
    e.preventDefault();
    if (!org) return;
    setOrgBusy(true);
    setOrgError(null);
    setOrgOk(false);
    try {
      await api.patch<MutationReceipt>("/organization", { idempotency_key: newIdempotencyKey(), name: orgName });
      setOrg({ ...org, name: orgName });
      setOrgOk(true);
    } catch (err) {
      setOrgError(err instanceof ApiError ? err.message : "Failed to update company");
    } finally {
      setOrgBusy(false);
    }
  }

  return (
    <div>
      <PageHead title="Company" subtitle="This deployment's single company record." />

      <Card pad>
        <CardHeader title="Company details" />
        {org && (
          <form onSubmit={onSaveOrg}>
            <Field label="Name" required error={orgError}>
              <Input value={orgName} onChange={(e) => setOrgName(e.target.value)} required />
            </Field>
            {orgOk && !orgError && <p className="mb-3">Saved.</p>}
            <Button type="submit" variant="primary" disabled={orgBusy}>
              {orgBusy ? "Saving…" : "Save company"}
            </Button>
          </form>
        )}
      </Card>
    </div>
  );
}
