# Transcription Providers

This package contains local and remote transcription providers used by the
application. Each provider exposes the same `transcribe()` contract and returns
a normalized `TranscriptionResult`, regardless of the underlying model runtime
or external API response shape.

The package is organized around provider adapters. Local and remote providers
can return different raw payloads, metadata, segment formats, and timing
details. The transcriber layer hides those differences behind a stable
application-level schema.

## Architecture

Transcribers follow a small provider adapter architecture:

```python
transcriber = SomeTranscriber(...)
result = transcriber.transcribe()
```

All providers inherit from `TranscriberBase`. Remote API providers inherit from
`TranscriberAPIBase`, which combines the transcription-specific state with the
shared `AdapterAPIBase` request flow:

```python
response = self._request()
return self._normalize_response(response)
```

`TranscriberAPIBase` exposes the domain method `transcribe()` and delegates the
request/normalization sequence to the shared adapter. This keeps
provider-specific request logic separate from result normalization while
allowing other domains, such as voice or image generation, to reuse the same API
adapter pattern. The rest of the application can depend on
`TranscriptionResult` instead of depending on provider-specific response
formats.

## Modules

| Module | Responsibility |
| --- | --- |
| `base.py` | Defines the shared transcriber contracts and connects remote transcribers to the shared API adapter flow. |
| `schemas.py` | Defines normalized Pydantic models for transcription results, text segments, and word segments. |
| `local_model.py` | Provides the local Faster Whisper transcriber implementation. |
| `remote_model.py` | Provides remote API-backed transcribers for OpenRouter, OpenAI, and ElevenLabs. |
| `__init__.py` | Exposes the package public API for contracts, schemas, and providers. |

## Public API

The package exports its recommended public API from `kyrg.transcribers`:

```python
from kyrg.transcribers import (
    ElevenLabsTranscriber,
    OpenAITranscriber,
    OpenRouterTranscriber,
    TranscriberWhisperLocal,
    TranscriptionResult,
)
```

Use direct module imports only when working on a specific implementation:

```python
from kyrg.transcribers.remote_model import OpenAITranscriber
from kyrg.transcribers.local_model import TranscriberWhisperLocal
```

## Normalized Result

Every provider returns a `TranscriptionResult`:

```python
TranscriptionResult(
    audio_path="audio.wav",
    language="en",
    text="Full transcription text.",
    segments=[],
    model="model-name",
    raw_response={},
    provider="provider-name",
)
```

The normalized schema allows the application to consume transcription output in
one consistent shape while still preserving the original provider payload in
`raw_response`.

## Local Provider

`TranscriberWhisperLocal` runs transcription locally through `faster_whisper`.
It loads the configured model, requests word-level timestamps, and converts
Faster Whisper segment objects into normalized text and word segments.

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

## Remote Providers

Remote providers call external transcription APIs and normalize the returned
payload:

| Provider | Class | Request Style |
| --- | --- | --- |
| OpenRouter | `OpenRouterTranscriber` | JSON request with base64-encoded audio. |
| OpenAI | `OpenAITranscriber` | Multipart form request with the audio file. |
| ElevenLabs | `ElevenLabsTranscriber` | Multipart form request with word-level timestamp support. |

Example:

```python
from kyrg.transcribers import OpenAITranscriber

transcriber = OpenAITranscriber(
    audio_path="audio.wav",
    model_name="whisper-1",
    language="en",
    temperature=0,
    api_key="...",
)

result = transcriber.transcribe()
```

## Adding a Provider

To add a new remote provider:

1. Create a class that inherits from `TranscriberAPIBase`.
2. Set `URL` and `PROVIDER`.
3. Implement `_request()` with the provider-specific HTTP request.
4. Implement `_normalize_response()` to return `TranscriptionResult`.
5. Export the class from `kyrg.transcribers.__init__`.

Example shape:

```python
class CustomProviderTranscriber(TranscriberAPIBase):
    URL = "https://provider.example/transcriptions"
    PROVIDER = "custom_provider"

    def _request(self) -> dict:
        ...

    def _normalize_response(self, response: dict) -> TranscriptionResult:
        ...
```

`TranscriberAPIBase` stores transcription configuration such as `audio_path`,
`model_name`, `language`, and `temperature`, while the shared adapter stores the
remote `api_key` and runs the common request/normalization flow.

## Design Guidelines

- Keep provider request logic inside the provider implementation.
- Normalize every provider response into `TranscriptionResult`.
- Preserve provider-specific payloads in `raw_response`.
- Keep `transcribe()` as the public domain method; reuse the shared adapter only for the API request flow.
- Keep API keys out of logs, errors, and persisted output.
- Prefer provider identifiers that are stable and machine-readable.
- Use `segments` and `words` only when the provider returns reliable timing metadata.
- Keep the public import surface in `kyrg.transcribers.__init__` explicit.

## Notes

Local transcription depends on the runtime environment and model availability.
Remote transcription depends on network access, provider credentials, provider
model names, and each provider's API contract. Provider adapters should keep
those differences isolated so the rest of the application can work with a
single normalized transcription interface.
