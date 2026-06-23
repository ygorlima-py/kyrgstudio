from typing import Any
from pydantic import ValidationError
from loguru import logger

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
from kyrg.workflows.errors import _format_validation_errors

def prepare_copy_input(state: CopyAnalysisState) -> dict:
    
    transcription = state.get("transcription")
    
    if transcription is None:
        raise RuntimeError("trancription is required to this workflow")

    text = transcription.text.strip()
    
    if not text:
        raise ValueError("transcription text is required for copy analysis")
    
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
    
    context = runtime.context
    
    if context is None:
        raise RuntimeError("Copy analysis workflow context is required.")
    
    clean_transcript = state.get("clean_transcript")
    
    if not clean_transcript:
        raise ValueError("clean_transcript is required to extract copy structure.")
    
    action = ExtractCopyStructure(
        llm=context.analysis_llm,
        clean_transcript=clean_transcript,
        structured_transcription=state.get("structured_transcription") or [],
        language=state.get("language"),
        validation_error_history=state.get("copy_structure_error_history") or [],
    )
    
    try:
        copy_structure = AIActionExecutor.run(action)
        token_usage = action.tokens_usage
        return {
            "copy_structure": copy_structure,
            "input_tokens": token_usage["input_tokens"],
            "output_tokens": token_usage["output_tokens"],
            "total_tokens": token_usage["total_tokens"],
        }
        
    except ValidationError as error:
        token_usage = action.tokens_usage
        
        formatted_errors = _format_validation_errors(error)
        retry_count = state.get("copy_structure_retry_count", 0) + 1
        
        logger.warning(
                f"Copy structure validation failed: "
                f"attempt={retry_count}, errors={len(formatted_errors)}"
            )
        
        logger.debug(
            f"Copy structure validation details: {formatted_errors}"
        )

        errors_history = [
                *state.get("copy_structure_error_history",[]),
                {
                    "attempt": retry_count,
                    "errors": formatted_errors,
                },
            ]
     
        return {
            "copy_structure_error_history": errors_history,
            "copy_structure_retry_count": retry_count,
            "input_tokens": token_usage["input_tokens"],
            "output_tokens": token_usage["output_tokens"],
            "total_tokens": token_usage["total_tokens"],
        }

def copy_structure_router(
    state: CopyAnalysisState,
    runtime: WorkflowRuntime[CopyAnalysisWorkflowContext],
    ) -> str:
    
    context = runtime.context
    max_retry = context.max_retry_errors
    
    if state.get("copy_structure") is not None:
        return "continue"

    if state.get("copy_structure_retry_count", 0) < max_retry:
        return "retry"

    return "failed"

def extract_offer_elements(
    state: CopyAnalysisState,
    runtime: WorkflowRuntime[CopyAnalysisWorkflowContext],
    ) -> dict:
    
    context = runtime.context
    
    if context is None:
        raise RuntimeError("Copy analysis workflow context is required.")
    
    clean_transcript = state.get("clean_transcript")
    
    if not clean_transcript:
        raise ValueError("clean_transcript is required to extract offer analysis.")

    copy_structure = state.get("copy_structure")
    
    if not copy_structure:
        raise ValueError("copy structure is required to extract offer analysis")
    
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
    runtime: WorkflowRuntime
    ) -> dict:
    context = runtime.context
    
    if context is None:
        raise RuntimeError("Copy analysis workflow context is required.")

    
    copy_structure = state.get("copy_structure")
    
    if not copy_structure:
        raise ValueError("copy structure is required to analyse persuasion")
    
    offer_analysis = state.get("offer_analysis")
    
    if not offer_analysis:
        raise ValueError("Offer structure is required to analyse persuasion")
    
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
    copy_structure = state.get("copy_structure")
    offer_analysis = state.get("offer_analysis")
    persuasion_analysis = state.get("persuasion_analysis")

    if copy_structure is None:
        raise ValueError("copy_structure is required to build copy analysis.")

    if offer_analysis is None:
        raise ValueError("offer_analysis is required to build copy analysis.")

    if persuasion_analysis is None:
        raise ValueError("persuasion_analysis is required to build copy analysis.")

    analysis = CopyAnalysisOutput(
        language=state.get("language"),
        copy_structure=copy_structure,
        offer_analysis=offer_analysis,
        persuasion_analysis=persuasion_analysis,
    )
    
    return {
        "analysis": analysis,
    }
        
        
