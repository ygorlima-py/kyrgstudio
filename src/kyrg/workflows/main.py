import os

from rich import print
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from kyrg.llms.openai_llm import OpenAILLM
from kyrg.transcribers.local_model import TranscriberWhisperLocal
from kyrg.workflows.transcriber.agent import TranscriptionAgent
from kyrg.workflows.transcriber.schemas import TranscriberWorkflowContext
from kyrg.workflows.transcriber.tools import (
    accept_transcription_tool,
    correct_transcription_tool,
    request_human_review_tool,
)
from kyrg.workflows.transcriber.workflow import TranscriberWorkflow


class OpenRouterLLM(OpenAILLM):
    BASE_URL = "https://openrouter.ai/api/v1"

if __name__ == "__main__":
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
        "source_path": "src/data/input/video_teste.mp4",
        "source_type": "video",
        "audio_path": "src/data/output/audio_extraido.wav",
        "transcriber": TranscriberWhisperLocal,
        "model_name": "small",
        "language": "pt"
    }
    
    context = TranscriberWorkflowContext(
        correction_llm=workflow_llm,
        extract_context_llm=workflow_llm,
    )

    workflow = TranscriberWorkflow(
        initial_state=initial_state,
        agent=agent,
        context=context,
    )

    result = workflow.start()
    
    print(result)