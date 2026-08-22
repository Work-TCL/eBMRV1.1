# WP-10 — API & Event Contracts

## Operations

| Operation | Doc | State-changing |
|---|---|---|
| `POST /security/v1/threat-models` | 61 | yes |
| `POST /security/v1/threats` | 61 | yes |
| `POST /security/v1/threats/{id}/controls` | 61 | yes |
| `POST /security/v1/risks/{id}/accept` | 61 | yes |
| `POST /security/v1/exceptions` | 61 | yes |
| `GET /security/v1/control-matrix` | 61 | no |
| `GET /auth/login` | 62 | no |
| `GET /auth/callback` | 62 | no |
| `POST /auth/logout` | 62 | yes |
| `POST /security/v1/sessions/{id}/revoke` | 62 | yes |
| `POST /security/v1/service-identities` | 62 | yes |
| `POST /security/v1/identity-providers` | 62 | yes |
| `POST /security/v1/privileged-access/requests` | 63 | yes |
| `POST /security/v1/privileged-access/requests/{id}/approve` | 63 | yes |
| `POST /security/v1/support-sessions` | 63 | yes |
| `POST /security/v1/admin-commands/{code}:execute` | 63 | yes |
| `POST /security/v1/break-glass` | 63 | yes |
| `POST /security/v1/privileged-sessions/{id}/close` | 63 | yes |
| `POST /security/v1/outbound-destinations` | 64 | yes |
| `POST /security/v1/webhook-profiles` | 64 | yes |
| `GET /security/v1/api-inventory` | 64 | no |
| `POST /security/v1/secrets/{id}/rotate` | 65 | yes |
| `POST /security/v1/certificates:issue` | 65 | yes |
| `POST /security/v1/certificates/{id}/rotate` | 65 | yes |
| `POST /security/v1/certificates/{id}/revoke` | 65 | yes |
| `GET /security/v1/crypto-health` | 65 | no |
| `GET /security/v1/network-flows` | 66 | no |
| `GET /security/v1/deployment-security-profile` | 66 | no |
| `POST /security/v1/incidents` | 67 | yes |
| `POST /security/v1/incidents/{id}/containment` | 67 | yes |
| `POST /security/v1/incidents/{id}/evidence` | 67 | yes |
| `POST /security/v1/incidents/{id}/gxp-impact` | 67 | yes |
| `POST /security/v1/incidents/{id}/close` | 67 | yes |
| `POST /security/v1/vulnerabilities` | 68 | yes |
| `POST /security/v1/vulnerabilities/{id}/assess` | 68 | yes |
| `POST /security/v1/vulnerabilities/{id}/exceptions` | 68 | yes |
| `GET /security/v1/releases/{id}/security-evidence` | 68 | no |

## Events

| Event | Doc | Producer |
|---|---|---|
| `ThreatModelDraftCreated` | 61 | SPEC-SEC-001 |
| `ThreatRegistered` | 61 | SPEC-SEC-001 |
| `SecurityControlMapped` | 61 | SPEC-SEC-001 |
| `ResidualSecurityRiskAccepted` | 61 | SPEC-SEC-001 |
| `SecurityExceptionOpened` | 61 | SPEC-SEC-001 |
| `ThreatModelReviewRequired` | 61 | SPEC-SEC-001 |
| `AuthenticationSucceeded` | 62 | SPEC-SEC-002 |
| `AuthenticationFailed` | 62 | SPEC-SEC-002 |
| `MFARequired` | 62 | SPEC-SEC-002 |
| `SessionCreated` | 62 | SPEC-SEC-002 |
| `SessionRevoked` | 62 | SPEC-SEC-002 |
| `ExternalIdentityMapped` | 62 | SPEC-SEC-002 |
| `ServiceIdentityProvisioned` | 62 | SPEC-SEC-002 |
| `PrivilegedAccessRequested` | 63 | SPEC-SEC-003 |
| `PrivilegedAccessGranted` | 63 | SPEC-SEC-003 |
| `SupportSessionOpened` | 63 | SPEC-SEC-003 |
| `AdminCommandExecuted` | 63 | SPEC-SEC-003 |
| `BreakGlassActivated` | 63 | SPEC-SEC-003 |
| `PrivilegedSessionClosed` | 63 | SPEC-SEC-003 |
| `PrivilegedSessionReviewed` | 63 | SPEC-SEC-003 |
| `APIAccessDenied` | 64 | SPEC-SEC-004 |
| `RateLimitTriggered` | 64 | SPEC-SEC-004 |
| `SSRFBlocked` | 64 | SPEC-SEC-004 |
| `MaliciousUploadDetected` | 64 | SPEC-SEC-004 |
| `WebhookReplayDetected` | 64 | SPEC-SEC-004 |
| `DeprecatedAPIUsed` | 64 | SPEC-SEC-004 |
| `SecretAccessDenied` | 65 | SPEC-SEC-005 |
| `SecretRotated` | 65 | SPEC-SEC-005 |
| `CertificateIssued` | 65 | SPEC-SEC-005 |
| `CertificateRotated` | 65 | SPEC-SEC-005 |
| `CertificateRevoked` | 65 | SPEC-SEC-005 |
| `CryptoHealthFailed` | 65 | SPEC-SEC-005 |
| `KeyAccessAnomaly` | 65 | SPEC-SEC-005 |
| `ForbiddenNetworkPathDetected` | 66 | SPEC-SEC-006 |
| `TenantScopeMismatchDetected` | 66 | SPEC-SEC-006 |
| `WorkloadHardeningFailed` | 66 | SPEC-SEC-006 |
| `UnexpectedPublicExposureDetected` | 66 | SPEC-SEC-006 |
| `SecurityAlertRaised` | 67 | SPEC-SEC-007 |
| `SecurityIncidentOpened` | 67 | SPEC-SEC-007 |
| `IncidentContainmentExecuted` | 67 | SPEC-SEC-007 |
| `ForensicEvidencePreserved` | 67 | SPEC-SEC-007 |
| `SecurityGxPImpactAssessed` | 67 | SPEC-SEC-007 |
| `SecurityIncidentClosed` | 67 | SPEC-SEC-007 |
| `ReleaseSBOMGenerated` | 68 | SPEC-SEC-008 |
| `VulnerabilityRegistered` | 68 | SPEC-SEC-008 |
| `VulnerabilityAssessed` | 68 | SPEC-SEC-008 |
| `SecurityReleaseBlocked` | 68 | SPEC-SEC-008 |
| `ReleaseArtifactSigned` | 68 | SPEC-SEC-008 |
| `SecurityAdvisoryPublished` | 68 | SPEC-SEC-008 |

## Contract rules
- schemas committed before implementation
- canonical command/receipt/error/event envelopes
- `additionalProperties: false` on commands
- decimal quantities as strings with UOM
- registry entry in `37_API_EVENT_COMPATIBILITY_REGISTRY.md`
