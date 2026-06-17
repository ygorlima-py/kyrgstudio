from kyrg.workflows.core import WORKFLOW_END, WORKFLOW_START
from kyrg.workflows.base import WorkflowBase
from kyrg.workflows.copyadaptation.state import CopyAdaptationState
from kyrg.workflows.copyadaptation.schemas import CopyAdaptationWorkflowContext
from kyrg.workflows.copyadaptation.nodes import (
    prepare_adaptation_input,
    build_copy_strategy,
    write_script_sections,
    review_section_flow,
    primary_route,
    validate_script,
    build_script_output,
    correct_section,
)


class CopyAdaptationWorkflow(WorkflowBase):
    STATE_SCHEMA = CopyAdaptationState
    CONTEXT_SCHEMA = CopyAdaptationWorkflowContext

    def _build(self) -> None:
        self.graph.add_node("prepare_adaptation_input", prepare_adaptation_input)
        self.graph.add_node("build_copy_strategy", build_copy_strategy)
        self.graph.add_node("write_script_sections", write_script_sections)
        self.graph.add_node("review_section_flow", review_section_flow)
        self.graph.add_node("validate_script", validate_script)
        self.graph.add_node("build_script_output", build_script_output)
        self.graph.add_node("correct_section", correct_section)

        self.graph.add_edge(WORKFLOW_START, "prepare_adaptation_input")
        self.graph.add_edge("prepare_adaptation_input", "build_copy_strategy")
        self.graph.add_edge("build_copy_strategy", "write_script_sections")
        self.graph.add_edge("write_script_sections", "review_section_flow")
        self.graph.add_conditional_edges(
                        "review_section_flow",
                        primary_route,
                        {
                            "retry": "correct_section",
                            "continue": "validate_script"
                        })
        self.graph.add_edge("correct_section", "review_section_flow")
        self.graph.add_edge("validate_script", "build_script_output")
        self.graph.add_edge("build_script_output", WORKFLOW_END)


if __name__ == "__main__":
    workflow = CopyAdaptationWorkflow(initial_state={})
    workflow.draw_workflow()
