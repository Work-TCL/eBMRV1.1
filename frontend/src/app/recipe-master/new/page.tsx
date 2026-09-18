"use client";

import { useState } from "react";
import type React from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, newIdempotencyKey } from "@/lib/api";
import { useApiResource, useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import { Button, LinkButton } from "@/components/ui/Button";
import {
  type ProductBusinessIdOption,
  type ProductVersionOption,
  type RecipeVersion,
  type SectionDraft,
  MANUFACTURING_PROFILES,
  RecipeGraphEditor,
  buildGraphPayload,
  totalStepCount,
  useRoleAndRuleOptions,
} from "../shared";

/** Full-page "New recipe draft" (moved off the old `DraftModal` popup 2026-09-16, project-owner-directed
 * — the Sections/Steps/Dependencies graph editor plus its 4 per-step sub-editors (§9.3.1-9.3.4) is too
 * much content for a modal to stay usable). Same fields, same `POST /recipes/v2/drafts` call, same
 * validation as the modal it replaces — only the container changed. On success, redirects to
 * `/recipe-master` where the new family/version shows up in the list. */
export default function NewRecipeDraftPage() {
  const router = useRouter();
  const { sites } = useSites();
  const [productBusinessId, setProductBusinessId] = useState("");
  const [recipeCode, setRecipeCode] = useState("");
  const [productVersionId, setProductVersionId] = useState("");
  const [versionNo, setVersionNo] = useState("1");
  const [siteId, setSiteId] = useState("");
  const [profile, setProfile] = useState("pharma");
  const [batchSizeValue, setBatchSizeValue] = useState("");
  const [batchSizeUom, setBatchSizeUom] = useState("");
  const [sections, setSections] = useState<SectionDraft[]>([]);
  const { roleOptions, ruleOptions, materialSpecOptions, qualificationCodeOptions, uomOptions, equipmentClassOptions } = useRoleAndRuleOptions();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Product Master pickers — real dropdowns (Process Engineer holds product.view).
  const { data: businessIdOptions } = useApiResource<ProductBusinessIdOption[]>("/products/v1/business-ids");
  const [productVersions, setProductVersions] = useState<ProductVersionOption[]>([]);
  const [pvError, setPvError] = useState<string | null>(null);
  const pickedVersion = productVersions.find((v) => v.product_version_id === productVersionId);

  async function onPickBusinessId(bid: string) {
    setProductBusinessId(bid);
    setProductVersionId("");
    setProductVersions([]);
    setPvError(null);
    if (!bid) return;
    try {
      const rows = await api.get<ProductVersionOption[]>(`/products/v1/${encodeURIComponent(bid)}/versions`);
      // Released versions first, then newest — a recipe should normally target a released product version.
      rows.sort(
        (a, b) =>
          (a.lifecycle_state === "released" ? 0 : 1) - (b.lifecycle_state === "released" ? 0 : 1) || b.version_no - a.version_no
      );
      setProductVersions(rows);
    } catch (err) {
      setPvError(err instanceof ApiError ? err.message : "Could not load versions for this Business ID");
    }
  }

  function onPickVersion(pvId: string) {
    setProductVersionId(pvId);
    const pv = productVersions.find((v) => v.product_version_id === pvId);
    if (pv) {
      if (pv.site_id) setSiteId(pv.site_id);
      if (pv.manufacturing_profile_code) setProfile(pv.manufacturing_profile_code);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const graph = buildGraphPayload(sections);
      const receipt = await api.post<{ aggregate_id: string }>("/recipes/v2/drafts", {
        idempotency_key: newIdempotencyKey(),
        product_business_id: productBusinessId,
        recipe_code: recipeCode,
        version_no: Number(versionNo),
        product_version_id: productVersionId,
        site_id: siteId,
        manufacturing_profile_code: profile,
        ...(batchSizeValue ? { batch_size_value: batchSizeValue } : {}),
        ...(batchSizeUom ? { batch_size_uom: batchSizeUom } : {}),
        ...graph,
      });
      const detail = await api.get<RecipeVersion>(`/recipes/v2/versions/${receipt.aggregate_id}`);
      router.push(`/recipe-master?openFamily=${encodeURIComponent(detail.recipe_family_id)}`);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to create draft");
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHead
        title="New recipe draft"
        subtitle="Master Recipe / Master Manufacturing Record. Author sections, steps and dependencies, then validate and release from the version detail screen."
        action={<LinkButton href="/recipe-master">Cancel</LinkButton>}
      />

      <Card className="p-4">
        <form onSubmit={onSubmit}>
          <div className="grid grid-cols-3 gap-4">
            <Field label="Product" required hint="From Product Master">
              <Select value={productBusinessId} onChange={(e) => onPickBusinessId(e.target.value)} required autoFocus>
                <option value="">Select a product…</option>
                {(businessIdOptions ?? []).map((o) => (
                  <option key={o.product_business_id} value={o.product_business_id}>
                    {o.product_business_id} - {o.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Recipe code" required>
              <Input value={recipeCode} onChange={(e) => setRecipeCode(e.target.value)} required />
            </Field>
            <Field label="Version no." required>
              <Input type="number" min={1} value={versionNo} onChange={(e) => setVersionNo(e.target.value)} required />
            </Field>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Field
              label="Product version"
              required
              hint={
                !productBusinessId
                  ? "Pick a product first"
                  : pickedVersion && pickedVersion.lifecycle_state !== "released"
                    ? "⚠ not released - a batch can only be created from a released product version"
                    : "The released product spec this recipe is authored against"
              }
            >
              <Select value={productVersionId} onChange={(e) => onPickVersion(e.target.value)} required disabled={!productBusinessId}>
                <option value="">{productBusinessId ? "Select a version…" : "—"}</option>
                {productVersions.map((v) => (
                  <option key={v.product_version_id} value={v.product_version_id}>
                    v{v.version_no} - {v.name} ({v.lifecycle_state})
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Site" required>
              <Select value={siteId} onChange={(e) => setSiteId(e.target.value)} required>
                <option value="">Select a site…</option>
                {sites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Manufacturing profile" required hint="Defaults to the product version's profile">
              <Select value={profile} onChange={(e) => setProfile(e.target.value)} required>
                {MANUFACTURING_PROFILES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
                {profile && !MANUFACTURING_PROFILES.includes(profile) && <option value={profile}>{profile}</option>}
              </Select>
            </Field>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Field label="Batch size (optional)">
              <Input value={batchSizeValue} onChange={(e) => setBatchSizeValue(e.target.value)} />
            </Field>
            <Field label="Batch size UOM (optional)">
              <Input list="dl-uom-batch-size" value={batchSizeUom} onChange={(e) => setBatchSizeUom(e.target.value)} />
              <datalist id="dl-uom-batch-size">
                {uomOptions.map((code) => (
                  <option key={code} value={code} />
                ))}
              </datalist>
            </Field>
          </div>
          {pvError && <p className="error-text mt-2">{pvError}</p>}
          {error && <p className="error-text mt-2">{error}</p>}

          <RecipeGraphEditor
            sections={sections}
            onChange={setSections}
            roleOptions={roleOptions}
            ruleOptions={ruleOptions}
            materialSpecOptions={materialSpecOptions}
            qualificationCodeOptions={qualificationCodeOptions}
            uomOptions={uomOptions}
            equipmentClassOptions={equipmentClassOptions}
          />

          <div className="flex justify-between gap-3 mt-2">
            <LinkButton href="/recipe-master">Cancel</LinkButton>
            <Button
              type="submit"
              variant="primary"
              disabled={
                busy ||
                !productBusinessId.trim() ||
                !recipeCode.trim() ||
                !siteId ||
                !productVersionId.trim() ||
                sections.length === 0 ||
                totalStepCount(sections) === 0
              }
            >
              {busy ? "Creating…" : "Create draft"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
