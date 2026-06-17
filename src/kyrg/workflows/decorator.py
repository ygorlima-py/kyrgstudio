import json
from functools import wraps

def save_output_json(func):
    
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        file_name = f"{self.__class__.__name__}.json"

        result = func(self, *args, **kwargs)

        with open(file_name, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2, default=str)

        return result

    return wrapper