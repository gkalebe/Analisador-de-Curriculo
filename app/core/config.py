from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"
    database_url: str = "postgresql+psycopg2://analisador:analisador@localhost:5432/analisador_curriculos"
    secret_key: str = "troque-por-uma-chave-secreta-forte"
    access_token_expire_minutes: int = 60
    password_reset_expire_minutes: int = 30
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    max_upload_size_mb: int = 5
    max_vaga_description_chars: int = 5000
    frontend_login_url: str = "http://localhost:8000/login"
    frontend_reset_password_url: str = "http://localhost:8000/usuarios/redefinir-senha"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
