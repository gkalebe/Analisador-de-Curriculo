# Plano de implementação — planos, cotas de IA e Stripe

## 1. Objetivo e escopo

Este documento propõe como evoluir o Analisador de Currículos para oferecer um plano gratuito e três assinaturas pagas, controlar o consumo de operações de IA, cobrar por meio da Stripe e tratar os dados de conta e cobrança de forma coerente com a LGPD. É um plano de implementação; não altera o código nem configura uma conta Stripe.

A aplicação atual usa FastAPI, SQLAlchemy, Alembic e PostgreSQL no backend, com uma SPA React no frontend. Cadastro, autenticação, currículos, análises, configurações de conta e exclusão de conta já existem. Não há integração de pagamento, assinatura comercial ou medição persistente de uso. O serviço chamado `PlanoService` hoje trata do histórico e de lacunas de competências, não de planos pagos.

O desenho proposto preserva a arquitetura existente: rotas HTTP na camada `app/web/`, regras de negócio em `app/core/service/`, modelos e repositórios em `app/core/persistencia/`, integração Stripe em `app/adapters/` e telas React em `frontend/src/`. Os nomes de tabelas e classes abaixo são sugestões sujeitas às convenções finais do projeto.

## 2. Regras de produto confirmadas

Os preços são valores iniciais para validação, não definitivos; devem ser reavaliados com dados reais de uso e custo. A configuração comercial deve permitir trocar preço, cotas e preço Stripe sem espalhar constantes pelo código.

| Plano | Preço mensal inicial | Análises de currículo/mês | Processamentos de currículo com IA/mês | Currículos guardados |
|---|---:|---:|---:|---:|
| Gratuito | R$ 0,00 | 2 | 2 | Até 100 por conta |
| PRO | R$ 19,90 | 20 | 5 | Até 100 por conta |
| MAX | R$ 49,90 | 50 | 10 | Até 100 por conta |
| ULTIMATE | R$ 129,90 | 120 | 20 | Até 100 por conta |

O limite de até 100 currículos é técnico e igual para todos os planos nesta primeira versão; não é uma cota de IA nem uma diferenciação comercial. Guardar um currículo, criar ou atualizar manualmente seus dados e consultar currículos já salvos não consome cota de IA. Ao atingir 100, bloquear novo cadastro com mensagem clara até que o usuário exclua manualmente um currículo, sem excluir ou substituir dados automaticamente. Uma operação que efetivamente invoque IA para estruturar ou reprocessar um currículo consome uma unidade de “processamento de currículo com IA”. Uma análise de currículo contra uma vaga consome uma unidade de “análise”.

As duas cotas são independentes e mensais; não acumulam. Somente uma operação concluída com sucesso é contabilizada. Durante uma chamada, uma reserva temporária deve impedir que requisições simultâneas ultrapassem a cota; se a chamada falhar, a reserva é liberada. O primeiro processamento de currículo no cadastro também consome a cota de processamento com IA do plano. Criar uma conta, por si só, não deve chamar a IA automaticamente.

As assinaturas são mensais, em reais, sem período de teste gratuito. A decisão é aceitar todos os meios elegíveis para cobrança recorrente em BRL que a Stripe habilitar para a conta. A disponibilidade precisa ser confirmada no ambiente Stripe; não se deve prometer que todo método disponível para pagamento avulso também estará disponível para recorrência.

### Ciclo de renovação das cotas

Para assinaturas pagas, alinhar a renovação das cotas ao ciclo individual de cobrança registrado pela Stripe. Para o plano gratuito, iniciar um período móvel de 30 dias na primeira operação bem-sucedida que consome uma cota de IA; a recomendação é que ambas as cotas gratuitas compartilhem esse mesmo período. Assim, se a primeira operação elegível ocorrer no dia X, a renovação será em X + 30 dias. Um currículo salvo ou editado manualmente não inicia esse período, pois não consome IA. Persistir cada janela como intervalo explícito (`início`, `fim`) em UTC e exibir a data de renovação na interface.

## 3. Arquitetura proposta por módulos

### 3.1 Catálogo e configuração de planos

Criar um catálogo persistido de planos e versões de preço/cotas. O catálogo define código estável (`free`, `pro`, `max`, `ultimate`), nome de exibição, preço em centavos, moeda, intervalo de cobrança, limites de análise e de processamento de currículo com IA, estado ativo e referência de preço da Stripe. O backend usa o catálogo como fonte confiável das regras; valores enviados pelo navegador servem apenas para identificar o plano desejado e nunca definem o preço.

Não sobrescrever uma configuração de plano que já esteja associada a assinaturas ativas sem decidir como isso afeta clientes existentes. Uma mudança comercial deve criar uma nova versão ou novo preço na Stripe e preservar a referência histórica. O plano pode ser desativado para novas compras sem apagar os dados de assinaturas antigas.

Os limites são inteiros, editáveis e versionados. A política deve especificar se alterações nas cotas têm efeito imediato para assinantes existentes ou apenas no próximo período. Ao chegar a 100 currículos, bloquear novos cadastros até que o usuário exclua manualmente um currículo; não apagar ou substituir conteúdo automaticamente. Preços devem ser armazenados em centavos (`1990`, `4990`, `12990`) e moeda ISO (`BRL`), evitando números de ponto flutuante em cálculos monetários.

### 3.2 Assinaturas e estado de acesso

Criar um serviço de assinatura que associe usuário, plano local e objetos Stripe. O estado local precisa distinguir, pelo menos, assinatura ativa, incompleta/em pagamento, inadimplente, cancelada ao fim do período, encerrada e em processo de exclusão. O estado deve refletir eventos validados da Stripe; o redirecionamento de retorno do Checkout não é confirmação de pagamento.

O serviço responde a perguntas como: “qual plano efetivo este usuário tem agora?”, “qual é o limite de cada cota na janela atual?”, “quando a assinatura renova?” e “o acesso termina em qual data?”. O plano gratuito é atribuído quando a conta é criada ou quando uma assinatura paga deixa de conceder acesso. Em caso de falha na renovação, manter os recursos pagos durante o período de tolerância aplicado pela Stripe; quando esse período terminar sem pagamento, mudar o acesso para Gratuito. Mapear e testar o comportamento real de `past_due`/grace period da configuração Stripe antes de produção.

Uma assinatura deve manter identificadores externos mínimos, como `stripe_customer_id` e `stripe_subscription_id`, além do preço/plano local, estado, início/fim do período pago, data do cancelamento e se o cancelamento é ao final do período. Upgrade no meio do ciclo aplica imediatamente com prorrata; downgrade fica agendado para o próximo ciclo. E-mail, nome e endereço de cobrança devem permanecer no sistema Stripe quando possível; não duplicar informações pessoais sem necessidade.

### 3.3 Medição e reserva de cotas de IA

Criar um serviço de cotas compartilhado por todos os caminhos da aplicação que chamem IA. As operações devem ter tipos inequívocos, por exemplo `analise_vaga` e `estruturacao_curriculo`. Antes de invocar o provedor, o serviço identifica o usuário e a janela de cota vigente, confere consumo bem-sucedido mais reservas em andamento e cria uma reserva atômica.

Após sucesso, a reserva é finalizada como consumida e associada ao resultado de domínio criado. Se a chamada falhar ou for cancelada antes de produzir uma operação válida, a reserva é marcada como falha/liberada e não conta para a cota. Deve existir uma estratégia para reservas abandonadas por queda do processo, com prazo de expiração e reconciliação segura. A contabilização e a criação do resultado precisam evitar cobrar duas unidades quando uma chamada é repetida por timeout ou retry.

As verificações devem ser aplicadas no backend. Desabilitar um botão no React melhora a experiência, mas não protege a cota. Usar transação e bloqueio apropriado no PostgreSQL ou uma operação de atualização condicional para suportar duas ou mais requisições simultâneas. O usuário deve receber erro de domínio previsível quando atingir a cota, incluindo tipo da cota e horário de renovação, sem revelar detalhes internos.

O cadastro de currículo precisa distinguir claramente os caminhos existentes: upload com revisão manual dos dados, upload que pede estruturação à IA, currículo manual, extração em preview, exportação e reprocessamento. Um preview que chama o modelo também é uso de IA e não pode ser usado como caminho alternativo para evitar a cota. Se uma resposta de preview for reutilizada para salvar o currículo, ela deve ser armazenada e reutilizada em vez de fazer a mesma chamada novamente.

Uma edição manual não deve invocar IA implicitamente. A exportação também não deve provocar processamento oculto sem consentimento e indicação de consumo; se algum fluxo atual ainda chamar IA para completar dados, ele deverá reutilizar os dados estruturados em cache ou contabilizar a chamada e informar o usuário previamente.

### 3.4 Integração Stripe e checkout hospedado

Implementar um adapter Stripe isolado em `app/adapters/`, com funções pequenas para criar Checkout Session, consultar ou cancelar assinatura quando necessário, criar ou consultar o Customer Portal e validar eventos. Instalar o SDK oficial da Stripe na etapa de implementação, após a alteração do `requirements.txt`, e manter chamadas HTTP e exceções do provedor fora das regras de negócio.

O fluxo de compra recomendado é:

1. A pessoa autenticada escolhe um plano na página de planos.
2. O frontend envia ao backend somente o código do plano pretendido.
3. O backend valida conta, plano e situação atual e cria uma sessão Stripe Checkout em modo de assinatura com o `price_id` configurado no servidor.
4. O backend devolve a URL de Checkout; o navegador redireciona a pessoa à página hospedada pela Stripe.
5. A Stripe redireciona de volta à aplicação para uma tela de confirmação/estado, mas essa tela não libera o plano por conta própria.
6. A Stripe envia eventos ao webhook. O backend valida a assinatura criptográfica do webhook, verifica o objeto na Stripe quando necessário e atualiza o estado local.

Criar o endpoint de webhook público sem exigir JWT, pois a Stripe não possui sessão de usuário na aplicação. A autenticidade deve ser conferida com o segredo de assinatura Stripe usando o corpo HTTP bruto, sem reserialização anterior. Responder rapidamente após validar e registrar o evento; processamento mais demorado pode ser feito em tarefa assíncrona durável se o volume justificar.

Persistir o identificador do evento Stripe com restrição de unicidade para idempotência. A Stripe pode reenviar o mesmo evento; processar novamente não pode duplicar assinatura, pagamento, reembolso ou acesso. Os handlers devem tolerar eventos fora de ordem: verificar o objeto atual na Stripe ou comparar datas/versões antes de substituir estado mais recente por estado antigo.

Eventos importantes a mapear incluem conclusão/expiração de Checkout, criação e atualização de assinatura, falha ou sucesso de pagamento de fatura, cancelamento e reembolso. A lista definitiva dependerá do modo de Checkout, métodos aceitos e configuração Stripe escolhidos. A rotina de reconciliação deve conseguir detectar divergência entre banco local e Stripe e permitir reparo auditável.

Usar sempre ambiente de teste Stripe separado de produção, com chaves e preços diferentes. Segredos Stripe e segredo do webhook ficam em variáveis de ambiente/gerenciador de segredos, nunca no frontend, repositório, logs ou tabela de plano. Configurações previstas: chave secreta, chave pública quando realmente necessária no frontend, segredo de assinatura do webhook, URL pública do frontend/backend e `price_id` por plano/versão.

O botão chama o backend da aplicação, e não a API Stripe com uma chave secreta. O checkout hospedado coleta os dados de pagamento na Stripe. O sistema guarda apenas referências da Stripe e estado necessário para acesso e suporte; não armazena número completo de cartão, CVC ou dados de autenticação.

### 3.5 Webhook, eventos e auditoria operacional

Criar uma tabela de eventos recebidos com ID Stripe, tipo, data de recebimento, estado de processamento, número de tentativas e erro técnico sanitizado. Guardar o corpo completo somente se houver necessidade demonstrável, base legal, controles de acesso e prazo de retenção; preferir guardar um conjunto reduzido de campos normalizados. Nunca registrar dados de cartão, segredos ou conteúdo de currículos em logs de eventos.

Eventos inválidos devem gerar resposta apropriada e log operacional sem incluir o corpo sensível. Falhas temporárias de processamento devem ser visíveis e repetíveis sem criar efeitos duplicados. Criar métricas e alertas para eventos não processados, pagamentos falhos, assinatura sem usuário local e divergência de estado. Uma interface administrativa pode ser posterior; inicialmente, logs estruturados e procedimento operacional documentado são necessários.

### 3.6 Persistência e estrutura do banco

Adicionar modelos SQLAlchemy e repositórios próprios para plano, assinatura, uso de IA e eventos Stripe. As tabelas são sugestões de domínio; devem ser ajustadas à nomenclatura, estratégia de migração e convenções atuais:

#### `plano`

- `id_plano`: UUID ou identificador interno.
- `codigo`: valor único e estável (`free`, `pro`, `max`, `ultimate`).
- `nome`: nome exibido.
- `versao`: número da versão comercial.
- `preco_centavos`: inteiro; zero para o plano gratuito.
- `moeda`: `BRL`.
- `intervalo`: mensal nesta primeira etapa.
- `limite_analises_mes` e `limite_processamentos_curriculo_ia_mes`.
- `stripe_price_id`: nulo para Gratuito; referência Stripe para plano pago.
- `ativo`, `vigente_desde`, `vigente_ate`, `criado_em`.

#### `assinatura`

- `id_assinatura` e `id_usuario`, com chave estrangeira para usuário.
- `id_plano`, incluindo a versão contratada.
- `stripe_customer_id` e `stripe_subscription_id`, com índices e unicidade adequados.
- `status`, `periodo_inicio`, `periodo_fim`, `cancelamento_agendado_em`, `cancelada_em`.
- `acesso_ate`, se necessário para representar acesso já pago após cancelamento.
- Datas de criação/atualização e campos de auditoria mínimos.

Cada usuário deve ter apenas uma assinatura que conceda acesso pago ao mesmo tempo, salvo decisão explícita futura de suportar múltiplas assinaturas. Adotar restrição ou regra transacional para impedir duplicidade de compras concorrentes.

#### `uso_ia`

- `id_uso`: UUID.
- `id_usuario`, referência à conta.
- `id_assinatura` e `id_plano`/versão efetivos no início, permitindo explicar a cota aplicada.
- `tipo_operacao`, estado (`reservado`, `consumido`, `liberado` ou equivalentes).
- `inicio_janela` e `fim_janela`, armazenados em UTC.
- `chave_idempotencia` única no escopo necessário.
- Referência ao resultado de análise/currículo, se já existir.
- `provedor`, `modelo`, tokens de entrada/saída e custo estimado, opcionais para telemetria.
- `criado_em`, `concluido_em` e causa de falha sanitizada.

Não copiar texto de currículo, vaga, prompt, resposta da IA ou outros dados pessoais para a tabela de uso. Para estimar custo, guardar quantidade de tokens e identificadores do modelo; calcular valores usando uma tabela de tarifas versionada ou processo analítico separado, pois preços do provedor e câmbio mudam.

#### `evento_stripe`

- `stripe_event_id`: chave única.
- Tipo e versão da API/evento quando disponíveis.
- Data do evento na origem e data local de recebimento.
- Estado de processamento, tentativas e erro sanitizado.
- Referências mínimas a Customer, Subscription, Invoice ou Checkout Session.

#### Pagamentos e faturas

Evitar duplicar todo o razão financeiro da Stripe sem finalidade. A Stripe permanece a fonte de verdade de faturas, cobranças e reembolsos. Caso a aplicação precise mostrar histórico financeiro, criar uma tabela reduzida de transações com ID Stripe, moeda, valor em centavos, estado, data e referência de fatura, sem dados de cartão. Definir retenção e necessidade fiscal com contabilidade/jurídico.

Adicionar índices por usuário e janela de uso, por ID Stripe, por estado/data de evento e restrições de unicidade para IDs externos e idempotência. Toda mudança de schema precisa de migração Alembic revisada, com `upgrade` e `downgrade` seguros e testes em banco vazio e banco já migrado.

### 3.7 Backend web e contratos da API

Criar rotas separadas, por exemplo `/planos`, `/assinatura/me`, `/assinatura/checkout`, `/assinatura/cancelar`, `/assinatura/portal` e `/webhooks/stripe`. Os nomes finais devem seguir convenções existentes. As rotas autenticadas resolvem o usuário exclusivamente pelo JWT atual; não aceitam ID ou e-mail do cliente para determinar a conta proprietária.

Expor catálogo público com nome, preço, cotas e benefícios, mas não segredos nem IDs internos sensíveis. A rota de checkout recebe somente o código de plano e retorna URL de checkout. A rota de estado da conta retorna plano efetivo, uso e limites de cada tipo, fim do período, situação de renovação e indicação de cota disponível. O cancelamento deve ser uma operação autenticada e idempotente.

Criar erros de domínio para plano inexistente/inativo, assinatura incompatível, cota esgotada, evento duplicado ou inválido, cancelamento não permitido e falha do provedor. Converter esses erros em códigos HTTP e mensagens consistentes na camada web. Falhas Stripe devem ser registradas com contexto operacional sanitizado e não apresentadas como sucesso ao usuário.

### 3.8 Frontend

Adicionar página de comparação de planos, área de assinatura nas configurações e telas de retorno do Checkout. A tabela deve deixar evidente que há duas cotas distintas: análises e processamentos de currículo com IA. Também deve explicar que a conta pode guardar até 100 currículos nesta primeira versão e que guardar ou editar manualmente não consome cota de IA, respeitando a política de retenção de arquivos descrita adiante.

O estado da página de retorno é provisório até o webhook atualizar a assinatura. A UI pode consultar o backend por alguns segundos e informar “confirmando pagamento”; nunca deve conceder acesso com base somente no parâmetro `success` da URL. A página deve tratar compra interrompida, pagamento pendente, falha e confirmação.

No uso de IA, mostrar previamente qual operação consumirá qual cota. Mostrar consumo atual e data de renovação. Se a cota acabou, oferecer comparação de planos e não enviar a requisição de IA. Formulários manuais e navegação de currículos salvos continuam disponíveis sem uso de IA.

Adicionar suporte aos novos contratos nas APIs existentes e manter a sessão atual sem guardar dados financeiros no `localStorage`. O frontend guarda apenas o token de autenticação que já usa e apresenta dados recebidos pelo backend.

### 3.9 Adaptador de IA, custos e privacidade

Centralizar a autorização de uso antes de cada chamada Gemini com custo real. O adaptador atual já tem pontos de integração e metadados de tokens; a medição de plano deve ser aplicada pelos serviços de domínio, sem acoplar o núcleo de cotas a um provedor específico. Para o escopo inicial, Gemini é o provedor de execução escolhido.

Persistir tokens e modelo usados, quando retornados pelo SDK, ajuda a estimar custo por operação e a planejar preços. A estimativa por análise não é fixa: muda com o tamanho do currículo e da vaga, tamanho da resposta, retries e operação de estruturação. O custo de cadastro/estruturação deve ser medido separadamente do custo de análise.

Revisar as condições comerciais e de tratamento de dados da Google para o uso de API paga em produção, incluindo retenção, uso para melhoria de serviço, região e transferência internacional. Enviar somente os campos necessários à tarefa, reduzir retenção de prompts, não colocar conteúdo pessoal em telemetria e atualizar aviso de privacidade. Não assumir que o uso de API tem as mesmas condições do uso gratuito do AI Studio.

## 4. LGPD e governança de dados

### 4.1 Finalidade, base legal e transparência

Atualizar o aviso de privacidade para explicar separadamente: tratamento necessário para fornecer a análise e a conta; administração de assinatura e pagamento; prevenção a fraude e suporte; registros fiscais/contábeis; e compartilhamento estritamente necessário com Stripe e Google/Gemini. Definir base legal adequada para cada finalidade com assessoria jurídica. Consentimento não deve ser escolhido automaticamente para atividades necessárias à execução de contrato ou obrigação legal.

Explicar quais dados são enviados à Stripe e ao provedor de IA, quais ficam no Analisador, por quanto tempo e como o titular pode exercer seus direitos. Registrar versão e data do aviso aceito quando o desenho jurídico/operacional exigir comprovação.

### 4.2 Minimização e segurança

Não receber nem armazenar PAN, CVC ou credenciais de pagamento. Guardar apenas IDs Stripe, status, plano, período e valores necessários. Proteger chaves Stripe, segredo de webhook, `GEMINI_API_KEY` e `SECRET_KEY` como segredos de servidor. Garantir HTTPS, controle de acesso por usuário, menor privilégio, backups protegidos, atualizações de dependências e logs sem conteúdo de currículo, prompts, tokens ou dados de pagamento.

Restringir a equipe com acesso a dados pessoais e trilhas administrativas. Definir procedimento de incidente, rotação de chaves, revogação de acesso e recuperação de backup. A hospedagem e o banco precisam ter política clara de criptografia em repouso, backups e região; verificar o estado real da infraestrutura em vez de assumir que o requisito antigo do documento de arquitetura já está atendido.

### 4.3 Retenção e direitos dos titulares

Manter um inventário de dados e uma tabela de retenção para: conta, currículo original, texto extraído, currículo estruturado, análise, logs de IA, eventos Stripe e documentos financeiros. Eliminar ou anonimizar quando a finalidade terminar, salvo obrigação legal concreta de retenção. O prazo de retenção financeira deve ser decidido com contabilidade/jurídico antes da produção.

O código atual tem configuração de 90 dias usada para filtrar o que aparece na biblioteca após a última atividade. Isso, por si só, não comprova que os arquivos sejam fisicamente eliminados ao fim do prazo; uma rotina de expurgo precisa ser projetada e testada se essa for a política escolhida. A LGPD não determina um número máximo universal de currículos nem um prazo único de guarda aplicável a todo produto; a finalidade e a necessidade do tratamento devem ser justificáveis, e os dados não devem ser mantidos além do necessário, sem prejuízo de obrigações legais específicas. O limite técnico de 100 currículos por conta é uma decisão operacional do produto, não um limite imposto pela LGPD. Validar com assessoria jurídica se os 90 dias continuam adequados, definir prazos separados para arquivo original, texto extraído, currículo estruturado e análises, e informar a política de forma transparente antes do upload.

### 4.4 Exclusão de conta e assinatura

O fluxo atual solicita exclusão e permite confirmação dentro de 48 horas, removendo a conta e dados vinculados. Integrar o ciclo de cobrança sem bloquear a solicitação de direitos:

1. Ao solicitar exclusão, marcar a conta para exclusão e impedir novas compras/uso de IA conforme regra aprovada.
2. Cancelar a renovação da assinatura na Stripe de forma idempotente.
3. Cancelamento sem reembolso mantém os recursos pagos até o fim do período já pago.
4. Se um reembolso for aprovado, revogar o acesso pago quando a Stripe confirmar o reembolso, de acordo com o alcance total/parcial definido na política comercial. Um pedido de cancelamento, por si só, não é confirmação de reembolso.
5. Após o fim do acesso aplicável, executar a exclusão/anonimização.
6. Remover currículos, documentos, texto extraído, dados estruturados, conversas e tokens locais que não tenham obrigação de retenção.
7. Manter apenas registros financeiros mínimos exigidos por lei, separados do perfil e dos dados de currículo, com acesso restrito, prazo documentado e sem reutilização para marketing.
8. Processar webhooks posteriores à exclusão sem recriar a conta. A associação do identificador Stripe ao registro restrito de cobrança deve ser suficiente para fechar a operação.

O fluxo incorpora a regra escolhida: cancelamento sem reembolso mantém acesso até o fim do período pago; reembolso aprovado implica revogação de acesso confirmada pela Stripe. Ainda é necessário definir elegibilidade e prazo de reembolso, reembolso parcial e chargeback/disputa; validar juridicamente e refletir nos termos de uso e na UI.

### 4.5 Operadores e transferência internacional

Mapear Stripe, Google/Gemini, hospedagem, banco, e-mail e monitoramento como fornecedores que podem tratar dados. Revisar contratos/DPA, suboperadores, região de processamento, transferências internacionais e mecanismos aplicáveis. Manter registro de operações de tratamento e canal de solicitações do titular. A existência de um checkout hospedado reduz o escopo de dados de cartão na aplicação, mas não torna automaticamente o sistema em conformidade com a LGPD ou elimina as responsabilidades do controlador.

## 5. Cancelamento, falhas de cobrança e reembolso

Separar “cancelar renovação”, “assinatura expirou”, “pagamento falhou”, “reembolso aprovado” e “disputa/chargeback”. Cada situação tem evento e efeito de acesso próprios. Em cancelamento sem reembolso, manter acesso pago até o fim do período já pago. Se a Stripe confirmar um reembolso aprovado, revogar o acesso na condição definida pela política comercial.

Não revogar ou manter acesso apenas com base no clique no frontend. O webhook assinado e o estado reconciliado na Stripe atualizam o estado local. Para pagamento atrasado, manter o acesso durante o prazo de recuperação de pagamento configurado na Stripe; quando esse prazo terminar sem sucesso, aplicar o plano Gratuito. Configurar e testar retries/dunning e avisos por e-mail antes de restringir o plano. Mudança para plano gratuito nunca apaga dados; apenas aplica as cotas do plano efetivo a partir da janela definida.

## 6. Configuração e implantação

Adicionar variáveis de ambiente documentadas em `.env.example`, sem valores secretos:

- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`, somente se o fluxo escolhido realmente a exigir
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_PRO`, `STRIPE_PRICE_MAX`, `STRIPE_PRICE_ULTIMATE` por versão/ambiente
- `STRIPE_SUCCESS_URL`, `STRIPE_CANCEL_URL` ou configuração equivalente do frontend
- `GEMINI_API_KEY` já existe e continua exclusivamente no backend

Separar credenciais e `price_id` de teste e produção. Nunca compartilhar dados reais de clientes em testes. Configurar a URL de webhook no painel Stripe para os eventos escolhidos e validar a entrega de ponta a ponta antes de habilitar o Checkout de produção. Atualizar Docker/Render apenas se as novas variáveis ou tarefas duráveis exigirem mudança.

## 7. Estratégia de migração de dados e usuários existentes

Criar migração aditiva: primeiro tabelas novas e índices; depois popular o catálogo inicial e atribuir plano gratuito a usuários existentes; por fim habilitar a verificação de cotas após checagem de dados e deploy. Não alterar/destruir dados de currículo ou análise existentes.

Usuários já existentes devem receber o plano gratuito, salvo decisão comercial diferente. Definir data de início da medição e como serão contadas operações históricas; recomendação: não consumir retroativamente cota no período inicial de lançamento. Usar flag de configuração para habilitar bloqueio gradualmente e manter rollback de aplicação/migração documentado.

## 8. Testes e critérios de aceite

### Unitários

- Catálogo retorna planos, preços em centavos e limites corretos.
- Usuário gratuito, pagante, cancelado e inadimplente recebe o plano efetivo esperado.
- Análises e estruturações consomem cotas independentes.
- Currículo manual, edição manual e armazenamento não consomem IA; o 101º currículo é recusado até que o usuário exclua manualmente um currículo.
- Sucesso consome uma unidade; erro, timeout ou cancelamento libera reserva.
- Janela do plano gratuito respeita `America/Sao_Paulo`; períodos pagos seguem as datas locais persistidas.
- Mudança de versão de preço não altera silenciosamente assinatura existente.

### Concorrência e idempotência

- Duas chamadas simultâneas na última unidade disponível não podem ambas iniciar com sucesso.
- Retry com a mesma chave idempotente não duplica consumo nem resultado.
- Reserva órfã expira e pode ser recuperada sem liberar consumo já concluído.
- O mesmo evento Stripe entregue repetidamente produz apenas uma atualização lógica.
- Evento antigo/out-of-order não sobrescreve status mais novo.

### Integração Stripe

- Criar Checkout em modo de assinatura para cada plano, com preço originado no servidor.
- Rejeitar plano inativo e valor/ID de preço manipulado pelo cliente.
- Validar assinatura inválida do webhook, payload malformado e evento duplicado.
- Tratar conclusão, expiração, renovação, falha de pagamento, cancelamento, reembolso e disputa conforme eventos configurados.
- Simular retorno de navegador antes do webhook: não conceder plano pago prematuramente.
- Upgrade aplica imediatamente com prorrata; downgrade vale no próximo ciclo.
- Cancelamento sem reembolso mantém acesso até o fim do período; reembolso aprovado revoga acesso após confirmação Stripe.
- Falha de cobrança mantém acesso durante o período de tolerância Stripe e depois aplica Gratuito.

### LGPD e exclusão

- Pedido de exclusão cancela renovação e não apaga registros financeiros que tenham retenção justificada.
- Confirmação de exclusão remove/anomiza todos os dados pessoais sob controle do produto previstos na política.
- Webhook tardio não recria conta nem restaura acesso depois da exclusão.
- Logs e telemetria não incluem conteúdo de currículos, prompts, respostas completas ou dados de cartão.
- Exportação/acesso, correção, oposição e exclusão têm fluxo e responsável documentados conforme aplicabilidade.

### Frontend e qualidade

- Planos, cotas, consumo e renovação aparecem de forma clara e acessível.
- O usuário entende antes da operação quando uma chamada usa IA e desconta uma cota.
- Checkout cancelado, pendente e concluído têm estados distintos.
- Testes automatizados React cobrem seleção de plano, cota esgotada, checkout e estados de assinatura.
- Executar testes backend/frontend, Ruff, build frontend e migrações em banco limpo antes do release.

## 9. Fases sugeridas de implementação

### Fase 0 — Fechar decisões de produto e compliance

Confirmar preços e cotas para lançamento, janela de renovação, meios recorrentes disponíveis, elegibilidade e prazo de reembolso, reembolso parcial/chargeback e retenção. Revisar o aviso de privacidade, termos de uso e contrato de fornecedores com contabilidade/jurídico. Não habilitar cobrança antes de concluir as decisões marcadas como pendentes.

### Fase 1 — Catálogo, schema e atribuição de plano

Criar modelos, repositórios e migração de planos, assinaturas, uso e eventos. Popular catálogo, atribuir plano gratuito aos usuários existentes e testar rollback. Nessa fase, a UI pode apresentar plano e cotas em modo informativo, ainda sem bloquear operações.

### Fase 2 — Medição confiável de uso de IA

Implementar serviço de cotas, reservas atômicas e idempotência. Integrar todos os caminhos de análise, cadastro/estruturação, preview e exportação que chamem IA. Instrumentar tokens/custos; garantir que salvamento/edição manual não consuma IA e que o limite técnico de 100 currículos seja aplicado sem exclusão automática.

### Fase 3 — Stripe em ambiente de teste

Criar produtos/preços mensais Stripe, Checkout hospedado, endpoint de retorno, webhook assinado, portal/cancelamento e reconciliação. Testar com cartões e meios disponíveis na conta de teste. Validar o mapeamento dos eventos e conferir que duplicações e eventos fora de ordem não criam inconsistências.

### Fase 4 — Interface e ciclo de vida da assinatura

Adicionar páginas de planos e cobrança em configurações, consumo de cotas e mensagens de estado. Implementar cancelamento e tratamento de falha de pagamento. Testar o ciclo de exclusão completo com assinatura ativa e definir exatamente a política de reembolso/acesso.

### Fase 5 — Produção gradual e acompanhamento

Habilitar primeiro em produção de forma controlada, com cotas/configuração inicial revisadas e alertas de webhook/custo. Monitorar conversão, custo real de Gemini por tipo de operação, usuários que atingem cota, falhas de pagamento, cancelamentos e solicitações de exclusão. Ajustar preço e limite mediante dados, preservando histórico das versões ofertadas.

## 10. Métricas que devem orientar os próximos preços

Separar métricas por plano e por operação: análises, processamentos de currículo com IA, custo real em moeda do provedor, custo convertido, tokens, retries, percentual de usuários que atingem limite, receita líquida de taxas, inadimplência, reembolso e cancelamento. Avaliar mediana e percentil 90 de uso, não apenas a média; usuários intensivos podem concentrar grande parte do gasto.

Para testar a sustentabilidade, calcular custo de IA no cenário observado e no percentil 90, adicionar tarifa Stripe, tributos, infraestrutura e custo de suporte, e então comparar com a receita líquida. A estimativa de tokens usada em conversas anteriores é apenas hipótese de planejamento e deve ser substituída pelos dados de produção/teste controlado.

## 11. Decisões confirmadas e decisões ainda pendentes

### Confirmadas

- Tabela inicial de planos e cotas da seção 2, com preços provisórios sujeitos à validação por dados de uso, incluindo o limite técnico de 100 currículos por conta em todos os planos.
- Upgrade imediato com prorrata; downgrade efetivo no próximo ciclo.
- Em falha de renovação, manter acesso durante o período de tolerância da Stripe e depois aplicar o plano Gratuito.
- Cancelamento sem reembolso mantém acesso até o fim do período pago; reembolso aprovado revoga acesso quando confirmado pela Stripe.
- Usar todos os meios que a Stripe habilitar para assinatura recorrente em BRL, sujeito à confirmação técnica para a conta.
- Cotas pagas renovam no ciclo de cobrança individual; cotas Gratuitas renovam 30 dias após a primeira operação bem-sucedida que consome IA.
- Ao atingir 100 currículos, bloquear novos cadastros até que o usuário exclua manualmente um currículo, sem remoção ou substituição automática.

### Pendentes

1. Confirmar como tratar as cotas quando houver upgrade com prorrata: recalcular a cota proporcionalmente ao tempo restante, conceder a cota cheia do plano novo ou manter o saldo já consumido?
2. Definir elegibilidade/prazo de reembolso, efeito de reembolso parcial e chargeback/disputa.
3. Validar com assessoria jurídica os 90 dias atualmente usados para filtrar a biblioteca e estabelecer prazos separados para arquivo, texto extraído, dados estruturados e análises. A intenção de “seguir a lei” requer uma política documentada por finalidade; a LGPD não fornece um prazo genérico único para todos esses dados. Confirmar também se será implementada eliminação física automática dos arquivos ao fim do prazo.
4. Definir prazo de retenção de dados mínimos de faturamento e eventos Stripe com contabilidade/jurídico, além dos responsáveis por pedidos dos titulares.
5. Aprovar os textos de privacidade, termos de assinatura, renovação automática, cancelamento e processamento de dados pela Stripe e Google.

## 12. Referências técnicas

- Código atual: `app/core/service/analisador_service.py`, `app/core/service/auth_service.py`, `app/adapters/ai_service/ai_service_adapter.py`, `app/core/persistencia/models/usuario.py`, `app/core/persistencia/models/curriculo.py`, `app/core/persistencia/models/analise.py`, `app/web/routers/analise_router.py` e `app/web/routers/auth_router.py`.
- Stripe Checkout para assinaturas: <https://docs.stripe.com/billing/subscriptions/build-subscriptions?payment-ui=checkout>
- Stripe Webhooks: <https://docs.stripe.com/webhooks>
- Stripe Billing / Customer Portal: <https://docs.stripe.com/customer-management>
- Google Gemini API — preços e termos: <https://ai.google.dev/gemini-api/docs/pricing> e <https://ai.google.dev/gemini-api/terms>
- Lei nº 13.709/2018 (LGPD): <https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm>
