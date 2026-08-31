"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, newIdempotencyKey, pagedFetcher, type MutationReceipt, type RecipeSummary } from "@/lib/api";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button, LinkButton } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Icon } from "@/components/ui/Icon";

const fetchRecipes = pagedFetcher<RecipeSummary>("/recipes");

export default function RecipesPage() {
  const router = useRouter();
  const [reloadToken, setReloadToken] = useState(0);
  const [deleting, setDeleting] = useState<RecipeSummary | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  async function onConfirmDelete() {
    if (!deleting) return;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await api.del<MutationReceipt>(`/recipes/${deleting.id}`, {
        idempotency_key: newIdempotencyKey(),
        recipe_id: deleting.id,
      });
      setDeleting(null);
      setReloadToken((n) => n + 1);
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Failed to delete recipe");
    } finally {
      setDeleteBusy(false);
    }
  }

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
    {
      key: "actions",
      header: "",
      render: (r) => (
        <div className="flex gap-2 justify-end">
          <Button size="sm" variant="secondary" onClick={() => router.push(`/recipes/${r.id}/edit`)}>
            Edit
          </Button>
          <Button size="sm" variant="danger" onClick={() => setDeleting(r)}>
            Delete
          </Button>
        </div>
      ),
    },
  ];

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
          reloadToken={reloadToken}
        />
      </Card>

      <ConfirmDialog
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        title="Delete recipe?"
        message={
          deleting ? (
            <>
              Delete <strong>{deleting.product_name}</strong> v{deleting.version}? This cannot be undone.
              Blocked once any batch has used it — create a new version instead.
            </>
          ) : (
            ""
          )
        }
        onConfirm={onConfirmDelete}
        busy={deleteBusy}
        error={deleteError}
      />
    </div>
  );
}
