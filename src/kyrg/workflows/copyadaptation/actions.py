"""LLM action layer for the copy adaptation workflow.

The classes in this module isolate prompt construction from graph orchestration.
Each action receives already-validated workflow inputs, formats the appropriate
prompt, and asks the configured LLM for a typed Pydantic response. Actions do
not mutate workflow state; node functions are responsible for translating their
outputs into state updates.
"""

import json
from typing import Any

from kyrg.llms.base import LLMBase
from kyrg.workflows.base import AIActionBase
from kyrg.workflows.copyanalysis.schemas import CopyAnalysisOutput, SectionType
from kyrg.workflows.copyadaptation.prompts import CopyAdaptationPrompts
from kyrg.workflows.copyadaptation.system_prompt import CopyAdaptationSystemPrompts
from kyrg.workflows.copyadaptation.schemas import (
    BuildCopyStrategyOutput,
    ReviewSectionFlowOutput,
    UserProfileOutput,
    ValidateScriptOutput,
    WriteScriptSectionsOutput,
)


class BuildCopyStrategy(AIActionBase):
    """Create the strategic brief that guides the adapted script.

    The strategy reconciles the reference copy analysis, the user's offer
    profile, mapped sections, missing sections, known gaps, target language,
    platform, and desired duration before any script copy is written.
    """

    def __init__(
        self,
        llm: LLMBase,
        user_profile: UserProfileOutput,
        copy_analysis: CopyAnalysisOutput,
        mapped_sections: list[dict[str, Any]],
        sections_to_create: list[SectionType],
        gaps_to_fix: list[str],
        target_language: str,
        platform: str,
        desired_duration: float | None,
    ) -> None:
        self.copy_analysis = copy_analysis
        self.user_profile = user_profile
        self.mapped_sections = mapped_sections
        self.sections_to_create = sections_to_create
        self.gaps_to_fix = gaps_to_fix
        self.target_language = target_language
        self.platform = platform
        self.desired_duration = desired_duration
        super().__init__(llm)

    def execute(self) -> BuildCopyStrategyOutput:
        """Run the strategy prompt synchronously and return structured output."""

        return self.llm.structured(
            prompt=self._build_prompt(),
            system_prompt=CopyAdaptationSystemPrompts.SYSTEM_PROMPT_BUILD_COPY_STRATEGY,
            prompt_cache_key="copy-adaptation:strategy",
            output_schema=BuildCopyStrategyOutput,
        )

    async def aexecute(self) -> BuildCopyStrategyOutput:
        """Run the strategy prompt asynchronously and return structured output."""

        return await self.llm.astructured(
            prompt=self._build_prompt(),
            system_prompt=CopyAdaptationSystemPrompts.SYSTEM_PROMPT_BUILD_COPY_STRATEGY,
            prompt_cache_key="copy-adaptation:strategy",
            output_schema=BuildCopyStrategyOutput,
        )

    def _build_prompt(self) -> str:
        """Format the strategy prompt with normalized adaptation context."""

        return CopyAdaptationPrompts.BUILD_COPY_STRATEGY.format(
            target_language=self.target_language,
            platform=self.platform,
            desired_duration=self.desired_duration,
            copy_analysis=self.copy_analysis.model_dump_json(indent=2),
            user_profile=self.user_profile.model_dump_json(indent=2),
            mapped_sections=json.dumps(
                self.mapped_sections,
                ensure_ascii=False,
                indent=2,
            ),
            sections_to_create=json.dumps(
                self.sections_to_create,
                ensure_ascii=False,
                indent=2,
            ),
            gaps_to_fix=json.dumps(
                self.gaps_to_fix,
                ensure_ascii=False,
                indent=2,
            ),
        )

class WriteScriptSection(AIActionBase):
    """Write the initial adapted script as ordered structured sections.

    The action uses the approved strategy and adaptation inputs to produce
    section-level copy, preserving persuasive intent while avoiding unsupported
    claims, invented proof, or literal reuse of the reference copy.
    """

    def __init__(
        self,
        llm: LLMBase,
        user_profile: UserProfileOutput,
        mapped_sections: list[dict[str, Any]],
        sections_to_create: list[SectionType],
        gaps_to_fix: list[str],
        target_language: str,
        platform: str,
        desired_duration: float | None,
        main_angle: str,
        awareness_level: str,
        main_promise: str,
        persuasion_pattern: str,
        objections_to_address: list[str],
        proof_plan: dict[str, Any],
        unique_mechanism: str,
    ) -> None:
        self.user_profile = user_profile
        self.mapped_sections = mapped_sections
        self.sections_to_create = sections_to_create
        self.gaps_to_fix = gaps_to_fix
        self.target_language = target_language
        self.platform = platform
        self.desired_duration = desired_duration
        self.main_angle = main_angle
        self.awareness_level = awareness_level
        self.main_promise = main_promise
        self.persuasion_pattern = persuasion_pattern
        self.objections_to_address = objections_to_address
        self.proof_plan = proof_plan
        self.unique_mechanism = unique_mechanism
        super().__init__(llm)

    def execute(self) -> WriteScriptSectionsOutput:
        """Run the writing prompt synchronously and return section drafts."""

        return self.llm.structured(
            prompt=self._build_prompt(),
            system_prompt=CopyAdaptationSystemPrompts.SYSTEM_PROMPT_WRITE_SCRIPT_SECTIONS,
            prompt_cache_key="copy-adaptation:write-sections",
            output_schema=WriteScriptSectionsOutput,
        )

    async def aexecute(self) -> WriteScriptSectionsOutput:
        """Run the writing prompt asynchronously and return section drafts."""

        return await self.llm.astructured(
            prompt=self._build_prompt(),
            system_prompt=CopyAdaptationSystemPrompts.SYSTEM_PROMPT_WRITE_SCRIPT_SECTIONS,
            prompt_cache_key="copy-adaptation:write-sections",
            output_schema=WriteScriptSectionsOutput,
        )

    def _build_prompt(self) -> str:
        """Format the section-writing prompt from strategy and offer inputs."""

        return CopyAdaptationPrompts.WRITE_SCRIPT_SECTIONS.format(
            target_language=self.target_language,
            platform=self.platform,
            desired_duration=self.desired_duration,
            user_profile=self.user_profile.model_dump_json(indent=2),
            mapped_sections=json.dumps(
                self.mapped_sections,
                ensure_ascii=False,
                indent=2,
            ),
            sections_to_create=json.dumps(
                self.sections_to_create,
                ensure_ascii=False,
                indent=2,
            ),
            gaps_to_fix=json.dumps(
                self.gaps_to_fix,
                ensure_ascii=False,
                indent=2,
            ),
            main_angle=self.main_angle,
            awareness_level=self.awareness_level,
            main_promise=self.main_promise,
            persuasion_pattern=self.persuasion_pattern,
            objections_to_address=json.dumps(
                self.objections_to_address,
                ensure_ascii=False,
                indent=2,
            ),
            proof_plan=json.dumps(
                self.proof_plan,
                ensure_ascii=False,
                indent=2,
            ),
            unique_mechanism=self.unique_mechanism,
        )

class CorrectScriptSections(AIActionBase):
    """Correct section drafts after the flow review rejects the sequence.

    The correction is constrained by review issues and revision instructions. It
    preserves the offer, strategy, and proof boundaries while fixing ordering,
    continuity, transitions, or section-level structural problems.
    """

    def __init__(
        self,
        llm: LLMBase,
        user_profile: UserProfileOutput,
        previous_sections: list[dict[str, Any]],
        flow_issues: list[str],
        revision_instructions: list[dict[str, Any]],
        missing_proofs: list[str],
        target_language: str,
        platform: str,
        desired_duration: float | None,
        main_angle: str,
        awareness_level: str,
        main_promise: str,
        persuasion_pattern: str,
        objections_to_address: list[str],
        proof_plan: dict[str, Any],
        unique_mechanism: str,
        retry_count: int,
    ) -> None:
        self.user_profile = user_profile
        self.previous_sections = previous_sections
        self.flow_issues = flow_issues
        self.revision_instructions = revision_instructions
        self.missing_proofs = missing_proofs
        self.target_language = target_language
        self.platform = platform
        self.desired_duration = desired_duration
        self.main_angle = main_angle
        self.awareness_level = awareness_level
        self.main_promise = main_promise
        self.persuasion_pattern = persuasion_pattern
        self.objections_to_address = objections_to_address
        self.proof_plan = proof_plan
        self.unique_mechanism = unique_mechanism
        self.retry_count = retry_count
        super().__init__(llm)

    def execute(self) -> WriteScriptSectionsOutput:
        """Run the section-correction prompt synchronously."""

        return self.llm.structured(
            prompt=self._build_prompt(),
            system_prompt=CopyAdaptationSystemPrompts.SYSTEM_PROMPT_CORRECT_SCRIPT_SECTIONS,
            prompt_cache_key="copy-adaptation:correct-sections",
            output_schema=WriteScriptSectionsOutput,
        )

    async def aexecute(self) -> WriteScriptSectionsOutput:
        """Run the section-correction prompt asynchronously."""

        return await self.llm.astructured(
            prompt=self._build_prompt(),
            system_prompt=CopyAdaptationSystemPrompts.SYSTEM_PROMPT_CORRECT_SCRIPT_SECTIONS,
            prompt_cache_key="copy-adaptation:correct-sections",
            output_schema=WriteScriptSectionsOutput,
        )

    def _build_prompt(self) -> str:
        """Format the section-correction prompt from flow review feedback."""

        return CopyAdaptationPrompts.CORRECT_SCRIPT_SECTIONS.format(
            target_language=self.target_language,
            platform=self.platform,
            desired_duration=self.desired_duration,
            retry_count=self.retry_count,
            user_profile=self.user_profile.model_dump_json(indent=2),
            main_angle=self.main_angle,
            awareness_level=self.awareness_level,
            main_promise=self.main_promise,
            persuasion_pattern=self.persuasion_pattern,
            objections_to_address=json.dumps(
                self.objections_to_address,
                ensure_ascii=False,
                indent=2,
            ),
            proof_plan=json.dumps(
                self.proof_plan,
                ensure_ascii=False,
                indent=2,
            ),
            unique_mechanism=self.unique_mechanism,
            previous_sections=json.dumps(
                self.previous_sections,
                ensure_ascii=False,
                indent=2,
            ),
            flow_issues=json.dumps(
                self.flow_issues,
                ensure_ascii=False,
                indent=2,
            ),
            revision_instructions=json.dumps(
                self.revision_instructions,
                ensure_ascii=False,
                indent=2,
            ),
            missing_proofs=json.dumps(
                self.missing_proofs,
                ensure_ascii=False,
                indent=2,
            ),
        )


class CorrectValidatedScript(AIActionBase):
    """Correct the full script after validation finds production blockers.

    This action receives validation errors, warnings, timing metrics, and the
    latest sections. It rewrites only what is needed to satisfy validation while
    keeping the same offer, promise, proof limits, and strategic direction.
    """

    def __init__(
        self,
        llm: LLMBase,
        user_profile: UserProfileOutput,
        sections: list[dict[str, Any]],
        validation_errors: list[dict[str, Any]],
        validation_warnings: list[dict[str, Any]],
        timing_metrics: dict[str, Any],
        missing_proofs: list[str],
        target_language: str,
        platform: str,
        desired_duration: float | None,
        main_angle: str,
        main_promise: str,
        proof_plan: dict[str, Any],
        unique_mechanism: str,
        retry_count: int,
    ) -> None:
        self.user_profile = user_profile
        self.sections = sections
        self.validation_errors = validation_errors
        self.validation_warnings = validation_warnings
        self.timing_metrics = timing_metrics
        self.missing_proofs = missing_proofs
        self.target_language = target_language
        self.platform = platform
        self.desired_duration = desired_duration
        self.main_angle = main_angle
        self.main_promise = main_promise
        self.proof_plan = proof_plan
        self.unique_mechanism = unique_mechanism
        self.retry_count = retry_count
        super().__init__(llm)

    def execute(self) -> WriteScriptSectionsOutput:
        """Run the validation-correction prompt synchronously."""

        return self.llm.structured(
            prompt=self._build_prompt(),
            system_prompt=CopyAdaptationSystemPrompts.SYSTEM_PROMPT_CORRECT_VALIDATED_SCRIPT,
            prompt_cache_key="copy-adaptation:correct-validated-script",
            output_schema=WriteScriptSectionsOutput,
        )

    async def aexecute(self) -> WriteScriptSectionsOutput:
        """Run the validation-correction prompt asynchronously."""

        return await self.llm.astructured(
            prompt=self._build_prompt(),
            system_prompt=CopyAdaptationSystemPrompts.SYSTEM_PROMPT_CORRECT_VALIDATED_SCRIPT,
            prompt_cache_key="copy-adaptation:correct-validated-script",
            output_schema=WriteScriptSectionsOutput,
        )

    def _build_prompt(self) -> str:
        """Format the full-script correction prompt from validation feedback."""

        return CopyAdaptationPrompts.CORRECT_VALIDATED_SCRIPT.format(
            target_language=self.target_language,
            platform=self.platform,
            desired_duration=self.desired_duration,
            retry_count=self.retry_count,
            user_profile=self.user_profile.model_dump_json(indent=2),
            main_angle=self.main_angle,
            main_promise=self.main_promise,
            unique_mechanism=self.unique_mechanism,
            proof_plan=json.dumps(
                self.proof_plan,
                ensure_ascii=False,
                indent=2,
            ),
            sections=json.dumps(
                self.sections,
                ensure_ascii=False,
                indent=2,
            ),
            validation_errors=json.dumps(
                self.validation_errors,
                ensure_ascii=False,
                indent=2,
            ),
            validation_warnings=json.dumps(
                self.validation_warnings,
                ensure_ascii=False,
                indent=2,
            ),
            timing_metrics=json.dumps(
                self.timing_metrics,
                ensure_ascii=False,
                indent=2,
            ),
            missing_proofs=json.dumps(
                self.missing_proofs,
                ensure_ascii=False,
                indent=2,
            ),
        )


class ReviewAction(AIActionBase):
    """Review whether drafted sections work as a coherent persuasive sequence.

    The review focuses on flow, ordering, narrative continuity, and transition
    quality. It can approve the sequence, return small revised sections, or
    provide explicit retry instructions for a writer correction pass.
    """

    def __init__(
        self,
        llm: LLMBase,
        sections: list[dict[str, Any]],
        missing_proofs: list[str],
        target_language: str,
        platform: str,
        desired_duration: float | None,
        main_angle: str,
        awareness_level: str,
        main_promise: str,
        persuasion_pattern: str,
        objections_to_address: list[str],
        proof_plan: dict[str, Any],
        unique_mechanism: str,
    ) -> None:
        self.sections = sections
        self.missing_proofs = missing_proofs
        self.target_language = target_language
        self.platform = platform
        self.desired_duration = desired_duration
        self.main_angle = main_angle
        self.awareness_level = awareness_level
        self.main_promise = main_promise
        self.persuasion_pattern = persuasion_pattern
        self.objections_to_address = objections_to_address
        self.proof_plan = proof_plan
        self.unique_mechanism = unique_mechanism
        super().__init__(llm)

    def execute(self) -> ReviewSectionFlowOutput:
        """Run the flow-review prompt synchronously."""

        return self.llm.structured(
            prompt=self._build_prompt(),
            system_prompt=CopyAdaptationSystemPrompts.SYSTEM_PROMPT_REVIEW_SECTION_FLOW,
            prompt_cache_key="copy-adaptation:review-flow",
            output_schema=ReviewSectionFlowOutput,
        )

    async def aexecute(self) -> ReviewSectionFlowOutput:
        """Run the flow-review prompt asynchronously."""

        return await self.llm.astructured(
            prompt=self._build_prompt(),
            system_prompt=CopyAdaptationSystemPrompts.SYSTEM_PROMPT_REVIEW_SECTION_FLOW,
            prompt_cache_key="copy-adaptation:review-flow",
            output_schema=ReviewSectionFlowOutput,
        )

    def _build_prompt(self) -> str:
        """Format the flow-review prompt with the latest drafted sections."""

        return CopyAdaptationPrompts.REVIEW_SECTION_FLOW.format(
            target_language=self.target_language,
            platform=self.platform,
            desired_duration=self.desired_duration,
            main_angle=self.main_angle,
            awareness_level=self.awareness_level,
            main_promise=self.main_promise,
            persuasion_pattern=self.persuasion_pattern,
            objections_to_address=json.dumps(
                self.objections_to_address,
                ensure_ascii=False,
                indent=2,
            ),
            proof_plan=json.dumps(
                self.proof_plan,
                ensure_ascii=False,
                indent=2,
            ),
            unique_mechanism=self.unique_mechanism,
            sections=json.dumps(
                self.sections,
                ensure_ascii=False,
                indent=2,
            ),
            missing_proofs=json.dumps(
                self.missing_proofs,
                ensure_ascii=False,
                indent=2,
            ),
        )


class ValidateScriptAction(AIActionBase):
    """Validate script readiness against offer truth and workflow safeguards.

    Validation checks production-facing risks such as unsupported claims,
    invented proof, CTA mismatches, language drift, duration issues, and literal
    copying from the reference analysis.
    """

    def __init__(
        self,
        llm: LLMBase,
        user_profile: UserProfileOutput,
        mapped_sections: list[dict[str, Any]],
        sections: list[dict[str, Any]],
        missing_proofs: list[str],
        target_language: str,
        platform: str,
        desired_duration: float | None,
        main_angle: str,
        main_promise: str,
        unique_mechanism: str,
        proof_plan: dict[str, Any],
        timing_metrics: dict[str, Any],
    ) -> None:
        self.user_profile = user_profile
        self.mapped_sections = mapped_sections
        self.sections = sections
        self.missing_proofs = missing_proofs
        self.target_language = target_language
        self.platform = platform
        self.desired_duration = desired_duration
        self.main_angle = main_angle
        self.main_promise = main_promise
        self.unique_mechanism = unique_mechanism
        self.proof_plan = proof_plan
        self.timing_metrics = timing_metrics
        super().__init__(llm)

    def execute(self) -> ValidateScriptOutput:
        """Run the validation prompt synchronously."""

        return self.llm.structured(
            prompt=self._build_prompt(),
            system_prompt=CopyAdaptationSystemPrompts.SYSTEM_PROMPT_VALIDATE_SCRIPT,
            prompt_cache_key="copy-adaptation:validate-script",
            output_schema=ValidateScriptOutput,
        )

    async def aexecute(self) -> ValidateScriptOutput:
        """Run the validation prompt asynchronously."""

        return await self.llm.astructured(
            prompt=self._build_prompt(),
            system_prompt=CopyAdaptationSystemPrompts.SYSTEM_PROMPT_VALIDATE_SCRIPT,
            prompt_cache_key="copy-adaptation:validate-script",
            output_schema=ValidateScriptOutput,
        )

    def _build_prompt(self) -> str:
        """Format the production-readiness validation prompt."""

        return CopyAdaptationPrompts.VALIDATE_SCRIPT.format(
            target_language=self.target_language,
            platform=self.platform,
            desired_duration=self.desired_duration,
            user_profile=self.user_profile.model_dump_json(indent=2),
            mapped_sections=json.dumps(
                self.mapped_sections,
                ensure_ascii=False,
                indent=2,
            ),
            main_angle=self.main_angle,
            main_promise=self.main_promise,
            unique_mechanism=self.unique_mechanism,
            proof_plan=json.dumps(
                self.proof_plan,
                ensure_ascii=False,
                indent=2,
            ),
            sections=json.dumps(
                self.sections,
                ensure_ascii=False,
                indent=2,
            ),
            missing_proofs=json.dumps(
                self.missing_proofs,
                ensure_ascii=False,
                indent=2,
            ),
            timing_metrics=json.dumps(
                self.timing_metrics,
                ensure_ascii=False,
                indent=2,
            ),
        )
