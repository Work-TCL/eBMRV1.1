from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GXP_", env_file=".env")

    database_url: str = (
        "postgresql+asyncpg://ebmr_new_gxp_app:changeme@localhost:5432/ebmr_new_gxp"
    )
    # Separate, higher-privileged role for running Alembic migrations (MIG-FR-020:
    # migration role is separate from the runtime role, which gets no DDL).
    migration_database_url: str | None = None
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
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


settings = Settings()
