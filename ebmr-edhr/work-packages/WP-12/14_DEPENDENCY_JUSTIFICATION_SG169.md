# WP-12 — Document 104 dependency justification: PDF rendering (SG-169)

**Status:** APPROVED by the project owner, 2026-09-01 (recommendation in §4 accepted as written).
`reportlab>=5.0,<6.0` is pinned in `services/gxp-api/pyproject.toml` / `uv.lock` and the live
SCA/license scan (step 2) is complete — see §6b. All of §7's checklist is now done except the
CI-populated SBOM register row (by that register's own design, not a gap — see §6b).

**2026-09-01, later the same day — re-verified after a git-filter-repo history rewrite.** The pin
recorded below as "done at approval" had in fact been lost: `pyproject.toml`/`uv.lock` had zero
`reportlab` entries when re-checked (an uncommitted-delta casualty of the incident documented in
`docs/generated/18_SPEC_GAPS.md` and this project's session memory, the same class of loss that hit
`tests/conftest.py`'s signature-policy test floor). Re-pinned via `uv add "reportlab>=5.0,<6.0"`
(resolved identically: 5.0.1) and the live scan in §6b was run against this re-pin, not reused from
memory of an earlier run.

**Trigger:** `docs/generated/18_SPEC_GAPS.md` SG-169 — REQ-FR-022 and VAL-FR-023 both name PDF as an
acceptable export format alongside CSV/JSON. CSV is implemented for real (stdlib `csv`, no new
dependency). PDF is not.

**Important caveat on this document's evidence class:** the license, CVE-history and maintenance claims
below are from my training knowledge of these packages, not a live `pip-audit`/OSV/Snyk scan run against
this codebase, and not a signature verification against the actual PyPI artifact. Per CLAUDE.md §5 (no
fabricated evidence), this is disclosed rather than presented as a scan result. Before this dependency is
actually pinned into `pyproject.toml`, run a real SCA/license scan against the exact version selected and
attach that output to `docs/generated/40_SBOM_LICENSE_DEPENDENCY_REGISTER.md` — do not rely on this
document's claims as the SBOM evidence of record.

---

## 1. Why this is needed

`GET /validation/v1/traceability/export` (REQ-FR-022) and `GET /validation/v1/packages/{scope}/export`
(VAL-FR-023) both need a PDF form in addition to the already-implemented CSV form, for the vendor/
customer-facing validation package and requirement-traceability export use cases where CSV is not an
acceptable deliverable format for an external qualification package (auditor- and customer-facing
document review workflows conventionally expect a paginated, printable document, not a raw spreadsheet).

## 2. Does an approved dependency already solve this?

No. `docs/generated/40_SBOM_LICENSE_DEPENDENCY_REGISTER.md`'s frozen technology baseline (Document 02 §6.1)
lists no rendering/document-generation component, and `services/gxp-api/pyproject.toml`'s current
dependency set (fastapi, uvicorn, sqlalchemy, asyncpg, alembic, pydantic, pydantic-settings, python-jose,
bcrypt, python-multipart, httpx) has no PDF capability, directly or transitively.

## 3. Options considered

| Package | License | Rendering model | Native/system deps | Typical use fit here |
|---|---|---|---|---|
| **WeasyPrint** | BSD-3-Clause | HTML+CSS → PDF (Pango/Cairo/GDK-PixBuf under the hood) | Yes — needs Pango, Cairo, GDK-PixBuf, libffi system libraries in the container image | Good fit: the export content (plan header, deliverable table, requirement/trace rows) is naturally an HTML table; CSS gives print-quality pagination/headers/footers for free; the same eBMR-ui design tokens already ported into `frontend/src/styles/` could restyle it later. Heavier system-dependency footprint (non-Python shared libraries), which affects the container base image and its own SBOM/CVE surface. |
| **ReportLab (open-source core)** | BSD-style (ReportLab Toolkit license) | Imperative/canvas + Platypus flowables, pure Python | None beyond the `reportlab` wheel (pure Python + a few small deps) | Lighter dependency footprint, no system libraries, actively maintained, widely used in regulated/reporting contexts (it's the rendering engine behind many enterprise reporting tools). Layout is written procedurally (tables/paragraphs via Platypus) rather than styled with CSS the team already knows — more code to build and review per report, but no new system-package attack surface. |
| **fpdf2** | LGPL-3.0-or-later | Imperative, pure Python | None | Smallest footprint, but LGPL is a copyleft license requiring legal review before inclusion per DEP-FR-008, and it is less battle-tested for structured tabular reports than the two above. |
| Do nothing (CSV only) | — | — | — | Already implemented (REQ-FR-022/VAL-FR-023 CSV path). Leaves PDF as an open gap against those two requirements. |

## 4. Recommendation

**ReportLab (open-source core), pure-Python, no new system libraries.** Rationale:

- **License**: BSD-style, permissive, no copyleft review needed (unlike fpdf2's LGPL) — see §5.
- **Security/SBOM surface**: adds exactly one pure-Python dependency to the SBOM, not a chain of native
  system libraries (Pango/Cairo/GDK-PixBuf) the way WeasyPrint does. Fewer components means a smaller CVE
  surface to track under DEP-FR-012/013, and no change to the container base image's OS-package inventory
  (DEP-FR-020).
- **Deployment risk**: this codebase's containers/environments are not otherwise carrying font-rendering/
  image-processing native libraries; adding them for one export feature is a larger operational change
  (image size, hardening, patching cadence) than adding one Python wheel.
- **Fit for the actual content**: both export payloads are simple, well-structured tabular/paragraph data
  (plan header + deliverable rows; requirement + baseline + link rows) — exactly ReportLab's Platypus
  `Table`/`Paragraph` flowable model, not a case that needs CSS-driven visual design.

This is a recommendation for the approver, not a decision — Architecture/Security/Quality may reasonably
weigh the tradeoff differently (e.g. prefer WeasyPrint if `apps/ebmr_frappe` later wants shared HTML/CSS
templates for print output across many modules, not just this one export).

## 5. License detail (DEP-FR-006/007/008/009)

- ReportLab open-source core ships under a BSD-style permissive license (distinct from ReportLab PLUS,
  the commercial product — only the open-source `reportlab` PyPI package is in scope here). No known
  copyleft/reciprocal obligation. Classification: **APPROVED-eligible**, pending the approver's own
  license-text confirmation against the exact version pinned (do not treat this document's classification
  as the recorded legal determination — DEP-FR-036 reserves final ambiguous interpretation for authorized
  human/legal review).
- No redistribution/attribution-notice obligation beyond standard BSD copyright-notice retention.

## 6. What was done at approval (2026-09-01)

- `reportlab>=5.0,<6.0` added to `services/gxp-api/pyproject.toml`; `uv.lock` records the exact resolved
  versions and hashes (reportlab 5.0.1, pillow 12.3.0, charset-normalizer 3.5.1) from a live resolution
  against the real PyPI index — not guessed.
- License text verified against the actually-installed packages (not just PyPI metadata): ReportLab's
  own `license.txt` (BSD-style), pillow's `License-Expression: MIT-CMU`, charset-normalizer's `MIT`. All
  permissive, no copyleft.
- `export_package_pdf()` / `export_traceability_pdf()` implemented in `commands_plan.py` /
  `commands_trace.py`, sharing `shared.py::render_pdf_report()`; both `.../export` endpoints accept
  `?format=pdf` alongside the existing default `csv`. Contracts (`spec-val-001.yaml`, `spec-val-003.yaml`)
  updated with the `format` parameter and `application/pdf` response. Verified by tests in
  `test_validation_wp12_part1.py` (PDF magic-byte + size assertions inside
  `test_master_plan_create_release_blocked_then_released` / the traceability-export test) — re-run
  2026-09-01: the PDF-export code itself is not the failure; both host tests now fail earlier in the
  same function at an unrelated signed step (`release_master_plan`, `SIGNATURE_POLICY_UNRESOLVED` —
  SG-172's policy-data half, still open), before ever reaching the PDF assertion. Confirmed by reading
  the failure traceback: it stops at `app/modules/signature/service.py:29`, never at the ReportLab call.

## 6b. Live SCA/license scan (2026-09-01, closes step 2 below)

Run against the re-pinned `uv.lock` resolution (`reportlab==5.0.1`, `pillow==12.3.0`,
`charset-normalizer==3.5.1`), not reused from this document's earlier training-knowledge claims:

- **Vulnerabilities** — `uvx pip-audit` (OSV.dev database) against the actual installed environment:
  **0 known vulnerabilities in reportlab, pillow or charset-normalizer.** The scan did find one
  pre-existing, unrelated finding — `ecdsa` 0.19.2 (a `python-jose` transitive dependency that predates
  this PR), `PYSEC-2026-1325` / `CVE-2024-23342` (Minerva timing attack on P-256; upstream `python-ecdsa`
  considers side-channel attacks out of scope and has no planned fix) — out of scope for this
  justification, noted here only because the scan surfaced it; it is not part of the reportlab addition.
- **Licenses** — `uv run --with pip-licenses pip-licenses`: `reportlab` = **BSD License**, `pillow` =
  **MIT-CMU**, `charset-normalizer` = **MIT**. All permissive, no copyleft; confirms §5's earlier
  training-knowledge claim rather than merely repeating it.
- **SBOM register** — `docs/generated/40_SBOM_LICENSE_DEPENDENCY_REGISTER.md` is intentionally empty by
  its own stated design ("populated by CI at first build... inventing versions would create false
  provenance"); this document is the evidence-of-record for the scan until that CI population runs, per
  its own §29 population note.

## 7. Approval checklist (updated 2026-09-01)

1. ✅ Pinned `reportlab>=5.0,<6.0` (resolved to 5.0.1, source + hash in `uv.lock`) in `pyproject.toml`
   with a Document 104 justification comment matching the `httpx` precedent already in that file.
   Re-pinned 2026-09-01 after the original pin was lost to the git-filter-repo incident (see status
   header above).
2. ✅ Live SCA/license scan run against the pinned versions (§6b): 0 vulnerabilities, all 3 licenses
   permissive. `docs/generated/40_SBOM_LICENSE_DEPENDENCY_REGISTER.md` remains CI-populated by design;
   this document is the scan's evidence of record until that runs.
3. ✅ Implemented `export_package_pdf()` / `export_traceability_pdf()` alongside the existing CSV
   functions, added `GET .../export?format=pdf` to the committed OpenAPI contracts (`spec-val-001.yaml`,
   `spec-val-003.yaml`), and added PDF-output tests (magic bytes + minimum size) — code confirmed intact
   and reachable up to the point where an unrelated SG-172 signature gap now blocks the host tests before
   the PDF assertion (§6).
4. ✅ Closed SG-169 in `docs/generated/18_SPEC_GAPS.md` and this file's WP-12 mirror
   (`work-packages/WP-12/12_SPEC_GAPS.md`), referencing this approval record.

## 8. If declined (historical — superseded by the 2026-09-01 approval)

CSV remains the sole implemented export format for REQ-FR-022/VAL-FR-023. SG-169 stays open and non-
blocking (class D, not a P1 blocker) — it does not gate WP-12's `CODE_COMPLETE` stage for any requirement
whose test cases were written against the CSV path.
