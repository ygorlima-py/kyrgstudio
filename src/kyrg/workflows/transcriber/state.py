from typing import (
                    Literal,
                    Optional,
                    NotRequired,
                   )

from langchain_core.language_models.chat_models import BaseChatModel
from langchain.agents import AgentState
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from kyrg.transcribers.base import TranscriberBase
from kyrg.transcribers import TranscriptionResult
from kyrg.workflows.transcriber.schemas import DomainContextOutput

class TranscriberState(AgentState):
    source_path: str
    source_type: Literal['video', 'audio']
    audio_path: str
    transcriber: type[TranscriberBase]
    model_name: str
    
    language: NotRequired[Optional[str]]
    temperature: NotRequired[float]
    api_key: NotRequired[Optional[str]]
    
    result: NotRequired[TranscriptionResult | None]
    domain_context: NotRequired[DomainContextOutput]
    final_result: NotRequired[TranscriptionResult | None]
    status: NotRequired[str | None]
    human_review_reason: NotRequired[str | None]
    
    