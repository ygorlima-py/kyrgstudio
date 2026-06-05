from langgraph.prebuilt import ToolRuntime
from langchain_core.tools import tool
from langgraph.types import Command

from kyrg.workflows.transcriber.actions import CorrectTranscription

@tool
def correct_transcription_tool(runtime: ToolRuntime) -> Command:
    """Description"""
    ...

@tool
def request_human_review_tool(runtime: ToolRuntime) -> Command:
    """Description"""
    ...

@tool
def accept_transcription_tool(runtime: ToolRuntime) -> Command:
    """Accept the current transcription as the final transcription."""
    state = runtime.state
    result = state["result"]
    
    if result is None:
        raise ValueError("result is required to accept transcription")
    
    return Command(
        update={
            "final_result": result,
            "status": "accepted",
        }
    )
    
    