"""Document 53 (SPEC-ERP-006) — the one shared integration reliability model every adapter (Documents
49/50/51) and master-data sync (Document 52) uses: error classification, retry/backoff computation,
dead-letter, circuit breaker. Built once here, not once per vendor (module docstring in models.py).

Numeric policy values (backoff base/cap/jitter, max attempts, circuit-breaker trip threshold) are
provisional defaults -- SG-123: no numeric SLO exists anywhere in the approved baseline for any of these.
Every value is a plain module-level constant an operator can override per instance/operation without a
code change (`ErpInstance.capabilities` JSONB can carry an override -- see `resolve_retry_policy`).
"""

import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.erp.models import ERROR_CATEGORIES, IntegrationCircuitBreaker

# --- INT-FR-002: canonical error taxonomy -----------------------------------------------------------
# Categories that retry automatically (INT-FR-003 "only retryable categories retry automatically").
RETRYABLE_CATEGORIES = frozenset({"RATE_LIMIT", "TRANSIENT_NETWORK", "SERVER_ERROR", "TIMEOUT_UNCERTAIN"})
# Categories that always require human correction/review before anything happens again.
MANUAL_REVIEW_CATEGORIES = frozenset({"CONFIG", "VALIDATION", "BUSINESS_REJECT", "SCHEMA", "SECURITY", "MANUAL_REVIEW"})
# AUTH and CONFLICT are deliberately in neither set above: AUTH is retried a small bounded number of
# times (a token may simply need refreshing) then becomes MANUAL_REVIEW; CONFLICT never auto-retries
# (INT-FR-007 payload-hash conflict is a data-integrity signal, not a transient fault).


@dataclass(frozen=True)
class RetryPolicy:
    initial_backoff_seconds: float = 30.0
    multiplier: float = 2.0
    cap_seconds: float = 3600.0
    jitter_fraction: float = 0.2
    max_attempts: int = 8


@dataclass(frozen=True)
class CircuitBreakerPolicy:
    failure_threshold: int = 5
    failure_window_seconds: float = 600.0
    open_duration_seconds: float = 60.0


@dataclass(frozen=True)
class RateLimitPolicy:
    """INT-FR-024/ERP-ARC-028: a proactive per-(instance, operation) quota, distinct from the circuit
    breaker's reactive failure-based trip -- this caps outbound call *volume* regardless of whether calls
    are succeeding, to avoid a well-behaved-but-chatty integration tripping a vendor's own rate limiter in
    the first place. Provisional default (SG-123's own precedent: no numeric SLO exists anywhere in the
    approved baseline for this either), fully overridable per instance via the same `capabilities` JSONB
    `rate_limit_policy` key `resolve_retry_policy` already uses for `retry_policy`."""

    max_requests_per_window: int = 60
    window_seconds: float = 60.0


DEFAULT_RETRY_POLICY = RetryPolicy()
DEFAULT_CIRCUIT_BREAKER_POLICY = CircuitBreakerPolicy()
DEFAULT_RATE_LIMIT_POLICY = RateLimitPolicy()


def resolve_rate_limit_policy(instance_capabilities: dict | None) -> RateLimitPolicy:
    override = (instance_capabilities or {}).get("rate_limit_policy") or {}
    return RateLimitPolicy(
        max_requests_per_window=override.get("max_requests_per_window", DEFAULT_RATE_LIMIT_POLICY.max_requests_per_window),
        window_seconds=override.get("window_seconds", DEFAULT_RATE_LIMIT_POLICY.window_seconds),
    )


def resolve_retry_policy(instance_capabilities: dict | None) -> RetryPolicy:
    """SG-123: an instance's `capabilities` JSONB may carry a `retry_policy` override
    (`{"initial_backoff_seconds": .., "multiplier": .., "cap_seconds": .., "jitter_fraction": ..,
    "max_attempts": ..}`); anything absent falls back to the provisional platform default."""

    override = (instance_capabilities or {}).get("retry_policy") or {}
    return RetryPolicy(
        initial_backoff_seconds=override.get("initial_backoff_seconds", DEFAULT_RETRY_POLICY.initial_backoff_seconds),
        multiplier=override.get("multiplier", DEFAULT_RETRY_POLICY.multiplier),
        cap_seconds=override.get("cap_seconds", DEFAULT_RETRY_POLICY.cap_seconds),
        jitter_fraction=override.get("jitter_fraction", DEFAULT_RETRY_POLICY.jitter_fraction),
        max_attempts=override.get("max_attempts", DEFAULT_RETRY_POLICY.max_attempts),
    )


def classify_integration_error(*, http_status: int | None, exception_kind: str | None, timed_out: bool) -> str:
    """INT-FR-002. classifyIntegrationError(). Never branches on message text (CTR-FR-006) -- only on
    status code / exception kind / the explicit timed_out flag the adapter reports."""

    if timed_out:
        return "TIMEOUT_UNCERTAIN"
    if exception_kind in ("ConnectError", "ConnectTimeout", "ReadTimeout", "PoolTimeout", "NetworkError"):
        return "TRANSIENT_NETWORK"
    # ENXT-FR-015: an adapter's own structured (non-message-text) signal that a call returned HTTP
    # success but the vendor document never reached a submitted/committed state (e.g. ERPNext docstatus
    # stayed 0/Draft or moved to 2/Cancelled) -- a business-level rejection, not an infra fault, so it
    # goes to manual review rather than an automatic retry of the same payload.
    if exception_kind == "NOT_SUBMITTED":
        return "BUSINESS_REJECT"
    # MULTI-FR-011: a write with no dataAreaId (D365) is a caller/integration-configuration defect --
    # never auto-retried against the same missing context (RETRYABLE_CATEGORIES excludes CONFIG).
    if exception_kind == "MISSING_DATA_AREA":
        return "CONFIG"
    if http_status is None:
        return "TRANSIENT_NETWORK"
    if http_status == 401 or http_status == 403:
        return "AUTH"
    if http_status == 400 or http_status == 422:
        return "VALIDATION"
    if http_status == 404:
        return "CONFIG"
    if http_status == 409:
        return "CONFLICT"
    if http_status == 429:
        return "RATE_LIMIT"
    if 500 <= http_status < 600:
        return "SERVER_ERROR"
    if http_status >= 400:
        return "BUSINESS_REJECT"
    return "SERVER_ERROR"


@dataclass(frozen=True)
class RetryDecision:
    should_retry: bool
    next_attempt_at: datetime | None
    backoff_seconds: float | None
    terminal_reason: str | None = None


def compute_retry_decision(
    *, error_category: str, attempt_count: int, policy: RetryPolicy, retry_after_seconds: float | None = None,
    now: datetime | None = None,
) -> RetryDecision:
    """INT-FR-003/004/005. computeRetryDecision(). `retry_after_seconds` is the vendor's own
    `Retry-After` header, honored verbatim when present (INT-FR-004)."""

    now = now or datetime.now(timezone.utc)
    if error_category not in RETRYABLE_CATEGORIES and not (error_category == "AUTH" and attempt_count < 2):
        return RetryDecision(should_retry=False, next_attempt_at=None, backoff_seconds=None, terminal_reason=error_category)
    if attempt_count >= policy.max_attempts:
        return RetryDecision(should_retry=False, next_attempt_at=None, backoff_seconds=None, terminal_reason="MAX_ATTEMPTS_EXCEEDED")

    if retry_after_seconds is not None:
        backoff = min(retry_after_seconds, policy.cap_seconds)
    else:
        raw = policy.initial_backoff_seconds * (policy.multiplier ** attempt_count)
        backoff = min(raw, policy.cap_seconds)
        jitter = backoff * policy.jitter_fraction
        backoff = backoff + random.uniform(-jitter, jitter)
        backoff = max(backoff, 0.0)

    return RetryDecision(should_retry=True, next_attempt_at=now + timedelta(seconds=backoff), backoff_seconds=backoff)


def validate_error_category(category: str) -> None:
    if category not in ERROR_CATEGORIES:
        raise ValueError(f"Unrecognized integration error category: {category}")


# --- INT-FR-022: circuit breaker ---------------------------------------------------------------------


async def get_or_create_breaker(
    session: AsyncSession, *, erp_instance_id: uuid.UUID, operation: str
) -> IntegrationCircuitBreaker:
    result = await session.execute(
        select(IntegrationCircuitBreaker).where(
            IntegrationCircuitBreaker.erp_instance_id == erp_instance_id,
            IntegrationCircuitBreaker.operation == operation,
        ).with_for_update()
    )
    breaker = result.scalar_one_or_none()
    if breaker is None:
        breaker = IntegrationCircuitBreaker(erp_instance_id=erp_instance_id, operation=operation, state="CLOSED", failure_count=0)
        session.add(breaker)
        await session.flush()
    return breaker


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def rate_limit_allows_call(
    breaker: IntegrationCircuitBreaker, *, policy: RateLimitPolicy, now: datetime | None = None
) -> bool:
    """INT-FR-024/ERP-ARC-028. Fixed-window counter reusing the per-(instance, operation) breaker row
    (module docstring). Mutates `rate_window_started_at`/`rate_window_count` as a side effect -- same
    "the caller commits it" contract `record_breaker_outcome` already has for the failure-count fields.
    Checked *before* dispatch, independent of `breaker_allows_call` (a healthy, closed circuit can still
    be over quota; an open circuit is already blocked regardless of quota)."""

    now = now or datetime.now(timezone.utc)
    if breaker.rate_window_started_at is None or (now - _aware(breaker.rate_window_started_at)) >= timedelta(seconds=policy.window_seconds):
        breaker.rate_window_started_at = now
        breaker.rate_window_count = 1
        return True
    if breaker.rate_window_count >= policy.max_requests_per_window:
        return False
    breaker.rate_window_count += 1
    return True


def breaker_allows_call(breaker: IntegrationCircuitBreaker, *, policy: CircuitBreakerPolicy, now: datetime | None = None) -> bool:
    """tripCircuitBreaker()/closeCircuitBreaker() decision surface, read-only half. An OPEN breaker
    allows exactly one probe call once `open_duration_seconds` has elapsed (half-open, INT-FR-022)."""

    now = now or datetime.now(timezone.utc)
    if breaker.state == "CLOSED":
        return True
    if breaker.state == "HALF_OPEN":
        return True
    # OPEN
    if breaker.opened_at is None:
        return True
    opened_at = breaker.opened_at if breaker.opened_at.tzinfo else breaker.opened_at.replace(tzinfo=timezone.utc)
    if now - opened_at >= timedelta(seconds=policy.open_duration_seconds):
        breaker.state = "HALF_OPEN"
        return True
    return False


def record_breaker_outcome(
    breaker: IntegrationCircuitBreaker, *, succeeded: bool, error_category: str | None, policy: CircuitBreakerPolicy,
    now: datetime | None = None,
) -> None:
    now = now or datetime.now(timezone.utc)
    if succeeded:
        breaker.state = "CLOSED"
        breaker.failure_count = 0
        breaker.opened_at = None
        breaker.last_probe_at = now
        return

    if breaker.state == "HALF_OPEN":
        breaker.last_probe_at = now
        if error_category in RETRYABLE_CATEGORIES:
            breaker.state = "OPEN"
            breaker.opened_at = now
            breaker.failure_count += 1
        else:
            breaker.state = "CLOSED"
            breaker.failure_count = 0
            breaker.opened_at = None
        return

    if error_category not in RETRYABLE_CATEGORIES:
        return  # a validation/config/business rejection is not the vendor being unreliable
    breaker.failure_count += 1
    if breaker.failure_count >= policy.failure_threshold and breaker.state != "OPEN":
        breaker.state = "OPEN"
        breaker.opened_at = now
