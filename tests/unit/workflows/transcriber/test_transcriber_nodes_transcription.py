"""Unit tests for the transcriber workflow transcription node."""

from types import SimpleNamespace
from typing import Any, ClassVar, cast

import pytest

from kyrg.workflows.core import WorkflowRuntime
from kyrg.workflows.transcriber import nodes
from kyrg.workflows.transcriber.schemas import TranscriptorConfig
from kyrg.workflows.transcriber.state import TranscriberState


class RemoteTranscriberMarker:
    """Identify remote fakes without inheriting production integrations."""


class RecordingTranscriber:
    """Record provider construction and transcription calls."""

    constructor_arguments: ClassVar[list[dict[str, object]]] = []
    instances: ClassVar[list["RecordingTranscriber"]] = []
    result: ClassVar[object] = object()
    constructor_error: ClassVar[BaseException | None] = None
    transcribe_error: ClassVar[BaseException | None] = None

    def __init__(self, **arguments: object) -> None:
        """Record constructor arguments or raise the configured error."""
        provider_type = type(self)
        provider_type.constructor_arguments.append(arguments)
        if provider_type.constructor_error is not None:
            raise provider_type.constructor_error

        self.transcribe_calls = 0
        self.atranscribe_calls = 0
        provider_type.instances.append(self)

    @classmethod
    def reset(cls) -> None:
        """Reset all observations and configured outcomes for one test."""
        cls.constructor_arguments = []
        cls.instances = []
        cls.result = object()
        cls.constructor_error = None
        cls.transcribe_error = None

    def transcribe(self) -> object:
        """Record a synchronous transcription and return its outcome."""
        self.transcribe_calls += 1
        error = type(self).transcribe_error
        if error is not None:
            raise error
        return type(self).result

    async def atranscribe(self) -> object:
        """Record an asynchronous transcription if it is ever requested."""
        self.atranscribe_calls += 1
        return type(self).result


class LocalTranscriberFake(RecordingTranscriber):
    """Represent a local synchronous transcription provider."""


class RemoteTranscriberFake(RemoteTranscriberMarker, RecordingTranscriber):
    """Represent a remote synchronous transcription provider."""


def _state(**values: object) -> TranscriberState:
    """Build a partial state for an isolated node test."""
    return cast(TranscriberState, values)


def _config(
    transcriptor: object,
    *,
    temperature: object = 0.0,
    api_key: object = None,
) -> TranscriptorConfig:
    """Build runtime configuration while allowing edge-case values."""
    return TranscriptorConfig(
        transcriptor=cast(Any, transcriptor),
        transcriptor_temperature=cast(Any, temperature),
        transcriptor_api_key=cast(Any, api_key),
    )


def _runtime(config: TranscriptorConfig) -> WorkflowRuntime:
    """Build the minimal runtime shape consumed by the node."""
    context = SimpleNamespace(transcriptor_config=config)
    return cast(WorkflowRuntime, SimpleNamespace(context=context))


def _patch_remote_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch remote-provider detection in the nodes module."""
    monkeypatch.setattr(nodes, "TranscriberAPIBase", RemoteTranscriberMarker)


def test_audio_text_converter_builds_and_calls_local_transcriber(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configure a local provider without forwarding its ignored API key."""
    _patch_remote_marker(monkeypatch)
    LocalTranscriberFake.reset()
    expected_result = object()
    LocalTranscriberFake.result = expected_result
    config = _config(
        LocalTranscriberFake,
        temperature=0.25,
        api_key="ignored-local-key",
    )
    state = _state(
        audio_path="working/audio.wav",
        model_name="local-model",
        language="pt",
    )

    result = nodes.audio_text_converter(state, _runtime(config))

    assert LocalTranscriberFake.constructor_arguments == [
        {
            "audio_path": "working/audio.wav",
            "model_name": "local-model",
            "language": "pt",
            "temperature": 0.25,
        }
    ]
    instance = LocalTranscriberFake.instances[0]
    assert instance.transcribe_calls == 1
    assert instance.atranscribe_calls == 0
    assert result["result"] is expected_result


def test_audio_text_converter_builds_and_calls_remote_transcriber(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configure a remote provider with its exact API key and arguments."""
    _patch_remote_marker(monkeypatch)
    RemoteTranscriberFake.reset()
    expected_result = object()
    RemoteTranscriberFake.result = expected_result
    config = _config(
        RemoteTranscriberFake,
        temperature=0.1,
        api_key="remote-secret",
    )
    state = _state(
        audio_path="working/audio.wav",
        model_name="remote-model",
        language="en",
    )

    result = nodes.audio_text_converter(state, _runtime(config))

    assert RemoteTranscriberFake.constructor_arguments == [
        {
            "audio_path": "working/audio.wav",
            "model_name": "remote-model",
            "language": "en",
            "temperature": 0.1,
            "api_key": "remote-secret",
        }
    ]
    instance = RemoteTranscriberFake.instances[0]
    assert instance.transcribe_calls == 1
    assert instance.atranscribe_calls == 0
    assert result["result"] is expected_result


def test_audio_text_converter_defaults_none_temperature_and_accepts_empty_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default None temperature to 0.0 and accept an empty remote API key."""
    _patch_remote_marker(monkeypatch)
    RemoteTranscriberFake.reset()
    config = _config(
        RemoteTranscriberFake,
        temperature=None,
        api_key="",
    )
    state = _state(
        audio_path="audio.wav",
        model_name="remote-model",
        language=None,
    )

    nodes.audio_text_converter(state, _runtime(config))

    assert RemoteTranscriberFake.constructor_arguments == [
        {
            "audio_path": "audio.wav",
            "model_name": "remote-model",
            "language": None,
            "temperature": 0.0,
            "api_key": "",
        }
    ]


def test_audio_text_converter_requires_runtime_context_before_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise RuntimeError before constructing a provider without context."""
    _patch_remote_marker(monkeypatch)
    LocalTranscriberFake.reset()
    runtime = cast(WorkflowRuntime, SimpleNamespace(context=None))
    state = _state(audio_path="audio.wav", model_name="model")

    with pytest.raises(
        RuntimeError,
        match="Transcriber workflow context is required",
    ):
        nodes.audio_text_converter(state, runtime)

    assert LocalTranscriberFake.constructor_arguments == []


def test_audio_text_converter_requires_remote_api_key_before_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise ValueError before constructing a remote provider without a key."""
    _patch_remote_marker(monkeypatch)
    RemoteTranscriberFake.reset()
    config = _config(RemoteTranscriberFake, api_key=None)
    state = _state(audio_path="audio.wav", model_name="model")

    with pytest.raises(
        ValueError,
        match="api_key is required for remote transcriber",
    ):
        nodes.audio_text_converter(state, _runtime(config))

    assert RemoteTranscriberFake.constructor_arguments == []


def test_audio_text_converter_propagates_non_class_type_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Show that the config dataclass accepts a value rejected by issubclass."""
    _patch_remote_marker(monkeypatch)
    invalid_transcriptor = "not-a-transcriber-class"
    config = _config(invalid_transcriptor)
    state = _state(audio_path="audio.wav", model_name="model")

    assert config.transcriptor is invalid_transcriptor
    with pytest.raises(TypeError):
        nodes.audio_text_converter(state, _runtime(config))


@pytest.mark.parametrize(
    ("state", "missing_key"),
    [
        pytest.param(_state(model_name="model"), "audio_path", id="audio-path"),
        pytest.param(_state(audio_path="audio.wav"), "model_name", id="model"),
    ],
)
def test_audio_text_converter_propagates_missing_state_key(
    monkeypatch: pytest.MonkeyPatch,
    state: TranscriberState,
    missing_key: str,
) -> None:
    """Propagate KeyError for each absent required state value."""
    _patch_remote_marker(monkeypatch)
    LocalTranscriberFake.reset()
    config = _config(LocalTranscriberFake)

    with pytest.raises(KeyError) as exc_info:
        nodes.audio_text_converter(state, _runtime(config))

    assert exc_info.value.args == (missing_key,)
    assert LocalTranscriberFake.constructor_arguments == []


def test_audio_text_converter_propagates_constructor_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Propagate the exact provider constructor exception."""
    _patch_remote_marker(monkeypatch)
    LocalTranscriberFake.reset()
    error = LookupError("provider initialization failed")
    LocalTranscriberFake.constructor_error = error
    config = _config(LocalTranscriberFake)
    state = _state(audio_path="audio.wav", model_name="model")

    with pytest.raises(LookupError) as exc_info:
        nodes.audio_text_converter(state, _runtime(config))

    assert exc_info.value is error
    assert len(LocalTranscriberFake.constructor_arguments) == 1


def test_audio_text_converter_propagates_transcribe_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Propagate the exact synchronous transcription exception."""
    _patch_remote_marker(monkeypatch)
    LocalTranscriberFake.reset()
    error = ConnectionError("provider failed")
    LocalTranscriberFake.transcribe_error = error
    config = _config(LocalTranscriberFake)
    state = _state(audio_path="audio.wav", model_name="model")

    with pytest.raises(ConnectionError) as exc_info:
        nodes.audio_text_converter(state, _runtime(config))

    instance = LocalTranscriberFake.instances[0]
    assert exc_info.value is error
    assert instance.transcribe_calls == 1
    assert instance.atranscribe_calls == 0


@pytest.mark.parametrize(
    "provider_result",
    [
        pytest.param(None, id="none"),
        pytest.param({"unexpected": "shape"}, id="unexpected-object"),
    ],
)
def test_audio_text_converter_returns_unvalidated_provider_result(
    monkeypatch: pytest.MonkeyPatch,
    provider_result: object,
) -> None:
    """Return any synchronous provider result without runtime validation."""
    _patch_remote_marker(monkeypatch)
    LocalTranscriberFake.reset()
    LocalTranscriberFake.result = provider_result
    config = _config(LocalTranscriberFake)
    state = _state(audio_path="audio.wav", model_name="model")

    result = nodes.audio_text_converter(state, _runtime(config))

    instance = LocalTranscriberFake.instances[0]
    assert result["result"] is provider_result
    assert instance.transcribe_calls == 1
    assert instance.atranscribe_calls == 0
