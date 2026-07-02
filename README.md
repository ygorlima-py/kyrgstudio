# kyrgstudio

kyrgstudio is a Python 3.12 library for AI-assisted media and marketing-copy
workflows. Its current center of gravity is the LangGraph workflow layer that
turns source media or transcripts into structured copy analysis and an adapted
script. The repository also includes reusable FFmpeg editor operations,
generation adapters, LLM adapters, and transcription providers that support
those workflows.

The package is exposed under the `kyrg` import namespace.

## Current Status

kyrgstudio is an active MVP/library project. It has working internal building
blocks and workflow graphs, but it is not yet a packaged product runtime.

Implemented today:

- LangGraph workflows for transcription, copy analysis, and copy adaptation.
- LLM adapters for OpenAI, Google Gemini, and LangChain chat models.
- Structured-output retry and latest-call token usage tracking in the shared
  LLM contract.
- Local transcription with Faster Whisper.
- Remote transcription adapters for OpenRouter, OpenAI, and ElevenLabs.
- FFmpeg and ffprobe command builders for audio and video editing operations.
- Generation adapters for images, voices, and videos.
- Memory, SQLite, and Postgres checkpointer abstractions for workflows.
- Unit, integration, and opt-in evaluation tests around the LLM and workflow
  layers.

Not implemented as stable product surfaces yet:

- No stable CLI.
- No web API.
- No queue or worker runtime.
- No frontend.
- No stable end-user application entry point.

`src/kyrg/workflows/main.py` is a hardcoded demo script, not a general-purpose
runtime.

## Architecture

kyrgstudio is organized around small, explicit contracts:

- `workflows`: LangGraph orchestration for transcription, copy analysis, and
  copy adaptation.
- `llms`: provider-neutral LLM interface plus OpenAI, Gemini, and LangChain
  adapters.
- `transcribers`: local and remote transcription providers that return a common
  `TranscriptionResult` schema.
- `editor`: FFmpeg and ffprobe command builders for audio/video operations.
- `generate`: provider adapters for image, voice, and video generation.
- `adapters`: shared API adapter lifecycle utilities.

Provider-specific behavior stays inside adapters. Workflow state is kept
serializable where possible, while non-serializable dependencies such as LLMs,
transcriber classes, SDK clients, and provider configuration are injected
through workflow context objects.

## Workflows

The current demo pipeline is:

```text
TranscriberWorkflow
-> CopyAnalysisWorkflow
-> CopyAdaptationWorkflow
```

### WorkflowBase

`WorkflowBase` centralizes the shared workflow runtime behavior:

- Builds a LangGraph `StateGraph` from `STATE_SCHEMA` and `CONTEXT_SCHEMA`.
- Stores `initial_state`, runtime `context`, optional `checkpointer`, and
  optional `thread_id`.
- Provides `start()` for synchronous execution.
- Provides `astart()` for asynchronous execution.
- Provides `draw_workflow()` to render a workflow graph PNG.

Important side effects:

- `start()` is decorated with `save_output_json` and writes a
  `<WorkflowClass>.json` artifact.
- `draw_workflow()` writes a `<WorkflowClass>.png` graph image.

`RunnableNode` is used to adapt workflow nodes that have both synchronous and
asynchronous implementations.

### Checkpointers

Workflow checkpointers live in `src/kyrg/workflows/checkpointers.py`:

- `MemoryCheckpointer`
- `SQLiteCheckpointer`
- `PostgresCheckpointer`

A `thread_id` allows LangGraph to resume state with a configured checkpointer.
State should contain serializable workflow data. Context should contain runtime
dependencies that should not be checkpointed.

SQLite checkpointing is included through `langgraph-checkpoint-sqlite`.
Postgres checkpointing requires the optional `langgraph-checkpoint-postgres`
package.

### Token Accounting

LLM adapters expose `token_usage()` as latest-call usage only:

```python
{"input_tokens": 100, "output_tokens": 40, "total_tokens": 140}
```

Workflow states use additive reducers for `input_tokens`, `output_tokens`, and
`total_tokens`, so each node contributes its latest LLM usage to the final
workflow totals.

### TranscriberWorkflow

`TranscriberWorkflow` converts an audio or video source into a normalized
transcription result.

Graph shape:

```text
START
-> prepare_audio or extract_audio
-> audio_text_converter
-> measure_audio
-> secondary_router
-> extract_hybrid_context -> correction_transcriber -> END
   or END
```

Behavior:

- `source_type="audio"` routes to `prepare_audio`.
- Other source types route to `extract_audio`.
- `audio_text_converter` instantiates the configured transcriber from
  `TranscriptorConfig`.
- `measure_audio` uses ffprobe-backed editor operations to determine duration.
- Correction runs only when `audio_duration_in_seconds <= 180` and
  `need_correction` is truthy.
- If correction does not run, the workflow ends with `result` and does not set
  `status="accepted"` or `final_result`.

### CopyAnalysisWorkflow

`CopyAnalysisWorkflow` turns a transcription into a structured strategic copy
analysis.

Graph shape:

```text
prepare_copy_input
-> extract_copy_structure
-> extract_offer_elements
-> analyse_persuasion
-> build_copy_analysis
```

The final `analysis` combines:

- Copy structure and section gaps.
- Offer elements such as audience, problem, desire, promise, proof, objections,
  CTA, and commercial terms.
- Persuasion signals, weaknesses, and pattern diagnosis.

### CopyAdaptationWorkflow

`CopyAdaptationWorkflow` adapts a reference copy analysis to a new offer profile
and returns an assembled script.

Graph shape:

```text
prepare_adaptation_input
-> build_copy_strategy
-> write_script_sections
-> review_section_flow
-> correct_section retry path
-> validate_script
-> correct_script retry path
-> build_script_output
```

Behavior:

- Uses `CopyAnalysisOutput` as the reference-copy analysis.
- Uses `UserProfileOutput` as the source of truth for the new offer, audience,
  claims, proof, CTA, tone, language, platform, duration, and restrictions.
- Reviews section flow before validation.
- Applies bounded retries through `correct_section` and `correct_script` using
  the `max_retry` value from `CopyAdaptationWorkflowContext`.
- Adds deterministic word count, timing, pause, and duration-fit metadata before
  final output assembly.

## LLM Layer

The LLM contract lives in `src/kyrg/llms`.

Public adapters:

```python
from kyrg.llms import GoogleLLM, LangChainLLM, LLMBase, OpenAILLM
```

`LLMBase` provides:

- `invoke()` / `ainvoke()` for plain text generation.
- `structured()` / `astructured()` for Pydantic structured output.
- Retry prompts for validation or parsing failures during structured output.
- `token_usage()` for latest-call input/output/total token counts.

`OpenAILLM` uses the OpenAI Responses API. OpenRouter can be used by subclassing
`OpenAILLM` and overriding `BASE_URL`, as shown in the workflow demo.

## Transcription

Public transcription adapters:

```python
from kyrg.transcribers import (
    ElevenLabsTranscriber,
    OpenAITranscriber,
    OpenRouterTranscriber,
    TranscriberWhisperLocal,
    TranscriptionResult,
)
```

Available providers:

- `TranscriberWhisperLocal`: local Faster Whisper transcription.
- `OpenRouterTranscriber`: remote OpenRouter transcription.
- `OpenAITranscriber`: remote OpenAI transcription.
- `ElevenLabsTranscriber`: remote ElevenLabs transcription.

All providers return a normalized `TranscriptionResult` with transcription text,
optional segments, optional word-level timing, provider metadata, and source
metadata.

## Editor Operations

Editor operations are command builders around FFmpeg and ffprobe. They build a
command list from a typed context and execute it through `CommandRunner`.

```python
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner
from kyrg.editor.video import TrimVideo

operation = TrimVideo(
    context=MediaContext(input_path="source.mp4", output_path="clip.mp4"),
    runner=CommandRunner(),
    start_time=10,
    duration=30,
)

operation.execute()
```

Audio operations live in `src/kyrg/editor/audio` and include conversion,
cleanup, dynamics, filters, timing, mixing, analysis, and effects.

Video operations live in `src/kyrg/editor/video` and include streams, cutting,
conversion, geometry, timing, color, overlays, subtitles, composition, frames,
metadata, and stabilization.

## Generation Adapters

Generation adapters follow the shared adapter lifecycle:

```text
_request() -> _normalize_response(raw_result)
```

Image generation:

```python
from kyrg.generate.images import GeminiImageGenerator, ImageGeneratorInput

image_input = ImageGeneratorInput(
    model="imagen-4.0-generate-001",
    prompt="A red sports car parked under studio lights.",
)

result = GeminiImageGenerator(
    api_key="...",
    image_input=image_input,
).generate()
```

Voice generation:

```python
from kyrg.generate.voices import OpenAIVoiceGenerator, TextToSpeechInput

tts_input = TextToSpeechInput(
    model="gpt-4o-mini-tts",
    text="Welcome to kyrgstudio.",
    voice="alloy",
    output_path="voice.mp3",
)

result = OpenAIVoiceGenerator(
    api_key="...",
    tts_input=tts_input,
).run()
```

Video generation:

```python
from kyrg.generate.videos import GeminiVideoGenerator, VideoGenerateInput

video_input = VideoGenerateInput(
    model="veo-3.1-generate-preview",
    prompt="A cinematic shot of a mountain valley at sunrise.",
)

result = GeminiVideoGenerator(
    api_key="...",
    video_input=video_input,
).generate()
```

Provider coverage:

- Images: OpenAI, OpenRouter, Gemini.
- Voices: OpenAI, OpenRouter, ElevenLabs.
- Videos: Gemini, OpenRouter, Runway.

Images normalize to bytes. Voices that generate audio write to local paths.
Videos normalize to remote video references and do not download assets
automatically.

## Project Layout

```text
src/kyrg/
  adapters/                  Shared adapter base classes.
  editor/                    FFmpeg/ffprobe audio and video command builders.
  generate/                  Image, voice, and video generation adapters.
  llms/                      Provider-neutral LLM interface and adapters.
  transcribers/              Local and remote transcription providers.
  workflows/                 LangGraph workflow infrastructure and graphs.
    checkpointers.py         Memory, SQLite, and Postgres checkpointers.
    main.py                  Hardcoded demo pipeline.
    transcriber/             TranscriberWorkflow.
    copyanalysis/            CopyAnalysisWorkflow.
    copyadaptation/          CopyAdaptationWorkflow.

tests/
  unit/llms/                 LLM adapter and retry behavior tests.
  unit/workflows/            Workflow unit tests.
  integration/workflows/     Deterministic workflow integration tests.
  evals/                     Opt-in live quality evaluations.
```

Additional package notes:

- `src/kyrg/editor/audio/README.md`
- `src/kyrg/editor/video/README.md`
- `src/kyrg/transcribers/README.md`
- `src/kyrg/workflows/README.md`

## Requirements

- Python `>=3.12`
- FFmpeg and ffprobe available in the system path for editor and workflow media
  operations
- Provider credentials for any remote API you call
- Optional Postgres checkpointing dependency when using `PostgresCheckpointer`

Core Python dependencies are defined in `pyproject.toml` and currently include:

- `elevenlabs`
- `faster-whisper`
- `google-genai`
- `langchain`
- `langchain-openai`
- `langgraph`
- `langgraph-checkpoint-sqlite`
- `loguru`
- `openai`
- `pydantic`
- `python-dotenv`
- `requests`
- `runwayml`
- `weasyprint`

Known dependency note: some demo or evolving code paths import packages such as
`rich` or `httpx` that may not be pinned in `pyproject.toml` yet.

## Installation

Using `uv`:

```bash
uv sync
```

Or with `pip` in an active virtual environment:

```bash
pip install -e .
```

## Environment Variables

Set only the provider keys required for the adapters or workflows you run:

```bash
OPENAI_API_KEY=...
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...
ELEVENLABS_API_KEY=...
RUNWAY_API_KEY=...
```

The workflow demo in `src/kyrg/workflows/main.py` requires
`OPENROUTER_API_KEY`.

Live evaluation tests require additional opt-in variables, depending on the eval
suite:

```bash
KYRG_RUN_COPYADAPTATION_EVALS=1
KYRG_COPYADAPTATION_EVAL_MODEL=...
```

Store secrets in a local `.env` file or shell environment and keep them out of
source control.

## Basic Workflow Usage

The example below mirrors the current workflow composition while keeping paths
and profile content minimal. Real runs require valid media files, FFmpeg/ffprobe,
model credentials, and a complete `UserProfileOutput`.

```python
from kyrg.llms.openai_llm import OpenAILLM
from kyrg.transcribers.local_model import TranscriberWhisperLocal
from kyrg.workflows.checkpointers import SQLiteCheckpointer
from kyrg.workflows.copyadaptation.schemas import (
    CopyAdaptationWorkflowContext,
    UserProfileOutput,
)
from kyrg.workflows.copyadaptation.workflow import CopyAdaptationWorkflow
from kyrg.workflows.copyanalysis.schemas import CopyAnalysisWorkflowContext
from kyrg.workflows.copyanalysis.workflow import CopyAnalysisWorkflow
from kyrg.workflows.transcriber.schemas import (
    TranscriberWorkflowContext,
    TranscriptorConfig,
)
from kyrg.workflows.transcriber.workflow import TranscriberWorkflow


class OpenRouterLLM(OpenAILLM):
    BASE_URL = "https://openrouter.ai/api/v1"


llm = OpenRouterLLM(
    api_key="...",
    model="deepseek/deepseek-v4-flash",
    temperature=0.3,
)

checkpointer = SQLiteCheckpointer("src/data/checkpoints/kyrg_workflows.sqlite")

transcriber_workflow = TranscriberWorkflow(
    initial_state={
        "source_path": "src/data/input/video_teste.mp4",
        "source_type": "video",
        "audio_path": "src/data/output/audio_extraido.wav",
        "model_name": "small",
        "language": "es",
        "need_correction": False,
    },
    context=TranscriberWorkflowContext(
        correction_llm=llm,
        extract_context_llm=llm,
        transcriptor_config=TranscriptorConfig(
            transcriptor=TranscriberWhisperLocal,
        ),
    ),
    checkpointer=checkpointer,
    thread_id="demo:transcriber",
)

transcriber_result = transcriber_workflow.start()
transcription = transcriber_result["result"]

analysis_workflow = CopyAnalysisWorkflow(
    initial_state={"transcription": transcription},
    context=CopyAnalysisWorkflowContext(analysis_llm=llm),
    checkpointer=checkpointer,
    thread_id="demo:copyanalysis",
)

analysis_result = analysis_workflow.start()
copy_analysis = analysis_result["analysis"]

user_profile = UserProfileOutput(
    product_or_solution="Example product",
    target_audience="Example audience",
    core_problem="Example problem",
    core_desire="Example desired outcome",
    main_promise="Example promise",
    unique_mechanism="Example mechanism",
    benefits=["Example benefit"],
    objections=["Example objection"],
    proof_assets=["Example proof"],
    offer_details="Example offer details",
    call_to_action="Click to learn more",
    tone="Direct and helpful",
    target_language="English",
    platform="Short-form video",
    desired_duration=1.5,
    restrictions=["Do not make unsupported claims"],
)

adaptation_workflow = CopyAdaptationWorkflow(
    initial_state={
        "copy_analysis": copy_analysis,
        "user_profile": user_profile,
        "max_words_per_minute": 160,
        "min_words_per_minute": 140,
    },
    context=CopyAdaptationWorkflowContext(
        strategy_llm=llm,
        writing_llm=llm,
        review_llm=llm,
        validation_llm=llm,
        max_retry=2,
    ),
    checkpointer=checkpointer,
    thread_id="demo:copyadaptation",
)

adaptation_result = adaptation_workflow.start()
adapted_script = adaptation_result["adapted_script"]
```

## Running the Demo

The current demo lives at:

```text
src/kyrg/workflows/main.py
```

It is intentionally hardcoded for local experimentation. Before running it,
check and adjust:

- `run_id`
- `database_path`
- `source_path`
- `audio_path`
- model names
- `UserProfileOutput`
- provider API keys

Example command:

```bash
uv run python src/kyrg/workflows/main.py
```

The demo can create local JSON and PNG workflow artifacts and SQLite checkpoint
files.

## Tests

Run the deterministic test suite:

```bash
uv run pytest
```

Run focused suites:

```bash
uv run pytest tests/unit/llms -q
uv run pytest tests/unit/workflows/transcriber -q
uv run pytest tests/unit/workflows/copyanalysis -q
uv run pytest tests/unit/workflows/copyadaptation -q
uv run pytest tests/integration/workflows -q
```

Live evals are opt-in because they can call paid, non-deterministic provider
APIs:

```bash
KYRG_RUN_COPYADAPTATION_EVALS=1 uv run pytest -m live_eval tests/evals
```

## Current Limitations

- The project is a library/MVP, not a stable product runtime.
- `src/kyrg/workflows/main.py` is a hardcoded demo.
- Workflow `start()` writes JSON artifacts as a side effect.
- `draw_workflow()` writes PNG artifacts as a side effect.
- FFmpeg/ffprobe operations depend on local binaries and local files.
- Remote providers require valid credentials and may incur cost.
- Video generation returns provider references; long-term storage/download is a
  caller responsibility.
- Postgres checkpointing requires an optional dependency that is not currently
  part of the core dependency list.
- Some evolving imports may not yet be represented in `pyproject.toml`.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
