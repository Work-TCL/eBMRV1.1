import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
# Document 43 SG-120: a distinct bearer scheme for non-human (edge gateway) identities. Deliberately not
# `oauth2_scheme` — a service credential must never be interchangeable with a human session token
# (MUT-FR-023/SIG-FR-023), and the two dependencies are never both accepted on the same route.
service_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: uuid.UUID, username: str, session_id: uuid.UUID | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    # Document 62 (SPEC-SEC-002) IAMSEC-FR-006/010/013/022: binds this token to a real, revocable
    # `security.application_session` row. Optional so every pre-existing token shape (and any caller
    # that still calls this without a session) keeps working unchanged -- see get_current_actor() below.
    if session_id is not None:
        payload["session_id"] = str(session_id)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class AuthenticatedActor:
    """Resolved server-side from a trusted token. Never trust a client-supplied actor field for
    authority decisions (MUT-FR-002 equivalent)."""

    def __init__(self, user_id: uuid.UUID, username: str, session_id: uuid.UUID | None = None) -> None:
        self.user_id = user_id
        self.username = username
        # Document 62 (SPEC-SEC-002): the `security.application_session` this token is bound to, when
        # the token carries one -- lets `/auth/logout` and step-up checks address "this session" without
        # re-decoding the token.
        self.session_id = session_id


async def get_current_actor(token: str = Depends(oauth2_scheme)) -> AuthenticatedActor:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        username = payload.get("username")
        if user_id is None or username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Document 62 (SPEC-SEC-002) IAMSEC-FR-006/007/010/013/022: when the token carries a session_id
    # (every token `/auth/token` issues now does), the underlying application_session must still be
    # ACTIVE and unexpired -- fail closed on revocation/logout/idle-expiry, not just JWT exp. Older-shaped
    # tokens with no session_id claim skip this check entirely (backward compatible). Opens its own
    # short-lived connection rather than the shared per-request session -- calling `session.get()` here
    # ahead of the route handler's own `async with session.begin():` would collide with SQLAlchemy
    # autobegin, the same documented reason `get_service_identity()` below does the same thing.
    session_id = payload.get("session_id")
    if session_id is not None:
        from app.core.db import SessionLocal
        from app.modules.security.identity_models import ApplicationSession

        async with SessionLocal() as db:
            app_session = await db.get(ApplicationSession, uuid.UUID(session_id))
        if app_session is None or app_session.state != "ACTIVE":
            raise credentials_exception
        now = datetime.now(timezone.utc)
        expires_at = app_session.expires_at if app_session.expires_at.tzinfo else app_session.expires_at.replace(tzinfo=timezone.utc)
        idle_expires_at = app_session.idle_expires_at if app_session.idle_expires_at.tzinfo else app_session.idle_expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at or now > idle_expires_at:
            raise credentials_exception

    return AuthenticatedActor(
        user_id=uuid.UUID(user_id), username=username,
        session_id=uuid.UUID(session_id) if session_id is not None else None,
    )


# ---------------------------------------------------------------------------
# Document 43 (SPEC-EDGE-001) SG-120 — minimal service identity, scoped to edge gateways only. See
# `app.modules.iam.models.ServiceIdentity`.
# ---------------------------------------------------------------------------

SERVICE_CREDENTIAL_PREFIX = "sid_"


def generate_service_credential() -> tuple[str, str]:
    """Returns (raw_secret, secret_hash). The raw secret is returned to the caller exactly once (at
    enrollment) and never stored; only its bcrypt hash is persisted, same treatment as a user password."""
    raw_secret = secrets.token_urlsafe(32)
    return raw_secret, hash_password(raw_secret)


def format_service_bearer_token(identity_id: uuid.UUID, raw_secret: str) -> str:
    return f"{SERVICE_CREDENTIAL_PREFIX}{identity_id}.{raw_secret}"


class AuthenticatedServiceIdentity:
    """Resolved server-side from a service bearer credential — never a human `AuthenticatedActor`, and
    structurally never eligible to satisfy a Part 11 signature (Document 106 P7 / SIG-FR-023). Callers
    that need to distinguish actor class for audit (AUD-FR-004) use `actor_type="service"`."""

    def __init__(self, identity_id: uuid.UUID, identity_type: str, subject_ref: uuid.UUID) -> None:
        self.identity_id = identity_id
        self.identity_type = identity_type
        self.subject_ref = subject_ref


async def get_service_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(service_bearer_scheme),
) -> AuthenticatedServiceIdentity:
    """Deliberately opens its own short-lived session rather than depending on the shared per-request
    `get_session` — the route handler's own `async with session.begin():` would otherwise collide with
    SQLAlchemy's autobegin once this dependency's lookup already touched that session
    (`InvalidRequestError: A transaction is already begun on this Session`)."""
    from app.core.db import SessionLocal
    from app.modules.iam.models import ServiceIdentity

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate service credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or not credentials.credentials.startswith(SERVICE_CREDENTIAL_PREFIX):
        raise credentials_exception
    token = credentials.credentials[len(SERVICE_CREDENTIAL_PREFIX):]
    try:
        identity_id_str, raw_secret = token.split(".", 1)
        identity_id = uuid.UUID(identity_id_str)
    except ValueError:
        raise credentials_exception

    async with SessionLocal() as session:
        identity = await session.get(ServiceIdentity, identity_id)
        if identity is None or identity.status != "active":
            raise credentials_exception
    if not verify_password(raw_secret, identity.credential_hash):
        raise credentials_exception
    return AuthenticatedServiceIdentity(
        identity_id=identity.id, identity_type=identity.identity_type, subject_ref=identity.subject_ref
    )
