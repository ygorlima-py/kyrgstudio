"""Integration tests for the compiled copy adaptation workflow graph."""

from collections import deque
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Generic, TypeVar, cast

import pytest
from pydantic import BaseModel

from kyrg.llms.base import LLMBase, OutputT
from kyrg.workflows.checkpointers import SQLiteCheckpointer
from kyrg.workflows.copyadaptation.schemas import (
    BuildCopyStrategyOutput,
    CopyAdaptationWorkflowContext,
    ReviewSectionFlowOutput,
    ScriptSectionOutput,
    SectionRevisionInstruction,
    UserProfileOutput,
    ValidationIssue,
    ValidateScriptOutput,
    WriteScriptSectionsOutput,
)
from kyrg.workflows.copyadaptation.state import CopyAdaptationState
from kyrg.workflows.copyadaptation.workflow import CopyAdaptationWorkflow
from kyrg.workflows.copyanalysis.schemas import (
    CopyAnalysisOutput,
    CopySection,
    CopyStructureOutput,
    OfferAnalysisOutput,
    PersuasionAnalysisOutput,
)


INPUT_TOKENS_PER_CALL = 10
OUTPUT_TOKENS_PER_CALL = 4
ResponseT = TypeVar("ResponseT", bound=BaseModel)


class SequenceLLM(LLMBase, Generic[ResponseT]):
    """Return ordered responses and record the cross-node execution sequence."""

    def __init__(
        self,
        role: str,
        events: list[str],
        output_schema: type[ResponseT],
        responses: Sequence[ResponseT | Exception],
    ) -> None:
        super().__init__()
        self.role = role
        self.events = events
        self.output_schema = output_schema
        self.responses = deque(responses)

    def invoke(self, prompt: str) -> str:
        raise AssertionError("Copy adaptation workflow must use structured output.")

    async def ainvoke(self, prompt: str) -> str:
        raise AssertionError("Copy adaptation workflow must use structured output.")

    def _structured_once(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        return self._next(output_schema)

    async def _astructured_once(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        return self._next(output_schema)

    def _next(self, output_schema: type[OutputT]) -> OutputT:
        self.events.append(f"{self.role}:{output_schema.__name__}")

        if output_schema is not self.output_schema:
            raise AssertionError(
                f"Unexpected {self.role} schema {output_schema.__name__}."
            )

        try:
            response = self.responses.popleft()
        except IndexError as error:
            raise AssertionError(
                f"Unexpected {self.role} call for {output_schema.__name__}."
            ) from error

        if isinstance(response, Exception):
            raise response

        assert type(response) is output_schema
        self._add_token(INPUT_TOKENS_PER_CALL, OUTPUT_TOKENS_PER_CALL)
        return cast(OutputT, response)


def _initial_state() -> CopyAdaptationState:
    """Return the public input expected by CopyAdaptationWorkflow."""

    return {
        "copy_analysis": CopyAnalysisOutput(
            language="English",
            copy_structure=CopyStructureOutput(
                language="English",
                content_type="VSL",
                main_hook="Your commission should support your future.",
                sections=[
                    CopySection(
                        section_type="hook",
                        text="Your commission should support your future.",
                        purpose="Capture attention through a relevant aspiration.",
                        start=0.0,
                        end=4.0,
                    ),
                    CopySection(
                        section_type="offer",
                        text="Learn a process for organizing your investments.",
                        purpose="Present the educational solution.",
                        start=4.0,
                        end=9.0,
                    ),
                ],
                narrative_flow=["hook", "offer"],
                section_gaps=[],
                summary="A short educational VSL.",
            ),
            offer_analysis=OfferAnalysisOutput(
                product_or_solution="A financial education course",
                summary="The offer teaches responsible long-term investing.",
            ),
            persuasion_analysis=PersuasionAnalysisOutput(
                dominant_emotion="confidence",
                persuasion_pattern="education-to-offer",
                hook_strength="high",
                promise_clarity="high",
                proof_strength="medium",
                urgency_strength="medium",
                cta_strength="high",
                summary="The copy educates before presenting the solution.",
            ),
        ),
        "user_profile": UserProfileOutput(
            product_or_solution="A practical personal finance course",
            target_audience="Agronomists who want to invest their commissions",
            core_problem="They lack a reliable long-term investment plan",
            core_desire="Build a diversified portfolio for the future",
            main_promise="Learn to organize and invest commissions responsibly",
            unique_mechanism="Commission Organization Method",
            benefits=["A repeatable portfolio planning process"],
            objections=["I do not know where to start"],
            proof_assets=["Recorded curriculum demonstration"],
            offer_details="Online course with a waiting list",
            call_to_action="Join the course waiting list",
            tone="Clear and practical",
            target_language="English",
            platform="YouTube",
            desired_duration=1.0,
            restrictions=["Do not promise guaranteed financial returns"],
        ),
    }


def _section(
    *,
    order: int,
    section_type: str,
    text: str,
) -> ScriptSectionOutput:
    """Build one valid generated section."""

    return ScriptSectionOutput.model_validate(
        {
            "order": order,
            "section_type": section_type,
            "text": text,
            "purpose": f"Serve the {section_type} role.",
            "adaptation_mode": "adapted_from_reference",
            "source_reference_section_type": section_type,
            "proof_used": None,
            "missing_proof": False,
            "transition_hint": "Continue to the next persuasive beat.",
            "pause_intent": "medium",
        }
    )


def _written_output(label: str) -> WriteScriptSectionsOutput:
    """Return a complete script version identifiable across retry cycles."""

    return WriteScriptSectionsOutput(
        sections=[
            _section(
                order=1,
                section_type="hook",
                text=f"{label} hook for responsible commission planning.",
            ),
            _section(
                order=2,
                section_type="mechanism",
                text=f"{label} explanation of the Commission Organization Method.",
            ),
            _section(
                order=3,
                section_type="offer",
                text=f"{label} presentation of the practical finance course.",
            ),
            _section(
                order=4,
                section_type="cta",
                text="Join the course waiting list.",
            ),
        ],
        missing_proofs=[],
        adaptation_notes=f"{label} script version.",
    )


def _strategy_output() -> BuildCopyStrategyOutput:
    return BuildCopyStrategyOutput(
        main_angle="Turn irregular commissions into a long-term plan",
        awareness_level="problem_aware",
        main_promise="Learn a responsible investment planning process",
        persuasion_pattern="education_to_offer",
        objections_to_address=["I do not know where to start"],
        proof_plan={"mechanism": "Use the curriculum demonstration"},
        unique_mechanism="Commission Organization Method",
        strategy_notes="Educate the audience before presenting the course.",
    )


def _review_output(approved: bool) -> ReviewSectionFlowOutput:
    if approved:
        return ReviewSectionFlowOutput(
            flow_approved=True,
            flow_issues=[],
            revision_instructions=[],
            sections_revised=[],
        )

    return ReviewSectionFlowOutput(
        flow_approved=False,
        flow_issues=["The mechanism transition is abrupt."],
        revision_instructions=[
            SectionRevisionInstruction(
                section_order=2,
                section_type="mechanism",
                issue="The transition is abrupt.",
                action="adjust_transition",
                instruction="Connect the hook to the mechanism naturally.",
                priority="high",
            )
        ],
        sections_revised=[],
    )


def _validation_output(passed: bool) -> ValidateScriptOutput:
    return ValidateScriptOutput(
        validation_passed=passed,
        validation_errors=[] if passed else [
            ValidationIssue(
                category="claim",
                code="unsupported_promise",
                section_order=1,
                section_type="hook",
                field="text",
                message="The promise is unsupported.",
                correction_action="soften",
            )
        ],
        validation_warnings=[],
    )


def _context(
    *,
    events: list[str],
    writing_responses: list[WriteScriptSectionsOutput],
    review_responses: list[ReviewSectionFlowOutput],
    validation_responses: list[ValidateScriptOutput | Exception],
    max_retry: int = 1,
) -> CopyAdaptationWorkflowContext:
    """Build role-specific deterministic LLM queues for one graph execution."""

    return CopyAdaptationWorkflowContext(
        strategy_llm=SequenceLLM(
            "strategy",
            events,
            BuildCopyStrategyOutput,
            [_strategy_output()],
        ),
        writing_llm=SequenceLLM(
            "writing",
            events,
            WriteScriptSectionsOutput,
            writing_responses,
        ),
        review_llm=SequenceLLM(
            "review",
            events,
            ReviewSectionFlowOutput,
            review_responses,
        ),
        validation_llm=SequenceLLM(
            "validation",
            events,
            ValidateScriptOutput,
            validation_responses,
        ),
        max_retry=max_retry,
    )


def _run_workflow(
    context: CopyAdaptationWorkflowContext,
    *,
    checkpointer: SQLiteCheckpointer | None = None,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Compile and execute the real graph with deterministic dependencies."""

    workflow = CopyAdaptationWorkflow(
        initial_state=dict(_initial_state()),
        context=context,
        checkpointer=checkpointer,
        thread_id=thread_id,
    )
    return workflow.start()


def _assert_token_totals(result: dict[str, Any], call_count: int) -> None:
    """Assert LangGraph reducers accumulated every successful LLM call."""

    assert result["input_tokens"] == INPUT_TOKENS_PER_CALL * call_count
    assert result["output_tokens"] == OUTPUT_TOKENS_PER_CALL * call_count
    assert result["total_tokens"] == (
        INPUT_TOKENS_PER_CALL + OUTPUT_TOKENS_PER_CALL
    ) * call_count


def test_happy_path_runs_in_order_and_returns_the_public_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approved content should traverse the graph once without corrections."""

    monkeypatch.chdir(tmp_path)
    events: list[str] = []
    context = _context(
        events=events,
        writing_responses=[_written_output("Initial")],
        review_responses=[_review_output(True)],
        validation_responses=[_validation_output(True)],
    )

    result = _run_workflow(context)

    assert events == [
        "strategy:BuildCopyStrategyOutput",
        "writing:WriteScriptSectionsOutput",
        "review:ReviewSectionFlowOutput",
        "validation:ValidateScriptOutput",
    ]
    assert result["adapted_script"]["validation_passed"] is True
    assert result["adapted_script"]["sections"][0]["text"].startswith("Initial")
    _assert_token_totals(result, call_count=4)


def test_flow_review_retry_is_corrected_and_then_approved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed flow review should execute one section correction cycle."""

    monkeypatch.chdir(tmp_path)
    events: list[str] = []
    context = _context(
        events=events,
        writing_responses=[
            _written_output("Initial"),
            _written_output("Flow-corrected"),
        ],
        review_responses=[_review_output(False), _review_output(True)],
        validation_responses=[_validation_output(True)],
    )

    result = _run_workflow(context)

    assert result["retry_count_correction_section"] == 1
    assert result["flow_approved"] is True
    assert result["adapted_script"]["sections"][0]["text"].startswith(
        "Flow-corrected"
    )
    assert events.count("review:ReviewSectionFlowOutput") == 2
    _assert_token_totals(result, call_count=6)


def test_validation_retry_is_corrected_and_then_approved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A validation failure should execute one final correction cycle."""

    monkeypatch.chdir(tmp_path)
    events: list[str] = []
    context = _context(
        events=events,
        writing_responses=[
            _written_output("Initial"),
            _written_output("Validation-corrected"),
        ],
        review_responses=[_review_output(True)],
        validation_responses=[
            _validation_output(False),
            _validation_output(True),
        ],
    )

    result = _run_workflow(context)

    assert result["retry_count_correction_script"] == 1
    assert result["validation_passed"] is True
    assert result["adapted_script"]["sections"][0]["text"].startswith(
        "Validation-corrected"
    )
    assert events.count("validation:ValidateScriptOutput") == 2
    _assert_token_totals(result, call_count=6)


def test_flow_and_validation_retries_can_run_in_the_same_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Independent correction loops should compose without stale state conflicts."""

    monkeypatch.chdir(tmp_path)
    events: list[str] = []
    context = _context(
        events=events,
        writing_responses=[
            _written_output("Initial"),
            _written_output("Flow-corrected"),
            _written_output("Validation-corrected"),
        ],
        review_responses=[_review_output(False), _review_output(True)],
        validation_responses=[
            _validation_output(False),
            _validation_output(True),
        ],
    )

    result = _run_workflow(context)

    assert result["retry_count_correction_section"] == 1
    assert result["retry_count_correction_script"] == 1
    assert result["adapted_script"]["validation_passed"] is True
    assert result["adapted_script"]["sections"][0]["text"].startswith(
        "Validation-corrected"
    )
    _assert_token_totals(result, call_count=8)


def test_retry_limits_prevent_infinite_loops_and_preserve_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated failures should stop at max_retry and remain visibly rejected."""

    monkeypatch.chdir(tmp_path)
    events: list[str] = []
    context = _context(
        events=events,
        writing_responses=[
            _written_output("Initial"),
            _written_output("Flow-attempt"),
            _written_output("Validation-attempt"),
        ],
        review_responses=[_review_output(False), _review_output(False)],
        validation_responses=[
            _validation_output(False),
            _validation_output(False),
        ],
        max_retry=1,
    )

    result = _run_workflow(context)

    assert result["retry_count_correction_section"] == 1
    assert result["retry_count_correction_script"] == 1
    assert result["flow_approved"] is False
    assert result["validation_passed"] is False
    assert result["adapted_script"]["validation_passed"] is False
    assert events.count("review:ReviewSectionFlowOutput") == 2
    assert events.count("validation:ValidateScriptOutput") == 2
    _assert_token_totals(result, call_count=8)


def test_new_thread_id_starts_without_retry_state_from_another_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fresh thread should not inherit counters from a completed execution."""

    monkeypatch.chdir(tmp_path)
    database_path = tmp_path / "copyadaptation.sqlite"
    checkpointer = SQLiteCheckpointer(str(database_path))

    first_events: list[str] = []
    first_context = _context(
        events=first_events,
        writing_responses=[
            _written_output("Initial"),
            _written_output("Flow-corrected"),
        ],
        review_responses=[_review_output(False), _review_output(True)],
        validation_responses=[_validation_output(True)],
    )
    first_result = _run_workflow(
        first_context,
        checkpointer=checkpointer,
        thread_id="project:run-one",
    )
    assert first_result["retry_count_correction_section"] == 1

    second_events: list[str] = []
    second_context = _context(
        events=second_events,
        writing_responses=[_written_output("Fresh")],
        review_responses=[_review_output(True)],
        validation_responses=[_validation_output(True)],
    )
    second_result = _run_workflow(
        second_context,
        checkpointer=checkpointer,
        thread_id="project:run-two",
    )

    assert second_result.get("retry_count_correction_section", 0) == 0
    assert second_result.get("retry_count_correction_script", 0) == 0
    assert second_events.count("writing:WriteScriptSectionsOutput") == 1
    _assert_token_totals(second_result, call_count=4)


def test_same_thread_id_resumes_from_the_failed_node(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An interrupted thread should retry its failed node without rebuilding prior work."""

    monkeypatch.chdir(tmp_path)
    events: list[str] = []
    context = _context(
        events=events,
        writing_responses=[_written_output("Initial")],
        review_responses=[_review_output(True)],
        validation_responses=[
            RuntimeError("Temporary validation provider failure"),
            _validation_output(True),
        ],
    )
    workflow = CopyAdaptationWorkflow(
        initial_state=dict(_initial_state()),
        context=context,
        checkpointer=SQLiteCheckpointer(str(tmp_path / "resume.sqlite")),
        thread_id="project:interrupted-run",
    )

    with pytest.raises(RuntimeError, match="Temporary validation provider failure"):
        workflow.start()

    result = workflow.start()

    assert events.count("strategy:BuildCopyStrategyOutput") == 1
    assert events.count("writing:WriteScriptSectionsOutput") == 1
    assert events.count("review:ReviewSectionFlowOutput") == 1
    assert events.count("validation:ValidateScriptOutput") == 2
    assert result["adapted_script"]["validation_passed"] is True
    _assert_token_totals(result, call_count=4)
