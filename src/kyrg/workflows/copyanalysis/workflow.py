from kyrg.workflows.core import WORKFLOW_START, WORKFLOW_END
from kyrg.workflows.base import WorkflowBase
from kyrg.workflows.adapter import RunnableNode
from kyrg.workflows.copyanalysis.schemas import CopyAnalysisWorkflowContext
from kyrg.workflows.copyanalysis.state import CopyAnalysisState
from kyrg.workflows.copyanalysis.nodes import (
    prepare_copy_input,
    extract_copy_structure,
    extract_offer_elements,
    analyse_persuasion,
    build_copy_analysis,
    aextract_copy_structure,
    aextract_offer_elements,
    aanalyse_persuasion,
    
)

class CopyAnalysisWorkflow(WorkflowBase):
   STATE_SCHEMA = CopyAnalysisState
   CONTEXT_SCHEMA = CopyAnalysisWorkflowContext
   
   def _build(self):
       self.graph.add_node('prepare_copy_input', prepare_copy_input)
       
       self.graph.add_node(
                            'extract_copy_structure',
                            RunnableNode(
                                    sync=extract_copy_structure,
                                    async_=aextract_copy_structure,
                                    context_schema=self.CONTEXT_SCHEMA,
                                    )
                            )
       self.graph.add_node(
                            'extract_offer_elements',
                            RunnableNode(
                                    sync=extract_offer_elements,
                                    async_=aextract_offer_elements,
                                    context_schema=self.CONTEXT_SCHEMA,
                                    )
                            )
       self.graph.add_node(
                    'analyse_persuasion',
                    RunnableNode(
                            sync=analyse_persuasion,
                            async_=aanalyse_persuasion,
                            context_schema=self.CONTEXT_SCHEMA,
                        )
                    )
       self.graph.add_node('build_copy_analysis', build_copy_analysis)
       
       self.graph.add_edge(WORKFLOW_START, 'prepare_copy_input')
       self.graph.add_edge('prepare_copy_input', 'extract_copy_structure')
       self.graph.add_edge('extract_copy_structure', 'extract_offer_elements')
       self.graph.add_edge('extract_offer_elements', 'analyse_persuasion')
       self.graph.add_edge('analyse_persuasion', 'build_copy_analysis')
       self.graph.add_edge('build_copy_analysis', WORKFLOW_END)
       
if __name__ == "__main__":
    workflow = CopyAnalysisWorkflow(initial_state={})
    workflow.draw_workflow()
