#!/usr/bin/env python3
"""Architecture guardrail lint for docs/generated/34_ARCHITECTURE_GUARDRAIL_MATRIX.md.

Codifies, as static AST checks over `services/gxp-api/app/`, the four guardrails named in the Phase 2
backbone ratchet (PHASE_2_BACKBONE.md Sec 4 item 6). Each maps to a row of the guardrail matrix and to a
CLAUDE.md Sec 9 hard prohibition:

  no-cross-module-write
      AG-05 / AG-06. A module may freely *read* another module's ORM model -- `select()`/join/existence
      lookups are pervasive and legitimate (156 cross-module model imports exist in app/modules/ today,
      all read-only) -- but it must never construct and `session.add()` another module's model instance.
      That write belongs to the owning module's own command, which is the only place that carries the
      audit/outbox/version discipline for that aggregate. Also flags `sqlalchemy.update(ForeignModel)` /
      `sqlalchemy.delete(ForeignModel)` Core statements against a non-owned table (none exist yet --
      this codebase uses ORM instance mutation exclusively -- but the check is ready for when one does).

  no-set-value-equivalent
      AG-06 / CLAUDE.md Sec 9 "No frappe.db.set_value() (or equivalent) on regulated data." Three shapes:
      the literal `frappe.db.set_value(...)` call (this codebase does not use Frappe for the GxP core --
      checked for completeness and to catch a future regression); a raw textual SQL UPDATE/DELETE passed
      to `text(...)` (bypasses the ORM's version/audit discipline entirely); and the live equivalent that
      actually appears in Python codebases -- `setattr(obj, field, value)` where `field` is the loop
      variable of a `for field, value in payload.items():` scan, i.e. "copy every externally-provided key
      onto the record" without per-field validation. A handful of *bounded*, closed-vocabulary
      `setattr()` calls already exist in app/ (e.g. selecting one of two named audit-timestamp fields
      from an internal, non-payload-derived variable) and are deliberately not flagged -- only the
      dynamic loop-over-a-dict shape is, since that is the shape with no per-field validation.

  no-generic-crud-endpoint
      AG-06 / CLAUDE.md Sec 9 "No generic CRUD or PATCH /regulated-record/{id} style endpoint." A
      PUT/PATCH/DELETE route on a regulated resource must accept a typed `*Command` parameter (the
      Mutation Gateway envelope: schema, idempotency key, expected_version where applicable) rather than
      an untyped/dict body -- the distinguishing feature between "REST-shaped URL that dispatches a
      validated command" (allowed; this codebase uses that shape on 8 existing routes across
      material/product/recipe/*_master) and "generic CRUD" (forbidden). A route with no typed Command
      parameter is flagged.

  no-bus-publish-without-outbox
      AG-09 / CLAUDE.md Sec 9 "No publishing to the bus without a committed outbox row." Only the
      eventbus module's own outbox publisher (`app/modules/eventbus/outbox.py`) and its caller
      (`app/main.py`, the background publisher loop) may call `publish_outbox_event`. Every other module
      must go through `write_outbox_event` (`app/mutation/gateway.py`), which writes the outbox row in
      the same PostgreSQL transaction as the domain state and audit event (MUT-FR-015/018).

  no-float-for-decimal-column
      ADR-0007 / Doc 110 CALC-FR-001 / CLAUDE.md Sec 9 "No binary float for a regulated quantity." Full
      generality (any `float` field anywhere) can't be told apart statically from the pervasive, legitimate
      use of `float` for engineering timing/duration values (`retry_after_seconds`, `timeout_seconds` and
      similar, all through `app/modules/erp/reliability.py` and friends) -- so this check is deliberately
      narrower and has zero false-positive risk: it flags only an ORM column whose *database* type is
      explicitly `Numeric`/`DECIMAL` (the author's own declared intent: exact decimal storage) but whose
      Python-side `Mapped[...]` annotation says `float` instead of `Decimal`. That exact, internally
      self-contradictory shape found one real bug in app/ (`qms.NcrDisposition.quantity`, fixed in the
      same commit this check was added) -- SQLAlchemy hands the application a lossy binary float on every
      read despite the column being stored as an exact decimal, silently defeating DATA-FR-019 downstream
      of the DB layer.

Exit code 0 when clean, 1 otherwise. Findings are evidence: this script reports what it sees.

SCOPE NOTE (disclosed, not a silent limitation): these are static, syntax-level AST checks, not a full
type/data-flow analysis. They cannot see through indirection (e.g. a model class re-exported under a new
name three modules away, or a real NATS client wrapped behind a same-named `publish` method introduced
later for the ADR-0011 broker migration -- when that lands, this file's no-bus-publish-without-outbox
check needs a matching second pattern). They check `services/gxp-api/app/` only -- `scripts/` (seed/dev
tooling, not the regulated runtime path) and `tests/` are out of scope by design, matching the scope note
in tooling/events/validate.py.

Usage:
    python3 tooling/guardrails/validate.py [--json]
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "services" / "gxp-api" / "app"
MODULES_ROOT = APP_ROOT / "modules"

# Files allowed to call the real outbox publisher, relative to the app root they live under.
OUTBOX_PUBLISHER_ALLOWLIST_RELPATHS = {
    Path("modules/eventbus/outbox.py"),
    Path("modules/eventbus/replay.py"),
    Path("main.py"),
}

# Files allowed a raw SQL UPDATE/DELETE via text(), relative to the app root -- PG-FR-008's one
# canonical conditional `UPDATE ... WHERE version = :expected` optimistic-concurrency helper needs
# atomic row-count-assertion semantics the ORM's load-then-flush pattern cannot express; it is the
# version-checking discipline done correctly, not a bypass of it. Any other file hitting this check is a
# genuine finding.
RAW_SQL_ALLOWLIST_RELPATHS = {
    Path("modules/dbops/concurrency.py"),
}


class Findings:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, rule: str, file: str, line: int, message: str) -> None:
        self.items.append({"rule": rule, "file": file, "line": line, "message": message})


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(), filename=str(path))
    except SyntaxError:
        return None


def _module_name(path: Path, modules_root: Path) -> str | None:
    try:
        rel = path.relative_to(modules_root)
    except ValueError:
        return None
    return rel.parts[0] if rel.parts else None


def _relpath(path: Path, app_root: Path) -> str:
    try:
        return str(path.relative_to(app_root.parent))
    except ValueError:
        return str(path)


# ---- check A: no-cross-module-write -------------------------------------------------------------------


def _owning_module_by_class(files: list[Path], modules_root: Path) -> dict[str, str]:
    """Map ORM model class name -> the one module that defines it. A class name defined identically in
    two modules is dropped from the map (ambiguous ownership -- not flagged either way rather than
    guessed)."""
    owner: dict[str, str] = {}
    ambiguous: set[str] = set()
    for f in files:
        if f.name != "models.py" and not f.name.endswith("_models.py"):
            continue
        mod = _module_name(f, modules_root)
        if mod is None:
            continue
        tree = _parse(f)
        if tree is None:
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                if node.name in owner and owner[node.name] != mod:
                    ambiguous.add(node.name)
                owner[node.name] = mod
    for name in ambiguous:
        owner.pop(name, None)
    return owner


def check_no_cross_module_write(findings: Findings, files: list[Path], modules_root: Path, app_root: Path) -> None:
    owner = _owning_module_by_class(files, modules_root)

    for f in files:
        if f.name == "models.py" or f.name.endswith("_models.py"):
            continue
        mod = _module_name(f, modules_root)
        if mod is None:
            continue
        tree = _parse(f)
        if tree is None:
            continue

        # local alias -> (owning_module, class_name), for names imported from a *different* module's
        # models file
        imported: dict[str, tuple[str, str]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.modules."):
                parts = node.module.split(".")
                if len(parts) < 3 or (parts[-1] != "models" and not parts[-1].endswith("_models")):
                    continue
                owning_mod = parts[2]
                if owning_mod == mod:
                    continue
                for alias in node.names:
                    local = alias.asname or alias.name
                    if owner.get(alias.name) == owning_mod:
                        imported[local] = (owning_mod, alias.name)
        if not imported:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            # session.add(ForeignModel(...)) / session.add_all([ForeignModel(...), ...])
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("add", "add_all"):
                ctor_calls = []
                for arg in node.args:
                    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
                        ctor_calls.append(arg)
                    elif isinstance(arg, (ast.List, ast.Tuple)):
                        ctor_calls.extend(
                            e for e in arg.elts if isinstance(e, ast.Call) and isinstance(e.func, ast.Name)
                        )
                for ctor in ctor_calls:
                    fname = ctor.func.id  # type: ignore[union-attr]
                    if fname in imported:
                        owning_mod, cls = imported[fname]
                        findings.add(
                            "no-cross-module-write",
                            _relpath(f, app_root),
                            node.lineno,
                            f"module '{mod}' constructs and session.add()s '{owning_mod}.{cls}' directly -- "
                            f"that write belongs in {owning_mod}'s own command/service.",
                        )
            # sqlalchemy Core update(ForeignModel) / delete(ForeignModel)
            elif isinstance(node.func, ast.Name) and node.func.id in ("update", "delete") and node.args:
                target = node.args[0]
                if isinstance(target, ast.Name) and target.id in imported:
                    owning_mod, cls = imported[target.id]
                    findings.add(
                        "no-cross-module-write",
                        _relpath(f, app_root),
                        node.lineno,
                        f"module '{mod}' issues a Core {node.func.id}() against '{owning_mod}.{cls}' "
                        f"directly -- that write belongs in {owning_mod}'s own command/service.",
                    )


# ---- check B: no-set-value-equivalent ------------------------------------------------------------------


def _call_chain(func: ast.expr) -> list[str]:
    """Render `a.b.c` as ['a', 'b', 'c']; anything else as []."""
    parts: list[str] = []
    node = func
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return list(reversed(parts))
    return []


def _const_str_contains_write(node: ast.expr) -> bool:
    text = ""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        text = node.value
    elif isinstance(node, ast.JoinedStr):
        text = "".join(v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str))
    upper = text.upper()
    return "UPDATE " in upper or "DELETE FROM " in upper


def check_no_set_value_equivalent(findings: Findings, files: list[Path], modules_root: Path, app_root: Path) -> None:
    for f in files:
        try:
            rel_to_app = f.relative_to(app_root)
        except ValueError:
            rel_to_app = None
        raw_sql_exempt = rel_to_app in RAW_SQL_ALLOWLIST_RELPATHS

        tree = _parse(f)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                chain = _call_chain(node.func)
                if chain == ["frappe", "db", "set_value"]:
                    findings.add(
                        "no-set-value-equivalent",
                        _relpath(f, app_root),
                        node.lineno,
                        "frappe.db.set_value() bypasses the Mutation Gateway (CLAUDE.md Sec 9).",
                    )
                elif (
                    not raw_sql_exempt
                    and chain
                    and chain[-1] == "text"
                    and node.args
                    and _const_str_contains_write(node.args[0])
                ):
                    findings.add(
                        "no-set-value-equivalent",
                        _relpath(f, app_root),
                        node.lineno,
                        "raw SQL UPDATE/DELETE via text() bypasses the ORM version/audit discipline.",
                    )

            if isinstance(node, ast.For):
                iter_node = node.iter
                is_items_loop = (
                    isinstance(iter_node, ast.Call)
                    and isinstance(iter_node.func, ast.Attribute)
                    and iter_node.func.attr in ("items", "keys")
                )
                if not is_items_loop:
                    continue
                key_names: set[str] = set()
                if isinstance(node.target, ast.Name):
                    key_names.add(node.target.id)
                elif isinstance(node.target, ast.Tuple) and node.target.elts:
                    first = node.target.elts[0]
                    if isinstance(first, ast.Name):
                        key_names.add(first.id)
                if not key_names:
                    continue
                for sub in ast.walk(node):
                    if (
                        isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Name)
                        and sub.func.id == "setattr"
                        and len(sub.args) >= 2
                    ):
                        field_arg = sub.args[1]
                        if isinstance(field_arg, ast.Name) and field_arg.id in key_names:
                            findings.add(
                                "no-set-value-equivalent",
                                _relpath(f, app_root),
                                sub.lineno,
                                "setattr() with a field name taken from a dict .items()/.keys() loop -- "
                                "copies every provided field onto the record with no per-field validation.",
                            )


# ---- check C: no-generic-crud-endpoint -----------------------------------------------------------------


def _annotation_name(ann: ast.expr | None) -> str | None:
    if ann is None:
        return None
    if isinstance(ann, ast.Name):
        return ann.id
    if isinstance(ann, ast.Attribute):
        return ann.attr
    return None


def check_no_generic_crud_endpoint(findings: Findings, files: list[Path], modules_root: Path, app_root: Path) -> None:
    for f in files:
        if f.name != "router.py" and not f.name.endswith("_router.py"):
            continue
        tree = _parse(f)
        if tree is None:
            continue

        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                if not (isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)):
                    continue
                if deco.func.attr not in ("put", "patch", "delete"):
                    continue
                if not (isinstance(deco.func.value, ast.Name) and deco.func.value.id == "router"):
                    continue
                has_command_param = any(
                    (_annotation_name(a.annotation) or "").endswith("Command") for a in node.args.args
                )
                if not has_command_param:
                    findings.add(
                        "no-generic-crud-endpoint",
                        _relpath(f, app_root),
                        node.lineno,
                        f"@router.{deco.func.attr}() route '{node.name}' has no typed *Command parameter -- "
                        "looks like a generic CRUD endpoint on a regulated resource.",
                    )


# ---- check D: no-bus-publish-without-outbox ------------------------------------------------------------


def check_no_bus_publish_without_outbox(
    findings: Findings, files: list[Path], modules_root: Path, app_root: Path
) -> None:
    all_files = list(files)
    main_py = app_root / "main.py"
    if main_py.exists() and main_py not in all_files:
        all_files.append(main_py)

    for f in all_files:
        try:
            rel_to_app = f.relative_to(app_root)
        except ValueError:
            rel_to_app = None
        if rel_to_app in OUTBOX_PUBLISHER_ALLOWLIST_RELPATHS:
            continue
        tree = _parse(f)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                chain = _call_chain(node.func)
                if chain and chain[-1] == "publish_outbox_event":
                    findings.add(
                        "no-bus-publish-without-outbox",
                        _relpath(f, app_root),
                        node.lineno,
                        "publish_outbox_event() called outside the eventbus publisher -- every other "
                        "module must write the outbox row via write_outbox_event() in the same "
                        "transaction as the domain state, not publish directly.",
                    )


# ---- check E: no-float-for-decimal-column --------------------------------------------------------------


def _annotation_mentions_float(ann: ast.expr | None) -> bool:
    if ann is None:
        return False
    return any(isinstance(n, ast.Name) and n.id == "float" for n in ast.walk(ann))


_DECIMAL_COLUMN_TYPES = {"Numeric", "DECIMAL", "Decimal"}


def _mapped_column_uses_decimal_type(value: ast.expr | None) -> bool:
    if value is None or not isinstance(value, ast.Call):
        return False
    chain = _call_chain(value.func)
    if not chain or chain[-1] != "mapped_column":
        return False
    for arg in list(value.args) + [kw.value for kw in value.keywords]:
        if isinstance(arg, ast.Call):
            arg_chain = _call_chain(arg.func)
            if arg_chain and arg_chain[-1] in _DECIMAL_COLUMN_TYPES:
                return True
    return False


def check_no_float_for_decimal_column(
    findings: Findings, files: list[Path], modules_root: Path, app_root: Path
) -> None:
    """AG-04/Doc 110 CALC-FR-001, ADR-0007: 'a lint rule forbidding float/double precision/real on any
    regulated quantity column'. Full-generality (any float column anywhere) can't be told apart
    statically from an ordinary engineering timing/duration float (`retry_after_seconds`, `timeout_seconds`
    and similar float fields are pervasive and legitimate throughout app/modules/*/{reliability,provider,
    read_routing,appsec}.py -- not regulated quantities). This check is deliberately narrower and has no
    false-positive risk: it flags the one shape that is unambiguously wrong regardless of field name --
    an ORM column whose *database* type is explicitly `Numeric`/`DECIMAL` (the author's own declared
    intent: exact decimal storage) but whose *Python*-side `Mapped[...]` annotation says `float` instead
    of `Decimal`. That mismatch found one real instance in app/ (qms.ncr_disposition.quantity, fixed in
    this same commit) -- SQLAlchemy hands the application a lossy binary float on every read despite the
    column being stored as an exact decimal, silently defeating DATA-FR-019 downstream of the DB layer."""
    for f in files:
        if f.name != "models.py" and not f.name.endswith("_models.py"):
            continue
        tree = _parse(f)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.AnnAssign)
                and _annotation_mentions_float(node.annotation)
                and _mapped_column_uses_decimal_type(node.value)
            ):
                target = node.target.id if isinstance(node.target, ast.Name) else "?"
                findings.add(
                    "no-float-for-decimal-column",
                    _relpath(f, app_root),
                    node.lineno,
                    f"'{target}' is Mapped[float] but its column type is Numeric/DECIMAL -- use "
                    "Mapped[Decimal] (DATA-FR-019: no binary float for a regulated quantity).",
                )


CHECKS = {
    "no-cross-module-write": check_no_cross_module_write,
    "no-set-value-equivalent": check_no_set_value_equivalent,
    "no-generic-crud-endpoint": check_no_generic_crud_endpoint,
    "no-bus-publish-without-outbox": check_no_bus_publish_without_outbox,
    "no-float-for-decimal-column": check_no_float_for_decimal_column,
}


def run(modules_root: Path | None = None, app_root: Path | None = None) -> Findings:
    """Run all checks against `modules_root` (default: the real app/modules tree) and return the
    findings. `app_root` defaults to `modules_root.parent` and is only used to render nicer relative
    paths in findings."""
    modules_root = modules_root if modules_root is not None else MODULES_ROOT
    app_root = app_root if app_root is not None else modules_root.parent
    files = sorted(p for p in modules_root.rglob("*.py") if "__pycache__" not in p.parts)
    findings = Findings()
    for check in CHECKS.values():
        check(findings, files, modules_root, app_root)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    findings = run()
    file_count = len(sorted(p for p in MODULES_ROOT.rglob("*.py") if "__pycache__" not in p.parts))

    print(f"files scanned : {file_count}")
    print(f"checks run    : {len(CHECKS)}  ({', '.join(CHECKS)})")

    if args.json:
        print(json.dumps({"findings": findings.items}, indent=2))
        return 1 if findings.items else 0

    if not findings.items:
        print("\nPASS  no architecture guardrail violations found")
        return 0

    print(f"\nFAIL  {len(findings.items)} violation(s)")
    for item in findings.items:
        print(f"  [{item['rule']}] {item['file']}:{item['line']}\n      {item['message']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
