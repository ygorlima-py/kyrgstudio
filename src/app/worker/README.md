# Worker Da Aplicacao

O package `src/app/worker` executa jobs que ja foram criados, tiveram o arquivo
de entrada salvo e foram colocados na fila pelo `PipelineService`.

O worker nao inicia uploads nem cria jobs. Sua entrada e um `job_id` persistido
com status `uploaded`; sua saida e o mesmo job em estado terminal `completed` ou
`failed`.

```text
API/Pipeline                       Worker
------------                       ------
valida input                       recebe job_id
cria job pending                   carrega job uploaded
salva arquivo                      marca running
marca uploaded                     executa workflows
enfileira job_id   ------------->  persiste resultado ou erro
retorna ao cliente                 limpa arquivos do processamento
```

## Fontes De Verdade

Este documento segue os contratos existentes nestes pontos:

- `app.schemas.pipeline`: tipos de pipeline e input publico;
- `app.schemas.workflow`: contratos internos entre runner e executor;
- `app.store.base.JobStoreBase`: leitura e transicoes do job;
- `app.storage.base.StorageBase`: acesso e remocao de arquivos;
- `app.queue.base.QueueBase`: envio do `job_id` para processamento;
- `kyrg.workflows`: implementacao dos workflows de transcricao, analise e
  adaptacao.

Quando houver divergencia entre este README e um contrato executavel, o contrato
executavel deve ser corrigido ou o README deve ser atualizado no mesmo change.

## Responsabilidades

O worker deve:

- consumir somente o identificador do job;
- validar que o job existe e esta pronto para execucao;
- tornar as transicoes de estado persistentes;
- disponibilizar o arquivo de entrada em um caminho local;
- montar os providers definidos em `job.input_json`;
- executar os workflows da biblioteca `kyrg` de forma assincrona;
- converter os estados finais dos workflows para um contrato interno estavel;
- persistir output, tokens e tempo total;
- persistir erro controlado quando a execucao falhar;
- limpar arquivos temporarios e arquivos do job conforme a politica de storage.

O worker nao deve:

- receber upload HTTP;
- criar o job inicial;
- autenticar usuario;
- verificar permissao de acesso ao job;
- processar pagamentos ou webhooks;
- implementar regras internas dos workflows `kyrg`;
- retornar uma resposta HTTP;
- guardar arquivos binarios no banco.

## Estado Atual

| Modulo | Estado | Observacao |
| --- | --- | --- |
| `runner.py` | Parcialmente implementado | Executa o fluxo principal e suporta arquivo local. Fronteiras de transacao e cleanup do arquivo original ainda precisam ser resolvidos. |
| `outputs.py` | Implementado | Monta payload persistivel. Ainda aceita formatos brutos alem do contrato canonico. |
| `workflows.py` | Concluido | Executa e normaliza os pipelines de analise e adaptacao usando os workflows `kyrg`. |
| `materializer.py` | Pendente | Necessario para baixar inputs de storage remoto. |
| `celery_app.py` | Pendente | A instancia e a configuracao real do Celery ainda nao existem. |
| `tasks.py` | Pendente | A task que liga Celery ao runner ainda nao existe. |
| `__init__.py` | Pendente | Deve exportar apenas a API publica estabilizada. |

O adapter `app.queue.CeleryQueue` ja sabe chamar `task.delay(job_id)`, mas isso
nao configura um worker Celery. A dependencia `celery`, o broker, a instancia da
aplicacao e a task ainda precisam ser adicionados para a fila externa funcionar.

## Contratos Internos

### Entrada Do Runner

```text
WorkerRunner.run(job_id: int) -> WorkerRunResult
```

O job carregado precisa conter:

- `id`;
- `status="uploaded"`;
- `pipeline_type`;
- `input_json`;
- `storage_backend`;
- `input_file_key`;
- `input_file_uri`.

### Pedido Para Os Workflows

O runner cria um `WorkflowExecutionRequest` com:

- `job_id`;
- `pipeline_type`;
- `source_path` local;
- `source_type`;
- copia de `input_json`.

### Resultado Dos Workflows

O contrato canonico entre `workflows.py` e o runner e
`WorkflowExecutionResult`:

```text
output_json: dict[str, Any]
token_usage: dict[str, Any]
```

`workflows.py` deve traduzir os estados especificos da biblioteca `kyrg` para
esse contrato. `outputs.py` nao deve precisar descobrir qual chave arbitraria
representa cada resultado.

As chaves brutas atuais da biblioteca sao:

| Workflow | Resultado principal | Tokens |
| --- | --- | --- |
| `TranscriberWorkflow` | `result` | `input_tokens`, `output_tokens`, `total_tokens` |
| `CopyAnalysisWorkflow` | `analysis` | `input_tokens`, `output_tokens`, `total_tokens` |
| `CopyAdaptationWorkflow` | `adapted_script` | `input_tokens`, `output_tokens`, `total_tokens` |

No fluxo de adaptacao, `validation_passed`, `validation_errors`,
`validation_warnings` e `missing_proofs` pertencem ao objeto
`adapted_script`. A traducao para o output do app deve acontecer uma unica vez
em `workflows.py`.

### Resultado Do Runner

O runner retorna `WorkerRunResult`, contendo apenas o resumo da execucao:

- `job_id`;
- `status`;
- `pipeline_type`;
- `execution_time_seconds`.

O resultado completo permanece no banco, em `jobs.output_json`.

## Fluxo De Execucao

```text
Celery recebe job_id
-> task cria as dependencias da execucao
-> runner carrega o job
-> runner exige status uploaded
-> job passa para running
-> input e resolvido para um caminho local
-> workflows.py executa o pipeline solicitado
-> outputs.py monta o payload persistivel
-> job passa para completed
-> arquivos temporarios e arquivos do job sao limpos
```

Em caso de erro depois que o job foi carregado:

```text
erro
-> converter para AppError ou erro controlado equivalente
-> persistir error_json
-> mover job para failed
-> executar cleanup
-> propagar o erro para a task registrar a falha
```

Falha ao registrar `failed` nao deve substituir nem esconder o erro original,
mas precisa ser registrada em log com `job_id` para investigacao.

## Transacoes Do Banco

Os stores SQLAlchemy nao fazem `commit`; a camada que abre a sessao controla a
transacao. O worker nao deve manter uma transacao aberta durante FFmpeg,
transcricao ou chamadas de LLM.

As operacoes precisam ser duraveis em transacoes curtas:

1. carregar e mover `uploaded -> running`, depois commit;
2. executar os workflows sem transacao de banco aberta;
3. mover `running -> completed`, depois commit;
4. em falha, mover o estado permitido para `failed`, depois commit.

O `runner.py` atual recebe um `JobStoreBase` unico e ainda nao define essas
fronteiras. Antes de ligar o runner a um worker real, deve ser criado um
coordenador de sessao/Unit of Work ou uma factory que forneca stores em
transacoes curtas. Envolver `runner.run()` inteiro em um unico
`async_transaction_scope` nao e aceitavel, porque manteria conexao e transacao
abertas durante todo o processamento pesado.

## Execucao Dos Workflows

`workflows.py` deve implementar `WorkflowExecutor` e ser a unica camada do app
que conhece a montagem dos workflows `kyrg`.

### `copy_analysis`

Executa, em ordem:

1. `TranscriberWorkflow.astart()`;
2. `CopyAnalysisWorkflow.astart()`.

O resultado normalizado deve conter:

```text
transcription
copy_analysis
```

### `copy_adaptation`

Executa, em ordem:

1. `TranscriberWorkflow.astart()`;
2. `CopyAnalysisWorkflow.astart()`;
3. `CopyAdaptationWorkflow.astart()`.

O resultado normalizado deve conter:

```text
transcription
copy_analysis
adapted_script
validation
missing_proofs
```

### Providers

Os providers e modelos devem vir de `request.input_json`:

- `transcriber_provider` e `transcriber_model`;
- `llm_provider` e `analysis_model`;
- `adaptation_model`, apenas para `copy_adaptation`;
- `language` e `need_correction`;
- `user_profile`, apenas para `copy_adaptation`.

`workflows.py` usa as factories de `app.providers`; o runner nao instancia
adapters concretos de LLM ou transcricao.

O executor deve acumular tokens por etapa sem confundir os contadores de
transcricao, analise e adaptacao. O formato final precisa ser um dicionario
serializavel e estavel.

## `runner.py`

Responsabilidade:

- controlar a sequencia de alto nivel da execucao;
- validar o job e seu estado;
- solicitar a resolucao do arquivo;
- construir `WorkflowExecutionRequest`;
- chamar `WorkflowExecutor.execute(...)`;
- medir o tempo total;
- montar o output por meio de `outputs.py`;
- persistir sucesso ou falha;
- garantir cleanup em `finally`.

O runner recebe dependencias. Ele nao deve construir engine, sessao, storage,
Celery ou providers concretos.

## `workflows.py`

Responsabilidade:

- implementar `WorkflowExecutor`;
- validar os campos de `input_json` necessarios para a execucao;
- construir os contextos de cada workflow;
- usar as factories de providers;
- executar os grafos com `astart()`;
- validar as chaves finais retornadas por cada grafo;
- converter os resultados para `WorkflowExecutionResult`.

Nao pertence a este modulo persistir job, fazer cleanup ou configurar Celery.

## `outputs.py`

Responsabilidade:

- receber `WorkflowExecutionResult`;
- separar o formato persistido de `copy_analysis` e `copy_adaptation`;
- adicionar `token_usage` e `execution_time_seconds`;
- garantir serializacao JSON;
- rejeitar pipeline ou resultado invalido com `WorkflowResultError`.

Depois que `workflows.py` estiver implementado, o caminho principal deve aceitar
somente `WorkflowExecutionResult`. O suporte atual a `Mapping` e `BaseModel` e
uma compatibilidade temporaria, nao o contrato definitivo entre os modulos.

## `materializer.py`

Responsabilidade:

- implementar `WorkerFileResolver`;
- usar diretamente o caminho de `LocalStorage` quando ele for valido;
- baixar objetos de S3, R2 ou GCP para um workspace temporario;
- retornar `ResolvedInputFile`;
- apagar somente a copia local temporaria em `cleanup(...)`.

O contrato atual de `StorageBase` nao possui operacao de download. Portanto,
storage remoto nao pode ser implementado corretamente apenas com `exists()` e
`uri()`. Antes de concluir `materializer.py`, o storage precisa expor uma
operacao comum de download para arquivo local, implementada por todos os
backends remotos.

## Cleanup E Retencao

Existem dois tipos diferentes de cleanup:

1. o materializer remove a copia temporaria local criada para executar FFmpeg e
   workflows;
2. ao terminar o job, a camada de execucao remove os arquivos do job no storage
   com `delete_prefix(job_prefix(job_id))`.

O segundo comportamento segue a politica definida em `app/storage/README.md`:
o video de entrada e temporario e deve ser apagado depois que o processamento
terminar, tanto em sucesso quanto em falha.

O `runner.py` atual executa apenas o primeiro tipo de cleanup. A remocao do
prefixo do job ainda precisa ser implementada. O resultado estruturado nao e
apagado porque pertence ao banco, nao ao storage de arquivos.

## `celery_app.py`

Responsabilidade:

- criar a instancia real de `Celery`;
- ler broker e configuracoes do worker a partir de settings;
- registrar as tasks do package;
- configurar serializacao JSON;
- definir limites de tempo e comportamento de acknowledgement de forma
  explicita;
- nao executar workflows durante import.

O banco e a fonte de verdade para status e resultado do job. O result backend
do Celery nao deve duplicar `jobs.output_json` sem uma necessidade concreta.

## `tasks.py`

Responsabilidade:

- declarar a task Celery publica;
- receber somente `job_id`;
- abrir o ciclo de vida das dependencias do worker;
- chamar o runner assincrono de forma segura;
- fechar sessoes, engine e recursos criados pela task;
- deixar a excecao visivel ao Celery depois que o job for marcado como failed.

A task nao deve repetir a logica de `WorkerRunner` nem receber o payload inteiro
do pipeline. O banco guarda o payload; a fila transporta apenas o identificador.

Retries automaticos do Celery nao devem ser habilitados antes de existir uma
politica para jobs deixados em `running` por encerramento abrupto do processo.
Sem essa politica, uma nova entrega encontraria o job em `running` e o runner
atual o rejeitaria.

## Concorrencia E Idempotencia

- `mark_running` deve continuar usando a transicao atomica
  `uploaded -> running` do `JobStore`;
- duas tasks nao podem executar o mesmo job simultaneamente;
- uma entrega duplicada para job `running`, `completed` ou `failed` nao deve
  iniciar os workflows novamente;
- o comportamento para job abandonado em `running` deve ser definido antes de
  ativar retry automatico ou `acks_late`.

## Ordem De Implementacao

1. implementar `workflows.py` e seus testes unitarios;
2. tornar `outputs.py` estrito em torno de `WorkflowExecutionResult`;
3. definir e implementar fronteiras curtas de transacao para o runner;
4. adicionar download ao contrato de storage remoto;
5. implementar `materializer.py`;
6. implementar cleanup do prefixo do job;
7. adicionar settings e dependencia do Celery;
8. implementar `celery_app.py`;
9. implementar `tasks.py`;
10. ajustar `worker/__init__.py` com a API publica;
11. criar testes unitarios do worker;
12. criar testes de integracao do runner;
13. criar teste controlado da task Celery.

## Testes Necessarios

### Unitarios

- rejeitar `job_id` invalido;
- rejeitar job inexistente;
- rejeitar job que nao esteja `uploaded`;
- garantir a transicao para `running` antes da execucao;
- construir corretamente `WorkflowExecutionRequest`;
- selecionar o fluxo de analise;
- selecionar o fluxo de adaptacao;
- validar os campos obrigatorios de `input_json`;
- normalizar resultados reais dos tres workflows `kyrg`;
- somar tokens por etapa;
- persistir output serializavel e tempo em sucesso;
- persistir erro controlado em falha;
- preservar o erro original se `mark_failed` tambem falhar;
- limpar arquivo materializado em sucesso e falha;
- remover o prefixo do job em sucesso e falha;
- garantir que a task receba apenas `job_id`;
- garantir que importar `celery_app.py` nao execute workflows;
- garantir que configuracao ausente de broker falhe com erro controlado.

### Integracao

- executar runner com job real `uploaded`, banco temporario, LocalStorage e
  workflows fake;
- confirmar commits separados para `running` e `completed`;
- confirmar status `failed` e `error_json` quando o executor falhar;
- confirmar persistencia de `output_json`, `token_usage_json` e
  `execution_time_seconds`;
- confirmar cleanup do arquivo local do job;
- materializar e limpar um objeto remoto usando backend fake;
- executar a task Celery em modo eager com runner fake;
- confirmar que entrega duplicada nao executa o mesmo job duas vezes.

Testes de qualidade das copies e chamadas reais de LLM pertencem aos workflows
ou aos evals, nao ao worker.

## Fora Do Escopo

- rotas HTTP;
- upload inicial;
- criacao inicial do job;
- autenticacao e autorizacao;
- Stripe e billing;
- implementacao interna dos providers;
- prompts e regras internas dos workflows;
- exportacao para Markdown, texto ou PDF;
- interface do usuario.
