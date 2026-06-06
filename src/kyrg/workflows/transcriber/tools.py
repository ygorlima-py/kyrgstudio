from langchain_core.tools import tool
from langchain_core.messages import ToolMessage

from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from kyrg.workflows.transcriber.actions import CorrectTranscription
from kyrg.workflows.base import AIActionExecutor

@tool
def correct_transcription_tool(runtime: ToolRuntime) -> Command:
    """Description"""
    state = runtime.state
    context = runtime.context
    
    result = state["result"]
    domain_context = state["domain_context"]
    
    if context is None:
        raise RuntimeError("Transcriber workflow context is required.")
    
    corrector_action = CorrectTranscription(
                                    llm=context.correction_llm,
                                    result=result,
                                    domain_context=domain_context,
                                    )
    
    correction_output = AIActionExecutor.run(corrector_action)

    corrected_result = result.model_copy(deep=True)
    corrected_result.text = correction_output.corrected_text

    segments_by_id = {
        segment.id: segment
        for segment in corrected_result.segments
    }

    for corrected_segment in correction_output.corrected_segments:
        segment = segments_by_id.get(corrected_segment.id)

        if segment is not None:
            segment.text = corrected_segment.text
    
    return Command(
        update={
            "final_result": corrected_result,
            "status": "corrected",
            "human_review_reason": None,
            "messages": [
                ToolMessage(
                    content="Transcription was corrected successfully.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
    
@tool
def request_human_review_tool(reason: str, runtime: ToolRuntime) -> Command:
    """Request human review when the transcription is too uncertain to correct safely."""
    return Command(
        update={
            "status": "needs_human_review",
            "human_review_reason": reason,
            "messages": [
                ToolMessage(
                    content=f"Human review requested: {reason}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )

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
            "human_review_reason": None,
            "messages": [
                ToolMessage(
                    content="The transcription was accepted as final.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
    
    