import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.web.routers import (
    analise_router,
    auth_router,
    diagnostico_router,
    painel_router,
    simulador_router,
    templates_router,
    vagas_router,
)

from app.core.database import Base, engine
import app.core.persistencia.models  # noqa: F401

logging.basicConfig(level=logging.INFO)

# Garante que as tabelas existem no banco ao iniciar
try:
    Base.metadata.create_all(bind=engine)
except Exception as erro:
    logging.warning(f"Não foi possível executar create_all na inicialização: {erro}")

app = FastAPI(title="Analisador de Currículos", version="0.1.0")

# Front-end agora é uma SPA em React (frontend/), servida separadamente pelo Vite em
# desenvolvimento (http://localhost:5173). O FastAPI passa a ser só uma API JSON.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(vagas_router.router)
app.include_router(analise_router.router)
app.include_router(diagnostico_router.router)
app.include_router(simulador_router.router)
app.include_router(templates_router.router)
app.include_router(painel_router.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
