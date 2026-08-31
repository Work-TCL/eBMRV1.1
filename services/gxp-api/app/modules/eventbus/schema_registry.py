"""Document 73 (SPEC-DATA-005) event-schema compatibility checker -- EVT-FR-011/012/029.

Pure function, no DB/network -- run in CI against the committed `contracts/events/*.json` before and
after a change (same spirit as `tooling/events/validate.py`, but scoped to a single event's old/new
payload schema rather than the whole repository). Additive changes (new optional property, an existing
required property becoming optional, a new enum value) are compatible; removing a property, adding a
new required property, or narrowing a type is breaking.
"""

from __future__ import annotations

from app.mutation.errors import EventSchemaBreakingChangeError


def verify_event_schema_compatibility(
    old_schema: dict, new_schema: dict, *, enforce: bool = False
) -> dict:
    old_props: dict = old_schema.get("properties", {}) or {}
    new_props: dict = new_schema.get("properties", {}) or {}
    old_required = set(old_schema.get("required", []) or [])
    new_required = set(new_schema.get("required", []) or [])

    violations: list[str] = []
    for name in old_props:
        if name not in new_props:
            violations.append(f"property '{name}' was removed")
    for name in sorted(new_required - old_required):
        violations.append(f"property '{name}' became newly required")
    for name in old_props:
        if name not in new_props:
            continue
        old_type = old_props[name].get("type")
        new_type = new_props[name].get("type")
        if old_type and new_type and old_type != new_type:
            violations.append(f"property '{name}' type changed from {old_type!r} to {new_type!r}")

    compatible = not violations
    report = {
        "compatible": compatible,
        "violations": violations,
        "added_properties": sorted(set(new_props) - set(old_props)),
        "removed_properties": sorted(set(old_props) - set(new_props)),
    }
    if not compatible and enforce:
        raise EventSchemaBreakingChangeError(
            "Proposed event schema change is not backward compatible", violations=violations
        )
    return report
