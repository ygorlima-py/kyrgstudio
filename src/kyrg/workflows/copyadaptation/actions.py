import json
from typing import Any

from kyrg.llms.base import LLMBase
from kyrg.workflows.base import AIActionBase
from kyrg.workflows.copyanalysis.schemas import CopyAnalysisOutput, SectionType
from kyrg.workflows.copyadaptation.prompts import CopyAdaptationPrompts
from kyrg.workflows.copyadaptation.schemas import (
    BuildCopyStrategyOutput,
    ReviewSectionFlowOutput,
    UserProfileOutput,
    ValidateScriptOutput,
    WriteScriptSectionsOutput,
)


class BuildCopyStrategy(AIActionBase):
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
        return self.llm.structured(
            prompt=self._build_prompt(),
            output_schema=BuildCopyStrategyOutput,
        )

    async def aexecute(self) -> BuildCopyStrategyOutput:
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            output_schema=BuildCopyStrategyOutput,
        )

    def _build_prompt(self) -> str:
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
        return self.llm.structured(
            prompt=self._build_prompt(),
            output_schema=WriteScriptSectionsOutput,
        )

    async def aexecute(self) -> WriteScriptSectionsOutput:
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            output_schema=WriteScriptSectionsOutput,
        )

    def _build_prompt(self) -> str:
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
        return self.llm.structured(
            prompt=self._build_prompt(),
            output_schema=WriteScriptSectionsOutput,
        )

    async def aexecute(self) -> WriteScriptSectionsOutput:
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            output_schema=WriteScriptSectionsOutput,
        )

    def _build_prompt(self) -> str:
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
        return self.llm.structured(
            prompt=self._build_prompt(),
            output_schema=WriteScriptSectionsOutput,
        )

    async def aexecute(self) -> WriteScriptSectionsOutput:
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            output_schema=WriteScriptSectionsOutput,
        )

    def _build_prompt(self) -> str:
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
        return self.llm.structured(
            prompt=self._build_prompt(),
            output_schema=ReviewSectionFlowOutput,
        )

    async def aexecute(self) -> ReviewSectionFlowOutput:
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            output_schema=ReviewSectionFlowOutput,
        )

    def _build_prompt(self) -> str:
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
        return self.llm.structured(
            prompt=self._build_prompt(),
            output_schema=ValidateScriptOutput,
        )

    async def aexecute(self) -> ValidateScriptOutput:
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            output_schema=ValidateScriptOutput,
        )

    def _build_prompt(self) -> str:
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
