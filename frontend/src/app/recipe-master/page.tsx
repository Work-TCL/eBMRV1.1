"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, canAuthorRecipe, clientPagedFetcher } from "@/lib/api";
import { useRequirePermission, useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button, LinkButton } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { type RecipeFamilyRow, type RecipeVersion } from "./shared";

export default function RecipeMasterPage() {
  const { me } = useRequirePermission("recipe.view");
  const { sites } = useSites();
  const router = useRouter();

  // "Versions" on a row reveals every version for that recipe family below the list — the released v1
  // alongside an in-progress draft v2, for example.
  const [openFamily, setOpenFamily] = useState<RecipeFamilyRow | null>(null);
  const [versions, setVersions] = useState<RecipeVersion[] | null>(null);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [versionsError, setVersionsError] = useState<string | null>(null);

  async function showVersions(family: RecipeFamilyRow) {
    setOpenFamily(family);
    setVersionsLoading(true);
    setVersionsError(null);
    try {
      setVersions(
        await api.get<RecipeVersion[]>(`/recipes/v2/${encodeURIComponent(family.recipe_family_id)}/versions`)
      );
    } catch (err) {
      setVersionsError(err instanceof ApiError ? err.message : "Lookup failed");
      setVersions(null);
    } finally {
      setVersionsLoading(false);
    }
  }

  // Deep link from /recipe-master/new after a successful create (`?openFamily=<id>`) — jump straight
  // to the new family's versions, same as the old DraftModal's onDone callback used to do inline. Also
  // handles the workflow-notifications bell's `?recipe_version_id=<id>` — jump straight to the version
  // detail (its own Release button lives there). Reads window.location directly rather than
  // next/navigation's useSearchParams(), which needs a Suspense boundary for static rendering this page
  // has no other reason to opt into.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const familyId = params.get("openFamily");
    const versionId = params.get("recipe_version_id");
    if (versionId) {
      router.replace(`/recipe-master/${versionId}`);
      return;
    }
    if (!familyId) return;
    let cancelled = false;
    api
      .get<RecipeFamilyRow[]>("/recipes/v2/families")
      .then((fresh) => {
        if (cancelled) return;
        const row = fresh.find((f) => f.recipe_family_id === familyId);
        if (row) showVersions(row);
      })
      .catch(() => {
        /* the families table still shows the new draft either way */
      });
    router.replace("/recipe-master");
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const siteName = (id: string) => sites.find((s) => s.id === id)?.name ?? id;

  // GET /recipes/v2/families returns a plain array, not the server-side Paged<T> envelope (Phase 1,
  // small row counts — same ceiling `listAll`/`clientPagedFetcher` document) — DataTable's
  // search/sort/paging is done client-side over that array here.
  const fetchFamilies = clientPagedFetcher<RecipeFamilyRow>(
    () => api.get<RecipeFamilyRow[]>("/recipes/v2/families"),
    { searchText: (f) => `${f.recipe_code} ${f.product_business_id}` }
  );

  const familyColumns: DataTableColumn<RecipeFamilyRow>[] = [
    {
      key: "recipe_code",
      header: "Recipe code",
      sortable: true,
      render: (f) => <span className="font-semibold tabular">{f.recipe_code}</span>,
    },
    {
      key: "product_business_id",
      header: "Product business ID",
      sortable: true,
      render: (f) => <span className="tabular fs-2">{f.product_business_id}</span>,
    },
    { key: "site_id", header: "Site", render: (f) => <span className="fs-2">{siteName(f.site_id)}</span> },
    { key: "manufacturing_profile_code", header: "Profile", render: (f) => <span className="fs-2">{f.manufacturing_profile_code}</span> },
    {
      key: "version_count",
      header: "Versions",
      sortable: true,
      render: (f) => <span className="tabular fs-2">{f.version_count}</span>,
    },
    {
      key: "latest_version_no",
      header: "Latest",
      render: (f) =>
        f.latest_version_no == null ? (
          <span className="text-muted fs-2">—</span>
        ) : (
          <span className="flex items-center gap-2">
            <span className="tabular fs-2">v{f.latest_version_no}</span>
            {f.latest_lifecycle_state && <WorkflowStatePill state={f.latest_lifecycle_state} />}
          </span>
        ),
    },
    {
      key: "actions",
      header: "",
      render: (f) => (
        <div className="flex gap-2 justify-end">
          <Button size="sm" variant="ghost" onClick={() => showVersions(f)}>
            Versions
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              if (f.latest_recipe_version_id) router.push(`/recipe-master/${f.latest_recipe_version_id}`);
            }}
            disabled={!f.latest_recipe_version_id}
          >
            Open latest
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHead
        title="Recipe Master"
        subtitle="Master Recipe / Master Manufacturing Record. Author sections, steps and dependencies in one block, validate the graph, and release."
        action={
          canAuthorRecipe(me) ? (
            <LinkButton href="/recipe-master/new" variant="primary">
              <Icon name="plus" /> New draft
            </LinkButton>
          ) : undefined
        }
      />

      <Card className="mb-4">
        <CardHeader title="Recipes" meta="One row per recipe family, its latest version - click Versions for the full history." />
        <DataTable
          columns={familyColumns}
          fetchPage={fetchFamilies}
          rowKey={(f) => f.recipe_family_id}
          searchPlaceholder="Search by recipe code or product…"
          emptyIcon="database"
          emptyMessage={<>No recipes drafted yet - use &quot;New draft&quot; above to create one.</>}
          defaultSort={{ by: "recipe_code", dir: "asc" }}
        />
      </Card>

      {openFamily && (
        <Card>
          <CardHeader
            title={`Versions - ${openFamily.recipe_code}`}
            meta={
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setOpenFamily(null);
                  setVersions(null);
                }}
              >
                Close
              </Button>
            }
          />
          {versionsLoading ? (
            <p className="hint" style={{ padding: "var(--space-4, 16px)" }}>
              Loading…
            </p>
          ) : versionsError ? (
            <p className="error-text" style={{ padding: "var(--space-4, 16px)" }}>
              {versionsError}
            </p>
          ) : !versions || versions.length === 0 ? (
            <EmptyState icon="database">No versions exist for this recipe family yet.</EmptyState>
          ) : (
            <Table>
              <thead>
                <tr>
                  <th>Version</th>
                  <th>State</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {versions.map((v) => (
                  <tr key={v.recipe_version_id}>
                    <td className="font-semibold tabular">{v.version_no}</td>
                    <td>
                      <WorkflowStatePill state={v.lifecycle_state} />
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <Button size="sm" variant="secondary" onClick={() => router.push(`/recipe-master/${v.recipe_version_id}`)}>
                        Open
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}

    </div>
  );
}
