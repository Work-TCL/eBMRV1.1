# US eBMR / eDHR Regulated Manufacturing Platform
## Document 99 — Repository & Branching Standard — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-ENG-003  
**Parent Documents:** Documents 01–96  
**Primary Dependencies:** Documents 61–68, 79–98, 103–104  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This specification is itself a control source for Claude Code/Codex. Engineering agents shall not treat it as optional style advice when the requirement is marked mandatory.

For every engineering-control function defined below preserve:

- caller/trigger;
- input type, source and requiredness;
- preconditions;
- authorization/ownership where applicable;
- repository/database/artifact reads;
- repository/database/artifact writes;
- transaction/atomicity boundary;
- output/return type;
- events/evidence;
- stable error codes;
- CI enforcement mechanism;
- positive and negative tests.

If a requirement cannot be implemented because of a conflict with another numbered specification, create a `SPEC_GAP` and stop the conflicting change rather than silently choosing a new architecture.

# Engineering Non-Negotiables

- Never modify or fork Frappe/ERPNext core.
- GxP-authoritative mutations enter through the proprietary Mutation Gateway/domain APIs.
- Frappe/MariaDB projections are not authoritative GxP records.
- No generic CRUD over released/regulated records.
- No direct SQL repair of regulated records outside controlled repair/migration mechanisms.
- No bypass of authorization, SoD, qualification or Part 11 signature requirements.
- No deletion/rewriting of immutable audit/version/evidence history.
- No external side effect inside a database transaction unless a specification explicitly establishes a safe protocol.
- Transactional outbox and idempotency are mandatory where specified.
- Temporal orchestrates; it does not own regulatory truth.
- Redis/search/NATS projections or caches are not GxP truth.
- Regulated calculations use exact decimal/UOM/rounding rules.
- All public contracts, DB migrations and release artifacts are versioned and traceable to requirement IDs.
- Production deployment must match a validated release authorization.
- AI is advisory by default; autonomous regulated decisions are prohibited unless a future separately approved specification explicitly changes that rule.

# 1. Objective

Define Git repository organization, branch protection, PR review, CODEOWNERS, release tags, hotfix governance and provenance needed for safe AI-assisted development and acquisition due diligence.

# 2. Actors / Components

- Developer
- Reviewer
- CODEOWNER
- Release Engineer
- Security
- Claude Code/Codex
- Git Hosting
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| GIT-FR-001 | Repository model | Use documented monorepo or approved multi-repo topology with explicit ownership; topology versioned in architecture. | Due diligence. |
| GIT-FR-002 | Main branch | `main`/equivalent is protected and always represents releasable integrated state subject to release gates. | Stability. |
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

# 4. Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB or repo effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createPullRequestChecklist() | PR bot/Developer | changed files; requirement IDs; task metadata | Branch based on protected baseline | Computes risk/path owners and mandatory PR fields/checks | PRChecklist | PullRequestChecklistCreated |
| resolveRequiredReviewers() | PR bot | changed paths; CODEOWNERS; risk classification | Ownership files valid | Returns mandatory reviewer groups/approval count | ReviewerRequirement | RequiredReviewersResolved |
| evaluateMergeGate() | Git hosting integration | PR; approvals; CI; unresolved threads; policy | PR open/current | Returns MERGE_ALLOWED or blockers | MergeGateDecision | MergeGateEvaluated |
| createReleaseTag() | Release automation | approved source commit; version; release authorization | Commit merged; release gates pass | Creates immutable signed/annotated tag and release manifest link | ReleaseTag | ReleaseTagCreated |
| openHotfixBranch() | Release/Security | production release tag; incident/change; scope | Authorized emergency change | Creates controlled hotfix branch with required policy | HotfixBranch | HotfixBranchOpened |
| reconcileHotfixForward() | Release automation | hotfix commit; main branch | Hotfix released | Creates/validates forward merge PR so fix not lost | ForwardMergeStatus | HotfixForwardMergeRequired |
| auditRepositoryAccess() | Security/Engineering Ops | repo/org memberships; role policy | Read access available | Compares current rights vs approved role ownership | RepoAccessReview | RepositoryAccessReviewCompleted |
| generateRepoDueDiligenceIndex() | Engineering Ops | repo inventory; release/tag/license/ownership data | Metadata available | Creates acquisition-ready repo inventory | RepoDueDiligenceIndex | RepoDueDiligenceGenerated |

# 5. Reference Monorepo Layout

```text
/
├── apps/ebmr_frappe/
├── services/
│   ├── mutation-gateway/
│   ├── signature/
│   ├── audit/
│   ├── vault/
│   ├── iam-policy/
│   ├── rules/
│   └── domain-*/
├── packages/
│   ├── contracts/
│   ├── domain-types/
│   └── testing/
├── edge/
├── infrastructure/
├── validation/
├── docs/
└── tooling/
```

If multi-repo is adopted later, service ownership and cross-repo version/release compatibility must remain explicit.

# 6. Branch Model

Preferred default:
- protected `main`;
- short-lived `feature/<issue>-<slug>`;
- `hotfix/<incident-or-change>-<slug>`;
- optional temporary release branch only if release operations need it;
- immutable release tags.

Long-lived environment branches are discouraged because deployment state belongs in deployment/release records, not divergent Git history.

# 7. PR Template Required Fields

```text
Purpose
Requirement IDs
Affected modules
Risk / validation impact
DB migration? yes/no
API/event change? yes/no
Dependency/license change? yes/no
Security impact
Test evidence
Rollback/compatibility notes
SPEC_GAPs
```


# 8. Mandatory Test / Enforcement Catalogue

- direct push protected branch rejected
- missing CODEOWNER approval
- failed CI merge blocked
- hotfix forward-merge check
- secret committed blocks PR
- release tag source mismatch
- bot personal PAT prohibited
- branch from stale release conflict

# 9. Acceptance Criteria

Every production change is attributable to a reviewed PR and exact release tag, with ownership, test, dependency, migration and validation evidence discoverable.

# 10. Claude Code / Codex Prohibitions

- Never use direct production edits outside Git-controlled emergency procedure.
- Never create permanent personal branches as deployment source.
- Never force-push protected release history.
- Never grant AI bot organization-admin privileges for convenience.
