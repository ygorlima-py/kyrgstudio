# Store Do App

Este modulo define a camada de persistencia estruturada do app.

Ele nao salva arquivos fisicos. Arquivos de video, audio, temporarios e objetos
de storage pertencem a `src/app/storage`.

O `store` salva dados de produto:

- usuarios;
- jobs;
- status de execucao;
- referencias para arquivos no storage;
- resultados estruturados;
- erros;
- uso de tokens;
- tempos de execucao;
- dados de billing/Stripe.

## Objetivo

Criar uma camada de persistencia limpa, testavel e preparada para producao.

O MVP ja deve nascer com usuario, billing e jobs. Por isso, a implementacao
principal deve ser pensada para Postgres com SQLAlchemy e Alembic.

SQLite pode existir para testes locais ou desenvolvimento simples, mas nao deve
guiar o desenho principal do produto.

## O Que Este Modulo Resolve

Sem `store`, o app ate consegue rodar um workflow e gerar resultado, mas nao
consegue funcionar como produto.

O `store` permite:

- criar uma execucao;
- consultar status;
- retornar resultado para a API;
- associar job a usuario;
- controlar assinatura/plano;
- salvar erro final de forma consistente;
- auditar tokens e tempo de processamento;
- manter historico de execucoes.

## O Que Este Modulo Nao Faz

Este modulo nao deve:

- salvar videos ou audios no banco;
- executar workflows;
- chamar LLM;
- chamar FFmpeg;
- fazer upload de arquivos;
- guardar estado interno do LangGraph;
- traduzir mensagens para o frontend;
- implementar regra de UI.

## Diferenca Entre Store, Storage E Checkpointer

`storage` salva arquivo fisico.

Exemplo:

```text
jobs/job_123/input.mp4
jobs/job_123/audio.wav
```

`checkpointer` salva estado interno do LangGraph.

Exemplo:

```text
thread_id
estado intermediario do grafo
node de retomada
```

`store` salva estado de produto.

Exemplo:

```text
job_id
user_id
status
current_step
input_file_key
output_json
error_json
token_usage
created_at
updated_at
```

Regra: checkpointer nao substitui `JobStore`.

## Estrutura Planejada

```text
src/app/store/
  __init__.py
  base.py
  database.py
  models.py
  jobs.py
  users.py
  billing.py
  factory.py
  README.md

alembic.ini
migrations/
  env.py
  versions/
```

`migrations/` fica na raiz do projeto porque Alembic normalmente opera no nivel
da aplicacao, nao dentro de um package interno.

## Dependencias Planejadas

Para a implementacao principal:

```text
sqlalchemy
alembic
asyncpg
```

O store deve usar SQLAlchemy Async desde o inicio:

```text
create_async_engine
async_sessionmaker
AsyncSession
```

Isso evita reescrever toda a camada de persistencia quando a API e o pipeline
forem executados em contexto assincrono.

Para testes, pode ser usado SQLite async em memoria ou arquivo temporario, desde
que os testes nao escondam comportamento importante do Postgres.

Para esse caso, usar:

```text
aiosqlite
```

## Padroes De Projeto

### Repository

Cada arquivo de dominio expõe operacoes de persistencia especificas.

Exemplo:

```text
JobStore
UserStore
BillingStore
```

O restante do app nao deve escrever SQL diretamente.

### Unit Of Work Simples

Operacoes que precisam ser atomicas devem compartilhar a mesma sessao/transaction.

Exemplo:

```text
criar job
salvar input normalizado
salvar referencia do arquivo
marcar status uploaded
finalizar transacao na camada externa
```

Se uma parte falhar, a transacao deve fazer rollback.

Regra importante: repositories/stores nao devem chamar `commit()` internamente em
cada metodo.

O controle de transacao deve ficar na camada que orquestra a operacao, como
service, pipeline ou rota da API.

Exemplo conceitual:

```text
async with session.begin():
  jobs = JobStore(session)
  users = UserStore(session)
  await jobs.create_job(...)
  await jobs.mark_running(...)
```

O store usa a sessao ativa, mas nao decide sozinho quando commitar.

### Factory

`factory.py` cria os stores com base nas settings.

O pipeline nao deve saber como configurar engine, pool de conexoes ou detalhes do
banco.

A camada externa pode abrir uma sessao usando os helpers de `database.py` e
passar essa sessao para a factory criar os stores concretos.

### Interface Base

`base.py` define contratos estaveis.

Isso permite trocar implementacao no futuro sem mudar pipeline/API.

## Modulos

### `database.py`

Responsavel por configurar a conexao com o banco.

Deve conter:

- criacao da engine SQLAlchemy async com `create_async_engine`;
- criacao de `async_sessionmaker`;
- helper para abrir `AsyncSession`;
- helper transacional, se necessario;
- helper de savepoint com `session.begin_nested()`;
- validacao da `DATABASE_URL`;
- traducao de erros de infraestrutura para `StoreError`.

Exemplo conceitual:

```text
create_async_engine_from_settings(settings)
create_async_session_factory(engine)
async_session_scope()
async_transaction_scope()
async_savepoint_scope(session)
```

Regra: nao criar engine espalhada em varios pontos do app.

Regra: se a API usar `async def`, o banco tambem deve ser acessado com
`AsyncSession`. Nao usar sessao SQLAlchemy sincronona dentro de rota async sem
threadpool explicito.

Regra: `async_savepoint_scope` deve preservar excecoes SQLAlchemy especificas,
como `IntegrityError`. O store de dominio precisa conseguir capturar esses erros
para implementar idempotencia segura sem abortar a transacao externa.

### `models.py`

Responsavel pelos modelos SQLAlchemy.

Tabelas iniciais:

```text
users
subscriptions
billing_events
jobs
job_events
```

O arquivo pode crescer. Se ficar grande demais, pode ser quebrado depois em:

```text
models/users.py
models/jobs.py
models/billing.py
```

Mas no inicio, um `models.py` unico reduz complexidade.

### `base.py`

Responsavel por contratos e tipos base dos stores.

Interfaces planejadas:

```text
JobStoreBase
UserStoreBase
BillingStoreBase
```

Os metodos devem ser assincronos:

```text
async def get_job(...)
async def create_job(...)
async def mark_completed(...)
```

Tambem pode conter enums compartilhados:

```text
JobStatus
BillingStatus
```

Se os enums crescerem, mover para `schemas.py` ou `types.py`.

Convencao de leitura:

```text
get_* retorna registro ou None
```

Nao encontrar um registro nao e erro de infraestrutura. A API ou service layer
decide se isso vira `404`, fluxo esperado ou erro de produto.

### `jobs.py`

Responsavel por persistencia de jobs.

Deve implementar:

```text
async create_job(input)
async mark_uploaded(job_id, input_file_key, input_file_uri, storage_backend)
async mark_running(job_id, step)
async mark_step_completed(job_id, step, payload)
async mark_completed(job_id, output)
async mark_failed(job_id, error)
async get_job(job_id)
async get_user_job(user_id, job_id)
async list_user_jobs(user_id, limit=20, offset=0)
```

Regra: `JobStore` nao guarda login do usuario.

Ele guarda apenas `user_id` para associar o job ao dono.

Regra: `mark_uploaded` deve salvar a referencia do arquivo no storage e mudar o
status de `pending` para `uploaded` de forma atomica.

Regra: `list_user_jobs` deve ter paginacao obrigatoria. O limite padrao pode ser
20 e o limite maximo deve ser controlado pela aplicacao, por exemplo 100.

Regra: `list_user_jobs` deve ter ordenacao explicita e estavel:

```text
ORDER BY created_at DESC, id DESC
```

Sem ordenacao explicita, paginas diferentes podem retornar resultados
inconsistentes quando novos jobs forem criados entre uma consulta e outra.

Regra: `get_job` e `get_user_job` retornam `None` quando o registro nao existe.
Excecoes ficam reservadas para falha real de infraestrutura.

### `users.py`

Responsavel por persistencia de usuarios.

Deve implementar:

```text
async create_user(email, password_hash)
async get_user(user_id)
async get_user_by_email(email)
async update_password_hash(user_id, password_hash)
async mark_email_verified(user_id)
```

Regra: nunca salvar senha pura.

Salvar apenas hash seguro.

Autenticacao, sessao, JWT ou OAuth podem ficar em outro modulo do app, por
exemplo `src/app/auth`. O `UserStore` apenas persiste dados do usuario.

Se login social entrar no roadmap, `password_hash` deve ser nullable desde a
primeira migration. O modelo deve permitir usuario criado por OAuth sem senha
local.

### `billing.py`

Responsavel por persistencia relacionada a Stripe.

Deve implementar:

```text
async set_stripe_customer(user_id, stripe_customer_id)
async upsert_subscription(...)
async get_active_subscription(user_id)
async mark_subscription_canceled(...)
async record_billing_event(...)
```

Regra: webhook da Stripe nao deve espalhar SQL direto.

O webhook chama `BillingStore`, e `BillingStore` atualiza as tabelas.

Regra: webhooks da Stripe precisam ser idempotentes.

A tabela de eventos de billing deve ter `stripe_event_id` unico. Se a Stripe
reenviar o mesmo evento, `record_billing_event` deve tratar como evento ja
processado e nao duplicar efeitos colaterais.

### `factory.py`

Responsavel por criar os stores.

Deve receber settings ou uma session factory e retornar os stores configurados.

Exemplo conceitual:

```text
create_store(session: AsyncSession) -> AppStore
```

`AppStore` pode ser um objeto simples contendo:

```text
jobs
users
billing
```

Isso evita passar tres stores separados por todo o pipeline.

## Modelo De Dados Inicial

### `users`

Campos:

```text
id: Integer, primary key
email: String(320), not null, unique
password_hash: String(256), nullable
name: String(255), nullable
avatar_url: String(2048), nullable
auth_provider: String(50), not null, default "password"
google_sub: String(255), nullable, unique
email_verified_at: DateTime(timezone=True), nullable
created_at: DateTime(timezone=True), not null, server_default now()
updated_at: DateTime(timezone=True), not null, server_default now(), onupdate now()
disabled_at: DateTime(timezone=True), nullable
```

Indices:

```text
unique(email)
unique(google_sub)
```

Observacoes:

- `email` deve ser normalizado antes de salvar;
- senha pura nunca entra no banco;
- `password_hash` pode ser nullable se o usuario vier de OAuth;
- `auth_provider` indica origem principal do usuario, como `password`, `google`
  ou `github`;
- login/sessao nao pertence diretamente ao `JobStore`.

### `subscriptions`

Campos:

```text
id: Integer, primary key
user_id: Integer, foreign key users.id, not null
stripe_customer_id: String(255), not null, unique
stripe_subscription_id: String(255), not null, unique
stripe_price_id: String(255), nullable
status: String(50), not null
plan: String(50), nullable
current_period_start: DateTime(timezone=True), nullable
current_period_end: DateTime(timezone=True), nullable
cancel_at_period_end: Boolean, not null, default false
created_at: DateTime(timezone=True), not null, server_default now()
updated_at: DateTime(timezone=True), not null, server_default now(), onupdate now()
```

Indices:

```text
index(user_id)
unique(stripe_customer_id)
unique(stripe_subscription_id)
```

Observacoes:

- o status local deve refletir os webhooks da Stripe;
- dados brutos grandes de webhook podem ir para uma tabela de eventos, nao para
  `subscriptions`.

### `billing_events`

Campos:

```text
id: Integer, primary key
stripe_event_id: String(255), not null, unique
event_type: String(100), not null
payload_json: JSON/JSONB, not null
processed_at: DateTime(timezone=True), nullable
created_at: DateTime(timezone=True), not null, server_default now()
```

Indices:

```text
unique(stripe_event_id)
index(event_type)
index(created_at)
```

Uso:

- deduplicar webhooks reenviados pela Stripe;
- auditar eventos de billing recebidos;
- permitir retry seguro de handlers;
- impedir efeitos colaterais duplicados.

Regra: violacao de `unique(stripe_event_id)` deve ser tratada como evento ja
processado, nao como erro fatal do usuario.

### `jobs`

Campos:

```text
id: Integer, primary key
user_id: Integer, foreign key users.id, not null
run_id: String(255), nullable, unique
status: String(50), not null
current_step: String(100), not null
pipeline_type: String(50), not null
input_json: JSON/JSONB, not null
storage_backend: String(50), nullable
input_file_key: String(1024), nullable
input_file_uri: String(2048), nullable
audio_file_key: String(1024), nullable
audio_file_uri: String(2048), nullable
output_json: JSON/JSONB, nullable
error_json: JSON/JSONB, nullable
token_usage_json: JSON/JSONB, nullable
execution_time_seconds: Float, nullable
created_at: DateTime(timezone=True), not null, server_default now()
updated_at: DateTime(timezone=True), not null, server_default now(), onupdate now()
started_at: DateTime(timezone=True), nullable
finished_at: DateTime(timezone=True), nullable
```

Indices:

```text
index(user_id)
index(status)
index(created_at)
unique(run_id)
```

Observacoes:

- `id` e o identificador interno do job;
- `run_id` e a chave de idempotencia externa da execucao;
- `input_json` guarda o input normalizado do pipeline;
- `output_json` guarda resultado estruturado final;
- `error_json` guarda erro controlado serializado;
- arquivos ficam no storage, nao no banco;
- `input_file_key` e `input_file_uri` apontam para o storage.

Se o cliente repetir a mesma requisicao com o mesmo `run_id`, o app deve retornar
o job existente ou falhar com erro controlado de idempotencia. Nao deve criar
dois jobs para a mesma tentativa logica.

Em concorrencia real, duas requisicoes podem tentar criar o mesmo `run_id` ao
mesmo tempo. A implementacao de `create_job` deve tratar isso explicitamente:

```text
1. abrir savepoint com async_savepoint_scope(session);
2. tentar inserir o job;
3. chamar flush dentro do savepoint;
4. se houver violacao de unique(run_id), capturar IntegrityError;
5. buscar o job existente por run_id;
6. retornar o job existente ou erro controlado de idempotencia.
```

Violacao de `unique(run_id)` nao deve vazar como erro bruto de banco para o
usuario.

Sem savepoint, o `IntegrityError` pode invalidar a transacao externa inteira no
Postgres.

`run_id` pode ser nulo em jobs internos ou execucoes que nao vieram de uma
tentativa idempotente do cliente. Nesse caso, ele nao participa da deduplicacao.

Quando `run_id` estiver preenchido, deve ser unico.

### `job_events`

Tabela opcional, mas recomendada para debug e produto.

Campos:

```text
id: Integer, primary key
job_id: Integer, foreign key jobs.id, not null
step: String(100), not null
event_type: String(100), not null
payload_json: JSON/JSONB, nullable
created_at: DateTime(timezone=True), not null, server_default now()
```

Indices:

```text
index(job_id, created_at)
index(created_at)
```

Uso:

- registrar mudanca de etapa;
- registrar warnings;
- registrar checkpoints de produto;
- facilitar debug de jobs demorados.

Nao guardar prompts completos, transcricoes enormes ou dados sensiveis em evento
sem criterio.

Politica de retencao:

- eventos de jobs concluidos podem ser apagados ou arquivados depois de um
  periodo definido, por exemplo 30 dias;
- payloads grandes devem ser evitados;
- eventos nao devem carregar transcricao completa, prompt completo ou output
  inteiro do workflow.

## Status De Job

Status inicial recomendado:

```text
pending
uploaded
running
completed
failed
cancelled
```

`current_step` deve ser mais especifico:

```text
uploading
validating_input
extracting_audio
transcribing
copy_analysis
copy_adaptation
exporting
cleanup
completed
failed
```

Regra: `status` e simples para o produto. `current_step` e detalhado para
progresso/debug.

No banco, `status` e `current_step` devem comecar como `VARCHAR`, nao como ENUM
nativo do Postgres.

Motivo: no MVP esses valores podem mudar com frequencia. ENUM nativo do Postgres
da mais trabalho em migrations quando novos status ou steps forem adicionados.

A validacao dos valores permitidos deve ficar na aplicacao.

### Transicoes Permitidas

Transicoes basicas:

```text
pending -> uploaded
uploaded -> running
running -> completed
running -> failed
running -> cancelled
pending -> failed
uploaded -> failed
```

Transicoes invalidas:

```text
completed -> failed
failed -> completed
completed -> running
cancelled -> completed
```

Regra: metodos como `mark_completed` e `mark_failed` devem proteger contra
transicoes fora de ordem.

Essa protecao deve ser feita com update condicional atomico, nao com
`SELECT` seguido de `UPDATE`.

Exemplo conceitual:

```sql
UPDATE jobs
SET
  status = 'completed',
  output_json = :output,
  finished_at = now(),
  updated_at = now()
WHERE id = :job_id
  AND status = 'running'
RETURNING id;
```

Para `mark_uploaded`, o filtro deve aceitar apenas `pending`:

```sql
WHERE id = :job_id
  AND status = 'pending'
RETURNING id;
```

Para `mark_completed`, o filtro deve aceitar apenas `running`:

```sql
WHERE id = :job_id
  AND status = 'running'
RETURNING id;
```

Para `mark_failed`, o filtro deve aceitar os estados que podem falhar:

```sql
WHERE id = :job_id
  AND status IN ('pending', 'uploaded', 'running')
RETURNING id;
```

Se `RETURNING` nao devolver linha, o job nao estava mais no estado esperado.
Nesse caso, o store deve aplicar o comportamento definido: no-op seguro ou erro
controlado.

Essa regra evita race condition quando dois workers ou retries tentam finalizar
o mesmo job ao mesmo tempo.

Se um worker duplicado tentar finalizar um job ja finalizado, o comportamento
deve ser explicito: no-op seguro ou erro controlado. Nao pode sobrescrever
`finished_at`, `status` ou `output_json` silenciosamente.

## Fluxo De Criacao De Job

Fluxo esperado:

```text
1. API recebe input
2. valida usuario autenticado
3. cria ou reutiliza job pelo run_id idempotente
4. salva upload no storage
5. chama mark_uploaded com input_file_key/input_file_uri/storage_backend
6. marca job como running
7. pipeline executa workflows
8. cada etapa relevante atualiza current_step
9. sucesso: mark_completed
10. erro: mark_failed
11. cleanup do storage acontece em finally
```

O job deve existir antes do processamento pesado comecar.

Assim, se o processo falhar, ainda existe um registro consultavel.

`run_id` deve ser usado para proteger retry de rede do cliente. A mesma tentativa
logica nao deve criar multiplos jobs. Jobs sem `run_id` nao participam dessa
deduplicacao.

## Transacoes

Cada operacao do store deve ser atomicamente segura.

Exemplo:

```text
mark_completed
- atualiza status
- salva output_json
- salva token_usage_json
- salva execution_time_seconds
- preenche finished_at
```

Se falhar no meio, deve fazer rollback.

O commit nao deve acontecer dentro de `mark_completed`.

A camada externa controla a transacao:

```text
async with session.begin():
  jobs = JobStore(session)
  await jobs.mark_completed(job_id, output)
```

Isso permite compor varias operacoes em uma unica transacao quando necessario.

## Erros

Erros de infraestrutura do store devem ser convertidos para `StoreError`.

Erros especificos de dominio devem usar erros especificos:

```text
JobStoreError
UserStoreError
BillingStoreError
```

O app nao deve expor erro bruto do driver para o frontend.

Exemplo de erro controlado:

```json
{
  "code": "job_store_error",
  "step": "job_store",
  "details": {
    "operation": "mark_completed",
    "job_id": "job_123"
  }
}
```

Regra: `technical_message` fica para logs. API retorna `code`, `step` e
`details` seguros.

## JSON No Banco

Campos como `input_json`, `output_json`, `error_json` e `token_usage_json` devem
ser JSON/JSONB no Postgres.

No SQLite de teste, podem ser texto serializado.

O store deve serializar e desserializar de forma centralizada.

Nao espalhar `json.dumps` e `json.loads` pelo pipeline.

## Timestamps

Usar timestamps timezone-aware.

Campos recomendados:

```text
created_at
updated_at
started_at
finished_at
```

Regras:

- `created_at`: criado uma vez;
- `updated_at`: atualizado em toda alteracao;
- `started_at`: quando o processamento realmente comeca;
- `finished_at`: quando finaliza com sucesso, falha ou cancelamento.

## Migracoes

Usar Alembic.

Estrutura:

```text
alembic.ini
migrations/
  env.py
  versions/
```

Regras:

- toda alteracao de modelo deve gerar migration;
- migration deve ser revisada antes de aplicar;
- nao usar `metadata.create_all()` em producao;
- `create_all()` pode ser aceito apenas em testes isolados.
- `status` e `current_step` devem iniciar como `VARCHAR` validado pela aplicacao,
  nao como ENUM nativo do Postgres.

## Configuracao

`settings.py` deve conter:

```text
database_url
database_echo
database_pool_size
database_max_overflow
database_pool_pre_ping
```

Exemplo:

```text
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kyrg
DATABASE_ECHO=false
```

SQLite pode ser usado assim para teste/dev local:

```text
DATABASE_URL=sqlite+aiosqlite:///./.storage/app.sqlite
```

Mas o alvo de producao deve ser Postgres.

## Limites E Seguranca

O store deve garantir:

- job sempre associado a `user_id`;
- consulta de job por usuario nao pode vazar job de outro usuario;
- email unico;
- senha apenas como hash;
- billing associado a usuario;
- erro salvo sem dados sensiveis desnecessarios;
- outputs grandes com tamanho controlado.

Regras de autorizacao devem ficar na API/service layer, mas o store deve oferecer
metodos que facilitem consultas seguras, como:

```text
get_user_job(user_id, job_id)
list_user_jobs(user_id, limit=20, offset=0)
```

## Ordem De Implementacao

Construir nesta ordem:

1. adicionar dependencias `sqlalchemy`, `alembic` e driver Postgres async;
2. criar `database.py` com `create_async_engine`, `async_sessionmaker` e
   `AsyncSession`;
3. criar `models.py` com `users`, `subscriptions`, `billing_events`, `jobs` e
   `job_events`;
4. configurar Alembic na raiz;
5. gerar primeira migration;
6. criar `base.py` com contratos;
7. criar `jobs.py`;
8. criar `users.py`;
9. criar `billing.py`;
10. criar `factory.py`;
11. integrar `JobStore` no pipeline;
12. integrar `UserStore` na camada de auth;
13. integrar `BillingStore` nos webhooks da Stripe;
14. criar testes unitarios;
15. criar testes de integracao com banco temporario.

## Testes Necessarios

Testes unitarios:

- cria usuario;
- impede email duplicado;
- busca usuario por email;
- cria job associado a usuario;
- marca job como uploaded com arquivo do storage;
- atualiza status do job;
- salva output final;
- salva erro final;
- lista jobs do usuario com paginacao;
- nao retorna job de outro usuario;
- impede transicao invalida de job;
- trata `run_id` duplicado de forma idempotente;
- trata concorrencia de `run_id` duplicado sem vazar erro bruto;
- cria ou atualiza assinatura;
- registra cancelamento de assinatura.
- nao processa webhook Stripe duplicado duas vezes.

Testes de integracao:

- migration sobe schema limpo;
- stores funcionam com `AsyncSession` real;
- rollback acontece em erro;
- pipeline fake cria job, marca running e completed;
- pipeline fake com erro marca failed;
- billing fake atualiza subscription via evento simulado.
- webhook Stripe duplicado nao duplica evento nem efeitos colaterais.

## Criterio De Pronto

O modulo `store` esta pronto para o MVP quando:

- existe banco Postgres configuravel por `DATABASE_URL`;
- o acesso ao banco usa SQLAlchemy Async;
- existe migration inicial versionada;
- `JobStore` cria, atualiza e busca jobs;
- `JobStore` marca upload de arquivo com `mark_uploaded`;
- `JobStore` pagina listagens de jobs;
- `JobStore` protege transicoes invalidas;
- `UserStore` cria e busca usuarios;
- `BillingStore` salva dados essenciais da Stripe;
- `BillingStore` deduplica webhooks por `stripe_event_id`;
- pipeline consegue salvar status e resultado;
- API consegue consultar job por usuario;
- testes cobrem fluxo feliz e falha;
- nenhum arquivo fisico e salvo no banco.
