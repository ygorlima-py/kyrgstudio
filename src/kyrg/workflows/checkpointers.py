from contextlib import asynccontextmanager, contextmanager
from collections.abc import AsyncIterator, Iterator

from kyrg.workflows.workflow_types import(
                WorkflowCheckpointer,
                WorkflowMemorySaver,
                )
from kyrg.workflows.base import CheckpointerBase


class MemoryCheckpointer(CheckpointerBase):
    
    @contextmanager
    def create(self) -> Iterator[WorkflowCheckpointer]:
        yield WorkflowMemorySaver()
    
    @asynccontextmanager
    async def acreate(self) -> AsyncIterator[WorkflowCheckpointer]:
        yield WorkflowMemorySaver()
        
    
class SQLiteCheckpointer(CheckpointerBase):
    def __init__(self, database_path: str):
        self.database_path = database_path
        
    @contextmanager
    def create(self) -> Iterator[WorkflowCheckpointer]:
        
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            
        except ImportError as error:
            raise RuntimeError(
                 "SQLite checkpointer requires the optional package "
                "'langgraph-checkpoint-sqlite'. Install it before using this backend."
            ) from error
            
        with SqliteSaver.from_conn_string(self.database_path) as checkpointer:
            yield checkpointer
    
    @asynccontextmanager
    async def acreate(self) -> AsyncIterator[WorkflowCheckpointer]:
        
        try: 
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        
        except ImportError as error:
            raise RuntimeError(
                "Async SQLite checkpointer requires the optional package "
                "'langgraph-checkpoint-sqlite'. Install it before using this backend."
            ) from error
            
        async with AsyncSqliteSaver.from_conn_string(self.database_path) as saver:
            yield saver
                 
class PostgresCheckpointer(CheckpointerBase):
    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string
        
    @contextmanager
    def create(self) -> Iterator[WorkflowCheckpointer]:
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            
            
        except ImportError as error:
            raise RuntimeError(
                "Postgres checkpointer requires the optional package "
                "'langgraph-checkpoint-postgres'. Install it before using this backend."
            ) from error

        with PostgresSaver.from_conn_string(self.connection_string) as checkpointer:
            checkpointer.setup()
            yield checkpointer
    
    @asynccontextmanager
    async def acreate(self) ->  AsyncIterator[WorkflowCheckpointer]:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            
        except ImportError as error:
            raise RuntimeError(
                "Async Postgres checkpointer requires the optional package "
                "'langgraph-checkpoint-postgres'."
            ) from error
            
        async with AsyncPostgresSaver.from_conn_string(self.connection_string) as checkpointer:
            await checkpointer.setup()
            yield checkpointer
