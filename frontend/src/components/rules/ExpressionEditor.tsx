"use client";

import type { CSSProperties } from "react";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

/**
 * A structured editor for `expression_ast` (Document 08 / RUL-FR-005) — the one genuinely recursive
 * payload in the rules module. The grammar below is transcribed exactly from
 * `app/modules/rules/expression.py::evaluate()` (the only place that interprets this JSON, so it is the
 * one source of truth for what's a legal node) — not guessed:
 *
 *   - `{"var": "name"}`                                 — a declared input lookup
 *   - a literal: string | boolean | null | number-as-string (never a JS float — AG-15)
 *   - `{"op": "not", "args": [node]}`                    — exactly one argument
 *   - `{"op": "and" | "or", "args": [node, ...]}`        — at least one argument
 *   - `{"op": "eq"|"ne"|"gt"|"gte"|"lt"|"lte", "args": [node, node]}`   — exactly two
 *   - `{"op": "+"|"-"|"*"|"/", "args": [node, node]}`    — exactly two
 *
 * `ExprNode` is the UI-friendly tree; `parseExpr`/`exprToAst` are the only two places that cross the
 * boundary to/from the wire shape, so the rest of the editor never has to think about raw JSON.
 */

export type ExprNode =
  | { kind: "var"; name: string }
  | { kind: "literal"; litType: "string" | "number" | "bool" | "null"; value: string }
  | { kind: "not"; arg: ExprNode }
  | { kind: "bool"; op: "and" | "or"; args: ExprNode[] }
  | { kind: "compare"; op: "eq" | "ne" | "gt" | "gte" | "lt" | "lte"; left: ExprNode; right: ExprNode }
  | { kind: "arith"; op: "+" | "-" | "*" | "/"; left: ExprNode; right: ExprNode };

const COMPARE_OPS: { value: "eq" | "ne" | "gt" | "gte" | "lt" | "lte"; label: string }[] = [
  { value: "eq", label: "= (equals)" },
  { value: "ne", label: "≠ (not equals)" },
  { value: "gt", label: "> (greater than)" },
  { value: "gte", label: "≥ (greater or equal)" },
  { value: "lt", label: "< (less than)" },
  { value: "lte", label: "≤ (less or equal)" },
];
const ARITH_OPS: { value: "+" | "-" | "*" | "/"; label: string }[] = [
  { value: "+", label: "+ (add)" },
  { value: "-", label: "− (subtract)" },
  { value: "*", label: "× (multiply)" },
  { value: "/", label: "÷ (divide)" },
];

function blankVar(): ExprNode {
  return { kind: "var", name: "" };
}

/** Default sub-tree used when a node's kind is switched — always the smallest legal shape for the new
 * kind, built from fresh blank variables/literals rather than trying to reinterpret the old node. */
export function defaultNodeFor(kind: ExprNode["kind"]): ExprNode {
  switch (kind) {
    case "var":
      return blankVar();
    case "literal":
      return { kind: "literal", litType: "string", value: "" };
    case "not":
      return { kind: "not", arg: blankVar() };
    case "bool":
      return { kind: "bool", op: "and", args: [blankVar()] };
    case "compare":
      return { kind: "compare", op: "gte", left: blankVar(), right: { kind: "literal", litType: "number", value: "0" } };
    case "arith":
      return { kind: "arith", op: "+", left: blankVar(), right: { kind: "literal", litType: "number", value: "0" } };
  }
}

export const DEFAULT_EXPR: ExprNode = {
  kind: "compare",
  op: "gte",
  left: { kind: "var", name: "value" },
  right: { kind: "literal", litType: "number", value: "0" },
};

const COMPARE_OP_SET = new Set(["eq", "ne", "gt", "gte", "lt", "lte"]);
const ARITH_OP_SET = new Set(["+", "-", "*", "/"]);

/** Wire JSON → `ExprNode`. Anything that doesn't match the grammar above (a rule created outside this
 * editor, or hand-edited) falls back to a blank variable rather than throwing — the editor should never
 * crash on real data, it should just show something the operator can fix. */
export function parseExpr(node: unknown): ExprNode {
  if (node === null) return { kind: "literal", litType: "null", value: "" };
  if (typeof node === "boolean") return { kind: "literal", litType: "bool", value: String(node) };
  if (typeof node === "string") return { kind: "literal", litType: "string", value: node };
  if (typeof node === "number") return { kind: "literal", litType: "number", value: String(node) };
  if (typeof node === "object" && node !== null) {
    const obj = node as Record<string, unknown>;
    if (typeof obj.var === "string") return { kind: "var", name: obj.var };
    if (typeof obj.op === "string") {
      const args = Array.isArray(obj.args) ? obj.args : [];
      if (obj.op === "not") return { kind: "not", arg: parseExpr(args[0]) };
      if (obj.op === "and" || obj.op === "or") return { kind: "bool", op: obj.op, args: args.length ? args.map(parseExpr) : [blankVar()] };
      if (COMPARE_OP_SET.has(obj.op)) {
        return { kind: "compare", op: obj.op as "eq" | "ne" | "gt" | "gte" | "lt" | "lte", left: parseExpr(args[0]), right: parseExpr(args[1]) };
      }
      if (ARITH_OP_SET.has(obj.op)) {
        return { kind: "arith", op: obj.op as "+" | "-" | "*" | "/", left: parseExpr(args[0]), right: parseExpr(args[1]) };
      }
    }
  }
  return blankVar();
}

/** `ExprNode` → the exact wire JSON `expression.py::evaluate()` expects. A "number" literal is always
 * emitted as a string — Decimal(str) and Decimal(int) evaluate identically, and a string can never
 * silently become a binary float the way a JS number literal could (AG-15 / DATA-FR-019). */
export function exprToAst(node: ExprNode): unknown {
  switch (node.kind) {
    case "var":
      return { var: node.name.trim() };
    case "literal":
      switch (node.litType) {
        case "string":
          return node.value;
        case "number":
          return node.value.trim();
        case "bool":
          return node.value === "true";
        case "null":
          return null;
      }
      break;
    case "not":
      return { op: "not", args: [exprToAst(node.arg)] };
    case "bool":
      return { op: node.op, args: node.args.map(exprToAst) };
    case "compare":
      return { op: node.op, args: [exprToAst(node.left), exprToAst(node.right)] };
    case "arith":
      return { op: node.op, args: [exprToAst(node.left), exprToAst(node.right)] };
  }
}

/** Every `{"var": ...}` name referenced anywhere in the tree — mirrors
 * `expression.py::referenced_variables()` so the editor can warn about an input the expression uses but
 * `input_contract` never declares, before the backend's own `validate_rule` would reject it. */
export function referencedVars(node: ExprNode): string[] {
  const found = new Set<string>();
  function walk(n: ExprNode) {
    if (n.kind === "var") {
      if (n.name.trim()) found.add(n.name.trim());
    } else if (n.kind === "literal") {
      // no children
    } else if (n.kind === "not") {
      walk(n.arg);
    } else if (n.kind === "bool") {
      n.args.forEach(walk);
    } else {
      walk(n.left);
      walk(n.right);
    }
  }
  walk(node);
  return Array.from(found);
}

/** True once every node in the tree is fully filled in (no blank variable name, no blank literal value
 * where one is meaningful) — gates the parent form's submit button the same way `isFormComplete` does
 * for DDCP's flat fields. */
export function isExprComplete(node: ExprNode): boolean {
  switch (node.kind) {
    case "var":
      return node.name.trim() !== "";
    case "literal":
      return node.litType === "null" || node.litType === "bool" || node.value.trim() !== "";
    case "not":
      return isExprComplete(node.arg);
    case "bool":
      return node.args.length > 0 && node.args.every(isExprComplete);
    case "compare":
    case "arith":
      return isExprComplete(node.left) && isExprComplete(node.right);
  }
}

const boxStyle: CSSProperties = {
  border: "1px solid var(--border-hairline)",
  borderRadius: "var(--radius-2, 6px)",
  padding: "var(--space-3, 12px)",
  background: "var(--surface-sunken)",
};
const rowStyle: CSSProperties = { display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8 };
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

const KIND_OPTIONS: { value: ExprNode["kind"]; label: string }[] = [
  { value: "var", label: "Input variable" },
  { value: "literal", label: "Fixed value" },
  { value: "compare", label: "Compare (=, >, <, …)" },
  { value: "arith", label: "Arithmetic (+, −, ×, ÷)" },
  { value: "bool", label: "AND / OR group" },
  { value: "not", label: "NOT" },
];

/** One node of the tree, and (for compare/arith/not/bool) its children — recursing into itself for
 * however deep the expression actually nests, same "the real shape, not a JSON approximation of it"
 * principle as the DDCP field editors. */
export function ExprNodeEditor({ node, onChange, depth = 0 }: { node: ExprNode; onChange: (next: ExprNode) => void; depth?: number }) {
  function changeKind(kind: ExprNode["kind"]) {
    if (kind === node.kind) return;
    onChange(defaultNodeFor(kind));
  }

  const kindSelector = (
    <Select value={node.kind} onChange={(e) => changeKind(e.target.value as ExprNode["kind"])} style={{ minWidth: 170 }}>
      {KIND_OPTIONS.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </Select>
  );

  if (node.kind === "var") {
    return (
      <div style={rowStyle}>
        {kindSelector}
        <Input
          value={node.name}
          onChange={(e) => onChange({ ...node, name: e.target.value })}
          placeholder="input name, e.g. value"
          style={{ flex: "1 1 160px", minWidth: 0 }}
        />
      </div>
    );
  }

  if (node.kind === "literal") {
    return (
      <div style={rowStyle}>
        {kindSelector}
        <Select
          value={node.litType}
          onChange={(e) => {
            const litType = e.target.value as "string" | "number" | "bool" | "null";
            onChange({ kind: "literal", litType, value: litType === "bool" ? "true" : "" });
          }}
          style={{ minWidth: 110 }}
        >
          <option value="string">Text</option>
          <option value="number">Number</option>
          <option value="bool">Yes / No</option>
 <option value="null">(none)</option>
        </Select>
        {node.litType === "bool" ? (
          <Select value={node.value} onChange={(e) => onChange({ ...node, value: e.target.value })} style={{ minWidth: 100 }}>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </Select>
        ) : node.litType === "null" ? (
          <span className="hint">No value.</span>
        ) : (
          <Input
            type="text"
            inputMode={node.litType === "number" ? "decimal" : undefined}
            value={node.value}
            onChange={(e) => onChange({ ...node, value: e.target.value })}
            placeholder={node.litType === "number" ? "0.000000" : "text"}
            style={{ flex: "1 1 140px", minWidth: 0 }}
          />
        )}
      </div>
    );
  }

  if (node.kind === "not") {
    return (
      <div>
 <div style={rowStyle}>{kindSelector}<span className="hint">true when the value below is false.</span></div>
        <div style={{ ...boxStyle, marginTop: 8, marginLeft: 20 }}>
          <ExprNodeEditor node={node.arg} onChange={(arg) => onChange({ ...node, arg })} depth={depth + 1} />
        </div>
      </div>
    );
  }

  if (node.kind === "bool") {
    // Aliased into a `const` — a nested function declaration capturing the narrowed `node` param
    // directly loses TypeScript's narrowing (it can't prove the closure only runs while still in this
    // branch), so every reference below goes through `boolNode` instead.
    const boolNode = node;
    function updateArg(i: number, next: ExprNode) {
      onChange({ ...boolNode, args: boolNode.args.map((a, idx) => (idx === i ? next : a)) });
    }
    function removeArg(i: number) {
      const args = boolNode.args.filter((_, idx) => idx !== i);
      onChange({ ...boolNode, args: args.length ? args : [blankVar()] });
    }
    return (
      <div>
        <div style={rowStyle}>
          {kindSelector}
          <Select value={boolNode.op} onChange={(e) => onChange({ ...boolNode, op: e.target.value as "and" | "or" })} style={{ minWidth: 100 }}>
            <option value="and">All must be true (AND)</option>
            <option value="or">Any must be true (OR)</option>
          </Select>
        </div>
        <div style={{ marginLeft: 20, marginTop: 8, display: "flex", flexDirection: "column", gap: 8 }}>
          {boolNode.args.map((arg, i) => (
            <div key={i} style={boxStyle}>
              <div className="flex items-center justify-between mb-2">
                <span className="fs-2 font-semibold text-muted">Condition {i + 1}</span>
                {boolNode.args.length > 1 && (
                  <button type="button" style={linkBtnStyle} onClick={() => removeArg(i)} aria-label={`Remove condition ${i + 1}`}>
                    <Icon name="x" /> Remove
                  </button>
                )}
              </div>
              <ExprNodeEditor node={arg} onChange={(next) => updateArg(i, next)} depth={depth + 1} />
            </div>
          ))}
          <Button type="button" variant="secondary" size="sm" onClick={() => onChange({ ...boolNode, args: [...boolNode.args, blankVar()] })}>
            <Icon name="plus" /> Add condition
          </Button>
        </div>
      </div>
    );
  }

  // compare / arith — both exactly two children, an operator between them. Aliased for the same
  // narrowing reason as `boolNode` above (safe here too, even though this branch has no nested function
  // declarations — keeps the rule uniform rather than relying on the arrow-function exception).
  const binNode = node;
  const ops = binNode.kind === "compare" ? COMPARE_OPS : ARITH_OPS;
  return (
    <div>
      <div style={rowStyle}>
        {kindSelector}
        <Select
          value={binNode.op}
          onChange={(e) => onChange({ ...binNode, op: e.target.value } as ExprNode)}
          style={{ minWidth: 170 }}
        >
          {ops.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
      </div>
      <div className="grid grid-cols-2 gap-3" style={{ marginTop: 8, marginLeft: 20 }}>
        <div style={boxStyle}>
          <p className="fs-2 font-semibold text-muted mb-2">Left side</p>
          <ExprNodeEditor node={binNode.left} onChange={(left) => onChange({ ...binNode, left } as ExprNode)} depth={depth + 1} />
        </div>
        <div style={boxStyle}>
          <p className="fs-2 font-semibold text-muted mb-2">Right side</p>
          <ExprNodeEditor node={binNode.right} onChange={(right) => onChange({ ...binNode, right } as ExprNode)} depth={depth + 1} />
        </div>
      </div>
    </div>
  );
}
