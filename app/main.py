import logging

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.web.routers import (
    analise_router,
    auth_router,
    diagnostico_router,
    painel_router,
    simulador_router,
    templates_router,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Analisador de Currículos", version="0.1.0")

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
templates = Jinja2Templates(directory="app/web/templates")

app.include_router(auth_router.router)
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
