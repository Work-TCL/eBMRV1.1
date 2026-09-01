"use client";

import { useEffect, useState } from "react";
import { api, ApiError, canAuthorRecipe, newIdempotencyKey } from "@/lib/api";
import { useMe, useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

// Matches app/modules/recipe_master/router.py::_version_dict + graph dicts.
interface RecipeStep {
  id: string;
  stable_step_code: string;
  section_id: string;
  step_type: string;
  instruction_text: string | null;
  sequence_hint: number;
  is_critical: boolean;
}

interface RecipeSection {
  id: string;
  stable_section_code: string;
  name: string;
  sequence: number;
}

interface RecipeDependency {
  id: string;
  predecessor_step_id: string;
  successor_step_id: string;
  condition_rule_id: string | null;
}

interface RecipeVersion {
  recipe_version_id: string;
  recipe_family_id: string;
  version_no: number;
  product_version_id: string;
  lifecycle_state: string;
  released_vault_object_id: string | null;
  version_hash: string | null;
  version: number;
  sections?: RecipeSection[];
  steps?: RecipeStep[];
  dependencies?: RecipeDependency[];
}

const GRAPH_TEMPLATE = {
  sections: [{ stable_section_code: "SEC-1", name: "Dispensing", sequence: 1 }],
  steps: [
    { stable_step_code: "STEP-A", section_code: "SEC-1", step_type: "weigh", sequence_hint: 1 },
    { stable_step_code: "STEP-B", section_code: "SEC-1", step_type: "instruction", sequence_hint: 2 },
  ],
  dependencies: [{ predecessor_step_code: "STEP-A", successor_step_code: "STEP-B" }],
};

const textareaStyle: React.CSSProperties = { fontFamily: "var(--font-mono, monospace)", fontSize: "var(--fs-1)" };

export default function RecipeMasterPage() {
  const { me } = useMe();
  const [recipeFamilyId, setRecipeFamilyId] = useState("");
  const [versions, setVersions] = useState<RecipeVersion[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftOpen, setDraftOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  async function performLookup() {
    if (!recipeFamilyId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<RecipeVersion[]>(`/recipes/v2/${encodeURIComponent(recipeFamilyId.trim())}/versions`);
      setVersions(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Lookup failed");
      setVersions(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHead
        title="Recipe Master"
        subtitle="Document 10 — Master Recipe / Master Manufacturing Record. Author sections/steps/dependencies, validate the graph, and release."
        action={
          canAuthorRecipe(me) ? (
            <Button variant="primary" onClick={() => setDraftOpen(true)}>
              <Icon name="plus" /> New draft
            </Button>
          ) : undefined
        }
      />

      <p className="hint mb-4">
        This is the real Document 10 master — separate from the legacy <code>Recipes</code> page, which
        still feeds batch creation until the Batch/Recipe cutover (SG-044) happens.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          performLookup();
        }}
        className="flex items-end gap-4 mb-4"
      >
        <Field label="Recipe family ID" hint="Returned as recipe_family_id when you create a draft">
          <Input value={recipeFamilyId} onChange={(e) => setRecipeFamilyId(e.target.value)} style={{ minWidth: 300 }} />
        </Field>
        <Button type="submit" variant="secondary" disabled={loading || !recipeFamilyId.trim()}>
          <Icon name="search" /> {loading ? "Looking up…" : "Look up versions"}
        </Button>
      </form>

      {error && (
        <Card>
          <p className="error-text" style={{ padding: "var(--space-4, 16px)" }}>
            {error}
          </p>
        </Card>
      )}

      {versions && !error && (
        <Card>
          <CardHeader title={recipeFamilyId} />
          {versions.length === 0 ? (
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
                    <td>{v.lifecycle_state}</td>
                    <td style={{ textAlign: "right" }}>
                      <Button size="sm" variant="secondary" onClick={() => setSelectedId(v.recipe_version_id)}>
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

      {draftOpen && (
        <DraftModal
          onClose={() => setDraftOpen(false)}
          onDone={(familyId) => {
            setDraftOpen(false);
            setRecipeFamilyId(familyId);
            performLookup();
          }}
        />
      )}

      {selectedId && (
        <VersionDetailModal
          recipeVersionId={selectedId}
          allVersions={versions ?? []}
          onClose={() => setSelectedId(null)}
          onChanged={() => {
            setSelectedId(null);
            performLookup();
          }}
        />
      )}
    </div>
  );
}

function DraftModal({ onClose, onDone }: { onClose: () => void; onDone: (recipeFamilyId: string) => void }) {
  const { sites } = useSites();
  const [productBusinessId, setProductBusinessId] = useState("");
  const [recipeCode, setRecipeCode] = useState("");
  const [productVersionId, setProductVersionId] = useState("");
  const [versionNo, setVersionNo] = useState("1");
  const [siteId, setSiteId] = useState("");
  const [profile, setProfile] = useState("pharma");
  const [graphJson, setGraphJson] = useState(JSON.stringify(GRAPH_TEMPLATE, null, 2));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const graph = JSON.parse(graphJson);
      const receipt = await api.post<{ aggregate_id: string }>("/recipes/v2/drafts", {
        idempotency_key: newIdempotencyKey(),
        product_business_id: productBusinessId,
        recipe_code: recipeCode,
        version_no: Number(versionNo),
        product_version_id: productVersionId,
        site_id: siteId,
        manufacturing_profile_code: profile,
        sections: graph.sections ?? [],
        steps: graph.steps ?? [],
        dependencies: graph.dependencies ?? [],
      });
      const detail = await api.get<RecipeVersion>(`/recipes/v2/versions/${receipt.aggregate_id}`);
      onDone(detail.recipe_family_id);
    } catch (err) {
      if (err instanceof SyntaxError) setError("Invalid graph JSON: " + err.message);
      else setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to create draft");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="New recipe draft" large>
      <form onSubmit={onSubmit}>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Product business ID" required>
            <Input value={productBusinessId} onChange={(e) => setProductBusinessId(e.target.value)} required autoFocus />
          </Field>
          <Field label="Recipe code" required>
            <Input value={recipeCode} onChange={(e) => setRecipeCode(e.target.value)} required />
          </Field>
          <Field label="Version no." required>
            <Input type="number" min={1} value={versionNo} onChange={(e) => setVersionNo(e.target.value)} required />
          </Field>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Product version ID" required hint="From Product Master">
            <Input value={productVersionId} onChange={(e) => setProductVersionId(e.target.value)} required />
          </Field>
          <Field label="Site" required>
            <select className="input" value={siteId} onChange={(e) => setSiteId(e.target.value)} required>
              <option value="">Select a site…</option>
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Manufacturing profile" required>
            <Input value={profile} onChange={(e) => setProfile(e.target.value)} required />
          </Field>
        </div>
        <Field
          label="Sections / steps / dependencies (JSON)"
          required
          error={error}
          hint="A raw graph editor is the honest V1 scope here, not a visual builder (same approach as the Rules module's expression editor)."
        >
          <textarea
            className="input"
            rows={16}
            style={textareaStyle}
            value={graphJson}
            onChange={(e) => setGraphJson(e.target.value)}
            spellCheck={false}
          />
        </Field>
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !productBusinessId.trim() || !recipeCode.trim() || !siteId || !productVersionId.trim()}>
            {busy ? "Creating…" : "Create draft"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

interface RecipeDiff {
  sections: { added: string[]; removed: string[]; changed: { code: string; changes: Record<string, { from: string; to: string }> }[] };
  steps: { added: string[]; removed: string[]; changed: { code: string; changes: Record<string, { from: string; to: string }> }[] };
}

function VersionDetailModal({
  recipeVersionId,
  allVersions,
  onClose,
  onChanged,
}: {
  recipeVersionId: string;
  allVersions: RecipeVersion[];
  onClose: () => void;
  onChanged: () => void;
}) {
  const { me } = useMe();
  const [version, setVersion] = useState<RecipeVersion | null>(null);
  const [eligibility, setEligibility] = useState<{ eligible: boolean; checks: Record<string, unknown> } | null>(null);
  const [simResult, setSimResult] = useState<{ complete: boolean; findings: string[] } | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [compareTo, setCompareTo] = useState("");
  const [diff, setDiff] = useState<RecipeDiff | null>(null);
  const [diffError, setDiffError] = useState<string | null>(null);

  async function runCompare() {
    if (!compareTo) return;
    setDiffError(null);
    setDiff(null);
    try {
      setDiff(await api.get<RecipeDiff>(`/recipes/v2/versions/${recipeVersionId}/compare/${compareTo}`));
    } catch (err) {
      setDiffError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Compare failed");
    }
  }

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recipeVersionId]);

  async function refresh() {
    const [v, e] = await Promise.all([
      api.get<RecipeVersion>(`/recipes/v2/versions/${recipeVersionId}`),
      api.get<{ eligible: boolean; checks: Record<string, unknown> }>(`/recipes/v2/versions/${recipeVersionId}/issue-eligibility`),
    ]);
    setVersion(v);
    setEligibility(e);
  }

  async function runAction(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await refresh();
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  const simulate = async () => {
    setError(null);
    try {
      const result = await api.post<{ complete: boolean; findings: string[] }>(`/recipes/v2/drafts/${recipeVersionId}/simulate`);
      setSimResult(result);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Simulation failed");
    }
  };

  const validate = () =>
    runAction(() =>
      api.post(`/recipes/v2/drafts/${recipeVersionId}/validate`, {
        idempotency_key: newIdempotencyKey(),
        recipe_version_id: recipeVersionId,
      })
    );

  const submit = () =>
    runAction(() =>
      api.post(`/recipes/v2/drafts/${recipeVersionId}/submit`, {
        idempotency_key: newIdempotencyKey(),
        recipe_version_id: recipeVersionId,
        expected_version: version!.version,
      })
    );

  const release = () =>
    runAction(() =>
      api.post(`/recipes/v2/drafts/${recipeVersionId}/release`, {
        idempotency_key: newIdempotencyKey(),
        recipe_version_id: recipeVersionId,
        expected_version: version!.version,
      })
    );

  if (!version) {
    return (
      <Modal open onClose={onClose} title="Loading…">
        {error ? <p className="error-text">{error}</p> : <p>Loading…</p>}
      </Modal>
    );
  }

  return (
    <Modal open onClose={onClose} title={`${version.recipe_family_id.slice(0, 8)}… — v${version.version_no}`} large>
      <div className="mb-4">
        {(
          [
            ["Lifecycle state", version.lifecycle_state],
            ["Released vault object", version.released_vault_object_id ?? "—"],
            ["Version hash", version.version_hash ?? "—"],
          ] as [string, string][]
        ).map(([label, value]) => (
          <div key={label} className="flex gap-3 fs-2" style={{ padding: "4px 0" }}>
            <span className="text-muted" style={{ minWidth: 170, flexShrink: 0 }}>
              {label}
            </span>
            <span className="tabular" style={{ wordBreak: "break-all" }}>
              {value}
            </span>
          </div>
        ))}
      </div>

      <p className="fs-1 text-muted mb-1">Steps ({version.steps?.length ?? 0})</p>
      {!version.steps || version.steps.length === 0 ? (
        <p className="hint mb-3">No steps declared.</p>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Type</th>
              <th>Critical</th>
            </tr>
          </thead>
          <tbody>
            {version.steps.map((s) => (
              <tr key={s.id}>
                <td className="tabular">{s.stable_step_code}</td>
                <td>{s.step_type}</td>
                <td>{s.is_critical ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {(version.lifecycle_state === "draft" || version.lifecycle_state === "under_review") && (
        <div className="mt-4">
          <Button size="sm" variant="secondary" onClick={simulate}>
            Simulate
          </Button>
          {simResult && (
            <p className="fs-2 mt-2">
              {simResult.complete ? (
                "Graph is complete — ready to submit/release."
              ) : (
                <>
                  Findings:
                  <ul style={{ paddingLeft: "1.2em" }}>
                    {simResult.findings.map((f) => (
                      <li key={f}>{f}</li>
                    ))}
                  </ul>
                </>
              )}
            </p>
          )}
        </div>
      )}

      {eligibility && (
        <div className="mt-4">
          <p className="fs-1 text-muted mb-1">Issue eligibility</p>
          <p className={eligibility.eligible ? "fs-2" : "error-text fs-2"}>
            {eligibility.eligible ? "Eligible to issue" : "Not eligible"}
          </p>
        </div>
      )}

      <div className="mt-4">
        <p className="fs-1 text-muted mb-1">Compare with another version</p>
        <div className="flex items-end gap-3">
          <Select value={compareTo} onChange={(e) => setCompareTo(e.target.value)} style={{ minWidth: 220 }}>
            <option value="">— pick a version —</option>
            {allVersions
              .filter((v) => v.recipe_version_id !== recipeVersionId)
              .map((v) => (
                <option key={v.recipe_version_id} value={v.recipe_version_id}>
                  v{v.version_no} ({v.lifecycle_state})
                </option>
              ))}
          </Select>
          <Button size="sm" variant="secondary" onClick={runCompare} disabled={!compareTo}>
            Compare
          </Button>
        </div>
        {diffError && <p className="error-text fs-2 mt-2">{diffError}</p>}
        {diff && (
          <div className="mt-3">
            {(["sections", "steps"] as const).map((kind) => {
              const d = diff[kind];
              const empty = d.added.length === 0 && d.removed.length === 0 && d.changed.length === 0;
              return (
                <div key={kind} className="mb-3">
                  <p className="fs-2 font-semibold" style={{ textTransform: "capitalize" }}>
                    {kind}
                  </p>
                  {empty ? (
                    <p className="fs-2 text-muted">No differences.</p>
                  ) : (
                    <ul className="fs-2" style={{ paddingLeft: "1.2em" }}>
                      {d.added.map((c) => (
                        <li key={`a-${c}`}>
                          <span className="tabular">{c}</span> — added
                        </li>
                      ))}
                      {d.removed.map((c) => (
                        <li key={`r-${c}`}>
                          <span className="tabular">{c}</span> — removed
                        </li>
                      ))}
                      {d.changed.map((c) => (
                        <li key={`c-${c.code}`}>
                          <span className="tabular">{c.code}</span> —{" "}
                          {Object.entries(c.changes)
                            .map(([f, { from, to }]) => `${f}: ${from} → ${to}`)
                            .join("; ")}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {error && <p className="error-text mt-3">{error}</p>}

      <div className="flex justify-between gap-3 mt-4">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        <div className="flex gap-2">
          {canAuthorRecipe(me) && version.lifecycle_state === "draft" && (
            <>
              <Button variant="secondary" onClick={validate} disabled={busy}>
                Validate
              </Button>
              <Button variant="primary" onClick={submit} disabled={busy}>
                Submit for review
              </Button>
            </>
          )}
          {canAuthorRecipe(me) && version.lifecycle_state === "under_review" && (
            <Button variant="success" onClick={release} disabled={busy}>
              {busy ? "Releasing…" : "Release"}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
