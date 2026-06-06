from langgraph.graph import START, END

from kyrg.workflows.base import WorkflowBase
from kyrg.workflows.copyanalysis.state import CopyAnalysisState
from kyrg.workflows.copyanalysis.nodes import (
    prepare_copy_input,
    extract_copy_structure,
    extract_offer_elements,
    analyse_persuasion,
    build_copy_analysis,
)

class CopyAnalysisWorkflow(WorkflowBase):
   STATE_SCHEMA = CopyAnalysisState
   
   def _build(self):
       self.graph.add_node('prepare_copy_input', prepare_copy_input)
       self.graph.add_node('extract_copy_structure', extract_copy_structure)
       self.graph.add_node('extract_offer_elements', extract_offer_elements)
       self.graph.add_node('analyse_persuasion', analyse_persuasion)
       self.graph.add_node('build_copy_analysis', build_copy_analysis)
       
       self.graph.add_edge(START, 'prepare_copy_input')
       self.graph.add_edge('prepare_copy_input', 'extract_copy_structure')
       self.graph.add_edge('extract_copy_structure', 'extract_offer_elements')
       self.graph.add_edge('extract_offer_elements', 'analyse_persuasion')
       self.graph.add_edge('analyse_persuasion', 'build_copy_analysis')
       self.graph.add_edge('build_copy_analysis', END)
       
if __name__ == "__main__":
    workflow = CopyAnalysisWorkflow(initial_state={})
    workflow.draw_workflow()