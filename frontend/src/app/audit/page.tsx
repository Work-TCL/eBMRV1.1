"use client";

import { useState } from "react";
import { api, type ListQuery, type Paged, type Site } from "@/lib/api";
import { useEntityOptions, useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { EntityPickerField } from "@/components/shared/EntityPicker";

// Matches app/modules/audit/service.py::event_to_dict — GET /audit/v1/search.
interface AuditEvent {
  id: string;
  site_id: string | null;
  aggregate_type: string;
  aggregate_id: string;
  aggregate_version: number;
  action: string;
  actor_type: string;
  actor_id: string;
  actor_username: string | null;
  occurred_at: string;
  reason: string | null;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  changed_fields: string[];
  signature_id: string | null;
  correlation_id: string;
  prev_event_hash: string | null;
  event_hash: string;
  // Present only via GET /audit/v1/records/{aggregate_type}/{aggregate_id}?verify_chain=true — absent
  // (undefined) from the plain /search results this page otherwise uses.
  chain_valid?: boolean | null;
}

const HAS_SIGNATURE_OPTIONS = [
  { value: "", label: "Any" },
  { value: "true", label: "Signed only" },
  { value: "false", label: "Unsigned only" },
];

export default function AuditLedgerPage() {
  const { sites } = useSites();
  const entities = useEntityOptions();
  const [aggregateType, setAggregateType] = useState("");
  const [aggregateId, setAggregateId] = useState("");
  const [actorId, setActorId] = useState("");
  const [siteId, setSiteId] = useState("");
  const [hasSignature, setHasSignature] = useState("");
  const [occurredFrom, setOccurredFrom] = useState("");
  const [occurredTo, setOccurredTo] = useState("");
  const [verifyChain, setVerifyChain] = useState(false);
  const [selected, setSelected] = useState<AuditEvent | null>(null);

  const canVerifyChain = Boolean(aggregateType.trim() && aggregateId.trim());

  function fetchEvents(query: ListQuery): Promise<Paged<AuditEvent>> {
    const search = new URLSearchParams({
      page: String(query.page),
      page_size: String(query.page_size),
      sort_dir: query.sort_dir,
    });
    if (query.q) search.set("q", query.q);
    search.set("sort_by", query.sort_by ?? "occurred_at");

    // GET /audit/v1/records/{aggregate_type}/{aggregate_id}?verify_chain=true — the only endpoint that
    // reports whether this record's hash chain is intact — is a distinct route, not a /search query
    // param (verified against audit/router.py), so a chain-verified lookup switches the base URL rather
    // than merely adding one more filter to /search.
    if (canVerifyChain && verifyChain) {
      search.set("verify_chain", "true");
      return api.get<Paged<AuditEvent>>(
        `/audit/v1/records/${encodeURIComponent(aggregateType.trim())}/${encodeURIComponent(aggregateId.trim())}?${search.toString()}`
      );
    }

    if (aggregateType) search.set("aggregate_type", aggregateType);
    if (aggregateId.trim()) search.set("aggregate_id", aggregateId.trim());
    if (actorId.trim()) search.set("actor_id", actorId.trim());
    if (siteId) search.set("site_id", siteId);
    if (hasSignature) search.set("has_signature", hasSignature);
    if (occurredFrom) search.set("occurred_from", new Date(occurredFrom).toISOString());
    if (occurredTo) search.set("occurred_to", new Date(occurredTo).toISOString());
    return api.get<Paged<AuditEvent>>(`/audit/v1/search?${search.toString()}`);
  }

  const siteName = (id: string | null) => (id ? sites.find((s) => s.id === id)?.code ?? id.slice(0, 8) : "—");

  const columns: DataTableColumn<AuditEvent>[] = [
    {
      key: "occurred_at",
      header: "Time",
      sortable: true,
      render: (e) => <span className="tabular fs-2">{new Date(e.occurred_at).toLocaleString()}</span>,
    },
    {
      key: "aggregate_type",
      header: "Record",
      sortable: true,
      render: (e) => (
        <span>
          {e.aggregate_type} <span className="text-muted tabular fs-1">({e.aggregate_id.slice(0, 8)})</span>
        </span>
      ),
    },
    { key: "action", header: "Action", sortable: true },
    {
      key: "actor_username",
      header: "Actor",
      render: (e) => e.actor_username ?? <span className="text-muted">{e.actor_type}</span>,
    },
    { key: "site_id", header: "Site", render: (e) => siteName(e.site_id) },
    {
      key: "signature_id",
      header: "Signed",
      render: (e) => (e.signature_id ? <Icon name="badge-check" /> : "—"),
    },
    {
      key: "changed_fields",
      header: "Changed fields",
      render: (e) => (e.changed_fields.length ? e.changed_fields.join(", ") : "—"),
    },
    {
      key: "chain_valid",
      header: "Chain",
      render: (e) =>
        e.chain_valid === undefined ? (
          <span className="text-muted">—</span>
        ) : e.chain_valid ? (
          <Icon name="check-circle" />
        ) : (
          <span className="error-text">
            <Icon name="alert-triangle" /> broken
          </span>
        ),
    },
  ];

  return (
    <div>
      <PageHead
        title="Audit ledger"
        subtitle="Search and review every regulated audit event - append-only, hash-chained, never editable."
      />

      <div className="flex items-end gap-4 mb-4" style={{ flexWrap: "wrap" }}>
        <Field label="Record ID" hint="One record's full timeline.">
          <Input
            value={aggregateId}
            onChange={(e) => setAggregateId(e.target.value)}
            placeholder="aggregate UUID"
            style={{ maxWidth: 210 }}
          />
        </Field>
        <EntityPickerField
          label="Actor ID"
          hint="One user's activity."
          value={actorId}
          onChange={setActorId}
          options={entities.users}
          status={entities.usersStatus}
          kind="user"
        />
        <Field label="Record type">
          <Input
            value={aggregateType}
            onChange={(e) => setAggregateType(e.target.value)}
            placeholder="e.g. batch, material_lot"
            style={{ maxWidth: 200 }}
          />
        </Field>
        <Field label="Site">
          <Select value={siteId} onChange={(e) => setSiteId(e.target.value)} style={{ maxWidth: 180 }}>
            <option value="">All sites</option>
            {sites.map((s: Site) => (
              <option key={s.id} value={s.id}>
                {s.code}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Signature">
          <Select value={hasSignature} onChange={(e) => setHasSignature(e.target.value)} style={{ maxWidth: 160 }}>
            {HAS_SIGNATURE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="From">
          <Input type="date" value={occurredFrom} onChange={(e) => setOccurredFrom(e.target.value)} />
        </Field>
        <Field label="To">
          <Input type="date" value={occurredTo} onChange={(e) => setOccurredTo(e.target.value)} />
        </Field>
        <Field
          label="Verify hash chain"
          hint={canVerifyChain ? "Confirms this record's events haven't been tampered with." : "Requires both Record ID and Record type."}
        >
          <label className="flex items-center gap-2 fs-2" style={{ height: "var(--input-height, 38px)" }}>
            <input
              type="checkbox"
              checked={verifyChain}
              disabled={!canVerifyChain}
              onChange={(e) => setVerifyChain(e.target.checked)}
            />
            Verify
          </label>
        </Field>
      </div>

      <Card>
        <CardHeader title="Events" />
        <DataTable
          key={`${aggregateType}|${aggregateId}|${actorId}|${siteId}|${hasSignature}|${occurredFrom}|${occurredTo}|${verifyChain}`}
          columns={columns}
          fetchPage={fetchEvents}
          rowKey={(e) => e.id}
          searchPlaceholder="Search by action or reason…"
          emptyIcon="history"
          emptyMessage="No audit events match these filters."
          defaultSort={{ by: "occurred_at", dir: "desc" }}
          onRowClick={setSelected}
        />
      </Card>

      {selected && <EventDetailModal event={selected} siteName={siteName} onClose={() => setSelected(null)} />}
    </div>
  );
}

function EventDetailModal({
  event,
  siteName,
  onClose,
}: {
  event: AuditEvent;
  siteName: (id: string | null) => string;
  onClose: () => void;
}) {
  const rows: [string, React.ReactNode][] = [
    ["Record", `${event.aggregate_type} / ${event.aggregate_id} (v${event.aggregate_version})`],
    ["Occurred at", new Date(event.occurred_at).toLocaleString()],
    ["Actor", `${event.actor_username ?? "—"} (${event.actor_type})`],
    ["Site", siteName(event.site_id)],
    ["Signature", event.signature_id ?? "Not signed"],
    ["Reason", event.reason ?? "—"],
    ["Correlation ID", event.correlation_id],
    ["Event hash", event.event_hash],
    ["Previous hash", event.prev_event_hash ?? "- (first event on this record)"],
  ];


  return (
    <Modal open onClose={onClose} title={`${event.aggregate_type} - ${event.action}`} large>
      <div className="mb-4">
        {rows.map(([label, value]) => (
          <div key={label} className="flex gap-3 fs-2" style={{ padding: "4px 0" }}>
            <span className="text-muted" style={{ minWidth: 130, flexShrink: 0 }}>
              {label}
            </span>
            <span className="tabular" style={{ wordBreak: "break-all" }}>
              {value}
            </span>
          </div>
        ))}
      </div>

      {event.changed_fields.length > 0 && (
        <>
          <p className="font-semibold fs-2 mb-2">Changed fields: {event.changed_fields.join(", ")}</p>
          <div className="grid grid-cols-2 gap-4 mb-3">
            <div>
              {event.old_value ? (
                <JsonPanel title="Old value" value={event.old_value} />
              ) : (
                <>
                  <p className="fact-k mb-2">Old value</p>
 <p className="text-muted fs-2">(none, this is the initial record)</p>
                </>
              )}
            </div>
            <div>
              {event.new_value ? (
                <JsonPanel title="New value" value={event.new_value} />
              ) : (
                <>
                  <p className="fact-k mb-2">New value</p>
                  <p className="text-muted fs-2">—</p>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </Modal>
  );
}
