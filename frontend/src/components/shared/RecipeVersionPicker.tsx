"use client";

import { useState } from "react";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useApiResource } from "@/lib/hooks";

// GET /recipes/v2/families — matches app/modules/recipe_master/router.py::get_families.
interface RecipeFamilyRow {
  recipe_family_id: string;
  recipe_code: string;
  product_business_id: string;
  manufacturing_profile_code: string;
  family_lifecycle_state: string;
  has_released: boolean;
}
// GET /recipes/v2/{family_id}/versions
interface RecipeVersionRow {
  recipe_version_id: string;
  recipe_family_id: string;
  version_no: number;
  lifecycle_state: string;
}

/**
 * Two dependent dropdowns — Recipe family, then that family's RELEASED versions only — for any field
 * that references a Recipe Master version id. Same shape as `ProductVersionPicker`'s
 * `ProductVersionPickerField` (both endpoints follow the identical "business id/family list, then that
 * item's versions" two-step Recipe Master's own page already established) — built for QC's specification
 * "Scope version ID" (`scope_type=in_process`), which previously asked the operator to go find a recipe
 * version id on `/recipe-master` and paste it in.
 */
export function RecipeVersionPickerField({
  label,
  required,
  hint,
  value,
  onChange,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const [familyId, setFamilyId] = useState("");
  const { data: families, loading: familiesLoading, error: familiesError } = useApiResource<RecipeFamilyRow[]>(
    "/recipes/v2/families",
  );
  const { data: versions, loading: versionsLoading, error: versionsError } = useApiResource<RecipeVersionRow[]>(
    familyId ? `/recipes/v2/${encodeURIComponent(familyId)}/versions` : null,
  );
  const released = (versions ?? []).filter((v) => v.lifecycle_state === "released");

  if (familiesError) {
    return (
      <Field label={label} required={required} hint="Couldn't load the recipe list - enter the recipe version ID directly.">
        <Input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder="Recipe version ID" />
      </Field>
    );
  }

  return (
    <Field label={label} required={required} hint={hint}>
      <div className="flex flex-wrap gap-2">
        <Select
          value={familyId}
          onChange={(e) => {
            setFamilyId(e.target.value);
            onChange("");
          }}
          disabled={familiesLoading}
          style={{ flex: "1 1 200px", minWidth: 0 }}
        >
          <option value="">{familiesLoading ? "Loading recipes…" : "Select a recipe…"}</option>
          {(families ?? []).filter((f) => f.has_released).map((f) => (
            <option key={f.recipe_family_id} value={f.recipe_family_id}>
              {f.recipe_code}
            </option>
          ))}
        </Select>
        <Select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={!familyId || versionsLoading}
          style={{ flex: "1 1 200px", minWidth: 0 }}
        >
          <option value="">
            {!familyId ? "—" : versionsLoading ? "Loading versions…" : released.length ? "Select a released version…" : "No released versions"}
          </option>
          {released.map((v) => (
            <option key={v.recipe_version_id} value={v.recipe_version_id}>
              v{v.version_no}
            </option>
          ))}
        </Select>
      </div>
      {versionsError && <p className="error-text mt-2">Couldn&rsquo;t load versions for this recipe.</p>}
    </Field>
  );
}
