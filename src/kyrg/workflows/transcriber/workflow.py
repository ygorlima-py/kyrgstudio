from langgraph.graph import START, END

from kyrg.workflows.base import WorkflowBase
from kyrg.workflows.transcriber.state import TranscriberState
from kyrg.workflows.transcriber.nodes import (
    primary_router,
    extract_audio,
    audio_text_converter,
    extract_hybrid_context,
    correction_transcriber,
    prepare_audio,
    analyse_transcriber,
)

class TranscriberWorkflow(WorkflowBase):
    STATE_SCHEMA = TranscriberState
    
    def _build(self) -> None:
        
        self.graph.add_node('extract_audio', extract_audio)
        self.graph.add_node('prepare_audio', prepare_audio)
        self.graph.add_node('audio_text_converter', audio_text_converter)
        self.graph.add_node('extract_hybrid_context', extract_hybrid_context)
        self.graph.add_node('analyse_transcriber', analyse_transcriber)
        self.graph.add_node('correction_transcriber', correction_transcriber )

        self.graph.add_conditional_edges(
            START, 
            primary_router, 
            {
            'normalize_audio': 'prepare_audio',
            'extract_audio': 'extract_audio',
            }
        )
        
        self.graph.add_edge('extract_audio', 'audio_text_converter')
        self.graph.add_edge('prepare_audio', 'audio_text_converter')
        self.graph.add_edge('audio_text_converter','extract_hybrid_context')
        self.graph.add_edge('extract_hybrid_context', 'analyse_transcriber')
        
        
        self.graph.add_edge('correction_transcriber', END)    

if __name__ == "__main__":
    workflow = TranscriberWorkflow(initial_state={})
    workflow.draw_workflow()