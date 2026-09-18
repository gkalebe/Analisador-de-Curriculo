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
    gemini_model_name: str = "gemini-3.6-flash"
    anthropic_api_key: str = ""
    anthropic_model_name: str = "claude-3-5-haiku-20241022"
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
    sendgrid_api_key: str = ""

    @property
    def database_url_resolvida(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg2://", 1)
        if url.startswith("postgresql://") and not url.startswith("postgresql+psycopg2://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
