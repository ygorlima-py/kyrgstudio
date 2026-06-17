import os
from pathlib import Path

from dotenv import load_dotenv
from rich import print

from kyrg.llms.openai_llm import OpenAILLM
from kyrg.transcribers.local_model import TranscriberWhisperLocal
from kyrg.workflows.checkpointers import SQLiteCheckpointer
from kyrg.workflows.copyadaptation.schemas import (
    CopyAdaptationWorkflowContext,
    UserProfileOutput,
)
from kyrg.workflows.copyadaptation.workflow import CopyAdaptationWorkflow
from kyrg.workflows.copyanalysis.schemas import CopyAnalysisWorkflowContext
from kyrg.workflows.copyanalysis.workflow import CopyAnalysisWorkflow
from kyrg.workflows.transcriber.schemas import (
    TranscriberWorkflowContext,
    TranscriptorConfig,
)
from kyrg.workflows.transcriber.workflow import TranscriberWorkflow


class OpenRouterLLM(OpenAILLM):
    BASE_URL = "https://openrouter.ai/api/v1"


if __name__ == "__main__":
    load_dotenv()

    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

    if openrouter_api_key is None:
        raise RuntimeError("OPENROUTER_API_KEY is required to run this workflow test.")

    Path("src/data/output").mkdir(parents=True, exist_ok=True)
    Path("src/data/checkpoints").mkdir(parents=True, exist_ok=True)

    run_id = "finance_agronomos_v2"
    database_path = "src/data/checkpoints/kyrg_workflows.sqlite"
    source_path = "src/data/input/video_spanish.mp4"
    audio_path = "src/data/output/audio_extraido.wav"

    transcriber_llm = OpenRouterLLM(
        api_key=openrouter_api_key,
        model="deepseek/deepseek-v4-flash",
        temperature=0.0,
    )
    copy_analysis_llm = OpenRouterLLM(
        api_key=openrouter_api_key,
        model="deepseek/deepseek-v4-flash",
        temperature=0.3,
    )
    strategy_llm = OpenRouterLLM(
        api_key=openrouter_api_key,
        model="deepseek/deepseek-v4-flash",
        temperature=0.3,
    )
    writing_llm = OpenRouterLLM(
        api_key=openrouter_api_key,
        model="deepseek/deepseek-v4-flash",
        temperature=0.7,
    )
    review_llm = OpenRouterLLM(
        api_key=openrouter_api_key,
        model="deepseek/deepseek-v4-flash",
        temperature=0.2,
    )
    validation_llm = OpenRouterLLM(
        api_key=openrouter_api_key,
        model="deepseek/deepseek-v4-flash",
        temperature=0.0,
    )

    transcriber_workflow = TranscriberWorkflow(
        initial_state={
            "source_path": source_path,
            "source_type": "video",
            "audio_path": audio_path,
            "model_name": "small",
            "language": "es",
            "need_correction": False,
        },
        context=TranscriberWorkflowContext(
            correction_llm=transcriber_llm,
            extract_context_llm=transcriber_llm,
            transcriptor_config=TranscriptorConfig(
                transcriptor=TranscriberWhisperLocal,
            ),
        ),
        checkpointer=SQLiteCheckpointer(database_path=database_path),
        thread_id=f"{run_id}:transcriber",
    )

    transcriber_result = transcriber_workflow.start()
    transcription = transcriber_result.get("final_result") or transcriber_result.get("result")

    if transcription is None:
        raise RuntimeError("Transcriber workflow finished without transcription result.")

    copyanalysis_workflow = CopyAnalysisWorkflow(
        initial_state={
            "transcription": transcription,
        },
        context=CopyAnalysisWorkflowContext(
            analysis_llm=copy_analysis_llm,
        ),
        checkpointer=SQLiteCheckpointer(database_path=database_path),
        thread_id=f"{run_id}:copyanalysis",
    )

    copyanalysis_result = copyanalysis_workflow.start()
    copy_analysis = copyanalysis_result.get("analysis")

    if copy_analysis is None:
        raise RuntimeError("CopyAnalysis workflow finished without analysis.")

    user_profile = UserProfileOutput(
        product_or_solution=(
            "Curso de finanças pessoais e investimentos para agrônomos, "
            "indo do básico ao avançado."
        ),
        target_audience=(
            "Agrônomos que recebem comissão, querem investir melhor esse dinheiro, "
            "mas ainda não sabem planejar o futuro financeiro."
        ),
        core_problem=(
            "Recebem comissão, mas não têm método para organizar, proteger e investir "
            "esse dinheiro com visão de longo prazo."
        ),
        core_desire=(
            "Aprender a investir com segurança, diversificar patrimônio e construir "
            "uma carteira sólida para o futuro."
        ),
        main_promise=(
            "Ensinar agrônomos a sair do básico em finanças e evoluir até uma estratégia "
            "de investimentos diversificada para longo prazo."
        ),
        unique_mechanism=(
            "Trilha progressiva que começa em juros simples e compostos, passa por "
            "planejamento financeiro, reserva, classes de ativos, diversificação e "
            "montagem de carteira."
        ),
        benefits=[
            "Entender juros simples e compostos sem linguagem complicada.",
            "Planejar o uso das comissões sem depender de tentativa e erro.",
            "Conhecer classes de investimentos e seus riscos.",
            "Aprender a diversificar uma carteira para longo prazo.",
            "Criar uma visão financeira mais estratégica para o futuro.",
        ],
        objections=[
            "Não sei nada sobre investimentos.",
            "Tenho medo de perder dinheiro.",
            "Não sei por onde começar.",
            "Minha renda varia por causa das comissões.",
            "Acho que investir é complicado demais.",
        ],
        proof_assets=[],
        offer_details=None,
        call_to_action="Entrar na lista de interesse do curso.",
        tone="Didático, direto, confiável e próximo da realidade do agrônomo.",
        target_language="português",
        platform="VSL para página de captura",
        desired_duration=2.5,
        restrictions=[
            "Não prometer enriquecimento rápido.",
            "Não prometer rentabilidade garantida.",
            "Não recomendar ativos específicos como garantia de resultado.",
            "Não usar linguagem sensacionalista.",
        ],
    )

    copyadaptation_workflow = CopyAdaptationWorkflow(
        initial_state={
            "copy_analysis": copy_analysis,
            "user_profile": user_profile,
        },
        context=CopyAdaptationWorkflowContext(
            strategy_llm=strategy_llm,
            writing_llm=writing_llm,
            review_llm=review_llm,
            validation_llm=validation_llm,
        ),
        checkpointer=SQLiteCheckpointer(database_path=database_path),
        thread_id=f"{run_id}:copyadaptation",
    )

    copyadaptation_result = copyadaptation_workflow.start()

    print("\n[bold]Roteiro adaptado[/bold]\n")
    print(copyadaptation_result.get("script"))

    print("\n[bold]Validação[/bold]\n")
    print(
        {
            "validation_passed": copyadaptation_result.get("validation_passed"),
            "validation_errors": copyadaptation_result.get("validation_errors"),
            "validation_warnings": copyadaptation_result.get("validation_warnings"),
            "missing_proofs": copyadaptation_result.get("missing_proofs"),
        }
    )

    print("\n[bold]Tokens[/bold]\n")
    print(
        {
            "transcriber": {
                "input": transcriber_result.get("input_tokens", 0),
                "output": transcriber_result.get("output_tokens", 0),
                "total": transcriber_result.get("total_tokens", 0),
            },
            "copyanalysis": {
                "input": copyanalysis_result.get("input_tokens", 0),
                "output": copyanalysis_result.get("output_tokens", 0),
                "total": copyanalysis_result.get("total_tokens", 0),
            },
            "copyadaptation": {
                "input": copyadaptation_result.get("input_tokens", 0),
                "output": copyadaptation_result.get("output_tokens", 0),
                "total": copyadaptation_result.get("total_tokens", 0),
            },
        }
    )
