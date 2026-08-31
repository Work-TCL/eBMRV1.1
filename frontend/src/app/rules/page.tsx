"use client";

import { useState } from "react";
import { api, ApiError, newIdempotencyKey } from "@/lib/api";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, EmptyState } from "@/components/ui/Table";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

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

const DRAFT_TEMPLATE = {
  expression_ast: { op: "gte", args: [{ var: "value" }, "0"] },
  input_contract: { value: { type: "decimal" } },
  output_contract: { eligible: { type: "boolean" } },
  unit_policy: {},
  precision_policy: { mode: "explicit", value: 2 },
  rounding_policy: { mode: "half_up", places: 2 },
};

const textareaStyle: React.CSSProperties = { fontFamily: "var(--font-mono, monospace)", fontSize: "var(--fs-1)" };

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
        className="flex items-end gap-4 mb-4"
      >
        <Field label="Rule ID">
          <Input value={ruleId} onChange={(e) => setRuleId(e.target.value)} placeholder="e.g. ASSAY-ELIGIBILITY" style={{ minWidth: 260 }} />
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
            <EmptyState icon="gauge">No versions exist for this rule_id yet.</EmptyState>
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
                    <td>{r.status}</td>
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
    </div>
  );
}

function DraftModal({ onClose, onDone }: { onClose: () => void; onDone: (ruleId: string) => void }) {
  const [ruleId, setRuleId] = useState("");
  const [ruleType, setRuleType] = useState("eligibility");
  const [semanticVersion, setSemanticVersion] = useState("1.0.0");
  const [json, setJson] = useState(JSON.stringify(DRAFT_TEMPLATE, null, 2));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const parsed = JSON.parse(json);
      await api.post("/rules/v1/drafts", {
        idempotency_key: newIdempotencyKey(),
        rule_id: ruleId,
        rule_type: ruleType,
        semantic_version: semanticVersion,
        expression_ast: parsed.expression_ast,
        input_contract: parsed.input_contract,
        output_contract: parsed.output_contract,
        unit_policy: parsed.unit_policy,
        precision_policy: parsed.precision_policy,
        rounding_policy: parsed.rounding_policy,
      });
      onDone(ruleId);
    } catch (err) {
      if (err instanceof SyntaxError) setError("Invalid JSON: " + err.message);
      else setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Failed to create draft");
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
        <Field
          label="Contract & expression (JSON)"
          required
          error={error}
          hint="expression_ast/input_contract/output_contract/unit_policy/precision_policy/rounding_policy — all required (Document 08 requires an explicit numeric policy per rule, never a guessed default)."
        >
          <textarea
            className="input"
            rows={16}
            style={textareaStyle}
            value={json}
            onChange={(e) => setJson(e.target.value)}
            spellCheck={false}
          />
        </Field>
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !ruleId.trim()}>
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
  const [testInputs, setTestInputs] = useState('{\n  \n}');
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
      const inputs = JSON.parse(testInputs);
      const result = await api.post<{ result: unknown }>(`/rules/v1/${rule.rule_object_id}/simulate`, { inputs });
      setSimResult(result.result);
    } catch (err) {
      if (err instanceof SyntaxError) setError("Invalid JSON inputs: " + err.message);
      else setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Simulation failed");
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

  const preStyle: React.CSSProperties = {
    background: "var(--surface-sunken)",
    border: "1px solid var(--border-hairline)",
    borderRadius: "var(--radius-2, 6px)",
    padding: "var(--space-2, 8px)",
    fontSize: "var(--fs-1)",
    overflowX: "auto",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  };

  return (
    <Modal open onClose={onClose} title={`${rule.rule_id} v${rule.semantic_version}`} large>
      <p className="fs-2 mb-3">
        Status: <strong>{rule.status}</strong>
      </p>

      <p className="fs-1 text-muted mb-1">Expression</p>
      <pre style={preStyle}>{JSON.stringify(rule.expression_ast, null, 2)}</pre>

      {rule.status === "draft" && (
        <p className="hint mt-3 mb-3">Validate the draft before it can be released.</p>
      )}

      {(rule.status === "draft" || rule.status === "validated") && (
        <div className="mt-4">
          <Field label="Simulate — test inputs (JSON)" hint="Never writes regulated state (RUL-FR-023).">
            <textarea
              className="input"
              rows={4}
              style={textareaStyle}
              value={testInputs}
              onChange={(e) => setTestInputs(e.target.value)}
              spellCheck={false}
            />
          </Field>
          <Button size="sm" variant="secondary" onClick={onSimulate}>
            Simulate
          </Button>
          {simResult !== undefined && (
            <p className="fs-2 mt-2">
              Result: <strong>{JSON.stringify(simResult)}</strong>
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
