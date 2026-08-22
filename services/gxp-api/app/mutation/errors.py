"""Stable machine-readable error codes (MUT-FR-021 equivalent). Callers branch on `.code`, never on
message text.
"""


class GxPError(Exception):
    code: str = "SYSTEM_FAULT"
    status_code: int = 500

    def __init__(self, message: str, **details: object) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class UnauthorizedError(GxPError):
    code = "UNAUTHORIZED"
    status_code = 401


class ForbiddenError(GxPError):
    code = "FORBIDDEN"
    status_code = 403


class ValidationFailedError(GxPError):
    code = "VALIDATION_FAILED"
    status_code = 422


class StaleVersionError(GxPError):
    code = "STALE_VERSION"
    status_code = 409


class InvalidTransitionError(GxPError):
    code = "INVALID_TRANSITION"
    status_code = 409


class MissingSignatureError(GxPError):
    code = "MISSING_SIGNATURE"
    status_code = 428


class SignatureChallengeInvalidError(GxPError):
    code = "SIGNATURE_CHALLENGE_INVALID"
    status_code = 409


class IdempotencyConflictError(GxPError):
    code = "IDEMPOTENCY_CONFLICT"
    status_code = 409


class DependencyUnavailableError(GxPError):
    code = "DEPENDENCY_UNAVAILABLE"
    status_code = 503


class NotFoundError(GxPError):
    code = "NOT_FOUND"
    status_code = 404


class QualificationExpiredError(GxPError):
    code = "QUALIFICATION_EXPIRED"
    status_code = 403
