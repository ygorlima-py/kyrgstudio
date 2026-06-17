from kyrg.workflows.copyadaptation.state import CopyAdaptationState
from kyrg.workflows.copyadaptation.actions import (
    BuildCopyStrategy,
    CorrectScriptSections,
    ReviewAction,
    ValidateScriptAction,
    WriteScriptSection,
)
from kyrg.workflows.copyadaptation.schemas import (
    AdaptedScriptOutput,
    CopyAdaptationWorkflowContext,
    ScriptSectionOutput,
)
from kyrg.workflows.base import AIActionExecutor
from kyrg.workflows.core import WorkflowRuntime
from kyrg.workflows.copyadaptation._utils import _resolve_final_sections


SECTION_ADAPTATION_FIELDS = {
    "hook": ["main_promise", "core_problem", "core_desire"],
    "problem": ["core_problem"],
    "pain": ["core_problem"],
    "agitation": ["core_problem", "core_desire"],
    "promise": ["main_promise"],
    "mechanism": ["unique_mechanism"],
    "proof": ["proof_assets"],
    "story": ["proof_assets", "core_problem", "core_desire"],
    "objection": ["objections"],
    "offer": ["product_or_solution", "offer_details"],
    "cta": ["call_to_action"],
    "urgency": ["offer_details"],
    "scarcity": ["offer_details"],
    "education": ["product_or_solution", "unique_mechanism"],
    "transition": ["target_audience", "main_promise"],
    "payoff": ["main_promise", "core_desire", "call_to_action"],
}


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
        previous_sections=state.get("sections") or [],
        flow_issues=state.get("flow_issues") or [],
        retry_count=state.get("retry_count", 0),
    )

    script_sections = AIActionExecutor.run(action)
    token_usage = action.tokens_usage

    return {
        "sections": [
            section.model_dump()
            for section in script_sections.sections
        ],
        "missing_proofs": script_sections.missing_proofs,
        "adaptation_notes": script_sections.adaptation_notes,
        "word_count": script_sections.word_count,
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

    if not review.flow_approved:
        output["retry_count"] = state.get("retry_count", 0) + 1

    return output

def primary_route(state: CopyAdaptationState):
    MAX_RETRY = 1
    
    flow_approved = state.get('flow_approved')
    retry_count = state.get("retry_count", 0)
    
    if not flow_approved:  
        if retry_count <= MAX_RETRY:
            
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

    corrected_sections_output = [
        section.model_dump()
        for section in corrected_sections.sections
    ]
    
    return {
        "sections": [
            section.model_dump()
            for section in corrected_sections.sections
        ],
        "sections_before_correction": previous_sections,
        "sections_after_correction": corrected_sections_output,
        "missing_proofs": corrected_sections.missing_proofs,
        "adaptation_notes": corrected_sections.adaptation_notes,
        "word_count": corrected_sections.word_count,
        "sections_revised": [],
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
        
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
        word_count=state.get("word_count"),
    )

    validation = AIActionExecutor.run(action)
    token_usage = action.tokens_usage

    return {
        "validation_passed": validation.validation_passed,
        "validation_errors": validation.validation_errors,
        "validation_warnings": validation.validation_warnings,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }

def build_script_output(state: CopyAdaptationState) -> dict:
    sections = _resolve_final_sections(state)

    section_texts = [
        section["text"].strip()
        for section in sections
        if section.get("text")
    ]

    if not section_texts:
        raise ValueError("section text is required to build script output")

    final_sections = [
        ScriptSectionOutput.model_validate(section)
        for section in sections
    ]

    script = "\n\n".join(
        f"## {section.get('section_type', 'section')}\n{section.get('text', '').strip()}"
        for section in sections
        if section.get("text")
    )
    voice_ready_text = "\n\n".join(section_texts)
    word_count = sum(len(text.split()) for text in section_texts)
    estimated_duration = round(word_count / 130, 2) if word_count else None

    hooks = [
        section["text"].strip()
        for section in sections
        if section.get("section_type") == "hook" and section.get("text")
    ]

    cta_sections = [
        section["text"].strip()
        for section in sections
        if section.get("section_type") == "cta" and section.get("text")
    ]
    cta = cta_sections[-1] if cta_sections else None

    scene_planning_input = [
        {
            "section_type": section.get("section_type"),
            "text": section.get("text"),
            "purpose": section.get("purpose"),
            "word_count": section.get("word_count"),
            "estimated_duration": round((section.get("word_count") or 0) / 130, 2),
        }
        for section in sections
        if section.get("text")
    ]

    adapted_script = AdaptedScriptOutput(
        script=script,
        sections=final_sections,
        hooks=hooks,
        cta=cta,
        estimated_duration=estimated_duration,
        word_count=word_count,
        voice_ready_text=voice_ready_text,
        scene_planning_input=scene_planning_input,
        adaptation_notes=state.get("adaptation_notes"),
        validation_warnings=state.get("validation_warnings") or [],
        validation_errors=state.get("validation_errors") or [],
        validation_passed=state.get("validation_passed", False),
        missing_proofs=state.get("missing_proofs") or [],
    )

    return {
        "adapted_script": adapted_script.model_dump(),
    }
