"""Document 51 (SPEC-ERP-004, MULTI-FR-001..024) — Microsoft Dynamics 365 Finance & Supply Chain
adapter. Real `httpx` calls against D365 F&O's genuine OData v4 data entity surface (`/data/<Entity>`)
-- see SG-125 for why every test here runs against a local `httpx.MockTransport`, never a live instance.

| Canonical op                     | D365 F&O OData data entity                                     |
|-----------------------------------|--------------------------------------------------------------------|
| SYNC_MATERIAL_ITEM                 | GET  ReleasedProducts                                              |
| SYNC_SUPPLIER                      | GET  VendorsV2                                                     |
| GET_PRODUCTION_ORDER_REFERENCE     | GET  ProductionOrders('{id}')                                      |
| POST_GOODS_RECEIPT                 | POST InventJournalTrans (journal type = Movement, receipt)         |
| POST_CONSUMPTION                   | POST InventJournalTrans (journal type = Movement, issue)           |
| POST_PURCHASE_ORDER_REF            | POST PurchaseOrderHeadersV2                                        |
| POST_RESERVATION                   | POST InventoryOnhandReservations                                   |
| POST_RELEASE_AVAILABILITY          | POST InventJournalTrans (journal type = Movement, receipt, transfer from blocked) |

WP-07 completion pass (ERP-ARC-008/011/016) -- D365 F&O's real, standard OData data entity names for "PO
reference" and "reservation"; release-availability reuses the same InventJournalTrans entity the other
movement operations already use. No per-vendor detail exists in Document 51's own baseline for any of the
three, so these carry the same never-verified-against-a-live-tenant caveat SG-125 applies platform-wide.

MULTI-FR-011: every write payload must carry `dataAreaId` (D365 F&O's real, standard legal-entity/company
context field on every data entity) -- `dispatch()` fails closed with a structured `MISSING_DATA_AREA`
rejection rather than defaulting to a company, which would risk posting a GxP-originated transaction
against the wrong legal entity.
"""

from typing import Any

import httpx

from app.modules.erp.adapters.base import HttpAdapterBase, extract_retry_after_seconds
from app.modules.erp.provider import CanonicalOutboundCommand, ERPChangesPage, ERPProviderResponse

SUPPORTED_OPERATIONS = (
    "SYNC_MATERIAL_ITEM", "SYNC_SUPPLIER", "GET_PRODUCTION_ORDER_REFERENCE",
    "POST_GOODS_RECEIPT", "POST_CONSUMPTION",
    "POST_PURCHASE_ORDER_REF", "POST_RESERVATION", "POST_RELEASE_AVAILABILITY", "GET_PURCHASE_ORDER_REFERENCE",
)

_MOVEMENT_DIRECTION = {"POST_GOODS_RECEIPT": "Receipt", "POST_CONSUMPTION": "Issue", "POST_RELEASE_AVAILABILITY": "Receipt"}
_SYNC_ENTITY = {"MATERIAL": "ReleasedProducts", "SUPPLIER": "VendorsV2"}


class Dynamics365Adapter(HttpAdapterBase):
    vendor = "DYNAMICS_365"
    contract_version = "fo-odata-v4"
    supported_operations = SUPPORTED_OPERATIONS
    health_path = "/data/$metadata"

    async def dispatch(self, command: CanonicalOutboundCommand) -> ERPProviderResponse:
        if command.command_type not in self.supported_operations:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"reason": "unsupported"})

        is_write = command.command_type not in ("GET_PRODUCTION_ORDER_REFERENCE", "GET_PURCHASE_ORDER_REFERENCE")
        if is_write and not command.payload.get("dataAreaId"):
            # MULTI-FR-011: fail closed rather than default to a company/legal entity -- see module docstring.
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"reason": "missing_data_area", "exception": "MISSING_DATA_AREA"})

        try:
            async with self._client() as client:
                if command.command_type == "GET_PRODUCTION_ORDER_REFERENCE":
                    order_id = command.payload.get("external_order_id")
                    response = await client.get(f"/data/ProductionOrders('{order_id}')")
                elif command.command_type == "GET_PURCHASE_ORDER_REFERENCE":
                    po_id = command.payload.get("external_order_id")
                    response = await client.get(f"/data/PurchaseOrderHeadersV2('{po_id}')")
                elif command.command_type == "POST_PURCHASE_ORDER_REF":
                    response = await client.post("/data/PurchaseOrderHeadersV2", json=command.payload)
                elif command.command_type == "POST_RESERVATION":
                    response = await client.post("/data/InventoryOnhandReservations", json=command.payload)
                elif command.command_type in _MOVEMENT_DIRECTION:
                    body: dict[str, Any] = {**command.payload, "MovementDirection": _MOVEMENT_DIRECTION[command.command_type]}
                    response = await client.post("/data/InventJournalTrans", json=body)
                else:
                    return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"reason": "unsupported"})
        except httpx.TimeoutException:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body=None, timed_out=True)
        except httpx.HTTPError as exc:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"exception": exc.__class__.__name__})

        body = _safe_json(response)
        external_reference = (
            (body or {}).get("JournalNumber") or (body or {}).get("ProductionOrderNumber")
            or (body or {}).get("PurchId") or (body or {}).get("ReservationId")
        ) if isinstance(body, dict) else None
        return ERPProviderResponse(
            succeeded=response.status_code < 300, external_reference=external_reference,
            raw_status=response.status_code, raw_body=body,
            retry_after_seconds=extract_retry_after_seconds(response),
        )

    async def fetch_changes(self, entity_type: str, cursor: str | None) -> ERPChangesPage:
        entity = _SYNC_ENTITY.get(entity_type)
        if entity is None:
            return ERPChangesPage(records=[], next_cursor=cursor, has_more=False)

        params: dict[str, Any] = {"$top": 100}
        if cursor:
            params["$filter"] = f"ModifiedDateTime gt {cursor}"
        try:
            async with self._client() as client:
                response = await client.get(f"/data/{entity}", params=params)
        except httpx.HTTPError:
            return ERPChangesPage(records=[], next_cursor=cursor, has_more=False)

        body = _safe_json(response) or {}
        records = body.get("value", []) if isinstance(body, dict) else []
        return ERPChangesPage(records=records, next_cursor=cursor, has_more=len(records) == 100)


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None
