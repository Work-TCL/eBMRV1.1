# WP-10 — Function Contracts

Every function must specify typed inputs, validations, authorization/qualification/SoD, signature requirement, processing rules, DB reads/writes, transaction boundary, outputs, events, errors, idempotency and concurrency. Full rows: `docs/generated/03_FUNCTION_CATALOGUE.csv` filtered by module.

| Function | Doc | Caller | Inputs | Preconditions | Output |
|---|---|---|---|---|---|
| createThreatModelVersion() | 61 | Security Architect | system_version; methodology_version; scope; assets; boundaries | Architect authorized; architecture version exists | ThreatModelDraft |
| registerThreat() | 61 | Architect/Engineer | threat_model_id; asset/boundary; threat_type; abuse_case; evidence | Draft/open model | ThreatRecord |
| mapSecurityControl() | 61 | Security Architect | threat_id; control_id; preventive/detective/recovery; implementation refs | Threat exists; control catalogue valid | ThreatControlMapping |
| calculateSecurityRisk() | 61 | Security Risk Service | threat_id; impact inputs; likelihood inputs; methodology | Methodology effective | SecurityRiskAssessment |
| acceptResidualSecurityRisk() | 61 | Security/Quality/Business approver | risk_id; rationale; expiry/review date; signatures | Required authorities met; mitigations reviewed | SecurityRiskAcceptance |
| openSecurityException() | 61 | Security owner | control/requirement; reason; compensating controls; expiry | Exception authority; risk assessment exists | SecurityException |
| triggerThreatModelReview() | 61 | Change/SDLC/event | change_id; affected modules; trigger type | Trigger recognized | ThreatReviewTask |
| generateSecurityControlMatrix() | 61 | Validation/Security | threat model/version; deployment profile | Mappings complete | SecurityControlMatrix |
| validateIdentityToken() | 62 | API gateway/session middleware | JWT/assertion; expected issuer/audience/tenant | Provider config effective; signing keys trusted | AuthContext |
| createApplicationSession() | 62 | Web login callback | AuthContext; browser/device metadata | AuthContext valid; user active | ApplicationSession |
| evaluateMFARequirement() | 62 | Login/admin action | user/role/context/risk | MFA policy loaded | MFARequirement |
| revokeUserSessions() | 62 | Identity lifecycle/Security Admin | subject_id; reason | Authorized trigger | RevocationReceipt |
| mapExternalIdentity() | 62 | Federation callback/provisioning | issuer; subject; claims | Issuer trusted; mapping policy effective | IdentityMapping |
| provisionServiceIdentity() | 62 | Security Admin/Deployment automation | service name; scopes; tenant/site; auth method | Service registered; least-privilege scopes reviewed | ServiceIdentity |
| validateServiceToken() | 62 | Service middleware | client token/cert; target audience | Service identity active; cert/token valid | ServiceAuthContext |
| requireFreshAuthentication() | 62 | Sensitive admin operation | session_id; required_age/auth_strength | Session active | FreshAuthResult |
| requestPrivilegedAccess() | 63 | Admin/Support user | requested_role; tenant/site/resources; reason; ticket; duration | Named user/MFA; entitlement/request policy valid | PrivilegedAccessRequest |
| approvePrivilegedAccess() | 63 | Authorized approver | request_id; decision; comments | Approver distinct unless emergency; request not stale | PrivilegedGrant |
| evaluatePrivilegedGrant() | 63 | Admin middleware | subject; operation; resource; current time | Grant active; MFA/session valid | PrivilegedDecision |
| openSupportSession() | 63 | Support portal | grant_id; customer tenant; support case | Support entitlement/customer approval valid | SupportSession |
| executeControlledAdminCommand() | 63 | Admin UI/CLI | command_code; parameters; grant; reason | Command allowlisted; grant authorizes; validation passes | AdminCommandReceipt |
| activateBreakGlass() | 63 | Emergency operator | emergency identity/path; incident ID; reason | Emergency criteria; strong auth; alerting available | BreakGlassSession |
| closePrivilegedSession() | 63 | User/system expiry | session_id; outcome | Session exists | CloseReceipt |
| reviewPrivilegedSession() | 63 | Security reviewer | session_id; evidence; findings | Session closed | PrivilegedReview |
| authorizeObjectAccess() | 64 | API/service method | AuthContext; action; resource type/id; requested fields | Authenticated; tenant scope known | AuthorizationDecision |
| validateRequestSchema() | 64 | API middleware | operationId; request body/query/path | Schema version registered | ValidatedRequest |
| sanitizeRichText() | 64 | UI/API input | html/text; sanitizer policy version | Field explicitly rich-text capable | SanitizedContent |
| validateOutboundDestination() | 64 | Integration/file fetch | URL/host/service ID; purpose | Outbound operation allowed | DestinationDecision |
| validateFileUpload() | 64 | Upload endpoint | stream; filename; declared type; expected context | Authorized context; quotas | UploadReceipt |
| protectSpreadsheetExport() | 64 | Export service | rows/columns; field metadata | Export authorized | SafeExportDataset |
| enforceRateLimit() | 64 | Gateway/middleware | subject/client/IP/operation; cost | Rate policy loaded | RateLimitDecision |
| verifyWebhook() | 64 | Inbound integration | headers/cert/body; provider profile | Provider active | VerifiedWebhook |
| mapSafeErrorResponse() | 64 | API exception handler | internal error; correlation ID | None | PublicError |
| resolveSecret() | 65 | Service runtime | secret_ref; service identity; purpose | Identity authorized; ref active | SecretHandle/value |
| rotateSecret() | 65 | Security Admin/automation | secret_id; new credential material/generator; overlap policy | Rotation approved/eligible | SecretRotationResult |
| issueServiceCertificate() | 65 | PKI service | CSR; service identity; SANs; validity; profile | Identity/SAN/purpose approved | CertificateRef |
| rotateCertificate() | 65 | Automation/Admin | certificate_id; CSR | Within rotation window or forced; identity active | CertificateRotation |
| revokeCertificate() | 65 | Security/Incident | certificate serial; reason | Authority validated | RevocationReceipt |
| encryptSensitiveField() | 65 | Application crypto service | tenant/key context; plaintext bytes; AAD | Field configured encrypted; key available | EncryptedField |
| decryptSensitiveField() | 65 | Authorized service | ciphertext envelope; access context | Field access authorized; key available | Plaintext |
| hashEvidence() | 65 | Evidence/Audit/Edge | stream/bytes; crypto profile | Profile effective | DigestRef |
| generateNetworkPolicySet() | 66 | Infrastructure compiler | deployment_profile; service inventory; approved flow catalogue | Profile/version approved | NetworkPolicyBundle |
| validateServiceFlow() | 66 | CI/security test | source identity/zone; destination; protocol/port | Flow catalogue loaded | FlowDecision |
| issueSiteScopedEdgeNetworkProfile() | 66 | Deployment/Edge admin | site_id; gateway_id; required endpoints | Gateway/site identity valid | EdgeNetworkProfile |
| verifyTenantScopePropagation() | 66 | Security test/runtime assertion | AuthContext/job/event; expected tenant/site | Context exists | ScopeVerification |
| testForbiddenNetworkPath() | 66 | Continuous/periodic security test | source workload; destination target | Test environment/prod safe test profile | SegmentationTestResult |
| validateDeploymentHardening() | 66 | CI/deploy admission | workload manifest/image/security context | Hardening policy effective | HardeningResult |
| emitSecurityEvent() | 67 | Any service/Edge/security control | event_code; subject; tenant/site; target; result; correlation; metadata | Event schema registered; metadata redaction policy | SecurityEventReceipt |
| evaluateDetectionRules() | 67 | SIEM/detection worker | security events; rule versions; window | Rules effective | SecurityAlert[] |
| openSecurityIncident() | 67 | Security analyst/critical rule | alert/evidence refs; severity; affected scope | Not duplicate or reviewer chooses separate incident | SecurityIncident |
| executeIncidentContainment() | 67 | Incident commander | incident_id; containment command; target; approval if required | Command allowlisted; authority valid | ContainmentReceipt |
| preserveForensicEvidence() | 67 | Incident responder | source/path/object/log range; acquisition metadata | Authorized; source available | ForensicEvidenceRef |
| assessGxPIncidentImpact() | 67 | Security + QA | incident_id; affected systems/time/data; evidence | Incident scoped | GxPIncidentImpact |
| closeSecurityIncident() | 67 | Incident owner/approver | incident_id; root cause; actions; residual risk | Containment/recovery/impact/actions complete per policy | IncidentClosure |
| testDetectionRule() | 67 | Security engineering/CI | rule_id; synthetic event set | Rule draft/effective test environment | DetectionTestResult |
| generateReleaseSBOM() | 68 | CI release pipeline | artifact/image; dependency graph; build metadata | Build reproducible inputs available | SBOMRef |
| scanReleaseArtifact() | 68 | CI security gate | artifact digest; scanners/profiles | Artifact built and immutable | SecurityScanReport |
| evaluateSecurityReleaseGate() | 68 | CI/release approver | scan report; open vulnerabilities; exceptions; security-control tests | Policies effective | SecurityGateDecision |
| registerVulnerability() | 68 | Scanner/researcher/customer/security | component/version; finding; evidence; affected releases | Finding not duplicate or linked duplicate | VulnerabilityRecord |
| assessVulnerabilitySeverity() | 68 | Security team | vuln_id; CVSS/exploit/KEV/exposure/GxP impact inputs | Evidence current | VulnerabilityAssessment |
| approveVulnerabilityException() | 68 | Security/Risk/Quality if GxP | vuln_id; rationale; compensating controls; expiry | No active conflicting decision; authority valid | VulnerabilityException |
| signReleaseArtifact() | 68 | Release pipeline | artifact digest; provenance; signing identity | Security gate passed; builder trusted | SignedArtifactRef |
| verifyDeploymentArtifact() | 68 | Deployment admission | artifact/image; expected release | Signature/trust root/release metadata available | ArtifactVerification |
| publishSecurityAdvisory() | 68 | Security response | vulnerability; affected/fixed versions; mitigation; disclosure timing | Disclosure approved | SecurityAdvisory |
| createSecurityRegressionTest() | 68 | Engineering | vuln/threat ID; reproducer; expected fixed behavior | Fix design available | SecurityTestRef |
