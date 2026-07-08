# Plano de Testes: TranscriberWorkflow

Este documento define a estratégia de testes para o package `src/kyrg/workflows/transcriber`. O objetivo é proteger o contrato executável atual da transcrição, da preparação de mídia e da correção contextual, sem depender de FFmpeg, subprocessos, filesystem, rede, APIs pagas ou respostas não determinísticas nas suítes regulares.

Todos os módulos descritos neste plano têm **Status: Pendente**.

## Contrato Atual Protegido

O fluxo ativo é:

```text
START
  |-- source_type == "audio" --> prepare_audio
  |-- qualquer outro valor ----> extract_audio
                                      |
                                      v
                             audio_text_converter
                                      |
                                      v
                                measure_audio
                                      |
  |-- duration <= 180 e need_correction truthy
  |          --> extract_hybrid_context
  |          --> correction_transcriber
  |          --> END
  |
  `-- caso contrario --> END
```

Os testes devem distinguir contrato atual de comportamento desejável:

- os nodes e a transcrição são síncronos;
- somente as actions oferecem `execute()` e `aexecute()`;
- o ramo sem correção termina sem preencher `status="accepted"` ou `final_result`;
- `need_correction` controla a rota, embora não esteja declarado em `TranscriberState`;
- `correction_llm` está declarado no state, mas não é usado no roteamento;
- não existe agente de qualidade ativo no grafo;
- não há retry, timeout, fallback, checkpoint, cleanup ou compensação configurados pelo package.

Esses pontos devem ser cobertos por testes de caracterização. Uma mudança futura de produto deve alterar primeiro o contrato esperado e, no mesmo change set, atualizar os testes correspondentes.

## Escopo

Fontes cobertos direta ou indiretamente:

```text
src/kyrg/workflows/transcriber/
|-- actions.py
|-- nodes.py
|-- prompts.py
|-- schemas.py
|-- state.py
`-- workflow.py
```

Fora de escopo:

- bytecodes órfãos de antigos `agent.py` e `tools.py`, pois esses fontes não existem e não são importados;
- comportamento genérico herdado de `WorkflowBase`, exceto quando observável no workflow compilado;
- funcionamento interno de FFmpeg, providers de transcrição, `CommandRunner`, `AIActionExecutor` ou LLMs;
- qualidade semântica de uma transcrição real na suíte determinística;
- arquitetura antiga descrita por `QUALITY_AGENT` e suas ferramentas, que não participa do grafo atual.

Não deve ser criado teste para módulo-fonte inexistente nem para os `.pyc` órfãos.

## Pirâmide De Testes

### 1. Testes unitários determinísticos

Local: `tests/unit/workflows/transcriber/`.

Validam schemas, state, routers, actions, nodes e montagem estrutural do grafo. Toda fronteira externa deve usar fake, stub, spy ou mock.

### 2. Integração determinística do workflow

Local: `tests/integration/workflows/`.

Executa o grafo real, mas substitui mídia, transcritores e LLMs por doubles locais. Deve provar ordem, rotas, reducers, interrupção em falhas e estado final sem acessar serviços reais.

### 3. Integrações reais e evals futuros

Locais futuros: `tests/integration/live/transcriber/` e `tests/evals/transcriber/`.

Devem ser opt-in, isolados por marker e variável de ambiente. Não podem ser coletados como parte da suíte determinística padrão nem usados como gate obrigatório de pull request.

## Estrutura Recomendada

```text
tests/
|-- unit/
|   `-- workflows/
|       `-- transcriber/
|           |-- README.md
|           |-- test_transcriber_workflow.py
|           |-- test_transcriber_nodes_transcription.py
|           |-- test_transcriber_nodes_correction.py
|           |-- test_transcriber_nodes_media.py
|           |-- test_transcriber_routers.py
|           |-- test_transcriber_actions.py
|           |-- test_transcriber_schemas.py
|           `-- test_transcriber_state_contract.py
|-- integration/
|   |-- workflows/
|   |   |-- test_transcriber_workflow.py
|   |   `-- test_transcriber_failure_reentry.py
|   `-- live/
|       `-- transcriber/
|           `-- test_live_transcription_providers.py       # futuro
`-- evals/
    `-- transcriber/
        `-- test_transcriber_quality.py                    # futuro
```

## Fixtures E Test Doubles

### Fixtures mínimas

- `transcription_result`: texto, idioma, segmentos, timestamps e metadados estáticos;
- `transcription_result_with_duplicate_ids`: dois segmentos originais com o mesmo ID;
- `domain_context_output`: modelo Pydantic completo, com termos, entidades, correções e incertezas;
- `corrected_transcription_output`: texto global e correções parciais de segmentos;
- `local_transcriber_class` e `remote_transcriber_class`: classes fake configuráveis;
- `transcriber_context`: `TranscriberWorkflowContext` com LLMs e config fakes;
- `workflow_runtime`: stub mínimo com atributo `context`;
- states pequenos para áudio, vídeo, com e sem correção;
- resultados fake de comando com `stdout` em bytes.

As fixtures devem ser construídas em memória, possuir valores explícitos e evitar arquivos de mídia reais.

### Doubles obrigatórios

- `ExtractAudio`, `ConvertToWhisperFormat`, `AudioSize` e `CommandRunner`: spies que registrem construção e execução;
- `MediaContext`: usar o objeto real apenas se sua construção não tiver efeitos; caso contrário, usar spy;
- transcritor local: classe derivada de `TranscriberBase`, captura argumentos e implementa somente o contrato necessário de `transcribe()`;
- transcritor remoto: classe derivada de `TranscriberAPIBase`, captura também `api_key` e nunca acessa rede;
- LLM fake: implementa `structured()` e `astructured()`, captura prompt e schema, enfileira respostas Pydantic ou exceções;
- `AIActionExecutor.run`: mock nos testes isolados de nodes e implementação real somente quando seu uso fizer parte da integração escolhida;
- `WorkflowRuntime`: stub com `context=None` ou contexto configurado;
- builder do grafo: spy para registrar nodes, edges e mapas condicionais sem executar o workflow.

Patches de mídia e execução devem atingir os símbolos já importados em `kyrg.workflows.transcriber.nodes`, por exemplo `kyrg.workflows.transcriber.nodes.AudioSize`, e não apenas os módulos onde as classes foram originalmente definidas.

### Disciplina de sincronismo

- actions síncronas devem chamar exclusivamente `structured()`;
- actions assíncronas devem aguardar exclusivamente `astructured()`;
- testes assíncronos podem usar `asyncio.run()` para não exigir plugin adicional;
- `audio_text_converter` deve chamar somente `transcribe()`, nunca `atranscribe()`;
- nodes de contexto e correção devem chamar `AIActionExecutor.run`, não uma variante assíncrona;
- não se deve prometer que `astart()` torna operações bloqueantes não bloqueantes: isso não é oferecido pelo package atual.

## Testes Unitários

### `test_transcriber_workflow.py`

**Status:** Implementado.

**Escopo:** montagem e topologia do grafo, sem executar mídia ou LLM.

Casos:

- registrar exatamente os seis nodes atuais com seus callables: `extract_audio`, `prepare_audio`, `audio_text_converter`, `measure_audio`, `extract_hybrid_context` e `correction_transcriber`;
- validar o mapa condicional inicial: `normalize_audio -> prepare_audio` e `extract_audio -> extract_audio`;
- validar as duas convergências em `audio_text_converter`;
- validar a sequência `audio_text_converter -> measure_audio`;
- validar o mapa condicional de `measure_audio`: `to_correction -> extract_hybrid_context` e `not_correction -> END`;
- validar `extract_hybrid_context -> correction_transcriber -> END`;
- confirmar que não existem node, edge ou router de agente de qualidade;
- confirmar que não há node de retry, fallback, human review, aceitação, cleanup ou checkpoint configurado por `_build()`;
- caracterizar que `CheckpointerBase` importado não participa da montagem;
- confirmar `STATE_SCHEMA = TranscriberState` e `CONTEXT_SCHEMA = TranscriberWorkflowContext`;
- exercitar os valores retornados pelos routers contra os mapas registrados, evitando rotas sem destino;
- cobrir estruturalmente o limite inclusivo de 180 segundos e os dois caminhos de origem.

### `test_transcriber_nodes_transcription.py`

**Status:** Implementado.

**Escopo:** `audio_text_converter` e seleção/configuração do transcritor.

Casos felizes:

- construir transcritor local com `audio_path`, `model_name`, `language` e `temperature` exatos;
- omitir `api_key` no construtor local;
- construir transcritor remoto com os mesmos argumentos e `api_key`;
- aceitar `language=None`, `temperature=None` e API key vazia, conforme o contrato atual;
- chamar `transcribe()` exatamente uma vez e retornar o mesmo objeto em `result`;
- provar que `atranscribe()` não é chamado, mesmo se o fake o disponibilizar.

Falhas e edge cases:

- `runtime.context is None` gera `RuntimeError` antes de instanciar o transcritor;
- transcritor remoto com API key `None` gera `ValueError` antes da instanciação;
- `transcriptor` que não seja classe faz `issubclass` propagar `TypeError`;
- chaves obrigatórias ausentes no state propagam `KeyError`;
- exceções do construtor e de `transcribe()` propagam sem tradução;
- retorno `None` ou objeto inesperado de `transcribe()` é repassado sem validação;
- a dataclass aceitar configuração de tipo inadequado não deve ser confundida com validação do node.

### `test_transcriber_nodes_correction.py`

**Status:** Implementado.

**Escopo:** `extract_hybrid_context` e `correction_transcriber`.

`extract_hybrid_context`:

- exigir contexto e `result`, com `RuntimeError` e `ValueError` específicos;
- construir `ExtractDomainContext` com a LLM e o resultado corretos;
- chamar `AIActionExecutor.run()` exatamente uma vez;
- retornar a mesma instância de `DomainContextOutput` produzida;
- montar uma mensagem de usuário com `QUALITY_AGENT_INPUT`, contexto e transcrição serializados;
- caracterizar que a mensagem é produzida, mas não consumida por agente ativo;
- retornar `input_tokens`, `output_tokens` e `total_tokens` da action;
- propagar exceções do executor;
- propagar `KeyError` quando qualquer chave esperada faltar em `tokens_usage`.

`correction_transcriber`:

- exigir contexto, resultado e contexto de domínio antes de executar a action;
- construir `CorrectTranscription` com dependências e entradas exatas;
- substituir sempre o texto global por `corrected_text`;
- retornar uma cópia profunda, mantendo o `TranscriptionResult` original inalterado;
- preservar timestamps, idioma e demais metadados não corrigidos;
- atualizar somente segmentos cujos IDs apareçam na resposta;
- manter segmentos não mencionados intactos;
- ignorar IDs desconhecidos silenciosamente;
- caracterizar que, com IDs originais duplicados, somente o último segmento indexado é atualizado;
- caracterizar que correções repetidas para o mesmo ID aplicam a última versão;
- aceitar lista de correções vazia, alterando apenas o texto global;
- retornar `status="corrected"` e `human_review_reason=None`;
- retornar as três métricas de token e propagar `KeyError` se estiverem incompletas;
- propagar falhas externas sem publicar resultado parcial.

Reducers de token devem ser comprovados no teste integrado do grafo; neste módulo basta verificar o delta devolvido por cada node.

### `test_transcriber_nodes_media.py`

**Status:** Implementado.

**Escopo:** `prepare_audio`, `extract_audio` e `measure_audio`, sempre sem subprocesso ou filesystem real.

`prepare_audio`:

- criar `MediaContext(source_path, audio_path)` com os paths exatos;
- criar um novo `CommandRunner` e passá-lo a `ConvertToWhisperFormat`;
- chamar `execute()` uma vez;
- devolver o mesmo `audio_path`;
- caracterizar que o node não valida arquivo de saída nem retorno da conversão;
- propagar `KeyError` de state incompleto e qualquer exceção externa.

`extract_audio`:

- repetir as garantias equivalentes usando `ExtractAudio`;
- provar que entrada e saída usam os mesmos paths fornecidos pelo state;
- propagar falhas sem cleanup ou tradução.

`measure_audio`:

- construir `AudioSize` com contexto e runner corretos;
- converter bytes com whitespace, por exemplo `b" 180.0\n"`, para `180.0`;
- aceitar zero, negativo, `NaN`, `inf` e `-inf`, caracterizando o uso direto de `float()`;
- propagar `ValueError` para bytes vazios ou não numéricos;
- propagar erro quando `stdout` não fornecer `decode()` compatível;
- devolver somente `audio_duration_in_seconds` e não alterar o state de entrada.

### `test_transcriber_routers.py`

**Status:** Implementado.

**Escopo:** decisões puras de `primary_router` e `secondary_router`.

`primary_router`:

- `source_type="audio"` retorna `normalize_audio`;
- `source_type="video"` retorna `extract_audio`;
- campo ausente, `None`, string vazia e valor inválido também retornam `extract_audio`;
- caracterizar que o `Literal` do TypedDict não valida valores em runtime.

`secondary_router`:

- duração menor que 180 com `need_correction` truthy retorna `to_correction`;
- exatamente 180 é limite inclusivo e retorna `to_correction`;
- duração maior que 180 sempre retorna `not_correction`;
- `need_correction` ausente, `None`, `False`, zero ou outro valor falsy retorna `not_correction`;
- valores truthy não booleanos acionam correção quando a duração permite;
- duração negativa com flag truthy entra em correção;
- `NaN` encerra sem correção porque sua comparação é falsa;
- infinitos positivo e negativo seguem a comparação nativa de `float`;
- duração ausente ou `None` gera `RuntimeError`;
- duração de tipo incompatível pode propagar `TypeError`.

### `test_transcriber_actions.py`

**Status:** Implementado.

**Escopo:** `ExtractDomainContext` e `CorrectTranscription`, nos modos síncrono e assíncrono.

`ExtractDomainContext`:

- serializar `TranscriptionResult` com `model_dump_json(indent=2)`;
- inserir a serialização em `EXTRACT_DOMAIN_CONTEXT` sem placeholder residual;
- chamar `structured(prompt=..., output_schema=DomainContextOutput)` em `execute()`;
- aguardar `astructured(prompt=..., output_schema=DomainContextOutput)` em `aexecute()`;
- devolver exatamente o modelo Pydantic fornecido pela LLM;
- propagar a mesma exceção nos dois modos.

`CorrectTranscription`:

- serializar resultado e domínio com indentação e inseri-los em `CORRECTION`;
- solicitar `CorrectedTranscriptionOutput` no método correto;
- garantir equivalência de prompt e schema entre os modos sync e async;
- provar que `execute()` não chama `astructured()` e `aexecute()` não chama `structured()`;
- propagar falha de serialização ou da LLM sem retry próprio.

Os testes dos prompts devem verificar conteúdo estrutural e interpolação, evitando snapshots frágeis de whitespace. `QUALITY_AGENT` não deve ser tratado como action ativa.

### `test_transcriber_schemas.py`

**Status:** Implementado.

**Escopo:** validação Pydantic e contrato permissivo das dataclasses.

`DomainContextOutput`:

- exigir `language`, `main_subject`, `content_type` e `summary`;
- inicializar todas as listas com factories independentes entre instâncias;
- aceitar listas completas de correções e termos incertos;
- aceitar strings vazias e itens duplicados, caracterizando a ausência de restrições adicionais;
- realizar round-trip de JSON sem perda.

`PossibleCorrection` e `UncertainTerm`:

- exigir todos os campos declarados;
- aceitar confiança exatamente `0` e `1`;
- rejeitar confiança abaixo de `0` ou acima de `1`;
- aceitar textos vazios conforme o schema atual.

`CorrectedSegment` e `CorrectedTranscriptionOutput`:

- exigir `id`, `text` e `corrected_text` onde aplicável;
- criar `corrected_segments` vazio e independente por padrão;
- aceitar IDs negativos, duplicados ou desconhecidos;
- aceitar divergência entre texto global e textos dos segmentos;
- validar serialização e restauração.

Dataclasses de contexto:

- exigir os três argumentos de `TranscriberWorkflowContext` no construtor;
- validar defaults `temperature=0.0` e `api_key=None` de `TranscriptorConfig`;
- aceitar `temperature=None`;
- caracterizar que dataclasses não validam tipos em runtime.

### `test_transcriber_state_contract.py`

**Status:** Implementado.

**Escopo:** shape do TypedDict, reducers e divergências conhecidas.

Casos:

- confirmar os quatro campos obrigatórios declarados: `source_path`, `source_type`, `audio_path` e `model_name`;
- confirmar os campos opcionais atuais, inclusive resultado, duração, domínio, status e revisão humana;
- inspecionar os metadados `Annotated` e provar que `input_tokens`, `output_tokens` e `total_tokens` usam `operator.add`;
- provar em integração que deltas sucessivos de contexto e correção são somados, não sobrescritos;
- registrar explicitamente que `need_correction` não aparece nas annotations do state;
- registrar explicitamente que `correction_llm` aparece, mas `secondary_router` não o consulta;
- caracterizar que TypedDict não faz validação runtime de valores nem impede chaves extras;
- não assumir contrato do campo herdado `messages` além do necessário para observar a atualização produzida pelo node.

## Integração Determinística Do Workflow

### `tests/integration/workflows/test_transcriber_workflow.py`

**Status:** Pendente.

**Escopo:** executar o grafo real com todas as fronteiras externas fakeadas.

Caminhos felizes:

- áudio sem correção: `prepare_audio -> audio_text_converter -> measure_audio -> END`;
- vídeo sem correção: `extract_audio -> audio_text_converter -> measure_audio -> END`;
- áudio com correção e duração abaixo de 180 segundos;
- vídeo com correção e duração exatamente igual a 180 segundos;
- confirmar ordem e quantidade exatas das chamadas em cada caminho;
- confirmar que contexto e correção não executam no ramo sem correção;
- confirmar que o transcritor sempre executa de forma síncrona;
- confirmar estado final corrigido, status, preservação de metadados e soma de tokens;
- confirmar que a mensagem de qualidade pode permanecer no state sem acionar agente;
- confirmar que o ramo sem correção não cria `status="accepted"` nem `final_result`;
- confirmar que um `status` antigo pode permanecer no ramo sem correção, conforme merge do state atual.

Falhas integradas:

- falha de conversão ou extração impede transcrição e nodes posteriores;
- falha de transcrição impede medição e correção;
- duração inválida interrompe antes do router secundário completar;
- falha na extração de contexto impede a correção;
- falha na correção não publica cópia parcialmente alterada;
- nenhuma falha externa é convertida, suprimida ou tentada novamente pelo package.

Não incluir chamadas reais nesse módulo.

### `tests/integration/workflows/test_transcriber_failure_reentry.py`

**Status:** Pendente.

**Escopo:** ausência de retry/checkpoint explícito e repetição de efeitos em reinvocação.

Casos:

- uma falha de `transcribe()` gera uma única tentativa naquela execução;
- reinvocar o workflow repete preparação/extração e transcrição;
- falha de LLM não causa retry, backoff ou fallback no grafo;
- reinvocação após falha de LLM repete conversão, transcrição e chamada LLM anteriores, salvo comportamento externo ao package;
- falha após criação da mídia não aciona cleanup nem compensação;
- o package não fornece idempotency key para provider remoto;
- ausência de checkpointer configurado não deve ser confundida com eventual capacidade herdada de `WorkflowBase`;
- call logs dos spies devem demonstrar efeitos repetidos sem usar rede ou disco.

Esses testes são de caracterização e documentam risco operacional; não devem inventar uma política de retry inexistente.

## Evals E Integrações Reais Futuras

### Integração real de providers

Módulo futuro: `tests/integration/live/transcriber/test_live_transcription_providers.py`.

**Status:** Pendente, futuro e opt-in.

Objetivo:

- validar autenticação, upload, formato aceito, idioma, modelo e shape real de `TranscriptionResult` para cada provider suportado;
- usar um fixture de áudio curto, versionado e sem dados pessoais;
- conferir tolerâncias de duração e timestamps sem exigir texto byte a byte;
- registrar provider, modelo, duração, custo/tokens quando disponíveis e identificador da fixture;
- nunca registrar API keys ou conteúdo sensível.

Requisitos antes da implementação:

- registrar um marker dedicado, por exemplo `live_transcription`, no `pyproject.toml`;
- exigir `KYRG_RUN_TRANSCRIBER_LIVE=1` e secrets específicos do provider;
- pular com motivo claro quando o opt-in ou secret estiver ausente;
- definir limites de custo, timeout e frequência;
- executar fora do gate determinístico padrão, preferencialmente em job manual ou agendado.

### Evals de qualidade

Módulo futuro: `tests/evals/transcriber/test_transcriber_quality.py`.

**Status:** Pendente, futuro e opt-in.

Objetivo:

- medir fidelidade textual, preservação de significado, nomes próprios, termos técnicos e timestamps;
- comparar transcrição bruta e corrigida contra referências humanas versionadas;
- medir se correções melhoram erros suportados sem inventar conteúdo;
- avaliar diferentes idiomas, sotaques, ruído, sobreposição de fala e domínios técnicos;
- separar métricas determinísticas, como WER/CER, de julgamento semântico por LLM;
- repetir amostras para observar variância e regressões por provider/modelo.

Esses evals devem usar o marker existente `live_eval`, opt-in explícito e thresholds documentados. Resultados não determinísticos não substituem os testes unitários nem os testes integrados com fakes.

## Riscos E Regressões Conhecidas

Cobertura obrigatória, distribuída pelos módulos acima:

- divergência entre `need_correction` e `correction_llm` pode desabilitar correção silenciosamente;
- valores inválidos de `source_type` seguem o ramo de vídeo;
- o ramo sem correção não marca aceitação nem define resultado final canônico;
- duração negativa pode entrar em correção; `NaN` pode evitá-la; infinito é aceito;
- API key remota vazia é aceita, embora `None` seja rejeitado;
- retorno inválido do transcritor não é validado;
- IDs de segmentos desconhecidos são ignorados e IDs duplicados têm semântica de última ocorrência;
- o texto global corrigido pode divergir dos segmentos;
- `QUALITY_AGENT_INPUT` é gerado, mas não há consumidor ativo;
- referências do prompt a ferramentas antigas não representam a topologia atual;
- falhas externas propagam sem contexto adicional;
- ausência de retry/checkpoint pode repetir chamadas pagas em reinvocação;
- nodes síncronos podem bloquear um runner assíncrono externo;
- ausência de validação de paths e saída da conversão pode postergar falhas;
- reducers podem duplicar métricas se um node for reexecutado sobre o mesmo state.

Testes de caracterização que consolidem um comportamento claramente indesejado devem ter nome explícito, por exemplo `test_secondary_router_negative_duration_currently_routes_to_correction`. Se houver issue para mudança de contrato, pode-se usar `xfail(strict=True)` com razão e referência; não usar `xfail` genérico para esconder regressões.

## Critérios De Aceitação

O package estará adequadamente protegido quando:

- todos os dez módulos determinísticos priorizados tiverem sido implementados e estiverem verdes;
- testes unitários e de integração determinística passarem sem rede, FFmpeg, subprocesso ou mídia real;
- todas as rotas e o limite inclusivo de 180 segundos estiverem cobertos;
- transcritores local e remoto tiverem argumentos, método síncrono e falhas verificados;
- actions tiverem paridade de prompt/schema e propagação de erro nos modos sync e async;
- correção preservar o objeto original e todos os metadados não alterados;
- reducers acumularem corretamente tokens de contexto e correção;
- topologia provar a ausência de agente de qualidade, retry e checkpoint configurados;
- inconsistências de state e comportamentos permissivos estiverem documentados por testes de caracterização;
- reinvocação e repetição de efeitos estiverem demonstradas deterministicamente;
- integrações reais e evals permanecerem opt-in e fora da suíte padrão;
- nenhum teste fizer referência a `agent.py`, `tools.py` ou bytecodes órfãos;
- a suíte não depender da ordem global dos testes nem compartilhar objetos mutáveis entre casos.

## Comandos Pytest Recomendados

```bash
# Coleta dos módulos unitários, sem executar
.venv/bin/pytest tests/unit/workflows/transcriber --collect-only -q

# Suíte unitária do package
.venv/bin/pytest tests/unit/workflows/transcriber -q

# Um módulo prioritário durante desenvolvimento
.venv/bin/pytest tests/unit/workflows/transcriber/test_transcriber_nodes_correction.py -q

# Um caso ou grupo por expressão
.venv/bin/pytest tests/unit/workflows/transcriber -k "secondary_router or correction" -q

# Integração determinística do workflow
.venv/bin/pytest \
  tests/integration/workflows/test_transcriber_workflow.py \
  tests/integration/workflows/test_transcriber_failure_reentry.py \
  -q

# Suíte determinística completa atual, excluindo evals reais
.venv/bin/pytest tests -m "not live_eval" -q
```

Comandos futuros, somente depois de registrar o marker e implementar os módulos opt-in:

```bash
# Integrações reais de providers
KYRG_RUN_TRANSCRIBER_LIVE=1 \
.venv/bin/pytest tests/integration/live/transcriber -m live_transcription -q

# Evals reais de qualidade
KYRG_RUN_TRANSCRIBER_EVALS=1 \
.venv/bin/pytest tests/evals/transcriber -m live_eval -q
```

Secrets de provider devem ser fornecidos pelo ambiente/CI e nunca escritos em comandos versionados, fixtures, logs ou relatórios de teste.
