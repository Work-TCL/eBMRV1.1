"""Document 49 (SPEC-ERP-002, ENXT-FR-001..024) — ERPNext adapter. Real `httpx` calls against ERPNext's
genuine REST surface (`/api/resource/<Doctype>`, token auth via `Authorization: token <key>:<secret>`) --
see SG-125 for why every test here runs against a local `httpx.MockTransport`, never a live bench.

Canonical operations implemented (ENXT-FR-002..015's procurement/inventory/quality/manufacturing scope,
the shared subset every adapter maps -- see provider.py's PROVIDER_OPERATIONS docstring for the full list
and SG-126 for what is declared-but-not-exercised beyond this subset):

| Canonical op                     | ERPNext doctype / endpoint                          |
|-----------------------------------|-----------------------------------------------------|
| SYNC_MATERIAL_ITEM                 | GET /api/resource/Item                             |
| SYNC_SUPPLIER                       | GET /api/resource/Supplier                         |
| SYNC_WAREHOUSE_LOCATION             | GET /api/resource/Warehouse                        |
| SYNC_UOM                            | GET /api/resource/UOM                              |
| POST_GOODS_RECEIPT                  | POST /api/resource/Stock Entry (purpose=Material Receipt) |
| POST_CONSUMPTION                    | POST /api/resource/Stock Entry (purpose=Material Issue)   |
| POST_RETURN                         | POST /api/resource/Stock Entry (purpose=Material Receipt, is_return) |
| POST_SCRAP_DESTRUCTION              | POST /api/resource/Stock Entry (purpose=Material Issue, target=Scrap) |
| POST_FINISHED_GOODS_RECEIPT         | POST /api/resource/Stock Entry (purpose=Manufacture) |
| POST_QUALITY_STATUS                 | POST /api/resource/Quality Inspection              |
| GET_PRODUCTION_ORDER_REFERENCE      | GET /api/resource/Work Order/{name}                |
| POST_PURCHASE_ORDER_REF             | POST /api/resource/Purchase Order                  |
| POST_RESERVATION                    | POST /api/resource/Stock Reservation Entry         |
| POST_RELEASE_AVAILABILITY           | POST /api/resource/Stock Entry (purpose=Material Transfer) |

WP-07 completion pass (ERP-ARC-008/011/016): Document 49's own spec text names Purchase Order explicitly
(getPurchaseOrder()/createPurchaseOrder(), §3) -- high confidence. Reservation/release-availability have
no vendor-specific detail anywhere in the baseline (neither ERP-ARC-011/016 nor Document 49 elaborate a
vendor doctype); "Stock Reservation Entry" and a purpose="Material Transfer" Stock Entry are this pass's
own choice of ERPNext's real, standard doctypes for "reserve stock" and "move stock between locations"
respectively -- plausible and standard, carrying the same never-verified-against-a-live-tenant caveat
SG-125 already applies platform-wide, not a specification-sourced mapping like the rows above it.

ENXT-FR-018 (custom field policy): this adapter assumes no ERPNext-side custom fields exist -- every
canonical operation above maps onto ERPNext's own stock/standard doctype fields only. If a customer
deployment needs an external-reference custom field (e.g. a GxP lot id on Item), it must be installed by
a versioned, documented ERPNext Frappe app migration on the customer's own bench (this codebase's own
`.claude/rules/00-architecture-non-negotiables.md` AG-01 forbids this codebase from ever touching another
system's schema directly) -- tracked as deployment/customer-onboarding documentation, not application code.

ENXT-FR-023 (permission scope): this adapter's complete, minimal required ERPNext permission set is
read+write on Stock Entry, Stock Reservation Entry, Purchase Order and Quality Inspection, and read-only
on Item/Supplier/Warehouse/UOM/Work Order -- exactly `SUPPORTED_OPERATIONS` above and no more. The
customer's own ERPNext API user is configured with exactly this scope on the ERPNext side (outside this
codebase's control, same boundary as ENXT-FR-018), not something this adapter can enforce itself.
"""

from typing import Any

import httpx

from app.modules.erp.adapters.base import HttpAdapterBase, extract_retry_after_seconds
from app.modules.erp.provider import CanonicalOutboundCommand, ERPChangesPage, ERPProviderResponse

SUPPORTED_OPERATIONS = (
    "SYNC_MATERIAL_ITEM", "SYNC_SUPPLIER", "SYNC_WAREHOUSE_LOCATION", "SYNC_UOM",
    "POST_GOODS_RECEIPT", "POST_CONSUMPTION", "POST_RETURN", "POST_SCRAP_DESTRUCTION",
    "POST_FINISHED_GOODS_RECEIPT", "POST_QUALITY_STATUS", "GET_PRODUCTION_ORDER_REFERENCE",
    "FETCH_MASTER_DATA_CHANGES",
    "POST_PURCHASE_ORDER_REF", "POST_RESERVATION", "POST_RELEASE_AVAILABILITY", "GET_PURCHASE_ORDER_REFERENCE",
)

_ENTITY_DOCTYPE = {"MATERIAL": "Item", "SUPPLIER": "Supplier", "WAREHOUSE": "Warehouse", "UOM": "UOM"}

_STOCK_ENTRY_PURPOSE = {
    "POST_GOODS_RECEIPT": "Material Receipt",
    "POST_CONSUMPTION": "Material Issue",
    "POST_RETURN": "Material Receipt",
    "POST_SCRAP_DESTRUCTION": "Material Issue",
    "POST_FINISHED_GOODS_RECEIPT": "Manufacture",
}


class ERPNextAdapter(HttpAdapterBase):
    vendor = "ERPNEXT"
    contract_version = "v14-resource-api"
    supported_operations = SUPPORTED_OPERATIONS
    health_path = "/api/method/frappe.auth.get_logged_user"

    async def dispatch(self, command: CanonicalOutboundCommand) -> ERPProviderResponse:
        if command.command_type not in self.supported_operations:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"reason": "unsupported"})

        try:
            async with self._client() as client:
                if command.command_type == "GET_PRODUCTION_ORDER_REFERENCE":
                    work_order = command.payload.get("external_order_id")
                    response = await client.get(f"/api/resource/Work Order/{work_order}")
                elif command.command_type == "GET_PURCHASE_ORDER_REFERENCE":
                    po_name = command.payload.get("external_order_id")
                    response = await client.get(f"/api/resource/Purchase Order/{po_name}")
                elif command.command_type == "POST_QUALITY_STATUS":
                    response = await client.post("/api/resource/Quality Inspection", json=command.payload)
                elif command.command_type in _STOCK_ENTRY_PURPOSE:
                    body: dict[str, Any] = {**command.payload, "purpose": _STOCK_ENTRY_PURPOSE[command.command_type]}
                    if command.command_type == "POST_RETURN":
                        body["is_return"] = 1
                    response = await client.post("/api/resource/Stock Entry", json=body)
                elif command.command_type == "POST_PURCHASE_ORDER_REF":
                    response = await client.post("/api/resource/Purchase Order", json=command.payload)
                elif command.command_type == "POST_RESERVATION":
                    response = await client.post("/api/resource/Stock Reservation Entry", json=command.payload)
                elif command.command_type == "POST_RELEASE_AVAILABILITY":
                    body = {**command.payload, "purpose": "Material Transfer"}
                    response = await client.post("/api/resource/Stock Entry", json=body)
                else:
                    return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"reason": "unsupported"})
        except httpx.TimeoutException:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body=None, timed_out=True)
        except httpx.HTTPError as exc:
            return ERPProviderResponse(succeeded=False, external_reference=None, raw_status=None, raw_body={"exception": exc.__class__.__name__})

        body = _safe_json(response)
        data = (body or {}).get("data", {}) if isinstance(body, dict) else {}
        external_reference = data.get("name") if isinstance(data, dict) else None
        succeeded = response.status_code < 300

        # ENXT-FR-015: an HTTP 200 alone never means "posted" for a submittable ERPNext doctype (Stock
        # Entry, Quality Inspection) -- ERPNext returns 200 for a saved-but-still-draft document exactly
        # as readily as for a submitted one. `docstatus` is the real signal: 0=Draft, 1=Submitted,
        # 2=Cancelled. Only a submitted document is a genuine external commit.
        if succeeded and command.command_type in (*_STOCK_ENTRY_PURPOSE, "POST_QUALITY_STATUS", "POST_PURCHASE_ORDER_REF", "POST_RESERVATION", "POST_RELEASE_AVAILABILITY") and isinstance(data, dict) and "docstatus" in data:
            docstatus = data.get("docstatus")
            if docstatus != 1:
                succeeded = False
                # "exception" is reliability.classify_integration_error()'s existing structured (never
                # free-text, CTR-FR-006) signal channel -- NOT_SUBMITTED classifies as BUSINESS_REJECT
                # (manual review, never auto-retried): a draft/cancelled document needs a human to look
                # at ERPNext, not a blind resend of the same payload.
                body = {**(body if isinstance(body, dict) else {}), "reason": "not_submitted", "docstatus": docstatus, "exception": "NOT_SUBMITTED"}

        return ERPProviderResponse(
            succeeded=succeeded, external_reference=external_reference,
            raw_status=response.status_code, raw_body=body,
            retry_after_seconds=extract_retry_after_seconds(response),
        )

    async def fetch_changes(self, entity_type: str, cursor: str | None) -> ERPChangesPage:
        doctype = _ENTITY_DOCTYPE.get(entity_type)
        if doctype is None:
            return ERPChangesPage(records=[], next_cursor=cursor, has_more=False)

        params: dict[str, Any] = {"limit_page_length": 100}
        if cursor:
            params["filters"] = f'[["modified", ">", "{cursor}"]]'
        try:
            async with self._client() as client:
                response = await client.get(f"/api/resource/{doctype}", params=params)
        except httpx.HTTPError:
            return ERPChangesPage(records=[], next_cursor=cursor, has_more=False)

        body = _safe_json(response) or {}
        records = body.get("data", []) if isinstance(body, dict) else []
        next_cursor = records[-1].get("modified", cursor) if records else cursor
        return ERPChangesPage(records=records, next_cursor=next_cursor, has_more=len(records) == 100)


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None
