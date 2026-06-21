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

    run_id = "finance_agronomos_v8"
    database_path = "src/data/checkpoints/kyrg_workflows.sqlite"
    source_path = "src/data/input/video_teste.mp4"
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
    product_or_solution="ClarePure - creme facial noturno para tratamento de acne e espinhas inflamadas",
    
    target_audience="Mulheres de 18 a 32 anos com pele oleosa a mista, que sofrem de acne hormonal recorrente e já tentaram outros produtos sem sucesso duradouro",
    
    core_problem="Espinhas inflamadas que voltam sempre, principalmente antes do período menstrual, causando baixa autoestima e frustração com produtos que prometem e não cumprem",
    
    core_desire="Ter uma pele limpa, uniforme e sem inflamações, podendo sair de casa sem maquiagem e se sentir confiante em fotos e no dia a dia",
    
    main_promise="Reduza visivelmente as espinhas inflamadas em até 14 dias de uso contínuo",
    
    unique_mechanism="Complexo Niacinamida 10% + Ácido Salicílico microencapsulado, que penetra nos poros de forma gradual durante a noite, reduzindo irritação comparado a tratamentos tradicionais",
    
    benefits=[
        "Reduz vermelhidão e inflamação em poucos dias",
        "Não resseca a pele como outros tratamentos com ácido",
        "Textura leve, não deixa a pele oleosa pela manhã",
        "Ajuda a prevenir novas espinhas com uso contínuo",
        "Dermatologicamente testado para peles sensíveis"
    ],
    
    objections=[
        "Já tentei muitos produtos e nenhum funcionou para mim",
        "Tenho medo de irritar ainda mais minha pele",
        "Acho que vai ser caro demais para o resultado",
        "Não tenho tempo para rotina complicada de skincare",
        "Será que funciona pra acne hormonal mesmo?"
    ],
    
    proof_assets=[
        "Estudo clínico com 120 participantes mostrando 78% de redução nas lesões inflamatórias em 30 dias",
        "Mais de 4.300 avaliações no site com média 4.7/5 estrelas",
        "Depoimento em vídeo da influenciadora @paulacosmeticos mostrando resultado de 21 dias",
        "Antes e depois de clientes reais postados no Instagram da marca",
        "Aprovado pela Sociedade Brasileira de Dermatologia (selo SBD)"
    ],
    
    offer_details="R$ 89,90 (de R$ 149,90) na compra do kit com 2 unidades, frete grátis para todo Brasil, garantia de 30 dias ou seu dinheiro de volta",
    
    call_to_action="Clique no link abaixo e garanta seu ClarePure com 40% de desconto antes que o estoque promocional acabe",
    
    tone="Empático, acolhedor e direto, like a friend giving honest advice — sem ser alarmista ou usar medo excessivo",
    
    target_language="Português (Brasil)",
    
    platform="Instagram Reels / TikTok",
    
    desired_duration=1.5,
    
    restrictions=[
        "Não prometer cura definitiva da acne",
        "Não usar a palavra 'milagroso' ou 'instantâneo'",
        "Não comparar diretamente com marcas concorrentes pelo nome",
        "Não usar antes/depois que pareçam editados ou irreais",
        "Não fazer promessas médicas (este não é produto medicamentoso registrado em ANVISA como fármaco)"
        ]
    )

    copyadaptation_workflow = CopyAdaptationWorkflow(
        initial_state={
            "copy_analysis": copy_analysis,
            "user_profile": user_profile,
            "max_words_per_minute": 160,
            "min_words_per_minute": 140,
        },
        context=CopyAdaptationWorkflowContext(
            strategy_llm=strategy_llm,
            writing_llm=writing_llm,
            review_llm=review_llm,
            validation_llm=validation_llm,
            max_retry=2
        ),
        checkpointer=SQLiteCheckpointer(database_path=database_path),
        thread_id=f"{run_id}:copyadaptation",
    )

    copyadaptation_result = copyadaptation_workflow.start()
    adapted_script = copyadaptation_result.get("adapted_script") or {}

    print("\n[bold]Roteiro adaptado[/bold]\n")
    print(adapted_script.get("script"))

    print("\n[bold]Validação[/bold]\n")
    print(
        {
            "validation_passed": adapted_script.get("validation_passed"),
            "validation_errors": adapted_script.get("validation_errors"),
            "validation_warnings": adapted_script.get("validation_warnings"),
            "missing_proofs": adapted_script.get("missing_proofs"),
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
