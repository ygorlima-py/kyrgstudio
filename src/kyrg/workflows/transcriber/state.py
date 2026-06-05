from typing import (
                    Literal,
                    Optional,
                    Any,
                    NotRequired,
                    Annotated)

from langchain_core.language_models.chat_models import BaseChatModel
from langchain.agents import AgentState
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from kyrg.transcribers.base import TranscriberBase
from kyrg.transcribers import TranscriptionResult

class TranscriberState(AgentState):
    messages: Annotated[list[AnyMessage], add_messages]
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
    quality_llm: BaseChatModel
    status: str | None
    human_review_reason: str | None
    
    