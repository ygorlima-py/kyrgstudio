"""Live quality evaluations for CopyAdaptationWorkflow.

This module is excluded from normal deterministic test runs. Enable it with
``KYRG_RUN_COPYADAPTATION_EVALS=1`` and provide both ``OPENAI_API_KEY`` and
``KYRG_COPYADAPTATION_EVAL_MODEL``.
"""

import json
import os
from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from kyrg.llms.openai_llm import OpenAILLM
from kyrg.workflows.copyadaptation.schemas import (
    CopyAdaptationWorkflowContext,
    UserProfileOutput,
)
from kyrg.workflows.copyadaptation.state import CopyAdaptationState
from kyrg.workflows.copyadaptation.workflow import CopyAdaptationWorkflow
from kyrg.workflows.copyanalysis.schemas import (
    CopyAnalysisOutput,
    CopySection,
    CopyStructureOutput,
    OfferAnalysisOutput,
    PersuasionAnalysisOutput,
)


pytestmark = pytest.mark.live_eval


class CopyQualityEvaluation(BaseModel):
    """Structured rubric returned by the independent quality judge."""

    reference_structure_score: float = Field(ge=0, le=1)
    respects_user_profile: bool
    invented_proof: bool
    invented_offer_details: bool
    respects_restrictions: bool
    target_language_correct: bool
    transitions_coherent: bool
    correction_improved_or_not_required: bool
    issues: list[str] = Field(default_factory=list)


def _live_llm() -> OpenAILLM:
    """Create the explicitly configured model used by generation and judging."""

    if os.getenv("KYRG_RUN_COPYADAPTATION_EVALS") != "1":
        pytest.skip("Live copy adaptation evals are disabled.")

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("KYRG_COPYADAPTATION_EVAL_MODEL")

    if not api_key or not model:
        pytest.skip(
            "OPENAI_API_KEY and KYRG_COPYADAPTATION_EVAL_MODEL are required."
        )

    return OpenAILLM(api_key=api_key, model=model, temperature=0.0)


def _copy_analysis() -> CopyAnalysisOutput:
    """Return a stable reference-copy analysis used across quality runs."""

    return CopyAnalysisOutput(
        language="Portuguese",
        copy_structure=CopyStructureOutput(
            language="Portuguese",
            content_type="VSL",
            main_hook="Seu dinheiro deveria trabalhar por você.",
            sections=[
                CopySection(
                    section_type="hook",
                    text="Seu dinheiro deveria trabalhar por você.",
                    purpose="Criar curiosidade sobre organização financeira.",
                ),
                CopySection(
                    section_type="problem",
                    text="Erros comuns impedem a construção de patrimônio.",
                    purpose="Apresentar o custo da falta de planejamento.",
                ),
                CopySection(
                    section_type="education",
                    text="A referência explica erros e princípios financeiros.",
                    purpose="Educar antes de apresentar uma solução.",
                ),
                CopySection(
                    section_type="offer",
                    text="Uma solução educacional organiza os próximos passos.",
                    purpose="Apresentar a solução depois da educação.",
                ),
                CopySection(
                    section_type="cta",
                    text="Comece com o que você tem.",
                    purpose="Convidar o espectador para o próximo passo.",
                ),
            ],
            narrative_flow=["hook", "problem", "education", "offer", "cta"],
            section_gaps=[],
            summary="A referência educa sobre erros financeiros antes da oferta.",
        ),
        offer_analysis=OfferAnalysisOutput(
            product_or_solution="Educação financeira",
            target_audience="Pessoas iniciando seus investimentos",
            core_problem="Falta de planejamento financeiro",
            core_desire="Construir patrimônio no longo prazo",
            main_promise="Começar a investir com mais clareza",
            unique_mechanism="Educação baseada em erros comuns",
            call_to_action="Começar com os recursos disponíveis",
            summary="Conteúdo educativo com transição para uma solução.",
        ),
        persuasion_analysis=PersuasionAnalysisOutput(
            dominant_emotion="confiança",
            persuasion_pattern="education-to-offer",
            hook_strength="high",
            promise_clarity="medium",
            proof_strength="low",
            urgency_strength="low",
            cta_strength="medium",
            summary="A persuasão combina educação e uma chamada prática.",
        ),
    )


def _user_profile() -> UserProfileOutput:
    """Return the target offer and strict truth constraints for the evaluation."""

    return UserProfileOutput(
        product_or_solution=(
            "Curso de finanças pessoais do básico ao avançado para agrônomos"
        ),
        target_audience=(
            "Agrônomos que recebem comissões, querem investir e ainda não sabem "
            "como planejar o futuro"
        ),
        core_problem=(
            "Recebem renda variável, mas não possuem método para organizar, "
            "diversificar e investir no longo prazo"
        ),
        core_desire=(
            "Transformar parte das comissões em uma carteira diversificada e "
            "adequada aos próprios objetivos"
        ),
        main_promise=(
            "Ensinar um processo educacional para organizar as finanças e tomar "
            "decisões de investimento mais conscientes"
        ),
        unique_mechanism="Método Comissão Organizada",
        benefits=[
            "Aprender juros simples e compostos",
            "Conhecer classes de investimentos",
            "Planejar uma carteira diversificada de longo prazo",
        ],
        objections=[
            "Não sei por onde começar",
            "Minha comissão varia todos os meses",
        ],
        proof_assets=[],
        offer_details=None,
        call_to_action="Entrar na lista de interesse do curso",
        tone="Educacional, direto e responsável",
        target_language="Portuguese",
        platform="YouTube",
        desired_duration=1.5,
        restrictions=[
            "Não prometer retorno financeiro",
            "Não inventar preço, garantia, bônus, suporte ou escassez",
            "Não inventar depoimentos, resultados ou credenciais",
        ],
    )


def _judge_prompt(
    analysis: CopyAnalysisOutput,
    profile: UserProfileOutput,
    result: dict,
) -> str:
    """Build a strict evidence-based rubric prompt for the independent judge."""

    return f"""
You are an independent senior direct-response quality evaluator.

Evaluate the adapted script only against the supplied reference analysis and
user profile. Do not reward persuasive language that violates source truth.

Reference analysis:
<reference_analysis>
{analysis.model_dump_json(indent=2)}
</reference_analysis>

User profile:
<user_profile>
{profile.model_dump_json(indent=2)}
</user_profile>

Workflow result:
<workflow_result>
{json.dumps(result, ensure_ascii=False, indent=2, default=str)}
</workflow_result>

Rubric:
- reference_structure_score measures preservation of persuasive roles and
  sequence, not literal wording.
- respects_user_profile is false if product, audience, promise, CTA, tone, or
  mechanism changes meaning.
- invented_proof is true for any unsupported testimonial, number, result,
  credential, research, demonstration, or authority claim.
- invented_offer_details is true for unsupported price, guarantee, bonus,
  support, module, delivery format, deadline, scarcity, or availability claim.
- respects_restrictions requires every user restriction to be followed.
- target_language_correct requires script narration to be Portuguese.
- transitions_coherent requires a logical spoken progression between sections.
- correction_improved_or_not_required is true when no correction was necessary,
  or when the final version fixes reported errors without damaging valid parts.
- issues must contain concise evidence for every false result.
"""


def test_live_copy_quality(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generate and judge one complete adaptation against the product rubric."""

    monkeypatch.chdir(tmp_path)
    llm = _live_llm()
    analysis = _copy_analysis()
    profile = _user_profile()
    context = CopyAdaptationWorkflowContext(
        strategy_llm=llm,
        writing_llm=llm,
        review_llm=llm,
        validation_llm=llm,
        max_retry=2,
    )
    initial_state: CopyAdaptationState = {
        "copy_analysis": analysis,
        "user_profile": profile,
    }
    workflow = CopyAdaptationWorkflow(
        initial_state=dict(initial_state),
        context=context,
    )

    result = workflow.start()
    evaluation = llm.structured(
        prompt=_judge_prompt(analysis, profile, result),
        output_schema=CopyQualityEvaluation,
    )

    adapted_script = result["adapted_script"]
    target_seconds = profile.desired_duration * 60

    assert adapted_script["validation_passed"] is True
    assert 0.85 * target_seconds <= adapted_script[
        "estimated_duration_seconds"
    ] <= 1.15 * target_seconds
    assert evaluation.reference_structure_score >= 0.7
    assert evaluation.respects_user_profile is True
    assert evaluation.invented_proof is False
    assert evaluation.invented_offer_details is False
    assert evaluation.respects_restrictions is True
    assert evaluation.target_language_correct is True
    assert evaluation.transitions_coherent is True
    assert evaluation.correction_improved_or_not_required is True

