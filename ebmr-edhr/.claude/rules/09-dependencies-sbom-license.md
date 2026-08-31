# Dependencies, SBOM and licensing

**Purpose:** Dependencies, SBOM and licensing for the eBMR/eDHR platform.
**Applicable paths/modules:** see `docs/generated/17_REPOSITORY_STRUCTURE.md`; this rule applies to every
service, the Frappe app, edge and integration code unless a narrower scope is stated below.
**Source documents:** Document 104 (SPEC-ENG-008), Document 68 (SPEC-SEC-008)
**Source requirement IDs:** DEP-FR-001..036 (36); SDLC-FR-001..034 (34)

---

## Required implementation pattern

Before proposing any dependency, model or binary: state why it is needed, whether an approved dependency
already solves it, the exact package/version/source/hash, the licence, security and EOL implications, the
SBOM effect, alternatives considered and the approval required (Document 104).

## Forbidden patterns

- adding a dependency to reduce coding effort
- floating version ranges in release builds
- unknown or prohibited licence
- unpinned or unverified provenance
- vendoring code without recording it in the SBOM

## Completion checks

`docs/generated/40_SBOM_LICENSE_DEPENDENCY_REGISTER.md` updated; SCA and licence gates pass.


## Source requirements (extract)

| ID | Requirement | Required behaviour |
|---|---|---|
| DEP-FR-001 | Dependency register | Inventory direct/transitive runtime/build/test dependencies with package/version/source/owner/purpose. |
| DEP-FR-002 | SBOM format | Generate machine-readable SPDX or CycloneDX-compatible SBOM per release/artifact. |
| DEP-FR-003 | Artifact linkage | SBOM tied exact artifact digest/source commit/build provenance. |
| DEP-FR-004 | Package source | Dependencies only from approved registries/sources; typosquat/private dependency-confusion controls. |
| DEP-FR-005 | Lock/pin | Production dependencies pinned via lockfile/digest; mutable floating versions prohibited. |
| DEP-FR-006 | License detection | Record declared/detected license(s), copyright notices and source reference. |
| DEP-FR-007 | License policy | Licenses classified APPROVED/REVIEW_REQUIRED/PROHIBITED by distribution/business model. |
| DEP-FR-008 | Copyleft review | Strong/network copyleft or reciprocal obligations require legal/IP review before inclusion. |
| DEP-FR-009 | Unknown license | Unknown/no-license package blocked until legal decision. |
| DEP-FR-010 | Notice obligations | Attribution/NOTICE/source-offer or other obligations tracked and packaged when applicable. |
| DEP-FR-011 | Commercial dependency | Track license key/subscription/redistribution/support/EOL terms for commercial components. |
| DEP-FR-012 | Vulnerability mapping | SBOM components correlated with CVE/advisories and internal risk. |
| DEP-FR-013 | Known exploited status | Known-exploited/advisory status feeds remediation priority. |
| DEP-FR-014 | Vulnerability exception | Risk acceptance time-bounded with compensating controls and affected releases. |
| DEP-FR-015 | EOL status | Track package/runtime/base image support/EOL and planned replacement. |
| DEP-FR-016 | Maintainer health | High-risk dependencies assessed for maintenance/release/signing provenance/abandonment. |
| DEP-FR-017 | Dependency necessity | New dependency requires documented purpose and alternative/existing capability review. |
| DEP-FR-018 | Critical library approval | Crypto/auth/parser/native/runtime-critical libraries require Security/Architecture approval. |
| DEP-FR-019 | Development dependencies | Build/dev/test dependencies inventoried because compromise can affect artifact. |
| DEP-FR-020 | Container OS packages | Base image and OS packages appear in SBOM/scans. |
| DEP-FR-021 | Frappe/ERPNext license | Framework/vendor component licenses and redistribution obligations tracked without modifying core ownership assumptions. |
| DEP-FR-022 | Generated/vendor code | Copied/generated snippets above trivial threshold require provenance/license record. |
| DEP-FR-023 | AI-generated code | AI output is treated as code authored for project and must pass provenance/license/duplication review tooling/policy where applicable. |
| DEP-FR-024 | Model assets | AI models, embedding models, datasets/prompts with third-party license/terms tracked separately in AI asset register. |
| DEP-FR-025 | Dependency update | Update goes through PR/tests/scans/license review and validation impact as relevant. |
| DEP-FR-026 | Automatic PRs | Dependabot/Renovate-style automation may propose updates but cannot auto-merge critical dependencies without gates. |
| DEP-FR-027 | Transitive change | Lockfile diff reviewed for unexpected new package/license/native binary. |
| DEP-FR-028 | Binary provenance | Prebuilt native binaries/images/plugins require trusted source/checksum/signature where available. |
| DEP-FR-029 | Vendor SBOM | Third-party appliances/connectors may ingest vendor SBOM/support evidence where available. |
| DEP-FR-030 | Acquisition export | Generate complete dependency/license/IP/vulnerability register for due diligence. |
| DEP-FR-031 | Removal | Unused dependency removed after confirming no required runtime/build/validation need. |
| DEP-FR-032 | No hidden fetch | Build cannot download undeclared executable/model/tool artifact from arbitrary URL. |
| DEP-FR-033 | License files | Required third-party notices/licenses shipped with appropriate product distributions. |
| DEP-FR-034 | SBOM retention | SBOM and vulnerability snapshot retained for each supported/released version. |
| DEP-FR-035 | Customer disclosure | Provide appropriate SBOM/security component disclosure under customer contract without exposing proprietary code. |
| DEP-FR-036 | No legal automation | Tool can classify/flag licenses but final ambiguous legal interpretation belongs authorized human/legal counsel. |
| SDLC-FR-001 | Secure SDLC policy | Security activities integrated into requirements, design, implementation, review, test, release and maintenance. |
| SDLC-FR-002 | SSDF mapping | Engineering process maps to NIST SSDF v1.1 practices; future v1.2 changes assessed separately when final. |
| SDLC-FR-003 | Security requirements | Security requirement IDs traced from threats/ASVS/API controls to code/tests. |
| SDLC-FR-004 | Branch protection | Protected branches, reviewed PRs, status checks and restricted force-push for production code. |

## SPEC_GAP triggers

Raise a SPEC_GAP rather than deciding, if you encounter: a missing signature/authorization/retention/
precision value, a conflict between two source documents, an entity without an owner, an event without a
producer, or any requirement that would need a regulated behaviour you cannot trace to
Document 104, Document 68 or Documents 106–115.
