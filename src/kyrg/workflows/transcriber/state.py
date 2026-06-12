from typing import (
                    Literal,
                    Optional,
                    NotRequired,
                    Annotated,
                   )
from operator import add

from kyrg.workflows.workflow_types import WorkFlowAgentState
from kyrg.transcribers import TranscriptionResult
from kyrg.workflows.transcriber.schemas import DomainContextOutput

class TranscriberState(WorkFlowAgentState):
    source_path: str
    source_type: Literal['video', 'audio']
    audio_path: str
    model_name: str
    input_tokens: NotRequired[Annotated[int, add]]
    output_tokens: NotRequired[Annotated[int, add]]
    total_tokens: NotRequired[Annotated[int, add]]
    
    language: NotRequired[Optional[str]]
    
    result: NotRequired[TranscriptionResult | None]
    domain_context: NotRequired[DomainContextOutput]
    final_result: NotRequired[TranscriptionResult | None]
    status: NotRequired[str | None]
    human_review_reason: NotRequired[str | None]
    
    