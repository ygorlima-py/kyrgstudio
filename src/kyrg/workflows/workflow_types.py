from __future__ import annotations

from langchain.agents import AgentState
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command

from typing import Any

WorkflowCheckpointer = BaseCheckpointSaver

WorkFlowAgentState = AgentState

WorkflowMemorySaver = MemorySaver

WorkflowStateGraph = StateGraph

WorkflowCompiledStateGraph = CompiledStateGraph

WorkflowAgentLLM = BaseChatModel

WorkflowBaseTool = BaseTool

WorkFlowCommand = Command

WorkflowRunnableConfig = RunnableConfig

WorkflowState = dict[str, Any]

WorkflowOutput = dict[str, Any]

