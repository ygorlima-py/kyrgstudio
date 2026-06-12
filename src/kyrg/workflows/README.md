# Workflows

Este pacote concentra os workflows inteligentes do projeto.

A ideia principal é dividir a criação de VSLs, criativos e vídeos de marketing em etapas menores, claras e reutilizáveis. Cada workflow resolve uma parte do processo. Depois, um workflow mestre poderá coordenar todos eles sem criar um state gigante e confuso.

## Visão Geral

O produto final desejado é uma plataforma capaz de automatizar a produção de VSLs e criativos com IA.

Fluxo macro desejado:

```text
material de entrada
-> transcrição
-> análise da copy
-> adaptação ou criação de roteiro
-> planejamento de cenas
-> geração de voz
-> geração visual
-> montagem
-> revisão
-> exportação
```

Nem todo workflow precisa ser agente.

A regra atual do projeto é:

```text
usar LLM estruturada quando a tarefa for extração, análise ou geração controlada
usar processo determinístico quando a tarefa for mídia, arquivo, FFmpeg, montagem ou validação objetiva
usar agente apenas quando existir decisão real com ferramentas e benefício claro
```

O agente ReAct foi removido do `TranscriberWorkflow` porque gerava redundância, aumentava muito o custo de tokens e não era necessário para o fluxo atual.

## Estrutura Atual

Workflows existentes:

```text
TranscriberWorkflow
CopyAnalysisWorkflow
```

Fluxo atual no `main.py`:

```text
TranscriberWorkflow
-> CopyAnalysisWorkflow
```

O primeiro workflow transforma áudio ou vídeo em uma transcrição final corrigida.

O segundo workflow transforma essa transcrição final em uma análise estratégica de copy.

## WorkflowBase

`WorkflowBase` é a base comum dos workflows.

Ele centraliza:

```text
criação do StateGraph
context_schema
initial_state
context de execução
checkpointer opcional
thread_id opcional
compile
start
astart
draw_workflow
```

O state guarda dados do processo.

O context guarda dependências de execução.

Exemplos de dependências no context:

```text
LLMs
transcriber config
providers
configurações externas
```

Essa separação é importante porque o state pode ser salvo em checkpointer. Dependências como classes, SDKs, clients e providers não devem ser salvas no state.

## Checkpointers

O projeto possui abstração para checkpointers em:

```text
src/kyrg/workflows/checkpointers.py
```

Backends atuais:

```text
MemoryCheckpointer
SQLiteCheckpointer
PostgresCheckpointer
```

Eles permitem persistir o estado do workflow e retomar execuções com `thread_id`.

Regra importante:

```text
state deve carregar dados serializáveis
context deve carregar dependências não serializáveis
```

Por isso o transcriber foi movido para o context, dentro de `TranscriptorConfig`, em vez de ficar no state.

## Contagem De Tokens

Os workflows usam campos acumuláveis no state:

```text
input_tokens
output_tokens
total_tokens
```

Esses campos usam reducer com `operator.add`.

Cada node que chama LLM retorna a quantidade de tokens gasta naquela chamada.

Exemplo conceitual:

```text
node A retorna input_tokens = 100, output_tokens = 50
node B retorna input_tokens = 200, output_tokens = 80
state final tem input_tokens = 300, output_tokens = 130
```

Isso deixa o resultado final do workflow fácil de ler:

```text
result["input_tokens"]
result["output_tokens"]
result["total_tokens"]
```

A contagem precisa representar a chamada atual da LLM, não o acumulado histórico da instância.

## TranscriberWorkflow

Responsabilidade:

```text
Transformar áudio ou vídeo em uma transcrição final corrigida.
```

Fluxo atual:

```text
START
-> extract_audio ou prepare_audio
-> audio_text_converter
-> extract_hybrid_context
-> correction_transcriber
-> END
```

Quando a entrada é vídeo, o workflow usa `extract_audio`.

Quando a entrada é áudio, o workflow usa `prepare_audio`.

Depois disso, ambos os caminhos chegam em `audio_text_converter`.

### Entrada Principal

Campos principais do state:

```text
source_path
source_type
audio_path
model_name
language
```

`source_path` é o arquivo original recebido.

`source_type` indica se a entrada é `audio` ou `video`.

`audio_path` é o caminho do áudio preparado ou extraído.

`model_name` é o modelo usado pelo transcriber.

`language` é opcional e pode guiar o transcriber.

### Context

O context do transcriber é `TranscriberWorkflowContext`.

Ele carrega:

```text
correction_llm
extract_context_llm
transcriptor_config
```

`transcriptor_config` carrega:

```text
transcriptor
transcriptor_temperature
transcriptor_api_key
```

Essa decisão evita salvar classes Python no state e evita erro de serialização em checkpointers.

## Nodes Do TranscriberWorkflow

### primary_router

Decide o caminho inicial.

Se `source_type` for `audio`:

```text
prepare_audio
```

Se `source_type` for `video`:

```text
extract_audio
```

### extract_audio

Extrai o áudio de um vídeo usando o módulo `editor`.

Entrada:

```text
source_path
audio_path
```

Saída:

```text
audio_path
```

### prepare_audio

Normaliza ou converte um arquivo de áudio para o formato esperado pela transcrição.

Esse node existe porque o usuário pode enviar áudio em formatos diferentes, com codec, canais ou sample rate inadequados para o transcriber.

### audio_text_converter

Executa a transcrição.

Ele lê o transcriber do context:

```text
context.transcriptor_config.transcriptor
```

Depois instancia o provider e chama:

```text
transcribe()
```

Saída:

```text
result: TranscriptionResult
```

### extract_hybrid_context

Usa LLM com structured output para extrair contexto da transcrição.

Esse contexto ajuda a correção posterior.

Extrai:

```text
idioma
assunto principal
tipo de conteúdo
resumo
termos importantes
nomes próprios
termos técnicos
possíveis correções
termos incertos
regras de correção
```

Saída:

```text
domain_context
input_tokens
output_tokens
total_tokens
```

### correction_transcriber

Usa a action `CorrectTranscription` para corrigir a transcrição com base no `domain_context`.

A LLM não deve recriar o `TranscriptionResult` inteiro.

Ela retorna uma estrutura de correção, e o node aplica essa correção no resultado original, preservando:

```text
timestamps
segments
words
probabilities
audio_path
provider
model
raw_response
```

Saída:

```text
final_result
status = corrected
human_review_reason = None
input_tokens
output_tokens
total_tokens
```

## O Que Falta No TranscriberWorkflow

Gerar `audio_path` automaticamente.

Hoje o caminho ainda é passado no input de teste. O ideal é o workflow criar um diretório por execução/projeto e gerar o caminho interno do áudio preparado.

Reduzir payload enviado para LLM.

Hoje alguns prompts ainda usam `TranscriptionResult` completo em JSON. Isso pode ficar caro, principalmente se incluir segmentos, words e metadados.

Salvar outputs intermediários.

Exemplos:

```text
transcription.json
domain_context.json
final_transcription.json
```

Criar testes fake.

Testes importantes:

```text
roteamento audio/video
extração de áudio
preparação de áudio
transcrição fake
extração de contexto fake
correção fake
contagem de tokens
checkpointer com state serializável
```

Criar suporte para transcrição por chunks.

Para vídeos longos, o caminho futuro deve ser:

```text
extract_audio
-> inspect_audio_duration
-> split_audio_chunks
-> transcribe_chunks
-> merge_transcriptions
-> extract_hybrid_context
-> correction_transcriber
```

Essa melhoria deve ficar no workflow, não nos transcribers.

## CopyAnalysisWorkflow

Responsabilidade:

```text
Ler a transcrição final e entender a estrutura persuasiva da copy.
```

Fluxo atual:

```text
START
-> prepare_copy_input
-> extract_copy_structure
-> extract_offer_elements
-> analyse_persuasion
-> build_copy_analysis
-> END
```

Esse workflow é linear.

Ele não usa agente ReAct porque a tarefa principal é análise estruturada, não decisão com tools.

### Entrada Principal

```text
transcription: TranscriptionResult
```

Ele recebe a transcrição final do `TranscriberWorkflow`.

### Context

O context do copy analysis é `CopyAnalysisWorkflowContext`.

Ele carrega:

```text
analysis_llm
```

Essa LLM é usada para extrair estrutura de copy, elementos de oferta e análise persuasiva.

## Nodes Do CopyAnalysisWorkflow

### prepare_copy_input

Prepara a transcrição para análise.

Faz:

```text
valida se existe transcrição
extrai texto limpo
normaliza espaços
cria structured_transcription com start, end e text
preserva language
```

Saída:

```text
clean_transcript
structured_transcription
language
```

### extract_copy_structure

Extrai a estrutura da copy.

Exemplos:

```text
hook
problema
dor
promessa
mecanismo
prova
história
objeção
oferta
CTA
urgência
escassez
transição
educação
payoff
```

Saída:

```text
copy_structure
input_tokens
output_tokens
total_tokens
```

### extract_offer_elements

Extrai os elementos comerciais da oferta.

Exemplos:

```text
produto ou solução
público-alvo
problema central
desejo central
promessa principal
mecanismo único
benefícios
objeções
provas
bônus
urgência ou escassez
CTA
preço ou condições
```

Saída:

```text
offer_analysis
input_tokens
output_tokens
total_tokens
```

### analyse_persuasion

Analisa como a copy persuade o espectador.

Avalia:

```text
emoção dominante
padrão persuasivo
força do hook
clareza da promessa
força da prova
força da urgência
força do CTA
sinais persuasivos
fraquezas
resumo estratégico
```

Saída:

```text
persuasion_analysis
input_tokens
output_tokens
total_tokens
```

### build_copy_analysis

Monta o resultado final do workflow.

Esse node não usa LLM.

Saída:

```text
analysis: CopyAnalysisOutput
```

## O Que Falta No CopyAnalysisWorkflow

Salvar o relatório final em arquivo.

Possíveis formatos:

```text
json
md
html
pdf
```

Criar testes fake.

Validar:

```text
prepare_copy_input
schema dos outputs
nodes com LLM fake
contagem de tokens
workflow completo com transcrição fake
```

Melhorar controle de tamanho para vídeos longos.

Para transcrições grandes, será necessário resumir ou dividir análise em partes sem perder a visão global da copy.

## Próximo Workflow Recomendado

O próximo workflow recomendado é o `CopyAdaptationWorkflow`.

Responsabilidade:

```text
Transformar a análise da copy de referência em um novo roteiro para uma oferta própria.
```

Esse é o próximo passo mais importante porque o projeto já consegue:

```text
transcrever
corrigir
analisar a copy
```

Mas ainda não gera o ativo principal que alimenta voz, cenas, vídeos e montagem:

```text
roteiro final
```

## CopyAdaptationWorkflow

Fluxo sugerido:

```text
START
-> prepare_adaptation_input
-> build_copy_strategy
-> write_script_sections
-> validate_script
-> build_script_output
-> END
```

### prepare_adaptation_input

Recebe a análise da copy e o briefing da nova oferta.

Entradas prováveis:

```text
copy_analysis
offer_brief
target_audience
target_language
desired_duration
tone
platform
```

### build_copy_strategy

Define a estratégia da nova copy.

Exemplos:

```text
ângulo principal
promessa principal
mecanismo
objeções a atacar
provas necessárias
CTA
estrutura persuasiva
```

### write_script_sections

Escreve o roteiro dividido em seções.

Exemplos:

```text
hook
abertura
problema
agitação
mecanismo
prova
oferta
CTA
```

### validate_script

Valida se o roteiro está coerente com a oferta.

Checa:

```text
não copiar literalmente a referência
não inventar prova
não prometer além do briefing
manter idioma e tom
ter CTA claro
ter duração aproximada aceitável
```

### build_script_output

Monta o output final.

Saídas prováveis:

```text
script
sections
hooks
cta
estimated_duration
voice_ready_text
scene_planning_input
```

## Ordem Recomendada Dos Próximos Workflows

```text
1. CopyAdaptationWorkflow
2. ScenePlannerWorkflow
3. VoiceWorkflow
4. VisualGenerationWorkflow
5. AssemblyWorkflow
6. ExportWorkflow
```

## Como Os Workflows Devem Se Conectar

Não deve existir um state único gigante para todos os workflows.

Cada workflow deve ter seu próprio state.

Um workflow mestre deve orquestrar os subworkflows e passar apenas os dados necessários.

Exemplo futuro:

```text
MasterVSLWorkflow
-> TranscriberWorkflow
-> CopyAnalysisWorkflow
-> CopyAdaptationWorkflow
-> ScenePlannerWorkflow
-> VoiceWorkflow
-> VisualGenerationWorkflow
-> AssemblyWorkflow
-> ExportWorkflow
```

O master deve guardar apenas os resultados principais:

```text
transcription
copy_analysis
script
scenes
voice_assets
visual_assets
final_video_path
```

Regra final:

```text
subworkflow tem state próprio
master passa outputs entre workflows
context carrega dependências
state carrega dados serializáveis
```
