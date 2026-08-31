"""Document 50 (SPEC-ERP-003, SAP-FR-001..025) — SAP S/4HANA adapter. Real `httpx` calls against SAP's
genuine OData v2 API service names (SAP API Business Hub) -- see SG-125 for why every test here runs
against a local `httpx.MockTransport`, never a live S/4HANA system.

Canonical operations implemented, mapped onto real SAP S/4HANA Cloud communication scenarios:

| Canonical op                     | SAP OData service / entity set                                  |
|-----------------------------------|-------------------------------------------------------------------|
| SYNC_MATERIAL_ITEM                 | GET API_PRODUCT_SRV/A_Product                                    |
| SYNC_SUPPLIER                      | GET API_BUSINESS_PARTNER/A_Supplier                              |
| GET_PRODUCTION_ORDER_REFERENCE     | GET API_PRODUCTION_ORDER_2_SRV/A_ProductionOrder_2('{id}')       |
| POST_GOODS_RECEIPT                 | POST API_MATERIAL_STOCK_SRV/A_MaterialDocumentHeader (mvt 101)   |
| POST_CONSUMPTION                   | POST API_MATERIAL_STOCK_SRV/A_MaterialDocumentHeader (mvt 261)   |
| POST_RETURN                        | POST API_MATERIAL_STOCK_SRV/A_MaterialDocumentHeader (mvt 262)   |
| POST_SCRAP_DESTRUCTION             | POST API_MATERIAL_STOCK_SRV/A_MaterialDocumentHeader (mvt 551)   |
| POST_FINISHED_GOODS_RECEIPT        | POST API_MATERIAL_STOCK_SRV/A_MaterialDocumentHeader (mvt 101, order-based) |
| POST_QUALITY_STATUS                | POST API_MATERIAL_STOCK_SRV/A_MaterialDocumentHeader (mvt 321/322 -- QI-to-unrestricted stock-type change) |
| POST_PURCHASE_ORDER_REF            | POST API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder                |
| POST_RESERVATION                   | POST API_MATERIAL_RESERVATION_SRV/A_ReservationDocumentHeader     |
| POST_RELEASE_AVAILABILITY          | POST API_MATERIAL_STOCK_SRV/A_MaterialDocumentHeader (mvt 343 -- release from blocked stock to unrestricted) |
| GET_MATERIAL_STOCK (SAP-FR-004)    | GET API_MATERIAL_STOCK_SRV/A_MaterialStock ($filter=Material)     |
| POST_TRANSFER (SAP-FR-008)         | POST API_MATERIAL_STOCK_SRV/A_MaterialDocumentHeader (mvt 311 -- storage-location-to-storage-location transfer) |

SAP-FR-007 (deep field-level IDoc/BAPI mapping for classic ECC-style scenarios, and the full 25-
requirement contract) is out of scope this pass beyond this shared operation set -- see SG-126. The four
rows above GET_MATERIAL_STOCK (WP-07 completion pass, ERP-ARC-008/011/016) are this pass's own choice of
SAP's real, standard OData service/movement-type names for "PO reference", "reservation" and "release
blocked stock" -- no per-vendor detail exists in Document 50's own baseline for any of the three, so these
carry the same never-verified-against-a-live-tenant caveat SG-125 applies platform-wide, not a
specification-sourced mapping like the rows above them.

SAP-FR-010: movement type codes are overridable per instance (`ErpInstance.capabilities.
movement_type_overrides`), not hardcoded across customers -- see `__init__`. SAP-FR-020: every
state-changing call fetches a CSRF token first (`_csrf_headers`) -- SAP OData v2's own mandatory
mechanic, handled entirely in this client layer, never surfaced to commands.py. SAP-FR-018 (OData
`$batch`) and SAP-FR-023 (custom BAPI/RFC) are not built this pass: `$batch`'s only real value is
against a live tenant's actual batching behaviour (SG-125 -- nothing here can meaningfully test it), and
BAPI/RFC integration is explicitly "not assumed common baseline" (SAP-FR-023's own acceptance intent) --
a genuine customer-specific adapter profile, not a default capability.

SAP-FR-016: posting/document dates are never derived or defaulted by this adapter -- `command.payload`
carries whatever date fields the calling GxP domain service supplies verbatim, unmodified, alongside the
canonical envelope's own timestamps (the actual GxP physical-occurrence time, always server-authoritative
per DATA-FR-018). Inventing a posting-date derivation rule here would be guessing an integration/business
policy Document 50 names but never defines (same class of gap SG-124 already declines to guess for
reconciliation tolerances).
"""

from typing import Any

import httpx

from app.modules.erp.adapters.base import HttpAdapterBase, extract_retry_after_seconds
from app.modules.erp.provider import AdapterConfig, CanonicalOutboundCommand, ERPChangesPage, ERPProviderResponse

SUPPORTED_OPERATIONS = (
    "SYNC_MATERIAL_ITEM", "SYNC_SUPPLIER", "GET_PRODUCTION_ORDER_REFERENCE",
    "POST_GOODS_RECEIPT", "POST_CONSUMPTION", "POST_RETURN", "POST_SCRAP_DESTRUCTION",
    "POST_FINISHED_GOODS_RECEIPT", "POST_QUALITY_STATUS",
    "POST_PURCHASE_ORDER_REF", "POST_RESERVATION", "POST_RELEASE_AVAILABILITY",
    "GET_PURCHASE_ORDER_REFERENCE", "GET_MATERIAL_STOCK", "POST_TRANSFER",
)

_MOVEMENT_TYPE = {
    "POST_GOODS_RECEIPT": "101",
    "POST_CONSUMPTION": "261",
    "POST_RETURN": "262",
    "POST_SCRAP_DESTRUCTION": "551",
    "POST_FINISHED_GOODS_RECEIPT": "101",
    "POST_QUALITY_STATUS": "321",
    "POST_RELEASE_AVAILABILITY": "343",
    "POST_TRANSFER": "311",  # SAP-FR-008: standard plant/storage-location-to-storage-location transfer
}

_SYNC_ENTITY_SET = {"MATERIAL": "A_Product", "SUPPLIER": "A_Supplier"}


class SapS4HanaAdapter(HttpAdapterBase):
    vendor = "SAP_S4HANA"
    contract_version = "s4hana-cloud-odata-v2"
    supported_operations = SUPPORTED_OPERATIONS
    health_path = "/API_PRODUCT_SRV/$metadata"

    def __init__(self, config: AdapterConfig) -> None:
        super().__init__(config)
        # SAP-FR-010: movement type codes are customer-configured (per-instance override), not
        # hardcoded across customers -- module defaults apply wherever an instance names no override.
        self.movement_type = {**_MOVEMENT_TYPE, **(config.extra.get("movement_type_overrides") or {})}

    async def _csrf_headers(self, client: httpx.AsyncClient) -> dict[str, str]:
        """SAP-FR-020: SAP OData v2 requires a CSRF token fetched via a GET carrying
        `X-CSRF-Token: Fetch` before any state-changing POST; the token (and any session cookie SAP
        sets alongside it) is then replayed on the POST. Client-layer concern only -- GxP domain code
        (commands.py) never sees or reasons about SAP session mechanics."""
        try:
            response = await client.get(self.health_path, headers={"X-CSRF-Token": "Fetch"})
        except httpx.HTTPError:
            return {}
        token = response.headers.get("x-csrf-token")
        return {"X-CSRF-Token": token} if token else {}

    async def dispatch(self, command: CanonicalOutboundCommand) -> ERPProviderResponse:
        if command.command_type not in self.supported_operations:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"reason": "unsupported"})

        is_write = command.command_type not in ("GET_PRODUCTION_ORDER_REFERENCE", "GET_PURCHASE_ORDER_REFERENCE", "GET_MATERIAL_STOCK")
        try:
            async with self._client() as client:
                csrf_headers = await self._csrf_headers(client) if is_write else {}
                if command.command_type == "GET_PRODUCTION_ORDER_REFERENCE":
                    order_id = command.payload.get("external_order_id")
                    response = await client.get(f"/API_PRODUCTION_ORDER_2_SRV/A_ProductionOrder_2('{order_id}')")
                elif command.command_type == "GET_PURCHASE_ORDER_REFERENCE":
                    po_id = command.payload.get("external_order_id")
                    response = await client.get(f"/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder('{po_id}')")
                elif command.command_type == "GET_MATERIAL_STOCK":
                    material = command.payload.get("material_number")
                    response = await client.get("/API_MATERIAL_STOCK_SRV/A_MaterialStock", params={"$filter": f"Material eq '{material}'"})
                elif command.command_type == "POST_PURCHASE_ORDER_REF":
                    response = await client.post("/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder", json=command.payload, headers=csrf_headers)
                elif command.command_type == "POST_RESERVATION":
                    response = await client.post("/API_MATERIAL_RESERVATION_SRV/A_ReservationDocumentHeader", json=command.payload, headers=csrf_headers)
                elif command.command_type in self.movement_type:
                    body: dict[str, Any] = {**command.payload, "GoodsMovementCode": self.movement_type[command.command_type]}
                    response = await client.post("/API_MATERIAL_STOCK_SRV/A_MaterialDocumentHeader", json=body, headers=csrf_headers)
                else:
                    return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"reason": "unsupported"})
        except httpx.TimeoutException:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body=None, timed_out=True)
        except httpx.HTTPError as exc:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"exception": exc.__class__.__name__})

        body = _safe_json(response)
        external_reference = (
            (body or {}).get("MaterialDocument") or (body or {}).get("ProductionOrder")
            or (body or {}).get("PurchaseOrder") or (body or {}).get("ReservationDocument")
        ) if isinstance(body, dict) else None
        return ERPProviderResponse(
            succeeded=response.status_code < 300, external_reference=external_reference,
            raw_status=response.status_code, raw_body=body,
            retry_after_seconds=extract_retry_after_seconds(response),
        )

    async def fetch_changes(self, entity_type: str, cursor: str | None) -> ERPChangesPage:
        entity_set = _SYNC_ENTITY_SET.get(entity_type)
        if entity_set is None:
            return ERPChangesPage(records=[], next_cursor=cursor, has_more=False)

        params: dict[str, Any] = {"$top": 100}
        if cursor:
            params["$filter"] = f"LastChangeDateTime gt datetime'{cursor}'"
        try:
            async with self._client() as client:
                response = await client.get(f"/API_PRODUCT_SRV/{entity_set}" if entity_type == "MATERIAL" else f"/API_BUSINESS_PARTNER/{entity_set}", params=params)
        except httpx.HTTPError:
            return ERPChangesPage(records=[], next_cursor=cursor, has_more=False)

        body = _safe_json(response) or {}
        records = (body.get("d", {}) or {}).get("results", []) if isinstance(body, dict) else []
        return ERPChangesPage(records=records, next_cursor=cursor, has_more=len(records) == 100)


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None
