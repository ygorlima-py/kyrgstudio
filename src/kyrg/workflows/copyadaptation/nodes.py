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
from kyrg.workflows.base import AIActionExecutor
from kyrg.workflows.core import WorkflowRuntime
from kyrg.workflows.copyadaptation._utils import (
    _add_words_count_per_section,
    _resolve_final_sections,
    _calculate_time_estimated,
    _BuildScriptOutput,
)
from kyrg.workflows.copyadaptation.constants import SECTION_ADAPTATION_FIELDS


def prepare_adaptation_input(state: CopyAdaptationState) -> dict:
    copy_analysis = state.get("copy_analysis")

    if copy_analysis is None:
        raise ValueError("copy_analysis is required to prepare adaptation input")

    user_profile = state.get("user_profile")

    if user_profile is None:
        raise ValueError("user_profile is required to prepare adaptation input")

    target_language = (
        user_profile.target_language
        or copy_analysis.language
        or copy_analysis.copy_structure.language
    )

    if target_language is None:
        raise ValueError("target_language is required to prepare adaptation input")

    mapped_sections = []

    for section in copy_analysis.copy_structure.sections:
        section_type = section.section_type.strip().lower()
        adaptation_fields = SECTION_ADAPTATION_FIELDS.get(
            section_type,
            ["product_or_solution", "target_audience", "main_promise"],
        )

        mapped_sections.append(
            {
                "reference_section_type": section.section_type,
                "reference_text": section.text,
                "reference_purpose": section.purpose,
                "start": section.start,
                "end": section.end,
                "has_direct_equivalent": section_type in SECTION_ADAPTATION_FIELDS,
                "user_profile_fields": adaptation_fields,
            }
        )

    sections_to_create = list(copy_analysis.copy_structure.missing_sections)
    gaps_to_fix = []

    persuasion_analysis = copy_analysis.persuasion_analysis
    strength_fields = {
        "hook_strength": persuasion_analysis.hook_strength,
        "promise_clarity": persuasion_analysis.promise_clarity,
        "proof_strength": persuasion_analysis.proof_strength,
        "urgency_strength": persuasion_analysis.urgency_strength,
        "cta_strength": persuasion_analysis.cta_strength,
    }

    for field_name, strength in strength_fields.items():
        if strength == "low":
            gaps_to_fix.append(f"Low persuasion score: {field_name}")

    for weakness in persuasion_analysis.weaknesses:
        gaps_to_fix.append(weakness.issue)

    if not user_profile.proof_assets:
        gaps_to_fix.append("User profile has no proof assets available")

    if user_profile.unique_mechanism is None:
        gaps_to_fix.append("User profile has no unique mechanism defined")

    output = {
        "mapped_sections": mapped_sections,
        "sections_to_create": sections_to_create,
        "gaps_to_fix": gaps_to_fix,
        "target_language": target_language,
        "platform": user_profile.platform or "generic",
    }

    if user_profile.desired_duration is not None:
        output["desired_duration"] = user_profile.desired_duration

    return output

def build_copy_strategy(
    state: CopyAdaptationState,
    runtime: WorkflowRuntime[CopyAdaptationWorkflowContext],
) -> dict:
    context = runtime.context

    if context is None:
        raise RuntimeError("Copy adaptation workflow context is required.")

    copy_analysis = state.get("copy_analysis")

    if copy_analysis is None:
        raise ValueError("copy_analysis is required to build copy strategy")

    user_profile = state.get("user_profile")

    if user_profile is None:
        raise ValueError("user_profile is required to build copy strategy")

    target_language = state.get("target_language")

    if target_language is None:
        raise ValueError("target_language is required to build copy strategy")

    platform = state.get("platform")

    if platform is None:
        raise ValueError("platform is required to build copy strategy")

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
    context = runtime.context

    if context is None:
        raise RuntimeError("Copy adaptation workflow context is required.")

    user_profile = state.get("user_profile")

    if user_profile is None:
        raise ValueError("user_profile is required to write script sections")

    target_language = state.get("target_language")

    if target_language is None:
        raise ValueError("target_language is required to write script sections")

    platform = state.get("platform")

    if platform is None:
        raise ValueError("platform is required to write script sections")

    main_angle = state.get("main_angle")

    if main_angle is None:
        raise ValueError("main_angle is required to write script sections")

    awareness_level = state.get("awareness_level")

    if awareness_level is None:
        raise ValueError("awareness_level is required to write script sections")

    main_promise = state.get("main_promise")

    if main_promise is None:
        raise ValueError("main_promise is required to write script sections")

    persuasion_pattern = state.get("persuasion_pattern")

    if persuasion_pattern is None:
        raise ValueError("persuasion_pattern is required to write script sections")

    unique_mechanism = state.get("unique_mechanism")

    if unique_mechanism is None:
        raise ValueError("unique_mechanism is required to write script sections")

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
    context = runtime.context

    if context is None:
        raise RuntimeError("Copy adaptation workflow context is required.")

    sections = state.get("sections")

    if not sections:
        raise ValueError("sections is required to review section flow")

    target_language = state.get("target_language")

    if target_language is None:
        raise ValueError("target_language is required to review section flow")

    platform = state.get("platform")

    if platform is None:
        raise ValueError("platform is required to review section flow")

    main_angle = state.get("main_angle")

    if main_angle is None:
        raise ValueError("main_angle is required to review section flow")

    awareness_level = state.get("awareness_level")

    if awareness_level is None:
        raise ValueError("awareness_level is required to review section flow")

    main_promise = state.get("main_promise")

    if main_promise is None:
        raise ValueError("main_promise is required to review section flow")

    persuasion_pattern = state.get("persuasion_pattern")

    if persuasion_pattern is None:
        raise ValueError("persuasion_pattern is required to review section flow")

    unique_mechanism = state.get("unique_mechanism")

    if unique_mechanism is None:
        raise ValueError("unique_mechanism is required to review section flow")

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
    context = runtime.context

    if context is None:
        raise RuntimeError("Copy adaptation workflow context is required.")

    user_profile = state.get("user_profile")

    if user_profile is None:
        raise ValueError("user_profile is required to correct script sections")

    previous_sections = state.get("sections")

    if not previous_sections:
        raise ValueError("sections is required to correct script sections")

    flow_issues = state.get("flow_issues")

    if not flow_issues:
        raise ValueError("flow_issues is required to correct script sections")

    revision_instructions = state.get("revision_instructions")

    if not revision_instructions:
        raise ValueError("revision_instructions is required to correct script sections")

    target_language = state.get("target_language")

    if target_language is None:
        raise ValueError("target_language is required to correct script sections")

    platform = state.get("platform")

    if platform is None:
        raise ValueError("platform is required to correct script sections")

    main_angle = state.get("main_angle")

    if main_angle is None:
        raise ValueError("main_angle is required to correct script sections")

    awareness_level = state.get("awareness_level")

    if awareness_level is None:
        raise ValueError("awareness_level is required to correct script sections")

    main_promise = state.get("main_promise")

    if main_promise is None:
        raise ValueError("main_promise is required to correct script sections")

    persuasion_pattern = state.get("persuasion_pattern")

    if persuasion_pattern is None:
        raise ValueError("persuasion_pattern is required to correct script sections")

    unique_mechanism = state.get("unique_mechanism")

    if unique_mechanism is None:
        raise ValueError("unique_mechanism is required to correct script sections")

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
        retry_count=state.get("retry_count", 0),
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
    context = runtime.context

    if context is None:
        raise RuntimeError("Copy adaptation workflow context is required.")

    user_profile = state.get("user_profile")

    if user_profile is None:
        raise ValueError("user_profile is required to validate script")

    sections = _resolve_final_sections(state)

    target_language = state.get("target_language")

    if target_language is None:
        raise ValueError("target_language is required to validate script")

    platform = state.get("platform")

    if platform is None:
        raise ValueError("platform is required to validate script")

    main_angle = state.get("main_angle")

    if main_angle is None:
        raise ValueError("main_angle is required to validate script")

    main_promise = state.get("main_promise")

    if main_promise is None:
        raise ValueError("main_promise is required to validate script")

    unique_mechanism = state.get("unique_mechanism")

    if unique_mechanism is None:
        raise ValueError("unique_mechanism is required to validate script")

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
            "validation_errors": validation.validation_errors,
            "validation_warnings": validation.validation_warnings,
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
    context = runtime.context

    if context is None:
        raise RuntimeError("Copy adaptation workflow context is required.")

    user_profile = state.get("user_profile")

    if user_profile is None:
        raise ValueError("user_profile is required to correct validated script")

    sections = state.get("sections")

    if not sections:
        raise ValueError("sections is required to correct validated script")

    validation_errors = state.get("validation_errors")

    if not validation_errors:
        raise ValueError("validation_errors is required to correct validated script")

    target_language = state.get("target_language")

    if target_language is None:
        raise ValueError("target_language is required to correct validated script")

    platform = state.get("platform")

    if platform is None:
        raise ValueError("platform is required to correct validated script")

    main_angle = state.get("main_angle")

    if main_angle is None:
        raise ValueError("main_angle is required to correct validated script")

    main_promise = state.get("main_promise")

    if main_promise is None:
        raise ValueError("main_promise is required to correct validated script")

    unique_mechanism = state.get("unique_mechanism")

    if unique_mechanism is None:
        raise ValueError("unique_mechanism is required to correct validated script")

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
    estimated_duration = timing_metrics["estimated_duration"]

    hooks = script_output._hooks()
    
    cta_sections = script_output._cta_sections()
    cta = cta_sections[-1] if cta_sections else None

    adapted_script = AdaptedScriptOutput(
        script=script,
        sections=final_sections,
        hooks=hooks,
        cta=cta,
        estimated_duration=estimated_duration,
        word_count=word_count,
        voice_ready_text=voice_ready_text,
        adaptation_notes=state.get("adaptation_notes"),
        validation_warnings=state.get("validation_warnings") or [],
        validation_errors=state.get("validation_errors") or [],
        validation_passed=state.get("validation_passed", False),
        missing_proofs=state.get("missing_proofs") or [],
    )   

    return {
        "adapted_script": adapted_script.model_dump(),
    }
