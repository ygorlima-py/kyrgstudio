"""Graph wiring for the copy adaptation workflow.

The workflow turns a reference-copy analysis and user offer profile into an
adapted script. It prepares inputs, creates a strategy, writes sections, reviews
flow, validates production readiness, applies bounded correction retries, and
assembles the final script output.
"""

from kyrg.workflows.core import WORKFLOW_END, WORKFLOW_START
from kyrg.workflows.base import WorkflowBase
from kyrg.workflows.adapter import RunnableNode
from kyrg.workflows.copyadaptation.state import CopyAdaptationState
from kyrg.workflows.copyadaptation.schemas import CopyAdaptationWorkflowContext
from kyrg.workflows.copyadaptation.nodes import (
    prepare_adaptation_input,
    build_copy_strategy,
    write_script_sections,
    review_section_flow,
    primary_route,
    secondary_route,
    validate_script,
    build_script_output,
    correct_section,
    correct_script,
    abuild_copy_strategy,
    awrite_script_sections,
    areview_section_flow,
    acorrect_section,
    avalidate_script,
    acorrect_script,
)


class CopyAdaptationWorkflow(WorkflowBase):
    """Executable graph for adapting analyzed copy to a new offer profile."""

    STATE_SCHEMA = CopyAdaptationState
    CONTEXT_SCHEMA = CopyAdaptationWorkflowContext

    def _build(self) -> None:
        """Register nodes, sync/async adapters, retry routes, and final edge."""

        self.graph.add_node("prepare_adaptation_input", prepare_adaptation_input)
        self.graph.add_node(
            "build_copy_strategy",
            RunnableNode(
                sync=build_copy_strategy,
                async_=abuild_copy_strategy,
                context_schema=self.CONTEXT_SCHEMA,
                ),
            )
        self.graph.add_node(
            "write_script_sections",
            RunnableNode(
                sync=write_script_sections,
                async_=awrite_script_sections,
                context_schema=self.CONTEXT_SCHEMA,
            ))
        self.graph.add_node(
            "review_section_flow",
            RunnableNode(
                sync=review_section_flow,
                async_=areview_section_flow,
                context_schema=self.CONTEXT_SCHEMA,
            ))
        self.graph.add_node(
            "validate_script",
            RunnableNode(
                sync=validate_script,
                async_=avalidate_script,
                context_schema=self.CONTEXT_SCHEMA,
            ))
        self.graph.add_node(
            "correct_section",
            RunnableNode(
                sync=correct_section,
                async_=acorrect_section,
                context_schema=self.CONTEXT_SCHEMA
        ))
        self.graph.add_node(
            "correct_script",
            RunnableNode(
                sync=correct_script,
                async_=acorrect_script,
                context_schema=self.CONTEXT_SCHEMA,
            ))
        self.graph.add_node("build_script_output", build_script_output)
        
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
        
        self.graph.add_conditional_edges(
                "validate_script",
            secondary_route,
            {
                "retry": "correct_script",
                "continue": "build_script_output",
            })

        self.graph.add_edge("correct_script", "validate_script")        
        self.graph.add_edge("build_script_output", WORKFLOW_END)


if __name__ == "__main__":
    workflow = CopyAdaptationWorkflow(initial_state={})
    workflow.draw_workflow()
