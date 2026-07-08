# Pipeline Application Layer

Este modulo sera a camada de orquestracao da aplicacao.

Ele nao deve conter regras internas dos workflows, nao deve implementar banco,
nao deve implementar storage e nao deve executar tarefas pesadas diretamente na
API. A funcao dele e conectar as pecas ja existentes do app de forma previsivel:

- schemas publicos em `src/app/schemas`;
- storage em `src/app/storage`;
- persistencia em `src/app/store`;
- fila em `src/app/queue`;
- providers em `src/app/providers`;
- workflows da biblioteca em `src/kyrg/workflows`;
- execucao pesada futura em `src/app/worker`.

## Decisao Arquitetural

Os schemas de entrada e saida do pipeline ja existem em
`src/app/schemas/pipeline.py`.

Por isso, este package nao deve criar outro `schemas.py`. Criar um schema dentro
de `src/app/pipeline` duplicaria contratos e criaria divergencia entre API,
service e worker.

Regra:

- `src/app/schemas/pipeline.py`: contratos publicos usados por API, service e
  worker;
- `src/app/pipeline`: logica de preparacao e orquestracao;
- `src/app/worker`: execucao do job em processo separado ou inline.

## Objetivo Do Pipeline

O pipeline deve receber uma solicitacao normalizada da aplicacao e transformar
isso em um job executavel.

Fluxo esperado:

1. receber input da API;
2. validar e normalizar input;
3. criar job no banco;
4. salvar arquivo de entrada no storage;
5. marcar job como `uploaded`;
6. enviar `job_id` para a fila;
7. retornar resposta inicial para a API.

O resultado final do workflow nao deve ser produzido nesta etapa. Ele sera
produzido pelo worker/runner depois que o job for processado.

## Modulos Planejados

### `input.py`

Responsabilidade:

- validar dados recebidos antes da criacao do job;
- normalizar `run_id`, idioma, providers, modelos e formatos de saida;
- diferenciar os tipos de pipeline: analise de copy e adaptacao de copy;
- impedir que dados incompletos avancem para storage, banco ou fila.

Por que existe:

Validacao de input misturada em `service.py` deixa a orquestracao dificil de ler
e de testar. Separar esse modulo permite testar regras de entrada sem precisar
abrir banco, storage ou fila.

Regras esperadas:

- `source_type` deve ser `video` ou `audio`;
- `transcriber_provider` deve existir;
- `transcriber_model` deve existir;
- `llm_provider` deve existir;
- `analysis_model` deve existir;
- `adaptation_model` deve existir apenas no fluxo de adaptacao;
- `user_profile` deve existir apenas no fluxo de adaptacao;
- `output_formats` deve ser normalizado e limitado aos formatos suportados pelo
  app;
- `max_duration_seconds`, quando existir, deve ser positivo.

### `files.py`

Responsabilidade:

- receber o arquivo enviado pela API;
- gerar a key de storage usando `app.storage.paths`;
- chamar `storage.save_upload(...)` ou `storage.save_file(...)`;
- retornar `StoredFile`;
- preparar referencias de arquivo para persistir no job.

Por que existe:

Arquivo fisico nao pertence ao banco. O banco guarda referencia, status e
metadados. O storage guarda o arquivo. Separar `files.py` evita que a camada de
service saiba como montar keys ou como salvar arquivos em backend local, S3, R2
ou GCP.

Regras esperadas:

- usar `job_input_key(job_id, filename)` para arquivo original;
- nunca montar path de storage manualmente no service;
- salvar somente depois que o job existir, porque a key depende do `job_id`;
- retornar `storage_backend`, `input_file_key` e `input_file_uri`;
- em caso de erro no upload, propagar erro controlado para o service marcar o
  job como failed quando fizer sentido.

### `jobs.py`

Responsabilidade:

- montar payload de criacao do job;
- chamar `store.jobs.create_job(...)`;
- chamar `store.jobs.mark_uploaded(...)`;
- chamar `store.jobs.mark_failed(...)` em falhas controladas;
- isolar o formato de payload esperado pelo banco.

Por que existe:

O `JobStore` e responsavel por persistencia. O pipeline precisa decidir quais
dados do request entram no job. Essa traducao nao deve ficar espalhada em
rotas, service ou worker.

Regras esperadas:

- criar job com `user_id`, `pipeline_type`, `run_id` e `input_json`;
- manter `input_json` como objeto serializavel;
- nao salvar arquivo binario no banco;
- persistir referencias do storage apenas depois do upload;
- usar transicoes validas do store: `pending -> uploaded -> running`.

### `service.py`

Responsabilidade:

- expor a fachada principal do pipeline para a API;
- coordenar input, job, storage e queue;
- manter o fluxo de alto nivel legivel;
- retornar resposta inicial da execucao.

Por que existe:

O service e o ponto unico que a API chama para iniciar um pipeline. Ele nao deve
conter detalhes de storage, validacao profunda ou regras SQL. Ele deve apenas
coordenar os modulos especializados.

Fluxo de alto nivel esperado:

```text
normalize input
create job
save input file
mark uploaded
enqueue job
return initial response
```

Regras esperadas:

- nao executar workflows diretamente;
- nao conhecer detalhes concretos de Celery, LocalStorage ou SQLAlchemy;
- receber dependencias prontas por injecao;
- usar `QueueBase.enqueue(job_id)` para disparar processamento;
- se a fila falhar, marcar o job como failed;
- se o upload falhar apos criar job, marcar o job como failed;
- nao apagar arquivo de input neste momento, porque o worker ainda precisa dele.

### `__init__.py`

Responsabilidade:

- exportar somente a API publica do package de pipeline;
- evitar que modulos internos sejam importados por acidente.

Por que existe:

Mantem uma superficie publica pequena. A API deve importar o service principal,
nao funcoes internas de normalizacao ou montagem de payload.

## Worker Relacionado

O worker nao deve ficar dentro de `src/app/pipeline`.

Modulo futuro:

```text
src/app/worker/
  runner.py
  tasks.py
  celery_app.py
```

### `worker/runner.py`

Responsabilidade:

- receber `job_id`;
- carregar job no banco;
- marcar job como `running`;
- materializar arquivo do storage quando necessario;
- construir providers;
- executar workflows;
- salvar output final;
- marcar job como `completed` ou `failed`;
- limpar arquivos temporarios e arquivos de input quando a politica permitir.

Por que fica separado:

Executar workflow e tarefa pesada. Isso nao deve rodar dentro da request HTTP
quando o app estiver com fila real. Separar runner agora permite rodar inline no
MVP e migrar para Celery depois sem mudar a API.

## Dependencias Esperadas

O service deve receber dependencias prontas, por exemplo:

- `AppStore`;
- `StorageBase`;
- `QueueBase`;
- settings da aplicacao;
- clock opcional para testes;
- gerador de `run_id` opcional para testes.

Ele nao deve criar engine, abrir conexao de banco, configurar Celery ou decidir
provider concreto sozinho.

Essas decisoes pertencem a camada de bootstrap da API ou command line.

## Erros E Rollback

Erros esperados devem virar erros controlados da aplicacao.

Exemplos:

- input invalido;
- falha ao salvar arquivo;
- falha ao criar job;
- falha ao marcar upload;
- falha ao enfileirar job.

Politica:

- se o job ainda nao existe, retornar erro controlado;
- se o job ja existe e o upload falha, marcar job como failed;
- se o upload funcionou e a fila falha, marcar job como failed;
- se houver arquivo salvo e o processo nao puder continuar, avaliar cleanup por
  `storage.delete_prefix(job_prefix(job_id))`;
- nao esconder erro tecnico nos logs.

## Ordem De Implementacao

Construir nesta ordem:

1. revisar `src/app/schemas/pipeline.py`;
2. criar `src/app/pipeline/input.py`;
3. criar `src/app/pipeline/files.py`;
4. criar `src/app/pipeline/jobs.py`;
5. criar `src/app/pipeline/service.py`;
6. criar `src/app/pipeline/__init__.py`;
7. criar testes unitarios do pipeline;
8. criar `src/app/worker/runner.py`;
9. integrar fila inline;
10. integrar Celery posteriormente;
11. integrar API.

## Testes Esperados

### Unitarios

- normalizacao de input de analise;
- normalizacao de input de adaptacao;
- rejeicao de input invalido;
- geracao correta de key de storage;
- montagem correta de payload de job;
- chamada correta de `mark_uploaded`;
- chamada correta de `queue.enqueue`;
- job marcado como failed quando upload falha;
- job marcado como failed quando enqueue falha.

### Integracao

- criar job real no banco;
- salvar arquivo real em storage local;
- marcar job como uploaded;
- enfileirar com `InlineQueue`;
- recuperar status do job depois da operacao.

## Fora Do Escopo Deste Package

Este package nao deve implementar:

- autenticação;
- Stripe;
- exporters;
- rotas HTTP;
- comandos CLI;
- execucao interna dos workflows;
- configuracao de Celery;
- migracoes de banco;
- implementacao concreta de storage.

Essas partes entram em outros packages do app.
