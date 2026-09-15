"""Thin HTTP client for the 6 server APIs Document 43 section 8 declares, plus the human-authenticated
enrollment/cert-rotation signature ceremony endpoints (services/gxp-api/app/modules/edge/router.py) and
the standard GxP login endpoint (services/gxp-api/app/modules/iam/router.py -- `POST /auth/token`).

`enroll()`/`rotate_certificate()` are the only two calls that require an authenticated *human* actor
(Installer/Site Admin per Document 43 section 2) -- everything else uses the gateway's own service-identity
bearer credential (SG-120), never a human session.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import httpx


@dataclass
class GatewayCredential:
    identity_id: str
    bearer_token: str

    def as_header(self) -> dict:
        return {"Authorization": f"Bearer {self.bearer_token}"}


class EdgeApiClient:
    def __init__(self, base_url: str, http_client: httpx.AsyncClient | None = None) -> None:
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(base_url=base_url, timeout=30.0)
        if http_client is None:
            self._client.base_url = httpx.URL(base_url)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # -- human-authenticated onboarding flow --------------------------------------------------------

    async def login(self, username: str, password: str) -> str:
        response = await self._client.post("/auth/token", data={"username": username, "password": password})
        response.raise_for_status()
        return response.json()["access_token"]

    async def request_enrollment_signature_challenge(self, jwt: str, bootstrap_token: str, gateway_fingerprint: str) -> dict:
        response = await self._client.post(
            "/edge/v1/enrollments/signature-challenges",
            headers={"Authorization": f"Bearer {jwt}"},
            json={"bootstrap_token": bootstrap_token, "gateway_fingerprint": gateway_fingerprint},
        )
        response.raise_for_status()
        return response.json()

    async def enroll(
        self, jwt: str, *, bootstrap_token: str, site_id: str, gateway_fingerprint: str,
        challenge_id: str, reauth_password: str, reason: str,
    ) -> dict:
        response = await self._client.post(
            "/edge/v1/enrollments",
            headers={"Authorization": f"Bearer {jwt}"},
            json={
                "idempotency_key": str(uuid.uuid4()),
                "bootstrap_token": bootstrap_token,
                "site_id": site_id,
                "gateway_fingerprint": gateway_fingerprint,
                "challenge_id": challenge_id,
                "reauth_password": reauth_password,
                "reason": reason,
            },
        )
        response.raise_for_status()
        return response.json()

    async def request_certificate_rotation_challenge(self, jwt: str, gateway_id: str) -> dict:
        response = await self._client.post(
            f"/edge/v1/gateways/{gateway_id}/signature-challenges",
            headers={"Authorization": f"Bearer {jwt}"},
            json={"action": "certificate_rotation"},
        )
        response.raise_for_status()
        return response.json()

    async def rotate_certificate(
        self, jwt: str, gateway_id: str, *, expected_version: int, new_fingerprint: str,
        challenge_id: str, reauth_password: str, reason: str,
    ) -> dict:
        response = await self._client.post(
            f"/edge/v1/gateways/{gateway_id}/certificate-rotation",
            headers={"Authorization": f"Bearer {jwt}"},
            json={
                "idempotency_key": str(uuid.uuid4()),
                "expected_version": expected_version,
                "new_fingerprint": new_fingerprint,
                "challenge_id": challenge_id,
                "reauth_password": reauth_password,
                "reason": reason,
            },
        )
        response.raise_for_status()
        return response.json()

    # -- machine-driven runtime calls (gateway service-identity credential) -------------------------

    def bind_service_identity(self, credential: GatewayCredential) -> httpx.AsyncClient:
        """Returns an httpx client pre-armed with the service-identity bearer header, for forwarder.py/
        health reporting -- these never see a human JWT."""
        self._client.headers.update(credential.as_header())
        return self._client