# Workflows

Este pacote concentra os fluxos de trabalho inteligentes do projeto.

A ideia principal é não tratar a criação de uma VSL ou criativo como uma tarefa gigante. O projeto deve ser dividido em workflows menores, cada um com uma responsabilidade clara, reutilizável e fácil de testar.

Um workflow cuida de uma etapa do processo. Depois, um workflow maior poderá orquestrar todos eles.

## Ideia Geral

O produto final desejado é uma plataforma capaz de automatizar a criação de VSLs, criativos e vídeos de marketing com IA.

O fluxo completo, no futuro, deve ser algo parecido com:

```text
material de entrada
-> transcrição
-> análise da copy
-> reescrita/adaptação
-> planejamento de cenas
-> geração de voz
-> geração visual
-> montagem
-> revisão
-> exportação
```

Nem todas as etapas precisam ser agentes.

Algumas etapas usam IA com structured output, outras usam agentes ReAct com tools, e outras são processos determinísticos, como conversão de áudio, extração com FFmpeg e montagem final.

## O Que Ja Foi Feito

O primeiro workflow criado foi o `TranscriberWorkflow`.

Ele já consegue receber áudio ou vídeo, preparar o áudio, transcrever, extrair contexto semântico, avaliar a qualidade da transcrição com um agente e decidir se a transcrição deve ser aceita, corrigida ou enviada para revisão humana.

Fluxo atual:

```text
START
-> extract_audio ou prepare_audio
-> audio_text_converter
-> extract_hybrid_context
-> analyse_agent
   -> model
   -> tools
   -> model
-> END
```

Quando a entrada é vídeo, o workflow usa `extract_audio`.

Quando a entrada é áudio, o workflow usa `prepare_audio`.

Depois disso, ambos os caminhos chegam em `audio_text_converter`.

## TranscriberWorkflow

Responsabilidade:

```text
Transformar áudio ou vídeo em uma transcrição final confiável.
```

Entrada principal:

```text
source_path
source_type
transcriber
model_name
```

`source_path` é o arquivo original recebido.

`source_type` indica se a entrada é `audio` ou `video`.

`transcriber` é a classe responsável por transcrever.

`model_name` é o modelo usado pelo transcriber.

O `audio_path` ainda existe como caminho interno do áudio preparado, mas a decisão correta para o futuro é ele ser gerado pelo próprio workflow, para não confundir o usuário da API.

## Nodes Do TranscriberWorkflow

### primary_router

Decide o caminho inicial.

Se for áudio:

```text
prepare_audio
```

Se for vídeo:

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

Normaliza/converte um arquivo de áudio para o formato esperado pela transcrição.

Esse node existe porque mesmo quando o usuário envia áudio, o arquivo pode vir em formato, codec, sample rate ou canais diferentes.

### audio_text_converter

Executa a transcrição.

Ele instancia o transcriber informado no state e chama:

```text
transcribe()
```

Saída:

```text
result: TranscriptionResult
```

### extract_hybrid_context

Usa LLM com structured output para analisar a transcrição e extrair contexto.

Esse contexto ajuda a identificar:

```text
idioma
assunto principal
tipo de conteúdo
termos importantes
nomes próprios
termos técnicos
possíveis correções
termos incertos
regras de correção
```

Saída:

```text
domain_context: DomainContextOutput
messages: entrada para o agente de qualidade
```

Esse node também cria a mensagem que será lida pelo agente ReAct.

### analyse_agent

Esse node é um subgrafo de agente criado com `create_agent`.

Ele recebe:

```text
messages
result
domain_context
```

O agente escolhe exatamente uma tool:

```text
accept_transcription_tool
correct_transcription_tool
request_human_review_tool
```

## Tools Do Agente

### accept_transcription_tool

Usada quando a transcrição está boa.

Ela define:

```text
final_result = result
status = accepted
```

### correct_transcription_tool

Usada quando existem erros corrigíveis com segurança.

Ela chama uma action de IA:

```text
CorrectTranscription
```

A LLM não deve reconstruir o `TranscriptionResult` inteiro.

Ela deve devolver apenas um patch de correção.

Depois a tool aplica esse patch no `TranscriptionResult` original, preservando:

```text
timestamps
words
probabilities
audio_path
provider
model
raw_response
```

Isso evita JSON gigante e reduz erro.

### request_human_review_tool

Usada quando a transcrição está ambígua demais para corrigir automaticamente.

Ela define:

```text
status = needs_human_review
human_review_reason = motivo informado pelo agente
```

## Decisoes Arquiteturais

O `TranscriberState` herda de `AgentState` porque o grafo principal contém um agente ReAct como subgrafo.

Isso faz sentido neste workflow, porque o agente faz parte real do grafo.

Regra:

```text
AgentState pode aparecer em workflows agentic.
AgentState nao deve vazar para transcribers, editor, generate ou schemas de dominio.
```

O `runtime.context` é usado para dependências de execução, como LLMs.

Exemplo:

```text
correction_llm
extract_context_llm
```

O state carrega dados do processo.

O context carrega dependências da execução.

## O Que Foi Validado

Teste com áudio:

```text
áudio -> prepare_audio -> transcrição -> contexto -> agente -> accepted
```

O agente aceitou a transcrição quando não encontrou correções relevantes.

Teste com vídeo:

```text
vídeo -> extract_audio -> transcrição -> contexto -> agente -> corrected
```

O contexto detectou a correção:

```text
la renda -> a renda
```

O agente chamou:

```text
correct_transcription_tool
```

E o workflow terminou com:

```text
status = corrected
```

## O Que Ainda Falta No TranscriberWorkflow

Gerar `audio_path` automaticamente.

Hoje o caminho ainda pode precisar ser passado manualmente em testes. O ideal é o workflow criar um diretório interno por execução/projeto e gerar o caminho do áudio preparado.

Reduzir o payload enviado ao agente.

Hoje o agente ainda recebe muitos dados da transcrição, incluindo segmentos e palavras. Funciona, mas pode ficar caro em vídeos maiores.

Salvar outputs em arquivos.

Exemplos:

```text
transcription.json
domain_context.json
final_transcription.json
```

Criar testes fake.

Testes fake devem validar:

```text
roteamento audio/video
accept tool
correct tool
human review tool
aplicação de patch
```

Criar suporte para transcrição por chunks.

Isso deve ficar para depois. Para vídeos longos, o ideal será:

```text
extract_audio
-> inspect_audio_duration
-> split_audio_chunks
-> transcribe_chunks
-> merge_transcriptions
```

Essa melhoria não deve mudar os transcribers. Ela deve ser uma camada acima, no workflow.

## Proximo Workflow

O próximo workflow recomendado é o `CopyAnalysisWorkflow`.

Ele deve transformar uma transcrição final em inteligência de venda.

Fluxo sugerido:

```text
START
-> prepare_copy_input
-> extract_copy_structure
-> extract_offer_elements
-> analyse_persuasion
-> build_copy_analysis
-> END
```

Esse workflow deve ser linear no começo.

Ele não precisa de agente ReAct agora, porque a tarefa principal é extração e análise estruturada, não decisão com tools.

## CopyAnalysisWorkflow

Responsabilidade:

```text
Ler a transcrição final e entender a estrutura persuasiva da copy.
```

### prepare_copy_input

Prepara o texto para análise.

Faz:

```text
valida se existe transcrição final
extrai texto limpo
remove metadados desnecessários
normaliza espaços
```

### extract_copy_structure

Extrai a estrutura da copy.

Exemplos:

```text
hook
abertura
dor
promessa
mecanismo
prova
objeções
oferta
CTA
urgência
escassez
```

### extract_offer_elements

Extrai os elementos comerciais.

Exemplos:

```text
produto
público-alvo
problema principal
desejo principal
transformação prometida
benefícios
diferenciais
bônus
garantia
preço
condição especial
```

### analyse_persuasion

Avalia a força persuasiva da copy.

Analisa:

```text
força do hook
clareza da promessa
credibilidade
provas usadas
objeções cobertas
clareza do CTA
riscos de exagero
lacunas
oportunidades de melhoria
```

### build_copy_analysis

Junta os resultados anteriores em um output final.

Esse node não precisa de LLM. Ele apenas monta o objeto final.

## Como Os Workflows Se Conectam No Futuro

Não deve existir um state gigante compartilhado por todos os workflows.

Cada workflow deve ter seu próprio state.

Um workflow mestre deve orquestrar os subworkflows e passar apenas os dados necessários.

Exemplo:

```text
MasterVSLWorkflow
-> TranscriberWorkflow
-> CopyAnalysisWorkflow
-> CopyRewriteWorkflow
-> ScenePlannerWorkflow
-> VoiceWorkflow
-> VisualGenerationWorkflow
-> AssemblyWorkflow
-> ReviewWorkflow
-> ExportWorkflow
```

O master guarda os resultados principais:

```text
transcription
copy_analysis
script
scenes
voice_assets
visual_assets
final_video_path
```

Regra:

```text
subworkflow tem state proprio
master passa outputs entre workflows
nao criar um state unico gigante para tudo
```

