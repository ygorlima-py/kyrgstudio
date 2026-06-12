from kyrg.workflows.core import WORKFLOW_START, WORKFLOW_END
from kyrg.workflows.base import WorkflowBase
from kyrg.workflows.transcriber.state import TranscriberState
from kyrg.workflows.transcriber.schemas import TranscriberWorkflowContext
from kyrg.workflows.transcriber.agent import TranscriptionAgent
from kyrg.workflows.transcriber.nodes import (
    primary_router,
    extract_audio,
    audio_text_converter,
    extract_hybrid_context,
    prepare_audio,
    collect_agent_tokens,
)
from kyrg.workflows.base import CheckpointerBase

class TranscriberWorkflow(WorkflowBase):
    STATE_SCHEMA = TranscriberState
    CONTEXT_SCHEMA = TranscriberWorkflowContext
    
    def __init__(
        self,
        initial_state: dict | None,
        agent: TranscriptionAgent,
        context: TranscriberWorkflowContext,
        checkpointer: CheckpointerBase | None = None,
        thread_id: str | None = None,
        ):
        
        self.agent_analysis = agent.create()
        super().__init__(initial_state, context, checkpointer, thread_id)
    
    def _build(self) -> None:
        
        self.graph.add_node('extract_audio', extract_audio)
        self.graph.add_node('prepare_audio', prepare_audio)
        self.graph.add_node('audio_text_converter', audio_text_converter)
        self.graph.add_node('extract_hybrid_context', extract_hybrid_context)
        self.graph.add_node('analyse_agent', self.agent_analysis)
        self.graph.add_node("collect_agent_tokens", collect_agent_tokens)

        self.graph.add_conditional_edges(
            WORKFLOW_START, 
            primary_router, 
            {
            'normalize_audio': 'prepare_audio',
            'extract_audio': 'extract_audio',
            }
        )
        
        self.graph.add_edge('extract_audio', 'audio_text_converter')
        self.graph.add_edge('prepare_audio', 'audio_text_converter')
        self.graph.add_edge('audio_text_converter','extract_hybrid_context')
        self.graph.add_edge('extract_hybrid_context', 'analyse_agent')
        self.graph.add_edge('analyse_agent', 'collect_agent_tokens')
        self.graph.add_edge('collect_agent_tokens', WORKFLOW_END)    
            

# if __name__ == "__main__":
#     from langchain_core.language_models.chat_models import BaseChatModel
#     from kyrg.workflows.transcriber.tools import (
#         accept_transcription_tool,
#         correct_transcription_tool,
#         request_human_review_tool,
#     )
    
#     from langchain_openai import ChatOpenAI
#     from dotenv import load_dotenv
#     import os 
    
#     load_dotenv()
    
#     agent = TranscriptionAgent(
#         llm=ChatOpenAI(
#             api_key=os.getenv("OPENROUTER_API_KEY"),
#             model="deepseek/deepseek-v4-flash"
#             ),
#         tools=[
#             accept_transcription_tool,
#             correct_transcription_tool,
#             request_human_review_tool,
#         ],
#         debug=True,
#     )

#     workflow = TranscriberWorkflow(initial_state={}, agent=agent)
#     workflow.draw_workflow()