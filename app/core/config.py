from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"
    database_url: str = "postgresql+psycopg2://analisador:analisador@localhost:5432/analisador_curriculos"
    secret_key: str = "troque-por-uma-chave-secreta-forte"
    access_token_expire_minutes: int = 60
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    max_upload_size_mb: int = 5
    max_vaga_description_chars: int = 5000


@lru_cache
def get_settings() -> Settings:
    return Settings()
