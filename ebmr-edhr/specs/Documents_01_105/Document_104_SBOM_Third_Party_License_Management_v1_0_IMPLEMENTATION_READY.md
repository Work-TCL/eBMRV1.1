# US eBMR / eDHR Regulated Manufacturing Platform
## Document 104 — SBOM / Third-Party License Management — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-ENG-008  
**Parent Documents:** Documents 01–96  
**Primary Dependencies:** Documents 61–68, 97–103, 105  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This document is a normative engineering-control source for Claude Code/Codex and human developers.

Every implementation must preserve:
- stable requirement IDs;
- explicit function input/output/error contracts;
- authorization/SoD/signature behavior;
- data owner and transaction boundaries;
- API/event schema and compatibility;
- validation/test evidence;
- security/dependency/license controls;
- actual rather than claimed CI/release evidence.

Where regulated behavior is not specified, create a `SPEC_GAP` and block the guess.

# Cross-Document Non-Negotiables

- Frappe/ERPNext core remains unmodified.
- GxP-authoritative writes flow through proprietary services/Mutation Gateway.
- No generic CRUD of released regulated records.
- No signature, authorization, audit, retention, data-owner or validation bypass.
- PostgreSQL is GxP authority; MariaDB/read models/cache/search/message/orchestration are not competing sources of truth.
- Transactional outbox/idempotent consumers are used where specified.
- Production release must match approved validated release authorization.
- AI remains advisory unless a future explicitly approved controlled specification authorizes a different risk class.

# 1. Objective

Define dependency inventory, SBOM generation, license/IP approval, vulnerability/EOL management and acquisition-ready third-party evidence.

# 2. Actors / Components

- Developer
- Dependency Bot
- Security
- Architecture
- Legal/IP
- Release Engineer
- Procurement
- Acquirer/Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
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

# 4. Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB or artifact effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| registerDependency() | Developer/Dependency bot | ecosystem; package; version; purpose; source | Package resolved from approved source | Creates/updates dependency candidate record | DependencyRecord | DependencyRegistered |
| evaluateDependencyLicense() | License service/Legal | dependency; detected licenses; distribution context | License metadata available | Applies policy classification, flags legal review | LicenseDecision | DependencyLicenseEvaluated |
| evaluateDependencySecurity() | SCA/Security | dependency/SBOM; vulnerabilities; exploitability/exposure | Scan/advisory data current | Creates risk/remediation/exception candidates | DependencySecurityDecision | DependencySecurityEvaluated |
| approveDependency() | Architecture/Security/Legal as required | dependency candidate; purpose; alternatives; license/security decisions | Required reviews complete | Marks version/source approved for defined scope | ApprovedDependency | DependencyApproved |
| generateReleaseSBOM() | Release pipeline | artifact digest; lockfiles/images; provenance | Artifact built | Generates SPDX/CycloneDX-compatible SBOM and hash/ref | SBOMArtifact | ReleaseSBOMGenerated |
| validateLockfileChange() | CI | old/new lockfile; manifest | Diff parsable | Flags unapproved/unexpected/transitive/license/native changes | LockfileDecision | UnexpectedDependencyChange |
| generateThirdPartyNotices() | Release tooling | release SBOM; license obligations | All licenses classified | Builds required notices/attributions/source-offer metadata | ThirdPartyNoticePackage | ThirdPartyNoticesGenerated |
| generateAcquisitionDependencyDossier() | Engineering/Legal | all supported releases; dependency registry | Data available | Produces inventory of licenses, vulnerabilities, exceptions, EOL, ownership and proprietary boundaries | DependencyDossier | DependencyDossierGenerated |

# 5. Dependency Record

```yaml
ecosystem:
name:
version:
source_registry:
integrity_hash:
direct_or_transitive:
runtime_build_test:
purpose:
owner:
license_expression:
license_status:
security_status:
eol_date:
approved_scope:
affected_artifacts: []
```


# 6. License Policy Categories

Examples of policy categories—not legal conclusions:
- `APPROVED_PERMISSIVE`
- `APPROVED_COMMERCIAL`
- `REVIEW_REQUIRED_RECIPROCAL`
- `REVIEW_REQUIRED_UNKNOWN_OR_CUSTOM`
- `PROHIBITED_BY_PRODUCT_POLICY`

Final policy must be approved by company counsel/ownership, especially before acquisition/distribution.

# 7. SBOM Scope

Release SBOM should include where technically applicable:
- Node/Python dependencies;
- Frappe/ERPNext/framework versions;
- OS/container packages;
- native libraries;
- Edge plugins/drivers;
- bundled third-party binaries;
- relevant model runtime dependencies.

AI model/dataset licensing additionally belongs Document105 AI asset register.

# 8. Due-Diligence Evidence

The dependency dossier should distinguish:
- proprietary source owned by company;
- open-source components and obligations;
- customer-owned connectors/customizations;
- third-party commercial modules;
- generated code/assets;
- unresolved IP/license exceptions;
- unsupported/EOL components;
- vulnerability remediation status.

# 9. Mandatory Test / Enforcement Catalogue

- unknown license blocked
- copyleft review
- transitive package surprise
- critical CVE
- known-exploited package priority
- SBOM artifact digest match
- third-party notices
- AI model license appears in AI register

# 10. Acceptance Criteria

Every shipped artifact has an exact SBOM and an approved dependency/license/security record sufficient for customer and acquisition due diligence.

# 11. Claude Code / Codex Prohibitions

- Never interpret ambiguous license terms solely with automated classifier.
- Never add package with no license/provenance.
- Never allow dependency bot to auto-merge critical update around review gates.
- Never ship undeclared binary/model fetched during build.
