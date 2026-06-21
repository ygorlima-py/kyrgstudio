from typing import Annotated, Any, NotRequired, TypedDict
from operator import add

from kyrg.workflows.copyanalysis.schemas import CopyAnalysisOutput
from kyrg.workflows.copyadaptation.schemas import UserProfileOutput

class CopyAdaptationState(TypedDict):
    
    # Analise estrategica da copy de referencia gerada pelo CopyAnalysisWorkflow.
    copy_analysis: CopyAnalysisOutput
    # Perfil da nova oferta do usuario: produto, publico, dores, provas, CTA e restricoes.
    user_profile: UserProfileOutput

    max_words_per_minute: NotRequired[int]
    min_words_per_minute: NotRequired[int]
    
    # Tokens de entrada gastos pelas chamadas de LLM deste workflow.
    input_tokens: NotRequired[Annotated[int, add]]
    # Tokens de saida gerados pelas chamadas de LLM deste workflow.
    output_tokens: NotRequired[Annotated[int, add]]
    # Soma dos tokens de entrada e saida.
    total_tokens: NotRequired[Annotated[int, add]]

    # Secoes da copy de referencia mapeadas para a nova oferta do usuario.
    mapped_sections: NotRequired[list[dict[str, Any]]]
    # Secoes que nao existem na referencia e precisam ser criadas do zero.
    sections_to_create: NotRequired[list[str]]
    # Pontos fracos ou lacunas que precisam ser corrigidos na nova copy.
    gaps_to_fix: NotRequired[list[str]]
    # Idioma final em que o roteiro adaptado deve ser escrito.
    target_language: NotRequired[str]
    # Plataforma ou canal onde a VSL/criativo sera usado.
    platform: NotRequired[str]
    # Duracao desejada do roteiro em minutos.
    desired_duration: NotRequired[float]

    # Angulo principal escolhido para vender a nova oferta.
    main_angle: NotRequired[str]
    # Nivel de consciencia do publico sobre o problema e a solucao.
    awareness_level: NotRequired[str]
    # Promessa central da nova copy.
    main_promise: NotRequired[str]
    # Padrao persuasivo escolhido, como PAS, AIDA, BAB ou Hybrid.
    persuasion_pattern: NotRequired[str]
    # Objecoes principais que o roteiro precisa responder.
    objections_to_address: NotRequired[list[str]]
    # Plano de provas que indica quais evidencias usar em cada parte do roteiro.
    proof_plan: NotRequired[dict[str, Any]]
    # Mecanismo unico que explica por que a oferta funciona ou e diferente.
    unique_mechanism: NotRequired[str]

    # Secoes escritas do roteiro adaptado.
    sections: NotRequired[list[dict[str, Any]]]
    # Problemas de continuidade, coerencia ou transicao encontrados entre secoes.
    flow_issues: NotRequired[list[str]]
    # Instrucoes estruturadas do review para orientar a proxima tentativa de escrita.
    revision_instructions: NotRequired[list[dict[str, Any]]]
    # Quantidade de tentativas de reescrita das secoes apos falha na revisao de fluxo.
    retry_count_correction_section: NotRequired[int]
    
    retry_count_correction_script: NotRequired[int]
    
    # Secoes revisadas depois da analise de fluxo.
    sections_revised: NotRequired[list[dict[str, Any]]]
    # Indica se o fluxo entre as secoes foi aprovado.
    flow_approved: NotRequired[bool]

    # Indica se o roteiro passou nas validacoes finais.
    validation_passed: NotRequired[bool]
    # Erros criticos que impedem o uso do roteiro.
    validation_errors: NotRequired[list[str]]
    # Avisos nao bloqueantes que devem ser mostrados ao usuario.
    validation_warnings: NotRequired[list[str]]

    # Quantidade total de palavras do roteiro.
    word_count: NotRequired[int]
    # Explicacao do que foi mantido da referencia e o que foi adaptado.
    adaptation_notes: NotRequired[str]
    # Lista de secoes que precisam de prova real antes de usar em producao.
    missing_proofs: NotRequired[list[str]]
    # Output final consolidado do workflow.
    adapted_script: NotRequired[dict[str, Any]]

    sections_before_script_correction: NotRequired[list[dict[str, Any]]]
    
    sections_after_script_correction: NotRequired[list[dict[str, Any]]]
    
    timing_metrics: NotRequired[dict[str, Any]]