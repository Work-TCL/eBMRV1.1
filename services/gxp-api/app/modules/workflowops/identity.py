"""Document 74 (SPEC-DATA-006) -- Temporal Durable Workflow Orchestration Architecture.

TMP-FR-002: a workflow ID derived from stable business-process identity, so starting the "same"
orchestration twice (a duplicate click, a redelivered event, a retried API call) does not create a
second parallel workflow. `derive_workflow_id()` is a pure function -- no Temporal client exists in
this deployment yet (no `temporalio` dependency; Phase 1 has no live Temporal cluster, same "mechanism
present, infra feed deferred" shape as Document 66/70/73/76-78's declaration modules) -- but the ID
scheme it fixes now is exactly what a future `client.start_workflow(id=...)` call will pass, so the
"no accidental duplicate orchestration" guarantee is decided once, not re-derived per caller.
"""

from __future__ import annotations

import re

_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._:-]+$")


def derive_workflow_id(*, workflow_type: str, business_id: str, namespace: str = "prod") -> str:
    """TMP-FR-002/019: `{namespace}.{workflow_type}.{business_id}` -- stable, reproducible, and
    namespace-qualified (TMP-FR-019: separate environment/customer namespace). Rejects a
    `business_id`/`workflow_type` that isn't a plain identifier-safe string rather than silently
    building an ambiguous or collidable ID."""
    for label, value in (("namespace", namespace), ("workflow_type", workflow_type), ("business_id", business_id)):
        if not value or not _SAFE_SEGMENT.match(value):
            raise ValueError(f"{label}={value!r} must be a non-empty identifier-safe string")
    return f"{namespace}.{workflow_type}.{business_id}"
