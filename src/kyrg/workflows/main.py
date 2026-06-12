import os

from rich import print
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from kyrg.llms.openai_llm import OpenAILLM
from kyrg.transcribers.local_model import TranscriberWhisperLocal
from kyrg.workflows.transcriber.agent import TranscriptionAgent
from kyrg.workflows.transcriber.schemas import TranscriberWorkflowContext, TranscriptorConfig
from kyrg.workflows.transcriber.tools import (
    accept_transcription_tool,
    correct_transcription_tool,
    request_human_review_tool,
)
from kyrg.workflows.transcriber.workflow import TranscriberWorkflow
from kyrg.workflows.copyanalysis.schemas import CopyAnalysisWorkflowContext
from kyrg.workflows.copyanalysis.workflow import CopyAnalysisWorkflow
from kyrg.workflows.checkpointers import SQLiteCheckpointer

class OpenRouterLLM(OpenAILLM):
    BASE_URL = "https://openrouter.ai/api/v1"

if __name__ == "__main__":
    from pathlib import Path
    from weasyprint import HTML
    load_dotenv()

    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    
    workflow_llm = OpenRouterLLM(
        api_key=openrouter_api_key,
        model="deepseek/deepseek-chat",
        temperature=0.0,
    )
    
    agent = TranscriptionAgent(
        llm=ChatOpenAI(
            api_key=openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model="deepseek/deepseek-chat",
            temperature=0.0,
        ),
        tools=[
            accept_transcription_tool,
            correct_transcription_tool,
            request_human_review_tool,
        ],
        debug=True,
    )
    
    initial_state = {
        "source_path": "src/data/input/video_spanish.mp4",
        "source_type": "video",
        "audio_path": "src/data/output/audio_extraido.wav",
        "model_name": "small",
        "language": "es"
    }
    
    context = TranscriberWorkflowContext(
        correction_llm=workflow_llm,
        extract_context_llm=workflow_llm,
        transcriptor_config=TranscriptorConfig(
            transcriptor=TranscriberWhisperLocal
            ),
    )

    transcriber_workflow = TranscriberWorkflow(
        initial_state=initial_state,
        agent=agent,
        context=context,
        checkpointer=SQLiteCheckpointer(
            database_path="src/data/checkpoints/kyrg_workflows.sqlite",
            ),
        thread_id="teste_vsl_leo:transcriber2",
    )

    transcriber_result = transcriber_workflow.start()
    transcription = transcriber_result.get("final_result")
    
    if transcription is None:
        raise RuntimeError("Transcriber workflow finished without final_result.")

    copyanalysis_context = CopyAnalysisWorkflowContext(
        analysis_llm=workflow_llm,
    )

    copyanalysis_workflow = CopyAnalysisWorkflow(
        initial_state={
            "transcription": transcription,
        },
        context=copyanalysis_context,
        checkpointer=SQLiteCheckpointer(
                database_path="src/data/checkpoints/kyrg_workflows.sqlite",
            ),
        thread_id="teste_vsl_leo:copy_analysis2",
    )

    copyanalysis_result = copyanalysis_workflow.start()

    print(copyanalysis_result["analysis"])
    print()

    print("Quantidade de tokens gasta Transcriber\n")
    print(f"Entrada {transcriber_result['input_tokens']}")
    print(f"Saida {transcriber_result['output_tokens']}")
    print(f"Total {transcriber_result['total_tokens']}")
    print("________________________________________________\n\n")

    print("Quantidade de tokens gasta CopyAnalyse\n")
    print(f"Entrada {copyanalysis_result['input_tokens']}")
    print(f"Saida {copyanalysis_result['output_tokens']}")
    print(f"Total {copyanalysis_result['total_tokens']}")
    print("________________________________________________\n\n")

    total_input = transcriber_result["input_tokens"] + copyanalysis_result["input_tokens"]
    total_output = transcriber_result["output_tokens"] + copyanalysis_result["output_tokens"]
    total_tokens = transcriber_result["total_tokens"] + copyanalysis_result["total_tokens"]

    print("Quantidade total de tokens\n")
    print(f"Entrada {total_input}")
    print(f"Saida {total_output}")
    print(f"Total {total_tokens}")

    def save_copy_analysis_pdf(
        analysis,
        output_path: str
    ) -> None:
        html = f"""
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Análise da Copy</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #222;
                    padding: 32px;
                }}
                h1 {{
                    font-size: 28px;
                    margin-bottom: 8px;
                }}
                h2 {{
                    margin-top: 28px;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 6px;
                }}
                .card {{
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 12px;
                    margin: 10px 0;
                    background: #fafafa;
                }}
                .muted {{
                    color: #666;
                    font-size: 13px;
                }}
            </style>
        </head>
        <body>
            <h1>Análise da Copy</h1>
            <p class="muted">Relatório gerado automaticamente.</p>

            <h2>Resumo</h2>
            <p>{analysis.copy_structure.summary}</p>

            <h2>Estrutura da Copy</h2>
            {"".join(
                f'''
                <div class="card">
                    <strong>{section.section_type}</strong>
                    <p>{section.text}</p>
                    <p><em>{section.purpose}</em></p>
                </div>
                '''
                for section in analysis.copy_structure.sections
            )}

            <h2>Oferta</h2>
            <p><strong>Solução:</strong> {analysis.offer_analysis.product_or_solution or "Não identificado"}</p>
            <p><strong>Público-alvo:</strong> {analysis.offer_analysis.target_audience or "Não identificado"}</p>
            <p><strong>Problema:</strong> {analysis.offer_analysis.core_problem or "Não identificado"}</p>
            <p><strong>Promessa:</strong> {analysis.offer_analysis.main_promise or "Não identificado"}</p>
            <p><strong>CTA:</strong> {analysis.offer_analysis.call_to_action or "Não identificado"}</p>

            <h2>Persuasão</h2>
            <p><strong>Emoção dominante:</strong> {analysis.persuasion_analysis.dominant_emotion or "Não identificado"}</p>
            <p><strong>Padrão:</strong> {analysis.persuasion_analysis.persuasion_pattern or "Não identificado"}</p>
            <p><strong>Força do hook:</strong> {analysis.persuasion_analysis.hook_strength or "Não identificado"}</p>
            <p><strong>Clareza da promessa:</strong> {analysis.persuasion_analysis.promise_clarity or "Não identificado"}</p>
            <p>{analysis.persuasion_analysis.summary}</p>
        </body>
        </html>
    """

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        HTML(string=html).write_pdf(str(output))
    
    save_copy_analysis_pdf(
        analysis=copyanalysis_result["analysis"],
        output_path="src/data/output/copy_analysis.pdf",
    )
