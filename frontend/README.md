# frontend/

SPA em React 18 + Vite que consome a API do backend (`app/`) via `fetch`. Esta é a única camada de frontend do projeto; o FastAPI serve apenas a API JSON.

## Como rodar

Para subir banco, API e frontend juntos via Docker, execute na raiz do projeto:

```
docker compose up --build
```

A SPA ficará disponível em `http://127.0.0.1:5173`.

Para desenvolvimento com hot reload dentro do Docker, execute na raiz do projeto:

```
docker compose -f docker-compose.dev.yml up --build
```

O Vite observa `frontend/src/` e o Uvicorn observa `app/`. As dependências do frontend ficam em um volume Docker, evitando misturar módulos nativos do container com os do Windows, macOS ou Linux. A SPA ficará disponível em `http://127.0.0.1:4173`. Para parar:

```
docker compose -f docker-compose.dev.yml down
```

Para desenvolvimento isolado do frontend:

```
cp .env.example .env.local
npm install
npm run dev
```

Sobe em `http://localhost:5173`. `VITE_API_URL` (em `.env.local`) aponta pra API do backend — por padrão `http://localhost:8000`, que precisa estar rodando em paralelo (ver README na raiz do projeto).

## Estrutura

```
src/
├── api/         # chamadas de rede (fetch) por domínio — authApi.js, vagasApi.js, curriculoApi.js, client.js (wrapper comum)
├── models/      # tipos (JSDoc) e funções puras, sem I/O — usuario.js, vaga.js, curriculo.js
├── pages/       # um componente por rota — ver App.jsx para o mapeamento
└── components/  # UI compartilhada entre páginas (ex.: AuthCard.jsx entre Login e Cadastro)
```

Regra ao adicionar uma tela nova: chamadas de rede vão em `api/`, nunca direto num componente de página; lógica que não depende de rede (validação, formatação, helpers de sessão) vai em `models/`. Isso mantém `pages/` só com UI e orquestração.

## Identificação de usuário

O login grava `access_token`, `usuario_nome` e `usuario_email` no `localStorage` (`src/models/usuario.js`). A tela de configurações usa o JWT para ler e atualizar o perfil autenticado (`GET/PATCH /usuarios/me`); nome e preferência de notificações são persistidos na tabela `usuario`. A maior parte das páginas de análise, vagas e currículos ainda identifica o usuário por e-mail via query string (ver `app/web/README.md`).

## Build

```
npm run build
```

Gera `dist/` — ainda não há um pipeline de deploy configurado para o frontend.

## Testes

Execute os testes automatizados do frontend com:

```
npm test
```

Os testes usam Vitest e React Testing Library. O CI instala as dependências com `npm ci` e executa esse mesmo comando.
