from typing import TypeVar


ValueT = TypeVar("ValueT")


def require_context(
    context: ValueT | None,
    workflow_name: str,
) -> ValueT:
    if context is None:
        raise RuntimeError(f"{workflow_name} workflow context is required.")

    return context

def require_value(
    value: ValueT | None,
    field_name: str,
    operation: str,
) -> ValueT:
    if value is None:
        raise ValueError(
            f"{field_name} is required to {operation}"
        )

    return value

def require_non_empty(
    value: ValueT | None,
    field_name: str,
    operation: str,
) -> ValueT:
    if not value:
        raise ValueError(
            f"{field_name} is required to {operation}"
        )

    return value