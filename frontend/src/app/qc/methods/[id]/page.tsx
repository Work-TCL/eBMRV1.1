"use client";

import { use, useState } from "react";
import { api, hasPermission, formatDateTime } from "@/lib/api";
import { useApiResource, useMe } from "@/lib/hooks";
import { RecordDetailShell } from "@/components/shared/RecordDetailShell";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { Fact } from "@/components/ui/FactGrid";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

// GET /qc/v1/methods/{method_version_id} — app/modules/qc/router.py::get_qc_method_version_detail
interface QcMethodVersionDetail {
  method_version_id: string;
  method_code: string;
  version_no: number;
  name: string;
  method_type: string;
  validation_evidence_reference: string | null;
  modification_reason: string | null;
  lifecycle_state: string;
  effective_from: string | null;
  effective_to: string | null;
  version: number;
  site_id: string;
}

export default function QcMethodDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const { data, loading, error, reload } = useApiResource<QcMethodVersionDetail>(`/qc/v1/methods/${id}`);
  const [releasing, setReleasing] = useState(false);

  const canRelease = hasPermission(me, "qc_method.release");

  return (
    <RecordDetailShell
      recordNumber={data ? `${data.method_code} v${data.version_no}` : ""}
      state={data?.lifecycle_state}
      subtitle={data?.name}
      backHref="/qc"
      backLabel="QC testing"
      loading={loading}
      error={error}
      actions={
        data &&
        canRelease &&
        data.lifecycle_state === "draft" && (
          <Button variant="success" onClick={() => setReleasing(true)}>
            <Icon name="pen" /> Release
          </Button>
        )
      }
      facts={
        data && (
          <>
            <Fact label="Method type">{data.method_type}</Fact>
            <Fact label="Validation evidence">{data.validation_evidence_reference ?? "—"}</Fact>
            <Fact label="Modification reason">{data.modification_reason ?? "—"}</Fact>
            <Fact label="Effective from">{data.effective_from ? formatDateTime(data.effective_from) : "—"}</Fact>
            <Fact label="Effective to">{data.effective_to ? formatDateTime(data.effective_to) : "—"}</Fact>
            <Fact label="Record version">{data.version}</Fact>
          </>
        )
      }
    >
      {data && releasing && (
        <SignatureCeremony
          open
          onClose={() => setReleasing(false)}
          onDone={() => {
            setReleasing(false);
            reload();
          }}
          challengePath={`/qc/v1/methods/${data.method_version_id}/signature-challenges`}
          action="release"
          title={`Release - ${data.method_code} v${data.version_no}`}
          summary={
            <>
              You are about to release <strong>{data.method_code} v{data.version_no}</strong> for use by test
              orders.
            </>
          }
          reason="none"
          submitLabel="Sign & release"
          submitVariant="success"
          onSign={(p) =>
            api.post(`/qc/v1/methods/drafts/${data.method_version_id}/release`, {
              idempotency_key: p.idempotency_key,
              method_version_id: data.method_version_id,
              expected_version: data.version,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
            })
          }
        />
      )}
    </RecordDetailShell>
  );
}
