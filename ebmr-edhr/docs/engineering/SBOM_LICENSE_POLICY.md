# SBOM / Third-Party License Management

**Derived from:** Document 104 (SPEC-ENG-008) — controlled source in `specs/`
**Purpose:** Dependency, SBOM and licence governance.
**Requirements:** DEP-FR-001..036 (36)

> This file is the working engineering standard. The controlled source is Document 104; where the two
> differ, the specification wins and this file is corrected.

## Requirements

| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| DEP-FR-001 | Dependency register | Inventory direct/transitive runtime/build/test dependencies with package/version/source/owner/purpose. | Complete inventory. |
| DEP-FR-002 | SBOM format | Generate machine-readable SPDX or CycloneDX-compatible SBOM per release/artifact. | Interoperability. |
| DEP-FR-003 | Artifact linkage | SBOM tied exact artifact digest/source commit/build provenance. | Accuracy. |
| DEP-FR-004 | Package source | Dependencies only from approved registries/sources; typosquat/private dependency-confusion controls. | Supply-chain. |
| DEP-FR-005 | Lock/pin | Production dependencies pinned via lockfile/digest; mutable floating versions prohibited. | Reproducibility. |
| DEP-FR-006 | License detection | Record declared/detected license(s), copyright notices and source reference. | IP. |
| DEP-FR-007 | License policy | Licenses classified APPROVED/REVIEW_REQUIRED/PROHIBITED by distribution/business model. | Governance. |
| DEP-FR-008 | Copyleft review | Strong/network copyleft or reciprocal obligations require legal/IP review before inclusion. | Acquisition readiness. |
| DEP-FR-009 | Unknown license | Unknown/no-license package blocked until legal decision. | IP protection. |
| DEP-FR-010 | Notice obligations | Attribution/NOTICE/source-offer or other obligations tracked and packaged when applicable. | Compliance. |
| DEP-FR-011 | Commercial dependency | Track license key/subscription/redistribution/support/EOL terms for commercial components. | Continuity. |
| DEP-FR-012 | Vulnerability mapping | SBOM components correlated with CVE/advisories and internal risk. | Security. |
| DEP-FR-013 | Known exploited status | Known-exploited/advisory status feeds remediation priority. | Risk. |
| DEP-FR-014 | Vulnerability exception | Risk acceptance time-bounded with compensating controls and affected releases. | Governance. |
| DEP-FR-015 | EOL status | Track package/runtime/base image support/EOL and planned replacement. | Lifecycle. |
| DEP-FR-016 | Maintainer health | High-risk dependencies assessed for maintenance/release/signing provenance/abandonment. | Supply-chain. |
| DEP-FR-017 | Dependency necessity | New dependency requires documented purpose and alternative/existing capability review. | Reduce attack surface. |
| DEP-FR-018 | Critical library approval | Crypto/auth/parser/native/runtime-critical libraries require Security/Architecture approval. | Higher scrutiny. |
| DEP-FR-019 | Development dependencies | Build/dev/test dependencies inventoried because compromise can affect artifact. | Supply-chain. |
| DEP-FR-020 | Container OS packages | Base image and OS packages appear in SBOM/scans. | Runtime visibility. |
| DEP-FR-021 | Frappe/ERPNext license | Framework/vendor component licenses and redistribution obligations tracked without modifying core ownership assumptions. | IP. |
| DEP-FR-022 | Generated/vendor code | Copied/generated snippets above trivial threshold require provenance/license record. | IP hygiene. |
| DEP-FR-023 | AI-generated code | AI output is treated as code authored for project and must pass provenance/license/duplication review tooling/policy where applicable. | AI development governance. |
| DEP-FR-024 | Model assets | AI models, embedding models, datasets/prompts with third-party license/terms tracked separately in AI asset register. | AI IP. |
| DEP-FR-025 | Dependency update | Update goes through PR/tests/scans/license review and validation impact as relevant. | Controlled change. |
| DEP-FR-026 | Automatic PRs | Dependabot/Renovate-style automation may propose updates but cannot auto-merge critical dependencies without gates. | Safe automation. |
| DEP-FR-027 | Transitive change | Lockfile diff reviewed for unexpected new package/license/native binary. | Visibility. |
| DEP-FR-028 | Binary provenance | Prebuilt native binaries/images/plugins require trusted source/checksum/signature where available. | Supply-chain. |
| DEP-FR-029 | Vendor SBOM | Third-party appliances/connectors may ingest vendor SBOM/support evidence where available. | Enterprise assurance. |
| DEP-FR-030 | Acquisition export | Generate complete dependency/license/IP/vulnerability register for due diligence. | Commercial value. |
| DEP-FR-031 | Removal | Unused dependency removed after confirming no required runtime/build/validation need. | Attack surface. |
| DEP-FR-032 | No hidden fetch | Build cannot download undeclared executable/model/tool artifact from arbitrary URL. | Reproducibility/security. |
| DEP-FR-033 | License files | Required third-party notices/licenses shipped with appropriate product distributions. | Compliance. |
| DEP-FR-034 | SBOM retention | SBOM and vulnerability snapshot retained for each supported/released version. | Historical evidence. |
| DEP-FR-035 | Customer disclosure | Provide appropriate SBOM/security component disclosure under customer contract without exposing proprietary code. | Enterprise. |
| DEP-FR-036 | No legal automation | Tool can classify/flag licenses but final ambiguous legal interpretation belongs authorized human/legal counsel. | Governance. |

## Enforcement

See `docs/generated/33_CODING_STANDARD_COMPLIANCE_MATRIX.md`,
`docs/generated/34_ARCHITECTURE_GUARDRAIL_MATRIX.md` and `.github/workflows/ci.yml`.

## Tests

- unknown license blocked
- copyleft review
- transitive package surprise
- critical CVE
- known-exploited package priority
- SBOM artifact digest match
- third-party notices
- AI model license appears in AI register
