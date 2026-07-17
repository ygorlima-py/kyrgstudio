"""Input validation and normalization for application pipelines."""

from __future__ import annotations

from typing import Literal, overload

from app.errors import InvalidInputError
from app.providers.llms import SUPPORTED_LLM_PROVIDERS
from app.providers.transcribers import SUPPORTED_TRANSCRIBER_PROVIDERS
from app.schemas.pipeline import (
    CopyAdaptationPipelineInput,
    CopyAnalysisPipelineInput,
    PipelineType,
)


PipelineInput = CopyAnalysisPipelineInput | CopyAdaptationPipelineInput
OutputFormat = Literal["json", "md", "txt"]

DEFAULT_OUTPUT_FORMATS: tuple[OutputFormat, ...] = ("json",)
SUPPORTED_OUTPUT_FORMATS: tuple[OutputFormat, ...] = ("json", "md", "txt")
OUTPUT_FORMAT_ALIASES = {
    "markdown": "md",
    "text": "txt",
}


@overload
def normalize_pipeline_input(
    pipeline_input: CopyAnalysisPipelineInput,
) -> CopyAnalysisPipelineInput:
    ...


@overload
def normalize_pipeline_input(
    pipeline_input: CopyAdaptationPipelineInput,
) -> CopyAdaptationPipelineInput:
    ...


def normalize_pipeline_input(pipeline_input: PipelineInput) -> PipelineInput:
    """Validate and normalize input before storage, database, or queue access."""

    pipeline_type = get_pipeline_type(pipeline_input)
    common_updates = _common_updates(pipeline_input, pipeline_type=pipeline_type)

    if isinstance(pipeline_input, CopyAdaptationPipelineInput):
        return pipeline_input.model_copy(
            update={
                **common_updates,
                "adaptation_model": _required_text(
                    pipeline_input.adaptation_model,
                    field_name="adaptation_model",
                    pipeline_type=pipeline_type,
                ),
            }
        )

    return pipeline_input.model_copy(update=common_updates)


def get_pipeline_type(pipeline_input: PipelineInput) -> PipelineType:
    """Return the concrete pipeline type represented by the input schema."""

    if isinstance(pipeline_input, CopyAdaptationPipelineInput):
        return "copy_adaptation"

    if isinstance(pipeline_input, CopyAnalysisPipelineInput):
        return "copy_analysis"

    raise InvalidInputError(
        technical_message="Unsupported pipeline input schema.",
        details={"input_type": type(pipeline_input).__name__},
    )


def _common_updates(
    pipeline_input: PipelineInput,
    *,
    pipeline_type: PipelineType,
) -> dict[str, object]:
    source_type = _normalize_source_type(
        pipeline_input.source_type,
        pipeline_type=pipeline_type,
    )
    transcriber_provider = _normalize_choice(
        pipeline_input.transcriber_provider,
        field_name="transcriber_provider",
        supported_values=SUPPORTED_TRANSCRIBER_PROVIDERS,
        pipeline_type=pipeline_type,
    )
    llm_provider = _normalize_choice(
        pipeline_input.llm_provider,
        field_name="llm_provider",
        supported_values=SUPPORTED_LLM_PROVIDERS,
        pipeline_type=pipeline_type,
    )

    return {
        "source_type": source_type,
        "run_id": _optional_text(pipeline_input.run_id),
        "language": _optional_text(pipeline_input.language),
        "transcriber_provider": transcriber_provider,
        "transcriber_model": _required_text(
            pipeline_input.transcriber_model,
            field_name="transcriber_model",
            pipeline_type=pipeline_type,
        ),
        "llm_provider": llm_provider,
        "analysis_model": _required_text(
            pipeline_input.analysis_model,
            field_name="analysis_model",
            pipeline_type=pipeline_type,
        ),
        "max_duration_seconds": _normalize_max_duration(
            pipeline_input.max_duration_seconds,
            pipeline_type=pipeline_type,
        ),
        "output_formats": _normalize_output_formats(
            pipeline_input.output_formats,
            pipeline_type=pipeline_type,
        ),
    }


def _required_text(
    value: str,
    *,
    field_name: str,
    pipeline_type: PipelineType,
) -> str:
    normalized_value = str(value or "").strip()

    if not normalized_value:
        raise InvalidInputError(
            technical_message=f"{field_name} is required.",
            details={
                "field": field_name,
                "pipeline_type": pipeline_type,
            },
        )

    return normalized_value


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()
    return normalized_value or None


def _normalize_source_type(
    value: str,
    *,
    pipeline_type: PipelineType,
) -> str:
    normalized_value = str(value or "").strip().lower()
    supported_values = ("video", "audio")

    if normalized_value not in supported_values:
        raise InvalidInputError(
            technical_message=f"Unsupported source_type: {value}",
            details={
                "field": "source_type",
                "value": value,
                "pipeline_type": pipeline_type,
                "supported_values": list(supported_values),
            },
        )

    return normalized_value


def _normalize_choice(
    value: str,
    *,
    field_name: str,
    supported_values: tuple[str, ...],
    pipeline_type: PipelineType,
) -> str:
    normalized_value = str(value or "").strip().lower()

    if not normalized_value:
        raise InvalidInputError(
            technical_message=f"{field_name} is required.",
            details={
                "field": field_name,
                "pipeline_type": pipeline_type,
                "supported_values": list(supported_values),
            },
        )

    if normalized_value not in supported_values:
        raise InvalidInputError(
            technical_message=f"Unsupported {field_name}: {value}",
            details={
                "field": field_name,
                "value": value,
                "pipeline_type": pipeline_type,
                "supported_values": list(supported_values),
            },
        )

    return normalized_value


def _normalize_max_duration(
    value: int | None,
    *,
    pipeline_type: PipelineType,
) -> int | None:
    if value is None:
        return None

    normalized_value = int(value)

    if normalized_value <= 0:
        raise InvalidInputError(
            technical_message="max_duration_seconds must be positive.",
            details={
                "field": "max_duration_seconds",
                "value": value,
                "pipeline_type": pipeline_type,
            },
        )

    return normalized_value


def _normalize_output_formats(
    values: list[str],
    *,
    pipeline_type: PipelineType,
) -> list[str]:
    if not values:
        return list(DEFAULT_OUTPUT_FORMATS)

    normalized_formats = []

    for value in values:
        normalized_value = str(value or "").strip().lower()
        normalized_value = OUTPUT_FORMAT_ALIASES.get(
            normalized_value,
            normalized_value,
        )

        if not normalized_value:
            continue

        if normalized_value not in SUPPORTED_OUTPUT_FORMATS:
            raise InvalidInputError(
                technical_message=f"Unsupported output format: {value}",
                details={
                    "field": "output_formats",
                    "value": value,
                    "pipeline_type": pipeline_type,
                    "supported_values": list(SUPPORTED_OUTPUT_FORMATS),
                },
            )

        if normalized_value not in normalized_formats:
            normalized_formats.append(normalized_value)

    if not normalized_formats:
        return list(DEFAULT_OUTPUT_FORMATS)

    return normalized_formats


__all__ = [
    "DEFAULT_OUTPUT_FORMATS",
    "OUTPUT_FORMAT_ALIASES",
    "OutputFormat",
    "PipelineInput",
    "PipelineType",
    "SUPPORTED_OUTPUT_FORMATS",
    "get_pipeline_type",
    "normalize_pipeline_input",
]
