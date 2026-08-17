"""Live quality evaluations for :class:`CopyAnalysisWorkflow`.

These evaluations are intentionally excluded from the deterministic suite.
Enable them with ``KYRG_RUN_COPYANALYSIS_EVALS=1`` and configure
``OPENAI_API_KEY`` plus ``KYRG_COPYANALYSIS_EVAL_MODEL``. An independent judge
model can be selected with ``KYRG_COPYANALYSIS_JUDGE_MODEL``.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
from loguru import logger
from pydantic import BaseModel, Field

from kyrg.llms.openai_llm import OpenAILLM
from kyrg.transcribers import TextSegment, TranscriptionResult
from kyrg.workflows.copyanalysis.schemas import (
    CopyAnalysisOutput,
    CopyAnalysisWorkflowContext,
)
from kyrg.workflows.copyanalysis.state import CopyAnalysisState
from kyrg.workflows.copyanalysis.workflow import CopyAnalysisWorkflow


pytestmark = pytest.mark.live_eval


@dataclass(frozen=True)
class LiveEvalModels:
    """Configured generation and judge models for one live evaluation."""

    generator: OpenAILLM
    judge: OpenAILLM
    generation_model: str
    judge_model: str


@dataclass(frozen=True)
class CopyAnalysisFixture:
    """Grounded source material and expected facts for the quality rubric."""

    fixture_id: str
    transcription: TranscriptionResult
    expected_hook: str
    expected_section_order: tuple[str, ...]
    expected_product: str
    expected_audience: str
    expected_call_to_action: str
    explicitly_absent_elements: tuple[str, ...]


class CopyAnalysisQualityEvaluation(BaseModel):
    """Evidence-based scores returned by the independent quality judge."""

    structure_grounding_score: float = Field(
        ge=0,
        le=1,
        description="Accuracy of hook, section order, purposes, gaps, and timing.",
    )
    offer_grounding_score: float = Field(
        ge=0,
        le=1,
        description="Accuracy of extracted offer facts and absent fields.",
    )
    persuasion_coherence_score: float = Field(
        ge=0,
        le=1,
        description="Consistency of persuasion judgments with extracted evidence.",
    )
    cross_step_consistency_score: float = Field(
        ge=0,
        le=1,
        description="Consistency among structure, offer, and persuasion outputs.",
    )
    hook_correct: bool = Field(
        description="Whether the main hook preserves the source hook's meaning."
    )
    section_order_preserved: bool = Field(
        description="Whether the detected sections follow the source progression."
    )
    gap_classification_coherent: bool = Field(
        description="Whether missing, incomplete, and weak gaps are distinguished."
    )
    timestamps_compatible: bool = Field(
        description="Whether section timestamps are compatible with source segments."
    )
    offer_facts_correct: bool = Field(
        description="Whether product, audience, problem, promise, and CTA are grounded."
    )
    invented_sections: list[str] = Field(
        default_factory=list,
        description="Sections asserted as present without support in the transcript.",
    )
    invented_offer_elements: list[str] = Field(
        default_factory=list,
        description="Unsupported price, bonus, proof, guarantee, urgency, or CTA facts.",
    )
    persuasion_supported_by_evidence: bool = Field(
        description="Whether persuasion diagnoses follow structure and offer evidence."
    )
    analysis_language_correct: bool = Field(
        description="Whether textual analysis uses the transcription language."
    )
    contradictions: list[str] = Field(
        default_factory=list,
        description="Direct contradictions found across workflow stages.",
    )
    critical_issues: list[str] = Field(
        default_factory=list,
        description="Concise evidence for failures that make the analysis unsafe to use.",
    )
    passed: bool = Field(
        description="Whether the result satisfies the complete quality rubric."
    )


def _live_models() -> LiveEvalModels:
    """Create live models only after explicit paid-evaluation opt-in."""

    if os.getenv("KYRG_RUN_COPYANALYSIS_EVALS") != "1":
        pytest.skip("Live copy analysis evals are disabled.")

    api_key = os.getenv("OPENAI_API_KEY")
    generation_model = os.getenv("KYRG_COPYANALYSIS_EVAL_MODEL")

    if not api_key or not generation_model:
        pytest.skip(
            "OPENAI_API_KEY and KYRG_COPYANALYSIS_EVAL_MODEL are required."
        )

    judge_model = os.getenv(
        "KYRG_COPYANALYSIS_JUDGE_MODEL",
        generation_model,
    )

    return LiveEvalModels(
        generator=OpenAILLM(
            api_key=api_key,
            model=generation_model,
            temperature=0.0,
        ),
        judge=OpenAILLM(
            api_key=api_key,
            model=judge_model,
            temperature=0.0,
        ),
        generation_model=generation_model,
        judge_model=judge_model,
    )


def _fixture() -> CopyAnalysisFixture:
    """Return a transcript with explicit offer facts and deliberate omissions."""

    segments = [
        TextSegment(
            id=0,
            start=0.0,
            end=5.0,
            text="Tu comisión puede construir tu futuro o desaparecer cada mes.",
        ),
        TextSegment(
            id=1,
            start=5.0,
            end=12.0,
            text=(
                "Muchos agrónomos reciben una buena comisión, pero dejan todo "
                "parado porque no saben cómo organizarla."
            ),
        ),
        TextSegment(
            id=2,
            start=12.0,
            end=20.0,
            text=(
                "Sin un plan, mezclan la reserva con inversiones de largo plazo "
                "y toman decisiones por recomendaciones aisladas."
            ),
        ),
        TextSegment(
            id=3,
            start=20.0,
            end=30.0,
            text=(
                "La Ruta de la Comisión es un curso que enseña a separar la "
                "reserva, entender las clases de activos y diversificar una cartera."
            ),
        ),
        TextSegment(
            id=4,
            start=30.0,
            end=38.0,
            text=(
                "El objetivo es que aprendas a decidir con un proceso, incluso "
                "si hoy no entiendes de inversiones."
            ),
        ),
        TextSegment(
            id=5,
            start=38.0,
            end=43.0,
            text="Haz clic en el enlace para entrar en la lista de interés.",
        ),
    ]
    transcription = TranscriptionResult(
        audio_path="/fixtures/comision.wav",
        language="es",
        text=" ".join(segment.text for segment in segments),
        segments=segments,
        model="fixture",
        raw_response={"duration": 43.0},
        provider="quality-fixture",
    )

    return CopyAnalysisFixture(
        fixture_id="spanish_commission_course_v1",
        transcription=transcription,
        expected_hook="Tu comisión puede construir tu futuro o desaparecer cada mes.",
        expected_section_order=(
            "hook",
            "problem",
            "agitation",
            "offer",
            "promise",
            "cta",
        ),
        expected_product="Curso La Ruta de la Comisión",
        expected_audience="Agrónomos que reciben comisiones",
        expected_call_to_action="Entrar en la lista de interés",
        explicitly_absent_elements=(
            "price",
            "payment terms",
            "guarantee",
            "bonus",
            "testimonial",
            "quantified result",
            "deadline",
            "urgency",
            "scarcity",
        ),
    )


def _run_workflow(
    fixture: CopyAnalysisFixture,
    llm: OpenAILLM,
) -> tuple[CopyAnalysisOutput, dict]:
    """Execute the real workflow and return its consolidated analysis and state."""

    context = CopyAnalysisWorkflowContext(analysis_llm=llm)
    initial_state: CopyAnalysisState = {
        "transcription": fixture.transcription,
    }
    result = CopyAnalysisWorkflow(
        initial_state=dict(initial_state),
        context=context,
    ).start()
    analysis = result.get("analysis")

    if not isinstance(analysis, CopyAnalysisOutput):
        raise AssertionError("Workflow did not return CopyAnalysisOutput.")

    return analysis, result


def _judge_prompt(
    fixture: CopyAnalysisFixture,
    analysis: CopyAnalysisOutput,
) -> str:
    """Build a strict rubric without exposing source material through logs."""

    return f"""
You are an independent senior evaluator of direct-response copy analysis.

Evaluate the generated analysis only against the supplied transcript and
ground truth. Do not reward plausible marketing interpretations that are not
supported by the source.

Source transcript:
<source_transcript>
{fixture.transcription.model_dump_json(indent=2)}
</source_transcript>

Expected grounded facts:
<ground_truth>
fixture_id: {fixture.fixture_id}
expected_hook: {fixture.expected_hook}
expected_section_order: {list(fixture.expected_section_order)}
expected_product: {fixture.expected_product}
expected_audience: {fixture.expected_audience}
expected_call_to_action: {fixture.expected_call_to_action}
explicitly_absent_elements: {list(fixture.explicitly_absent_elements)}
</ground_truth>

Generated analysis:
<generated_analysis>
{analysis.model_dump_json(indent=2)}
</generated_analysis>

Evaluation rules:
- Judge semantic accuracy, not exact wording.
- A summarized section is valid only when its role is grounded in the source.
- Preserve the real chronological progression of source sections.
- Treat a timestamp as compatible when it points to source speech supporting
  that section and remains inside the transcript duration.
- A missing gap means the section is absent. An incomplete gap means it exists
  but lacks required information. A weak gap means it exists but persuades
  poorly.
- Offer facts require explicit or strongly implied transcript evidence.
- Any unsupported price, guarantee, bonus, proof, deadline, urgency, scarcity,
  or commercial condition is an invented offer element.
- Persuasion strength and weaknesses must follow the extracted structure and
  offer evidence. Strategic opinion must not be presented as an extracted fact.
- Textual explanations must remain in Spanish. Schema keys and canonical enum
  values remain in English.
- Cross-step contradictions include facts present in one output and denied,
  altered, or unsupported in another.
- Set passed=true only when every boolean criterion passes, no invented element
  or contradiction exists, every score is at least 0.80, and there is no
  critical issue.
"""


def _assert_timestamp_integrity(
    analysis: CopyAnalysisOutput,
    duration_seconds: float,
) -> None:
    """Reject inverted, out-of-range, or chronologically regressive timestamps."""

    previous_start = 0.0

    for section in analysis.copy_structure.sections:
        if section.start is None and section.end is None:
            continue

        assert section.start is not None
        assert section.end is not None
        assert 0.0 <= section.start <= section.end <= duration_seconds
        assert section.start >= previous_start
        previous_start = section.start


def _normalized_words(value: str | None) -> set[str]:
    """Return comparable lowercase word tokens for semantic stability checks."""

    if not value:
        return set()

    return set(re.findall(r"\w+", value.casefold(), flags=re.UNICODE))


def _word_overlap(left: str | None, right: str | None) -> float:
    """Measure retained vocabulary relative to the shorter phrase."""

    left_words = _normalized_words(left)
    right_words = _normalized_words(right)

    if not left_words or not right_words:
        return 0.0

    return len(left_words & right_words) / min(len(left_words), len(right_words))


def _sequence_stability(left: list[str], right: list[str]) -> float:
    """Return the longest-common-subsequence ratio for two section sequences."""

    if not left or not right:
        return 0.0

    previous = [0] * (len(right) + 1)

    for left_item in left:
        current = [0]
        for index, right_item in enumerate(right, start=1):
            if left_item == right_item:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(previous[index], current[-1]))
        previous = current

    return previous[-1] / max(len(left), len(right))


def test_live_copyanalysis_quality(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generate and independently judge one grounded copy analysis."""

    monkeypatch.chdir(tmp_path)
    models = _live_models()
    fixture = _fixture()

    logger.info(
        "Starting copy analysis quality eval: fixture_id={}, provider=openai, "
        "generation_model={}, judge_model={}, schema={}, structured_max_attempts={}",
        fixture.fixture_id,
        models.generation_model,
        models.judge_model,
        CopyAnalysisQualityEvaluation.__name__,
        models.generator.max_attempts,
    )

    workflow_started = time.perf_counter()
    analysis, result = _run_workflow(fixture, models.generator)
    workflow_duration = time.perf_counter() - workflow_started

    assert analysis.copy_structure == result["copy_structure"]
    assert analysis.offer_analysis == result["offer_analysis"]
    assert analysis.persuasion_analysis == result["persuasion_analysis"]
    assert analysis.offer_analysis.price_or_terms is None
    assert analysis.offer_analysis.bonuses == []
    assert analysis.offer_analysis.proof_elements == []
    assert analysis.offer_analysis.urgency_or_scarcity == []
    _assert_timestamp_integrity(analysis, duration_seconds=43.0)

    judge_started = time.perf_counter()
    evaluation = models.judge.structured(
        prompt=_judge_prompt(fixture, analysis),
        system_prompt="Evaluate the copy analysis strictly against the rubric.",
        prompt_cache_key="eval:copy-analysis-quality",
        output_schema=CopyAnalysisQualityEvaluation,
    )
    judge_duration = time.perf_counter() - judge_started

    logger.info(
        "Completed copy analysis quality eval: fixture_id={}, status={}, "
        "workflow_duration_seconds={:.3f}, judge_duration_seconds={:.3f}, "
        "workflow_input_tokens={}, workflow_output_tokens={}, judge_input_tokens={}, "
        "judge_output_tokens={}",
        fixture.fixture_id,
        "passed" if evaluation.passed else "failed",
        workflow_duration,
        judge_duration,
        result.get("input_tokens", 0),
        result.get("output_tokens", 0),
        models.judge.token_usage()["input_tokens"],
        models.judge.token_usage()["output_tokens"],
    )

    assert evaluation.structure_grounding_score >= 0.80
    assert evaluation.offer_grounding_score >= 0.80
    assert evaluation.persuasion_coherence_score >= 0.80
    assert evaluation.cross_step_consistency_score >= 0.80
    assert evaluation.hook_correct is True
    assert evaluation.section_order_preserved is True
    assert evaluation.gap_classification_coherent is True
    assert evaluation.timestamps_compatible is True
    assert evaluation.offer_facts_correct is True
    assert evaluation.invented_sections == []
    assert evaluation.invented_offer_elements == []
    assert evaluation.persuasion_supported_by_evidence is True
    assert evaluation.analysis_language_correct is True
    assert evaluation.contradictions == []
    assert evaluation.critical_issues == []
    assert evaluation.passed is True


def test_live_copyanalysis_structural_stability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require stable structural fields across repeated zero-temperature runs."""

    monkeypatch.chdir(tmp_path)
    models = _live_models()
    fixture = _fixture()

    first, _ = _run_workflow(fixture, models.generator)
    second, _ = _run_workflow(fixture, models.generator)

    first_sections = [
        section.section_type
        for section in first.copy_structure.sections
    ]
    second_sections = [
        section.section_type
        for section in second.copy_structure.sections
    ]
    sequence_score = _sequence_stability(first_sections, second_sections)
    hook_score = _word_overlap(
        first.copy_structure.main_hook,
        second.copy_structure.main_hook,
    )

    logger.info(
        "Completed copy analysis stability eval: fixture_id={}, provider=openai, "
        "model={}, sequence_score={:.3f}, hook_score={:.3f}, status={}",
        fixture.fixture_id,
        models.generation_model,
        sequence_score,
        hook_score,
        "passed" if sequence_score >= 0.75 and hook_score >= 0.60 else "failed",
    )

    assert first.copy_structure.content_type.casefold() == (
        second.copy_structure.content_type.casefold()
    )
    assert sequence_score >= 0.75
    assert hook_score >= 0.60
