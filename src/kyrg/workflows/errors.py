from pydantic import ValidationError

def _format_validation_errors(error: ValidationError):
            
    validation_errors = [
        {
            "path": ".".join(map(str, item["loc"])),
            "type": item["type"],
            "message": item["msg"],
            "invalid_value": (
                item.get("input")
                if item["type"] != "missing"
                else None
            ),
            "constraints": item.get("ctx"),
        }
        for item in error.errors()
    ]
    return validation_errors