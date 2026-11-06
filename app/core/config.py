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
    gemini_model_name: str = "gemini-3.8-flash"
    # Lista separada por vírgula; usada quando o modelo principal responde 503 (alta demanda).
    gemini_fallback_models: str = "gemini-3.6-flash,gemini-flash-latest"
    groq_api_key: str = ""
    groq_model_name: str = "openai/gpt-oss-120b"
    mistral_api_key: str = ""
    mistral_model_name: str = "mistral-large-latest"
    anthropic_api_key: str = ""
    anthropic_model_name: str = "claude-3-5-haiku-20241022"
    max_upload_size_mb: int = 5
    max_vaga_description_chars: int = 20000
    # RN-010: o currículo original não fica armazenado por mais de 90 dias após a última
    # atividade (upload, edição ou análise). A biblioteca (US-018) deixa de listar o que
    # passou desse prazo.
    retencao_curriculo_dias: int = 90
    # Origens autorizadas a chamar a API (CORS). Em produção, configurar via env var
    # CORS_ORIGINS com o domínio real do front-end — nunca deixar em "*" com uma API
    # que expõe dados de usuário autenticado.
    cors_origins: str = (
        "http://localhost:5173,http://localhost:4173,"
        "http://127.0.0.1:5173,http://127.0.0.1:4173"
    )
    frontend_login_url: str = "http://localhost:8000/login"
    frontend_reset_password_url: str = "http://localhost:8000/usuarios/redefinir-senha"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    sendgrid_api_key: str = ""
    stripe_mode: str = "test"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_max: str = ""
    stripe_price_ultimate: str = ""
    stripe_success_url: str = "http://localhost:4173/planos?checkout=success&session_id={CHECKOUT_SESSION_ID}"
    stripe_cancel_url: str = "http://localhost:4173/planos?checkout=cancelled"
    stripe_portal_return_url: str = "http://127.0.0.1:4173/planos"
    demo_account_email: str = ""
    demo_account_password: str = ""

    @property
    def stripe_price_ids(self) -> dict[str, str]:
        return {
            "pro": self.stripe_price_pro,
            "max": self.stripe_price_max,
            "ultimate": self.stripe_price_ultimate,
        }

    @property
    def gemini_modelos_reserva(self) -> list[str]:
        return [m.strip() for m in self.gemini_fallback_models.split(",") if m.strip()]

    @property
    def cors_origins_lista(self) -> list[str]:
        return [origem.strip() for origem in self.cors_origins.split(",") if origem.strip()]

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
