"""Document 74 (SPEC-DATA-006) TMP-FR-011 -- `classify_retry()` as a pure function. No Temporal server
needed (TEST-FR-002: deterministic domain functions get fast isolated tests); the live-server proof that
this function is actually wired into a running Activity is `tests/test_workflowops_temporal.py`.
"""

from app.modules.workflowops.retry_policy import classify_retry
from app.mutation.errors import DependencyUnavailableError, NotFoundError, StaleVersionError, ValidationFailedError


def test_stale_version_is_a_retryable_transient_race():
    decision = classify_retry(StaleVersionError("changed since read", current_version=2))
    assert decision.retryable is True


def test_dependency_unavailable_is_a_retryable_compliance_dependency_failure():
    decision = classify_retry(DependencyUnavailableError("DB briefly unreachable"))
    assert decision.retryable is True


def test_not_found_is_a_settled_outcome_never_retried():
    decision = classify_retry(NotFoundError("step does not exist"))
    assert decision.retryable is False


def test_validation_failed_is_a_settled_outcome_never_retried():
    decision = classify_retry(ValidationFailedError("bad input"))
    assert decision.retryable is False
