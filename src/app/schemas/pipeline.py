from pydantic import BaseModel
from typing import Literal, Any

from kyrg.workflows.copyanalysis import CopyAnalysisOutput
from kyrg.workflows.copyadaptation import UserProfileOutput, AdaptedScriptOutput


class BasePipelineInput(BaseModel):
    source_path: str
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