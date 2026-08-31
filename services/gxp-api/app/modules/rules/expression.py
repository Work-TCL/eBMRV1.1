"""RUL-FR-005 — a constrained, explicit AST interpreter. No `eval`, no arbitrary Python/JS/SQL, no
network/file access: an expression is a JSON tree of `{"op": ..., "args": [...]}` nodes, `{"var": "name"}`
lookups, and literal values (str/bool/None/Decimal-compatible numbers). This is a deliberately minimal V1
operator set (RUL-FR-004/009/030) — enough for eligibility/limit/reconciliation-style rules, not a general
computation language.

Document 110 (SG-143): an optional `class_policy`/`precision_policy` pair, resolved by the caller from
the released rule's own `precision_policy.calculation_class` (`app.modules.rules.precision`), governs
comparison-stage rounding (N4/CALC-FR-005). Omitted, evaluation behaves exactly as before — a rule
drafted before Document 110's calculation-class taxonomy applied to it (or a rule outside GxP-decision
scope, e.g. one under evaluation without a resolved class) is not retroactively broken.
"""

from decimal import Decimal, DivisionByZero, InvalidOperation

from app.modules.rules.precision import ClassPolicy, compare as precision_compare
from app.mutation.errors import DivisionUndefinedError, ValidationFailedError

_COMPARISON = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
}
_ARITHMETIC = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
}
_BOOLEAN_NARY = {"and", "or"}


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, bool):
        raise ValidationFailedError("Boolean cannot be used as a numeric operand")
    if isinstance(value, float):
        # AG-03 / DATA-FR-019: no binary float for a regulated quantity, ever — including inside a rule.
        raise ValidationFailedError("Binary float inputs are prohibited; use a decimal string or int")
    if isinstance(value, (int, str, Decimal)):
        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise ValidationFailedError(f"Not a valid decimal value: {value!r}") from exc
    raise ValidationFailedError(f"Cannot convert {value!r} to a decimal operand")


def evaluate(
    node: object,
    variables: dict[str, object],
    *,
    class_policy: ClassPolicy | None = None,
    precision_policy: dict | None = None,
) -> object:
    """Evaluates one AST node against a flat variables dict. Raises ValidationFailedError for a
    malformed node or an operator/variable not in the allowed set — never silently substitutes a
    default (RUL-FR-029).

    `class_policy`/`precision_policy`, when given, round both operands to the calculation class's
    declared comparison precision (N4) before applying a comparison operator — never mid-chain
    arithmetic (N2): `+`/`-`/`*`/`/` always compute on full-precision Decimal."""
    if isinstance(node, dict):
        if "var" in node:
            name = node["var"]
            if name not in variables:
                raise ValidationFailedError(f"Missing required input: {name}", missing_input=name)
            return variables[name]
        if "op" in node:
            op = node["op"]
            args = node.get("args", [])
            if op == "not":
                if len(args) != 1:
                    raise ValidationFailedError("'not' takes exactly one argument")
                return not bool(evaluate(args[0], variables, class_policy=class_policy, precision_policy=precision_policy))
            if op in _BOOLEAN_NARY:
                if not args:
                    raise ValidationFailedError(f"'{op}' requires at least one argument")
                values = [
                    bool(evaluate(a, variables, class_policy=class_policy, precision_policy=precision_policy))
                    for a in args
                ]
                return all(values) if op == "and" else any(values)
            if op in _COMPARISON:
                if len(args) != 2:
                    raise ValidationFailedError(f"'{op}' takes exactly two arguments")
                left = evaluate(args[0], variables, class_policy=class_policy, precision_policy=precision_policy)
                right = evaluate(args[1], variables, class_policy=class_policy, precision_policy=precision_policy)
                left, right = _to_decimal(left), _to_decimal(right)
                if class_policy is not None:
                    return precision_compare(left, right, class_policy, precision_policy or {}, _COMPARISON[op])
                return _COMPARISON[op](left, right)
            if op in _ARITHMETIC:
                if len(args) != 2:
                    raise ValidationFailedError(f"'{op}' takes exactly two arguments")
                left = _to_decimal(evaluate(args[0], variables, class_policy=class_policy, precision_policy=precision_policy))
                right = _to_decimal(evaluate(args[1], variables, class_policy=class_policy, precision_policy=precision_policy))
                try:
                    if op == "/" and right == 0:
                        raise DivisionUndefinedError("Division by zero in rule expression")
                    return _ARITHMETIC[op](left, right)
                except (DivisionByZero, InvalidOperation) as exc:
                    if op == "/":
                        raise DivisionUndefinedError(f"Undefined division result: {exc}") from exc
                    raise ValidationFailedError(f"Arithmetic error evaluating '{op}': {exc}") from exc
            raise ValidationFailedError(f"Unknown or disallowed operator: {op!r}")
        raise ValidationFailedError(f"Malformed expression node: {node!r}")
    if isinstance(node, (str, bool, int, type(None))):
        return node
    if isinstance(node, float):
        raise ValidationFailedError("Binary float literals are prohibited in a rule expression")
    raise ValidationFailedError(f"Unsupported expression literal: {node!r}")


def referenced_variables(node: object) -> set[str]:
    """Walks the AST collecting every `{"var": ...}` name — used by validate_rule to confirm the
    expression only references inputs declared in input_contract (no undeclared/implicit input)."""
    found: set[str] = set()
    if isinstance(node, dict):
        if "var" in node:
            found.add(node["var"])
        for arg in node.get("args", []):
            found |= referenced_variables(arg)
    return found
