import json
from functools import wraps
from typing import TypeVar, Callable,  Any

from kyrg.workflows.workflow_types import WorkflowRunnableConfig
from kyrg.workflows.core import get_workflow_runtime

ContextT = TypeVar("ContextT")

def save_output_json(func):
    
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        file_name = f"{self.__class__.__name__}.json"

        result = func(self, *args, **kwargs)

        with open(file_name, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2, default=str)

        return result

    return wrapper


