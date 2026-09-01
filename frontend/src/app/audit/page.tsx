"use client";

import { useState } from "react";
import { api, type ListQuery, type Paged, type Site } from "@/lib/api";
import { useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";

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
}

const HAS_SIGNATURE_OPTIONS = [
  { value: "", label: "Any" },
  { value: "true", label: "Signed only" },
  { value: "false", label: "Unsigned only" },
];

export default function AuditLedgerPage() {
  const { sites } = useSites();
  const [aggregateType, setAggregateType] = useState("");
  const [aggregateId, setAggregateId] = useState("");
  const [actorId, setActorId] = useState("");
  const [siteId, setSiteId] = useState("");
  const [hasSignature, setHasSignature] = useState("");
  const [occurredFrom, setOccurredFrom] = useState("");
  const [occurredTo, setOccurredTo] = useState("");
  const [selected, setSelected] = useState<AuditEvent | null>(null);

  function fetchEvents(query: ListQuery): Promise<Paged<AuditEvent>> {
    const search = new URLSearchParams({
      page: String(query.page),
      page_size: String(query.page_size),
      sort_dir: query.sort_dir,
    });
    if (query.q) search.set("q", query.q);
    search.set("sort_by", query.sort_by ?? "occurred_at");
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
  ];

  return (
    <div>
      <PageHead
        title="Audit ledger"
        subtitle="Search and review every regulated audit event — append-only, hash-chained, never editable."
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
        <Field label="Actor ID" hint="One user's activity.">
          <Input
            value={actorId}
            onChange={(e) => setActorId(e.target.value)}
            placeholder="subject UUID"
            style={{ maxWidth: 210 }}
          />
        </Field>
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
      </div>

      <Card>
        <CardHeader title="Events" />
        <DataTable
          key={`${aggregateType}|${aggregateId}|${actorId}|${siteId}|${hasSignature}|${occurredFrom}|${occurredTo}`}
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
    ["Previous hash", event.prev_event_hash ?? "— (first event on this record)"],
  ];

  const preStyle: React.CSSProperties = {
    background: "var(--surface-sunken)",
    border: "1px solid var(--border-hairline)",
    borderRadius: "var(--radius-2, 6px)",
    padding: "var(--space-2, 8px)",
    fontSize: "var(--fs-1)",
    overflowX: "auto",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  };

  return (
    <Modal open onClose={onClose} title={`${event.aggregate_type} — ${event.action}`} large>
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
              <p className="fs-1 text-muted mb-1">Old value</p>
              <pre style={preStyle}>{JSON.stringify(event.old_value, null, 2)}</pre>
            </div>
            <div>
              <p className="fs-1 text-muted mb-1">New value</p>
              <pre style={preStyle}>{JSON.stringify(event.new_value, null, 2)}</pre>
            </div>
          </div>
        </>
      )}
    </Modal>
  );
}
