from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Shared with modules/deployment/checks.py's jwt_secret_not_default check -- kept here (not there) so
# config.py has no dependency on the deployment module, and re-exported for that check to reuse.
DEV_SECRET_MARKERS = ("dev-secret", "changeme", "change-me")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GXP_", env_file=".env")

    # No default: a regulated deployment must fail to start rather than silently run with a known,
    # public credential (previously defaulted to a literal "changeme" password). Same reasoning as
    # jwt_secret below.
    database_url: str
    # Separate, higher-privileged role for running Alembic migrations (MIG-FR-020:
    # migration role is separate from the runtime role, which gets no DDL).
    migration_database_url: str | None = None
    # No default, and validated below against known dev placeholders -- a signing secret that's public
    # in this repo's source history must never be capable of reaching a running instance, whether via a
    # missing env var or via someone copying the old default into their .env verbatim.
    jwt_secret: str
    jwt_algorithm: str = "HS256"

    @field_validator("jwt_secret")
    @classmethod
    def _reject_dev_jwt_secret(cls, value: str) -> str:
        if any(marker in value.lower() for marker in DEV_SECRET_MARKERS):
            raise ValueError(
                "GXP_JWT_SECRET looks like a known dev placeholder -- set a real secret before starting"
            )
        return value

    @field_validator("database_url")
    @classmethod
    def _reject_dev_database_password(cls, value: str) -> str:
        if any(marker in value.lower() for marker in DEV_SECRET_MARKERS):
            raise ValueError(
                "GXP_DATABASE_URL looks like it carries a known dev placeholder password -- set a real "
                "credential before starting"
            )
        return value

    access_token_expire_minutes: int = 1440
    signature_challenge_expire_minutes: int = 5
    # IAMSEC-FR-007 (Document 62): idle/absolute application-session lifetimes. No approved baseline
    # (Documents 106-115) defines a numeric session-timeout value anywhere -- same "numeric periods
    # unresolved" shape as SG-005's retention gap. These are engineering-default floors, not a guessed
    # regulated value; see docs/generated/18_SPEC_GAPS.md SG-163.
    # 2026-09-03: bumped 30/480 -> 1440/1440 (1 day) for client-demo convenience per user request.
    # Still a SPEC_GAP-163 placeholder, not a validated regulated value -- revert before any
    # qualification/production use.
    session_idle_timeout_minutes: int = 1440
    session_absolute_timeout_minutes: int = 1440
    # WP-11 (Document 73, ADR-0011): NATS JetStream transport for the transactional outbox. Bound to
    # localhost by default (see infra/nats-server.conf) -- never exposed beyond this deployment.
    nats_url: str = "nats://127.0.0.1:4222"
    # WP-11 Stage 2 (Document 74, ADR-0011): Temporal dev-server (infra/README.md), bound to localhost.
    temporal_target: str = "127.0.0.1:7233"
    temporal_namespace: str = "default"
    # Comma-separated explicit origin allowlist (e.g. "https://app.example.com,https://admin.example.com").
    # When unset, main.py falls back to a dev-only "any host on port 4101" regex and logs a warning --
    # that fallback must never be relied on outside local/dev use (see main.py's CORSMiddleware setup).
    cors_allowed_origins: str | None = None
    # Client gap-analysis Phase 1 (2026-10-05): bulk-imported users are activated via an emailed invite
    # link. Uses stdlib smtplib (no new dependency -- Document 104 only applies to a *new* package) against
    # whatever SMTP relay this deployment's operator configures; per ADR-0006 single-tenant-per-deployment,
    # each client's own deployment carries its own relay credentials, same as its own database. `smtp_host`
    # unset (the default) means invite emails are skipped with a logged warning rather than blocking user
    # creation -- see app/core/email.py::send_invite_email.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_from_address: str = "no-reply@ebmr.local"
    # IAMSEC-FR-021-adjacent engineering default (no approved baseline value exists for this specific
    # token's lifetime, same "numeric value unresolved" shape as session_idle_timeout_minutes above) --
    # not a SPEC_GAP-worthy regulated value since it governs account provisioning, not a GxP record.
    invite_token_expire_hours: int = 168  # 7 days
    frontend_base_url: str = "http://localhost:4101"


settings = Settings()
