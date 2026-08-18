"""Execution boundary between app jobs and the ``kyrg`` workflows.

This module translates the stable application request into the states and
contexts expected by the workflow library. It also validates every workflow
result before exposing a normalized ``WorkflowExecutionResult`` to the worker
runner. Persistence, queue configuration, and input-file cleanup belong to
other application layers.
"""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.errors import (
    FileNotFoundAppError,
    MediaTooLongError,
    WorkflowResultError,
)
from app.providers import build_llm, build_transcriptor_config
from app.schemas.pipeline import (
    CopyAdaptationPipelineInput,
    CopyAnalysisPipelineInput,
    PipelineType,
)
from app.schemas.workflow import (
    WorkflowExecutionRequest,
    WorkflowExecutionResult,
)
from app.settings import AppSettings
from kyrg.llms import LLMBase
from kyrg.transcribers import TranscriptionResult
from kyrg.workflows import (
    AdaptedScriptOutput,
    CopyAdaptationWorkflow,
    CopyAdaptationWorkflowContext,
    CopyAnalysisOutput,
    CopyAnalysisWorkflow,
    CopyAnalysisWorkflowContext,
    TranscriberWorkflow,
    TranscriberWorkflowContext,
    TranscriptorConfig,
)


TRANSCRIPTION_STAGE = "transcriber"
COPY_ANALYSIS_STAGE = "copy_analysis"
COPY_ADAPTATION_STAGE = "copy_adaptation"

INPUT_TOKEN_KEY = "input_tokens"
OUTPUT_TOKEN_KEY = "output_tokens"
TOTAL_TOKEN_KEY = "total_tokens"

DEFAULT_MAX_RETRY = 1
TRANSCRIPTION_AUDIO_FILENAME = "transcription.mp3"

ModelT = TypeVar("ModelT", bound=BaseModel)
PipelineInput = CopyAnalysisPipelineInput | CopyAdaptationPipelineInput


class LLMFactory(Protocol):
    """Factory contract used to construct provider-neutral LLM adapters."""

    def __call__(
        self,
        *,
        provider: str,
        model: str,
        settings: AppSettings,
        temperature: float | None = None,
    ) -> LLMBase:
        ...


class TranscriptorConfigFactory(Protocol):
    """Factory contract used to configure the transcription workflow."""

    def __call__(
        self,
        *,
        provider: str,
        settings: AppSettings,
        temperature: float | None = None,
    ) -> TranscriptorConfig:
        ...


class AsyncWorkflow(Protocol):
    """Minimal asynchronous interface shared by the concrete workflows."""

    async def astart(self) -> Any:
        ...


class WorkflowFactory(Protocol):
    """Constructor contract shared by the workflow graph classes."""

    def __call__(
        self,
        *,
        initial_state: dict[str, Any],
        context: object,
    ) -> AsyncWorkflow:
        ...


class KyrgWorkflowExecutor:
    """Execute the configured ``kyrg`` pipeline for one worker request.

    A new set of provider adapters is created for each execution. This avoids
    sharing mutable token counters and provider clients between concurrent
    worker jobs.
    """

    def __init__(
        self,
        *,
        settings: AppSettings,
        llm_factory: LLMFactory = build_llm,
        transcriptor_config_factory: TranscriptorConfigFactory = (
            build_transcriptor_config
        ),
        transcriber_workflow_factory: WorkflowFactory = TranscriberWorkflow,
        copy_analysis_workflow_factory: WorkflowFactory = CopyAnalysisWorkflow,
        copy_adaptation_workflow_factory: WorkflowFactory = (
            CopyAdaptationWorkflow
        ),
        llm_temperature: float | None = None,
        transcriber_temperature: float | None = None,
        max_retry: int = DEFAULT_MAX_RETRY,
    ) -> None:
        self.settings = settings
        self.llm_factory = llm_factory
        self.transcriptor_config_factory = transcriptor_config_factory
        self.transcriber_workflow_factory = transcriber_workflow_factory
        self.copy_analysis_workflow_factory = copy_analysis_workflow_factory
        self.copy_adaptation_workflow_factory = copy_adaptation_workflow_factory
        self.llm_temperature = (
            settings.llm_temperature
            if llm_temperature is None
            else llm_temperature
        )
        self.transcriber_temperature = transcriber_temperature
        self.max_retry = _normalize_max_retry(max_retry)

    async def execute(
        self,
        request: WorkflowExecutionRequest,
    ) -> WorkflowExecutionResult:
        """Execute and normalize the pipeline selected by ``request``.

        The temporary directory contains only workflow-generated media such as
        normalized MP3 audio. The runner remains responsible for the stored
        input file and any materialized remote copy.
        """

        source_path = _require_source_file(request.source_path)
        source_type = _require_source_type(request.source_type)
        pipeline_input = _validate_pipeline_input(
            request.input_json,
            pipeline_type=request.pipeline_type,
        )
        _ensure_source_type_matches(source_type, pipeline_input.source_type)

        with TemporaryDirectory(prefix=f"kyrg-job-{request.job_id}-") as workspace:
            audio_path = Path(workspace) / TRANSCRIPTION_AUDIO_FILENAME
            transcription, transcription_state = await self._transcribe(
                source_path=source_path,
                source_type=source_type,
                audio_path=audio_path,
                pipeline_input=pipeline_input,
            )
            _enforce_max_duration(
                transcription_state,
                max_duration_seconds=pipeline_input.max_duration_seconds,
            )

            copy_analysis, analysis_state = await self._analyse_copy(
                transcription=transcription,
                pipeline_input=pipeline_input,
            )

            stage_usage = {
                TRANSCRIPTION_STAGE: _extract_token_usage(
                    transcription_state,
                    stage=TRANSCRIPTION_STAGE,
                ),
                COPY_ANALYSIS_STAGE: _extract_token_usage(
                    analysis_state,
                    stage=COPY_ANALYSIS_STAGE,
                ),
            }

            output_json: dict[str, Any] = {
                "transcription": transcription.model_dump(mode="json"),
                "copy_analysis": copy_analysis.model_dump(mode="json"),
            }

            if isinstance(pipeline_input, CopyAdaptationPipelineInput):
                adapted_script, adaptation_state = await self._adapt_copy(
                    copy_analysis=copy_analysis,
                    pipeline_input=pipeline_input,
                )
                adapted_script_json = adapted_script.model_dump(mode="json")
                stage_usage[COPY_ADAPTATION_STAGE] = _extract_token_usage(
                    adaptation_state,
                    stage=COPY_ADAPTATION_STAGE,
                )
                output_json.update(
                    {
                        "adapted_script": adapted_script_json,
                        "validation": _build_validation_output(
                            adapted_script_json
                        ),
                        "missing_proofs": list(adapted_script.missing_proofs),
                    }
                )

        return WorkflowExecutionResult(
            output_json=output_json,
            token_usage=_build_token_usage(stage_usage),
        )

    async def _transcribe(
        self,
        *,
        source_path: Path,
        source_type: str,
        audio_path: Path,
        pipeline_input: PipelineInput,
    ) -> tuple[TranscriptionResult, Mapping[str, Any]]:
        """Run transcription and return its validated result and final state."""

        support_llm = self._build_llm(
            provider=pipeline_input.llm_provider,
            model=pipeline_input.analysis_model,
        )
        transcriptor_config = self.transcriptor_config_factory(
            provider=pipeline_input.transcriber_provider,
            settings=self.settings,
            temperature=self.transcriber_temperature,
        )
        workflow = self.transcriber_workflow_factory(
            initial_state={
                "source_path": str(source_path),
                "source_type": source_type,
                "audio_path": str(audio_path),
                "model_name": pipeline_input.transcriber_model,
                "language": pipeline_input.language,
                "need_correction": pipeline_input.need_correction,
            },
            context=TranscriberWorkflowContext(
                correction_llm=support_llm,
                extract_context_llm=support_llm,
                transcriptor_config=transcriptor_config,
            ),
        )
        state = await _run_workflow(
            workflow,
            workflow_name="TranscriberWorkflow",
        )
        transcription = _validate_model_result(
            state,
            key="result",
            model=TranscriptionResult,
            workflow_name="TranscriberWorkflow",
        )
        return transcription, state

    async def _analyse_copy(
        self,
        *,
        transcription: TranscriptionResult,
        pipeline_input: PipelineInput,
    ) -> tuple[CopyAnalysisOutput, Mapping[str, Any]]:
        """Run copy analysis and validate the aggregated analysis output."""

        analysis_llm = self._build_llm(
            provider=pipeline_input.llm_provider,
            model=pipeline_input.analysis_model,
        )
        workflow = self.copy_analysis_workflow_factory(
            initial_state={"transcription": transcription},
            context=CopyAnalysisWorkflowContext(analysis_llm=analysis_llm),
        )
        state = await _run_workflow(
            workflow,
            workflow_name="CopyAnalysisWorkflow",
        )
        copy_analysis = _validate_model_result(
            state,
            key="analysis",
            model=CopyAnalysisOutput,
            workflow_name="CopyAnalysisWorkflow",
        )
        return copy_analysis, state

    async def _adapt_copy(
        self,
        *,
        copy_analysis: CopyAnalysisOutput,
        pipeline_input: CopyAdaptationPipelineInput,
    ) -> tuple[AdaptedScriptOutput, Mapping[str, Any]]:
        """Run copy adaptation with independent LLMs for each workflow role."""

        provider = pipeline_input.llm_provider
        model = pipeline_input.adaptation_model

        workflow = self.copy_adaptation_workflow_factory(
            initial_state={
                "copy_analysis": copy_analysis,
                "user_profile": pipeline_input.user_profile,
            },
            context=CopyAdaptationWorkflowContext(
                strategy_llm=self._build_llm(provider=provider, model=model),
                writing_llm=self._build_llm(provider=provider, model=model),
                review_llm=self._build_llm(provider=provider, model=model),
                validation_llm=self._build_llm(provider=provider, model=model),
                max_retry=self.max_retry,
            ),
        )
        state = await _run_workflow(
            workflow,
            workflow_name="CopyAdaptationWorkflow",
        )
        adapted_script = _validate_model_result(
            state,
            key="adapted_script",
            model=AdaptedScriptOutput,
            workflow_name="CopyAdaptationWorkflow",
        )
        return adapted_script, state

    def _build_llm(self, *, provider: str, model: str) -> LLMBase:
        """Construct one isolated LLM adapter for a workflow role."""

        return self.llm_factory(
            provider=provider,
            model=model,
            settings=self.settings,
            temperature=self.llm_temperature,
        )


async def _run_workflow(
    workflow: AsyncWorkflow,
    *,
    workflow_name: str,
) -> Mapping[str, Any]:
    result = await workflow.astart()

    if not isinstance(result, Mapping):
        raise WorkflowResultError(
            technical_message=f"{workflow_name} returned an invalid state.",
            step="validating_workflow_result",
            details={
                "workflow": workflow_name,
                "result_type": type(result).__name__,
            },
        )

    return result


def _validate_model_result(
    state: Mapping[str, Any],
    *,
    key: str,
    model: type[ModelT],
    workflow_name: str,
) -> ModelT:
    value = state.get(key)

    if value is None:
        raise WorkflowResultError(
            technical_message=f"{workflow_name} finished without {key}.",
            step="validating_workflow_result",
            details={"workflow": workflow_name, "missing_key": key},
        )

    try:
        return model.model_validate(value)
    except ValidationError as error:
        raise WorkflowResultError(
            technical_message=f"{workflow_name} returned invalid {key}.",
            step="validating_workflow_result",
            details={
                "workflow": workflow_name,
                "result_key": key,
                "validation_errors": error.errors(
                    include_url=False,
                    include_input=False,
                ),
            },
        ) from error


def _build_validation_output(
    adapted_script: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "validation_passed": bool(
            adapted_script.get("validation_passed", False)
        ),
        "validation_errors": list(
            adapted_script.get("validation_errors") or []
        ),
        "validation_warnings": list(
            adapted_script.get("validation_warnings") or []
        ),
    }


def _validate_pipeline_input(
    value: Any,
    *,
    pipeline_type: PipelineType,
) -> PipelineInput:
    if pipeline_type == "copy_analysis":
        input_model: (
            type[CopyAnalysisPipelineInput]
            | type[CopyAdaptationPipelineInput]
        ) = CopyAnalysisPipelineInput
    elif pipeline_type == "copy_adaptation":
        input_model = CopyAdaptationPipelineInput
    else:
        raise WorkflowResultError(
            technical_message="Unsupported worker pipeline type.",
            step="preparing_workflows",
            details={"pipeline_type": pipeline_type},
        )

    try:
        return input_model.model_validate(value)
    except ValidationError as error:
        raise WorkflowResultError(
            technical_message="Persisted pipeline input is invalid.",
            step="preparing_workflows",
            details={
                "pipeline_type": pipeline_type,
                "validation_errors": error.errors(
                    include_url=False,
                    include_input=False,
                ),
            },
        ) from error


def _ensure_source_type_matches(
    request_source_type: str,
    persisted_source_type: str,
) -> None:
    if request_source_type != persisted_source_type:
        raise WorkflowResultError(
            technical_message="Worker source type does not match persisted input.",
            step="preparing_workflows",
            details={
                "request_source_type": request_source_type,
                "persisted_source_type": persisted_source_type,
            },
        )


def _extract_token_usage(
    state: Mapping[str, Any],
    *,
    stage: str,
) -> dict[str, int]:
    input_tokens = _nonnegative_int(
        state.get(INPUT_TOKEN_KEY, 0),
        field=INPUT_TOKEN_KEY,
        stage=stage,
    )
    output_tokens = _nonnegative_int(
        state.get(OUTPUT_TOKEN_KEY, 0),
        field=OUTPUT_TOKEN_KEY,
        stage=stage,
    )

    return {
        INPUT_TOKEN_KEY: input_tokens,
        OUTPUT_TOKEN_KEY: output_tokens,
        TOTAL_TOKEN_KEY: input_tokens + output_tokens,
    }


def _build_token_usage(
    stage_usage: Mapping[str, Mapping[str, int]],
) -> dict[str, Any]:
    total_input = sum(
        usage[INPUT_TOKEN_KEY]
        for usage in stage_usage.values()
    )
    total_output = sum(
        usage[OUTPUT_TOKEN_KEY]
        for usage in stage_usage.values()
    )

    return {
        **{stage: dict(usage) for stage, usage in stage_usage.items()},
        "total": {
            INPUT_TOKEN_KEY: total_input,
            OUTPUT_TOKEN_KEY: total_output,
            TOTAL_TOKEN_KEY: total_input + total_output,
        },
    }


def _enforce_max_duration(
    transcription_state: Mapping[str, Any],
    *,
    max_duration_seconds: int | None,
) -> None:
    max_duration = _optional_positive_number(
        max_duration_seconds,
        field="max_duration_seconds",
    )

    if max_duration is None:
        return

    duration = _optional_positive_number(
        transcription_state.get("audio_duration_in_seconds"),
        field="audio_duration_in_seconds",
    )

    if duration is not None and duration > max_duration:
        raise MediaTooLongError(
            technical_message="Input media exceeds the configured duration limit.",
            step="validating_media_duration",
            details={
                "duration_seconds": duration,
                "max_duration_seconds": max_duration,
            },
        )


def _require_source_file(value: Path) -> Path:
    path = Path(value).expanduser()

    if not path.is_file():
        raise FileNotFoundAppError(
            technical_message="Worker input file does not exist.",
            step="preparing_workflows",
            details={"source_path": str(path)},
        )

    return path


def _require_source_type(value: str) -> str:
    normalized = str(value or "").strip().lower()

    if normalized not in {"video", "audio"}:
        raise WorkflowResultError(
            technical_message="Unsupported worker source type.",
            step="preparing_workflows",
            details={
                "source_type": value,
                "supported_source_types": ["audio", "video"],
            },
        )

    return normalized


def _optional_positive_number(value: Any, *, field: str) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _invalid_number(field, value)

    normalized = float(value)

    if not isfinite(normalized) or normalized <= 0:
        raise _invalid_number(field, value)

    return normalized


def _invalid_number(field: str, value: Any) -> WorkflowResultError:
    return WorkflowResultError(
        technical_message=f"{field} must be a positive number.",
        step="preparing_workflows",
        details={"field": field, "value": value},
    )


def _nonnegative_int(value: Any, *, field: str, stage: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _invalid_token_usage(field, stage, value)

    if value < 0:
        raise _invalid_token_usage(field, stage, value)

    return value


def _invalid_token_usage(
    field: str,
    stage: str,
    value: Any,
) -> WorkflowResultError:
    return WorkflowResultError(
        technical_message="Workflow returned invalid token usage.",
        step="validating_workflow_result",
        details={"stage": stage, "field": field, "value": value},
    )


def _normalize_max_retry(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("max_retry must be a non-negative integer.")

    if value < 0:
        raise ValueError("max_retry must be a non-negative integer.")

    return value


__all__ = [
    "COPY_ADAPTATION_STAGE",
    "COPY_ANALYSIS_STAGE",
    "DEFAULT_MAX_RETRY",
    "KyrgWorkflowExecutor",
    "TRANSCRIPTION_STAGE",
]
