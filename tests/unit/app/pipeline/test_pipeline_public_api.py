"""Unit tests for the public pipeline package API."""

from __future__ import annotations

import app.pipeline as pipeline
from app.pipeline.files import (
    build_pipeline_input_key,
    save_pipeline_file,
    save_pipeline_upload,
    stored_file_to_job_payload,
)
from app.pipeline.input import (
    DEFAULT_OUTPUT_FORMATS,
    OUTPUT_FORMAT_ALIASES,
    SUPPORTED_OUTPUT_FORMATS,
    get_pipeline_type,
    normalize_pipeline_input,
)
from app.pipeline.jobs import (
    build_create_job_payload,
    build_failed_job_payload,
    build_input_json,
    build_uploaded_job_payload,
    create_pipeline_job,
    mark_pipeline_job_failed,
    mark_pipeline_job_uploaded,
)
from app.pipeline.service import PipelineService
from app.schemas.pipeline import PipelineInputFile, PipelineStartResult


def test_public_api_exports_expected_symbols() -> None:
    """Keep the pipeline package root API explicit and stable."""

    assert set(pipeline.__all__) == {
        "DEFAULT_OUTPUT_FORMATS",
        "OUTPUT_FORMAT_ALIASES",
        "OutputFormat",
        "PipelineInput",
        "PipelineInputFile",
        "PipelineService",
        "PipelineStartResult",
        "PipelineType",
        "SUPPORTED_OUTPUT_FORMATS",
        "build_create_job_payload",
        "build_failed_job_payload",
        "build_input_json",
        "build_pipeline_input_key",
        "build_uploaded_job_payload",
        "create_pipeline_job",
        "get_pipeline_type",
        "mark_pipeline_job_failed",
        "mark_pipeline_job_uploaded",
        "normalize_pipeline_input",
        "save_pipeline_file",
        "save_pipeline_upload",
        "stored_file_to_job_payload",
    }


def test_public_api_imports_without_circular_imports() -> None:
    """Package root imports should resolve to the concrete public objects."""

    assert pipeline.DEFAULT_OUTPUT_FORMATS is DEFAULT_OUTPUT_FORMATS
    assert pipeline.OUTPUT_FORMAT_ALIASES is OUTPUT_FORMAT_ALIASES
    assert pipeline.SUPPORTED_OUTPUT_FORMATS is SUPPORTED_OUTPUT_FORMATS
    assert pipeline.PipelineInputFile is PipelineInputFile
    assert pipeline.PipelineService is PipelineService
    assert pipeline.PipelineStartResult is PipelineStartResult
    assert pipeline.build_create_job_payload is build_create_job_payload
    assert pipeline.build_failed_job_payload is build_failed_job_payload
    assert pipeline.build_input_json is build_input_json
    assert pipeline.build_pipeline_input_key is build_pipeline_input_key
    assert pipeline.build_uploaded_job_payload is build_uploaded_job_payload
    assert pipeline.create_pipeline_job is create_pipeline_job
    assert pipeline.get_pipeline_type is get_pipeline_type
    assert pipeline.mark_pipeline_job_failed is mark_pipeline_job_failed
    assert pipeline.mark_pipeline_job_uploaded is mark_pipeline_job_uploaded
    assert pipeline.normalize_pipeline_input is normalize_pipeline_input
    assert pipeline.save_pipeline_file is save_pipeline_file
    assert pipeline.save_pipeline_upload is save_pipeline_upload
    assert pipeline.stored_file_to_job_payload is stored_file_to_job_payload
