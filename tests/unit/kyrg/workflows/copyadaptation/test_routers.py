"""Unit tests for copy adaptation workflow routing decisions."""

from typing import Any, cast

import pytest

from kyrg.llms.base import LLMBase, OutputT
from kyrg.workflows.copyadaptation.nodes import primary_route, secondary_route
from kyrg.workflows.copyadaptation.schemas import CopyAdaptationWorkflowContext
from kyrg.workflows.copyadaptation.state import CopyAdaptationState
from kyrg.workflows.core import WorkflowRuntime


class UnusedLLM(LLMBase):
    """Satisfy context typing while ensuring routers never call an LLM."""

    def invoke(self, prompt: str) -> str:
        raise AssertionError("Routers must not call an LLM.")

    async def ainvoke(self, prompt: str) -> str:
        raise AssertionError("Routers must not call an LLM.")

    def _structured_once(
        self,
        prompt: str,
        system_prompt: str,
        prompt_cache_key: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        raise AssertionError("Routers must not call an LLM.")

    async def _astructured_once(
        self,
        prompt: str,
        system_prompt: str,
        prompt_cache_key: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        raise AssertionError("Routers must not call an LLM.")


def _runtime(max_retry: int = 2) -> WorkflowRuntime[CopyAdaptationWorkflowContext]:
    """Build a real typed runtime with a configurable retry boundary."""

    llm = UnusedLLM()
    context = CopyAdaptationWorkflowContext(
        strategy_llm=llm,
        writing_llm=llm,
        review_llm=llm,
        validation_llm=llm,
        max_retry=max_retry,
    )
    return WorkflowRuntime(context=context)


@pytest.mark.parametrize(
    ("approved", "retry_count", "max_retry", "expected"),
    (
        (True, 0, 2, "continue"),
        (True, 2, 2, "continue"),
        (False, 0, 2, "retry"),
        (False, 1, 2, "retry"),
        (False, 2, 2, "continue"),
        (False, 3, 2, "continue"),
        (None, 0, 2, "retry"),
        (None, 2, 2, "continue"),
    ),
)
def test_primary_route_respects_approval_and_exact_retry_limit(
    approved: bool | None,
    retry_count: int,
    max_retry: int,
    expected: str,
) -> None:
    """Flow review retries should stop exactly at the configured boundary."""

    state = cast(
        CopyAdaptationState,
        {
            "flow_approved": approved,
            "retry_count_correction_section": retry_count,
        },
    )

    assert primary_route(state, _runtime(max_retry)) == expected


@pytest.mark.parametrize(
    ("approved", "retry_count", "max_retry", "expected"),
    (
        (True, 0, 2, "continue"),
        (True, 2, 2, "continue"),
        (False, 0, 2, "retry"),
        (False, 1, 2, "retry"),
        (False, 2, 2, "continue"),
        (False, 3, 2, "continue"),
        (None, 0, 2, "retry"),
        (None, 2, 2, "continue"),
    ),
)
def test_secondary_route_respects_validation_and_exact_retry_limit(
    approved: bool | None,
    retry_count: int,
    max_retry: int,
    expected: str,
) -> None:
    """Validation retries should stop exactly at the configured boundary."""

    state = cast(
        CopyAdaptationState,
        {
            "validation_passed": approved,
            "retry_count_correction_script": retry_count,
        },
    )

    assert secondary_route(state, _runtime(max_retry)) == expected


@pytest.mark.parametrize(
    ("router", "expected"),
    (
        (primary_route, "retry"),
        (secondary_route, "retry"),
    ),
)
def test_router_treats_missing_decision_and_counter_as_first_failure(
    router: Any,
    expected: str,
) -> None:
    """An absent decision should enter the first retry instead of bypassing review."""

    state = cast(CopyAdaptationState, {})
    assert router(state, _runtime(max_retry=1)) == expected
