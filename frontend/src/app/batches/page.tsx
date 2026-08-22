"use client";

import { useRouter } from "next/navigation";
import { pagedFetcher, type BatchSummary } from "@/lib/api";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { LinkButton } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { BatchStatePill } from "@/components/ui/StatePill";

const fetchBatches = pagedFetcher<BatchSummary>("/batches");

const columns: DataTableColumn<BatchSummary>[] = [
  {
    key: "batch_number",
    header: "Batch #",
    sortable: true,
    render: (b) => (
      <span className="font-semibold tabular" style={{ color: "var(--brand-600)" }}>
        {b.batch_number}
      </span>
    ),
  },
  {
    key: "product_code",
    header: "Product",
    sortable: true,
    render: (b) => (
      <span>
        {b.product_name} <span className="text-muted tabular">({b.product_code})</span>
      </span>
    ),
  },
  {
    key: "target_quantity",
    header: "Quantity",
    sortable: true,
    align: "right",
    render: (b) => (
      <span className="tabular">
        {b.target_quantity} {b.uom}
      </span>
    ),
  },
  { key: "status", header: "Status", sortable: true, render: (b) => <BatchStatePill status={b.status} /> },
];

export default function BatchesPage() {
  const router = useRouter();

  return (
    <div>
      <PageHead
        title="Batches"
        subtitle="Every batch record this site has issued, in progress, or released."
        action={
          <LinkButton href="/batches/new" variant="primary">
            <Icon name="plus" /> New batch
          </LinkButton>
        }
      />

      <Card>
        <CardHeader title="Batches" />
        <DataTable
          columns={columns}
          fetchPage={fetchBatches}
          rowKey={(b) => b.id}
          searchPlaceholder="Search by batch number or product…"
          emptyIcon="flask"
          emptyMessage="No batches yet — create one to get started."
          defaultSort={{ by: "created_at", dir: "desc" }}
          onRowClick={(b) => router.push(`/batches/${b.id}`)}
        />
      </Card>
    </div>
  );
}
