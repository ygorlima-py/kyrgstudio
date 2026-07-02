"""Data contracts for the copy adaptation workflow.

The models in this module define user input, structured LLM outputs, validation
issues, and the final assembled script returned by the workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from pydantic import BaseModel, Field

from kyrg.llms.base import LLMBase
from kyrg.workflows.domain_types import SectionType


@dataclass(frozen=True)
class CopyAdaptationWorkflowContext:
    """LLM dependencies and retry policy injected into workflow nodes."""

    strategy_llm: LLMBase = field(
        metadata={
            "description": "LLM used to define the copy adaptation strategy before writing the script."
        }
    )
    writing_llm: LLMBase = field(
        metadata={
            "description": "LLM used to write the adapted script sections."
        }
    )
    review_llm: LLMBase = field(
        metadata={
            "description": "LLM used to review section flow, coherence, and transitions."
        }
    )
    validation_llm: LLMBase = field(
        metadata={
            "description": "LLM used to validate the adapted script against the user profile and safety rules."
        }
    )
    max_retry: int = field(
        default=1,
        metadata={
            "description": "maximum attempts at correction"
        }
    )


class UserProfileOutput(BaseModel):
    """User offer profile used as the source of truth for adaptation."""

    # Product, service, method, or solution promoted by the new script.
    product_or_solution: str = Field(
        description="Product, service, method, opportunity, or solution being promoted."
    )
    # Audience the script should address.
    target_audience: str = Field(
        description="Audience the adapted script should speak to."
    )
    # Main pain, problem, or obstacle this audience faces.
    core_problem: str = Field(
        description="Main problem, pain, frustration, or obstacle the audience has."
    )
    # Main desire or transformation this audience wants to achieve.
    core_desire: str = Field(
        description="Main desired outcome, aspiration, or transformation."
    )
    # Main promise allowed for the offer.
    main_promise: str = Field(
        description="Main promise the adapted script is allowed to make."
    )
    # Mechanism, method, or explanation that makes the offer credible and different.
    unique_mechanism: str | None = Field(
        default=None,
        description="Mechanism, method, angle, or explanation that makes the offer credible and different."
    )
    # Real benefits that may be used in the script.
    benefits: list[str] = Field(
        default_factory=list,
        description="Benefits that can be used in the adapted script."
    )
    # Objections, fears, or doubts the script should answer.
    objections: list[str] = Field(
        default_factory=list,
        description="Objections, doubts, fears, or barriers the script should address."
    )
    # Available proof, such as testimonials, data, studies, screenshots, or demonstrations.
    proof_assets: list[str] = Field(
        default_factory=list,
        description="Real proof available for the script, such as testimonials, data, cases, demonstrations, or credentials."
    )
    # Commercial offer details, such as price, guarantee, bonuses, deadline, or terms.
    offer_details: str | None = Field(
        default=None,
        description="Commercial details such as price, guarantee, bonuses, deadline, or payment terms."
    )
    # Action the viewer should take at the end of the script.
    call_to_action: str = Field(
        description="Action the viewer should take after watching the script."
    )
    # Desired tone of voice for the script.
    tone: str | None = Field(
        default=None,
        description="Desired tone of voice for the adapted script."
    )
    # Language the adapted script should be written in.
    target_language: str | None = Field(
        default=None,
        description="Language the adapted script should be written in."
    )
    # Platform or channel where the script will be used.
    platform: str | None = Field(
        default=None,
        description="Distribution platform or placement for the adapted script."
    )
    # Desired script duration in minutes.
    desired_duration: float = Field(
        description="Desired script duration in minutes."
    )
    # Promises, words, topics, or angles that must not be used.
    restrictions: list[str] = Field(
        default_factory=list,
        description="Claims, words, promises, or angles that must not be used."
    )


class BuildCopyStrategyOutput(BaseModel):
    """Strategic plan generated before script writing begins."""

    # Main angle that guides the new copy.
    main_angle: str = Field(
        description="Primary strategic angle that should drive the adapted copy."
    )
    # Audience awareness level; determines how educational or direct the copy should be.
    awareness_level: Literal[
        "unaware",
        "problem_aware",
        "solution_aware",
        "product_aware",
        "most_aware",
    ] = Field(
        description="Audience awareness level that determines how direct or educational the opening strategy should be."
    )
    # Central script promise, limited by the brief.
    main_promise: str = Field(
        description="Central promise of the adapted script, constrained by the user profile."
    )
    # Persuasive structure selected to organize the copy.
    persuasion_pattern: Literal[
        "PAS",
        "AIDA",
        "BAB",
        "storytelling",
        "problem_solution",
        "education_to_offer",
        "hybrid",
    ] = Field(
        description="Persuasive structure selected for the adapted script."
    )
    # Priority objections the script needs to overcome.
    objections_to_address: list[str] = Field(
        default_factory=list,
        description="Prioritized objections the adapted script should address."
    )
    # Plan for which proof to use in each important part of the script.
    proof_plan: dict[str, str] = Field(
        default_factory=dict,
        description="Plan describing which proof asset or proof type should support each relevant section."
    )
    # Mechanism or explanation that makes the offer credible and different.
    unique_mechanism: str = Field(
        description="Mechanism, method, or explanation that makes the adapted offer feel credible and different."
    )
    # Short explanation of why the strategy was selected.
    strategy_notes: str = Field(
        description="Short explanation of why this strategy was chosen and how it uses the reference copy analysis."
    )


class ScriptSectionOutput(BaseModel):
    """Single written section of the adapted script before timing enrichment."""

    # Section order within the adapted script.
    order: int = Field(
        description="Position of this section inside the adapted script."
    )
    # Canonical section type. This value must remain in English.
    section_type: Literal[
        "hook",
        "problem",
        "pain",
        "agitation",
        "promise",
        "mechanism",
        "proof",
        "story",
        "objection",
        "offer",
        "cta",
        "urgency",
        "scarcity",
        "transition",
        "education",
        "payoff",
    ] = Field(
        description="Canonical English type of the written script section. Never translate this value."
    )
    # Final written text for this section, ready for flow review.
    text: str = Field(
        description="Written script copy for this section, in the target language."
    )
    # Persuasive role of this section within the script.
    purpose: str = Field(
        description="Strategic persuasive role of this section in the adapted script."
    )
    # Whether the section came from a reference or was created from scratch.
    adaptation_mode: Literal[
        "adapted_from_reference",
        "created_from_scratch",
    ] = Field(
        description="Whether this section was adapted from a mapped reference section or created from scratch."
    )
    # Original reference section type, when one exists.
    source_reference_section_type: str | None = Field(
        default=None,
        description="Reference section type used as inspiration, when this section was adapted from the original copy."
    )
    # Real proof used in this section, when available.
    proof_used: str | None = Field(
        default=None,
        description="Real proof asset or proof instruction used in this section, when available."
    )
    # Whether this section needs proof but no proof was available.
    missing_proof: bool = Field(
        default=False,
        description="Whether this section needs proof but no valid proof asset was available."
    )
    # Short note to help the next node review the transition.
    transition_hint: str | None = Field(
        default=None,
        description="Short note explaining how this section should connect to the next one."
    )
    # Narrative intent of the following pause; exact timing is calculated by code.
    pause_intent: Literal[
        "short",
        "medium",
        "long",
        "dramatic",
    ] = Field(
        description=(
            "Semantic pause intent after this section. Use short for continuity, "
            "medium for a normal transition, long for emphasis, and dramatic only "
            "for a major reveal or emotional beat. This field expresses intent, "
            "not a duration in seconds."
        )
    )
   
class TimedScriptSectionOutput(ScriptSectionOutput):
    """Final script section enriched with deterministic timing metadata."""

    # Estimated word count for this section.
    word_count: int = Field(
        description="Estimated number of words in this section."
    )
    # Estimated spoken duration for this section in seconds, excluding the following pause.
    estimated_duration_seconds: float | None = Field(
        default=None,
        description="Estimated spoken duration for this section in seconds, excluding the pause after it."
    )
    # Estimated pause after this section in seconds.
    pause_after_seconds: float | None = Field(
        default=None,
        description="Estimated pause after this section in seconds."
    )
    # Estimated time when this section starts in the final narration.
    start_seconds: float | None = Field(
        default=None,
        description="Estimated start time of this section in the final narration."
    )
    # Estimated time when this section ends, excluding the following pause.
    end_seconds: float | None = Field(
        default=None,
        description="Estimated end time of this section in the final narration, excluding the pause after it."
    )
    
class WriteScriptSectionsOutput(BaseModel):
    """Structured output produced by writing and correction steps."""

    # Written adapted-script sections before final flow review.
    sections: list[ScriptSectionOutput] = Field(
        default_factory=list,
        description="Ordered written sections of the adapted script."
    )
    # Sections or moments that need real proof before production use.
    missing_proofs: list[str] = Field(
        default_factory=list,
        description="Sections or claims that need real proof before the script can be safely used."
    )
    # Short explanation of what was adapted, created from scratch, or constrained.
    adaptation_notes: str = Field(
        description="Short explanation of how the reference copy was adapted to the user offer."
    )


class SectionRevisionInstruction(BaseModel):
    """Actionable instruction for correcting section flow issues."""

    # Order of the section needing revision, when the issue is localized.
    section_order: int | None = Field(
        default=None,
        description="Order of the section that needs revision, when the issue is tied to a specific section."
    )
    # Type of the affected section, when applicable.
    section_type: str | None = Field(
        default=None,
        description="Type of the section that needs revision, such as hook, promise, mechanism, objection, offer, or cta."
    )
    # Specific problem found in the flow.
    issue: str = Field(
        description="Specific flow, continuity, sequence, or transition problem found in the script."
    )
    # Concrete action the writing node should perform on retry.
    action: Literal[
        "rewrite_section",
        "move_section",
        "merge_section",
        "remove_section",
        "adjust_transition",
        "strengthen_promise",
        "remove_unsupported_claim",
        "shorten_section",
    ] = Field(
        description="Concrete revision action required to fix the issue."
    )
    # Clear instruction for the writing node to follow on retry.
    instruction: str = Field(
        description="Clear instruction that write_script_sections must follow on retry."
    )
    # Revision priority.
    priority: Literal["low", "medium", "high"] = Field(
        description="Priority of the revision instruction."
    )


class ReviewSectionFlowOutput(BaseModel):
    """Result of reviewing continuity and persuasive sequence between sections."""

    # Whether the sections form a coherent sequence ready for validation.
    flow_approved: bool = Field(
        description="Whether the section sequence is coherent enough to proceed to final validation."
    )
    # Specific continuity, ordering, contradiction, or transition issues.
    flow_issues: list[str] = Field(
        default_factory=list,
        description="Specific and actionable flow issues that should be fixed if the script is not approved."
    )
    # Structured instructions to guide the writing-node retry.
    revision_instructions: list[SectionRevisionInstruction] = Field(
        default_factory=list,
        description="Structured revision instructions for write_script_sections when retry is needed."
    )
    # Only sections with small transition or continuity adjustments.
    sections_revised: list[ScriptSectionOutput] = Field(
        default_factory=list,
        description="Only the sections that were actually revised during the flow review."
    )

class ValidateScriptOutput(BaseModel):
    """Final validation result for production readiness checks."""

    # Whether the script passed without critical errors.
    validation_passed: bool = Field(
        description="Whether the adapted script passed validation without critical blocking errors."
    )
    # Critical errors that block the script from being delivered as ready.
    validation_errors: list[ValidationIssue] = Field(
        default_factory=list,
        description="Critical validation errors that block the script from being production-ready."
    )
    # Non-blocking warnings to show or consider before use.
    validation_warnings: list[ValidationIssue] = Field(
        default_factory=list,
        description="Non-blocking validation warnings that should be reviewed before production."
    )
    
class ValidationIssue(BaseModel):
    """Structured validation problem or warning found in the adapted script."""

    category: Literal[
        "claim",
        "proof",
        "offer",
        "cta",
        "scarcity",
        "duration",
        "language",
        "structure",
        "copy_similarity",
        "other",
    ] = Field(
        description="Broad category used to classify the validation issue."
    )

    code: str = Field(
        description=(
            "Specific machine-readable issue identifier in lowercase snake_case, "
            "such as unsupported_claim or missing_cta."
        )
    )

    section_order: int | None = Field(
        default=None,
        description="Order of the affected script section, when identifiable."
    )

    section_type: SectionType | None = Field(
        default=None,
        description="Canonical type of the affected script section, when identifiable."
    )

    field: str | None = Field(
        default=None,
        description="Name of the affected section field, such as text or proof_used."
    )

    message: str = Field(
        description=(
            "Clear explanation of what is wrong and why it affects script quality "
            "or production readiness."
        )
    )

    correction_action: Literal[
        "remove",
        "soften",
        "rewrite",
        "shorten",
        "expand",
        "align_with_profile",
        "custom",
    ] = Field(
        description="Primary operation required to resolve the validation issue."
    )

    custom_instruction: str | None = Field(
        default=None,
        description=(
            "Explicit correction instruction when correction_action is custom; "
            "otherwise this field must be null."
        )
    )

class AdaptedScriptOutput(BaseModel):
    """Final workflow output assembled from validated script sections."""

    # Complete script in a human-readable review format.
    script: str = Field(
        description="Complete adapted script assembled from the approved sections."
    )
    # Final sections used to assemble the script.
    sections: list[TimedScriptSectionOutput] = Field(
        default_factory=list,
        description="Final ordered sections enriched with deterministic timing data."
    )
    # Hook variations or hook texts found in the final script.
    hooks: list[str] = Field(
        default_factory=list,
        description="Hook texts extracted from the final script sections."
    )
    # Main call to action in the script.
    cta: str | None = Field(
        default=None,
        description="Primary call to action extracted from the final script."
    )
    # Estimated total duration in seconds, including speech and section pauses.
    estimated_duration_seconds: float | None = Field(
        default=None,
        description="Estimated total duration in seconds, including spoken text and pauses between sections."
    )
    # Total word count of the final script.
    word_count: int = Field(
        description="Total estimated word count of the final adapted script."
    )
    # Clean TTS text without markdown or metadata.
    voice_ready_text: str = Field(
        description="Clean narration text ready for text-to-speech generation."
    )
    # Explanation of what was adapted and which safeguards were applied.
    adaptation_notes: str | None = Field(
        default=None,
        description="Notes explaining what was adapted from the reference and what changed."
    )
    # Non-blocking validation warnings.
    validation_warnings: list[ValidationIssue] = Field(
        default_factory=list,
        description="Non-blocking validation warnings inherited from script validation."
    )
    # Critical validation errors, if any.
    validation_errors: list[ValidationIssue] = Field(
        default_factory=list,
        description="Critical validation errors inherited from script validation."
    )
    # Whether the script passed final validation.
    validation_passed: bool = Field(
        description="Whether the final adapted script passed validation."
    )
    # Sections or claims that need real proof before production use.
    missing_proofs: list[str] = Field(
        default_factory=list,
        description="Proof gaps that should be reviewed before production."
    )

if __name__ == "__main__":
    from rich import print
    print(ValidateScriptOutput.model_json_schema())
