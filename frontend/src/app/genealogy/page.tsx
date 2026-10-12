"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useRequirePermission, useSiteId, type EntityOption, type EntityOptionsStatus } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field, RowButtonSlot } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { Tabs } from "@/components/ui/Tabs";
import { StatePill } from "@/components/ui/StatePill";
import { EntityPickerField } from "@/components/shared/EntityPicker";

interface Node {
  node_id: string;
  site_id: string;
  node_type: string;
  business_ref: string;
  authoritative_record_type: string;
  authoritative_record_id: string | null;
  authoritative_record_label: string | null;
  authoritative_version: number | null;
  record_hash: string | null;
}

interface Edge {
  id: string;
  from_node_id: string;
  to_node_id: string;
  edge_type: string;
  quantity: string | null;
  uom: string | null;
  state: string;
  supersedes_edge_id: string | null;
  created_at: string;
}

interface Trace {
  root_node_id: string;
  nodes: Node[];
  edge_ids: string[];
  edges: Edge[];
  truncated: boolean;
}

type Mode = "lookup" | "serial" | "material_lot";

// Must mirror `genealogy/models.py::NODE_TYPES` exactly (Document 13 §2) -- the prior list ("batch",
// "shipment") named node types that don't actually exist in the backend's enum, so picking either
// silently returned zero rows even when matching data existed under the real type name (e.g. a real
// node with node_type "drug_batch" never matched a "batch" filter). Confirmed live 2026-10-08.
const NODE_TYPES = [
  "",
  "supplier_lot",
  "material_lot",
  "material_container",
  "drug_batch",
  "intermediate",
  "fill_group",
  "device_component_lot",
  "device_component_serial",
  "device_unit",
  "combination_product_lot",
  "combination_product_serial",
  "package",
  "carton",
  "pallet",
  "distribution_reference",
  "evidence_record",
  "constituent_compatibility_version",
];

/** "Full trace by serial" and "Affected products by lot" both take a real reference value, not free
 * text — `genealogy_service.full_trace()`/`affected_products()` (services/gxp-api/app/modules/
 * genealogy/service.py) both look up `GenealogyNode.business_ref` for this exact `site_id`, the same
 * column "Find nodes" already browses via `GET /genealogy/v1/nodes/lookup`. Confirmed 2026-10-09 (real
 * user question) by reading both service functions side by side with the lookup endpoint. Shared
 * between both modes (unfiltered by node_type — a "serial" and a "lot" are both just a business_ref on
 * this one table, and the backend itself doesn't distinguish them at lookup time), valued by the
 * business_ref string itself (the URL path segment these two endpoints take), not the node's database
 * id -- same "value is the human code, not the id" shape as `materialLotCodes` in lib/hooks.ts. */
function useGenealogyNodeRefs(siteId: string | null): { options: EntityOption[]; status: EntityOptionsStatus } {
  const [options, setOptions] = useState<EntityOption[]>([]);
  const [status, setStatus] = useState<EntityOptionsStatus>("loading");

  useEffect(() => {
    if (!siteId) return;
    let cancelled = false;
    api
      .get<Node[]>(`/genealogy/v1/nodes/lookup?site_id=${siteId}`)
      .then((rows) => {
        if (cancelled) return;
        setOptions(rows.map((n) => ({ value: n.business_ref, label: `${n.business_ref} (${n.node_type})` })));
        setStatus(rows.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [siteId]);

  return { options, status };
}

export default function GenealogyPage() {
  useRequirePermission("genealogy.view");
  const { siteId } = useSiteId();
  const nodeRefs = useGenealogyNodeRefs(siteId);
  const [mode, setMode] = useState<Mode>("lookup");
  const [nodeType, setNodeType] = useState("");
  const [businessRef, setBusinessRef] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [nodes, setNodes] = useState<Node[] | null>(null);
  const [selected, setSelected] = useState<Node | null>(null);
  const [ancestors, setAncestors] = useState<Trace | null>(null);
  const [descendants, setDescendants] = useState<Trace | null>(null);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;
    setLoading(true);
    setError(null);
    setNodes(null);
    setSelected(null);
    setAncestors(null);
    setDescendants(null);
    const ref = encodeURIComponent(businessRef.trim());
    try {
      if (mode === "lookup") {
        const params = new URLSearchParams({ site_id: siteId });
        if (nodeType) params.set("node_type", nodeType);
        if (businessRef.trim()) params.set("business_ref", businessRef.trim());
        setNodes(await api.get<Node[]>(`/genealogy/v1/nodes/lookup?${params}`));
      } else if (mode === "serial") {
        const result = await api.get<{ root: Node; ancestors: Trace; descendants: Trace }>(
          `/genealogy/v1/serial/${ref}/full-trace?site_id=${siteId}`
        );
        setSelected(result.root);
        setAncestors(result.ancestors);
        setDescendants(result.descendants);
      } else {
        const result = await api.get<{ root: Node; descendants?: Trace; affected?: Trace }>(
          `/genealogy/v1/material-lot/${ref}/affected-products?site_id=${siteId}`
        );
        setSelected(result.root);
        setDescendants(result.descendants ?? result.affected ?? null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
    } finally {
      setLoading(false);
    }
  }

  async function openNode(node: Node) {
    setSelected(node);
    setLoading(true);
    setError(null);
    try {
      const [a, d] = await Promise.all([
        api.get<Trace>(`/genealogy/v1/nodes/${node.node_id}/ancestors`),
        api.get<Trace>(`/genealogy/v1/nodes/${node.node_id}/descendants`),
      ]);
      setAncestors(a);
      setDescendants(d);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Could not load the trace");
    } finally {
      setLoading(false);
    }
  }

  const MODE_LABEL: Record<Mode, string> = {
    lookup: "Find nodes",
    serial: "Full trace by serial",
    material_lot: "Affected products by lot",
  };

  return (
    <div>
      <PageHead
        title="Genealogy"
        subtitle="Forward and backward traceability across batches, material lots, device units and packages."
      />

      {/* items-start, not items-end: the Query field's hint (shown when mode === "lookup") sits below
         its select, which items-end would bottom-align the row to instead of the select/input itself —
         dragging the button down below where it visually belongs. RowButtonSlot gives the button a
         same-height invisible label so it lines up with the real inputs regardless of hint presence. */}
      <form onSubmit={run} className="flex items-start gap-4 mb-4 flex-wrap">
        <Field label="Query">
          <Select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
            {(Object.keys(MODE_LABEL) as Mode[]).map((m) => (
              <option key={m} value={m}>
                {MODE_LABEL[m]}
              </option>
            ))}
          </Select>
        </Field>
        {mode === "lookup" && (
          <Field label="Node type">
            <Select value={nodeType} onChange={(e) => setNodeType(e.target.value)}>
              {NODE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t || "Any"}
                </option>
              ))}
            </Select>
          </Field>
        )}
        {mode === "lookup" ? (
          <Field label="Business reference" hint="Leave blank to list every node of the chosen type.">
            <Input value={businessRef} onChange={(e) => setBusinessRef(e.target.value)} style={{ minWidth: 300 }} />
          </Field>
        ) : (
          <EntityPickerField
            label={mode === "serial" ? "Serial" : "Material lot"}
            required
            value={businessRef}
            onChange={setBusinessRef}
            options={nodeRefs.options}
            status={nodeRefs.status}
            kind={mode === "serial" ? "serial" : "lot"}
            placeholder={mode === "serial" ? "Serial / business reference" : "Lot business reference"}
          />
        )}
        <RowButtonSlot>
          <Button
            type="submit"
            variant="secondary"
            disabled={loading || !siteId || (mode !== "lookup" && !businessRef.trim())}
          >
            <Icon name="search" /> {loading ? "Searching…" : "Search"}
          </Button>
        </RowButtonSlot>
      </form>

      {error && (
        <Banner tone="critical" title="Query failed">
          {error}
        </Banner>
      )}

      {nodes && (
        <Card className="mb-4">
          <CardHeader title="Matching nodes" meta={`${nodes.length} node(s)`} />
          {nodes.length === 0 ? (
            <EmptyState icon="layers">No genealogy nodes match this query.</EmptyState>
          ) : (
            <Table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Business reference</th>
                  <th>Authoritative record</th>
                  <th>Version</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {nodes.map((n) => (
                  <tr key={n.node_id}>
                    <td>
                      <StatePill state="unknown" icon="layers">
                        {n.node_type}
                      </StatePill>
                    </td>
                    <td className="font-semibold tabular">{n.business_ref}</td>
                    <td className="fs-2">{n.authoritative_record_type}</td>
                    <td className="tabular fs-2">{n.authoritative_version ?? "—"}</td>
                    <td style={{ textAlign: "right" }}>
                      <Button size="sm" variant="secondary" onClick={() => openNode(n)}>
                        Trace
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}

      {selected && (
        <>
          <Card pad className="mb-4">
            <div className="flex justify-between items-center mb-3">
              <span className="font-semibold">
                {selected.business_ref}{" "}
                <StatePill state="unknown" icon="layers">
                  {selected.node_type}
                </StatePill>
              </span>
            </div>
            <FactGrid>
              <Fact label="Node type">{selected.node_type}</Fact>
              <Fact label="Authoritative record">{selected.authoritative_record_type}</Fact>
              <Fact label="Version">{selected.authoritative_version ?? "—"}</Fact>
              <IdFact label="Node ID" value={selected.node_id} />
              <IdFact label="Record ID" value={selected.authoritative_record_label ?? selected.authoritative_record_id} />
              <IdFact label="Record hash" value={selected.record_hash} />
            </FactGrid>
          </Card>

          <Tabs
            tabs={[
              {
                id: "ancestors",
                label: "Ancestors (what went into it)",
                badge: ancestors?.nodes.length,
                content: <TraceTable trace={ancestors} onOpen={openNode} emptyText="No ancestor nodes." />,
              },
              {
                id: "descendants",
                label: "Descendants (what it became)",
                badge: descendants?.nodes.length,
                content: <TraceTable trace={descendants} onOpen={openNode} emptyText="No descendant nodes." />,
              },
            ]}
          />
        </>
      )}
    </div>
  );
}

function TraceTable({
  trace,
  onOpen,
  emptyText,
}: {
  trace: Trace | null;
  onOpen: (node: Node) => void;
  emptyText: string;
}) {
  if (!trace) return <EmptyState icon="layers">Not loaded.</EmptyState>;
  const labelByNodeId = new Map(trace.nodes.map((n) => [n.node_id, `${n.business_ref} (${n.node_type})`]));
  return (
    <>
      <Card>
        <CardHeader title={`${trace.nodes.length} node(s)`} meta={`${trace.edge_ids.length} edge(s)`} />
        {trace.truncated && (
          <Banner tone="warn" title="Trace truncated">
            The graph exceeded the traversal limit, so this is a partial view - not the complete genealogy.
          </Banner>
        )}
        {trace.nodes.length === 0 ? (
          <EmptyState icon="layers">{emptyText}</EmptyState>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Business reference</th>
                <th>Authoritative record</th>
                <th>Version</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {trace.nodes.map((n) => (
                <tr key={n.node_id}>
                  <td>
                    <StatePill state="unknown" icon="layers">
                      {n.node_type}
                    </StatePill>
                  </td>
                  <td className="font-semibold tabular">{n.business_ref}</td>
                  <td className="fs-2">{n.authoritative_record_type}</td>
                  <td className="tabular fs-2">{n.authoritative_version ?? "—"}</td>
                  <td style={{ textAlign: "right" }}>
                    <Button size="sm" variant="ghost" onClick={() => onOpen(n)}>
                      Trace from here
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {trace.edges.length > 0 && (
        <Card className="mt-3">
          <CardHeader title="Edges (the connections)" meta={`${trace.edges.length} edge(s)`} />
          <Table>
            <thead>
              <tr>
                <th>Edge type</th>
                <th>From</th>
                <th>To</th>
                <th>Quantity</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {trace.edges.map((e) => (
                <tr key={e.id}>
                  <td className="fs-2">{e.edge_type}</td>
                  <td className="fs-2">{labelByNodeId.get(e.from_node_id) ?? e.from_node_id}</td>
                  <td className="fs-2">{labelByNodeId.get(e.to_node_id) ?? e.to_node_id}</td>
                  <td className="tabular fs-2">{e.quantity ? `${e.quantity} ${e.uom ?? ""}` : "—"}</td>
                  <td>
                    <StatePill
                      state={e.state === "ACTIVE" ? "accepted" : e.state === "VOIDED" ? "blocked" : "stale"}
                      icon={e.state === "ACTIVE" ? "check-circle" : e.state === "VOIDED" ? "x" : "clock"}
                    >
                      {e.state}
                    </StatePill>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      )}
    </>
  );
}
