from langgraph.runtime import Runtime
from langgraph.prebuilt import ToolRuntime
from langgraph.graph import END, START
from langgraph.graph.message import add_messages
from langgraph.runtime import get_runtime

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from typing import Any

from kyrg.workflows.workflow_types import WorkflowRuntime, ContextT


WorkflowToolRuntime = ToolRuntime

WorkflowToolMessage = ToolMessage

WORKFLOW_START = START

WORKFLOW_END = END

workflow_message_reducer = add_messages

create_workflow_flow_agent = create_agent

workflow_tool = tool

def get_workflow_runtime(context: type[ContextT]) -> WorkflowRuntime[Any]:
    # LangGraph accepts dataclass as context at runtime despite StateLike bound
    return get_runtime(context)  # type: ignore[arg-type]