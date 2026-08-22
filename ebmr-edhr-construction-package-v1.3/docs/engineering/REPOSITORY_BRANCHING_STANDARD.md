# Repository & Branching Standard

**Derived from:** Document 99 (SPEC-ENG-003) — controlled source in `specs/`
**Purpose:** Branching, protection, review and hotfix rules.
**Requirements:** GIT-FR-001..030 (30)

> This file is the working engineering standard. The controlled source is Document 99; where the two
> differ, the specification wins and this file is corrected.

## Requirements

| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| GIT-FR-001 | Repository model | Use documented monorepo or approved multi-repo topology with explicit ownership; topology versioned in architecture. | Due diligence. |
| GIT-FR-002 | Main branch | main/equivalent is protected and always represents releasable integrated state subject to release gates. | Stability. |
| GIT-FR-003 | No direct push | Direct pushes/force pushes to protected production branches prohibited. | Control. |
| GIT-FR-004 | Feature branches | Short-lived branches from current protected baseline; naming includes issue/change/task ID. | Traceability. |
| GIT-FR-005 | PR required | All production code/config/migration/contract changes merge through pull request. | Review. |
| GIT-FR-006 | PR metadata | PR includes purpose, requirement IDs, risk, migrations, APIs/events, dependencies, tests, validation impact. | Review context. |
| GIT-FR-007 | CODEOWNERS | GxP core, IAM/signature, audit/Vault, migrations, security, CI/release and validation paths have mandatory owners. | Independent review. |
| GIT-FR-008 | Required approvals | Approval count/roles based on path/risk; author cannot satisfy all required approvals. | SoD. |
| GIT-FR-009 | Status checks | Required CI checks cannot be bypassed by normal developers. | Automated gate. |
| GIT-FR-010 | Conversation resolution | Required review threads resolved before merge; dismissals recorded. | Review integrity. |
| GIT-FR-011 | Signed commits/tags | Release tags/artifacts use organization-approved signing/attestation; developer commit signing policy configurable. | Provenance. |
| GIT-FR-012 | Commit content | Commits avoid secrets/binaries/generated build output unless designated; messages reference issue/change where practical. | Clean history. |
| GIT-FR-013 | History rewrite | Published protected history not rewritten except exceptional repository security procedure. | Evidence. |
| GIT-FR-014 | Release tags | Immutable annotated/signed release tags identify exact source baseline. | Reproducibility. |
| GIT-FR-015 | Versioning | Product/service/schema/contract versions follow documented semantic/calendar strategy; one release manifest is authoritative. | Consistency. |
| GIT-FR-016 | Hotfix | Hotfix starts from production release baseline, receives expedited but mandatory controls, then merges forward. | Emergency control. |
| GIT-FR-017 | Security fix | Embargoed private workflow supported for sensitive vulnerability patches. | Disclosure safety. |
| GIT-FR-018 | Rollback branch | Rollback uses known prior release/artifact; no ad-hoc revert of database history. | Safe recovery. |
| GIT-FR-019 | Generated files | Generated contracts/clients checked or rebuilt according to policy; source generator remains authoritative. | Consistency. |
| GIT-FR-020 | Large files | Evidence/test binaries stored artifact/evidence system or Git LFS only if approved; normal Git history not used as regulated archive. | Repo health. |
| GIT-FR-021 | Submodules | Git submodules discouraged/controlled; third-party source pinned and license/provenance tracked. | Supply chain. |
| GIT-FR-022 | Secrets | Secret scanning blocks pushes/PR; leaked credential treated as incident and rotated. | Security. |
| GIT-FR-023 | Branch retention | Merged feature branches may delete; protected release tags/history remain. | Hygiene. |
| GIT-FR-024 | Forks | External forks for proprietary regulated code disabled/restricted according to organization policy. | IP. |
| GIT-FR-025 | Access review | Repository roles/team access periodically reviewed and offboarding immediate. | Security. |
| GIT-FR-026 | Bot accounts | CI/AI bots use named apps/service identities and least privilege, not personal PATs. | Attribution. |
| GIT-FR-027 | PR provenance | Automation identifies AI-assisted changes if organization policy requires, but human accountability remains with reviewers/authorizers. | Governance. |
| GIT-FR-028 | Release evidence | PR/commit/tag/build/validation authorization connected in release manifest. | Acquisition readiness. |
| GIT-FR-029 | Archive | Repository backup/export and ownership records support acquisition/business continuity. | Due diligence. |
| GIT-FR-030 | No orphan code | Every production repo has owner, purpose, license/IP status, CI and release lifecycle. | Portfolio hygiene. |

## Enforcement

See `docs/generated/33_CODING_STANDARD_COMPLIANCE_MATRIX.md`,
`docs/generated/34_ARCHITECTURE_GUARDRAIL_MATRIX.md` and `.github/workflows/ci.yml`.

## Tests

- direct push protected branch rejected
- missing CODEOWNER approval
- failed CI merge blocked
- hotfix forward-merge check
- secret committed blocks PR
- release tag source mismatch
- bot personal PAT prohibited
- branch from stale release conflict
