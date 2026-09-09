"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { listAll } from "@/lib/api";
import { useApiResource } from "@/lib/hooks";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import type { AsyncStatus } from "./entityOptions";
import {
  type DdcpField,
  type DdcpFormState,
  type FieldValue,
  type KvRow,
  type RefValue,
  type RepeatRow,
  type SelectOption,
} from "./fields";

export interface ProfileSummary {
  id: string;
  profile_code: string;
  subtype: string | null;
  version: number;
  state: string;
}

export interface EntityCtx {
  batches: SelectOption[];
  batchesStatus: AsyncStatus;
  equipment: SelectOption[];
  equipmentStatus: AsyncStatus;
  areas: SelectOption[];
  areasStatus: AsyncStatus;
  materialLots: SelectOption[];
  materialLotsStatus: AsyncStatus;
  releasedBatches: SelectOption[];
  releasedBatchesStatus: AsyncStatus;
}

function plural(kind: string): string {
  return /[sxz]$|[cs]h$/.test(kind) ? `${kind}es` : `${kind}s`;
}

// "user"/"unit"/"unique" etc. start with the letter u but the consonant /j/ ("yoo") sound, so they take
// "a" like any consonant word — the "starts with a vowel letter" heuristic below gets these wrong.
const CONSONANT_SOUND_EXCEPTIONS = /^(user|unit|unique|uniform|one)\b/i;

function article(kind: string): string {
  if (CONSONANT_SOUND_EXCEPTIONS.test(kind)) return "a";
  return /^[aeiou]/i.test(kind) ? "an" : "a";
}

const linkBtnStyle: CSSProperties = {
  background: "none",
  border: "none",
  padding: 0,
  color: "var(--brand-600)",
  fontSize: "var(--fs-2)",
  cursor: "pointer",
  textDecoration: "underline",
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
};

/** Renders a whole field list in the app's standard two-column responsive grid (collapses to one
 * column under 900px per `ebmr-components.css`) — repeatable/key-value fields always span both
 * columns since their rows need the room. */
export function DdcpFieldsGrid({
  fields,
  state,
  onChange,
  entities,
  profilePrefix,
  recentRecords,
  siteId,
}: {
  fields: DdcpField[];
  state: DdcpFormState;
  onChange: (name: string, value: FieldValue) => void;
  entities: EntityCtx;
  /** Required when `fields` contains a "profileSelect" field — the current family's API prefix (e.g.
   * `/ddcp/v1/prefilled-syringe`), so the picker knows which family's profiles to list. */
  profilePrefix?: string;
  /** Required when `fields` contains a "recordSelect" field — every id recorded so far this session,
   * keyed by `DdcpOp.producesRecordKind` (see catalog.ts / ExecutionCard). */
  recentRecords?: Record<string, SelectOption[]>;
  /** Required when `fields` contains a "sterilizationSelect" field — scopes the eligible-items list to
   * the current site. */
  siteId?: string | null;
}) {
  // A `ref` field's QC-result picker (key "record_id", see `refEntityFor`) is scoped to *this batch*,
  // not global like every other entity list — the same batch_id field always sitting alongside it in
  // the same form is the only place to read that from, so it's derived here rather than threaded in as
  // yet another prop every caller would have to supply redundantly.
  const batchId = typeof state.batch_id === "string" ? state.batch_id : undefined;
  return (
    <div className="grid grid-cols-2 gap-4">
      {fields.map((f) => (
        <div key={f.name} style={f.type === "repeat" || f.type === "kv" ? { gridColumn: "1 / -1" } : undefined}>
          <DdcpFieldControl
            field={f}
            value={state[f.name]}
            onChange={(v) => onChange(f.name, v)}
            entities={entities}
            profilePrefix={profilePrefix}
            recentRecords={recentRecords}
            siteId={siteId}
            batchId={batchId}
          />
        </div>
      ))}
    </div>
  );
}

export function DdcpFieldControl({
  field,
  value,
  onChange,
  entities,
  profilePrefix,
  recentRecords,
  siteId,
  batchId,
}: {
  field: DdcpField;
  value: FieldValue;
  onChange: (value: FieldValue) => void;
  entities: EntityCtx;
  profilePrefix?: string;
  recentRecords?: Record<string, SelectOption[]>;
  siteId?: string | null;
  /** Required for a "ref" field's QC-result picker (key "record_id") — scopes `GET /qc/v1/results` to
   * this form's own `batch_id` field, read by `DdcpFieldsGrid`. */
  batchId?: string;
}) {
  switch (field.type) {
    case "select":
      return (
        <Field label={field.label} required={field.required} hint={field.hint}>
          <Select value={value as string} onChange={(e) => onChange(e.target.value)}>
 <option value="">Select</option>
            {(field.options ?? []).map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </Field>
      );
    case "bool":
    case "boolKv":
      return (
        <Field label={field.label} required={field.required} hint={field.hint}>
          <Select value={value as string} onChange={(e) => onChange(e.target.value)}>
 <option value="">Select</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </Select>
        </Field>
      );
    case "recordSelect":
      return (
        <PickerField
          field={field}
          value={value as string}
          onChange={onChange}
          options={recentRecords?.[field.recordKind ?? ""] ?? []}
          status={(recentRecords?.[field.recordKind ?? ""]?.length ?? 0) > 0 ? "ready" : "empty"}
          kind={field.pickerKind ?? "record"}
          // This picker's list is session memory (no backend "list all handoffs/assembly records"
          // endpoint) — after a refresh it's empty even though the real records still exist. Point at
          // the actual recovery step instead of the generic "none yet" (which reads as "you never made
          // one"), for the record kinds page.tsx's genealogy lookup can actually refill.
          emptyHint={
            field.recordKind === "pfs_handoff" || field.recordKind === "pfs_assembly_record" || field.recordKind === "pfs_fill_operation"
              ? `No ${plural(field.pickerKind ?? "record")} remembered this session (a page refresh clears it) — use "Look up existing records for a batch" above to reload them from this batch's real history.`
              : undefined
          }
        />
      );
    case "batchSelect":
      return (
        <PickerField
          field={field}
          value={value as string}
          onChange={onChange}
          options={entities.batches}
          status={entities.batchesStatus}
          kind="batch"
        />
      );
    case "equipmentSelect":
      return (
        <PickerField
          field={field}
          value={value as string}
          onChange={onChange}
          options={entities.equipment}
          status={entities.equipmentStatus}
          kind="equipment asset"
        />
      );
    case "areaSelect":
      return (
        <PickerField
          field={field}
          value={value as string}
          onChange={onChange}
          options={entities.areas}
          status={entities.areasStatus}
          kind="equipment area"
        />
      );
    case "profileSelect":
      return <ProfilePickerField field={field} value={value as string} onChange={onChange} profilePrefix={profilePrefix} />;
    case "productVersionSelect":
      return <ProductVersionPickerField field={field} value={value as string} onChange={onChange} />;
    case "sterilizationSelect":
      return <SterilizationItemPickerField field={field} value={value as string} onChange={onChange} siteId={siteId} />;
    case "ruleSelect":
      return <RuleAcceptancePickerField field={field} value={value as string} onChange={onChange} />;
    case "asepticInterventionSelect":
      return <AsepticInterventionPickerField field={field} value={value as string} onChange={onChange} siteId={siteId} />;
    case "datetime":
      return (
        <Field label={field.label} required={field.required} hint={field.hint}>
          <Input type="datetime-local" value={value as string} onChange={(e) => onChange(e.target.value)} />
        </Field>
      );
    case "number":
      return (
        <Field label={field.label} required={field.required} hint={field.hint}>
          <Input type="number" value={value as string} onChange={(e) => onChange(e.target.value)} placeholder={field.placeholder} />
        </Field>
      );
    case "decimal":
      return (
        <Field label={field.label} required={field.required} hint={field.hint}>
          <Input
            type="text"
            inputMode="decimal"
            value={value as string}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder ?? "0.000000"}
          />
        </Field>
      );
    case "ref":
      return <RefFieldControl field={field} value={value as RefValue} onChange={onChange} entities={entities} batchId={batchId} />;
    case "repeat":
      return <RepeatFieldControl field={field} value={value as RepeatRow[]} onChange={onChange} />;
    case "kv":
      return <KvFieldControl field={field} value={value as KvRow[]} onChange={onChange} />;
    default:
      return (
        <Field label={field.label} required={field.required} hint={field.hint}>
          <Input
            type="text"
            list={field.suggestions ? `dl-${field.name}` : undefined}
            value={value as string}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
          />
          {field.suggestions && (
            <datalist id={`dl-${field.name}`}>
              {field.suggestions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </datalist>
          )}
        </Field>
      );
  }
}

/** The DDCP-specific FK picker: unlike batch/equipment, which entities load are known up front,
 * profiles are scoped per product family — this fetches from `{profilePrefix}/profiles` itself
 * (defaulting to RELEASED only, the only state a batch/execution field can actually use) rather than
 * going through the shared `useEntityOptions` hook, which has no notion of "which family". Re-fetches
 * whenever `profilePrefix` changes (i.e. the user switched product family). */
/** Exported so pages that need a profile picker outside the normal `DdcpFieldsGrid` flow — e.g.
 * `ProfileCard`'s "release a profile version" / "look up a profile version" sub-forms, which target a
 * DRAFT profile at least as often as a RELEASED one — can reuse it directly with `allStates`. */
export function ProfilePickerField({
  field,
  value,
  onChange,
  profilePrefix,
  allStates,
  refreshToken,
  onSelectVersion,
}: {
  field: DdcpField;
  value: string;
  onChange: (value: FieldValue) => void;
  profilePrefix?: string;
  /** Default (false/omitted): only RELEASED profiles, matching what a batch actually checks against.
   * true: every state, labelled with its state — for release/lookup flows where a DRAFT is the normal
   * target. */
  allStates?: boolean;
  /** Bump (e.g. a counter) to force a refetch — for a caller like "release a profile" that creates a
   * new profile elsewhere on the same page and wants it to show up in this list without a remount. */
  refreshToken?: number;
  /** Fired whenever the picked option changes to a profile this list actually has a row for — carries
   * that profile's real current `version`, so a caller with its own "Expected version" field (release)
   * can keep it correct instead of drifting from a stale hardcoded default (STALE_VERSION otherwise —
   * a profile's `version` is *not* always 1 even freshly created: reusing an existing profile_code
   * continues that code's own version sequence). `null` when the picker switches to manual-id entry,
   * where no row (and so no known version) exists to read from. */
  onSelectVersion?: (version: number | null) => void;
}) {
  const [rows, setRows] = useState<ProfileSummary[]>([]);
  const [fetchStatus, setFetchStatus] = useState<AsyncStatus>("loading");
  // `profilePrefix` is always supplied in practice (every DdcpFieldsGrid call passes family.prefix) —
  // the missing case is a defensive fallback, derived at render time rather than via an effect-time
  // setState so the "no prefix" case never needs its own effect run.
  const status: AsyncStatus = profilePrefix ? fetchStatus : "error";
  const options: SelectOption[] = rows.map((p) => ({
    value: p.id,
 label: `${p.profile_code} v${p.version}${allStates ? ` ${p.state}` : ""}${p.subtype ? ` ${p.subtype}` : ""}`,
  }));

  useEffect(() => {
    if (!profilePrefix) return;
    let cancelled = false;
    // No synchronous "loading" reset here — the card this renders inside is remounted (via a `key`
    // keyed to the product family) on every family switch, so this component's initial `useState`
    // already starts fresh at "loading" whenever `profilePrefix` could meaningfully change.
    listAll<ProfileSummary>(`${profilePrefix}/profiles`, allStates ? { state: "" } : undefined)
      .then((fetched) => {
        if (cancelled) return;
        setRows(fetched);
        setFetchStatus(fetched.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setFetchStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [profilePrefix, allStates, refreshToken]);

  function handleChange(v: FieldValue) {
    onChange(v);
    if (onSelectVersion) onSelectVersion(rows.find((r) => r.id === v)?.version ?? null);
  }

  return (
    <PickerField field={field} value={value} onChange={handleChange} options={options} status={status} kind={allStates ? "profile" : "released profile"} />
  );
}

// GET /products/v1/business-ids — one row per Product Master Business ID (its latest version).
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

/** SG-175 (product_version_id half, 2026-09-08): every DDCP profile now names the real, RELEASED
 * Product Master version it is the combination-product spec for. Two dependent dropdowns — Product,
 * then that product's RELEASED versions only — the same shape Recipe Master's own Product/Product-
 * version fields use, for the same reason: Product Master is keyed by business ID first, there is no
 * flat "every product version" list endpoint to pick from directly. Shows the picked version's
 * `manufacturing_profile_code` inline so an operator can see a family mismatch (this generic control
 * has no notion of which DDCP family it's rendering inside) before submit ever comes back
 * `PROFILE_SCHEMA_INVALID` — the backend is what actually enforces the match, for the two families
 * where it's unambiguous (see `commands.py::_assert_product_version_for_profile`). */
function ProductVersionPickerField({
  field,
  value,
  onChange,
}: {
  field: DdcpField;
  value: string;
  onChange: (value: FieldValue) => void;
}) {
  const [businessId, setBusinessId] = useState("");
  const { data: businessIds, loading: businessIdsLoading, error: businessIdsError } =
    useApiResource<ProductBusinessIdOption[]>("/products/v1/business-ids");
  const { data: versions, loading: versionsLoading, error: versionsError } = useApiResource<ProductVersionOption[]>(
    businessId ? `/products/v1/${encodeURIComponent(businessId)}/versions` : null,
  );
  const released = (versions ?? []).filter((v) => v.lifecycle_state === "released");
  const picked = released.find((v) => v.product_version_id === value);

  if (businessIdsError) {
    return (
      <Field label={field.label} required={field.required} hint="Couldn't load the product list — enter the product version ID directly.">
        <Input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder="Product version ID" />
      </Field>
    );
  }

  return (
    <Field
      label={field.label}
      required={field.required}
      hint={picked ? `Manufacturing profile: ${picked.manufacturing_profile_code}` : field.hint}
    >
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
              {b.product_business_id} — {b.name}
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
              v{v.version_no} — {v.name}
            </option>
          ))}
        </Select>
      </div>
      {versionsError && <p className="error-text mt-2">Couldn&rsquo;t load versions for this product.</p>}
    </Field>
  );
}

// GET /sterilization/v1/items/eligible — real picker data for DDCP's constituent-handoff
// "Sterilization/depyrogenation reference" (PFS-FR-005), previously free-text UUID entry. Lists only
// items the same check the handoff decision runs would actually accept (SterilizationLoadItem
// sterile_status=eligible, or SterileFilterUse state=completed) — see the endpoint's own docstring.
interface EligibleSterilizationItem {
  id: string;
  kind: "load_item" | "filter_use";
  label: string;
}

function SterilizationItemPickerField({
  field,
  value,
  onChange,
  siteId,
}: {
  field: DdcpField;
  value: string;
  onChange: (value: FieldValue) => void;
  siteId?: string | null;
}) {
  const { data, loading, error } = useApiResource<EligibleSterilizationItem[]>(
    siteId ? `/sterilization/v1/items/eligible?site_id=${siteId}` : null,
  );
  const options: SelectOption[] = (data ?? []).map((item) => ({ value: item.id, label: item.label }));
  const status: AsyncStatus = !siteId ? "error" : loading ? "loading" : error ? "error" : options.length ? "ready" : "empty";

  return (
    <PickerField
      field={field}
      value={value}
      onChange={onChange}
      options={options}
      status={status}
      kind="sterilization/depyrogenation record"
      emptyHint="No completed sterilization or depyrogenation record is on file yet for this site — record one on /sterilization first, or leave this blank if the component doesn't need one."
    />
  );
}

// GET /rules/v1 — one row per rule with a currently-effective RELEASED version, keyed by its human
// `rule_id` (not a uuid) — the same list recipe_master's condition_rule_id picker already uses. Every
// acceptance_rule_id field was previously free-text entry with no way to discover a valid id, surfacing
// only as a NOT_FOUND ("No effective released version resolves for this rule") on submit.
interface ReleasedRuleOption {
  rule_id: string;
  rule_type: string;
  semantic_version: string;
}

function RuleAcceptancePickerField({
  field,
  value,
  onChange,
}: {
  field: DdcpField;
  value: string;
  onChange: (value: FieldValue) => void;
}) {
  const { data, loading, error } = useApiResource<ReleasedRuleOption[]>("/rules/v1");
  const options: SelectOption[] = (data ?? []).map((r) => ({ value: r.rule_id, label: `${r.rule_id} v${r.semantic_version} (${r.rule_type})` }));
  const status: AsyncStatus = loading ? "loading" : error ? "error" : options.length ? "ready" : "empty";

  return (
    <PickerField
      field={field}
      value={value}
      onChange={onChange}
      options={options}
      status={status}
      kind="released rule"
      emptyHint="No rule has a currently-effective RELEASED version yet — release one on /rules first."
    />
  );
}

// GET /aseptic/v1/interventions — real picker data for DDCP's "Record an aseptic intervention"
// source_aseptic_intervention_id, previously free-text UUID entry with no way to discover a real
// AsepticIntervention id.
interface AsepticInterventionOption {
  id: string;
  operation_id: string;
  label: string;
}

function AsepticInterventionPickerField({
  field,
  value,
  onChange,
  siteId,
}: {
  field: DdcpField;
  value: string;
  onChange: (value: FieldValue) => void;
  siteId?: string | null;
}) {
  const { data, loading, error } = useApiResource<AsepticInterventionOption[]>(
    siteId ? `/aseptic/v1/interventions?site_id=${siteId}` : null,
  );
  const options: SelectOption[] = (data ?? []).map((i) => ({ value: i.id, label: i.label }));
  const status: AsyncStatus = !siteId ? "error" : loading ? "loading" : error ? "error" : options.length ? "ready" : "empty";

  return (
    <PickerField
      field={field}
      value={value}
      onChange={onChange}
      options={options}
      status={status}
      kind="aseptic intervention"
      emptyHint="No aseptic intervention is on file yet for this site — record one on /aseptic first, or leave this blank if there's no linked intervention."
    />
  );
}

/** The bare control behind every foreign-key picker — a dropdown of human-readable rows once the list
 * has loaded, with a manual-ID fallback the user can always reach (loading/empty/error states per spec
 * section 14) — with no `<Field>` wrapper of its own, so a caller that needs to place something else
 * (e.g. `RefFieldControl`'s key selector) beside it in the *same* labelled field can. `PickerField` below
 * is this plus that wrapper, for the common one-control-per-field case every other caller wants. */
function PickerControl({
  value,
  onChange,
  options,
  status,
  kind,
  placeholder,
  onHintChange,
  emptyHint,
}: {
  value: string;
  onChange: (value: FieldValue) => void;
  options: SelectOption[];
  status: AsyncStatus;
  kind: string;
  placeholder?: string;
  /** Fires (in an effect, never during render) with a status-specific hint override, or `null` to fall
   * back to the field's own hint — `PickerField` uses this to swap the `<Field>` hint text; a caller
   * placing this control inline (no separate hint slot) can omit it. */
  onHintChange?: (hint: string | null) => void;
  /** Replaces the default "No {kind} available yet." shown while `status === "empty"`. */
  emptyHint?: string;
}) {
  const [manual, setManual] = useState(false);
  const useManual = manual || status === "error";
  const hint = useManual
    ? status === "error"
 ? `Couldn't load the ${kind} list enter the ID directly.`
      : null
    : status === "empty"
      ? (emptyHint ?? `No ${plural(kind)} available yet.`)
      : null;

  useEffect(() => {
    onHintChange?.(hint);
    // onHintChange is a fresh closure every render in every caller here — including it would re-fire
    // this effect every render regardless of whether `hint` itself changed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hint]);

  if (useManual) {
    return (
      <>
        <Input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder ?? `${kind} ID`} />
        {status !== "error" && (
          <button type="button" style={{ ...linkBtnStyle, marginTop: 6 }} onClick={() => setManual(false)}>
            Choose from list instead
          </button>
        )}
      </>
    );
  }

  if (status === "loading") {
    return (
      <Select disabled>
        <option>{`Loading ${plural(kind)}…`}</option>
      </Select>
    );
  }

  if (status === "empty") {
    return <Input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder ?? `${kind} ID`} />;
  }

  return (
    <>
      <Select value={value} onChange={(e) => onChange(e.target.value)}>
 <option value="">{`Select ${article(kind)} ${kind}`}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>
      <button type="button" style={{ ...linkBtnStyle, marginTop: 6 }} onClick={() => setManual(true)}>
        Can&rsquo;t find it? Enter ID manually
      </button>
    </>
  );
}

function PickerField({
  field,
  value,
  onChange,
  options,
  status,
  kind,
  emptyHint,
}: {
  field: DdcpField;
  value: string;
  onChange: (value: FieldValue) => void;
  options: SelectOption[];
  status: AsyncStatus;
  kind: string;
  /** Overrides the generic "No {kind} available yet." shown while `status === "empty"` — for a picker
   * with a real recovery step (e.g. "look up existing records for a batch" above, DDCP's session-memory
   * record pickers) rather than just manual entry. */
  emptyHint?: string;
}) {
  const [hintOverride, setHintOverride] = useState<string | null>(null);
  return (
    <Field label={field.label} required={field.required} hint={hintOverride ?? field.hint}>
      <PickerControl
        value={value}
        onChange={onChange}
        options={options}
        status={status}
        kind={kind}
        placeholder={field.placeholder}
        onHintChange={setHintOverride}
        emptyHint={emptyHint}
      />
    </Field>
  );
}

/** `ref` key names this app actually has a real record list for — a value typed by hand against one of
 * these is exactly how the earlier DDCP "Source" bug happened (a non-UUID string reached the backend's
 * `uuid.UUID()` unguarded and 500'd instead of a clean validation error). Every other ref key
 * (container/device/unit/procedure/record/plan/method/cycle/ncr id, …) has no list endpoint anywhere in
 * this app to pick from — those stay manual text, honestly, rather than fake a dropdown with nothing to
 * fill it.
 *
 * "record_id" (every `qc_record_reference` field's own key) is deliberately absent here — unlike
 * batch_id/lot_id it isn't a flat site-wide list, it's scoped to *this form's own* batch_id, which this
 * function has no access to. `RefFieldControl` below handles it as a second, dynamic picker source
 * instead of extending this one. */
function refEntityFor(key: string, entities: EntityCtx): { options: SelectOption[]; status: AsyncStatus; kind: string } | null {
  // "released" only, not the plain `batches` list every other batch picker on this page uses — a
  // handoff's upstream batch_id source specifically has to already be released (PFS-FR-003/004,
  // BULK_NOT_RELEASED otherwise), so an unreleased batch is never a valid choice here.
  if (key === "batch_id") return { options: entities.releasedBatches, status: entities.releasedBatchesStatus, kind: "released batch" };
  if (key === "lot_id") return { options: entities.materialLots, status: entities.materialLotsStatus, kind: "material lot" };
  return null;
}

interface QcResultOption {
  id: string;
  label: string;
}

/** A small "which kind of reference, and what's the id" pair — replaces a raw `{"batch_id": "..."}` /
 * `{"lot_id": "..."}` JSON object with two plain controls. The id half is a real picker (dropdown +
 * manual fallback) whenever the selected key names a kind this app has a record list for; otherwise
 * plain text, same as before. */
function RefFieldControl({
  field,
  value,
  onChange,
  entities,
  batchId,
}: {
  field: DdcpField;
  value: RefValue;
  onChange: (value: FieldValue) => void;
  entities: EntityCtx;
  batchId?: string;
}) {
  const keys = field.refKeys ?? [{ value: "value", label: field.label }];
  const selectedKey = value?.key ?? keys[0].value;
  const staticEntity = refEntityFor(selectedKey, entities);

  // "record_id" (qc_record_reference, PFS-FR-014/017 and its family-equivalents) — scoped to whichever
  // batch this same form's own batch_id field currently names, so unlike every other ref picker this one
  // has to fetch dynamically rather than read a list `entities` already loaded once up front.
  const isQcResult = selectedKey === "record_id";
  const { data: qcResults, loading: qcLoading, error: qcError } = useApiResource<QcResultOption[]>(
    isQcResult && batchId ? `/qc/v1/results?batch_id=${batchId}` : null,
  );
  const qcOptions: SelectOption[] = (qcResults ?? []).map((r) => ({ value: r.id, label: r.label }));
  // No batch entered yet reads as "empty" (my own emptyHint below explains why), not "error" — "error"
  // would show the generic "couldn't load the list" wording, wrong for a state that isn't a failure.
  const qcStatus: AsyncStatus = !batchId ? "empty" : qcLoading ? "loading" : qcError ? "error" : qcOptions.length ? "ready" : "empty";
  const qcEntity = isQcResult ? { options: qcOptions, status: qcStatus, kind: "QC result" } : null;

  const entity = staticEntity ?? qcEntity;
  const [hintOverride, setHintOverride] = useState<string | null>(null);

  return (
    // hintOverride only applies while `entity` is actually mounted (below) — otherwise it can be a
    // stale leftover from before the operator switched to a ref key with no picker (e.g. batch_id's
    // "No batches available yet." lingering on a plain-text device_id field).
    <Field label={field.label} required={field.required} hint={entity ? hintOverride ?? field.hint : field.hint}>
      <div className="flex flex-wrap gap-2 items-start">
        {keys.length > 1 && (
          <Select
            value={selectedKey}
            // A batch id typed/picked for "lot_id" (or vice versa) is meaningless once the key changes —
            // clear the value along with it rather than leave a stale, wrong-kind id sitting there.
            onChange={(e) => onChange({ key: e.target.value, value: "" })}
            style={{ flex: "1 1 160px", minWidth: 0 }}
          >
            {keys.map((k) => (
              <option key={k.value} value={k.value}>
                {k.label}
              </option>
            ))}
          </Select>
        )}
        <div style={{ flex: "2 1 160px", minWidth: 0 }}>
          {entity ? (
            <PickerControl
              value={value?.value ?? ""}
              onChange={(v) => onChange({ key: selectedKey, value: v as string })}
              options={entity.options}
              status={entity.status}
              kind={entity.kind}
              placeholder={field.refValuePlaceholder}
              onHintChange={setHintOverride}
              emptyHint={
                isQcResult
                  ? batchId
                    ? "No QC result is on file yet for this batch — link one via the QC module (/qc: sample → test order → result) first, or enter the ID manually if it isn't in this batch's QC chain."
                    : "Enter the batch above first to look up its QC results."
                  : undefined
              }
            />
          ) : (
            <Input
              type="text"
              value={value?.value ?? ""}
              onChange={(e) => onChange({ key: selectedKey, value: e.target.value })}
              placeholder={field.refValuePlaceholder ?? "Enter the ID"}
            />
          )}
        </div>
      </div>
    </Field>
  );
}

/** A scalar sub-field inside one repeatable row — same input types as the top-level control, minus the
 * nested/repeatable ones (a row's cells are always plain values). */
function SubFieldControl({ field, value, onChange }: { field: DdcpField; value: string; onChange: (value: string) => void }) {
  const labelRow = (
    <label className="hint" style={{ display: "block", marginBottom: 4 }}>
      {field.label} {field.required && <span style={{ color: "var(--status-critical-solid)" }}>*</span>}
    </label>
  );
  if (field.type === "select") {
    return (
      <div>
        {labelRow}
        <Select value={value} onChange={(e) => onChange(e.target.value)}>
 <option value="">Select</option>
          {(field.options ?? []).map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
      </div>
    );
  }
  if (field.type === "bool") {
    return (
      <div>
        {labelRow}
        <Select value={value} onChange={(e) => onChange(e.target.value)}>
 <option value=""></option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </Select>
      </div>
    );
  }
  return (
    <div>
      {labelRow}
      <Input
        type={field.type === "number" ? "number" : "text"}
        inputMode={field.type === "decimal" ? "decimal" : undefined}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={field.placeholder}
      />
    </div>
  );
}

/** Replaces a JSON array (e.g. `constituent_requirements`, one sample per row) with Add/Remove rows of
 * plain fields — spec section 5/6's worked example. */
function RepeatFieldControl({ field, value, onChange }: { field: DdcpField; value: RepeatRow[]; onChange: (value: FieldValue) => void }) {
  const rows = value ?? [];
  const itemLabel = field.itemLabel ?? field.label;

  function addRow() {
    const blank: RepeatRow = {};
    for (const sf of field.subFields ?? []) blank[sf.name] = sf.default ?? "";
    onChange([...rows, blank]);
  }
  function updateRow(i: number, name: string, v: string) {
    onChange(rows.map((r, idx) => (idx === i ? { ...r, [name]: v } : r)));
  }
  function removeRow(i: number) {
    onChange(rows.filter((_, idx) => idx !== i));
  }

  return (
    <div className="field">
      <label className="label">
        {field.label} {field.required && <span className="req">*</span>}
      </label>
      {field.hint && <p className="hint mb-2">{field.hint}</p>}
      {rows.map((row, i) => (
        <div key={i} className="sig-block mb-3">
          <div className="flex items-center justify-between mb-2">
            <span className="fs-2 font-semibold text-muted">
              {itemLabel} {i + 1}
            </span>
            <button type="button" style={linkBtnStyle} onClick={() => removeRow(i)} aria-label={`Remove ${itemLabel} ${i + 1}`}>
              <Icon name="x" /> Remove
            </button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {(field.subFields ?? []).map((sf) => (
              <SubFieldControl key={sf.name} field={sf} value={row[sf.name] ?? ""} onChange={(v) => updateRow(i, sf.name, v)} />
            ))}
          </div>
        </div>
      ))}
      <Button type="button" variant="secondary" size="sm" onClick={addRow}>
        <Icon name="plus" /> Add {itemLabel.toLowerCase()}
      </Button>
      {rows.length === 0 && field.required && (
        <p className="error-text mt-2">
          <Icon name="alert-circle" /> Add at least one {itemLabel.toLowerCase()}.
        </p>
      )}
    </div>
  );
}

/** Replaces a free-form JSON object (no fixed schema — e.g. `constituent_architecture`) with plain
 * "setting name" / "value" rows, per spec section 6's key/value-collection guidance. Values are typed
 * automatically (true/false/number/text) when the payload is built — the user never sees `{}`, `"`, `,`. */
function KvFieldControl({ field, value, onChange }: { field: DdcpField; value: KvRow[]; onChange: (value: FieldValue) => void }) {
  const rows = value ?? [];

  function update(i: number, patch: Partial<KvRow>) {
    onChange(rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }
  function add() {
    onChange([...rows, { key: "", value: "" }]);
  }
  function remove(i: number) {
    onChange(rows.filter((_, idx) => idx !== i));
  }

  return (
    <div className="field">
      <label className="label">{field.label}</label>
      {field.hint && <p className="hint mb-2">{field.hint}</p>}
      {rows.map((row, i) => (
        <div key={i} className="flex flex-wrap gap-2 mb-2 items-center">
          <Input placeholder="Setting name" value={row.key} onChange={(e) => update(i, { key: e.target.value })} style={{ flex: "1 1 140px", minWidth: 0 }} />
          <Input placeholder="Value" value={row.value} onChange={(e) => update(i, { value: e.target.value })} style={{ flex: "2 1 140px", minWidth: 0 }} />
          <button type="button" style={linkBtnStyle} onClick={() => remove(i)} aria-label={`Remove setting ${i + 1}`}>
            <Icon name="x" />
          </button>
        </div>
      ))}
      <Button type="button" variant="secondary" size="sm" onClick={add}>
        <Icon name="plus" /> Add setting
      </Button>
    </div>
  );
}
