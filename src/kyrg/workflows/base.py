from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Callable
from loguru import logger

from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from langchain_core.tools import BaseTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain.agents import create_agent, AgentState

from kyrg.llms.base import LLMBase

class WorkflowBase(ABC):
    STATE_SCHEMA: type[Any]
    CONTEXT_SCHEMA: type[Any] = dict

        
    def __init__(
        self,
        initial_state: dict | None,
        context: object | None = None,
        ):
        
        self.graph = StateGraph(self.STATE_SCHEMA, context_schema=self.CONTEXT_SCHEMA)
        
        self.initial_state = initial_state or {}
        
        self.context = context if context is not None else {}
        
        self._compiled_graph: Any  = None
        
        self._build()
        
    @abstractmethod
    def _build(self) -> None:
        ...

    def _compile(self) -> Any:
        if self._compiled_graph is None:
            self._compiled_graph = self.graph.compile()

        return self._compiled_graph
        
    def draw_workflow(self):
        filename = f"{self.__class__.__name__}.png"
        return self._compile().get_graph(xray=True).draw_mermaid_png(output_file_path=filename)
    
    def start(self):
        return self._compile().invoke(
                            input=self.initial_state,
                            context=self.context,
                            )
        
    async def astart(self):
        return await self._compile().ainvoke(
                        input=self.initial_state,
                        context=self.context,
                        )

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
        
    
    def create(self) -> CompiledStateGraph:
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.PROMPT,
            state_schema=self.STATE_SCHEMA,
            debug=self.debug,
            name=self.NAME,
        )
    
class AIActionBase(ABC):
    def __init__(self, llm: LLMBase):
        self.llm = llm

    def _build_prompt(self) -> str:
        ...
        
    def execute(self) -> Any:
        ...
        
    async def aexecute(self) -> Any:
        ... 
        
class AIActionExecutor:
    
    @staticmethod
    def run(action: AIActionBase) -> Any:
        logger.info(f"Executing {action.__class__.__name__}")
        try:
            result = action.execute()
            logger.info(f"Success {action.__class__.__name__}")
            return result
        except Exception as e:
            logger.error(f"Failed {action.__class__.__name__}: {e}")
            raise
        
    @staticmethod
    async def arun(action: AIActionBase) -> Any:
        logger.info(f"Executing {action.__class__.__name__}")
        try:
            result = await action.aexecute()
            logger.info(f"Success {action.__class__.__name__}")
            return result
        except Exception as e:
            logger.error(f"Failed {action.__class__.__name__}: {e}")
            raise
