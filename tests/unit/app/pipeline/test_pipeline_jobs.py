"""Unit tests for pipeline job payload helpers.

These tests verify the translation between pipeline input/file/error objects
and the JobStore contract without opening a real database.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from app.errors import InvalidInputError
from app.pipeline.jobs import (
    build_create_job_payload,
    build_input_json,
    create_pipeline_job,
    mark_pipeline_job_failed,
    mark_pipeline_job_uploaded,
)
from app.schemas.pipeline import (
    CopyAdaptationPipelineInput,
    CopyAnalysisPipelineInput,
    PipelineInputFile,
)
from app.storage.base import StoredFile
from app.store.base import JobStoreBase
from kyrg.workflows.copyadaptation import UserProfileOutput


def test_build_create_job_payload_for_copy_analysis() -> None:
    """Copy analysis payload should match JobStore.create_job contract."""

    pipeline_input = _copy_analysis_input()

    payload = build_create_job_payload(
        user_id=7,
        pipeline_input=pipeline_input,
    )

    assert payload["user_id"] == 7
    assert payload["pipeline_type"] == "copy_analysis"
    assert payload["run_id"] == "run_123"
    assert payload["input_json"]["source_type"] == "video"
    assert payload["input_json"]["need_correction"] is False


def test_build_create_job_payload_for_copy_adaptation() -> None:
    """Copy adaptation payload should include adaptation-specific input."""

    pipeline_input = _copy_adaptation_input()

    payload = build_create_job_payload(
        user_id=8,
        pipeline_input=pipeline_input,
    )

    assert payload["user_id"] == 8
    assert payload["pipeline_type"] == "copy_adaptation"
    assert payload["run_id"] == "run_123"
    assert payload["input_json"]["adaptation_model"] == (
        "deepseek/deepseek-v4-flash"
    )
    assert payload["input_json"]["user_profile"]["product_or_solution"] == (
        "A practical personal finance course"
    )


def test_build_input_json_is_json_serializable() -> None:
    """Pipeline input JSON should be serializable before persistence."""

    input_json = build_input_json(_copy_adaptation_input())

    encoded = json.dumps(input_json)
    decoded = json.loads(encoded)

    assert decoded["source_type"] == "video"
    assert decoded["user_profile"]["target_audience"] == (
        "Agronomists who want to invest commissions"
    )


def test_create_pipeline_job_calls_job_store_create_job() -> None:
    """create_pipeline_job should delegate to JobStore.create_job once."""

    store = JobStoreFake()
    pipeline_input = _copy_analysis_input()

    result = _run_async(
        create_pipeline_job(
            job_store=store,
            user_id=7,
            pipeline_input=pipeline_input,
        )
    )

    assert result == {"id": 10, "status": "pending"}
    assert store.create_job_calls == [
        {
            "user_id": 7,
            "pipeline_type": "copy_analysis",
            "run_id": "run_123",
            "input_json": build_input_json(pipeline_input),
        }
    ]


def test_mark_pipeline_job_uploaded_calls_job_store_mark_uploaded() -> None:
    """mark_pipeline_job_uploaded should delegate upload references to store."""

    store = JobStoreFake()
    input_file = PipelineInputFile(
        stored_file=StoredFile(
            key="jobs/10/input.mp4",
            uri="fake://jobs/10/input.mp4",
            backend="fake",
        )
    )

    result = _run_async(
        mark_pipeline_job_uploaded(
            job_store=store,
            job_id=10,
            input_file=input_file,
        )
    )

    assert result == {"id": 10, "status": "uploaded"}
    assert store.mark_uploaded_calls == [
        {
            "job_id": 10,
            "payload": {
                "storage_backend": "fake",
                "input_file_key": "jobs/10/input.mp4",
                "input_file_uri": "fake://jobs/10/input.mp4",
            },
        }
    ]


def test_mark_pipeline_job_failed_calls_job_store_mark_failed() -> None:
    """mark_pipeline_job_failed should persist controlled error payloads."""

    store = JobStoreFake()
    error = InvalidInputError(
        technical_message="Invalid pipeline input.",
        details={"field": "analysis_model"},
    )

    result = _run_async(
        mark_pipeline_job_failed(
            job_store=store,
            job_id=10,
            error=error,
        )
    )

    assert result == {"id": 10, "status": "failed"}
    assert store.mark_failed_calls == [
        {
            "job_id": 10,
            "error": {
                "code": "invalid_input",
                "step": "validating_input",
                "details": {"field": "analysis_model"},
            },
        }
    ]


@pytest.mark.parametrize("user_id", [0, -1, True, "not-an-int"])
def test_rejects_invalid_user_id(user_id: object) -> None:
    """Job creation payload should reject invalid user identifiers."""

    with pytest.raises(InvalidInputError) as error:
        build_create_job_payload(
            user_id=user_id,  # type: ignore[arg-type]
            pipeline_input=_copy_analysis_input(),
        )

    assert error.value.details["field"] == "user_id"
    assert error.value.details["value"] == user_id
    assert error.value.details["pipeline_type"] == "copy_analysis"


class JobStoreFake(JobStoreBase):
    """Async JobStore fake that records calls without a database."""

    def __init__(self) -> None:
        self.create_job_calls: list[dict[str, Any]] = []
        self.mark_uploaded_calls: list[dict[str, Any]] = []
        self.mark_failed_calls: list[dict[str, Any]] = []

    async def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.create_job_calls.append(payload)
        return {"id": 10, "status": "pending"}

    async def mark_uploaded(
        self,
        job_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self.mark_uploaded_calls.append(
            {
                "job_id": job_id,
                "payload": payload,
            }
        )
        return {"id": job_id, "status": "uploaded"}

    async def mark_running(self, job_id: int, step: str) -> dict[str, Any]:
        return {"id": job_id, "status": "running", "step": step}

    async def mark_step_completed(
        self,
        job_id: int,
        step: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {"id": job_id, "step": step, "payload": payload}

    async def mark_completed(
        self,
        job_id: int,
        output: dict[str, Any],
    ) -> dict[str, Any]:
        return {"id": job_id, "status": "completed", "output": output}

    async def mark_failed(
        self,
        job_id: int,
        error: dict[str, Any],
    ) -> dict[str, Any]:
        self.mark_failed_calls.append(
            {
                "job_id": job_id,
                "error": error,
            }
        )
        return {"id": job_id, "status": "failed"}

    async def get_job(self, job_id: int) -> dict[str, Any] | None:
        return None

    async def get_job_by_run_id(self, run_id: str) -> dict[str, Any] | None:
        return None

    async def list_user_jobs(
        self,
        user_id: int,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return []


def _copy_analysis_input(**overrides: Any) -> CopyAnalysisPipelineInput:
    """Build a valid copy analysis pipeline input."""

    payload: dict[str, Any] = {
        "source_type": "video",
        "run_id": "run_123",
        "language": "pt-BR",
        "transcriber_provider": "whisper_local",
        "transcriber_model": "small",
        "llm_provider": "openrouter",
        "analysis_model": "deepseek/deepseek-v4-flash",
        "max_duration_seconds": 300,
        "output_formats": ["json"],
    }
    payload.update(overrides)

    return CopyAnalysisPipelineInput(**payload)


def _copy_adaptation_input(**overrides: Any) -> CopyAdaptationPipelineInput:
    """Build a valid copy adaptation pipeline input."""

    payload: dict[str, Any] = {
        "source_type": "video",
        "run_id": "run_123",
        "language": "pt-BR",
        "transcriber_provider": "whisper_local",
        "transcriber_model": "small",
        "llm_provider": "openrouter",
        "analysis_model": "deepseek/deepseek-v4-flash",
        "adaptation_model": "deepseek/deepseek-v4-flash",
        "user_profile": _user_profile(),
        "max_duration_seconds": 300,
        "output_formats": ["json"],
    }
    payload.update(overrides)

    return CopyAdaptationPipelineInput(**payload)


def _user_profile() -> UserProfileOutput:
    """Build a complete user profile for adaptation payload tests."""

    return UserProfileOutput(
        product_or_solution="A practical personal finance course",
        target_audience="Agronomists who want to invest commissions",
        core_problem="They do not know how to build an investment plan",
        core_desire="Invest commissions with more clarity and consistency",
        main_promise="Learn to organize commissions into a long-term portfolio",
        unique_mechanism="Commission Organization Method",
        benefits=["Clear investment planning steps"],
        objections=["I do not know where to start"],
        proof_assets=["Recorded curriculum walkthrough"],
        offer_details="Online course with waiting list",
        call_to_action="Join the waiting list",
        tone="Clear and practical",
        target_language="Portuguese",
        platform="YouTube",
        desired_duration=2.5,
        restrictions=["Do not promise guaranteed financial returns"],
    )


def _run_async(awaitable: Any) -> Any:
    """Run a coroutine in unit tests without requiring pytest-asyncio."""

    return asyncio.run(awaitable)
