"""Workflow nodes that transform transcription input into copy analysis output."""

from kyrg.workflows.copyanalysis.state import CopyAnalysisState
from kyrg.workflows.copyanalysis.schemas import (
    StructuredTranscript,
    CopyAnalysisWorkflowContext,
    CopyAnalysisOutput,
)
from kyrg.workflows.copyanalysis.actions import (
    ExtractCopyStructure,
    ExtractOfferElements,
    AnalysePersuasion,
)
from kyrg.workflows.base import AIActionExecutor
from kyrg.workflows.core import WorkflowRuntime
from kyrg.workflows import guards

# ----- Nodes Sync --------------------
def prepare_copy_input(state: CopyAnalysisState) -> dict:
    """Normalize transcription text and expose timestamped segments for analysis."""
    
    transcription = guards.require_value(
        state.get("transcription"),
        "transcription",
        "prepare copy input",
    )
    
    text = guards.require_non_empty(
        transcription.text.strip(),
        "transcription text",
        "prepare copy input"
    )
    
    clean_transcript = " ".join(text.split())
         
    structured_transcription: list[StructuredTranscript] = [] 
    for segment in transcription.segments:
        structured_transcription.append(
            StructuredTranscript(
                start=segment.start,
                end=segment.end,
                text=segment.text,
            )
        )
    
    return {
        "clean_transcript": clean_transcript,
        "structured_transcription": structured_transcription,
        "language": transcription.language,
    }


def extract_copy_structure(
        state: CopyAnalysisState,
        runtime: WorkflowRuntime[CopyAnalysisWorkflowContext],
    ) -> dict:
    """Run the structural copy analysis step and merge token usage into state."""
    
    context = guards.require_context(
        runtime.context,
        "Copy analysis",
    )
    clean_transcript = guards.require_non_empty(
        state.get("clean_transcript"),
        "clean_transcript",
        "extract copy structure",
    )
    
    action = ExtractCopyStructure(
        llm=context.analysis_llm,
        clean_transcript=clean_transcript,
        structured_transcription=state.get("structured_transcription") or [],
        language=state.get("language"),
    )

    copy_structure = AIActionExecutor.run(action)
    token_usage = action.tokens_usage

    return {
        "copy_structure": copy_structure,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }


def extract_offer_elements(
    state: CopyAnalysisState,
    runtime: WorkflowRuntime[CopyAnalysisWorkflowContext],
    ) -> dict:
    """Run the offer extraction step using the prepared transcript and structure."""
    
    context = guards.require_context(
        runtime.context,
        "Copy analysis",
    )
    clean_transcript = guards.require_non_empty(
        state.get("clean_transcript"),
        "clean_transcript",
        "extract offer analysis",
    )
    copy_structure = guards.require_value(
        state.get("copy_structure"),
        "copy structure",
        "extract offer analysis",
    )
    
    action = ExtractOfferElements(
        llm=context.analysis_llm,
        clean_transcript=clean_transcript,
        copy_structure=copy_structure,
        language=state.get("language")
    )
    
    offer_analysis = AIActionExecutor.run(action)
    token_usage = action.tokens_usage
    
    return {
        "offer_analysis": offer_analysis,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }


def analyse_persuasion(
    state: CopyAnalysisState,
    runtime: WorkflowRuntime[CopyAnalysisWorkflowContext],
    ) -> dict:
    """Run the persuasion diagnosis step from structure and offer analysis."""
    context = guards.require_context(
        runtime.context,
        "Copy analysis",
    )
    copy_structure = guards.require_value(
        state.get("copy_structure"),
        "copy structure",
        "analyse persuasion",
    )
    offer_analysis = guards.require_value(
        state.get("offer_analysis"),
        "Offer structure",
        "analyse persuasion",
    )
    
    action = AnalysePersuasion(
        llm=context.analysis_llm,
        copy_structure=copy_structure,
        offer_analysis=offer_analysis,
        language=state.get("language"),
    )
    
    persuasion_analysis = AIActionExecutor.run(action)
    token_usage = action.tokens_usage

    return {
        "persuasion_analysis": persuasion_analysis,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }

    
def build_copy_analysis(state: CopyAnalysisState) -> dict:
    """Assemble the final copy analysis payload from completed workflow stages."""
    copy_structure = guards.require_value(
        state.get("copy_structure"),
        "copy_structure",
        "build copy analysis",
    )
    offer_analysis = guards.require_value(
        state.get("offer_analysis"),
        "offer_analysis",
        "build copy analysis",
    )
    persuasion_analysis = guards.require_value(
        state.get("persuasion_analysis"),
        "persuasion_analysis",
        "build copy analysis",
    )

    analysis = CopyAnalysisOutput(
        language=state.get("language"),
        copy_structure=copy_structure,
        offer_analysis=offer_analysis,
        persuasion_analysis=persuasion_analysis,
    )
    
    return {
        "analysis": analysis,
    }
    
# ----- Nodes Async --------------------

async def aextract_copy_structure(
        state: CopyAnalysisState,
        runtime: WorkflowRuntime[CopyAnalysisWorkflowContext],
    ) -> dict:
    """Run the structural copy analysis step asynchronously."""
    
    context = guards.require_context(
        runtime.context,
        "Copy analysis",
    )
    clean_transcript = guards.require_non_empty(
        state.get("clean_transcript"),
        "clean_transcript",
        "extract copy structure",
    )
    
    action = ExtractCopyStructure(
        llm=context.analysis_llm,
        clean_transcript=clean_transcript,
        structured_transcription=state.get("structured_transcription") or [],
        language=state.get("language"),
    )

    copy_structure = await AIActionExecutor.arun(action)
    token_usage = action.tokens_usage

    return {
        "copy_structure": copy_structure,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }

async def aextract_offer_elements(
    state: CopyAnalysisState,
    runtime: WorkflowRuntime[CopyAnalysisWorkflowContext],
    ) -> dict:
    """Run the offer extraction step asynchronously."""
    
    context = guards.require_context(
        runtime.context,
        "Copy analysis",
    )
    clean_transcript = guards.require_non_empty(
        state.get("clean_transcript"),
        "clean_transcript",
        "extract offer analysis",
    )
    copy_structure = guards.require_value(
        state.get("copy_structure"),
        "copy structure",
        "extract offer analysis",
    )
    
    action = ExtractOfferElements(
        llm=context.analysis_llm,
        clean_transcript=clean_transcript,
        copy_structure=copy_structure,
        language=state.get("language")
    )
    
    offer_analysis = await AIActionExecutor.run(action)
    token_usage = action.tokens_usage
    
    return {
        "offer_analysis": offer_analysis,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }

async def aanalyse_persuasion(
    state: CopyAnalysisState,
    runtime: WorkflowRuntime[CopyAnalysisWorkflowContext],
    ) -> dict:
    """Run the persuasion diagnosis step asynchronously."""
    context = guards.require_context(
        runtime.context,
        "Copy analysis",
    )
    copy_structure = guards.require_value(
        state.get("copy_structure"),
        "copy structure",
        "analyse persuasion",
    )
    offer_analysis = guards.require_value(
        state.get("offer_analysis"),
        "Offer structure",
        "analyse persuasion",
    )
    
    action = AnalysePersuasion(
        llm=context.analysis_llm,
        copy_structure=copy_structure,
        offer_analysis=offer_analysis,
        language=state.get("language"),
    )
    
    persuasion_analysis = await AIActionExecutor.run(action)
    token_usage = action.tokens_usage

    return {
        "persuasion_analysis": persuasion_analysis,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }
