from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

from kyrg.llms.base import LLMBase


@dataclass(frozen=True)
class CopyAdaptationWorkflowContext:
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


class UserProfileOutput(BaseModel):
    # Produto, servico, metodo ou solucao que o novo roteiro vai vender.
    product_or_solution: str = Field(
        description="Product, service, method, opportunity, or solution being promoted."
    )
    # Publico que o roteiro deve atingir.
    target_audience: str = Field(
        description="Audience the adapted script should speak to."
    )
    # Principal dor, problema ou obstaculo desse publico.
    core_problem: str = Field(
        description="Main problem, pain, frustration, or obstacle the audience has."
    )
    # Principal desejo ou transformacao que esse publico quer alcancar.
    core_desire: str = Field(
        description="Main desired outcome, aspiration, or transformation."
    )
    # Promessa principal permitida para a oferta.
    main_promise: str = Field(
        description="Main promise the adapted script is allowed to make."
    )
    # Mecanismo, metodo ou explicacao que torna a oferta diferente e crivel.
    unique_mechanism: str | None = Field(
        default=None,
        description="Mechanism, method, angle, or explanation that makes the offer credible and different."
    )
    # Beneficios reais que podem ser usados no roteiro.
    benefits: list[str] = Field(
        default_factory=list,
        description="Benefits that can be used in the adapted script."
    )
    # Objecoes, medos ou duvidas que o roteiro precisa responder.
    objections: list[str] = Field(
        default_factory=list,
        description="Objections, doubts, fears, or barriers the script should address."
    )
    # Provas reais disponiveis, como depoimentos, dados, estudos, prints ou demonstracoes.
    proof_assets: list[str] = Field(
        default_factory=list,
        description="Real proof available for the script, such as testimonials, data, cases, demonstrations, or credentials."
    )
    # Detalhes comerciais da oferta, como preco, garantia, bonus, prazo ou condicoes.
    offer_details: str | None = Field(
        default=None,
        description="Commercial details such as price, guarantee, bonuses, deadline, or payment terms."
    )
    # Acao que o espectador deve tomar ao final do roteiro.
    call_to_action: str = Field(
        description="Action the viewer should take after watching the script."
    )
    # Tom de voz desejado para o roteiro.
    tone: str | None = Field(
        default=None,
        description="Desired tone of voice for the adapted script."
    )
    # Idioma em que o roteiro adaptado deve ser escrito.
    target_language: str | None = Field(
        default=None,
        description="Language the adapted script should be written in."
    )
    # Plataforma ou canal onde o roteiro sera usado.
    platform: str | None = Field(
        default=None,
        description="Distribution platform or placement for the adapted script."
    )
    # Duracao desejada do roteiro em minutos.
    desired_duration: float | None = Field(
        default=None,
        description="Desired script duration in minutes."
    )
    # Promessas, palavras, temas ou angulos que nao podem ser usados.
    restrictions: list[str] = Field(
        default_factory=list,
        description="Claims, words, promises, or angles that must not be used."
    )


class BuildCopyStrategyOutput(BaseModel):
    # Angulo principal que vai guiar toda a nova copy.
    main_angle: str = Field(
        description="Primary strategic angle that should drive the adapted copy."
    )
    # Nivel de consciencia do publico; define se a copy deve educar mais ou vender mais direto.
    awareness_level: Literal[
        "unaware",
        "problem_aware",
        "solution_aware",
        "product_aware",
        "most_aware",
    ] = Field(
        description="Audience awareness level that determines how direct or educational the opening strategy should be."
    )
    # Promessa central do roteiro, limitada ao que o briefing permite.
    main_promise: str = Field(
        description="Central promise of the adapted script, constrained by the user profile."
    )
    # Estrutura persuasiva escolhida para organizar a copy.
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
    # Objecoes prioritarias que o roteiro precisa quebrar.
    objections_to_address: list[str] = Field(
        default_factory=list,
        description="Prioritized objections the adapted script should address."
    )
    # Plano de quais provas usar em cada parte importante do roteiro.
    proof_plan: dict[str, str] = Field(
        default_factory=dict,
        description="Plan describing which proof asset or proof type should support each relevant section."
    )
    # Mecanismo ou explicacao que torna a oferta crivel e diferente.
    unique_mechanism: str = Field(
        description="Mechanism, method, or explanation that makes the adapted offer feel credible and different."
    )
    # Explicacao curta do motivo da estrategia escolhida.
    strategy_notes: str = Field(
        description="Short explanation of why this strategy was chosen and how it uses the reference copy analysis."
    )


class ScriptSectionOutput(BaseModel):
    # Ordem da secao dentro do roteiro adaptado.
    order: int = Field(
        description="Position of this section inside the adapted script."
    )
    # Tipo canonico da secao. Esse valor deve continuar em ingles.
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
    # Texto final escrito para essa secao, pronto para revisao de fluxo.
    text: str = Field(
        description="Written script copy for this section, in the target language."
    )
    # Papel persuasivo dessa secao dentro do roteiro.
    purpose: str = Field(
        description="Strategic persuasive role of this section in the adapted script."
    )
    # Indica se a secao veio de uma referencia ou foi criada do zero.
    adaptation_mode: Literal[
        "adapted_from_reference",
        "created_from_scratch",
    ] = Field(
        description="Whether this section was adapted from a mapped reference section or created from scratch."
    )
    # Tipo da secao original usada como referencia, quando existir.
    source_reference_section_type: str | None = Field(
        default=None,
        description="Reference section type used as inspiration, when this section was adapted from the original copy."
    )
    # Prova real usada nesta secao, se houver.
    proof_used: str | None = Field(
        default=None,
        description="Real proof asset or proof instruction used in this section, when available."
    )
    # Indica se esta secao precisaria de prova, mas nao havia prova disponivel.
    missing_proof: bool = Field(
        default=False,
        description="Whether this section needs proof but no valid proof asset was available."
    )
    # Observacao curta para ajudar o proximo node a revisar a transicao.
    transition_hint: str | None = Field(
        default=None,
        description="Short note explaining how this section should connect to the next one."
    )
    # Estimativa de palavras desta secao.
    word_count: int = Field(
        description="Estimated number of words in this section."
    )


class WriteScriptSectionsOutput(BaseModel):
    # Secoes escritas do roteiro adaptado, ainda sem revisao final de fluxo.
    sections: list[ScriptSectionOutput] = Field(
        default_factory=list,
        description="Ordered written sections of the adapted script."
    )
    # Secoes ou momentos que precisam de prova real antes de usar em producao.
    missing_proofs: list[str] = Field(
        default_factory=list,
        description="Sections or claims that need real proof before the script can be safely used."
    )
    # Explicacao curta do que foi adaptado, criado do zero ou protegido por restricoes.
    adaptation_notes: str = Field(
        description="Short explanation of how the reference copy was adapted to the user offer."
    )
    # Quantidade total estimada de palavras geradas.
    word_count: int = Field(
        description="Estimated total number of words across all written sections."
    )


class SectionRevisionInstruction(BaseModel):
    # Ordem da secao que precisa de revisao, quando o problema for localizado.
    section_order: int | None = Field(
        default=None,
        description="Order of the section that needs revision, when the issue is tied to a specific section."
    )
    # Tipo da secao afetada, quando aplicavel.
    section_type: str | None = Field(
        default=None,
        description="Type of the section that needs revision, such as hook, promise, mechanism, objection, offer, or cta."
    )
    # Problema especifico encontrado no fluxo.
    issue: str = Field(
        description="Specific flow, continuity, sequence, or transition problem found in the script."
    )
    # Acao concreta que o node de escrita deve executar no retry.
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
    # Instrucao clara para o node de escrita seguir no retry.
    instruction: str = Field(
        description="Clear instruction that write_script_sections must follow on retry."
    )
    # Prioridade da revisao.
    priority: Literal["low", "medium", "high"] = Field(
        description="Priority of the revision instruction."
    )


class ReviewSectionFlowOutput(BaseModel):
    # Indica se as secoes formam uma sequencia coerente e pronta para validacao.
    flow_approved: bool = Field(
        description="Whether the section sequence is coherent enough to proceed to final validation."
    )
    # Problemas especificos de continuidade, ordem, contradicao ou transicao.
    flow_issues: list[str] = Field(
        default_factory=list,
        description="Specific and actionable flow issues that should be fixed if the script is not approved."
    )
    # Instrucoes estruturadas para orientar o retry do node de escrita.
    revision_instructions: list[SectionRevisionInstruction] = Field(
        default_factory=list,
        description="Structured revision instructions for write_script_sections when retry is needed."
    )
    # Apenas as secoes que tiveram ajustes pequenos de transicao ou continuidade.
    sections_revised: list[ScriptSectionOutput] = Field(
        default_factory=list,
        description="Only the sections that were actually revised during the flow review."
    )


class ValidateScriptOutput(BaseModel):
    # Indica se o roteiro passou sem erros criticos.
    validation_passed: bool = Field(
        description="Whether the adapted script passed validation without critical blocking errors."
    )
    # Erros criticos que impedem o roteiro de ser entregue como pronto.
    validation_errors: list[str] = Field(
        default_factory=list,
        description="Critical validation errors that block the script from being production-ready."
    )
    # Avisos nao bloqueantes que devem ser exibidos ou considerados antes do uso.
    validation_warnings: list[str] = Field(
        default_factory=list,
        description="Non-blocking validation warnings that should be reviewed before production."
    )


class AdaptedScriptOutput(BaseModel):
    # Roteiro completo em formato legivel para revisao humana.
    script: str = Field(
        description="Complete adapted script assembled from the approved sections."
    )
    # Secoes finais usadas para montar o roteiro.
    sections: list[ScriptSectionOutput] = Field(
        default_factory=list,
        description="Final ordered sections used to assemble the adapted script."
    )
    # Variacoes ou textos de hook encontrados no roteiro final.
    hooks: list[str] = Field(
        default_factory=list,
        description="Hook texts extracted from the final script sections."
    )
    # Chamada para acao principal do roteiro.
    cta: str | None = Field(
        default=None,
        description="Primary call to action extracted from the final script."
    )
    # Duracao estimada em minutos com base na quantidade de palavras.
    estimated_duration: float | None = Field(
        default=None,
        description="Estimated spoken duration in minutes."
    )
    # Quantidade total de palavras do roteiro final.
    word_count: int = Field(
        description="Total estimated word count of the final adapted script."
    )
    # Texto limpo para TTS, sem markdown ou metadados.
    voice_ready_text: str = Field(
        description="Clean narration text ready for text-to-speech generation."
    )
    # Entrada inicial para o futuro workflow de planejamento de cenas.
    scene_planning_input: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Structured section data prepared for a future scene planning workflow."
    )
    # Explicacao do que foi adaptado e quais cuidados foram aplicados.
    adaptation_notes: str | None = Field(
        default=None,
        description="Notes explaining what was adapted from the reference and what changed."
    )
    # Avisos de validacao nao bloqueantes.
    validation_warnings: list[str] = Field(
        default_factory=list,
        description="Non-blocking validation warnings inherited from script validation."
    )
    # Erros criticos de validacao, se existirem.
    validation_errors: list[str] = Field(
        default_factory=list,
        description="Critical validation errors inherited from script validation."
    )
    # Indica se o roteiro passou na validacao final.
    validation_passed: bool = Field(
        description="Whether the final adapted script passed validation."
    )
    # Secoes ou claims que precisam de prova real antes de uso em producao.
    missing_proofs: list[str] = Field(
        default_factory=list,
        description="Proof gaps that should be reviewed before production."
    )
