from dataclasses import dataclass, field
from app.schemas.pipeline import PipelineType
from pathlib import Path

from typing import Any
@dataclass(frozen=True)
class ResolvedInputFile:
    """Local file reference ready to be consumed by the workflow layer."""

    storage_backend: str
    input_file_key: str
    input_file_uri: str
    local_path: Path
    should_cleanup: bool = False
    
@dataclass(frozen=True)
class WorkflowExecutionRequest:
    """Input passed from the runner to the workflow executor."""

    job_id: int
    pipeline_type: PipelineType
    source_path: Path
    source_type: str
    input_json: dict[str, Any]

@dataclass(frozen=True)
class WorkflowExecutionResult:
    """Workflow result normalized enough for the runner to persist it."""

    output_json: dict[str, Any]
    token_usage: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class WorkerRunResult:
    """Small execution summary returned by ``WorkerRunner.run``."""

    job_id: int
    status: str
    pipeline_type: PipelineType
    execution_time_seconds: float
