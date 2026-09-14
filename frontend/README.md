# frontend/

SPA em React 18 + Vite que consome a API do backend (`app/`) via `fetch`. Substitui a renderização Jinja2 antiga (`app/web/templates/`), que ficou obsoleta.

## Como rodar

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

Não existe sessão persistida no backend — o login grava `access_token`, `usuario_nome` e `usuario_email` no `localStorage` (`src/models/usuario.js`) e as páginas que precisam identificar o usuário logado (Painel, Nova Vaga, Upload de Currículo) usam o e-mail, propagado via query string entre rotas. Trocar por autenticação via JWT nos endpoints é trabalho pendente (ver `app/web/README.md`).

## Build

```
npm run build
```

Gera `dist/` — ainda não há um pipeline de deploy configurado para o frontend.
