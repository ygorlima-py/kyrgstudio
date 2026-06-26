from typing import Any

from kyrg.workflows.copyadaptation.state import CopyAdaptationState
from kyrg.workflows.copyadaptation.actions import (
    BuildCopyStrategy,
    CorrectScriptSections,
    CorrectValidatedScript,
    ReviewAction,
    ValidateScriptAction,
    WriteScriptSection,
)
from kyrg.workflows.copyadaptation.schemas import (
    AdaptedScriptOutput,
    CopyAdaptationWorkflowContext,
)
from kyrg.workflows.guards import require_context, require_non_empty, require_value
from kyrg.workflows.base import AIActionExecutor
from kyrg.workflows.core import WorkflowRuntime
from kyrg.workflows.copyadaptation._utils import (
    _add_words_count_per_section,
    _resolve_final_sections,
    _calculate_time_estimated,
    _BuildScriptOutput,
)

from kyrg.workflows.copyadaptation._preparation import _build_adaptation_input
from kyrg.workflows.copyadaptation.constants import SECTION_ADAPTATION_FIELDS

# ----- Nodes Sync --------------------
def prepare_adaptation_input(state: CopyAdaptationState) -> dict[str, Any]:
    copy_analysis = require_value(
        state.get("copy_analysis"),
        "copy_analysis",
        "prepare adaptation input",
    )
    user_profile = require_value(
        state.get("user_profile"),
        "user_profile",
        "prepare adaptation input",
    )

    return _build_adaptation_input(copy_analysis, user_profile)

def build_copy_strategy(
    state: CopyAdaptationState,
    runtime: WorkflowRuntime[CopyAdaptationWorkflowContext],
) -> dict:
    context = require_context(runtime.context, "Copy adaptation")
    copy_analysis = require_value(
        state.get("copy_analysis"),
        "copy_analysis",
        "build copy strategy",
    )
    user_profile = require_value(
        state.get("user_profile"),
        "user_profile",
        "build copy strategy",
    )
    target_language = require_value(
        state.get("target_language"),
        "target_language",
        "build copy strategy",
    )
    platform = require_value(
        state.get("platform"),
        "platform",
        "build copy strategy",
    )

    action = BuildCopyStrategy(
        llm=context.strategy_llm,
        copy_analysis=copy_analysis,
        user_profile=user_profile,
        mapped_sections=state.get("mapped_sections") or [],
        sections_to_create=state.get("sections_to_create") or [],
        gaps_to_fix=state.get("gaps_to_fix") or [],
        target_language=target_language,
        platform=platform,
        desired_duration=state.get("desired_duration"),
    )

    strategy = AIActionExecutor.run(action)
    token_usage = action.tokens_usage

    return {
        "main_angle": strategy.main_angle,
        "awareness_level": strategy.awareness_level,
        "main_promise": strategy.main_promise,
        "persuasion_pattern": strategy.persuasion_pattern,
        "objections_to_address": strategy.objections_to_address,
        "proof_plan": strategy.proof_plan,
        "unique_mechanism": strategy.unique_mechanism,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }

def write_script_sections(
    state: CopyAdaptationState,
    runtime: WorkflowRuntime[CopyAdaptationWorkflowContext],
) -> dict:
    context = require_context(runtime.context, "Copy adaptation")
    user_profile = require_value(
        state.get("user_profile"),
        "user_profile",
        "write script sections",
    )
    target_language = require_value(
        state.get("target_language"),
        "target_language",
        "write script sections",
    )
    platform = require_value(
        state.get("platform"),
        "platform",
        "write script sections",
    )
    main_angle = require_value(
        state.get("main_angle"),
        "main_angle",
        "write script sections",
    )
    awareness_level = require_value(
        state.get("awareness_level"),
        "awareness_level",
        "write script sections",
    )
    main_promise = require_value(
        state.get("main_promise"),
        "main_promise",
        "write script sections",
    )
    persuasion_pattern = require_value(
        state.get("persuasion_pattern"),
        "persuasion_pattern",
        "write script sections",
    )
    unique_mechanism = require_value(
        state.get("unique_mechanism"),
        "unique_mechanism",
        "write script sections",
    )

    action = WriteScriptSection(
        llm=context.writing_llm,
        user_profile=user_profile,
        mapped_sections=state.get("mapped_sections") or [],
        sections_to_create=state.get("sections_to_create") or [],
        gaps_to_fix=state.get("gaps_to_fix") or [],
        target_language=target_language,
        platform=platform,
        desired_duration=state.get("desired_duration"),
        main_angle=main_angle,
        awareness_level=awareness_level,
        main_promise=main_promise,
        persuasion_pattern=persuasion_pattern,
        objections_to_address=state.get("objections_to_address") or [],
        proof_plan=state.get("proof_plan") or {},
        unique_mechanism=unique_mechanism,
    )

    script_sections = AIActionExecutor.run(action)
    token_usage = action.tokens_usage
    sections = _add_words_count_per_section(script_sections)
    
    word_count = sum(
        section["word_count"]
        for section in sections
    )
    
    return {
        "sections": sections,
        "missing_proofs": script_sections.missing_proofs,
        "adaptation_notes": script_sections.adaptation_notes,
        "word_count": word_count,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }

def review_section_flow(
    state: CopyAdaptationState,
    runtime: WorkflowRuntime[CopyAdaptationWorkflowContext],
) -> dict:
    context = require_context(runtime.context, "Copy adaptation")
    sections = require_non_empty(
        state.get("sections"),
        "sections",
        "review section flow",
    )
    target_language = require_value(
        state.get("target_language"),
        "target_language",
        "review section flow",
    )
    platform = require_value(
        state.get("platform"),
        "platform",
        "review section flow",
    )
    main_angle = require_value(
        state.get("main_angle"),
        "main_angle",
        "review section flow",
    )
    awareness_level = require_value(
        state.get("awareness_level"),
        "awareness_level",
        "review section flow",
    )
    main_promise = require_value(
        state.get("main_promise"),
        "main_promise",
        "review section flow",
    )
    persuasion_pattern = require_value(
        state.get("persuasion_pattern"),
        "persuasion_pattern",
        "review section flow",
    )
    unique_mechanism = require_value(
        state.get("unique_mechanism"),
        "unique_mechanism",
        "review section flow",
    )

    action = ReviewAction(
        llm=context.review_llm,
        sections=sections,
        missing_proofs=state.get("missing_proofs") or [],
        target_language=target_language,
        platform=platform,
        desired_duration=state.get("desired_duration"),
        main_angle=main_angle,
        awareness_level=awareness_level,
        main_promise=main_promise,
        persuasion_pattern=persuasion_pattern,
        objections_to_address=state.get("objections_to_address") or [],
        proof_plan=state.get("proof_plan") or {},
        unique_mechanism=unique_mechanism,
    )

    review = AIActionExecutor.run(action)
    token_usage = action.tokens_usage

    output = {
        "flow_approved": review.flow_approved,
        "flow_issues": review.flow_issues,
        "revision_instructions": [
            instruction.model_dump()
            for instruction in review.revision_instructions
        ],
        "sections_revised": [
            section.model_dump()
            for section in review.sections_revised
        ],
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }

    return output

def primary_route(
    state: CopyAdaptationState,
    runtime: WorkflowRuntime[CopyAdaptationWorkflowContext]
    ):
    context = runtime.context
    
    max_retry = context.max_retry
    
    flow_approved = state.get('flow_approved')
    retry_count = state.get("retry_count_correction_section", 0)
    
    if not flow_approved:  
        if retry_count < max_retry:
            
            return "retry"
        return "continue"
    
    return "continue"

def secondary_route(
    state: CopyAdaptationState,
    runtime: WorkflowRuntime[CopyAdaptationWorkflowContext],
    ):
    context = runtime.context
    max_retry = context.max_retry
    
    validation_passed = state.get('validation_passed')
    retry_count = state.get("retry_count_correction_script", 0)
    
    if not validation_passed:  
        if retry_count < max_retry:
            
            return "retry"
        return "continue"
    
    return "continue"

def correct_section(
    state: CopyAdaptationState,
    runtime: WorkflowRuntime[CopyAdaptationWorkflowContext],
) -> dict:
    context = require_context(runtime.context, "Copy adaptation")
    user_profile = require_value(
        state.get("user_profile"),
        "user_profile",
        "correct script sections",
    )

    previous_sections = _resolve_final_sections(state)

    flow_issues = require_non_empty(
        state.get("flow_issues"),
        "flow_issues",
        "correct script sections",
    )
    revision_instructions = require_non_empty(
        state.get("revision_instructions"),
        "revision_instructions",
        "correct script sections",
    )
    target_language = require_value(
        state.get("target_language"),
        "target_language",
        "correct script sections",
    )
    platform = require_value(
        state.get("platform"),
        "platform",
        "correct script sections",
    )
    main_angle = require_value(
        state.get("main_angle"),
        "main_angle",
        "correct script sections",
    )
    awareness_level = require_value(
        state.get("awareness_level"),
        "awareness_level",
        "correct script sections",
    )
    main_promise = require_value(
        state.get("main_promise"),
        "main_promise",
        "correct script sections",
    )
    persuasion_pattern = require_value(
        state.get("persuasion_pattern"),
        "persuasion_pattern",
        "correct script sections",
    )
    unique_mechanism = require_value(
        state.get("unique_mechanism"),
        "unique_mechanism",
        "correct script sections",
    )

    action = CorrectScriptSections(
        llm=context.writing_llm,
        user_profile=user_profile,
        previous_sections=previous_sections,
        flow_issues=flow_issues,
        revision_instructions=revision_instructions,
        missing_proofs=state.get("missing_proofs") or [],
        target_language=target_language,
        platform=platform,
        desired_duration=state.get("desired_duration"),
        main_angle=main_angle,
        awareness_level=awareness_level,
        main_promise=main_promise,
        persuasion_pattern=persuasion_pattern,
        objections_to_address=state.get("objections_to_address") or [],
        proof_plan=state.get("proof_plan") or {},
        unique_mechanism=unique_mechanism,
        retry_count=state.get("retry_count_correction_section", 0),
    )

    corrected_sections = AIActionExecutor.run(action)
    token_usage = action.tokens_usage
    sections = _add_words_count_per_section(corrected_sections)
    
    word_count = sum(
        section["word_count"]
        for section in sections
    )
    
    return {
        "sections": sections,
        "missing_proofs": corrected_sections.missing_proofs,
        "adaptation_notes": corrected_sections.adaptation_notes,
        "word_count": word_count,
        "sections_revised": [],
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
        "retry_count_correction_section": state.get("retry_count_correction_section", 0) + 1,
    }

def validate_script(
    state: CopyAdaptationState,
    runtime: WorkflowRuntime[CopyAdaptationWorkflowContext],
) -> dict:
    context = require_context(runtime.context, "Copy adaptation")
    user_profile = require_value(
        state.get("user_profile"),
        "user_profile",
        "validate script",
    )

    sections = _resolve_final_sections(state)

    target_language = require_value(
        state.get("target_language"),
        "target_language",
        "validate script",
    )
    platform = require_value(
        state.get("platform"),
        "platform",
        "validate script",
    )
    main_angle = require_value(
        state.get("main_angle"),
        "main_angle",
        "validate script",
    )
    main_promise = require_value(
        state.get("main_promise"),
        "main_promise",
        "validate script",
    )
    unique_mechanism = require_value(
        state.get("unique_mechanism"),
        "unique_mechanism",
        "validate script",
    )

    timing_metrics = _calculate_time_estimated(state)
    
    action = ValidateScriptAction(
        llm=context.validation_llm,
        user_profile=user_profile,
        mapped_sections=state.get("mapped_sections") or [],
        sections=sections,
        missing_proofs=state.get("missing_proofs") or [],
        target_language=target_language,
        platform=platform,
        desired_duration=state.get("desired_duration"),
        main_angle=main_angle,
        main_promise=main_promise,
        unique_mechanism=unique_mechanism,
        proof_plan=state.get("proof_plan") or {},
        timing_metrics=timing_metrics,
    )

    validation = AIActionExecutor.run(action)
    token_usage = action.tokens_usage
    
    output = {
            "validation_passed": validation.validation_passed,
            "validation_errors": [
                issue.model_dump()
                for issue in validation.validation_errors
            ],
            "validation_warnings": [
                issue.model_dump()
                for issue in validation.validation_warnings
            ],
            "timing_metrics": timing_metrics,
            "input_tokens": token_usage["input_tokens"],
            "output_tokens": token_usage["output_tokens"],
            "total_tokens": token_usage["total_tokens"],
    }

    return output

def correct_script(
    state: CopyAdaptationState,
    runtime: WorkflowRuntime[CopyAdaptationWorkflowContext]
    ) -> dict:
    context = require_context(runtime.context, "Copy adaptation")
    user_profile = require_value(
        state.get("user_profile"),
        "user_profile",
        "correct validated script",
    )
    sections = require_non_empty(
        _resolve_final_sections(state),
        "sections",
        "correct validated script",
    )
    validation_errors = require_non_empty(
        state.get("validation_errors"),
        "validation_errors",
        "correct validated script",
    )
    target_language = require_value(
        state.get("target_language"),
        "target_language",
        "correct validated script",
    )
    platform = require_value(
        state.get("platform"),
        "platform",
        "correct validated script",
    )
    main_angle = require_value(
        state.get("main_angle"),
        "main_angle",
        "correct validated script",
    )
    main_promise = require_value(
        state.get("main_promise"),
        "main_promise",
        "correct validated script",
    )
    unique_mechanism = require_value(
        state.get("unique_mechanism"),
        "unique_mechanism",
        "correct validated script",
    )

    timing_metrics = state.get("timing_metrics") or _calculate_time_estimated(state)

    action = CorrectValidatedScript(
        llm=context.writing_llm,
        user_profile=user_profile,
        sections=sections,
        validation_errors=validation_errors,
        validation_warnings=state.get("validation_warnings") or [],
        timing_metrics=timing_metrics,
        missing_proofs=state.get("missing_proofs") or [],
        target_language=target_language,
        platform=platform,
        desired_duration=state.get("desired_duration"),
        main_angle=main_angle,
        main_promise=main_promise,
        proof_plan=state.get("proof_plan") or {},
        unique_mechanism=unique_mechanism,
        retry_count=state.get("retry_count_correction_script", 0),
    )

    corrected_script = AIActionExecutor.run(action)
    token_usage = action.tokens_usage
    corrected_sections = _add_words_count_per_section(corrected_script)

    word_count = sum(section["word_count"] for section in corrected_sections)

    return {
        "sections": corrected_sections,
        "sections_before_script_correction": sections,
        "sections_after_script_correction": corrected_sections,
        "sections_revised": [],
        "missing_proofs": corrected_script.missing_proofs,
        "adaptation_notes": corrected_script.adaptation_notes,
        "word_count": word_count,
        "retry_count_correction_script": state.get("retry_count_correction_script", 0) + 1,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }
    
def build_script_output(state: CopyAdaptationState) -> dict:
    script_output = _BuildScriptOutput(state)

    final_sections = script_output._final_sections()

    script = script_output._script()
    
    voice_ready_text = script_output._voice_ready_text()
    timing_metrics = _calculate_time_estimated(state)
    word_count = timing_metrics["word_count"]
    estimated_duration_seconds = timing_metrics["estimated_duration_seconds"]

    hooks = script_output._hooks()
    
    cta_sections = script_output._cta_sections()
    cta = cta_sections[-1] if cta_sections else None

    adapted_script = AdaptedScriptOutput(
        script=script,
        sections=final_sections,
        hooks=hooks,
        cta=cta,
        estimated_duration_seconds=estimated_duration_seconds,
        word_count=word_count,
        voice_ready_text=voice_ready_text,
        adaptation_notes=state.get("adaptation_notes"),
        validation_warnings=script_output._validation_warnings_from_state,
        validation_errors=script_output._validation_issues_from_state,
        validation_passed=state.get("validation_passed", False),
        missing_proofs=state.get("missing_proofs") or [],
    )   

    return {
        "adapted_script": adapted_script.model_dump(),
    }

# ----- Nodes Async --------------------
async def abuild_copy_strategy(
    state: CopyAdaptationState,
    runtime: WorkflowRuntime[CopyAdaptationWorkflowContext],
) -> dict:
    context = require_context(runtime.context, "Copy adaptation")
    copy_analysis = require_value(
        state.get("copy_analysis"),
        "copy_analysis",
        "build copy strategy",
    )
    user_profile = require_value(
        state.get("user_profile"),
        "user_profile",
        "build copy strategy",
    )
    target_language = require_value(
        state.get("target_language"),
        "target_language",
        "build copy strategy",
    )
    platform = require_value(
        state.get("platform"),
        "platform",
        "build copy strategy",
    )

    action = BuildCopyStrategy(
        llm=context.strategy_llm,
        copy_analysis=copy_analysis,
        user_profile=user_profile,
        mapped_sections=state.get("mapped_sections") or [],
        sections_to_create=state.get("sections_to_create") or [],
        gaps_to_fix=state.get("gaps_to_fix") or [],
        target_language=target_language,
        platform=platform,
        desired_duration=state.get("desired_duration"),
    )

    strategy = await AIActionExecutor.arun(action)
    token_usage = action.tokens_usage

    return {
        "main_angle": strategy.main_angle,
        "awareness_level": strategy.awareness_level,
        "main_promise": strategy.main_promise,
        "persuasion_pattern": strategy.persuasion_pattern,
        "objections_to_address": strategy.objections_to_address,
        "proof_plan": strategy.proof_plan,
        "unique_mechanism": strategy.unique_mechanism,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }

async def awrite_script_sections(
    state: CopyAdaptationState,
    runtime: WorkflowRuntime[CopyAdaptationWorkflowContext],
) -> dict:
    context = require_context(runtime.context, "Copy adaptation")
    user_profile = require_value(
        state.get("user_profile"),
        "user_profile",
        "write script sections",
    )
    target_language = require_value(
        state.get("target_language"),
        "target_language",
        "write script sections",
    )
    platform = require_value(
        state.get("platform"),
        "platform",
        "write script sections",
    )
    main_angle = require_value(
        state.get("main_angle"),
        "main_angle",
        "write script sections",
    )
    awareness_level = require_value(
        state.get("awareness_level"),
        "awareness_level",
        "write script sections",
    )
    main_promise = require_value(
        state.get("main_promise"),
        "main_promise",
        "write script sections",
    )
    persuasion_pattern = require_value(
        state.get("persuasion_pattern"),
        "persuasion_pattern",
        "write script sections",
    )
    unique_mechanism = require_value(
        state.get("unique_mechanism"),
        "unique_mechanism",
        "write script sections",
    )

    action = WriteScriptSection(
        llm=context.writing_llm,
        user_profile=user_profile,
        mapped_sections=state.get("mapped_sections") or [],
        sections_to_create=state.get("sections_to_create") or [],
        gaps_to_fix=state.get("gaps_to_fix") or [],
        target_language=target_language,
        platform=platform,
        desired_duration=state.get("desired_duration"),
        main_angle=main_angle,
        awareness_level=awareness_level,
        main_promise=main_promise,
        persuasion_pattern=persuasion_pattern,
        objections_to_address=state.get("objections_to_address") or [],
        proof_plan=state.get("proof_plan") or {},
        unique_mechanism=unique_mechanism,
    )

    script_sections = await AIActionExecutor.arun(action)
    token_usage = action.tokens_usage
    sections = _add_words_count_per_section(script_sections)
    
    word_count = sum(
        section["word_count"]
        for section in sections
    )
    
    return {
        "sections": sections,
        "missing_proofs": script_sections.missing_proofs,
        "adaptation_notes": script_sections.adaptation_notes,
        "word_count": word_count,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }

async def areview_section_flow(
    state: CopyAdaptationState,
    runtime: WorkflowRuntime[CopyAdaptationWorkflowContext],
) -> dict:
    context = require_context(runtime.context, "Copy adaptation")
    sections = require_non_empty(
        state.get("sections"),
        "sections",
        "review section flow",
    )
    target_language = require_value(
        state.get("target_language"),
        "target_language",
        "review section flow",
    )
    platform = require_value(
        state.get("platform"),
        "platform",
        "review section flow",
    )
    main_angle = require_value(
        state.get("main_angle"),
        "main_angle",
        "review section flow",
    )
    awareness_level = require_value(
        state.get("awareness_level"),
        "awareness_level",
        "review section flow",
    )
    main_promise = require_value(
        state.get("main_promise"),
        "main_promise",
        "review section flow",
    )
    persuasion_pattern = require_value(
        state.get("persuasion_pattern"),
        "persuasion_pattern",
        "review section flow",
    )
    unique_mechanism = require_value(
        state.get("unique_mechanism"),
        "unique_mechanism",
        "review section flow",
    )

    action = ReviewAction(
        llm=context.review_llm,
        sections=sections,
        missing_proofs=state.get("missing_proofs") or [],
        target_language=target_language,
        platform=platform,
        desired_duration=state.get("desired_duration"),
        main_angle=main_angle,
        awareness_level=awareness_level,
        main_promise=main_promise,
        persuasion_pattern=persuasion_pattern,
        objections_to_address=state.get("objections_to_address") or [],
        proof_plan=state.get("proof_plan") or {},
        unique_mechanism=unique_mechanism,
    )

    review = await AIActionExecutor.arun(action)
    token_usage = action.tokens_usage

    output = {
        "flow_approved": review.flow_approved,
        "flow_issues": review.flow_issues,
        "revision_instructions": [
            instruction.model_dump()
            for instruction in review.revision_instructions
        ],
        "sections_revised": [
            section.model_dump()
            for section in review.sections_revised
        ],
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }

    return output

async def acorrect_section(
    state: CopyAdaptationState,
    runtime: WorkflowRuntime[CopyAdaptationWorkflowContext],
) -> dict:
    context = require_context(runtime.context, "Copy adaptation")
    user_profile = require_value(
        state.get("user_profile"),
        "user_profile",
        "correct script sections",
    )

    previous_sections = _resolve_final_sections(state)

    flow_issues = require_non_empty(
        state.get("flow_issues"),
        "flow_issues",
        "correct script sections",
    )
    revision_instructions = require_non_empty(
        state.get("revision_instructions"),
        "revision_instructions",
        "correct script sections",
    )
    target_language = require_value(
        state.get("target_language"),
        "target_language",
        "correct script sections",
    )
    platform = require_value(
        state.get("platform"),
        "platform",
        "correct script sections",
    )
    main_angle = require_value(
        state.get("main_angle"),
        "main_angle",
        "correct script sections",
    )
    awareness_level = require_value(
        state.get("awareness_level"),
        "awareness_level",
        "correct script sections",
    )
    main_promise = require_value(
        state.get("main_promise"),
        "main_promise",
        "correct script sections",
    )
    persuasion_pattern = require_value(
        state.get("persuasion_pattern"),
        "persuasion_pattern",
        "correct script sections",
    )
    unique_mechanism = require_value(
        state.get("unique_mechanism"),
        "unique_mechanism",
        "correct script sections",
    )

    action = CorrectScriptSections(
        llm=context.writing_llm,
        user_profile=user_profile,
        previous_sections=previous_sections,
        flow_issues=flow_issues,
        revision_instructions=revision_instructions,
        missing_proofs=state.get("missing_proofs") or [],
        target_language=target_language,
        platform=platform,
        desired_duration=state.get("desired_duration"),
        main_angle=main_angle,
        awareness_level=awareness_level,
        main_promise=main_promise,
        persuasion_pattern=persuasion_pattern,
        objections_to_address=state.get("objections_to_address") or [],
        proof_plan=state.get("proof_plan") or {},
        unique_mechanism=unique_mechanism,
        retry_count=state.get("retry_count_correction_section", 0),
    )

    corrected_sections = await AIActionExecutor.arun(action)
    token_usage = action.tokens_usage
    sections = _add_words_count_per_section(corrected_sections)
    
    word_count = sum(
        section["word_count"]
        for section in sections
    )
    
    return {
        "sections": sections,
        "missing_proofs": corrected_sections.missing_proofs,
        "adaptation_notes": corrected_sections.adaptation_notes,
        "word_count": word_count,
        "sections_revised": [],
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
        "retry_count_correction_section": state.get("retry_count_correction_section", 0) + 1,
    }

async def avalidate_script(
    state: CopyAdaptationState,
    runtime: WorkflowRuntime[CopyAdaptationWorkflowContext],
) -> dict:
    context = require_context(runtime.context, "Copy adaptation")
    user_profile = require_value(
        state.get("user_profile"),
        "user_profile",
        "validate script",
    )

    sections = _resolve_final_sections(state)

    target_language = require_value(
        state.get("target_language"),
        "target_language",
        "validate script",
    )
    platform = require_value(
        state.get("platform"),
        "platform",
        "validate script",
    )
    main_angle = require_value(
        state.get("main_angle"),
        "main_angle",
        "validate script",
    )
    main_promise = require_value(
        state.get("main_promise"),
        "main_promise",
        "validate script",
    )
    unique_mechanism = require_value(
        state.get("unique_mechanism"),
        "unique_mechanism",
        "validate script",
    )

    timing_metrics = _calculate_time_estimated(state)
    
    action = ValidateScriptAction(
        llm=context.validation_llm,
        user_profile=user_profile,
        mapped_sections=state.get("mapped_sections") or [],
        sections=sections,
        missing_proofs=state.get("missing_proofs") or [],
        target_language=target_language,
        platform=platform,
        desired_duration=state.get("desired_duration"),
        main_angle=main_angle,
        main_promise=main_promise,
        unique_mechanism=unique_mechanism,
        proof_plan=state.get("proof_plan") or {},
        timing_metrics=timing_metrics,
    )

    validation = await AIActionExecutor.arun(action)
    token_usage = action.tokens_usage
    
    output = {
            "validation_passed": validation.validation_passed,
            "validation_errors": [
                issue.model_dump()
                for issue in validation.validation_errors
            ],
            "validation_warnings": [
                issue.model_dump()
                for issue in validation.validation_warnings
            ],
            "timing_metrics": timing_metrics,
            "input_tokens": token_usage["input_tokens"],
            "output_tokens": token_usage["output_tokens"],
            "total_tokens": token_usage["total_tokens"],
    }

    return output

async def acorrect_script(
        state: CopyAdaptationState,
        runtime: WorkflowRuntime[CopyAdaptationWorkflowContext]
        ) -> dict:
        context = require_context(runtime.context, "Copy adaptation")
        user_profile = require_value(
            state.get("user_profile"),
            "user_profile",
            "correct validated script",
        )
        sections = require_non_empty(
            _resolve_final_sections(state),
            "sections",
            "correct validated script",
        )
        validation_errors = require_non_empty(
            state.get("validation_errors"),
            "validation_errors",
            "correct validated script",
        )
        target_language = require_value(
            state.get("target_language"),
            "target_language",
            "correct validated script",
        )
        platform = require_value(
            state.get("platform"),
            "platform",
            "correct validated script",
        )
        main_angle = require_value(
            state.get("main_angle"),
            "main_angle",
            "correct validated script",
        )
        main_promise = require_value(
            state.get("main_promise"),
            "main_promise",
            "correct validated script",
        )
        unique_mechanism = require_value(
            state.get("unique_mechanism"),
            "unique_mechanism",
            "correct validated script",
        )

        timing_metrics = state.get("timing_metrics") or _calculate_time_estimated(state)

        action = CorrectValidatedScript(
            llm=context.writing_llm,
            user_profile=user_profile,
            sections=sections,
            validation_errors=validation_errors,
            validation_warnings=state.get("validation_warnings") or [],
            timing_metrics=timing_metrics,
            missing_proofs=state.get("missing_proofs") or [],
            target_language=target_language,
            platform=platform,
            desired_duration=state.get("desired_duration"),
            main_angle=main_angle,
            main_promise=main_promise,
            proof_plan=state.get("proof_plan") or {},
            unique_mechanism=unique_mechanism,
            retry_count=state.get("retry_count_correction_script", 0),
        )

        corrected_script = await AIActionExecutor.arun(action)
        token_usage = action.tokens_usage
        corrected_sections = _add_words_count_per_section(corrected_script)

        word_count = sum(section["word_count"] for section in corrected_sections)

        return {
            "sections": corrected_sections,
            "sections_before_script_correction": sections,
            "sections_after_script_correction": corrected_sections,
            "sections_revised": [],
            "missing_proofs": corrected_script.missing_proofs,
            "adaptation_notes": corrected_script.adaptation_notes,
            "word_count": word_count,
            "retry_count_correction_script": state.get("retry_count_correction_script", 0) + 1,
            "input_tokens": token_usage["input_tokens"],
            "output_tokens": token_usage["output_tokens"],
            "total_tokens": token_usage["total_tokens"],
        }
        