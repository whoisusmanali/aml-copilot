"""Typed configuration, loaded from environment variables (prefix AML_) or a .env file.

Every module reads settings from here instead of calling os.environ directly, so
configuration is validated once at startup and is easy to override in tests.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AML_", env_file=".env", extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "aml"
    postgres_user: str = "aml"
    postgres_password: SecretStr = SecretStr("change-me-locally")

    kafka_bootstrap: str = "localhost:19092"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("change-me-locally")

    temporal_host: str = "localhost:7233"
    mlflow_uri: str = "http://localhost:5000"

    data_dir: Path = Path("./data")
    random_seed: int = 42

    llm_provider: str = "anthropic"
    llm_api_key: SecretStr | None = None

    @property
    def postgres_dsn(self) -> str:
        pwd = self.postgres_password.get_secret_value()
        return (
            f"postgresql://{self.postgres_user}:{pwd}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
