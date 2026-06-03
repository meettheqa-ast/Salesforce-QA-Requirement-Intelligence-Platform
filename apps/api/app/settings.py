"""Application settings, loaded from environment via pydantic-settings.

Every external dependency defaults to a stub so the application boots offline.
See .env.example at the repo root for the full list and documentation.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class AuthProvider(StrEnum):
    DEV = "dev"
    OIDC = "oidc"


class AIProvider(StrEnum):
    STUB = "stub"
    ANTHROPIC = "anthropic"


class EmbeddingsProvider(StrEnum):
    STUB = "stub"
    OPENAI = "openai"


class JiraProvider(StrEnum):
    STUB = "stub"
    CLOUD = "cloud"


class KMSProvider(StrEnum):
    LOCAL = "local"
    AWS = "aws"
    GCP = "gcp"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General
    app_env: AppEnv = AppEnv.LOCAL
    log_level: str = "INFO"
    app_secret_key: str = "change-me-dev-only-not-for-production"

    # CORS. Comma-separated list of allowed browser origins. Defaults cover the
    # local web dev server on common ports. Set explicitly per environment.
    cors_allow_origins: str = "http://localhost:3000,http://localhost:3001"

    # Database
    # Host port 5433 avoids clashing with a natively-installed PostgreSQL on 5432.
    #
    # The application connects as the restricted, RLS-subject role `sfqa_app`.
    # Migrations connect as the superuser `sfqa` via `migration_database_url`.
    # This separation is required: superusers and BYPASSRLS roles ignore RLS.
    database_url: str = (
        "postgresql+asyncpg://sfqa_app:sfqa_app_dev_only@localhost:5433/sfqa"
    )
    migration_database_url: str = (
        "postgresql+asyncpg://sfqa:sfqa_dev_only@localhost:5433/sfqa"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Object storage
    s3_endpoint_url: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_access_key: str = "sfqa_minio"
    s3_secret_key: str = "sfqa_minio_dev_only"
    s3_bucket_exports: str = "sfqa-exports"

    # Auth
    auth_provider: AuthProvider = AuthProvider.DEV
    oidc_issuer: str = ""
    oidc_audience: str = ""
    # If blank, the JWKS URL is derived from the issuer (issuer/.well-known/...).
    oidc_jwks_url: str = ""
    # JWKS responses are cached this long to avoid a network hop per request.
    oidc_jwks_cache_seconds: int = 3600
    # Claim names carrying tenant + role. Auth0 requires namespaced custom claims;
    # the defaults match a typical Auth0 custom-claims namespace. When a token
    # lacks these claims, the app falls back to a DB membership lookup by subject.
    oidc_tenant_claim: str = "https://sfqa.app/tenant_id"
    oidc_role_claim: str = "https://sfqa.app/role"
    dev_auth_shared_secret: str = "dev-only-not-for-production"

    # AI provider (LLM)
    ai_provider: AIProvider = AIProvider.STUB
    anthropic_api_key: str = ""
    anthropic_model_primary: str = "claude-opus-4-8"
    anthropic_model_cheap: str = "claude-haiku-4-5"
    # Per-request timeout (seconds) for provider HTTP calls.
    llm_request_timeout_seconds: float = 60.0

    # AI provider (embeddings)
    embeddings_provider: EmbeddingsProvider = EmbeddingsProvider.STUB
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    # Jira
    jira_provider: JiraProvider = JiraProvider.STUB

    # KMS
    kms_provider: KMSProvider = KMSProvider.LOCAL
    kms_local_master_key: str = "dev-only-32-bytes-base64-fake-key-do-not-use-in-prod=="

    # Cost guardrails
    default_tenant_monthly_budget_cents: int = 2000

    # Feature flags
    feature_change_intelligence: bool = False
    feature_prompt_cache: bool = False

    # Prompts directory (relative to repo root, resolved at runtime)
    prompts_dir: str = Field(default="../../prompts")

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnv.PROD

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
