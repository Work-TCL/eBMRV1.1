"""Gateway identity/fingerprint generation for `enrollGateway()`/`rotateGatewayCertificate()`
(Document 43 section 4). EDGE-FR-002/EDGE-FR-020.

No real X.509 CSR/certificate issuance is implemented here, deliberately matching the server side's own
documented limitation (services/gxp-api/app/modules/edge/commands.py::GatewayEnrollmentResult docstring:
"no real PKI issuance exists in this codebase -- cert_chain -> the fingerprint captured at enrollment").
Building a real PKI client here while the server has nothing to issue against would be inventing a trust
mechanism the rest of the system cannot verify -- exactly the guessed-security-primitive risk AG-15 and
SEC-THR-024 (new auth mode requires threat review) exist to stop. Tracked as SG-187 (see
docs/generated/18_SPEC_GAPS.md) alongside SG-118/SG-120's existing "no real PKI" precedent.
"""

from __future__ import annotations

import hashlib
import secrets


def generate_gateway_fingerprint(host_identity: str) -> str:
    """A stable-looking but locally-generated identifier -- not a certificate fingerprint in the X.509
    sense. `host_identity` (hostname/serial/asset tag) is folded in only for operator readability in logs;
    the actual uniqueness/unforgeability comes from the random component, not the hostname."""
    random_component = secrets.token_hex(32)
    return hashlib.sha256(f"{host_identity}:{random_component}".encode()).hexdigest()