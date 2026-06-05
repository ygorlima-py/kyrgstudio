from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Callable

from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from langchain_core.tools import BaseTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain.agents import create_agent, AgentState

class WorkflowBase(ABC):
    STATE_SCHEMA: type[Any]
        
    def __init__(self, initial_state: dict | None):
        self.graph = StateGraph(self.STATE_SCHEMA)
        self.initial_state = initial_state or {}
        self._compiled_graph: CompiledStateGraph | None = None
        self._build()
        
    @abstractmethod
    def _build(self) -> None:
        ...

    def _compile(self) -> CompiledStateGraph:
        if self._compiled_graph is None:
            self._compiled_graph = self.graph.compile()

        return self._compiled_graph
        
    def draw_workflow(self):
        filename = f"{self.__class__.__name__}.png"
        return self._compile().get_graph().draw_mermaid_png(output_file_path=filename)
    
    def start(self):
        return self._compile().invoke(input=self.initial_state)
        
    async def astart(self):
        return await self._compile().ainvoke(input=self.initial_state)

class AgentBase(ABC):
    NAME: str
    PROMPT: str
    STATE_SCHEMA: type[AgentState] | None = None
    
    def __init__(
        self,
        llm: BaseChatModel,
        tools: Sequence[BaseTool | Callable[..., Any] | dict[str, Any]],
        debug: bool = True,
        ) -> None:
        
        self.llm = llm
        self.tools = tools
        self.debug = debug
        
    
    def create(self) -> Any:
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.PROMPT,
            state_schema=self.STATE_SCHEMA,
            debug=self.debug,
            name=self.NAME,
        )
    