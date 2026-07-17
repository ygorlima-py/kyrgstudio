from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel

from kyrg.workflows.copyanalysis import CopyAnalysisOutput
from kyrg.workflows.copyadaptation import UserProfileOutput, AdaptedScriptOutput

from app.storage.base import StoredFile


PipelineType = Literal["copy_analysis", "copy_adaptation"]


class BasePipelineInput(BaseModel):
    source_type: Literal["video", "audio"]
    run_id: str | None = None
    language: str | None = None
    transcriber_provider: str
    transcriber_model: str
    llm_provider: str
    analysis_model: str
    max_duration_seconds: int | None = None
    output_formats: list[str] = ["json"]
    
class CopyAnalysisPipelineInput(BasePipelineInput):
    need_correction: bool = False
    
class CopyAdaptationPipelineInput(BasePipelineInput):
    user_profile: UserProfileOutput
    need_correction: bool = False
    adaptation_model: str
    
class CopyAnalysisPipelineOutput(BaseModel):
    run_id: str
    status: str
    transcription: Any | None
    copy_analysis: CopyAnalysisOutput | None
    token_usage: dict
    execution_time_seconds: float | None
    warnings: list[str]
    error: str | None
    
class CopyAdaptationPipelineOutput(BaseModel):
    run_id: str
    status: str
    transcription: Any | None
    copy_analysis: CopyAnalysisOutput | None
    adapted_script: AdaptedScriptOutput | None
    exports: dict
    validation: dict | None
    missing_proofs: list[str]
    token_usage: dict
    execution_time_seconds: float | None
    warnings: list[str]
    error: str | None
    
@dataclass(frozen=True)
class PipelineInputFile:
    """Stored input file plus the payload expected by JobStore.mark_uploaded."""

    stored_file: StoredFile

    @property
    def storage_backend(self) -> str:
        return self.stored_file.backend

    @property
    def input_file_key(self) -> str:
        return self.stored_file.key

    @property
    def input_file_uri(self) -> str:
        return self.stored_file.uri

    def to_job_payload(self) -> dict[str, str]:
        """Return the database payload used to mark a job as uploaded."""

        return {
            "storage_backend": self.storage_backend,
            "input_file_key": self.input_file_key,
            "input_file_uri": self.input_file_uri,
        }

@dataclass(frozen=True)
class PipelineStartResult:
    """Initial response returned after a pipeline job is queued."""

    job_id: int
    run_id: str | None
    status: str
    current_step: str | None
    pipeline_type: PipelineType
    storage_backend: str
    input_file_key: str
    input_file_uri: str

    def to_dict(self) -> dict[str, Any]:
        """Return an API-friendly representation of the start result."""

        return {
            "job_id": self.job_id,
            "run_id": self.run_id,
            "status": self.status,
            "current_step": self.current_step,
            "pipeline_type": self.pipeline_type,
            "storage_backend": self.storage_backend,
            "input_file_key": self.input_file_key,
            "input_file_uri": self.input_file_uri,
        }
