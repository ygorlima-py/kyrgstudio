from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Callable
from loguru import logger
from contextlib import AbstractAsyncContextManager, AbstractContextManager
import time

from kyrg.llms.base import LLMBase
from kyrg.workflows.decorators import save_output_json
from kyrg.workflows.core import create_workflow_flow_agent
from kyrg.workflows.workflow_types import (
    WorkflowCheckpointer,
    WorkflowStateGraph,
    WorkflowCompiledStateGraph,
    WorkflowAgentLLM,
    WorkFlowAgentState,
    WorkflowBaseTool,
    WorkflowRunnableConfig,
    )

class WorkflowBase(ABC):
    STATE_SCHEMA: type[Any]
    CONTEXT_SCHEMA: type[Any] = dict

        
    def __init__(
        self,
        initial_state: dict | None,
        context: object | None = None,
        checkpointer: CheckpointerBase | None = None,
        thread_id: str | None = None,
        ):
        
        self.graph = WorkflowStateGraph(self.STATE_SCHEMA, context_schema=self.CONTEXT_SCHEMA)
        self.initial_state = initial_state or {}
        self.context = context if context is not None else {}
        self.checkpointer = checkpointer
        self.thread_id = thread_id
        self._compiled_graph: Any  = None
        self._build()
        
    @abstractmethod
    def _build(self) -> None:
        ...

    def _compile(self) -> Any:
        
        if self._compiled_graph is None:
            self._compiled_graph = self.graph.compile()

        return self._compiled_graph
    
    def _config(self) ->  WorkflowRunnableConfig | None:
        if self.thread_id is None:
            return None

        return WorkflowRunnableConfig(
            configurable={
                "thread_id": self.thread_id,
            }
        )
        
    def draw_workflow(self):
        filename = f"{self.__class__.__name__}.png"
        return self._compile().get_graph(xray=True).draw_mermaid_png(output_file_path=filename)
    
    @save_output_json
    def start(self):     
        if self.checkpointer is None:
            return self._compile().invoke(
                input=self.initial_state,
                context=self.context,
            )
        
        with self.checkpointer.create() as checkpointer:
            compiled_graph = self.graph.compile(
                checkpointer=checkpointer,
            )
            config = self._config()
            checkpoint = (
                checkpointer.get_tuple(config)
                if config is not None
                else None
            )
            graph_input = None if checkpoint is not None else self.initial_state
            
            return compiled_graph.invoke(
                input=graph_input,
                context=self.context,
                config=config,
            )
        
    async def astart(self):
        
        if self.checkpointer is None:
            return await self._compile().ainvoke(
                            input=self.initial_state,
                            context=self.context,
                            )
        
        async with self.checkpointer.acreate() as checkpointer:
            compiled_graph = self.graph.compile(
                checkpointer=checkpointer,
            )
            config = self._config()
            checkpoint = (
                await checkpointer.aget_tuple(config)
                if config is not None
                else None
            )
            graph_input = None if checkpoint is not None else self.initial_state

            return await compiled_graph.ainvoke(
                input=graph_input,
                context=self.context,
                config=config,
            )

class AgentBase(ABC):
    NAME: str
    PROMPT: str
    STATE_SCHEMA: type[WorkFlowAgentState] | None = None
    
    def __init__(
        self,
        llm: WorkflowAgentLLM,
        tools: Sequence[WorkflowBaseTool | Callable[..., Any] | dict[str, Any]],
        debug: bool = True,
        ) -> None:
        
        self.llm = llm
        self.tools = tools
        self.debug = debug
        
    
    def create(self) -> WorkflowCompiledStateGraph:
        return create_workflow_flow_agent(
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

    @abstractmethod
    def _build_prompt(self) -> str:
        ...

    @abstractmethod
    def execute(self) -> Any:
        ...
    
    @abstractmethod
    async def aexecute(self) -> Any:
        ... 
        
    @property
    def tokens_usage(self):      
        return self.llm.token_usage()
        
class AIActionExecutor:
    
    @staticmethod
    def run(action: AIActionBase) -> Any:
        logger.info(f"Executing {action.__class__.__name__}")
        try:
            start = time.perf_counter()
            result = action.execute()
            end = time.perf_counter()
            logger.info(f"Success {action.__class__.__name__}")
            logger.info(f"Task execution time {end-start}s")
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
        

class CheckpointerBase(ABC):
    ...
    
    @abstractmethod
    def create(self) -> AbstractContextManager[WorkflowCheckpointer]:
        ...
        
    @abstractmethod
    def acreate(self) -> AbstractAsyncContextManager[WorkflowCheckpointer]:
        ...
