"""SG-142 partial resolution (2026-09-14, project-owner-directed: "build the registry + warn-only
logging now" -- option A's expand/migrate/contract shape from the SG-142 SPEC_GAP entry, phase 1 of 2).

AUD-FR-005 requires "stable event types" for the audit `action` field but names only illustrative
examples (Created, Changed, Corrected, Signed, Approved, Released, StatusChanged, Consumed, Returned,
IntegrationAccepted, "etc."), not a closed list, and nothing anywhere previously constrained the value --
`write_audit_event()` took a bare `str`, so a typo or a new spelling had nothing to reject it.

This registry is the *observed* current vocabulary (verified 2026-09-14 by extracting every literal
`action="..."` argument actually passed to `write_audit_event()`/the `_write_receipt()`-style wrappers
across `app/`, not copied from the SG-142 SPEC_GAP entry's own now-stale 20-value snapshot -- that
snapshot predates at least 8 of the 26 values below, including "Signed" itself, which AUD-FR-005 names
explicitly but which was not actually used anywhere in this codebase until this same day's own SG-048/
SG-160 work started using it for a chain-signature ceremony's intermediate positions).

Deliberately warn-only for now (see `write_audit_event()`'s own call site in `gateway.py`): closing this
to a hard-enforced enum immediately would risk rejecting a legitimate new action value the moment one is
needed, which under MUT-FR-015 would roll back the domain mutation with it -- exactly the failure mode
CLAUDE.md's migration discipline (expand -> migrate -> contract, at least two releases apart) exists to
avoid. Phase 2 (closing the enum, once a release or more has passed with no unregistered value observed
in the warning log) is a separate, later decision -- not attempted this pass.
"""

KNOWN_AUDIT_ACTIONS: frozenset[str] = frozenset(
    {
        # AUD-FR-005's own eight named examples (all except "Signed" were already in use before this
        # session; "Signed" is now real, not merely named -- see the module docstring above).
        "Created",
        "Changed",
        "Corrected",
        "Signed",
        "Approved",
        "Released",
        "StatusChanged",
        "Consumed",
        # Additional values already in real, live use across the codebase (verified 2026-09-14).
        "Adjusted",
        "AdvisoryUnavailable",
        "Allowed",
        "Closed",
        "ContextBuilt",
        "Deleted",
        "Denied",
        "Destroyed",
        "GovernancePackageGenerated",
        "IntegrationAccepted",
        "LossRecorded",
        "Performed",
        "PermissionsChanged",
        "Rejected",
        "Retired",
        "Returned",
        "Reviewed",
        "Sampled",
        "StepCompleted",
        "StepStarted",
    }
)