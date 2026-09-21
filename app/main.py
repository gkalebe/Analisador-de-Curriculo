from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.web.routers import (
    analise_router,
    auth_router,
    chat_router,
    diagnostico_router,
    painel_router,
    simulador_router,
    templates_router,
    vagas_router,
)

from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.rate_limit import limiter
import app.core.persistencia.models  # noqa: F401

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        logging.info("Tabelas do banco verificadas/criadas no startup.")
    except Exception as erro:
        logging.error(f"Erro ao inicializar tabelas no banco: {erro}")
    yield


app = FastAPI(title="Analisador de Currículos", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Front-end agora é uma SPA em React (frontend/), servida separadamente pelo Vite em
# desenvolvimento (http://localhost:5173) ou publicada no domínio de produção. A lista
# de origens autorizadas vem de CORS_ORIGINS (ver app/core/config.py) — nunca "*" aqui,
# já que a API expõe dados de usuário autenticado.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_lista,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


_CAMINHOS_SEM_CSP = {"/docs", "/redoc", "/openapi.json"}


@app.middleware("http")
async def adicionar_cabecalhos_seguranca(request: Request, chamar_proximo):
    """
    Cabeçalhos de segurança básicos, aplicados a toda resposta da API.

    Escopo propositalmente enxuto (não é uma auditoria OWASP completa): mitigam as
    classes de ataque mais comuns contra uma API JSON (clickjacking, MIME sniffing,
    vazamento de referrer) sem exigir nenhuma mudança de comportamento no front-end.
    """
    resposta = await chamar_proximo(request)
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resposta.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    resposta.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    if request.url.path not in _CAMINHOS_SEM_CSP:
        resposta.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return resposta


app.include_router(auth_router.router)
app.include_router(vagas_router.router)
app.include_router(analise_router.router)
app.include_router(chat_router.router)
app.include_router(diagnostico_router.router)
app.include_router(simulador_router.router)
app.include_router(templates_router.router)
app.include_router(painel_router.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
