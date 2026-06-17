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

# CopyAdaptationWorkflow

## Objetivo

Transformar a análise de uma VSL de referência em um roteiro profissional adaptado para uma nova oferta, mantendo os padrões persuasivos que fazem a referência converter enquanto substitui produto, público, provas e mecanismo.

---

## Pré-requisitos

Este workflow depende de dois outputs já existentes no projeto:

- `CopyAnalysisOutput` — gerado pelo `CopyAnalysisWorkflow`
- `UserProfileOutput` — gerado pelo `UserProfileWorkflow`

Ambos devem estar disponíveis no estado do grafo antes de iniciar este workflow.

---

## Fluxo atual

```
START
-> prepare_adaptation_input
-> build_copy_strategy
-> write_script_sections
-> review_section_flow
-> validate_script
-> build_script_output
-> END
```

## Fluxo planejado com retry

O retry planejado não deve simplesmente repetir um node sem contexto.

Quando `review_section_flow` reprovar o fluxo das seções, o grafo deve voltar para `write_script_sections` levando feedback no state.

Fluxo esperado:

```text
START
-> prepare_adaptation_input
-> build_copy_strategy
-> write_script_sections
-> review_section_flow
-> route_flow_review
   -> validate_script          # aprovado
   -> write_script_sections    # reprovado com retry disponível

validate_script
-> build_script_output
-> END
```

O retorno para `write_script_sections` deve carregar:

```text
previous_sections  # seções geradas na tentativa anterior
flow_issues        # problemas encontrados pelo review_section_flow
retry_count        # quantidade de tentativas já realizadas
```

Esse retry é uma reescrita orientada por feedback, não uma nova geração cega.

O router planejado deve decidir:

```text
se flow_approved == true:
    seguir para validate_script

se flow_approved == false e retry_count ainda está dentro do limite:
    voltar para write_script_sections com flow_issues

se flow_approved == false e retry_count excedeu o limite:
    seguir para validate_script ou retornar erro controlado
```

---

## Nós

### `prepare_adaptation_input`

**Responsabilidade:** Consolidar a análise da referência e o perfil da oferta num contexto único e estruturado que alimenta todos os nós seguintes.

**Entradas:**
- `copy_analysis: CopyAnalysisOutput` — análise completa da VSL de referência
- `user_profile: UserProfileOutput` — produto, público, dores, mecanismo, provas disponíveis, tom, restrições

**O que deve fazer:**
- Mapear cada `CopySection` da referência para o contexto da nova oferta
- Identificar quais seções têm equivalente direto e quais precisam ser criadas do zero
- Extrair os scores fracos da `PersuasionAnalysisOutput` (urgência, objeções, prova) para sinalizar gaps a corrigir
- Normalizar o `target_language` — se a referência está em espanhol e a nova oferta é em português, registrar isso explicitamente

**Campos de saída do estado:**
```
mapped_sections       # seções da referência mapeadas para a nova oferta
sections_to_create    # seções que precisam ser criadas do zero
gaps_to_fix           # dimensões com score baixo na análise original
target_language       # idioma do roteiro final
platform              # onde a VSL vai rodar (YouTube, página de vendas, etc.)
desired_duration      # duração estimada em minutos
```

---

### `build_copy_strategy`

**Responsabilidade:** Definir a estratégia persuasiva da nova copy antes de escrever qualquer linha de roteiro.

**O que deve fazer:**
- Escolher o ângulo principal baseado na dor mais forte do `UserProfileOutput`
- Definir o nível de consciência do público (`unaware`, `problem aware`, `solution aware`, `product aware`) e adaptar a estratégia de entrada
- Formular a promessa principal em uma frase clara e verificável contra o briefing
- Selecionar o padrão persuasivo (`PAS`, `AIDA`, `BAB`, `Hybrid`) mais adequado ao produto e plataforma
- Listar as objeções prioritárias a atacar, em ordem de impacto
- Definir que tipo de prova será usada em cada seção (depoimento, dado, demonstração, história)
- Especificar o mecanismo único — o que torna a solução diferente e crível

**Campos de saída do estado:**
```
main_angle            # ângulo principal da copy
awareness_level       # nível de consciência do público
main_promise          # promessa central em uma frase
persuasion_pattern    # padrão estrutural escolhido
objections_to_address # lista ordenada de objeções
proof_plan            # tipo de prova por seção
unique_mechanism      # mecanismo único da oferta
```

> **Atenção:** Este nó não escreve copy. Define estratégia. O modelo deve retornar apenas decisões estratégicas, sem rascunhos de texto.

---

### `write_script_sections`

**Responsabilidade:** Escrever cada seção do roteiro individualmente, usando a estratégia definida e os padrões extraídos da referência.

Este node não recebe mais o `CopyAnalysisOutput` completo.

O prompt desta etapa foi ajustado para usar apenas o contexto refinado gerado pelos nodes anteriores.

Entradas usadas pela action:

```
user_profile          # oferta, público, promessa, provas, CTA, tom e restrições
mapped_sections       # seções da referência já mapeadas
sections_to_create    # seções que devem ser criadas do zero
gaps_to_fix           # fraquezas estratégicas que devem ser corrigidas
target_language       # idioma final do roteiro
platform              # canal de uso do criativo/VSL
desired_duration      # duração desejada
main_angle            # ângulo escolhido pela estratégia
awareness_level       # nível de consciência do público
main_promise          # promessa central permitida
persuasion_pattern    # estrutura persuasiva escolhida
objections_to_address # objeções prioritárias
proof_plan            # plano de provas por seção
unique_mechanism      # mecanismo único
previous_sections     # seções anteriores, usado em retry
flow_issues           # feedback do review_section_flow, usado em retry
retry_count           # tentativa atual de reescrita
```

Motivo da mudança:

```
copy_analysis já foi usado por prepare_adaptation_input e build_copy_strategy.
write_script_sections deve escrever com o contexto refinado, não com a análise bruta inteira.
Isso reduz tokens, evita redundância e diminui risco de misturar a oferta da referência com a oferta do usuário.
```

**O que deve fazer:**
- Escrever cada seção em sequência usando os tipos canônicos: `hook`, `problem`, `pain`, `agitation`, `education`, `mechanism`, `proof`, `offer`, `urgency`, `cta`
- Para cada seção: manter o padrão persuasivo identificado na referência, substituir todos os elementos contextuais (produto, público, dor, prova, mecanismo) pelos dados do `UserProfileOutput`
- Respeitar `target_language`, `tone` e `platform` do estado
- Não inventar provas, depoimentos ou dados que não estejam no `UserProfileOutput`
- Marcar `missing_proof = true` quando a estratégia exige prova mas o briefing não forneceu
- Em retry, usar `previous_sections` como versão base e `flow_issues` como instruções obrigatórias de correção

**Campos de saída do estado:**
```
sections: list[ScriptSection]
  - order                         # ordem da seção no roteiro
  - section_type                  # hook, problem, mechanism, cta, etc.
  - text                          # texto da seção
  - purpose                       # função persuasiva da seção
  - adaptation_mode               # adapted_from_reference ou created_from_scratch
  - source_reference_section_type # seção da referência usada como base, se existir
  - proof_used                    # prova utilizada ou null
  - missing_proof                 # true se há gap de prova
  - transition_hint               # observação para conexão com a próxima seção
  - word_count                    # contagem de palavras
missing_proofs                    # lista de provas faltantes
adaptation_notes                  # notas sobre adaptação e retry
word_count                        # total estimado de palavras
```

---

### `review_section_flow`

**Responsabilidade:** Verificar coerência e continuidade entre as seções antes da validação final.

**O que deve fazer:**
- Checar se a promessa do `hook` é entregue pelo `mecanismo`
- Verificar se cada seção faz transição natural para a próxima
- Identificar contradições entre seções (ex: hook promete resultado em 7 dias, oferta menciona 30 dias)
- Verificar se o nível emocional sobe progressivamente até o CTA
- Reescrever apenas as transições problemáticas — não reescreve seções inteiras

**Campos de saída do estado:**
```
flow_issues           # lista de problemas de fluxo encontrados
sections_revised      # seções corrigidas (apenas as alteradas)
flow_approved         # bool — true se não há problemas críticos
retry_count           # incrementado quando o fluxo reprovar e voltar para escrita
```

---

### `validate_script`

**Responsabilidade:** Checagem de segurança antes de montar o output final.

**Regras de validação — todas obrigatórias:**

| Regra | Descrição |
|-------|-----------|
| `no_literal_copy` | Nenhuma frase da referência foi copiada literalmente |
| `no_invented_proof` | Nenhuma prova, dado ou depoimento foi inventado |
| `no_overpromise` | A promessa não excede o que o briefing autoriza |
| `language_consistent` | Todo o roteiro está no idioma definido |
| `tone_consistent` | Tom e voz estão alinhados com o `UserProfileOutput` |
| `cta_present` | Há pelo menos um CTA claro e direto |
| `duration_acceptable` | Duração estimada está dentro do intervalo solicitado |
| `no_missing_proof_critical` | Seções marcadas com `[PROVA NECESSÁRIA]` foram sinalizadas ao usuário |

**Comportamento esperado:**
- Se alguma regra crítica falhar (`no_invented_proof`, `no_overpromise`, `no_literal_copy`): interromper e retornar erro com descrição do problema
- Se regras secundárias falharem: registrar warnings e continuar
- Não tentar corrigir automaticamente — reportar para o usuário decidir

**Campos de saída do estado:**
```
validation_passed     # bool
validation_errors     # list[str] — erros críticos
validation_warnings   # list[str] — avisos não bloqueantes
```

---

### `build_script_output`

**Responsabilidade:** Montar o output final estruturado e pronto para consumo pelos workflows de produção (voz, cenas, montagem).

**O que deve fazer:**
- Consolidar as seções aprovadas em um roteiro contínuo
- Gerar `voice_ready_text` — texto limpo, sem markdown, com pontuação para pausas naturais, pronto para TTS
- Gerar `scene_planning_input` — roteiro segmentado com sugestão de cena por bloco de texto
- Calcular duração estimada (referência: 130 palavras por minuto para narração pausada)
- Produzir `adaptation_notes` explicando o que foi mantido da referência e o que foi mudado

**Campos do output final (`AdaptedScriptOutput`):**
```
script                # roteiro completo em markdown
sections              # list[ScriptSection] com metadados
hooks                 # list[str] — variações do hook para teste A/B
cta                   # texto final do CTA
estimated_duration    # duração estimada em minutos
word_count            # total de palavras
voice_ready_text      # texto limpo para TTS, sem formatação
scene_planning_input  # roteiro segmentado por cena
adaptation_notes      # o que foi mantido, o que foi mudado e por quê
validation_warnings   # warnings herdados do validate_script
missing_proofs        # seções que precisam de prova real antes de usar
```

---

## Regras gerais para implementação

1. **Modelo:** Usar o modelo mais capaz disponível neste nó — o output é o ativo principal que o usuário vai usar em produção.
2. **Temperatura:** Manter baixa nos nós de estratégia e validação (`0.3`). Permitir criatividade nos nós de escrita (`0.7`).
3. **Contexto:** Não passar `CopyAnalysisOutput` completo em todos os nós. Usar `copy_analysis` completo apenas em etapas que realmente analisam ou definem estratégia. Em escrita, usar contexto refinado (`mapped_sections`, `sections_to_create`, `gaps_to_fix`, estratégia e `user_profile`).
4. **Idioma:** Nunca assumir idioma. Sempre ler `target_language` do estado.
5. **Prova:** Nunca inventar. Se não há prova disponível no briefing, marcar e sinalizar — jamais criar.
6. **Output do usuário:** O único arquivo que o usuário deve ver é o `AdaptedScriptOutput`. Todos os estados intermediários são internos ao grafo.
