"""Document 68 (SPEC-SEC-008) -- the CI / deploy-admission library functions Document 68 # 4 names for
the release-security gate and artifact verification. Pure functions; the persisted state lives in
`release_security_evidence` (written by the pipeline, read via the GET endpoint) and
`vulnerability_record` (Mutation Gateway commands in `supplychain_commands.py`).
"""

import uuid
from datetime import datetime, timezone

from app.mutation.errors import SecurityReleaseBlockedError, UntrustedArtifactError

# SDLC-FR-030: severities that block a release unless a non-expired, approved exception covers them.
_BLOCKING_SEVERITIES = {"HIGH", "CRITICAL"}


def evaluate_security_release_gate(
    *,
    scan_report: dict,
    open_vulnerabilities: list[dict],
    accepted_exceptions: list[dict] | None = None,
    control_test_results: dict | None = None,
    now: datetime | None = None,
) -> dict:
    """SDLC-FR-030: return PASS / WARN / BLOCK. BLOCK when any HIGH/CRITICAL vulnerability (or a
    known-exploited one at any severity) is unremediated and not covered by a currently-valid approved
    exception, or when a required security-control test failed. Raises `SecurityReleaseBlockedError`
    only when asked to enforce (`scan_report['enforce'] is True`); otherwise the caller inspects the
    decision."""
    current = now or datetime.now(timezone.utc)
    exceptions_by_vuln = {}
    for ex in (accepted_exceptions or []):
        expiry = ex.get("expiry")
        try:
            exp_dt = datetime.fromisoformat(expiry) if isinstance(expiry, str) else expiry
        except ValueError:
            exp_dt = None
        if ex.get("approved") and exp_dt is not None and exp_dt.tzinfo and exp_dt > current:
            exceptions_by_vuln[ex.get("vulnerability_id")] = ex

    blocking = []
    for v in open_vulnerabilities:
        sev = (v.get("severity") or "").upper()
        kev = bool(v.get("kev_status"))
        if v.get("state") in ("REMEDIATED", "CLOSED"):
            continue
        if (sev in _BLOCKING_SEVERITIES or kev) and v.get("vulnerability_id") not in exceptions_by_vuln:
            blocking.append({"vulnerability_id": v.get("vulnerability_id"), "severity": sev, "kev": kev})

    failed_controls = [name for name, ok in (control_test_results or {}).items() if not ok]
    if failed_controls:
        blocking.append({"control_tests_failed": failed_controls})

    warn = bool(scan_report.get("medium_findings")) and not blocking
    result = "BLOCK" if blocking else ("WARN" if warn else "PASS")
    decision = {
        "result": result,
        "blocking_findings": blocking,
        "accepted_exception_count": len(exceptions_by_vuln),
        "evaluated_at": current.isoformat(),
    }
    if result == "BLOCK" and scan_report.get("enforce"):
        raise SecurityReleaseBlockedError("Security release gate blocked the release", blocking_findings=blocking)
    return decision


def verify_deployment_artifact(
    *, artifact: dict, expected_release: dict, trust_roots: list[str] | None = None
) -> dict:
    """SDLC-FR-011 / Document 68 # 14: verify a deployment artifact's signature, digest, SBOM linkage,
    provenance builder and that it matches an approved release. Raises `UntrustedArtifactError`. A
    mutable `latest` tag is never a valid release identity."""
    reasons = []
    if artifact.get("tag") in ("latest", "", None) and not artifact.get("digest"):
        reasons.append("artifact identified only by a mutable tag / no digest")
    if artifact.get("digest") != expected_release.get("artifact_digest"):
        reasons.append("artifact digest does not match the approved release")
    if not artifact.get("signature"):
        reasons.append("artifact is not signed")
    elif trust_roots is not None and artifact.get("signed_by") not in set(trust_roots):
        reasons.append("artifact signed by an untrusted identity")
    if artifact.get("sbom_ref") != expected_release.get("sbom_ref"):
        reasons.append("SBOM reference does not match the approved release")
    builder = (artifact.get("provenance") or {}).get("builder")
    if builder is not None and builder not in (expected_release.get("provenance") or {}).get("allowed_builders", [builder]):
        reasons.append("build provenance names an untrusted builder")
    if expected_release.get("gate_result") not in ("PASS", "WARN"):
        reasons.append(f"approved release gate result is {expected_release.get('gate_result')!r}")

    if reasons:
        raise UntrustedArtifactError("Deployment artifact failed verification", reasons=reasons)
    return {"trusted": True, "release_id": expected_release.get("release_id")}


def generate_release_sbom(*, artifact_digest: str, components: list[dict], build_metadata: dict) -> dict:
    """SDLC-FR-009/013: produce a CycloneDX-shaped SBOM document linked to the artifact digest. This
    build emits the structure and a content hash; a real pipeline signs it."""
    from app.modules.security.crypto import hash_evidence
    import json

    doc = {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "metadata": {"timestamp": datetime.now(timezone.utc).isoformat(), "component": {"type": "application"},
                     "properties": build_metadata},
        "components": [
            {"type": c.get("type", "library"), "name": c["name"], "version": c["version"],
             "licenses": [{"license": {"id": c.get("license", "UNKNOWN")}}], "purl": c.get("purl")}
            for c in components
        ],
    }
    digest = hash_evidence(json.dumps(doc, sort_keys=True).encode(), algorithm="SHA-256")
    return {"sbom": doc, "artifact_digest": artifact_digest, "component_count": len(components),
            "sbom_digest": digest["digest"]}


async def emit_security_event(session, *, event_type: str, payload: dict, aggregate_id: uuid.UUID | None = None) -> None:
    from app.mutation.gateway import write_outbox_event

    await write_outbox_event(
        session, event_type=event_type, aggregate_type="security_event",
        aggregate_id=aggregate_id or uuid.uuid4(), aggregate_version=1, payload=payload,
        correlation_id=uuid.uuid4(),
    )
