"""ERP-ARC-001/003: the vendor-neutral `ERPProvider` contract. GxP domain code (commands.py) only ever
talks to this interface and the canonical DTOs below -- no vendor type (ERPNext doctype names, SAP OData
entity sets, Oracle Fusion resource paths, Dynamics 365 entity names) crosses into the GxP domain.

Every concrete adapter in `adapters/` declares its own `capabilities` (ERP-ARC-003 "adapter declares
supported operations rather than GxP assuming all ERP functions exist") and implements exactly this
interface. `commands.py::dispatch_erp_command` never imports a concrete adapter directly -- it resolves
one from `ADAPTER_REGISTRY` by `ErpInstance.vendor`.
"""

import abc
from dataclasses import dataclass, field
from typing import Any

# ERP-ARC-003. Every canonical outbound operation any adapter *may* declare support for. An adapter's
# capability set is a subset of these -- see PROVIDER_OPERATIONS in each adapters/*.py module.
PROVIDER_OPERATIONS = (
    "SYNC_MATERIAL_ITEM",       # ERP-ARC-006, MDS-FR-005
    "SYNC_SUPPLIER",            # ERP-ARC-007
    "SYNC_WAREHOUSE_LOCATION",  # ERP-ARC-018, MDS-FR-012
    "SYNC_UOM",                 # ERP-ARC-019, MDS-FR-010
    "POST_PURCHASE_ORDER_REF",  # ERP-ARC-008
    "POST_GOODS_RECEIPT",       # ERP-ARC-009
    "POST_QUALITY_STATUS",      # ERP-ARC-010
    "POST_RESERVATION",         # ERP-ARC-011
    "POST_CONSUMPTION",         # ERP-ARC-012
    "POST_RETURN",              # ERP-ARC-013
    "POST_SCRAP_DESTRUCTION",   # ERP-ARC-014
    "POST_FINISHED_GOODS_RECEIPT",  # ERP-ARC-015
    "POST_RELEASE_AVAILABILITY",    # ERP-ARC-016
    "GET_PRODUCTION_ORDER_REFERENCE",  # ERP-ARC-017
    "FETCH_MASTER_DATA_CHANGES",       # MDS-FR-005
    "GET_PURCHASE_ORDER_REFERENCE",    # ERP-ARC-008/ENXT-FR-006 read side -- same "GET a single external
                                        # reference by id" shape as GET_PRODUCTION_ORDER_REFERENCE, routed
                                        # through dispatch() rather than a new interface method.
    "GET_MATERIAL_STOCK",               # SAP-FR-004
    "POST_TRANSFER",                    # SAP-FR-008
)


@dataclass(frozen=True)
class ERPCapabilities:
    """getCapabilities() output. ERP-ARC-003/030."""

    vendor: str
    contract_version: str
    supported_operations: tuple[str, ...]
    reachable: bool
    detail: str | None = None


@dataclass(frozen=True)
class CanonicalOutboundCommand:
    """queueERPCommand()/dispatchERPCommand() payload shape -- the same shape for every vendor. The
    adapter's own `dispatch()` method is responsible for mapping this into its vendor's wire format."""

    command_type: str
    entity_type: str | None
    internal_ref: dict[str, Any]
    payload: dict[str, Any]
    idempotency_key: str


@dataclass(frozen=True)
class ERPProviderResponse:
    """dispatchERPCommand() outcome. `external_reference` is the vendor doc/job id used for
    reconciliation (ERP-ARC-009/012/025, INT-FR-009). `raw_status`/`raw_body` feed error classification
    in reliability.py -- never interpreted by branching on message text (CTR-FR-006 discipline)."""

    succeeded: bool
    external_reference: str | None
    raw_status: int | None
    raw_body: Any
    timed_out: bool = False
    # INT-FR-004: the vendor's own Retry-After header (seconds), when present -- honored verbatim by
    # compute_retry_decision() rather than the platform's own computed backoff. WP-07 test-execution pass
    # (TC-053-S003) found this was accepted by reliability.py but never actually populated by any
    # adapter or read by dispatch_erp_command() -- a real gap, not a template mismatch, fixed here.
    retry_after_seconds: float | None = None


@dataclass(frozen=True)
class ERPChangesPage:
    """fetch_changes() output for master-data incremental sync (MDS-FR-005/022)."""

    records: list[dict[str, Any]]
    next_cursor: str | None
    has_more: bool


class ERPProvider(abc.ABC):
    """ERP-ARC-001. One contract for master data, procurement, inventory, manufacturing references and
    distribution references -- vendor-neutral by construction (no vendor SDK type appears in this
    signature set)."""

    vendor: str

    @abc.abstractmethod
    def capabilities(self) -> ERPCapabilities: ...

    @abc.abstractmethod
    async def dispatch(self, command: CanonicalOutboundCommand) -> ERPProviderResponse:
        """Sends one outbound command. Never called outside `commands.py::dispatch_erp_command`, which
        wraps every call in the reliability model (classification, retry, circuit breaker) -- an adapter
        never retries itself (ERP-ARC-023/024, no distributed 2PC, INT-FR-003)."""

    @abc.abstractmethod
    async def fetch_changes(self, entity_type: str, cursor: str | None) -> ERPChangesPage:
        """Incremental master-data pull (MDS-FR-005). Adapters unable to support a given entity_type
        raise `ERPCapabilityUnsupportedError` (ERP-ARC-003)."""

    @abc.abstractmethod
    async def probe(self) -> bool:
        """Lightweight reachability probe used by the circuit breaker's half-open recovery check
        (INT-FR-022) -- never a business operation."""


@dataclass
class AdapterConfig:
    """What an adapter needs to talk to one `ErpInstance` row -- resolved from the DB row plus the
    (out-of-band) secret manager lookup for `auth_secret_ref`, never a raw secret in a log or audit
    event (AUD-FR-025, SEC forbidden pattern "secrets in logs")."""

    base_url: str
    auth_method: str
    auth_secret: str | None
    contract_version: str | None
    timeout_seconds: float = 15.0
    extra: dict[str, Any] = field(default_factory=dict)
