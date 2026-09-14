# core/persistencia/

Modelos ORM (`models.py`) e repositórios (`*_repository.py`). Esta é a única camada que fala SQLAlchemy diretamente — services não devem importar `sqlalchemy` nem montar `select(...)` fora daqui.

## `models.py`

As 5 entidades (`Usuario`, `Curriculo`, `Candidato`, `Vaga`, `Analise`) já estão completas, com chaves primárias UUID e relacionamentos, seguindo o diagrama UML do Documento de Arquitetura de Software (Seção 4.1) e o modelo de dados da Seção 6. Isso não é trabalho de nenhuma US específica — é o schema que o time já validou no documento, só transcrito para código.

Se uma US precisar de um campo novo que não está no diagrama original, adicione o campo aqui e gere a migração (`alembic revision --autogenerate -m "..."`), mas avise o time antes: mexer em `models.py` é área de conflito sensível (ver Plano de Ação, Seção 1.4).

## Repositórios

Os métodos abaixo estão com assinatura pronta, mas o corpo lança `NotImplementedError` — implementar é parte do trabalho da US, não algo pré-pronto. Exceções: `usuario_repository.buscar_por_id`, `buscar_por_email` e `atualizar` (necessários para US-003), todos os métodos de `vaga_repository.py` (US-019) e `analise_repository.criar`/`buscar_por_id`/`listar_por_usuario` (US-007, ver abaixo) já estão implementados. `curriculo_repository.buscar_por_id`, `listar_por_usuario` e `excluir` continuam como esqueleto.

| Arquivo | US | Sprint | Dev |
|---|---|---|---|
| `usuario_repository.py` | US-001, US-002, US-003, US-017 | 1 | Kevin, Gabriel Kalebe, Allan |
| `vaga_repository.py` | US-019 | 1 | Gabriel Kalebe (concluído) |
| `curriculo_repository.py` | US-004, US-016, US-018 | 1, 4 | Gustavo Souto Pereira (US-004), Carlos (US-016), Allan (US-018) |
| `analise_repository.py` | US-007, US-014, US-016 | 2, 4 | Gabriel Kalebe (`criar`/`buscar_por_id`/`listar_por_usuario`, US-007, concluído — autorizado pelo time), Kevin, Carlos (US-014/US-016 restantes) |

Padrão a seguir em cada método (`criar`, `buscar_por_id`, `listar_por_usuario`, etc.): usar `self.db.add` / `self.db.get` / `select(...)` do SQLAlchemy 2.0, sempre `commit()` + `refresh()` após escrita, e devolver a entidade (nunca um dicionário).

## Migrações (Alembic)

```
alembic revision --autogenerate -m "descricao-curta"
alembic upgrade head
```

Toda mudança em `models.py` deve vir acompanhada da migração correspondente no mesmo PR — a migração `54b69fafad49_adiciona_data_nascimento_e_exclusao_.py` corrigiu um caso em que isso não tinha acontecido (`Usuario.data_nascimento` e `Usuario.exclusao_solicitada_em` já existiam no model mas nunca tinham sido migrados, quebrando `alembic upgrade head` em bancos criados do zero). Depois de puxar essa migração, rode `alembic upgrade head` no seu ambiente local.
