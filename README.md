# Analisador de Currículos

Ecossistema digital baseado em IA para otimizar currículos frente a sistemas de rastreamento de candidatos (ATS) e simular entrevistas.

## Stack

- Backend: Python 3.13 + FastAPI, servindo API JSON pura (sem renderização de HTML)
- Frontend: React 18 + Vite, SPA separada consumindo a API via `fetch`
- Banco de dados: PostgreSQL 16
- IA generativa: Gemini API ou Anthropic Claude API
- Arquitetura: Clean Architecture simplificada (`web/`, `core/service/`, `core/persistencia/`, `adapters/`) no backend; `frontend/src/` separado em `api/` (chamadas de rede), `models/` (tipos e funções puras) e `pages/`/`components/` (UI)

## Como rodar localmente

Pré-requisitos: Python 3.13, Node.js 18+, Docker e Docker Compose.

Backend (API):

```
cp .env.example .env
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
docker compose up -d db
alembic upgrade head
uvicorn app.main:app --reload
```

A API sobe em `http://localhost:8000`. Health-check em `http://localhost:8000/health`.

Frontend (SPA), em outro terminal:

```
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

A aplicação (telas) sobe em `http://localhost:5173` e consome a API em `http://localhost:8000` via CORS. Os dois processos rodam em paralelo durante o desenvolvimento.

Para subir o projeto inteiro, incluindo banco, API e frontend:

```
docker compose up --build
```

Depois, acesse a aplicação em `http://127.0.0.1:5173` e a documentação da API em `http://127.0.0.1:8000/docs`. Para executar em segundo plano, use `docker compose up --build -d`.

Para parar os containers:

```
docker compose down
```

O serviço `frontend` compila a SPA React e a serve com Nginx. As portas são publicadas explicitamente em IPv4 para evitar travamentos do `localhost` via IPv6 no Windows/Docker Desktop.

Para desenvolver com hot reload usando Docker, use o Compose de desenvolvimento:

```
docker compose -f docker-compose.dev.yml up --build
```

Nesse modo, alterações em `app/` reiniciam o Uvicorn automaticamente e alterações em `frontend/src/` atualizam pelo HMR do Vite. A aplicação fica em `http://127.0.0.1:5173`.

Para parar o ambiente de desenvolvimento:

```
docker compose -f docker-compose.dev.yml down
```

O Compose padrão continua usando o build React + Nginx, sem hot reload, para simular a execução empacotada.

## Testes

```
pytest
ruff check .
```

## Dependências

`requirements.txt` passa por auditoria periódica: cada biblioteca listada precisa estar de fato em uso (import direto) ou ser um requisito real de outra que está (ex.: `python-multipart` para `UploadFile`/`File` do FastAPI, `email-validator` para `EmailStr` do Pydantic, `python-dotenv` para o `env_file` do `pydantic-settings`). Em 17/09, `jinja2` foi removida — sobrava de antes da migração para a SPA React, sem nenhum router ou template usando Jinja2 há tempos (`app/web/README.md` já registrava isso como obsoleto). O front (`frontend/package.json`) já estava enxuto: `react`, `react-dom`, `react-router-dom` e as duas devDependencies do Vite, todas em uso.

## Estrutura de pastas

```
app/
├── main.py
├── web/              # rotas (API JSON pura) e schemas Pydantic
├── core/
│   ├── service/      # regras de negócio
│   └── persistencia/ # modelos ORM e repositórios
└── adapters/
    ├── ai_service/       # integração com Gemini/Claude
    ├── curriculo_parser/ # extração de texto de PDF/DOCX
    └── email/            # envio de e-mail transacional (SendGrid ou SMTP)

frontend/
└── src/
    ├── api/         # chamadas de rede (fetch) por domínio
    ├── models/      # tipos e funções puras, sem I/O
    ├── pages/       # componentes de rota
    └── components/  # UI compartilhada entre páginas
```

O frontend do projeto tem uma única fonte: [`frontend/`](frontend/), uma SPA React com Vite. A camada `app/web/` contém apenas a API JSON, schemas e routers do backend; não há mais renderização HTML pelo FastAPI.

Cada pasta abaixo tem seu próprio `README.md` com a tabela de quem implementa o quê, em qual Sprint, e o que já está pronto vs. pendente:

- [`app/web/README.md`](app/web/README.md)
- [`app/core/service/README.md`](app/core/service/README.md)
- [`app/core/persistencia/README.md`](app/core/persistencia/README.md)
- [`app/adapters/README.md`](app/adapters/README.md)

A Sprint 0 entregou só a estrutura: assinatura de classes e métodos, os models ORM completos (o schema já acordado no Documento de Arquitetura, não lógica de negócio) e o wiring entre camadas. Os métodos de repositório e as implementações dos adapters propositalmente lançavam `NotImplementedError` — implementar isso é o trabalho de cada US nas Sprints 1 a 4; várias US já foram implementadas desde então (ver os READMEs de cada pasta).

## Fluxo de contribuição

Ver o Plano de Ação do projeto para convenção de branches, commits e distribuição das Sprints. Resumo rápido:

```
git checkout develop
git pull origin develop
git checkout -b feature/US-XXX-descricao-curta
```

Abrir PR contra `develop`, com pelo menos 1 aprovação e CI verde antes do merge.
