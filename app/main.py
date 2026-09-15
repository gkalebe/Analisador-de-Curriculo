import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.web.routers import (
    analise_router,
    auth_router,
    diagnostico_router,
    painel_router,
    simulador_router,
    templates_router,
    vagas_router,
)

logging.basicConfig(level=logging.INFO)

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

# Mantido só para servir /analises/upload (ainda não migrado para React).
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

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


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/cadastro")
def pagina_cadastro(request: Request):
    return templates.TemplateResponse(request=request, name="auth.html", context={"modo": "cadastro"})


@app.get("/login")
def pagina_login(request: Request):
    return templates.TemplateResponse(request=request, name="auth.html", context={"modo": "login"})


@app.get("/painel")
def pagina_painel(request: Request):
    return templates.TemplateResponse(request=request, name="painel.html", context={})


@app.get("/configuracoes")
def pagina_configuracoes(request: Request, email: str = ""):
    return templates.TemplateResponse(request=request, name="configuracoes.html", context={"email": email})
