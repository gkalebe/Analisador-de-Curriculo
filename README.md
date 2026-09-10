# Analisador de Currículos

Ecossistema digital baseado em IA para otimizar currículos frente a sistemas de rastreamento de candidatos (ATS) e simular entrevistas.

## Stack

- Backend: Python 3.13 + FastAPI
- Frontend: HTML + Tailwind CSS (renderizado via Jinja2)
- Banco de dados: PostgreSQL 16
- IA generativa: Gemini API ou Anthropic Claude API
- Arquitetura: Clean Architecture simplificada (`web/`, `core/service/`, `core/persistencia/`, `adapters/`)

## Como rodar localmente

Pré-requisitos: Python 3.13, Docker e Docker Compose.

```
cp .env.example .env
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
docker compose up -d db
alembic revision --autogenerate -m "schema inicial"
alembic upgrade head
uvicorn app.main:app --reload
```

A aplicação sobe em `http://localhost:8000`. Health-check em `http://localhost:8000/health`.

Para rodar tudo via Docker (app + banco):

```
docker compose up --build
```

## Testes

```
pytest
ruff check .
```

## Estrutura de pastas

```
app/
├── main.py
├── web/              # rotas, templates HTML, estáticos
├── core/
│   ├── service/      # regras de negócio
│   └── persistencia/ # modelos ORM e repositórios
└── adapters/
    ├── ai_service/       # integração com Gemini/Claude
    └── curriculo_parser/ # extração de texto de PDF/DOCX
```

Cada pasta acima tem seu próprio `README.md` com a tabela de quem implementa o quê, em qual Sprint, e o que já está pronto vs. pendente:

- [`app/web/README.md`](app/web/README.md)
- [`app/core/service/README.md`](app/core/service/README.md)
- [`app/core/persistencia/README.md`](app/core/persistencia/README.md)
- [`app/adapters/README.md`](app/adapters/README.md)

A Sprint 0 entregou só a estrutura: assinatura de classes e métodos, `models.py` completo (é o schema já acordado no Documento de Arquitetura, não lógica de negócio) e o wiring entre camadas. Os métodos de repositório e as implementações dos adapters propositalmente lançam `NotImplementedError` — implementar isso é o trabalho de cada US nas Sprints 1 a 4.

## Fluxo de contribuição

Ver o Plano de Ação do projeto para convenção de branches, commits e distribuição das Sprints. Resumo rápido:

```
git checkout develop
git pull origin develop
git checkout -b feature/US-XXX-descricao-curta
```

Abrir PR contra `develop`, com pelo menos 1 aprovação e CI verde antes do merge.
