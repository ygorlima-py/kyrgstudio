# Worker Do App

Este modulo sera responsavel por executar jobs que ja foram criados pelo
`src/app/pipeline`.

O pipeline prepara o trabalho:

```text
cria job
salva arquivo
marca uploaded
enfileira job_id
retorna resposta inicial
```

O worker executa o trabalho:

```text
recebe job_id
carrega job
marca running
executa workflows
salva resultado
marca completed ou failed
```

## Decisao Arquitetural

O worker fica fora de `src/app/pipeline` porque executar workflow e tarefa
pesada.

O pipeline deve ser rapido e seguro para a API. O worker pode demorar, chamar
FFmpeg, transcritor, LLMs e workflows.

Essa separacao permite que a API apenas crie e agende o job, enquanto o
processamento pesado roda no worker via Celery.

`InlineQueue` pode continuar existindo para testes e desenvolvimento local, mas
Celery faz parte da implementacao planejada deste modulo desde o inicio.

## Modulos Planejados

### `runner.py`

O que vai ser feito:

- receber um `job_id`;
- buscar o job no banco usando `JobStore`;
- validar se o job pode ser executado;
- marcar o job como `running`;
- localizar o arquivo original salvo no storage;
- preparar um arquivo local para os workflows quando necessario;
- construir providers de transcricao e LLM;
- executar o fluxo correto conforme `job.pipeline_type`;
- salvar `output_json`, `token_usage_json` e `execution_time_seconds`;
- marcar o job como `completed`;
- marcar o job como `failed` quando ocorrer erro;
- limpar arquivos temporarios locais usados durante a execucao.

Por que vai ser feito:

O runner centraliza a execucao real do processamento. Sem ele, a API ou o
pipeline teriam que executar workflows diretamente, o que misturaria upload,
orquestracao e processamento pesado no mesmo lugar.

Regra principal:

```text
runner executa job existente
pipeline cria e agenda job
```

O `runner.py` nao deve:

- receber upload;
- criar job inicial;
- decidir autenticacao;
- lidar com Stripe;
- responder HTTP;
- configurar Celery;
- salvar arquivo inicial no storage.

### `materializer.py`

O que vai ser feito:

- receber `storage_backend`, `input_file_key` e `input_file_uri`;
- garantir que o arquivo esteja disponivel em um caminho local;
- se o storage for local, usar o caminho local diretamente quando possivel;
- se o storage for remoto, baixar o arquivo para uma pasta temporaria;
- devolver o caminho local que os workflows conseguem usar.

Por que vai ser feito:

FFmpeg e os workflows atuais trabalham melhor com arquivo local. O materializer
isola a diferenca entre LocalStorage, S3, R2 e GCP.

Sem esse modulo, o runner teria que conhecer detalhes de cada backend de
storage.

Regra principal:

```text
workflow recebe caminho local
storage pode ser local ou remoto
```

### `outputs.py`

O que vai ser feito:

- consolidar resultado final em formato persistivel no banco;
- montar `output_json`;
- montar `token_usage`;
- montar `execution_time_seconds`;
- separar output de analise e output de adaptacao;
- garantir que o banco receba apenas dados serializaveis.

Por que vai ser feito:

Os workflows retornam objetos estruturados. O banco deve receber um dicionario
limpo, serializavel e estavel.

Separar essa etapa evita que o runner vire um arquivo grande misturando
execucao, conversao de output e persistencia.

### `workflows.py`

O que vai ser feito:

- construir e executar os workflows da biblioteca `kyrg`;
- executar `TranscriberWorkflow`;
- executar `CopyAnalysisWorkflow`;
- executar `CopyAdaptationWorkflow` quando o pipeline for de adaptacao;
- retornar um resultado interno padronizado para o runner.

Por que vai ser feito:

O runner precisa coordenar execucao, mas nao deve carregar todos os detalhes de
como cada workflow e instanciado.

Esse modulo cria uma fronteira clara:

```text
runner decide quando executar
workflows.py sabe como executar
```

### `tasks.py`

O que vai ser feito:

- definir funcoes que a fila pode chamar;
- receber apenas `job_id`;
- abrir dependencias necessarias;
- chamar `runner.run(job_id)`.

Por que vai ser feito:

Celery ou outro sistema de fila precisa de uma funcao de entrada simples. Essa
funcao nao deve conter a logica do processamento. Ela deve apenas adaptar o
formato da fila para o runner.

Neste projeto, `tasks.py` deve expor a task Celery responsavel por receber o
`job_id` e delegar a execucao para o runner.

Exemplo conceitual:

```text
run_pipeline_job_task(job_id)
  -> cria dependencias
  -> chama runner
```

### `celery_app.py`

O que vai ser feito:

- criar e configurar a instancia do Celery;
- configurar broker;
- configurar backend de resultado, se necessario;
- registrar tasks;
- centralizar configuracoes de fila usadas pelo worker.

Por que vai ser feito:

Configuracao de Celery nao deve ficar no `PipelineService`, nem no `runner`.
Fila e execucao sao responsabilidades diferentes.

Este modulo faz parte da implementacao inicial do worker. Ele permite rodar o
processamento fora do processo da API, mantendo a API responsavel apenas por
criar o job e enviar o `job_id` para a fila.

### `__init__.py`

O que vai ser feito:

- exportar somente a API publica do package worker;
- evitar imports acidentais de modulos internos;
- manter superficie publica pequena.

Por que vai ser feito:

O restante do app deve depender de poucos pontos claros, como `WorkerRunner` ou
uma task publica, nao de funcoes internas de materializacao ou montagem de
outputs.

## Fluxo De Execucao Esperado

```text
Queue recebe job_id
-> task/handler chama runner
-> runner busca job
-> runner marca running
-> runner materializa arquivo
-> runner executa workflows
-> runner monta output
-> runner marca completed
```

Em caso de erro:

```text
erro durante execucao
-> runner captura erro
-> runner marca failed
-> runner salva error_json
-> runner limpa temporarios locais
```

## Tipos De Pipeline

### `copy_analysis`

O que deve executar:

```text
TranscriberWorkflow
CopyAnalysisWorkflow
```

Resultado esperado:

```text
transcription
copy_analysis
token_usage
execution_time_seconds
```

### `copy_adaptation`

O que deve executar:

```text
TranscriberWorkflow
CopyAnalysisWorkflow
CopyAdaptationWorkflow
```

Resultado esperado:

```text
transcription
copy_analysis
adapted_script
validation
missing_proofs
token_usage
execution_time_seconds
```

## Dependencias Esperadas

O runner deve receber dependencias prontas ou factories bem definidas:

- `AppStore` ou `JobStoreBase`;
- `StorageBase`;
- `AppSettings`;
- factories de providers;
- diretorio temporario;
- clock/temporizador, se necessario para testes.

Ele nao deve criar configuracoes espalhadas no codigo. Bootstrap, API, CLI ou
task devem montar dependencias e entregar para o runner.

## Regras De Estado Do Job

O worker deve respeitar as transicoes do store:

```text
uploaded -> running -> completed
uploaded -> running -> failed
uploaded -> failed
```

O worker nao deve executar job que ainda esta `pending`, porque isso significa
que o arquivo ainda nao foi salvo ou que o pipeline nao finalizou a etapa de
upload.

## Cleanup

O worker pode limpar:

- arquivos temporarios locais criados para execucao;
- downloads locais de arquivos remotos;
- arquivos intermediarios que nao precisam ser preservados.

O worker nao deve apagar o arquivo original do storage sem uma politica clara.

Essa decisao deve considerar:

- debug;
- reprocessamento;
- custo de storage;
- privacidade;
- regra de retencao do produto.

## Ordem De Implementacao

Construir nesta ordem:

1. `runner.py`;
2. `outputs.py`;
3. `workflows.py`;
4. `materializer.py`;
5. `celery_app.py`;
6. `tasks.py` para adaptar Celery ao runner;
7. testes unitarios do runner com fakes;
8. testes unitarios das tasks com runner fake;
9. teste de integracao com job real, storage local e workflows fake;
10. teste de integracao da task Celery em modo eager ou com task chamada de
    forma controlada.

## Testes Esperados

### Unitarios

- runner rejeita job inexistente;
- runner rejeita job que nao esta `uploaded`;
- runner marca job como `running`;
- runner chama executor correto para `copy_analysis`;
- runner chama executor correto para `copy_adaptation`;
- runner marca `completed` quando executor retorna sucesso;
- runner marca `failed` quando executor falha;
- output final e serializavel;
- token usage e tempo sao persistidos;
- cleanup local e chamado em sucesso e falha;
- task Celery recebe apenas `job_id`;
- task Celery chama o runner;
- configuracao do Celery nao executa workflow no import.

### Integracao

- criar job real `uploaded`;
- salvar arquivo real em LocalStorage;
- executar runner com workflows fake;
- verificar status `completed`;
- verificar `output_json`;
- verificar `token_usage_json`;
- verificar `execution_time_seconds`;
- verificar status `failed` quando executor fake falha;
- executar task Celery em modo controlado com runner fake e confirmar que ela
  delega para o runner.

## Fora Do Escopo Deste Modulo

Este modulo nao deve implementar:

- rotas HTTP;
- upload inicial de arquivo;
- criacao inicial de job;
- autenticacao;
- billing/Stripe;
- exporters;
- UI;
- regras de permissao;
- implementacao concreta de provider;
- implementacao interna dos workflows da biblioteca.
