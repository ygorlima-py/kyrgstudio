# kyrgstudio

kyrgstudio is an early-stage Python toolkit for media editing and
transcription workflows. The project currently focuses on two foundations:

- FFmpeg-backed audio and video command builders.
- Local and remote transcription providers with normalized output schemas.

The codebase is being shaped as a library: operations are grouped by domain,
providers are adapted behind shared contracts, and public imports are exposed
through package-level APIs.

## Current Status

This project is under active development. The core architecture is in place,
but higher-level orchestration, pipelines, CLI commands, tests, and production
runtime behavior are still expected to evolve.

What is already implemented:

- Audio editing command builders grouped by conversion, cleanup, dynamics,
  filters, timing, mixing, analysis, and effects.
- Video editing command builders grouped by streams, cutting, conversion,
  geometry, timing, color, overlays, subtitles, composition, frames, metadata,
  and stabilization.
- Shared editor infrastructure with contexts, a base command operation, and a
  subprocess-backed command runner.
- Transcription contracts for local and remote providers.
- A local Faster Whisper transcriber.
- Remote transcription adapters for OpenRouter, OpenAI, and ElevenLabs.
- Normalized Pydantic schemas for transcription results, text segments, and
  word-level metadata.

## Architecture

kyrgstudio currently follows a small set of explicit architectural patterns.

### Command-Based Editor Operations

Audio and video operations are implemented as command builders. Each operation
receives a context object, builds a command-line argument list, and delegates
execution to the shared runner.

```python
operation = SomeEditorOperation(context, runner, ...)
command = operation.build_command()
operation.execute()
```

This keeps FFmpeg command construction separate from process execution and
makes individual operations easier to test.

### Provider Adapters

Transcription providers expose a common `transcribe()` method and return the
same `TranscriptionResult` schema. Remote providers keep request logic and
response normalization inside provider-specific adapters.

```python
response = self._request()
return self._normalize_response(response)
```

This allows the rest of the application to consume one stable transcription
shape instead of depending directly on each provider response.

## Project Layout

```text
src/kyrg/
  editor/
    base.py              # Base editor operation contract
    context.py           # Context objects for command inputs and outputs
    runner.py            # Subprocess-backed command execution
    audio/               # Audio editing command builders
    video/               # Video editing command builders
  transcribers/
    base.py              # Transcription provider contracts
    schemas.py           # Normalized Pydantic transcription schemas
    local_model.py       # Faster Whisper local provider
    remote_model.py      # OpenRouter, OpenAI, and ElevenLabs providers
```

Detailed package documentation is available in:

- `src/kyrg/editor/audio/README.md`
- `src/kyrg/editor/video/README.md`
- `src/kyrg/transcribers/README.md`

## Requirements

- Python `>=3.12`
- FFmpeg available in the system path for editor operations
- Provider credentials for remote transcription APIs

Python dependencies are defined in `pyproject.toml`:

- `faster-whisper`
- `pydantic`
- `requests`

## Installation

Using `uv`:

```bash
uv sync
```

Or with `pip` in an active virtual environment:

```bash
pip install -e .
```

The Python package is currently exposed under the `kyrg` import namespace.

## Usage

### Video Editing

```python
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner
from kyrg.editor.video import TrimVideo

context = MediaContext(
    input_path="source.mp4",
    output_path="clip.mp4",
)

runner = CommandRunner()
operation = TrimVideo(
    context=context,
    runner=runner,
    start_time=10,
    duration=30,
)

operation.execute()
```

### Audio Editing

```python
from kyrg.editor.audio import ReduceNoise
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner

context = MediaContext(
    input_path="raw_voice.wav",
    output_path="clean_voice.wav",
)

runner = CommandRunner()
operation = ReduceNoise(
    context=context,
    runner=runner,
    noise_reduction=12,
    noise_floor=-50,
)

operation.execute()
```

### Remote Transcription

```python
import os

from kyrg.transcribers import OpenAITranscriber

transcriber = OpenAITranscriber(
    audio_path="audio.wav",
    model_name="whisper-1",
    language="en",
    temperature=0,
    api_key=os.environ["OPENAI_API_KEY"],
)

result = transcriber.transcribe()
print(result.text)
```

### Local Transcription

```python
from kyrg.transcribers import TranscriberWhisperLocal

transcriber = TranscriberWhisperLocal(
    audio_path="audio.wav",
    model_name="small",
    language="en",
    temperature=0,
)

result = transcriber.transcribe()
print(result.text)
```

## Public APIs

The editor package exposes operations by media domain:

```python
from kyrg.editor.audio import NormalizeVolume, MixVoiceWithMusic
from kyrg.editor.video import TrimVideo, AddSubtitles, ReplaceVideoAudio
```

The transcriber package exposes contracts, schemas, and providers:

```python
from kyrg.transcribers import (
    ElevenLabsTranscriber,
    OpenAITranscriber,
    OpenRouterTranscriber,
    TranscriberWhisperLocal,
    TranscriptionResult,
)
```

## Design Principles

- Keep command construction separate from command execution.
- Keep provider-specific API details inside provider adapters.
- Normalize external output before it reaches the rest of the application.
- Prefer explicit context objects over loosely shaped dictionaries.
- Group operations by domain responsibility instead of implementation detail.
- Keep package-level imports explicit and stable.

## Development Roadmap

Planned areas for evolution:

- Add tests for command generation and provider normalization.
- Add a pipeline/orchestration layer for multi-step editing workflows.
- Improve `CommandRunner` with structured output, logging, and richer errors.
- Add parameter validation for operation classes.
- Add CLI or service-level entry points.
- Decide whether the public package namespace should remain `kyrg` or move to
  `kyrgstudio`.
- Expand documentation with end-to-end examples.

## Security and Local Files

API keys and local environment files should be stored in `.env` or environment
variables and should not be committed. Generated media, local datasets, caches,
virtual environments, and model artifacts are ignored by `.gitignore`.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
