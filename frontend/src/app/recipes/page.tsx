"use client";

import { pagedFetcher, type RecipeSummary } from "@/lib/api";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { LinkButton } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

const fetchRecipes = pagedFetcher<RecipeSummary>("/recipes");

const columns: DataTableColumn<RecipeSummary>[] = [
  {
    key: "product_code",
    header: "Product",
    sortable: true,
    render: (r) => (
      <span>
        <span className="font-semibold">{r.product_name}</span>{" "}
        <span className="text-muted tabular">({r.product_code})</span>
      </span>
    ),
  },
  { key: "version", header: "Version", sortable: true, render: (r) => <span className="tabular">v{r.version}</span> },
  { key: "status", header: "Status", sortable: true },
];

export default function RecipesPage() {
  return (
    <div>
      <PageHead
        title="Recipes"
        subtitle="Versioned manufacturing recipes — one row per version, nothing overwritten."
        action={
          <LinkButton href="/recipes/new" variant="primary">
            <Icon name="plus" /> New recipe
          </LinkButton>
        }
      />

      <Card>
        <CardHeader title="Recipes" />
        <DataTable
          columns={columns}
          fetchPage={fetchRecipes}
          rowKey={(r) => r.id}
          searchPlaceholder="Search by product code or name…"
          emptyIcon="database"
          emptyMessage="No recipes yet — create one to get started."
          defaultSort={{ by: "created_at", dir: "desc" }}
        />
      </Card>
    </div>
  );
}
