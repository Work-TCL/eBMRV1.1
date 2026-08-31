"""One-time correction: the original fill_wp07_test_cases.py run (see its own docstring) wrote per-case
Status/Executed-by/Date/Actual-result lines into `ebmr-edhr/test-cases/WP-07/*.md` -- an untracked stray
duplicate of the real package -- instead of the git-tracked canonical copy at
`ebmr-edhr-construction-package-v1.3/test-cases/WP-07/*.md`. TEST_CASE_LIBRARY.csv (the actual master per
CLAUDE.md section 7b) was appended correctly in the tracked package at the time; only the per-document
markdown books were left at NOT_STARTED there. This script re-derives the identical classification (same
dicts, same logic, imported unmodified from fill_wp07_test_cases.py) and rewrites *only* the markdown
status lines in the tracked package -- it does not touch TEST_CASE_LIBRARY.csv again (already correct).

Discovered and fixed 2026-08-26 while starting Document 17 (SPEC-EBMR-008) work and re-verifying the
canonical package location.

Run with: python3 scripts/fix_wp07_tracked_case_files.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fill_wp07_test_cases as orig  # noqa: E402

TRACKED_CASE_DIR = orig.REPO_ROOT / "ebmr-edhr-construction-package-v1.3/test-cases/WP-07"


def main() -> None:
    orig.CASE_DIR = TRACKED_CASE_DIR
    total = 0
    for doc_num, spec_id, req_status, mandatory, scenario in orig.DOCS:
        case_file = next(TRACKED_CASE_DIR.glob(f"Document_{doc_num}_{spec_id}_TEST_CASES.md"))
        text = case_file.read_text()
        cases = orig.parse_cases(text)
        results = {case["id"]: orig.classify(case, req_status, mandatory, scenario) for case in cases}

        out_lines = []
        current_id = None
        for line in text.splitlines():
            if orig.STATUS_LINE_RE.match(line):
                status, actual_result = results[current_id]
                out_lines.append(
                    f"- **Status:** {status}  |  **Executed by:** {orig.EXECUTED_BY}  |  **Date:** {orig.EXECUTED_AT}  |  "
                    f"**Actual result:** {actual_result}  |  **Defect:** —"
                )
                continue
            header = orig.CASE_HEADER_RE.match(line)
            if header:
                current_id = header.group(1)
            out_lines.append(line)
        case_file.write_text("\n".join(out_lines) + ("\n" if text.endswith("\n") else ""))
        print(f"rewrote {len(cases)} case statuses in {case_file} (tracked)")
        total += len(cases)
    print(f"total: {total}")


if __name__ == "__main__":
    main()
