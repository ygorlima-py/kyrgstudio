"""Unit tests for the application worker workflow executor."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest

from app.errors import WorkflowResultError
from app.schemas.workflow import WorkflowExecutionRequest
from app.settings import AppSettings
from app.worker.workflows import KyrgWorkflowExecutor
from kyrg.llms import LLMBase
from kyrg.transcribers import TranscriptionResult
from kyrg.workflows import TranscriptorConfig
from kyrg.workflows.copyadaptation.schemas import (
    AdaptedScriptOutput,
    UserProfileOutput,
)
from kyrg.workflows.copyanalysis.schemas import (
    CopyAnalysisOutput,
    CopySection,
    CopyStructureOutput,
    OfferAnalysisOutput,
    PersuasionAnalysisOutput,
)


def test_selects_copy_analysis_workflow(tmp_path: Path) -> None:
    """Copy-analysis jobs should not construct the adaptation workflow."""

    transcriber_factory = WorkflowFactoryFake(
        _transcription_state(input_tokens=2, output_tokens=1)
    )
    analysis_factory = WorkflowFactoryFake(
        _analysis_state(input_tokens=3, output_tokens=4)
    )
    adaptation_factory = WorkflowFactoryFake(
        _adaptation_state(input_tokens=5, output_tokens=6)
    )
    executor = _executor(
        transcriber_factory=transcriber_factory,
        analysis_factory=analysis_factory,
        adaptation_factory=adaptation_factory,
    )

    result = _run_async(
        executor.execute(
            _request(
                tmp_path,
                pipeline_type="copy_analysis",
                input_json=_copy_analysis_input(tmp_path),
            )
        )
    )

    assert len(transcriber_factory.calls) == 1
    assert len(analysis_factory.calls) == 1
    assert adaptation_factory.calls == []
    assert result.output_json["transcription"] == _transcription().model_dump(
        mode="json"
    )
    assert result.output_json["copy_analysis"] == _copy_analysis().model_dump(
        mode="json"
    )


def test_selects_copy_adaptation_workflow(tmp_path: Path) -> None:
    """Copy-adaptation jobs should execute all three workflow stages."""

    transcriber_factory = WorkflowFactoryFake(_transcription_state())
    analysis_factory = WorkflowFactoryFake(_analysis_state())
    adaptation_factory = WorkflowFactoryFake(_adaptation_state())
    executor = _executor(
        transcriber_factory=transcriber_factory,
        analysis_factory=analysis_factory,
        adaptation_factory=adaptation_factory,
    )
    input_json = _copy_adaptation_input(tmp_path)

    result = _run_async(
        executor.execute(
            _request(
                tmp_path,
                pipeline_type="copy_adaptation",
                input_json=input_json,
            )
        )
    )

    assert len(transcriber_factory.calls) == 1
    assert len(analysis_factory.calls) == 1
    assert len(adaptation_factory.calls) == 1
    assert adaptation_factory.calls[0]["initial_state"] == {
        "copy_analysis": _copy_analysis(),
        "user_profile": _user_profile(),
    }
    assert result.output_json["adapted_script"] == _adapted_script().model_dump(
        mode="json"
    )


def test_rejects_missing_required_input_json_fields(tmp_path: Path) -> None:
    """Persisted inputs must contain every field required by their pipeline."""

    executor = _executor()
    valid_input = _copy_analysis_input(tmp_path)

    for field in (
        "transcriber_provider",
        "transcriber_model",
        "llm_provider",
        "analysis_model",
    ):
        invalid_input = dict(valid_input)
        invalid_input.pop(field)

        with pytest.raises(WorkflowResultError) as error:
            _run_async(
                executor.execute(
                    _request(
                        tmp_path,
                        pipeline_type="copy_analysis",
                        input_json=invalid_input,
                    )
                )
            )

        assert error.value.step == "preparing_workflows"
        assert error.value.details["pipeline_type"] == "copy_analysis"


def test_normalizes_transcriber_copy_analysis_and_copy_adaptation_results(
    tmp_path: Path,
) -> None:
    """Validated results from all kyrg stages should become one stable payload."""

    transcription = _transcription()
    copy_analysis = _copy_analysis()
    adapted_script = _adapted_script()
    executor = _executor(
        transcriber_factory=WorkflowFactoryFake(
            _transcription_state(result=transcription)
        ),
        analysis_factory=WorkflowFactoryFake(
            _analysis_state(result=copy_analysis)
        ),
        adaptation_factory=WorkflowFactoryFake(
            _adaptation_state(result=adapted_script)
        ),
    )

    result = _run_async(
        executor.execute(
            _request(
                tmp_path,
                pipeline_type="copy_adaptation",
                input_json=_copy_adaptation_input(tmp_path),
            )
        )
    )

    assert result.output_json == {
        "transcription": transcription.model_dump(mode="json"),
        "copy_analysis": copy_analysis.model_dump(mode="json"),
        "adapted_script": adapted_script.model_dump(mode="json"),
        "validation": {
            "validation_passed": True,
            "validation_errors": [],
            "validation_warnings": [],
        },
        "missing_proofs": ["A real testimonial is still required."],
    }


def test_aggregates_token_usage_by_stage(tmp_path: Path) -> None:
    """Stage token counts should produce correct per-stage and total usage."""

    executor = _executor(
        transcriber_factory=WorkflowFactoryFake(
            _transcription_state(input_tokens=2, output_tokens=3)
        ),
        analysis_factory=WorkflowFactoryFake(
            _analysis_state(input_tokens=5, output_tokens=7)
        ),
        adaptation_factory=WorkflowFactoryFake(
            _adaptation_state(input_tokens=11, output_tokens=13)
        ),
    )

    result = _run_async(
        executor.execute(
            _request(
                tmp_path,
                pipeline_type="copy_adaptation",
                input_json=_copy_adaptation_input(tmp_path),
            )
        )
    )

    assert result.token_usage == {
        "transcriber": {
            "input_tokens": 2,
            "output_tokens": 3,
            "total_tokens": 5,
        },
        "copy_analysis": {
            "input_tokens": 5,
            "output_tokens": 7,
            "total_tokens": 12,
        },
        "copy_adaptation": {
            "input_tokens": 11,
            "output_tokens": 13,
            "total_tokens": 24,
        },
        "total": {
            "input_tokens": 18,
            "output_tokens": 23,
            "total_tokens": 41,
        },
    }


class AsyncWorkflowFake:
    """Workflow fake that returns one predetermined final state."""

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state

    async def astart(self) -> dict[str, Any]:
        return self.state


class WorkflowFactoryFake:
    """Workflow factory fake that records constructor inputs."""

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        *,
        initial_state: dict[str, Any],
        context: object,
    ) -> AsyncWorkflowFake:
        self.calls.append(
            {
                "initial_state": initial_state,
                "context": context,
            }
        )
        return AsyncWorkflowFake(self.state)


class LLMFactoryFake:
    """LLM factory fake that records provider configuration requests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        *,
        provider: str,
        model: str,
        settings: AppSettings,
        temperature: float | None = None,
    ) -> LLMBase:
        self.calls.append(
            {
                "provider": provider,
                "model": model,
                "settings": settings,
                "temperature": temperature,
            }
        )
        return cast(LLMBase, object())


class TranscriptorConfigFactoryFake:
    """Transcriber config factory fake that records configuration requests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        *,
        provider: str,
        settings: AppSettings,
        temperature: float | None = None,
    ) -> TranscriptorConfig:
        self.calls.append(
            {
                "provider": provider,
                "settings": settings,
                "temperature": temperature,
            }
        )
        return cast(TranscriptorConfig, object())


def _executor(
    *,
    transcriber_factory: WorkflowFactoryFake | None = None,
    analysis_factory: WorkflowFactoryFake | None = None,
    adaptation_factory: WorkflowFactoryFake | None = None,
) -> KyrgWorkflowExecutor:
    """Build an executor whose workflow dependencies are entirely fake."""

    return KyrgWorkflowExecutor(
        settings=_settings(),
        llm_factory=LLMFactoryFake(),
        transcriptor_config_factory=TranscriptorConfigFactoryFake(),
        transcriber_workflow_factory=(
            transcriber_factory or WorkflowFactoryFake(_transcription_state())
        ),
        copy_analysis_workflow_factory=(
            analysis_factory or WorkflowFactoryFake(_analysis_state())
        ),
        copy_adaptation_workflow_factory=(
            adaptation_factory or WorkflowFactoryFake(_adaptation_state())
        ),
    )


def _request(
    tmp_path: Path,
    *,
    pipeline_type: str,
    input_json: dict[str, Any],
) -> WorkflowExecutionRequest:
    """Create a request with an existing local media file."""

    source_path = tmp_path / "source.mp4"
    source_path.write_bytes(b"media")

    return WorkflowExecutionRequest(
        job_id=17,
        pipeline_type=cast(Any, pipeline_type),
        source_path=source_path,
        source_type="video",
        input_json=input_json,
    )


def _copy_analysis_input(tmp_path: Path) -> dict[str, Any]:
    """Build persisted input for a copy-analysis job."""

    return {
        "source_path": str(tmp_path / "source.mp4"),
        "source_type": "video",
        "run_id": "run-analysis",
        "language": "en",
        "transcriber_provider": "whisper_local",
        "transcriber_model": "small",
        "llm_provider": "openrouter",
        "analysis_model": "test-analysis-model",
        "max_duration_seconds": 60,
        "output_formats": ["json"],
    }


def _copy_adaptation_input(tmp_path: Path) -> dict[str, Any]:
    """Build persisted input for a copy-adaptation job."""

    return {
        **_copy_analysis_input(tmp_path),
        "run_id": "run-adaptation",
        "adaptation_model": "test-adaptation-model",
        "user_profile": _user_profile().model_dump(mode="json"),
    }


def _transcription_state(
    *,
    result: TranscriptionResult | None = None,
    input_tokens: int = 1,
    output_tokens: int = 1,
) -> dict[str, Any]:
    """Build a valid final transcription workflow state."""

    return {
        "result": result or _transcription(),
        "audio_duration_in_seconds": 10.0,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def _analysis_state(
    *,
    result: CopyAnalysisOutput | None = None,
    input_tokens: int = 1,
    output_tokens: int = 1,
) -> dict[str, Any]:
    """Build a valid final copy-analysis workflow state."""

    return {
        "analysis": result or _copy_analysis(),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def _adaptation_state(
    *,
    result: AdaptedScriptOutput | None = None,
    input_tokens: int = 1,
    output_tokens: int = 1,
) -> dict[str, Any]:
    """Build a valid final copy-adaptation workflow state."""

    return {
        "adapted_script": result or _adapted_script(),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def _transcription() -> TranscriptionResult:
    """Build a validated transcription returned by the fake workflow."""

    return TranscriptionResult(
        audio_path="/tmp/transcription.wav",
        language="en",
        text="A short sales message.",
        model="small",
        provider="whisper_local",
    )


def _copy_analysis() -> CopyAnalysisOutput:
    """Build a minimal validated copy-analysis workflow result."""

    return CopyAnalysisOutput(
        language="en",
        copy_structure=CopyStructureOutput(
            language="en",
            content_type="VSL",
            main_hook="Build a clearer future.",
            sections=[
                CopySection(
                    section_type="hook",
                    text="Build a clearer future.",
                    purpose="Open with the desired outcome.",
                    start=0.0,
                    end=3.0,
                )
            ],
            narrative_flow=["hook", "offer"],
            section_gaps=[],
            summary="A concise educational VSL.",
        ),
        offer_analysis=OfferAnalysisOutput(
            product_or_solution="Financial planning course",
            summary="A course for responsible investment planning.",
        ),
        persuasion_analysis=PersuasionAnalysisOutput(
            summary="Uses clarity and education to build confidence.",
        ),
    )


def _user_profile() -> UserProfileOutput:
    """Build a complete profile required by copy-adaptation input validation."""

    return UserProfileOutput(
        product_or_solution="Financial planning course",
        target_audience="Agronomists investing commission income",
        core_problem="They lack an investment plan.",
        core_desire="Build a reliable long-term portfolio.",
        main_promise="Learn a responsible investment planning process.",
        unique_mechanism="Commission Organization Method",
        call_to_action="Join the waiting list.",
        desired_duration=2.0,
    )


def _adapted_script() -> AdaptedScriptOutput:
    """Build a minimal validated final script for adaptation normalization."""

    return AdaptedScriptOutput(
        script="Organize each commission with a clear long-term plan.",
        word_count=9,
        voice_ready_text="Organize each commission with a clear long-term plan.",
        validation_passed=True,
        missing_proofs=["A real testimonial is still required."],
    )


def _settings() -> AppSettings:
    """Build deterministic settings without provider credentials."""

    return AppSettings(
        environment="test",
        storage_dir=Path("/tmp/kyrg-storage"),
        sqlite_path=Path("/tmp/kyrg.sqlite"),
        database_url="sqlite+aiosqlite:////tmp/kyrg.sqlite",
        database_echo=False,
        database_pool_size=5,
        database_max_overflow=10,
        database_pool_pre_ping=True,
        openrouter_api_key=None,
        openai_api_key=None,
        gemini_api_key=None,
        default_llm_provider="openrouter",
        default_analysis_model="test-analysis-model",
        default_adaptation_model="test-adaptation-model",
        default_transcriber_provider="whisper_local",
        default_transcriber_model="small",
        max_duration_seconds=60,
        request_timeout_seconds=60,
        celery_broker_url="amqp://guest:guest@localhost:5672//",
        celery_queue_name="pipeline",
        celery_task_soft_time_limit_seconds=60,
        celery_task_time_limit_seconds=90,
    )


def _run_async(awaitable: Any) -> Any:
    """Run one coroutine without requiring an async pytest plugin."""

    return asyncio.run(awaitable)
