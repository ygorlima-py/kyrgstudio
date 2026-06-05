# Pipeline

A ideia é construir uma plataforma de automação de VSLs e criativos baseada em workflows inteligentes.

Em vez de tratar a criação de uma VSL como uma única tarefa gigante, o sistema dividiria o processo em várias etapas menores, organizadas e reutilizáveis. Cada etapa teria uma responsabilidade clara dentro do fluxo de produção.

O workflow principal seria responsável por coordenar toda a criação da VSL, desde a entrada do material até a exportação final. Dentro dele existiriam workflows menores, cada um cuidando de uma parte específica do processo.

Um workflow de ingestão receberia os materiais iniciais, como briefing da oferta, vídeo de referência, áudio, imagens, produto, público-alvo e idioma desejado. Ele organizaria esses dados e prepararia o projeto para as próximas etapas.

Um workflow de transcrição transformaria vídeos ou áudios de referência em texto. Esse texto serviria como base para análise da estrutura da copy, identificação de hooks, promessa, provas, objeções e chamadas para ação.

Um workflow de copywriting usaria IA para criar ou adaptar o roteiro da VSL. Ele não apenas escreveria texto, mas organizaria a mensagem de venda em uma estrutura persuasiva, separando abertura, desenvolvimento, quebra de objeções, prova, oferta e CTA.

Um workflow de planejamento de cenas dividiria o roteiro em blocos menores. Cada bloco teria duração estimada, texto de narração, intenção visual, prompt de vídeo, prompt de imagem e informações necessárias para sincronização. Essa divisão é importante porque vídeos longos gerados por IA costumam falhar mais; cenas curtas são mais controláveis, baratas e fáceis de regenerar.

Um workflow de voz geraria a narração com TTS ou clonagem autorizada de voz. Ele poderia criar o áudio por cena, calcular duração real, ajustar pausas e devolver arquivos prontos para montagem.

Um workflow de geração visual criaria os vídeos, imagens ou assets necessários para cada cena. Ele poderia escolher entre provedores diferentes, como Gemini, Runway, OpenRouter ou outros, dependendo do tipo de cena, custo, qualidade e disponibilidade.

Um workflow de montagem pegaria todos os elementos gerados e usaria o motor de edição do projeto para montar o vídeo final. Ele sincronizaria narração, cenas, trilha, legendas, cortes, transições, formatos e versões.

Um workflow de revisão verificaria problemas antes da exportação, como cenas ausentes, duração incompatível, áudio faltando, vídeo sem URI, falhas de geração, texto muito longo ou problemas de sincronização.

Um workflow de exportação geraria os arquivos finais: VSL completa, cortes curtos, variações de hook, versões verticais, horizontais e outros formatos úteis para campanhas.

LangGraph entraria como a camada de orquestração desses workflows. Ele permitiria controlar estado, retentativas, execução longa, aprovação humana e retomada do processo caso uma etapa falhe. O grafo principal saberia qual etapa executar, quando pausar para aprovação e quando repetir uma cena ou regenerar um asset.

A arquitetura ideal teria um estado central do projeto, mas organizado por partes. Esse estado guardaria informações da oferta, transcrição, roteiro, cenas, vozes, vídeos, montagem, revisão, exportações e erros. Cada workflow leria apenas a parte do estado que precisa e devolveria sua contribuição para o próximo estágio.

Nem todo workflow precisa ser um agente de IA. As etapas criativas, como copywriting e planejamento de cenas, podem usar agentes. Já etapas técnicas, como renderização, conversão, concatenação, legendagem e exportação, devem ser processos determinísticos. Isso deixa o sistema mais previsível, mais barato e mais fácil de debugar.

O valor do produto está justamente nessa orquestração. O usuário não quer abrir dez ferramentas diferentes, copiar texto, baixar áudio, subir vídeo, cortar cenas e montar tudo manualmente. Ele quer fornecer uma oferta ou referência e receber uma VSL pronta, com possibilidade de revisar pontos importantes no caminho.

O resultado final seria uma fábrica automatizada de VSLs: um sistema onde cada parte da produção é dividida em workflows pequenos, confiáveis e reutilizáveis, enquanto um workflow principal coordena tudo de forma inteligente até gerar os criativos finais.

2:55 PM


## GRAPH

```
VSLMasterGraph
-> IngestGraph
-> TranscriptionGraph
-> CopywritingGraph
-> VoiceGraph
-> ScenePlanningGraph
-> VideoGenerationGraph
-> AssemblyGraph
-> ReviewGraph
-> ExportGraph
```

### IngestGraph
 Recebe vídeo, áudio, briefing, produto, oferta, arquivos.

### TranscriptionGraph
Usa seu módulo transcribers.

### CopywritingGraph
Agente de copy. Esse sim pensa: hook, promessa, objeções, CTA, estrutura VSL.

### ScenePlanningGraph
Transforma roteiro em cenas curtas de 8-15 segundos.

### VoiceGraph
Usa generate.voices para narração, clonagem ou TTS.

### VideoGenerationGraph
Usa Gemini, Runway, OpenRouter etc. Decide provider, divide cenas, faz retry.

### AssemblyGraph
Usa editor.video e editor.audio. Esse é mais determinístico, não precisa ser agente.

### QAReviewGraph
Checa duração, cenas vazias, áudio, legenda, sincronização, erros.

### ExportGraph
Gera versões: VSL completa, criativos curtos, cortes, formatos.


## State

```
class VSLState(TypedDict):
    project: ProjectState
    ingest: IngestState
    transcription: TranscriptionState
    copy: CopyState
    scenes: ScenesState
    voice: VoiceState
    video: VideoState
    assembly: AssemblyState
    review: ReviewState
    export: ExportState
    errors: list[PipelineError]
```

### Exemplos
```
class SceneState(TypedDict):
    id: str
    index: int
    script_text: str
    duration_target: float
    visual_prompt: str
    voice_asset_id: str | None
    video_asset_id: str | None


class ScenesState(TypedDict):
    items: list[SceneState]

```

### TranscriberState

```
class TranscriberState(TypedDict):
    source_path: str
    source_type: Literal["audio", "video"]
    provider: type[TranscriberBase]
    model: str
    language: str | None
    temperature: float
    audio_path: str | None
    result: TranscriptionResult | None
    error: str | None

source_path = arquivo original recebido
source_type = audio ou video
provider = quem vai transcrever
model = modelo usado
language = idioma opcional
temperature = temperatura
audio_path = áudio final usado para transcrição
result = TranscriptionResult normalizado
error = erro simples do workflow

```