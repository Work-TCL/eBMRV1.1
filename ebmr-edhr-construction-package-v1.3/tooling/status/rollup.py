#!/usr/bin/env python3
"""Regenerate status/BUILD_STATUS.md and traceability states from build-status.json + the test library.

Usage:  python tooling/status/rollup.py
Never hand-edit BUILD_STATUS.md; it is derived.
"""
import csv, json, collections, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parents[2]
status = json.loads((ROOT / "status/build-status.json").read_text())

# ---- fold real test results into module counters
counts = collections.defaultdict(collections.Counter)
req_state = collections.defaultdict(dict)
with open(ROOT / "test-cases/TEST_CASE_LIBRARY.csv") as f:
    for row in csv.DictReader(f):
        counts[row["module"]][row["status"] or "NOT_STARTED"] += 1
        req_state[row["module"]].setdefault(row["requirement_id"], []).append(row["status"] or "NOT_STARTED")

for m in status["modules"]:
    c = counts.get(m["module"], collections.Counter())
    m["test_pass"], m["test_fail"], m["test_blocked"] = c["PASS"], c["FAIL"], c["BLOCKED"]
    for rid, sts in req_state.get(m["module"], {}).items():
        if rid in m["requirements_state"]:
            if all(s == "PASS" for s in sts):
                m["requirements_state"][rid] = "VERIFIED"
            elif any(s == "FAIL" for s in sts):
                m["requirements_state"][rid] = "BLOCKED"
            elif any(s in ("PASS", "IN_PROGRESS") for s in sts):
                m["requirements_state"][rid] = "IN_PROGRESS"

order = status["stage_model"]
for wp in status["work_packages"]:
    mods = [m for m in status["modules"] if m["work_package"] == wp["id"]]
    wp["modules_total"] = len(mods)
    wp["modules_done"] = sum(1 for m in mods if m["stage"] in ("QUALIFIED", "RELEASED"))
    wp["stage"] = min((m["stage"] for m in mods), key=lambda s: order.index(s)) if mods else "NOT_STARTED"

status["totals"]["modules_started"] = sum(1 for m in status["modules"] if m["stage"] != "NOT_STARTED")
status["totals"]["modules_released"] = sum(1 for m in status["modules"] if m["stage"] == "RELEASED")
status["generated"] = datetime.date.today().isoformat()
(ROOT / "status/build-status.json").write_text(json.dumps(status, indent=1))

verified = sum(1 for m in status["modules"] for s in m["requirements_state"].values() if s == "VERIFIED")
total_req = sum(m["requirements"] for m in status["modules"])
executed = sum(m["test_pass"] + m["test_fail"] for m in status["modules"])

L = ["# Build Status", "", f"_Generated {status['generated']} — do not hand-edit._", "",
     f"**Overall:** {status['totals']['modules_started']}/{len(status['modules'])} modules started · "
     f"{status['totals']['modules_released']} released · {verified}/{total_req} requirements verified · "
     f"{executed}/{status['totals']['test_cases']} test cases executed", "",
     "## Work packages", "",
     "| WP | Title | Modules done | Stage | Depends on |", "|---|---|---|---|---|"]
for wp in status["work_packages"]:
    L.append(f"| {wp['id']} | {wp['title']} | {wp['modules_done']}/{wp['modules_total']} | "
             f"{wp['stage']} | {', '.join(wp['depends_on']) or '—'} |")
L += ["", "## Modules", "",
      "| Doc | Module | WP | Risk | Reqs | Verified | Tests | Pass | Fail | Blocked | Stage | Owner |",
      "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for m in status["modules"]:
    v = sum(1 for s in m["requirements_state"].values() if s == "VERIFIED")
    L.append(f"| {m['document']:02d} | {m['module']} | {m['work_package']} | "
             f"{'H' if m['risk_class'].startswith('HIGHER') else 'S'} | {m['requirements']} | {v} | "
             f"{m['test_cases']} | {m['test_pass']} | {m['test_fail']} | {m['test_blocked']} | "
             f"{m['stage']} | {m['owner'] or '—'} |")
blocked = [m for m in status["modules"] if m["blockers"]]
if blocked:
    L += ["", "## Blocked modules", "", "| Module | Blocker |", "|---|---|"]
    for m in blocked:
        L.append(f"| {m['module']} | {'; '.join(m['blockers'])} |")
(ROOT / "status/BUILD_STATUS.md").write_text("\n".join(L) + "\n")
print(f"rollup: {status['totals']['modules_started']} started, {verified}/{total_req} requirements verified, "
      f"{executed} test cases executed")
