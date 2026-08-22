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
    access_token_expire_minutes: int = 60
    signature_challenge_expire_minutes: int = 5


settings = Settings()
