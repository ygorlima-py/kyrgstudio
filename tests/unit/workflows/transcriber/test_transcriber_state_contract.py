"""Contract tests for the transcriber workflow state."""

from operator import add
from typing import Annotated, Any, NotRequired, TypeVar, cast, get_args
from typing import get_origin, get_type_hints

from langgraph.graph import END, START
from langgraph.graph.state import StateNode
from pydantic import BaseModel

from kyrg.llms.base import LLMBase
from kyrg.transcribers.schemas import TextSegment, TranscriptionResult
from kyrg.workflows.transcriber.nodes import (
    correction_transcriber,
    extract_hybrid_context,
    secondary_router,
)
from kyrg.workflows.transcriber.schemas import (
    CorrectedSegment,
    CorrectedTranscriptionOutput,
    DomainContextOutput,
    TranscriberWorkflowContext,
)
from kyrg.workflows.transcriber.state import TranscriberState
from kyrg.workflows.workflow_types import WorkflowStateGraph


OutputT = TypeVar("OutputT", bound=BaseModel)

REQUIRED_TRANSCRIBER_FIELDS = {
    "source_path",
    "source_type",
    "audio_path",
    "model_name",
}
OPTIONAL_TRANSCRIBER_FIELDS = {
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "language",
    "result",
    "audio_duration_in_seconds",
    "correction_llm",
    "domain_context",
    "status",
    "human_review_reason",
}
TOKEN_FIELDS = ("input_tokens", "output_tokens", "total_tokens")


class FixedOutputLLM(LLMBase):
    """Return one configured structured model with fixed token usage."""

    def __init__(
        self,
        response: BaseModel,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Store the model and expose deterministic token counters."""
        super().__init__(max_attempts=1)
        self.response = response
        self._add_token(input_tokens, output_tokens)

    def invoke(self, prompt: str) -> str:
        """Reject unstructured synchronous calls."""
        raise AssertionError(f"Unexpected invoke call: {prompt}")

    async def ainvoke(self, prompt: str) -> str:
        """Reject unstructured asynchronous calls."""
        raise AssertionError(f"Unexpected ainvoke call: {prompt}")

    def _structured_once(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        """Return the configured model for a structured request."""
        del prompt, output_schema
        return cast(OutputT, self.response)

    async def _astructured_once(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        """Return the configured model for an async structured request."""
        del prompt, output_schema
        return cast(OutputT, self.response)


def transcription_result() -> TranscriptionResult:
    """Build an in-memory transcription for reducer integration."""
    return TranscriptionResult(
        audio_path="/virtual/source.wav",
        language="en",
        text="The speaker says pie dantic.",
        segments=[
            TextSegment(
                id=2,
                start=0.0,
                end=2.0,
                text="The speaker says pie dantic.",
            )
        ],
        model="offline-model",
        provider="fake-provider",
    )


def extracted_context() -> DomainContextOutput:
    """Build deterministic domain context returned by the fake LLM."""
    return DomainContextOutput(
        language="English",
        main_subject="Pydantic",
        content_type="lesson",
        summary="A lesson about Pydantic.",
        technical_terms=["Pydantic"],
    )


def corrected_transcription() -> CorrectedTranscriptionOutput:
    """Build deterministic correction output returned by the fake LLM."""
    return CorrectedTranscriptionOutput(
        corrected_text="The speaker says Pydantic.",
        corrected_segments=[
            CorrectedSegment(id=2, text="The speaker says Pydantic.")
        ],
    )


def test_transcriber_state_declares_four_required_fields() -> None:
    """Keep the four transcriber inputs required by the current state."""
    assert REQUIRED_TRANSCRIBER_FIELDS <= TranscriberState.__required_keys__
    assert REQUIRED_TRANSCRIBER_FIELDS.isdisjoint(
        TranscriberState.__optional_keys__
    )


def test_transcriber_state_declares_current_optional_fields() -> None:
    """Keep the current transcriber-specific fields optional."""
    assert TranscriberState.__optional_keys__ == OPTIONAL_TRANSCRIBER_FIELDS


def test_transcriber_state_contains_expected_specific_shape() -> None:
    """Expose every transcriber-specific field in state annotations."""
    expected_fields = REQUIRED_TRANSCRIBER_FIELDS | OPTIONAL_TRANSCRIBER_FIELDS

    assert expected_fields <= TranscriberState.__annotations__.keys()


def test_token_fields_use_operator_add_reducer() -> None:
    """Annotate every token counter with the operator.add reducer."""
    hints = get_type_hints(TranscriberState, include_extras=True)

    for field_name in TOKEN_FIELDS:
        optional_hint = hints[field_name]
        assert get_origin(optional_hint) is NotRequired
        annotated_hint = get_args(optional_hint)[0]
        assert get_origin(annotated_hint) is Annotated
        value_type, reducer = get_args(annotated_hint)
        assert value_type is int
        assert reducer is add


def test_context_and_correction_token_deltas_are_added() -> None:
    """Add successive context and correction token deltas in a real graph."""
    context_llm = FixedOutputLLM(
        extracted_context(),
        input_tokens=2,
        output_tokens=3,
    )
    correction_llm = FixedOutputLLM(
        corrected_transcription(),
        input_tokens=7,
        output_tokens=11,
    )
    workflow_context = TranscriberWorkflowContext(
        correction_llm=correction_llm,
        extract_context_llm=context_llm,
        transcriptor_config=cast(Any, object()),
    )
    graph = WorkflowStateGraph(
        TranscriberState,
        context_schema=TranscriberWorkflowContext,
    )
    context_node = cast(
        StateNode[TranscriberState, TranscriberWorkflowContext],
        extract_hybrid_context,
    )
    correction_node = cast(
        StateNode[TranscriberState, TranscriberWorkflowContext],
        correction_transcriber,
    )
    graph.add_node("context", context_node)
    graph.add_node("correction", correction_node)
    graph.add_edge(START, "context")
    graph.add_edge("context", "correction")
    graph.add_edge("correction", END)
    initial_state = cast(
        TranscriberState,
        {
            "source_path": "/virtual/source.mp4",
            "source_type": "video",
            "audio_path": "/virtual/source.wav",
            "model_name": "offline-model",
            "result": transcription_result(),
            "messages": [],
        },
    )

    final_state = graph.compile().invoke(
        initial_state,
        context=workflow_context,
    )

    assert final_state["input_tokens"] == 9
    assert final_state["output_tokens"] == 14
    assert final_state["total_tokens"] == 23
    assert final_state["messages"]
    assert final_state["status"] == "corrected"
    assert final_state["result"].text == "The speaker says Pydantic."


def test_need_correction_is_not_declared_in_state() -> None:
    """Document that need_correction remains absent from state annotations."""
    assert "need_correction" not in TranscriberState.__annotations__
    assert "need_correction" not in TranscriberState.__required_keys__
    assert "need_correction" not in TranscriberState.__optional_keys__


def test_secondary_router_ignores_declared_correction_llm_field() -> None:
    """Route without correction when only correction_llm is true."""
    state = cast(
        TranscriberState,
        {
            "audio_duration_in_seconds": 30.0,
            "correction_llm": True,
        },
    )

    assert secondary_router(state) == "not_correction"


def test_secondary_router_reads_undeclared_need_correction_key() -> None:
    """Route to correction from the undeclared need_correction key."""
    state = cast(
        TranscriberState,
        {
            "audio_duration_in_seconds": 30.0,
            "correction_llm": False,
            "need_correction": True,
        },
    )

    assert secondary_router(state) == "to_correction"


def test_typed_dict_does_not_validate_values_or_extra_keys() -> None:
    """Accept invalid values and extra keys at TypedDict construction time."""
    state_factory: Any = TranscriberState

    state = state_factory(
        source_path=123,
        source_type="document",
        audio_path=None,
        model_name=object(),
        unexpected_field="preserved",
    )

    assert state["source_path"] == 123
    assert state["source_type"] == "document"
    assert state["audio_path"] is None
    assert state["unexpected_field"] == "preserved"
