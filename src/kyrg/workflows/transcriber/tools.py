from kyrg.workflows.core import WorkflowToolRuntime, WorkflowToolMessage, workflow_tool
from kyrg.workflows.workflow_types import WorkFlowCommand
from kyrg.workflows.transcriber.actions import CorrectTranscription
from kyrg.workflows.base import AIActionExecutor

@workflow_tool
def correct_transcription_tool(runtime: WorkflowToolRuntime) -> WorkFlowCommand:
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

    token_usage = corrector_action.tokens_usage

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
    
    return WorkFlowCommand(
        update={
            "final_result": corrected_result,
            "status": "corrected",
            "human_review_reason": None,
            "input_tokens": token_usage["input_tokens"],
            "output_tokens": token_usage["output_tokens"],
            "total_tokens": token_usage["total_tokens"],
            "messages": [
                WorkflowToolMessage(
                    content="Transcription was corrected successfully.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
    
@workflow_tool
def request_human_review_tool(reason: str, runtime: WorkflowToolRuntime) -> WorkFlowCommand:
    """Request human review when the transcription is too uncertain to correct safely."""
    return WorkFlowCommand(
        update={
            "status": "needs_human_review",
            "human_review_reason": reason,
            "messages": [
                WorkflowToolMessage(
                    content=f"Human review requested: {reason}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )

@workflow_tool
def accept_transcription_tool(runtime: WorkflowToolRuntime) -> WorkFlowCommand:
    """Accept the current transcription as the final transcription."""
    state = runtime.state
    result = state["result"]
    
    if result is None:
        raise ValueError("result is required to accept transcription")
    
    return WorkFlowCommand(
        update={
            "final_result": result,
            "status": "accepted",
            "human_review_reason": None,
            "messages": [
                WorkflowToolMessage(
                    content="The transcription was accepted as final.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
    
    