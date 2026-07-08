Este documento define a estratégia de testes para o package `src/kyrg/workflows/copyanalysis`. O objetivo é proteger o contrato do workflow, a transformação dos dados, a integração com a camada de LLM, a persistência de estado e a qualidade das análises produzidas.

O `CopyAnalysisWorkflow` recebe uma `TranscriptionResult`, prepara uma representação limpa da transcrição, extrai a estrutura persuasiva, identifica os elementos da oferta, analisa os mecanismos de persuasão e consolida tudo em `CopyAnalysisOutput`.

## Escopo

O plano cobre os seguintes módulos:

```text
src/kyrg/workflows/copyanalysis/
├── actions.py
├── nodes.py
├── prompts.py
├── schemas.py
├── state.py
└── workflow.py
```

Também são consideradas as integrações diretas com:

- `LLMBase` e seu retry técnico de structured output;
- `AIActionExecutor`;
- reducers de tokens do LangGraph;
- `WorkflowBase`;
- checkpointers;
- `TranscriptionResult`;
- `SectionType` compartilhado em `workflows/domain_types.py`.

## Objetivos de Qualidade

A suíte deve garantir que:

- o workflow respeita a ordem definida no grafo;
- cada node recebe e devolve somente os dados esperados;
- nenhuma etapa inventa informações ausentes na transcrição;
- tipos estruturados inválidos são tratados pela camada central de LLM;
- falhas não permitem que nodes dependentes sejam executados;
- tokens são contabilizados corretamente;
- execução síncrona e assíncrona possuem comportamento equivalente;
- checkpoints retomam do ponto correto sem repetir trabalho concluído;
- o resultado final é serializável e utilizável pelo `CopyAdaptationWorkflow`.

## Estrutura Recomendada

```text
tests/
├── unit/
│   └── workflows/
│       └── copyanalysis/
│           ├── test_schemas.py
│           ├── test_actions.py
│           └── test_nodes.py
├── integration/
│   └── workflows/
│       └── test_copyanalysis_workflow.py
└── evals/
    └── copyanalysis/
        └── test_copyanalysis_quality.py
```

Prompts, state e montagem do grafo são testados indiretamente. Arquivos dedicados só devem ser criados quando houver comportamento isolado que justifique sua existência.

## Fixtures Obrigatórias

A suíte deve possuir fixtures pequenas, explícitas e reutilizáveis para os seguintes cenários:

- VSL curta com hook, problema, promessa, mecanismo, oferta e CTA;
- vídeo educacional sem oferta comercial;
- transcrição com segmentos e timestamps válidos;
- transcrição sem segmentos;
- transcrição com idioma ausente;
- transcrição em português;
- transcrição em espanhol;
- oferta sem prova, urgência ou preço;
- copy com seção fraca;
- copy com seção incompleta;
- copy com seção ausente;
- transcrição vazia ou composta somente por espaços;
- conteúdo longo o suficiente para expor problemas de contexto e serialização.

Os textos das fixtures devem ser estáticos. Testes determinísticos não podem depender de arquivos externos, rede ou APIs pagas.

## Test Double de LLM

Os testes devem utilizar uma implementação determinística de `LLMBase` que:

- implemente `_structured_once()` e `_astructured_once()`;
- retorne respostas Pydantic configuradas por schema;
- permita enfileirar respostas e exceções;
- registre schema, prompt, modo de execução e ordem das chamadas;
- registre tokens de entrada e saída;
- falhe imediatamente quando receber um schema inesperado;
- permita simular `ValidationError`, `StructuredOutputParsingError` e erro não recuperável.

O double não deve sobrescrever `structured()` ou `astructured()`, pois esses métodos pertencem à política central de retry de `LLMBase`.

---

## Testes Unitários

### `test_schemas.py`

**Status:** Completed on 2026-06-23.

#### `StructuredTranscript`

- aceitar texto com timestamps completos;
- aceitar timestamps nulos;
- rejeitar ausência de texto;
- preservar valores durante serialização JSON.

#### `CopySection`

- aceitar todos os valores canônicos de `SectionType`;
- rejeitar tipos não canônicos como `authority`;
- preservar ordem, texto, propósito e timestamps;
- aceitar timestamps ausentes;
- garantir que tipos de seção permaneçam em inglês e lowercase.

#### `SectionGap`

- aceitar `missing`, `incomplete` e `weak`;
- rejeitar valores fora do enum;
- exigir `section_type` canônico;
- exigir uma justificativa textual;
- serializar corretamente para checkpoint e JSON.

#### `CopyStructureOutput`

- aceitar estrutura completa;
- inicializar listas com factories independentes;
- preservar a ordem das seções;
- aceitar ausência de idioma e hook;
- rejeitar seções ou gaps com tipos inválidos;
- realizar round-trip JSON sem perda de dados.

#### `OfferAnalysisOutput`

- aceitar uma oferta completa;
- aceitar oferta parcial com campos nulos;
- inicializar benefícios, objeções, provas, bônus e urgência como listas independentes;
- preservar evidências associadas aos elementos;
- realizar round-trip JSON sem perda de dados.

#### `PersuasionAnalysisOutput`

- aceitar análise completa;
- aceitar ausência de emoção ou padrão persuasivo;
- validar os valores permitidos para forças, caso estejam restringidos pelo schema;
- preservar sinais, fraquezas e evidências;
- garantir listas default independentes.

#### `CopyAnalysisOutput`

- consolidar estrutura, oferta e persuasão;
- aceitar idioma nulo quando não detectado;
- rejeitar ausência de qualquer análise obrigatória;
- realizar round-trip JSON sem perda de dados.

#### `CopyAnalysisWorkflowContext`

- exigir uma instância de `LLMBase`;
- preservar a LLM configurada;
- não possuir campos antigos de retry pertencentes ao grafo.

### `test_actions.py`

**Status:** Completed on 2026-06-23.

Para cada action, testar `execute()` e `aexecute()`.

#### `ExtractCopyStructure`

- solicitar `CopyStructureOutput` ao método structured correto;
- enviar idioma, transcrição limpa e transcrição estruturada nas tags corretas;
- serializar segmentos como JSON válido;
- suportar lista de segmentos vazia;
- não manter placeholders não resolvidos;
- não incluir o antigo histórico de retry do grafo;
- expor tokens após a chamada.

#### `ExtractOfferElements`

- solicitar `OfferAnalysisOutput`;
- inserir `clean_transcript` e `copy_structure` nas tags corretas;
- serializar o modelo Pydantic sem representação Python ambígua;
- não alterar os objetos recebidos;
- expor tokens após a chamada.

#### `AnalysePersuasion`

- solicitar `PersuasionAnalysisOutput`;
- inserir `copy_structure`, `offer_analysis` e idioma nas tags corretas;
- não reenviar a transcrição integral quando ela não fizer parte do contrato;
- preservar JSON Unicode;
- expor tokens após a chamada.

#### Contrato comum

- propagar exceções da LLM sem substituí-las por resultados parciais;
- gerar prompts sem placeholders residuais;
- produzir prompts equivalentes nos caminhos síncrono e assíncrono;
- garantir que a action não implemente retry próprio;
- garantir que cada action utilize somente seu schema declarado.

### `test_nodes.py`

**Status:** Completed on 2026-06-23.

#### `prepare_copy_input`

- rejeitar ausência de `transcription`;
- rejeitar texto vazio ou composto somente por espaços;
- remover espaços externos;
- normalizar sequências de whitespace sem alterar palavras;
- preservar o idioma da transcrição;
- converter todos os segmentos em `StructuredTranscript`;
- preservar timestamps nulos;
- retornar lista vazia quando não houver segmentos;
- não modificar a `TranscriptionResult` original.

#### `extract_copy_structure`

- exigir contexto;
- exigir `clean_transcript` não vazio;
- encaminhar segmentos e idioma para a action;
- atualizar somente `copy_structure` e tokens;
- propagar falha após o esgotamento do retry central;
- não manter contador, histórico ou router de retry no state.

#### `extract_offer_elements`

- exigir contexto;
- exigir transcrição limpa;
- exigir `copy_structure`;
- encaminhar exatamente a estrutura produzida anteriormente;
- atualizar somente `offer_analysis` e tokens;
- não executar quando a extração estrutural falhar.

#### `analyse_persuasion`

- exigir contexto tipado;
- exigir `copy_structure` e `offer_analysis`;
- encaminhar o idioma correto;
- atualizar somente `persuasion_analysis` e tokens;
- não executar quando a análise de oferta falhar.

#### `build_copy_analysis`

- exigir os três resultados anteriores;
- consolidar os mesmos objetos sem perda de dados;
- preservar o idioma do state;
- retornar somente `analysis`;
- produzir `CopyAnalysisOutput` válido e serializável.

---

## Testes de Integração do Workflow

### `test_copyanalysis_workflow.py`

**Status:** Implemented on 2026-06-23. The async graph scenario remains skipped because `astart()` currently stalls after the first LLM-backed node.

### Caminho feliz

- executar os nodes na ordem `prepare_copy_input`, `extract_copy_structure`, `extract_offer_elements`, `analyse_persuasion` e `build_copy_analysis`;
- realizar exatamente três chamadas estruturadas de LLM;
- retornar `analysis` como `CopyAnalysisOutput`;
- preservar idioma, seções, oferta e análise persuasiva;
- acumular os tokens das três chamadas;
- não executar qualquer router de retry removido.

### Transcrição sem segmentos

- concluir o workflow usando apenas `clean_transcript`;
- enviar `structured_transcription` como lista vazia;
- manter timestamps de seções nulos quando não houver evidência temporal;
- produzir análise final válida.

### Structured output inválido seguido de sucesso

- fazer a primeira tentativa de uma action gerar `ValidationError`;
- confirmar que `LLMBase` executa uma segunda tentativa dentro do mesmo node;
- confirmar que o prompt seguinte contém o diagnóstico do schema;
- confirmar que o workflow continua após a resposta válida;
- garantir que nodes anteriores não sejam executados novamente;
- garantir que não existem campos de retry técnico no state final.

### Erro de parsing seguido de sucesso

- fazer a primeira tentativa gerar `StructuredOutputParsingError`;
- confirmar que a segunda tentativa ocorre;
- confirmar que o workflow continua sem router adicional;
- contabilizar as duas tentativas na observabilidade definida para a operação.

### Retry técnico esgotado

- retornar structured output inválido em todas as tentativas;
- confirmar a emissão de `StructuredOutputError`;
- garantir que os nodes seguintes não sejam executados;
- garantir que nenhum `CopyAnalysisOutput` parcial seja publicado.

### Erro não recuperável

- simular erro de autenticação, configuração ou programação;
- confirmar que não ocorre retry de schema;
- confirmar propagação imediata da exceção;
- garantir que nodes posteriores não sejam executados.

### Tokens

- acumular os tokens das três actions no caminho feliz;
- incluir consumo de tentativas técnicas quando ocorrer retry;
- não duplicar tokens no reducer do state;
- garantir que `total_tokens` seja igual a `input_tokens + output_tokens`;
- garantir que uma nova action não reutilize incorretamente tokens da action anterior.

### Checkpoint e retomada

- persistir o estado após cada node concluído;
- retomar com a mesma `thread_id` a partir do node interrompido;
- não executar novamente nodes já confirmados no checkpoint;
- iniciar estado limpo com uma nova `thread_id`;
- impedir que outputs intermediários de outra thread contaminem a execução;
- restaurar corretamente os modelos Pydantic presentes no state.

### Execução assíncrona

- executar o workflow por `astart()`;
- usar `_astructured_once()` nos doubles;
- garantir a mesma ordem e o mesmo resultado funcional da execução síncrona;
- confirmar que nenhuma chamada síncrona bloqueante é usada no caminho assíncrono.

### Dependências obrigatórias

- falhar antes da primeira chamada de LLM quando não existir transcrição;
- interromper no node correto quando um estado intermediário obrigatório estiver ausente;
- não produzir análise final parcialmente preenchida;
- fornecer mensagens de erro que identifiquem o campo ausente.

---

## Testes de Regressão Obrigatórios

**Status:** Pendente.

- `section_type="authority"` deve ser rejeitado pelo schema e corrigido pelo retry central, nunca normalizado silenciosamente pelo workflow.
- Tipos de seção devem permanecer canônicos, lowercase e em inglês.
- Uma seção existente não pode ser marcada simultaneamente como `missing`.
- `section_gaps` deve distinguir `missing`, `incomplete` e `weak`.
- Ausência de prova não pode gerar prova inventada em `OfferAnalysisOutput`.
- Ausência de CTA não pode gerar CTA inventado.
- `clean_transcript` e `structured_transcription` não podem ser interpretados como conteúdos diferentes.
- Timestamps só podem ser preenchidos quando existirem segmentos que os sustentem.
- A ordem das seções deve seguir a transcrição original.
- Campos antigos `copy_structure_error_history` e `copy_structure_retry_count` não podem reaparecer no state.
- `copy_structure_router` não pode reaparecer no grafo.
- Structured output inválido não pode encerrar a execução antes das tentativas configuradas na `LLMBase`.
- Erros não recuperáveis não podem entrar em loop de retry.
- O output final deve conter uma única análise consolidada, sem duplicar os resultados em estruturas paralelas.

---

## Evals de Qualidade

### `test_copyanalysis_quality.py`

**Status:** Implementado e opt-in.

Evals realizam chamadas reais e não devem fazer parte da suíte determinística padrão. Devem usar o marker `live_eval` e exigir configuração explícita por variável de ambiente.

O módulo implementado cobre:

- julgamento estruturado e independente da estrutura, oferta, persuasão e consistência entre etapas;
- verificações determinísticas de preservação dos outputs e integridade dos timestamps;
- detecção de elementos comerciais e provas não sustentados pela transcrição;
- estabilidade mínima da sequência estrutural e do hook em execuções repetidas;
- logs de provider, modelos, fixture, duração, tokens, schema e resultado, sem registrar prompts ou chaves.

Configuração necessária:

- `KYRG_RUN_COPYANALYSIS_EVALS=1`;
- `OPENAI_API_KEY`;
- `KYRG_COPYANALYSIS_EVAL_MODEL`;
- `KYRG_COPYANALYSIS_JUDGE_MODEL` opcional, usando o modelo de geração por padrão.

### Estrutura da copy

- identificar corretamente o hook principal;
- manter a ordem real das seções;
- não inventar seções ausentes;
- distinguir seção ausente, incompleta e fraca;
- atribuir propósito coerente a cada seção;
- usar timestamps compatíveis com os segmentos fornecidos.

### Oferta

- identificar corretamente produto, público, problema, desejo e promessa;
- não inventar preço, garantia, bônus, prova, urgência ou CTA;
- associar evidência somente quando sustentada pela transcrição;
- retornar campos nulos ou listas vazias quando a informação não existir.

### Persuasão

- identificar padrão persuasivo compatível com a estrutura;
- avaliar hook, promessa, prova, urgência e CTA de forma coerente;
- produzir fraquezas específicas e sustentadas por evidência;
- não transformar opinião estratégica em fato extraído;
- manter o idioma textual da transcrição.

### Consistência entre etapas

- `OfferAnalysisOutput` não pode contradizer fatos explícitos de `CopyStructureOutput`;
- `PersuasionAnalysisOutput` deve usar estrutura para julgamentos estruturais e oferta para julgamentos comerciais;
- a análise final não pode perder campos produzidos pelas etapas anteriores;
- a mesma fixture avaliada repetidamente deve manter estabilidade mínima nos campos estruturais.

## Observabilidade dos Evals

Cada execução real deve registrar:

- provider e modelo;
- duração de cada action;
- tokens de entrada e saída;
- número de tentativas estruturadas;
- schema solicitado;
- status da validação;
- identificador da fixture;
- resultado da avaliação de qualidade.

Prompts completos, transcrições sensíveis e chaves de API não devem aparecer em logs de nível `INFO`.

---

## Critérios de Aceitação

O package estará adequadamente protegido quando:

- todos os testes unitários forem determinísticos e passarem sem rede;
- todos os cenários de integração passarem nos modos síncrono e assíncrono;
- retries estruturados forem testados sem adicionar loops ao grafo;
- retomada por checkpoint for comprovada;
- regressões conhecidas estiverem cobertas;
- evals estiverem isolados por marker e configuração explícita;
- nenhuma fixture depender de segredo ou serviço externo;
- o resultado final puder ser consumido diretamente pelo `CopyAdaptationWorkflow`.

## Comandos de Execução

```bash
# Testes unitários do package
.venv/bin/pytest tests/unit/workflows/copyanalysis -q

# Integração do workflow
.venv/bin/pytest tests/integration/workflows/test_copyanalysis_workflow.py -q

# Suíte determinística completa
.venv/bin/pytest tests -m "not live_eval" -q

# Evals reais, quando explicitamente configurados
KYRG_RUN_COPYANALYSIS_EVALS=1 \
OPENAI_API_KEY="..." \
KYRG_COPYANALYSIS_EVAL_MODEL="..." \
.venv/bin/pytest tests/evals/copyanalysis -m live_eval -q
```
