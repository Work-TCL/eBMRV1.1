"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { Fact, FactGrid, IdFact } from "@/components/ui/FactGrid";
import { Tabs } from "@/components/ui/Tabs";
import { StatePill } from "@/components/ui/StatePill";

interface Node {
  node_id: string;
  site_id: string;
  node_type: string;
  business_ref: string;
  authoritative_record_type: string;
  authoritative_record_id: string | null;
  authoritative_version: number | null;
  record_hash: string | null;
}

interface Trace {
  root_node_id: string;
  nodes: Node[];
  edge_ids: string[];
  truncated: boolean;
}

type Mode = "lookup" | "serial" | "material_lot";

const NODE_TYPES = ["", "batch", "material_lot", "device_unit", "package", "shipment"];

export default function GenealogyPage() {
  const { siteId } = useSiteId();
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
        subtitle="Document 13 — forward and backward traceability across batches, material lots, device units and packages."
      />

      <form onSubmit={run} className="flex items-end gap-4 mb-4 flex-wrap">
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
        <Field
          label={mode === "serial" ? "Serial" : mode === "material_lot" ? "Material lot" : "Business reference"}
          hint={mode === "lookup" ? "Leave blank to list every node of the chosen type." : undefined}
        >
          <Input value={businessRef} onChange={(e) => setBusinessRef(e.target.value)} style={{ minWidth: 300 }} />
        </Field>
        <Button
          type="submit"
          variant="secondary"
          disabled={loading || !siteId || (mode !== "lookup" && !businessRef.trim())}
        >
          <Icon name="search" /> {loading ? "Searching…" : "Search"}
        </Button>
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
              <IdFact label="Record ID" value={selected.authoritative_record_id} />
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
  return (
    <Card>
      <CardHeader title={`${trace.nodes.length} node(s)`} meta={`${trace.edge_ids.length} edge(s)`} />
      {trace.truncated && (
        <Banner tone="warn" title="Trace truncated">
          The graph exceeded the traversal limit, so this is a partial view — not the complete genealogy.
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
  );
}
