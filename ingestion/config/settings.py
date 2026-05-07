"""Pydantic-settings configuration classes for the ingestion layer.

Each class maps to a group of environment variables via its env_prefix.
All secrets are wrapped in SecretStr so they are never logged as plaintext.
"""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")

    user: str = "guardrail"
    password: SecretStr = SecretStr("guardrail_dev")
    host: str = "localhost"
    port: int = 5432
    db: str = "burnout_guardrail"

    @property
    def url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.db}"
        )


class KafkaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KAFKA_", extra="ignore")

    bootstrap_servers: str = "localhost:9092"
    schema_registry_url: str = "http://localhost:8081"
    group_id: str = "burnout-guardrail"
    security_protocol: str = "PLAINTEXT"
    # SASL — only used when security_protocol is SASL_SSL (e.g., Confluent Cloud)
    sasl_mechanism: str = "PLAIN"
    sasl_username: str = ""
    sasl_password: SecretStr = SecretStr("")


class SlackSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SLACK_", extra="ignore")

    bot_token: SecretStr
    signing_secret: SecretStr


class GoogleSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GOOGLE_", extra="ignore")

    service_account_path: str = "./secrets/google_service_account.json"


class JiraSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JIRA_", extra="ignore")

    base_url: str
    api_token: SecretStr
    email: str


class GitHubSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GITHUB_", extra="ignore")

    app_id: str
    private_key_path: str = "./secrets/github_private_key.pem"
    org: str
    webhook_secret: SecretStr = SecretStr("")
