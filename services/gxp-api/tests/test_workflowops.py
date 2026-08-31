"""Document 74 (SPEC-DATA-006) -- Temporal Durable Workflow Orchestration Architecture. No Temporal
cluster exists in this deployment; these are the two reusable primitives (workflow-ID derivation,
error-class retry classification) a future Temporal integration must use, tested standalone (no DB).
"""

import pytest

from app.modules.workflowops.identity import derive_workflow_id
from app.modules.workflowops.retry_policy import classify_retry
from app.mutation.errors import (
    DependencyUnavailableError,
    MissingSignatureError,
    StaleVersionError,
    ValidationFailedError,
)


def test_derive_workflow_id_stable_and_validated():
    wid = derive_workflow_id(workflow_type="batch_release", business_id="B-2026-001", namespace="prod")
    assert wid == "prod.batch_release.B-2026-001"
    # same inputs -> same ID (TMP-FR-002: prevents accidental duplicate orchestration)
    assert derive_workflow_id(workflow_type="batch_release", business_id="B-2026-001", namespace="prod") == wid

    with pytest.raises(ValueError):
        derive_workflow_id(workflow_type="batch release", business_id="B-1")  # space not identifier-safe
    with pytest.raises(ValueError):
        derive_workflow_id(workflow_type="", business_id="B-1")


def test_classify_retry_business_outcomes_not_retried():
    """TMP-FR-011: business validation / stale-signature-target / auth denial is never retried blindly."""
    for exc in (ValidationFailedError("bad input"), MissingSignatureError("no step-up")):
        decision = classify_retry(exc)
        assert decision.retryable is False


def test_classify_retry_dependency_and_transient_race_are_retryable():
    """TMP-FR-011/024: a dependency outage is retryable; a stale-version race is retryable (the caller
    re-reads and retries), unlike a settled business rejection."""
    assert classify_retry(DependencyUnavailableError("db down")).retryable is True
    assert classify_retry(StaleVersionError("changed", current_version=2)).retryable is True
