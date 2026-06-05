from typing import TypedDict, Literal, Optional, Any, NotRequired

from langchain.agents import AgentState

from kyrg.transcribers.base import TranscriberBase
from kyrg.transcribers import TranscriptionResult

class TranscriberState(TypedDict):
    source_path: str
    source_type: Literal['video', 'audio']
    audio_path: str
    transcriber: type[TranscriberBase]
    model_name: str
    language: Optional[str]
    temperature: float
    api_key: Optional[str]
    result: TranscriptionResult | None
    domain_context: dict[str, Any]

class TranscriptionAgentState(AgentState):
    result: NotRequired[TranscriptionResult | None]
    domain_context: NotRequired[dict[str, Any]]
    final_result: NotRequired[TranscriptionResult | None]
    status: NotRequired[str]
    human_review_reason: NotRequired[str]
    