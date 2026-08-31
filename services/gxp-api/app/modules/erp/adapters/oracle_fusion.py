"""Document 51 (SPEC-ERP-004, MULTI-FR-001..024) — Oracle Fusion Cloud SCM adapter. Real `httpx` calls
against Oracle's genuine REST API surface (`/fscmRestApi/resources/<version>/<resource>`) -- see SG-125
for why every test here runs against a local `httpx.MockTransport`, never a live Fusion instance.

| Canonical op                     | Oracle Fusion REST resource                                   |
|-----------------------------------|------------------------------------------------------------------|
| SYNC_MATERIAL_ITEM                 | GET  items                                                       |
| SYNC_SUPPLIER                      | GET  suppliers                                                   |
| GET_PRODUCTION_ORDER_REFERENCE     | GET  workOrders/{id}                                              |
| POST_GOODS_RECEIPT                 | POST inventoryTransactions (transactionType=Miscellaneous receipt)|
| POST_CONSUMPTION                   | POST inventoryTransactions (transactionType=Miscellaneous issue)  |
| POST_RETURN                        | POST inventoryTransactions (transactionType=Miscellaneous receipt, reason=RETURN) |
| POST_PURCHASE_ORDER_REF            | POST purchaseOrders                                              |
| POST_RESERVATION                   | POST inventoryReservations                                       |
| POST_RELEASE_AVAILABILITY          | POST inventoryTransactions (transactionType=Miscellaneous receipt, subinventory transfer from hold) |

WP-07 completion pass (ERP-ARC-008/011/016) -- Oracle Fusion's real, standard REST resource names for
"PO reference" and "reservation"; release-availability reuses the same inventoryTransactions resource the
other movement operations already use. No per-vendor detail exists in Document 51's own baseline for any
of the three, so these carry the same never-verified-against-a-live-tenant caveat SG-125 applies
platform-wide.

MULTI-FR-005: Oracle's own lot/serial reference (`LotNumber`/`SerialNumber` on `inventoryTransactions`
payloads) is preserved verbatim in the outbound payload and, on the inbound side, recorded through the
same `MATERIAL_LOT`/`SERIAL` `ErpExternalMapping` entity types every vendor shares (ERP-ARC-020) --
internal GxP genealogy is never derived from it. MULTI-FR-006: this adapter never requests or assumes
any Oracle privilege beyond the specific REST resources listed above -- the service account's actual
scope is a customer-side Oracle IAM configuration concern, out of this codebase's control, but the
adapter's own capability declaration (`SUPPORTED_OPERATIONS`) is the complete, minimal set it will ever
call, so the customer's grant can be scoped to exactly that set with no unused permission surface.
"""

from typing import Any

import httpx

from app.modules.erp.adapters.base import HttpAdapterBase, extract_retry_after_seconds
from app.modules.erp.provider import CanonicalOutboundCommand, ERPChangesPage, ERPProviderResponse

SUPPORTED_OPERATIONS = (
    "SYNC_MATERIAL_ITEM", "SYNC_SUPPLIER", "GET_PRODUCTION_ORDER_REFERENCE",
    "POST_GOODS_RECEIPT", "POST_CONSUMPTION", "POST_RETURN",
    "POST_PURCHASE_ORDER_REF", "POST_RESERVATION", "POST_RELEASE_AVAILABILITY", "GET_PURCHASE_ORDER_REFERENCE",
)

_API_ROOT = "/fscmRestApi/resources/11.13.18.05"
_TRANSACTION_TYPE = {
    "POST_GOODS_RECEIPT": "Miscellaneous receipt",
    "POST_CONSUMPTION": "Miscellaneous issue",
    "POST_RETURN": "Miscellaneous receipt",
    "POST_RELEASE_AVAILABILITY": "Miscellaneous receipt",
}
_SYNC_RESOURCE = {"MATERIAL": "items", "SUPPLIER": "suppliers"}


class OracleFusionAdapter(HttpAdapterBase):
    vendor = "ORACLE_FUSION"
    contract_version = "fusion-scm-11.13.18.05"
    supported_operations = SUPPORTED_OPERATIONS
    health_path = f"{_API_ROOT}/items?limit=1"

    async def dispatch(self, command: CanonicalOutboundCommand) -> ERPProviderResponse:
        if command.command_type not in self.supported_operations:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"reason": "unsupported"})

        try:
            async with self._client() as client:
                if command.command_type == "GET_PRODUCTION_ORDER_REFERENCE":
                    order_id = command.payload.get("external_order_id")
                    response = await client.get(f"{_API_ROOT}/workOrders/{order_id}")
                elif command.command_type == "GET_PURCHASE_ORDER_REFERENCE":
                    po_id = command.payload.get("external_order_id")
                    response = await client.get(f"{_API_ROOT}/purchaseOrders/{po_id}")
                elif command.command_type == "POST_PURCHASE_ORDER_REF":
                    response = await client.post(f"{_API_ROOT}/purchaseOrders", json=command.payload)
                elif command.command_type == "POST_RESERVATION":
                    response = await client.post(f"{_API_ROOT}/inventoryReservations", json=command.payload)
                elif command.command_type in _TRANSACTION_TYPE:
                    body: dict[str, Any] = {**command.payload, "transactionType": _TRANSACTION_TYPE[command.command_type]}
                    response = await client.post(f"{_API_ROOT}/inventoryTransactions", json=body)
                else:
                    return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"reason": "unsupported"})
        except httpx.TimeoutException:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body=None, timed_out=True)
        except httpx.HTTPError as exc:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"exception": exc.__class__.__name__})

        body = _safe_json(response)
        external_reference = (
            (body or {}).get("TransactionId") or (body or {}).get("WorkOrderNumber")
            or (body or {}).get("OrderNumber") or (body or {}).get("ReservationId")
        ) if isinstance(body, dict) else None
        return ERPProviderResponse(
            succeeded=response.status_code < 300, external_reference=str(external_reference) if external_reference else None,
            raw_status=response.status_code, raw_body=body,
            retry_after_seconds=extract_retry_after_seconds(response),
        )

    async def fetch_changes(self, entity_type: str, cursor: str | None) -> ERPChangesPage:
        resource = _SYNC_RESOURCE.get(entity_type)
        if resource is None:
            return ERPChangesPage(records=[], next_cursor=cursor, has_more=False)

        params: dict[str, Any] = {"limit": 100}
        if cursor:
            params["q"] = f"LastUpdateDate>{cursor}"
        try:
            async with self._client() as client:
                response = await client.get(f"{_API_ROOT}/{resource}", params=params)
        except httpx.HTTPError:
            return ERPChangesPage(records=[], next_cursor=cursor, has_more=False)

        body = _safe_json(response) or {}
        records = body.get("items", []) if isinstance(body, dict) else []
        return ERPChangesPage(records=records, next_cursor=cursor, has_more=bool(body.get("hasMore")))


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None
