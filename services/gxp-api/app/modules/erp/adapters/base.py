"""Shared httpx plumbing every vendor adapter (Documents 49/50/51) builds on. Real outbound HTTP calls --
the first in this codebase's regulated path (see SG-125: no live vendor sandbox is reachable from this
environment, so tests exercise this against `httpx.MockTransport`, never a live system).

`transport` in `AdapterConfig.extra` lets tests substitute an `httpx.MockTransport` for the real network
without changing a single line of adapter logic (httpx's own supported seam for this, not a bespoke one).
"""

import httpx

from app.modules.erp.provider import AdapterConfig, ERPCapabilities, ERPProvider
from app.mutation.errors import ErpAuthFailedError


def extract_retry_after_seconds(response: httpx.Response) -> float | None:
    """INT-FR-004: the vendor's own `Retry-After` response header (seconds form only -- the HTTP-date
    form exists but no vendor in this codebase's adapters is documented as using it, and guessing a
    date-parsing policy here is exactly the kind of unverified behaviour SG-125 already cautions
    against). Returns None on anything not a plain non-negative number, never raises."""
    raw = response.headers.get("retry-after")
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


class HttpAdapterBase(ERPProvider):
    vendor: str = "GENERIC"
    contract_version: str = "v1"
    supported_operations: tuple[str, ...] = ()
    health_path: str = "/"

    def __init__(self, config: AdapterConfig) -> None:
        if config.auth_method != "BASIC" and not config.auth_secret:
            raise ErpAuthFailedError(
                f"{self.vendor} instance has no usable credential for auth_method={config.auth_method}"
            )
        self.config = config

    def capabilities(self) -> ERPCapabilities:
        return ERPCapabilities(
            vendor=self.vendor,
            contract_version=self.config.contract_version or self.contract_version,
            supported_operations=self.supported_operations,
            reachable=True,
        )

    def _auth_headers(self) -> dict[str, str]:
        if self.config.auth_method == "API_KEY":
            return {"Authorization": f"token {self.config.auth_secret}"}
        if self.config.auth_method == "OAUTH2_CLIENT_CREDENTIALS":
            return {"Authorization": f"Bearer {self.config.auth_secret}"}
        return {}

    def _client(self) -> httpx.AsyncClient:
        kwargs: dict = {
            "base_url": self.config.base_url,
            "timeout": self.config.timeout_seconds,
            "headers": self._auth_headers(),
        }
        transport = self.config.extra.get("transport")
        if transport is not None:
            kwargs["transport"] = transport
        if self.config.auth_method == "BASIC":
            kwargs["auth"] = tuple((self.config.auth_secret or "").split(":", 1)) if self.config.auth_secret else None
        return httpx.AsyncClient(**kwargs)

    async def probe(self) -> bool:
        try:
            async with self._client() as client:
                response = await client.get(self.health_path)
                return response.status_code < 500
        except httpx.HTTPError:
            return False
