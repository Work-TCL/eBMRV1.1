"use client";

import { useState } from "react";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useApiResource } from "@/lib/hooks";

// GET /products/v1/business-ids — every Product Master business id, one row per latest version.
interface ProductBusinessIdOption {
  product_business_id: string;
  name: string;
  version_no: number;
  lifecycle_state: string;
}
// GET /products/v1/{business_id}/versions — every version of one Business ID.
interface ProductVersionOption {
  product_version_id: string;
  product_business_id: string;
  version_no: number;
  name: string;
  lifecycle_state: string;
  manufacturing_profile_code: string;
  site_id: string;
}

/**
 * Two dependent dropdowns — Product, then that product's RELEASED versions only — for any field that
 * references a Product Master version id. Extracted from `components/ddcp/DdcpFieldControl.tsx`'s
 * `ProductVersionPickerField` (built for DDCP's `product_version_id`, SG-175) into a reusable, DDCP-
 * agnostic component so other pages needing the same "a released product version" reference (a
 * complaint's product, a device lot's product, a QC specification's scope) don't hand-type a UUID found
 * by going to look it up on `/product-master` first. The DDCP component itself is left as-is (out of
 * scope for this pass) — this is a parallel, independent copy, not a shared import, so a future change
 * to one doesn't silently affect the other's DDCP-specific behaviour (e.g. its manufacturing-profile-code
 * hint).
 */
export function ProductVersionPickerField({
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
  const [businessId, setBusinessId] = useState("");
  const { data: businessIds, loading: businessIdsLoading, error: businessIdsError } =
    useApiResource<ProductBusinessIdOption[]>("/products/v1/business-ids");
  const { data: versions, loading: versionsLoading, error: versionsError } = useApiResource<ProductVersionOption[]>(
    businessId ? `/products/v1/${encodeURIComponent(businessId)}/versions` : null,
  );
  const released = (versions ?? []).filter((v) => v.lifecycle_state === "released");

  if (businessIdsError) {
    return (
      <Field label={label} required={required} hint="Couldn't load the product list - enter the product version ID directly.">
        <Input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder="Product version ID" />
      </Field>
    );
  }

  return (
    <Field label={label} required={required} hint={hint}>
      <div className="flex flex-wrap gap-2">
        <Select
          value={businessId}
          onChange={(e) => {
            setBusinessId(e.target.value);
            onChange("");
          }}
          disabled={businessIdsLoading}
          style={{ flex: "1 1 200px", minWidth: 0 }}
        >
          <option value="">{businessIdsLoading ? "Loading products…" : "Select a product…"}</option>
          {(businessIds ?? []).map((b) => (
            <option key={b.product_business_id} value={b.product_business_id}>
              {b.product_business_id} - {b.name}
            </option>
          ))}
        </Select>
        <Select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={!businessId || versionsLoading}
          style={{ flex: "1 1 200px", minWidth: 0 }}
        >
          <option value="">
            {!businessId ? "—" : versionsLoading ? "Loading versions…" : released.length ? "Select a released version…" : "No released versions"}
          </option>
          {released.map((v) => (
            <option key={v.product_version_id} value={v.product_version_id}>
              v{v.version_no} - {v.name}
            </option>
          ))}
        </Select>
      </div>
      {versionsError && <p className="error-text mt-2">Couldn&rsquo;t load versions for this product.</p>}
    </Field>
  );
}
