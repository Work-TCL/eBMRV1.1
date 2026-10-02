"use client";

import { use, useState } from "react";
import { api, hasPermission } from "@/lib/api";
import { useApiResource, useMe } from "@/lib/hooks";
import { RecordDetailShell } from "@/components/shared/RecordDetailShell";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { Fact, IdFact } from "@/components/ui/FactGrid";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

interface TestDefinition {
  id: string;
  test_code: string;
  test_name: string;
  result_data_type: string;
  uom: string | null;
}

// GET /qc/v1/specifications/{id} — app/modules/qc/router.py::get_specification
interface SpecificationDetail {
  id: string;
  spec_code: string;
  version_no: number;
  status: string;
  scope_type: string;
  scope_version_id: string;
  version: number;
  test_definitions: TestDefinition[];
}

export default function SpecificationDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const { data, loading, error, reload } = useApiResource<SpecificationDetail>(`/qc/v1/specifications/${id}`);
  const [releasing, setReleasing] = useState(false);

  const canRelease = hasPermission(me, "qc_test_specification.release");

  return (
    <RecordDetailShell
      recordNumber={data ? `${data.spec_code} v${data.version_no}` : ""}
      state={data?.status}
      backHref="/qc"
      backLabel="QC testing"
      loading={loading}
      error={error}
      actions={
        data &&
        canRelease &&
        data.status === "draft" && (
          <Button variant="success" onClick={() => setReleasing(true)}>
            <Icon name="pen" /> Release
          </Button>
        )
      }
      facts={
        data && (
          <>
            <Fact label="Scope type">{data.scope_type}</Fact>
            <Fact label="Test definitions">{data.test_definitions.length}</Fact>
            <Fact label="Record version">{data.version}</Fact>
            <IdFact label="Scope version" value={data.scope_version_id} />
          </>
        )
      }
    >
      {data && (
        <Card>
          <CardHeader title="Test definitions" />
          {data.test_definitions.length === 0 ? (
            <EmptyState icon="flask">No test definitions on this specification.</EmptyState>
          ) : (
            <Table>
              <thead>
                <tr>
                  <th>Test code</th>
                  <th>Test name</th>
                  <th>Result type</th>
                  <th>UOM</th>
                </tr>
              </thead>
              <tbody>
                {data.test_definitions.map((d) => (
                  <tr key={d.id}>
                    <td className="fs-2 font-semibold">{d.test_code}</td>
                    <td className="fs-2">{d.test_name}</td>
                    <td className="fs-2">{d.result_data_type}</td>
                    <td className="fs-2">{d.uom ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}

      {data && releasing && (
        <SignatureCeremony
          open
          onClose={() => setReleasing(false)}
          onDone={() => {
            setReleasing(false);
            reload();
          }}
          challengePath={`/qc/v1/specifications/${data.id}/signature-challenges`}
          action="release"
          title={`Release - ${data.spec_code} v${data.version_no}`}
          summary="Releasing makes every test definition on this specification usable for a real test order - this cannot be undone by unreleasing it."
          submitLabel="Sign & release"
          submitVariant="success"
          onSign={(p) =>
            api.post(`/qc/v1/specifications/${data.id}/release`, {
              idempotency_key: p.idempotency_key,
              specification_id: data.id,
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
