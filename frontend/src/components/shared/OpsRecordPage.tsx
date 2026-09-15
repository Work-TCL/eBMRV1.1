"use client";

import { useState, type ReactNode } from "react";
import { api, ApiError, newIdempotencyKey, type Me, type MutationReceipt } from "@/lib/api";
import { useEntityOptions, useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { FactGrid } from "@/components/ui/FactGrid";
import { Banner } from "@/components/ui/Banner";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { WorkflowActionButton } from "@/components/shared/WorkflowActionButton";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { RepeatableRows, KeyValueRows, buildKvObject, buildRepeatArray, type RepeatRow, type KvRow, type RepeatSubField } from "@/components/shared/RepeatableFields";

/** A form field on a create form or a transition form. `json` fields are parsed before submit;
 * `select`/`bool` render a dropdown instead of free text; `batchSelect`/`equipmentSelect` render a
 * picker instead of a raw id; `repeat`/`kv` replace a JSON array/object with structured rows (additive
 * — every pre-existing type behaves exactly as before). */
export interface OpsFieldDef {
  name: string;
  label: string;
  type?: "text" | "number" | "date" | "textarea" | "json" | "select" | "bool" | "batchSelect" | "equipmentSelect" | "areaSelect" | "userSelect" | "materialSelect" | "supplierSelect" | "sterilizationProfileSelect" | "asepticProfileSelect" | "repeat" | "kv";
  hint?: string;
  required?: boolean;
  placeholder?: string;
  /** "select" only. */
  options?: { value: string; label: string }[];
  /** "repeat" only — the shape of each row. */
  subFields?: RepeatSubField[];
  /** "repeat" only — used in "Add …" / "Remove …" text. Defaults to `label`. */
  itemLabel?: string;
}

export interface OpsTransitionDef<T> {
  key: string;
  label: string;
  /** true → routed through the Part 11 signature ceremony. */
  signed?: boolean;
  /** action name posted to `{detailPath}/signature-challenges` (signed) — defaults to `key`. */
  challengeAction?: string;
  variant?: "primary" | "secondary" | "ghost" | "danger" | "success";
  fields?: OpsFieldDef[];
  /** Whether to offer this transition for the loaded record. */
  show?: (record: T) => boolean;
  can?: (me: Me | null) => boolean;
  summary: ReactNode;
  /** Path segment appended to `{apiRoot}/{id}` for the mutation. Defaults to `key`. */
  pathSegment?: string;
  /** Build the mutation body from parsed field values + the record. `idempotency_key` and (for
   * signed) `challenge_id`/`reauth_password` are merged in automatically. */
  buildBody: (record: T, values: Record<string, unknown>) => Record<string, unknown>;
}

export interface OpsRecordConfig<T> {
  title: string;
  subtitle: string;
  /** Human label for the id input, e.g. "Cleaning execution ID". */
  idLabel: string;
  /** e.g. `/cleaning/v1/executions` — detail is `{apiRoot}/{id}`, mutations `{apiRoot}/{id}/{seg}`. */
  apiRoot: string;
  create?: {
    label: string;
    can: (me: Me | null) => boolean;
    /** POST target, e.g. `/cleaning/v1/executions`. */
    path: string;
    fields: OpsFieldDef[];
    /** `siteId` is the active site; returns the POST body (idempotency_key merged automatically). */
    buildBody: (values: Record<string, unknown>, siteId: string | null) => Record<string, unknown>;
  };
  stateOf: (r: T) => string;
  numberOf: (r: T) => string;
  facts: (r: T) => ReactNode;
  extra?: (r: T) => ReactNode;
  transitions: OpsTransitionDef<T>[];
}

function parseValues(
  fields: OpsFieldDef[],
  raw: Record<string, string>,
  complex: Record<string, RepeatRow[] | KvRow[]> = {}
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    if (f.type === "repeat") {
      out[f.name] = buildRepeatArray(f.subFields ?? [], (complex[f.name] as RepeatRow[]) ?? []);
      continue;
    }
    if (f.type === "kv") {
      out[f.name] = buildKvObject((complex[f.name] as KvRow[]) ?? []);
      continue;
    }
    const v = (raw[f.name] ?? "").trim();
    if (v === "") {
      out[f.name] = null;
      continue;
    }
    if (f.type === "number") out[f.name] = Number(v);
    else if (f.type === "json") out[f.name] = JSON.parse(v);
    else if (f.type === "date") out[f.name] = new Date(v).toISOString();
    else out[f.name] = v;
  }
  return out;
}

function FieldInputs({
  fields,
  values,
  setValue,
  complexValues,
  setComplexValue,
}: {
  fields: OpsFieldDef[];
  values: Record<string, string>;
  setValue: (name: string, v: string) => void;
  complexValues?: Record<string, RepeatRow[] | KvRow[]>;
  setComplexValue?: (name: string, v: RepeatRow[] | KvRow[]) => void;
}) {
  const entities = useEntityOptions();
  return (
    <>
      {fields.map((f) => {
        if (f.type === "repeat") {
          return (
            <div key={f.name} style={{ gridColumn: "1 / -1" }}>
              <RepeatableRows
                label={f.label}
                required={f.required}
                hint={f.hint}
                itemLabel={f.itemLabel}
                subFields={f.subFields ?? []}
                value={(complexValues?.[f.name] as RepeatRow[]) ?? []}
                onChange={(rows) => setComplexValue?.(f.name, rows)}
                materialLotOptions={entities.materialLotCodes}
                materialLotOptionsStatus={entities.materialLotCodesStatus}
              />
            </div>
          );
        }
        if (f.type === "kv") {
          return (
            <div key={f.name} style={{ gridColumn: "1 / -1" }}>
              <KeyValueRows
                label={f.label}
                hint={f.hint}
                value={(complexValues?.[f.name] as KvRow[]) ?? []}
                onChange={(rows) => setComplexValue?.(f.name, rows)}
              />
            </div>
          );
        }
        if (f.type === "batchSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.batches} status={entities.batchesStatus} kind="batch"
            />
          );
        }
        if (f.type === "equipmentSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.equipment} status={entities.equipmentStatus} kind="equipment asset"
            />
          );
        }
        if (f.type === "areaSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.areas} status={entities.areasStatus} kind="equipment area"
            />
          );
        }
        if (f.type === "userSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.users} status={entities.usersStatus} kind="user"
            />
          );
        }
        if (f.type === "materialSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.materials} status={entities.materialsStatus} kind="material"
            />
          );
        }
        if (f.type === "supplierSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.suppliers} status={entities.suppliersStatus} kind="supplier"
            />
          );
        }
        if (f.type === "sterilizationProfileSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.sterilizationProfiles} status={entities.sterilizationProfilesStatus}
              kind="sterilization/CIP-SIP profile version"
            />
          );
        }
        if (f.type === "asepticProfileSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.asepticProfiles} status={entities.asepticProfilesStatus}
              kind="aseptic process profile version"
            />
          );
        }
        return (
          <Field key={f.name} label={f.label} required={f.required} hint={f.hint}>
            {f.type === "select" ? (
              <Select value={values[f.name] ?? ""} onChange={(e) => setValue(f.name, e.target.value)}>
 <option value="">Select</option>
                {(f.options ?? []).map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </Select>
            ) : f.type === "bool" ? (
              <Select value={values[f.name] ?? ""} onChange={(e) => setValue(f.name, e.target.value)}>
 <option value="">Select</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </Select>
            ) : f.type === "textarea" || f.type === "json" ? (
              <textarea
                className="input"
                rows={f.type === "json" ? 4 : 2}
                value={values[f.name] ?? ""}
                onChange={(e) => setValue(f.name, e.target.value)}
                placeholder={f.placeholder ?? (f.type === "json" ? "{ }" : undefined)}
                spellCheck={false}
              />
            ) : (
              <Input
                type={f.type === "number" ? "number" : f.type === "date" ? "date" : "text"}
                value={values[f.name] ?? ""}
                onChange={(e) => setValue(f.name, e.target.value)}
                placeholder={f.placeholder}
              />
            )}
          </Field>
        );
      })}
    </>
  );
}

/** The shared "look up one operations record by id, view it, drive its workflow" page — used by the
 * WP-06 cleaning / EM / sterilization / aseptic screens, none of which have a list endpoint. */
export function OpsRecordPage<T extends { id: string; version: number }>({
  config,
  headerAction,
  afterHeader,
  collapseCreate,
  onCreated,
  detailInModal,
  hideLookup,
}: {
  config: OpsRecordConfig<T>;
  /** Extra control rendered next to the title (e.g. a "New <related master data>" button) — additive,
   * every existing caller omits it and gets the same header as before. */
  headerAction?: ReactNode;
  /** Rendered directly under the title/actions, above the create form and the lookup box — e.g. a
   * browsable list of related master data the caller wants visible as soon as the page opens, not
   * scrolled past. A plain `ReactNode` for a list unrelated to `T` (aseptic's profile list); or a
   * function receiving `openRecord` — this page's own by-id lookup, so a list of `T` itself (e.g.
   * sterilization's cycle list) can wire each row's "Open" button straight into it instead of the
   * caller re-implementing the lookup. Additive; every pre-existing caller passes a plain node. */
  afterHeader?: ReactNode | ((openRecord: (id: string) => void) => ReactNode);
  /** When true, `config.create`'s form moves behind a "+ <create label>" button next to `headerAction`
   * and opens in a Modal instead of always being expanded inline — useful once the page has other
   * content (like `afterHeader`) that should be the first thing visible. Defaults to false (every
   * existing caller keeps today's always-expanded inline form, unaffected). */
  collapseCreate?: boolean;
  /** Fired after a successful create, once the new record is loaded — lets a caller whose `afterHeader`
   * lists `T` itself (e.g. sterilization's cycle list) refresh that list so the new row shows up
   * without a manual reload. Additive; omitted by every pre-existing caller. */
  onCreated?: () => void;
  /** When true, an opened record (facts + extra + actions) renders in a `Modal` — closed by its own X —
   * instead of inline below the lookup box. Pairs with an `afterHeader` list whose "Open" button drives
   * `openRecord`, so opening a row reads as "view this record" rather than growing the page underneath
   * the list. Defaults to false (every pre-existing caller keeps today's inline rendering). */
  detailInModal?: boolean;
  /** When true, omits the "look up by id" card entirely — for a page whose `afterHeader` list already
   * covers every way in to a record (its own "Open" button), where a second manual-id lookup path is
   * redundant. Defaults to false (every pre-existing caller keeps the lookup box). */
  hideLookup?: boolean;
}) {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [id, setId] = useState("");
  const [record, setRecord] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sigTransition, setSigTransition] = useState<OpsTransitionDef<T> | null>(null);
  const [sigValues, setSigValues] = useState<Record<string, string>>({});
  const [sigComplexValues, setSigComplexValues] = useState<Record<string, RepeatRow[] | KvRow[]>>({});
  const [createValues, setCreateValues] = useState<Record<string, string>>({});
  const [createComplexValues, setCreateComplexValues] = useState<Record<string, RepeatRow[] | KvRow[]>>({});
  const [createErr, setCreateErr] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

  async function load(target = id) {
    if (!target.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setRecord(await api.get<T>(`${config.apiRoot}/${target.trim()}`));
      setId(target.trim());
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
      setRecord(null);
    } finally {
      setLoading(false);
    }
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!config.create) return;
    setCreating(true);
    setCreateErr(null);
    try {
      const values = parseValues(config.create.fields, createValues, createComplexValues);
      const receipt = await api.post<MutationReceipt>(config.create.path, {
        idempotency_key: newIdempotencyKey(),
        ...config.create.buildBody(values, siteId),
      });
      setCreateValues({});
      setCreateComplexValues({});
      load(receipt.aggregate_id);
      onCreated?.();
      if (collapseCreate) setCreateOpen(false);
    } catch (err) {
      if (err instanceof SyntaxError) setCreateErr(`Invalid JSON: ${err.message}`);
      else setCreateErr(err instanceof ApiError ? `${err.code}: ${err.message}` : "Create failed");
    } finally {
      setCreating(false);
    }
  }

  const createForm = config.create && (
    <form onSubmit={create} className="grid grid-cols-2 gap-4 mt-3">
      <FieldInputs
        fields={config.create.fields}
        values={createValues}
        setValue={(n, v) => setCreateValues((c) => ({ ...c, [n]: v }))}
        complexValues={createComplexValues}
        setComplexValue={(n, v) => setCreateComplexValues((c) => ({ ...c, [n]: v }))}
      />
      <div style={{ gridColumn: "1 / -1" }}>
        {createErr && <p className="error-text mb-2">{createErr}</p>}
        <Button type="submit" variant="primary" disabled={creating}>
          {creating ? "Creating…" : config.create.label}
        </Button>
      </div>
    </form>
  );

  return (
    <div>
      <PageHead
        title={config.title}
        subtitle={config.subtitle}
        action={
          <>
            {headerAction}
            {collapseCreate && config.create && config.create.can(me) && (
              <Button variant="secondary" onClick={() => setCreateOpen(true)}>
                <Icon name="plus" /> {config.create.label}
              </Button>
            )}
          </>
        }
      />

      {typeof afterHeader === "function" ? afterHeader(load) : afterHeader}

      {!collapseCreate && config.create && !config.create.can(me) && (
        <Banner tone="info" title="Read-only">
                {config.create.label} needs additional access - the lookup below still works for everyone.
        </Banner>
      )}

      {!collapseCreate && config.create && config.create.can(me) && (
        <Card pad className="mb-4">
          <CardHeader title={config.create.label} />
          {createForm}
        </Card>
      )}

      {collapseCreate && createOpen && config.create && (
        <Modal open onClose={() => setCreateOpen(false)} title={config.create.label} large>
          {createForm}
        </Modal>
      )}

      {!hideLookup && (
        <Card pad className="mb-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              load();
            }}
            className="flex flex-wrap items-end gap-3"
          >
            <Field label={config.idLabel}>
              <Input value={id} onChange={(e) => setId(e.target.value)} style={{ minWidth: 200, maxWidth: 320, width: "100%" }} />
            </Field>
            <Button type="submit" variant="secondary" disabled={loading || !id.trim()}>
              <Icon name="search" /> {loading ? "Loading…" : "Open"}
            </Button>
          </form>
          {error && <p className="error-text mt-3">{error}</p>}
        </Card>
      )}

      {record && (() => {
        const inStateNow = config.transitions.filter((t) => (t.show ? t.show(record) : true));
        const visible = inStateNow.filter((t) => (t.can ? t.can(me) : true));
        // Distinguishes the two reasons a record can show zero actions -- "nothing is valid from this
        // state" (every transition's own `show` excluded it) vs "something's valid but this user's role
        // doesn't grant it" -- so the empty case reads as an explanation, not a dead end (this is
        // exactly the gap a `show: (r) => r.state === "X"` guard opened: hiding a wrong-state action is
        // right, but landing on a record with none available and no reason given looks like a bug).
        const hiddenByRole = inStateNow.length > 0 && visible.length === 0;
        const actions = visible.length > 0 ? (
          <div className="flex flex-wrap gap-2 mt-3">
            {visible.map((t) =>
              t.signed ? (
                <Button
                  key={t.key}
                  variant={t.variant ?? "secondary"}
                  onClick={() => {
                    setSigValues({});
                    setSigComplexValues({});
                    setSigTransition(t);
                  }}
                >
                  {t.label}
                </Button>
              ) : (
                <UnsignedTransition key={t.key} config={config} transition={t} record={record} onDone={() => load()} />
              )
            )}
          </div>
        ) : (
          <p className="hint mt-2">
            {hiddenByRole
              ? "Your role doesn't grant any action available on this record right now."
              : `No action is available while this record is in its "${config.stateOf(record)}" state.`}
          </p>
        );

        if (detailInModal) {
          return (
            <Modal
              open
              onClose={() => setRecord(null)}
              large
              title={
                <span className="flex items-center gap-3">
                  {config.numberOf(record)} <WorkflowStatePill state={config.stateOf(record)} />
                </span>
              }
            >
              <FactGrid>{config.facts(record)}</FactGrid>
              {config.extra?.(record)}
              <CardHeader title="Actions" />
              {actions}
            </Modal>
          );
        }

        return (
          <>
            <Card pad className="mb-4">
              <div className="flex justify-between items-center mb-3">
                <span className="font-semibold flex items-center gap-3">
                  {config.numberOf(record)} <WorkflowStatePill state={config.stateOf(record)} />
                </span>
              </div>
              <FactGrid>{config.facts(record)}</FactGrid>
            </Card>

            {config.extra?.(record)}

            <Card pad>
              <CardHeader title="Actions" />
              {actions}
            </Card>
          </>
        );
      })()}

      {record && sigTransition && (
        <SignatureCeremony
          open
          onClose={() => setSigTransition(null)}
          onDone={() => {
            setSigTransition(null);
            load();
          }}
          challengePath={`${config.apiRoot}/${record.id}/signature-challenges`}
          action={sigTransition.challengeAction ?? sigTransition.key}
          title={`${sigTransition.label} - ${config.numberOf(record)}`}
          summary={sigTransition.summary}
          submitVariant={sigTransition.variant === "danger" ? "danger" : sigTransition.variant === "success" ? "success" : "primary"}
          extraFields={
            sigTransition.fields && sigTransition.fields.length > 0 ? (
              <FieldInputs
                fields={sigTransition.fields}
                values={sigValues}
                setValue={(n, v) => setSigValues((c) => ({ ...c, [n]: v }))}
                complexValues={sigComplexValues}
                setComplexValue={(n, v) => setSigComplexValues((c) => ({ ...c, [n]: v }))}
              />
            ) : undefined
          }
          onSign={(p) => {
            const values = parseValues(sigTransition.fields ?? [], sigValues, sigComplexValues);
            return api.post<MutationReceipt>(
              `${config.apiRoot}/${record.id}/${sigTransition.pathSegment ?? sigTransition.key}`,
              {
                idempotency_key: p.idempotency_key,
                challenge_id: p.challenge_id,
                reauth_password: p.reauth_password,
                ...sigTransition.buildBody(record, values),
              }
            );
          }}
        />
      )}
    </div>
  );
}

function UnsignedTransition<T extends { id: string; version: number }>({
  config,
  transition,
  record,
  onDone,
}: {
  config: OpsRecordConfig<T>;
  transition: OpsTransitionDef<T>;
  record: T;
  onDone: () => void;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [complexValues, setComplexValues] = useState<Record<string, RepeatRow[] | KvRow[]>>({});
  return (
    <WorkflowActionButton
      label={transition.label}
      title={`${transition.label} - ${config.numberOf(record)}`}
      summary={transition.summary}
      confirmLabel={transition.label}
      variant={transition.variant ?? "secondary"}
      onDone={onDone}
      extraFields={
        transition.fields && transition.fields.length > 0 ? (
          <FieldInputs
            fields={transition.fields}
            values={values}
            setValue={(n, v) => setValues((c) => ({ ...c, [n]: v }))}
            complexValues={complexValues}
            setComplexValue={(n, v) => setComplexValues((c) => ({ ...c, [n]: v }))}
          />
        ) : undefined
      }
      onConfirm={() => {
        const parsed = parseValues(transition.fields ?? [], values, complexValues);
        return api.post<MutationReceipt>(`${config.apiRoot}/${record.id}/${transition.pathSegment ?? transition.key}`, {
          idempotency_key: newIdempotencyKey(),
          ...transition.buildBody(record, parsed),
        });
      }}
    />
  );
}

export { Fact, IdFact } from "@/components/ui/FactGrid";
