from kyrg.workflows.base import AgentBase
from kyrg.workflows.transcriber.state import TranscriberState
from kyrg.workflows.transcriber.prompts import TranscriptionPrompts

class TranscriptionAgent(AgentBase):
    NAME = "transcription_quality_agent"
    PROMPT = TranscriptionPrompts.QUALITY_AGENT
    STATE_SCHEMA = TranscriberState
    
    
    
