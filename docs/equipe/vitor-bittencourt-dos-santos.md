# Vitor Bittencourt dos Santos

Integrante a ser incorporado ao time em breve — ainda sem Sprint 0 nem US atribuída no Plano de Ação. Esta página existe para já deixar claro o ponto de entrada assim que você entrar.

## Ponto de entrada sugerido

O Plano de Ação foi desenhado para comportar sua entrada sem retrabalho: os módulos e o backlog já preveem onde você se encaixa, de preferência na **Sprint 3 ou 4**, assumindo um módulo completo (ex.: Painel + Biblioteca) em vez de dividir um arquivo já em andamento com outra pessoa — assim você não fica dependente de refatorar o que já estiver pronto.

Sugestão do Plano de Ação (Seção 3.7): ao entrar, assumir a extensão da **Sprint 4** — testes de carga (RNF-001: resposta em até 30s; RNF-007: 100 usuários simultâneos), hardening e documentação — e, no ciclo pós-MVP, os itens que hoje ficam fora do escopo das 19 US originais (ex.: novos perfis de usuário, idiomas, certificações — citados na Seção 6.5 do Documento de Arquitetura como extensões futuras do modelo de dados).

## Antes de começar

1. Confirme com o Tech Lead/Scrum Master, no início da sprint em que você entrar, qual módulo específico será seu (o Plano de Ação não fixa uma US individual para você ainda, só a área).
2. Leia o README da camada correspondente ao módulo que assumir (`app/web/README.md`, `app/core/service/README.md`, `app/core/persistencia/README.md` ou `app/adapters/README.md`) para ver o que já está pronto e o que falta.
3. Siga a Seção 1.4 do Plano de Ação: uma US = uma branch (`feature/US-XXX-slug`) = um dono, rebase diário em cima de `develop`, PR pequeno e frequente.

Assim que sua US/sprint de entrada for definida, atualize este arquivo com a tabela de US, pontos, módulo e dependências, no mesmo formato usado para o resto do time.
