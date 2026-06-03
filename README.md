# kyrgstudio

kyrgstudio is a Python media toolkit for editing, generating, and transcribing
audio, images, and video. It is organized as a library: each domain exposes a
small public contract, provider-specific behavior stays inside adapters, and
external results are normalized before they reach application code.

The project is still evolving, but its core direction is clear:

- Build FFmpeg-backed audio and video editor operations.
- Generate images, voices, and videos through provider adapters.
- Transcribe audio locally or through remote APIs.
- Normalize provider responses into stable Pydantic schemas.
- Keep command execution, provider calls, and application-level data contracts
  cleanly separated.

## Current Status

kyrgstudio is under active development. The foundations are in place, but
tests, orchestration workflows, CLI entry points, richer error handling, and
production runtime behavior are still expected to evolve.

Implemented today:

- Audio editor command builders for conversion, cleanup, dynamics, filters,
  timing, mixing, analysis, and effects.
- Video editor command builders for streams, cutting, conversion, geometry,
  timing, color, overlays, subtitles, composition, frames, metadata, and
  stabilization.
- Shared editor infrastructure with context objects, a base operation contract,
  and a subprocess-backed command runner.
- Image generation adapters for OpenAI, OpenRouter, and Gemini.
- Voice generation and voice identity adapters for OpenAI-compatible providers
  and ElevenLabs.
- Video generation adapters for Gemini, OpenRouter, and Runway.
- Local transcription with Faster Whisper.
- Remote transcription adapters for OpenRouter, OpenAI, and ElevenLabs.

## Architecture

kyrgstudio follows a few explicit architectural patterns. These patterns are
small on purpose: they keep the codebase understandable while leaving room for
new providers and workflows.

### Command-Based Editor Operations

Editor operations are command builders. They receive a context object, build a
command-line argument list, and delegate process execution to a shared runner.

```python
operation = SomeEditorOperation(context, runner, ...)
command = operation.build_command()
operation.execute()
```

This keeps FFmpeg command construction separate from process execution.
Operations stay focused on media semantics, while `CommandRunner` owns the
subprocess boundary.

### Provider Adapters

Remote APIs and SDKs return different response shapes. Adapters hide those
differences behind a common request and normalization flow:

```python
raw_result = self._request()
return self._normalize_response(raw_result)
```

Each provider owns its request logic, polling behavior, authentication details,
and response parsing. The rest of the application works with normalized output
schemas instead of provider-specific payloads.

### Stable Schemas

Pydantic models define the public data contracts for generation and
transcription. These schemas are intentionally small and explicit:

- Image generation returns image bytes plus media type metadata.
- Voice generation returns local audio paths or voice identity metadata.
- Video generation returns remote video references, not downloaded files.
- Transcription returns text, optional segments, optional word timing, and raw
  provider metadata.

### Domain-Oriented Packages

Modules are grouped by responsibility instead of by implementation detail. For
example, audio editor operations are organized around cleanup, timing, mixing,
and effects rather than raw FFmpeg filter names. Provider adapters are grouped
by media type and provider domain.

## Project Layout

```text
src/kyrg/
  adapters/
    base.py                 # Shared API adapter template classes.

  editor/
    base.py                 # Base command operation contract.
    context.py              # Input/output context objects.
    runner.py               # Subprocess-backed command runner.
    audio/                  # FFmpeg-backed audio operations.
    video/                  # FFmpeg-backed video operations.

  generate/
    images/                 # Image generation schemas and providers.
    voices/                 # Voice generation and voice identity providers.
    videos/                 # Video generation schemas and providers.

  transcribers/
    base.py                 # Transcription provider contracts.
    schemas.py              # Normalized transcription schemas.
    local_model.py          # Faster Whisper local provider.
    remote_model.py         # OpenRouter, OpenAI, and ElevenLabs providers.
```

Detailed package documentation:

- `src/kyrg/editor/audio/README.md`
- `src/kyrg/editor/video/README.md`
- `src/kyrg/transcribers/README.md`

## Requirements

- Python `>=3.12`
- FFmpeg available in the system path for editor operations
- Provider credentials for the remote APIs you use

Python dependencies are defined in `pyproject.toml` and currently include:

- `elevenlabs`
- `faster-whisper`
- `google-genai`
- `openai`
- `pydantic`
- `requests`
- `runwayml`

## Installation

Using `uv`:

```bash
uv sync
```

Or with `pip` in an active virtual environment:

```bash
pip install -e .
```

The package is exposed under the `kyrg` import namespace.

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

operation = TrimVideo(
    context=context,
    runner=CommandRunner(),
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

operation = ReduceNoise(
    context=context,
    runner=CommandRunner(),
    noise_reduction=12,
    noise_floor=-50,
)

operation.execute()
```

### Image Generation

```python
import os

from kyrg.generate.images import GeminiImageGenerator, ImageGeneratorInput

image_input = ImageGeneratorInput(
    model="imagen-4.0-generate-001",
    prompt="A red sports car parked under studio lights.",
)

generator = GeminiImageGenerator(
    api_key=os.environ["GEMINI_API_KEY"],
    image_input=image_input,
)

result = generator.generate()
image = result.images[0]
```

Image adapters normalize provider output into bytes:

```python
image.data        # raw image bytes
image.media_type  # for example, "image/png"
```

### Voice Generation

```python
import os

from kyrg.generate.voices import OpenAIVoiceGenerator, TextToSpeechInput

tts_input = TextToSpeechInput(
    model="gpt-4o-mini-tts",
    text="Welcome to kyrgstudio.",
    voice="alloy",
    output_path="voice.mp3",
)

generator = OpenAIVoiceGenerator(
    api_key=os.environ["OPENAI_API_KEY"],
    tts_input=tts_input,
)

result = generator.run()
print(result.audio_path)
```

Voice adapters that produce audio write files to the configured output path and
return a normalized `VoiceOutput`.

### Video Generation

```python
import os

from kyrg.generate.videos import GeminiVideoGenerator, VideoGenerateInput

video_input = VideoGenerateInput(
    model="veo-3.1-generate-preview",
    prompt="A cinematic shot of a mountain valley at sunrise.",
)

generator = GeminiVideoGenerator(
    api_key=os.environ["GEMINI_API_KEY"],
    video_input=video_input,
)

result = generator.generate()
video = result.videos[0]
print(video.uri)
```

Video adapters return remote video references. They do not download generated
assets automatically:

```python
video.uri            # temporary provider URL or URI
video.requires_auth  # whether download needs provider credentials
video.media_type     # usually "video/mp4"
```

For image-to-video providers, pass an optional image reference:

```python
video_input = VideoGenerateInput(
    model="gen4.5",
    prompt="A timelapse on a sunny day with clouds moving fast.",
    image="./example.png",
    image_mime_type="image/png",
    config={
        "ratio": "1280:720",
        "duration": 5,
    },
)
```

### Transcription

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

Local transcription uses the same public contract:

```python
from kyrg.transcribers import TranscriberWhisperLocal

transcriber = TranscriberWhisperLocal(
    audio_path="audio.wav",
    model_name="small",
    language="en",
    temperature=0,
)

result = transcriber.transcribe()
```

## Public APIs

### Editor

The editor layer exposes context objects, a command runner, and operation
classes grouped by media domain:

```python
from kyrg.editor.context import MediaContext, MultiInputContext
from kyrg.editor.runner import CommandRunner
from kyrg.editor.audio import NormalizeVolume, MixVoiceWithMusic
from kyrg.editor.video import TrimVideo, AddSubtitles, ReplaceVideoAudio
```

### Generation

Image generation:

```python
from kyrg.generate.images import (
    GeminiImageGenerator,
    ImageGeneratorInput,
    ImageGeneratorOutput,
    OpenAIImageGenerator,
    OpenRouterImageGenerator,
)
```

Voice generation and voice identity:

```python
from kyrg.generate.voices import (
    ElevenLabsSpeechToSpeech,
    ElevenLabsVoiceCloner,
    ElevenLabsVoiceDesignPreview,
    ElevenLabsVoiceDesignSaver,
    ElevenLabsVoiceGenerator,
    OpenAIVoiceGenerator,
    OpenRouterVoiceGenerator,
    TextToSpeechInput,
    VoiceOutput,
)
```

Video generation:

```python
from kyrg.generate.videos import (
    GeminiVideoGenerator,
    OpenRouterVideoGenerator,
    RunwayVideoGenerator,
    VideoGenerateInput,
    VideoGenerateOutput,
)
```

### Transcription

```python
from kyrg.transcribers import (
    ElevenLabsTranscriber,
    OpenAITranscriber,
    OpenRouterTranscriber,
    TranscriberWhisperLocal,
    TranscriptionResult,
)
```

## Data Contracts

### Editor Contexts

Editor operations receive explicit context objects:

- `MediaContext`: one input file and one output file.
- `MultiInputContext`: multiple input files and one output file.
- `VideoAudioContext`: one video input, one audio input, and one output file.
- `SubtitlesContext`: one video input, one subtitle file, and one output file.
- `VideoOverlayContext`: one video input, one overlay asset, and one output
  file.
- `ImageSequenceContext`: one image sequence pattern and one output file.

### Generation Outputs

Generation adapters normalize different provider outputs into stable models:

- `ImageGeneratorOutput`: generated images as bytes.
- `VoiceOutput`: generated or converted audio as local file paths.
- `VoiceIdentityOutput`: permanent voice identifiers.
- `VoiceDesignOutput`: temporary voice design previews.
- `VideoGenerateOutput`: generated videos as remote references.

### Transcription Output

`TranscriptionResult` contains:

- `audio_path`: source audio path.
- `language`: detected or requested language.
- `text`: complete transcription text.
- `segments`: optional segment-level timing data.
- `model`: provider model used.
- `raw_response`: preserved provider metadata.
- `provider`: stable provider identifier.

## Adding New Functionality

### Add an Editor Operation

1. Choose the correct media package and responsibility module.
2. Create a class that inherits from `BaseEditor`.
3. Use the smallest context that accurately describes the input shape.
4. Implement `build_command()` and return a list of command arguments.
5. Export the operation from the package `__init__.py` when it is part of the
   public API.

### Add an API Provider

1. Create a provider adapter in the correct domain package.
2. Set a stable `PROVIDER` identifier and `URL` when applicable.
3. Implement `_request()` for synchronous provider calls.
4. Implement async behavior when the domain contract requires it.
5. Normalize successful responses into the domain output schema.
6. Keep credentials, provider-specific payloads, polling, and SDK quirks inside
   the adapter.
7. Export the provider from the package `__init__.py` when it is ready for
   users.

## Design Principles

- Keep command construction separate from command execution.
- Keep provider-specific API details inside provider adapters.
- Normalize external output before it reaches the rest of the application.
- Prefer explicit schemas and context objects over loosely shaped dictionaries.
- Keep public imports deliberate and stable.
- Do not leak API keys into normalized results, logs, or persisted metadata.
- Preserve raw provider metadata only when it helps debugging and does not
  expose secrets.
- Let each media type keep the contract that matches its real behavior:
  images as bytes, voices as local files, videos as remote references.

## Security and Local Files

Store API keys in environment variables or local `.env` files and keep them out
of source control. Generated media, local datasets, caches, virtual
environments, and model artifacts should not be committed.

Video generation outputs can be temporary provider URLs or authenticated URIs.
Applications that need long-term access should download or copy those assets
into their own storage layer.

## Roadmap

Planned areas for evolution:

- Add tests for command generation and provider normalization.
- Add a pipeline layer for multi-step media workflows.
- Improve `CommandRunner` with structured output, logging, and richer errors.
- Add validation around provider-specific configuration.
- Add CLI or service-level entry points.
- Add download/storage helpers for generated remote assets.
- Decide whether the public package namespace should remain `kyrg` or move to
  `kyrgstudio`.
- Expand end-to-end examples for generation, editing, and transcription
  pipelines.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
