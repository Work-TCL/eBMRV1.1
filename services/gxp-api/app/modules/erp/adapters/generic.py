"""Document 51 (SPEC-ERP-004, MULTI-FR-001..024) — generic customer ERP adapter. Unlike the three named
vendors, a "generic ERP" has no fixed API shape at all, so this adapter's capability set and endpoint
mapping come entirely from `ErpInstance.capabilities["endpoint_map"]`
(`{"SYNC_MATERIAL_ITEM": "/api/items", "POST_GOODS_RECEIPT": "/api/goods-receipts", ...}`), configured per
customer at `registerERPInstance()` time (ERP-ARC-002/003 "adapter declares supported operations" applied
literally: a generic instance declares them via configuration instead of code). Every mapped endpoint is
called with the canonical payload verbatim -- no vendor-specific request shaping, since there is no vendor
to shape it for.

WP-07 completion pass -- transport modes beyond HTTP/REST (MULTI-FR-014/015/016), deliberately not built:

- MULTI-FR-014 (optional SOAP/WSDL adapter): no SOAP client library is a dependency of this codebase (no
  Document 104 justification exists for one -- SG-125's "no live vendor sandbox" already means a real WSDL
  contract could never be validated against, and the requirement's own wording is "when legacy ERP
  requires it": zero registered instances require it today). `endpoint_map`/`transport_mode` is this
  adapter's real extensibility point for when a genuine legacy-ERP customer profile needs it.
- MULTI-FR-015 (SFTP/CSV/XML/EDI batch exchange): CSV/XML parsing itself needs no new dependency (Python
  stdlib `csv`/`xml.etree` cover it), but SFTP transport does (e.g. `paramiko`) and, per MULTI-FR-015's
  own text, batch file exchange requires manifest/checksum/file-identity/acknowledgement/replay rules this
  codebase has never designed -- inventing that shape now would guess exactly the kind of untested
  integration-reliability behaviour SG-123/124 already decline to guess elsewhere in this module family.
- MULTI-FR-016 (direct read-only external DB access): genuinely impossible to build meaningfully without
  a real target schema (no customer has ever supplied one) -- the same class of gap as SG-121's "zero
  entities declared", not a missing feature so much as nothing concrete yet to build against. The
  governance half this pass *can* build without guessing a schema -- "may be supported only read-only
  under a customer-approved adapter" -- is `validate_erp_instance()` (MULTI-FR-024, `commands.py`): no
  GENERIC instance of any kind, DB-backed or otherwise, may post a write until certified.

MULTI-FR-023 (contract/certification tests via simulator/sandbox): every adapter in this module, including
this one, is exercised only against `httpx.MockTransport` (SG-125) -- `tests/test_erp_flow.py` already is
the simulator-based contract suite this requirement asks for, not a separate harness to build.
"""

from typing import Any

import httpx

from app.modules.erp.adapters.base import HttpAdapterBase, extract_retry_after_seconds
from app.modules.erp.provider import AdapterConfig, CanonicalOutboundCommand, ERPChangesPage, ERPProviderResponse


class GenericErpAdapter(HttpAdapterBase):
    vendor = "GENERIC"
    contract_version = "customer-configured-v1"
    health_path = "/"

    def __init__(self, config: AdapterConfig) -> None:
        super().__init__(config)
        self.endpoint_map: dict[str, str] = dict(config.extra.get("endpoint_map") or {})
        self.supported_operations = tuple(self.endpoint_map.keys())

    async def dispatch(self, command: CanonicalOutboundCommand) -> ERPProviderResponse:
        path = self.endpoint_map.get(command.command_type)
        if path is None:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"reason": "unsupported"})

        try:
            async with self._client() as client:
                response = await client.post(path, json=command.payload)
        except httpx.TimeoutException:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body=None, timed_out=True)
        except httpx.HTTPError as exc:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"exception": exc.__class__.__name__})

        body = _safe_json(response)
        external_reference = (body or {}).get("id") if isinstance(body, dict) else None
        return ERPProviderResponse(
            succeeded=response.status_code < 300, external_reference=str(external_reference) if external_reference else None,
            raw_status=response.status_code, raw_body=body,
            retry_after_seconds=extract_retry_after_seconds(response),
        )

    async def fetch_changes(self, entity_type: str, cursor: str | None) -> ERPChangesPage:
        path = self.endpoint_map.get(f"FETCH_{entity_type}")
        if path is None:
            return ERPChangesPage(records=[], next_cursor=cursor, has_more=False)

        params: dict[str, Any] = {"since": cursor} if cursor else {}
        try:
            async with self._client() as client:
                response = await client.get(path, params=params)
        except httpx.HTTPError:
            return ERPChangesPage(records=[], next_cursor=cursor, has_more=False)

        body = _safe_json(response) or {}
        records = body.get("records", []) if isinstance(body, dict) else []
        return ERPChangesPage(records=records, next_cursor=body.get("next_cursor", cursor), has_more=bool(body.get("has_more")))


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None
