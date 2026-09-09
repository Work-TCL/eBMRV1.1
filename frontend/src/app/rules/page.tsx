"use client";

import { useState } from "react";
import { api, ApiError, newIdempotencyKey } from "@/lib/api";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { KeyValueRows, buildKvObject, type KvRow } from "@/components/shared/RepeatableFields";
import { JsonPanel, summarizeJson } from "@/components/ui/JsonPanel";
import {
  ExprNodeEditor,
  DEFAULT_EXPR,
  exprToAst,
  isExprComplete,
  referencedVars,
  type ExprNode,
} from "@/components/rules/ExpressionEditor";

// Matches app/modules/rules/router.py::_rule_dict.
interface RuleDefinition {
  rule_object_id: string;
  rule_id: string;
  rule_type: string;
  semantic_version: string;
  status: string;
  effective_from: string | null;
  effective_to: string | null;
  expression_ast: Record<string, unknown>;
  input_contract: Record<string, unknown>;
  output_contract: Record<string, unknown>;
  unit_policy: Record<string, unknown>;
  precision_policy: Record<string, unknown>;
  rounding_policy: Record<string, unknown>;
  released_vault_object_id: string | null;
}

const exprBoxStyle: React.CSSProperties = {
  border: "1px solid var(--border-hairline)",
  borderRadius: "var(--radius-2, 6px)",
  padding: "var(--space-3, 12px)",
};

export default function RulesPage() {
  const [ruleId, setRuleId] = useState("");
  const [versions, setVersions] = useState<RuleDefinition[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftOpen, setDraftOpen] = useState(false);
  const [selected, setSelected] = useState<RuleDefinition | null>(null);

  async function performLookup() {
    if (!ruleId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<RuleDefinition[]>(`/rules/v1/${encodeURIComponent(ruleId.trim())}/versions`);
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
        title="Rules"
        subtitle="Calculation and eligibility rules — draft, validate, simulate against test inputs, and release."
        action={
          <Button variant="primary" onClick={() => setDraftOpen(true)}>
            <Icon name="plus" /> New draft
          </Button>
        }
      />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          performLookup();
        }}
        className="flex flex-wrap items-end gap-4 mb-4"
      >
        <Field label="Rule ID">
          <Input value={ruleId} onChange={(e) => setRuleId(e.target.value)} placeholder="e.g. ASSAY-ELIGIBILITY" style={{ minWidth: 200, maxWidth: 260, width: "100%" }} />
        </Field>
        <Button type="submit" variant="secondary" disabled={loading || !ruleId.trim()}>
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
          <CardHeader title={ruleId} />
          {versions.length === 0 ? (
            <EmptyState icon="gauge">No versions exist for this rule ID yet.</EmptyState>
          ) : (
            <Table>
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Type</th>
                  <th>Effective</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {versions.map((r) => (
                  <tr key={r.rule_object_id}>
                    <td className="font-semibold tabular">{r.semantic_version}</td>
                    <td><WorkflowStatePill state={r.status} /></td>
                    <td>{r.rule_type}</td>
                    <td className="tabular fs-2">
                      {r.effective_from ? new Date(r.effective_from).toLocaleDateString() : "—"}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <Button size="sm" variant="secondary" onClick={() => setSelected(r)}>
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
          onDone={(newRuleId) => {
            setDraftOpen(false);
            setRuleId(newRuleId);
            performLookup();
          }}
        />
      )}

      {selected && (
        <RuleDetailModal
          rule={selected}
          onClose={() => setSelected(null)}
          onChanged={() => {
            setSelected(null);
            performLookup();
          }}
        />
      )}

      <div className="mt-6">
        <UomSection />
      </div>
    </div>
  );
}

// --- Units of measure (Document 08 "Units / Precision / Rounding") -------------------------------

interface Uom {
  uom_id: string;
  code: string;
  dimension: string;
  base_unit: string;
  factor: string;
  offset: string;
  precision_dp: number;
  status: string;
  version: number;
}

function UomSection() {
  const [code, setCode] = useState("");
  const [versions, setVersions] = useState<Uom[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [draftOpen, setDraftOpen] = useState(false);

  async function lookup() {
    if (!code.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setVersions(await api.get<Uom[]>(`/rules/v1/uom/${encodeURIComponent(code.trim())}/versions`));
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setUnavailable(true);
        setVersions(null);
      } else {
        setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
        setVersions(null);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Units of measure"
        meta={
          <Button size="sm" variant="secondary" onClick={() => setDraftOpen(true)}>
            <Icon name="plus" /> New UOM draft
          </Button>
        }
      />
      <div style={{ padding: "var(--space-3) var(--space-4)" }}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            lookup();
          }}
          className="flex flex-wrap items-end gap-4"
        >
          <Field label="UOM code">
            <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. mg, mL, %w/w" style={{ minWidth: 200, maxWidth: 220, width: "100%" }} />
          </Field>
          <Button type="submit" variant="secondary" disabled={loading || !code.trim()}>
            <Icon name="search" /> {loading ? "Looking up…" : "Look up versions"}
          </Button>
        </form>

        {error && <p className="error-text mt-3">{error}</p>}

        {unavailable && (
          <p className="hint mt-3">
            The unit-of-measure registry endpoints are not enabled in this deployment build.
          </p>
        )}

        {versions && !error && (
          <div className="mt-3">
            {versions.length === 0 ? (
              <EmptyState icon="scale">No versions exist for this UOM code yet.</EmptyState>
            ) : (
              <Table>
                <thead>
                  <tr>
                    <th>Version</th>
                    <th>Status</th>
                    <th>Dimension</th>
                    <th>Base unit</th>
                    <th>Factor</th>
                    <th>Offset</th>
                    <th>Precision</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((u) => (
                    <tr key={u.uom_id}>
                      <td className="font-semibold tabular">v{u.version}</td>
                      <td><WorkflowStatePill state={u.status} /></td>
                      <td>{u.dimension}</td>
                      <td className="tabular">{u.base_unit}</td>
                      <td className="tabular">{u.factor}</td>
                      <td className="tabular">{u.offset}</td>
                      <td className="tabular">{u.precision_dp}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </div>
        )}
      </div>

      {draftOpen && (
        <UomDraftModal
          onClose={() => setDraftOpen(false)}
          onDone={(newCode) => {
            setDraftOpen(false);
            setCode(newCode);
            setVersions(null);
          }}
        />
      )}
    </Card>
  );
}

function UomDraftModal({ onClose, onDone }: { onClose: () => void; onDone: (code: string) => void }) {
  const [code, setCode] = useState("");
  const [dimension, setDimension] = useState("mass");
  const [baseUnit, setBaseUnit] = useState("kg");
  const [factor, setFactor] = useState("1");
  const [offset, setOffset] = useState("0");
  const [precisionDp, setPrecisionDp] = useState("3");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/rules/v1/uom/drafts", {
        idempotency_key: newIdempotencyKey(),
        code: code.trim(),
        dimension: dimension.trim(),
        base_unit: baseUnit.trim(),
        factor: factor.trim(),
        offset: offset.trim(),
        precision_dp: Number(precisionDp),
      });
      onDone(code.trim());
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to create UOM draft");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="New unit of measure — draft">
      <form onSubmit={onSubmit}>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Code" required>
            <Input value={code} onChange={(e) => setCode(e.target.value)} required autoFocus />
          </Field>
          <Field label="Dimension" required>
            <Input value={dimension} onChange={(e) => setDimension(e.target.value)} required />
          </Field>
          <Field label="Base unit" required>
            <Input value={baseUnit} onChange={(e) => setBaseUnit(e.target.value)} required />
          </Field>
          <Field label="Factor" required hint="Multiplier to base unit (exact decimal string).">
            <Input value={factor} onChange={(e) => setFactor(e.target.value)} required />
          </Field>
          <Field label="Offset">
            <Input value={offset} onChange={(e) => setOffset(e.target.value)} />
          </Field>
          <Field label="Precision (dp)" required>
            <Input type="number" min={0} value={precisionDp} onChange={(e) => setPrecisionDp(e.target.value)} required />
          </Field>
        </div>
        {error && <p className="error-text mt-2">{error}</p>}
        <p className="hint mt-2 mb-3">
          Releasing a UOM needs a signature policy — this deployment hasn&apos;t defined yet — the draft is
          stored; release will correctly fail closed until one exists.
        </p>
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !code.trim()}>
            {busy ? "Creating…" : "Create draft"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// input_contract / output_contract are `{name: {type: "..."}}` maps — a name + type pair per row, not
// a fixed schema for what "type" values exist (the backend never validates that vocabulary, only that
// the keys used in expression_ast are declared), so type is a free-text field with common values
// offered as suggestions rather than a closed `select`.
interface ContractRow {
  name: string;
  type: string;
}
const CONTRACT_TYPE_SUGGESTIONS = ["decimal", "integer", "boolean", "string", "datetime"];

// app/modules/rules/precision.py CLASS_POLICY, transcribed — create_draft calls resolve_class_policy()
// unconditionally, so precision_policy.calculation_class is a real, code-enforced requirement (not a
// guessed schema), and CC-5 specifically requires reported_decimal_places. Never pre-selected: which
// class governs a rule is an authoring decision the operator makes, not a default this editor picks
// for them (AG-15 — "no regulated behavior guessed").
const CALCULATION_CLASSES = [
  { value: "CC-1", label: "CC-1 — Mass / weight capture (raw, instrument resolution)" },
  { value: "CC-2", label: "CC-2 — Volume capture (raw, as captured)" },
  { value: "CC-3", label: "CC-3 — Tolerance evaluation" },
  { value: "CC-4", label: "CC-4 — Yield / reconciliation" },
  { value: "CC-5", label: "CC-5 — Concentration / potency (needs reported decimal places)" },
  { value: "CC-6", label: "CC-6 — Count / units (exact equality)" },
  { value: "CC-7", label: "CC-7 — Time / duration" },
  { value: "CC-8", label: "CC-8 — Environmental" },
  { value: "CC-9", label: "CC-9 — Statistical / trending (advisory only, never a release decision by itself)" },
  { value: "CC-10", label: "CC-10 — Financial / commercial (not a GxP decision)" },
];

function buildContract(rows: ContractRow[]): Record<string, { type: string }> {
  const out: Record<string, { type: string }> = {};
  for (const r of rows) {
    const name = r.name.trim();
    if (!name) continue;
    out[name] = { type: r.type.trim() || "decimal" };
  }
  return out;
}

function ContractRows({
  label,
  hint,
  itemLabel,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  itemLabel: string;
  value: ContractRow[];
  onChange: (rows: ContractRow[]) => void;
}) {
  const listId = `contract-type-suggestions-${label.replace(/\s+/g, "-")}`;
  function update(i: number, patch: Partial<ContractRow>) {
    onChange(value.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }
  function remove(i: number) {
    onChange(value.filter((_, idx) => idx !== i));
  }
  return (
    <div className="field">
      <label className="label">{label}</label>
      {hint && <p className="hint mb-2">{hint}</p>}
      <datalist id={listId}>
        {CONTRACT_TYPE_SUGGESTIONS.map((t) => (
          <option key={t} value={t} />
        ))}
      </datalist>
      {value.map((row, i) => (
        <div key={i} className="flex flex-wrap gap-2 mb-2 items-center">
          <Input
            placeholder={`${itemLabel} name`}
            value={row.name}
            onChange={(e) => update(i, { name: e.target.value })}
            style={{ flex: "1 1 160px", minWidth: 0 }}
          />
          <Input
            placeholder="type"
            list={listId}
            value={row.type}
            onChange={(e) => update(i, { type: e.target.value })}
            style={{ flex: "1 1 140px", minWidth: 0 }}
          />
          <button type="button" style={{ background: "none", border: "none", padding: 0, cursor: "pointer" }} onClick={() => remove(i)} aria-label={`Remove ${itemLabel} ${i + 1}`}>
            <Icon name="x" />
          </button>
        </div>
      ))}
      <Button type="button" variant="secondary" size="sm" onClick={() => onChange([...value, { name: "", type: "" }])}>
        <Icon name="plus" /> Add {itemLabel.toLowerCase()}
      </Button>
    </div>
  );
}

function DraftModal({ onClose, onDone }: { onClose: () => void; onDone: (ruleId: string) => void }) {
  const [ruleId, setRuleId] = useState("");
  const [ruleType, setRuleType] = useState("eligibility");
  const [semanticVersion, setSemanticVersion] = useState("1.0.0");
  const [expr, setExpr] = useState<ExprNode>(DEFAULT_EXPR);
  const [inputRows, setInputRows] = useState<ContractRow[]>([{ name: "value", type: "decimal" }]);
  const [outputRows, setOutputRows] = useState<ContractRow[]>([{ name: "eligible", type: "boolean" }]);
  const [unitRows, setUnitRows] = useState<KvRow[]>([]);
  const [calculationClass, setCalculationClass] = useState("");
  const [reportedDecimalPlaces, setReportedDecimalPlaces] = useState("2");
  const [roundingRows, setRoundingRows] = useState<KvRow[]>([{ key: "mode", value: "half_up" }, { key: "places", value: "2" }]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const outputContract = buildContract(outputRows);
  const inputContract = buildContract(inputRows);
  const undeclared = referencedVars(expr).filter((name) => !(name in inputContract));
  const needsReportedDp = calculationClass === "CC-5";
  const precisionPolicy: Record<string, unknown> = calculationClass ? { calculation_class: calculationClass } : {};
  if (needsReportedDp && reportedDecimalPlaces.trim()) precisionPolicy.reported_decimal_places = Number(reportedDecimalPlaces);
  const canSubmit =
    ruleId.trim() &&
    isExprComplete(expr) &&
    Object.keys(outputContract).length > 0 &&
    undeclared.length === 0 &&
    !!calculationClass &&
    (!needsReportedDp || reportedDecimalPlaces.trim() !== "");

  const previewBody = {
    rule_id: ruleId,
    rule_type: ruleType,
    semantic_version: semanticVersion,
    expression_ast: exprToAst(expr),
    input_contract: inputContract,
    output_contract: outputContract,
    unit_policy: buildKvObject(unitRows),
    precision_policy: precisionPolicy,
    rounding_policy: buildKvObject(roundingRows),
  };

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/rules/v1/drafts", { idempotency_key: newIdempotencyKey(), ...previewBody });
      onDone(ruleId);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to create draft");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="New rule draft" large>
      <form onSubmit={onSubmit}>
        <div className="grid grid-cols-3 gap-4">
          <Field label="Rule ID" required>
            <Input value={ruleId} onChange={(e) => setRuleId(e.target.value)} required autoFocus />
          </Field>
          <Field label="Rule type" required>
            <Input value={ruleType} onChange={(e) => setRuleType(e.target.value)} required />
          </Field>
          <Field label="Semantic version" required>
            <Input value={semanticVersion} onChange={(e) => setSemanticVersion(e.target.value)} required />
          </Field>
        </div>

        <div className="mt-4">
          <label className="label">Expression</label>
          <p className="hint mb-2">The condition this rule evaluates — built from input variables, fixed values, comparisons and AND/OR groups.</p>
          <div style={{ ...exprBoxStyle, background: "var(--surface-sunken)" }}>
            <ExprNodeEditor node={expr} onChange={setExpr} />
          </div>
          {undeclared.length > 0 && (
            <p className="error-text mt-2">
              <Icon name="alert-circle" /> The expression uses input{undeclared.length > 1 ? "s" : ""} not declared below: {undeclared.join(", ")}.
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 mt-4">
          <ContractRows label="Input variables" itemLabel="Input" value={inputRows} onChange={setInputRows} hint="Every variable the expression above refers to." />
          <ContractRows label="Output" itemLabel="Output" hint="At least one — what this rule produces." value={outputRows} onChange={setOutputRows} />
        </div>

        <div className="grid grid-cols-3 gap-4 mt-4">
          <KeyValueRows label="Unit policy" hint="Optional — leave empty if this rule has no unit conversion." value={unitRows} onChange={setUnitRows} />
          <Field
            label="Calculation class"
            required
            hint="Which of the ten calculation classes governs this rule's comparison rounding."
          >
            <Select value={calculationClass} onChange={(e) => setCalculationClass(e.target.value)}>
 <option value="">Select</option>
              {CALCULATION_CLASSES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </Select>
            {needsReportedDp && (
              <div className="mt-2">
                <Field label="Reported decimal places" required hint="CC-5 requires a source-specified reported precision.">
                  <Input
                    type="number"
                    min={0}
                    value={reportedDecimalPlaces}
                    onChange={(e) => setReportedDecimalPlaces(e.target.value)}
                  />
                </Field>
              </div>
            )}
          </Field>
          <KeyValueRows label="Rounding policy" hint="Not currently enforced by the engine, but required and stored (fill in your own convention)." value={roundingRows} onChange={setRoundingRows} />
        </div>

        <details className="mt-4">
          <summary className="hint" style={{ cursor: "pointer" }}>Preview the exact request body</summary>
          <div className="mt-2">
            <JsonPanel title="Draft payload" value={previewBody} />
          </div>
        </details>

        {error && <p className="error-text mt-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !canSubmit}>
            {busy ? "Creating…" : "Create draft"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function RuleDetailModal({
  rule,
  onClose,
  onChanged,
}: {
  rule: RuleDefinition;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [testInputs, setTestInputs] = useState<KvRow[]>([]);
  const [simResult, setSimResult] = useState<unknown>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onValidate() {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/rules/v1/${rule.rule_object_id}/validate`, {
        idempotency_key: newIdempotencyKey(),
        rule_object_id: rule.rule_object_id,
      });
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Validation failed");
    } finally {
      setBusy(false);
    }
  }

  async function onSimulate() {
    setError(null);
    try {
      const inputs = buildKvObject(testInputs);
      const result = await api.post<{ result: unknown }>(`/rules/v1/${rule.rule_object_id}/simulate`, { inputs });
      setSimResult(result.result);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Simulation failed");
    }
  }

  async function onRelease() {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/rules/v1/${rule.rule_object_id}/release`, {
        idempotency_key: newIdempotencyKey(),
        rule_object_id: rule.rule_object_id,
      });
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Release failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={`${rule.rule_id} v${rule.semantic_version}`} large>
      <p className="fs-2 mb-3 flex items-center gap-2">
        Status: <WorkflowStatePill state={rule.status} />
      </p>

      <JsonPanel title="Expression" value={rule.expression_ast} />

      {rule.status === "draft" && (
        <p className="hint mt-3 mb-3">Validate the draft before it can be released.</p>
      )}

      {(rule.status === "draft" || rule.status === "validated") && (
        <div className="mt-4">
          <KeyValueRows
 label="Simulate test inputs"
            hint="The values to test this rule with. Never writes regulated state (RUL-FR-023)."
            value={testInputs}
            onChange={setTestInputs}
          />
          <Button size="sm" variant="secondary" onClick={onSimulate}>
            Simulate
          </Button>
          {simResult !== undefined && (
            <p className="fs-2 mt-2">
              Result: <strong>{summarizeJson(simResult)}</strong>
            </p>
          )}
        </div>
      )}

      {error && <p className="error-text mt-3">{error}</p>}

      <div className="flex justify-between gap-3 mt-4">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        <div className="flex gap-2">
          {rule.status === "draft" && (
            <Button variant="primary" onClick={onValidate} disabled={busy}>
              {busy ? "Validating…" : "Validate"}
            </Button>
          )}
          {rule.status === "validated" && (
            <Button variant="success" onClick={onRelease} disabled={busy}>
              {busy ? "Releasing…" : "Release"}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
