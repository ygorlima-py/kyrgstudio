from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar, override

from kyrg.workflows.workflow_types import (
    WorkflowRunnableConfig,
    WorkflowRunnable,
    WorkflowRuntime,
    ContextT, 
    StateT
)
from kyrg.workflows.core import get_workflow_runtime

OutputT = TypeVar("OutputT")

class RunnableNode(
    WorkflowRunnable[StateT, OutputT],
    Generic[StateT,  OutputT, ContextT],
):
    """Run the synchronous or asynchronous implementation of a workflow node."""

    def __init__(
        self,
        *,
        sync: Callable[
            [StateT, WorkflowRuntime[ContextT]],
            OutputT,
        ],
        async_: Callable[
            [StateT, WorkflowRuntime[ContextT]],
            Awaitable[OutputT],
        ],
        context_schema: type[ContextT],
    ) -> None:
        self._sync = sync
        self._async = async_
        self._context_schema = context_schema

    @override
    def invoke(
        self,
        input: StateT,
        config: WorkflowRunnableConfig | None = None,
        **kwargs: Any,
    ) -> OutputT:
        """Execute the synchronous node implementation."""

        runtime = get_workflow_runtime(self._context_schema)
        return self._sync(input, runtime)

    @override
    async def ainvoke(
        self,
        input: StateT,
        config: WorkflowRunnableConfig | None = None,
        **kwargs: Any,
    ) -> OutputT:
        """Execute the asynchronous node implementation."""

        runtime = get_workflow_runtime(self._context_schema)
        return await self._async(input, runtime)
