"""Document 74 (SPEC-DATA-006) -- TMP-FR-011/024. "Activity retry/backoff explicitly defined by error
class; business validation/signature denial not retried blindly." This is the actual classification
logic a Temporal Activity wrapper (once one exists) calls after `executeGxPActivity()` raises: it turns
this codebase's real `GxPError` taxonomy (`app/mutation/errors.py`) into a retry decision, rather than
leaving "should this retry" as an unwritten judgment call per activity author.

Rule: a compliance-critical **dependency failure** (503, `DEPENDENCY_UNAVAILABLE`/`PRIMARY_UNAVAILABLE`
/`REPLICA_TOO_STALE`/`CRYPTO_HEALTH_FAILED`/`DEADLOCK_DETECTED`, or an unclassified 5xx `SYSTEM_FAULT`)
is retryable with backoff (TMP-FR-024: "Activities fail/retry; workflows never invent successful domain
transition"). A **business/authorization/validation/signature outcome** (401/403/404/422/428, or a 409
that is a business-state conflict rather than a transient race) is never retried blindly -- retrying it
would resubmit the same rejected decision, not recover from an outage.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.mutation.errors import GxPError

# 409s that ARE a transient concurrency race (a retry after re-reading current state can legitimately
# succeed) vs 409s that are a settled business/security outcome (retrying changes nothing).
_RETRYABLE_409_CODES = {"STALE_VERSION", "DEADLOCK_DETECTED", "OUTBOX_PUBLISH_STATE_CONFLICT"}
_RETRYABLE_STATUS_CODES = {503, 500}


@dataclass(frozen=True)
class RetryDecision:
    retryable: bool
    reason: str


def classify_retry(exc: GxPError) -> RetryDecision:
    """TMP-FR-011. Takes any `GxPError` instance (or subclass) and returns whether a Temporal Activity
    wrapper should let Temporal's retry policy run again, or fail the Activity permanently (surfacing
    to the workflow for compensation/human review instead)."""
    code = getattr(exc, "code", "SYSTEM_FAULT")
    status = getattr(exc, "status_code", 500)

    if code in _RETRYABLE_409_CODES:
        return RetryDecision(True, f"{code} is a transient concurrency race, safe to retry after re-read")
    if status in _RETRYABLE_STATUS_CODES:
        return RetryDecision(True, f"status {status} ({code}) is a compliance-critical dependency failure")
    return RetryDecision(False, f"status {status} ({code}) is a settled business/authorization/validation outcome")
