"use client";

import { use, useState } from "react";
import {
  api,
  canDispositionOos,
  hasPermission,
  formatDateTime,
  newIdempotencyKey,
  type MutationReceipt,
} from "@/lib/api";
import { useApiResource, useMe } from "@/lib/hooks";
import { RecordDetailShell, useCommand } from "@/components/shared/RecordDetailShell";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { Fact, IdFact } from "@/components/ui/FactGrid";
import { JsonPanel, HistoryPanel } from "@/components/ui/JsonPanel";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";

// GET /quality/oot/v1/{id} — app/modules/qc/router.py::get_oot_record
interface OotDetail {
  id: string;
  source_result_id: string;
  trend_rule_id: string | null;
  trend_rule_version: string | null;
  baseline_ref: string | null;
  trigger_details: Record<string, unknown> | null;
  state: string;
  investigation_notes: string | null;
  impact_assessment: string | null;
  investigation_owner_user_id: string | null;
  hold_status: string | null;
  version: number;
  opened_at: string | null;
  closed_at: string | null;
  reopen_history: Record<string, unknown>[];
}

export default function OotDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { me } = useMe();
  const { data, loading, error, reload } = useApiResource<OotDetail>(`/quality/oot/v1/${id}`);
  const [closing, setClosing] = useState(false);
  const [reopening, setReopening] = useState(false);

  const canClose = canDispositionOos(me) && data?.state === "open";
  const canReopen = hasPermission(me, "oot_record.reopen") && data?.state === "closed";

  return (
    <RecordDetailShell
      recordNumber={data ? `OOT ${data.id.slice(0, 8)}…` : ""}
      state={data?.state}
      subtitle={data ? `Source result ${data.source_result_id.slice(0, 8)}…` : undefined}
      backHref="/quality/oos"
      backLabel="OOS / OOT"
      loading={loading}
      error={error}
      actions={
        data && (
          <>
            {canClose && (
              <Button variant="success" onClick={() => setClosing(true)}>
                <Icon name="pen" /> Close OOT
              </Button>
            )}
            {canReopen && (
              <Button variant="secondary" onClick={() => setReopening(true)}>
                Reopen
              </Button>
            )}
          </>
        )
      }
      facts={
        data && (
          <>
            <Fact label="Trend rule version">{data.trend_rule_version ?? "—"}</Fact>
            <Fact label="Hold status">{data.hold_status ?? "—"}</Fact>
            <Fact label="Opened">{data.opened_at ? formatDateTime(data.opened_at) : "—"}</Fact>
            <Fact label="Closed">{data.closed_at ? formatDateTime(data.closed_at) : "—"}</Fact>
            <Fact label="Record version">{data.version}</Fact>
            <IdFact label="Source result" value={data.source_result_id} />
            {data.trend_rule_id && <IdFact label="Trend rule" value={data.trend_rule_id} />}
            {data.investigation_owner_user_id && (
              <IdFact label="Investigation owner" value={data.investigation_owner_user_id} />
            )}
          </>
        )
      }
    >
      {data && (
        <>
          <JsonPanel title="Trigger details" value={data.trigger_details} />
          {data.investigation_notes && (
            <p className="fs-2 mb-2">
              <span className="fact-k">Investigation notes:</span> {data.investigation_notes}
            </p>
          )}
          {data.impact_assessment && (
            <p className="fs-2 mb-2">
              <span className="fact-k">Impact assessment:</span> {data.impact_assessment}
            </p>
          )}
          <HistoryPanel title="Reopens" entries={data.reopen_history} />
        </>
      )}

      {data && closing && (
        <SignatureCeremony
          open
          onClose={() => setClosing(false)}
          onDone={() => {
            setClosing(false);
            reload();
          }}
          challengePath={`/quality/oot/v1/${data.id}/signature-challenges`}
          action="close"
          title="Close OOT"
          summary="Closes the out-of-trend record. Signer must be independent of the investigation owner (SoD)."
          submitLabel="Sign & close"
          submitVariant="success"
          onSign={(p) =>
            api.post<MutationReceipt>(`/quality/oot/v1/${data.id}/close`, {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              oot_record_id: data.id,
              expected_version: data.version,
            })
          }
        />
      )}

      {data && reopening && (
        <ReopenOotModal oot={data} onClose={() => setReopening(false)} onDone={() => { setReopening(false); reload(); }} />
      )}
    </RecordDetailShell>
  );
}

function ReopenOotModal({ oot, onClose, onDone }: { oot: OotDetail; onClose: () => void; onDone: () => void }) {
  const { busy, error, run } = useCommand(onDone);
  const [reason, setReason] = useState("");
  const [newEvidence, setNewEvidence] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() =>
      api.post(`/quality/oot/v1/${oot.id}/reopen`, {
        idempotency_key: newIdempotencyKey(),
        oot_record_id: oot.id,
        expected_version: oot.version,
        reason,
        new_evidence: newEvidence,
      })
    );
  }

  return (
    <Modal open onClose={onClose} title="Reopen OOT">
      <form onSubmit={submit}>
        <Field label="Reason" required>
          <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} required />
        </Field>
        <Field label="New evidence" required>
          <textarea className="input" rows={2} value={newEvidence} onChange={(e) => setNewEvidence(e.target.value)} required />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !reason.trim() || !newEvidence.trim()}>
            {busy ? "Reopening…" : "Reopen"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
