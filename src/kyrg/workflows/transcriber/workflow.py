from kyrg.workflows.core import WORKFLOW_START, WORKFLOW_END
from kyrg.workflows.base import WorkflowBase
from kyrg.workflows.adapter import RunnableNode
from kyrg.workflows.transcriber.state import TranscriberState
from kyrg.workflows.transcriber.schemas import TranscriberWorkflowContext
from kyrg.workflows.transcriber.nodes import (
    primary_router,
    extract_audio,
    audio_text_converter,
    measure_audio,
    secondary_router,
    extract_hybrid_context,
    prepare_audio,
    correction_transcriber,
    aaudio_text_converter,
    aextract_hybrid_context,
    acorrection_transcriber,
)
from kyrg.workflows.base import CheckpointerBase

class TranscriberWorkflow(WorkflowBase):
    STATE_SCHEMA = TranscriberState
    CONTEXT_SCHEMA = TranscriberWorkflowContext
    
    def _build(self) -> None:
        
        self.graph.add_node('extract_audio', extract_audio)
        self.graph.add_node('prepare_audio', prepare_audio)
        self.graph.add_node(
            'audio_text_converter',
            RunnableNode(
                sync=audio_text_converter,
                async_=aaudio_text_converter,
                context_schema=self.CONTEXT_SCHEMA,
                ),
            )
        self.graph.add_node(
            'extract_hybrid_context',
            RunnableNode(
                sync=extract_hybrid_context,
                async_=aextract_hybrid_context,
                context_schema=self.CONTEXT_SCHEMA,
                )
            )
        self.graph.add_node(
            'correction_transcriber',
            RunnableNode(
                sync=correction_transcriber,
                async_=acorrection_transcriber,
                context_schema=self.CONTEXT_SCHEMA
                ),
            )
        self.graph.add_node('measure_audio', measure_audio)
        
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
        self.graph.add_edge("audio_text_converter", "measure_audio")
        
        self.graph.add_conditional_edges(
            'measure_audio',
            secondary_router,
            {
             'to_correction': 'extract_hybrid_context',
             'not_correction': WORKFLOW_END,
            }
        )   
        self.graph.add_edge('extract_hybrid_context', 'correction_transcriber')
        self.graph.add_edge('correction_transcriber', WORKFLOW_END)
            

if __name__ == "__main__":
    
    workflow = TranscriberWorkflow(initial_state={})
    workflow.draw_workflow()