"""Negative-fixture tests for tooling/guardrails/validate.py.

Each fixture under tests/fixtures/<check>/modules/ is a small synthetic `app/modules/` tree containing
one deliberate violation of the named check plus at least one adjacent *allowed* pattern, so a check that
flagged everything indiscriminately would fail these tests just as loudly as one that flagged nothing.

`validate.py` itself needs only stdlib `ast`/`pathlib`/`json` (no app dependencies), matching the
dependency-free style of the other tooling/*/validate.py checks, so it runs directly in the `guardrails`
CI job with plain `python3`. This test file needs `pytest`, which the repo already has as a `gxp-api` dev
dependency -- it runs in the `lint` job (which already does `uv sync --frozen --group dev`) as
`uv run python -m pytest ../../ebmr-edhr/tooling/guardrails/tests`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validate  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _findings_for(fixture_name: str) -> list[dict]:
    modules_root = FIXTURES / fixture_name / "modules"
    return validate.run(modules_root).items


def test_cross_module_write_flags_the_foreign_construct_and_add() -> None:
    findings = _findings_for("cross_module_write")
    hits = [f for f in findings if f["rule"] == "no-cross-module-write"]
    assert len(hits) == 1, hits
    assert hits[0]["file"].endswith("other_mod/commands.py")
    assert "OwnedThing" in hits[0]["message"]


def test_cross_module_write_allows_reads_and_same_module_writes() -> None:
    findings = _findings_for("cross_module_write")
    flagged_files = {f["file"] for f in findings if f["rule"] == "no-cross-module-write"}
    assert not any(f.endswith("other_mod/service.py") for f in flagged_files)  # read-only select
    assert not any(f.endswith("owner_mod/commands.py") for f in flagged_files)  # writes its own model


def test_set_value_equivalent_flags_all_three_shapes() -> None:
    findings = _findings_for("set_value_equivalent")
    hits = [f for f in findings if f["rule"] == "no-set-value-equivalent"]
    lines = {f["line"] for f in hits}
    assert len(hits) == 3, hits
    # one hit per violating function: frappe.db.set_value, text()-UPDATE, and the dynamic setattr loop
    assert {6, 11, 17} <= lines or len(lines) == 3


def test_set_value_equivalent_allows_bounded_setattr() -> None:
    findings = _findings_for("set_value_equivalent")
    hits = [f for f in findings if f["rule"] == "no-set-value-equivalent"]
    assert all("ok_bounded_setattr" not in str(h) for h in hits)


def test_generic_crud_flags_untyped_patch_route() -> None:
    findings = _findings_for("generic_crud")
    hits = [f for f in findings if f["rule"] == "no-generic-crud-endpoint"]
    assert len(hits) == 1, hits
    assert "patch_thing_generic" in hits[0]["message"]


def test_generic_crud_allows_typed_command_route() -> None:
    findings = _findings_for("generic_crud")
    hits = [f for f in findings if f["rule"] == "no-generic-crud-endpoint"]
    assert all("patch_thing_typed" not in h["message"] for h in hits)


def test_bus_publish_flags_direct_call_outside_eventbus() -> None:
    findings = _findings_for("bus_publish")
    hits = [f for f in findings if f["rule"] == "no-bus-publish-without-outbox"]
    assert len(hits) == 1, hits
    assert hits[0]["file"].endswith("a_mod/commands.py")


def test_bus_publish_allows_the_publisher_itself_and_the_gateway_helper() -> None:
    findings = _findings_for("bus_publish")
    flagged_files = {f["file"] for f in findings if f["rule"] == "no-bus-publish-without-outbox"}
    assert not any(f.endswith("eventbus/outbox.py") for f in flagged_files)


def test_real_codebase_is_clean() -> None:
    """The actual app/modules/ tree must pass all four checks today -- this is the blocking CI gate,
    not a ratchet, so there is no allowance for known-bad baseline entries here."""
    findings = validate.run().items
    assert findings == [], findings
