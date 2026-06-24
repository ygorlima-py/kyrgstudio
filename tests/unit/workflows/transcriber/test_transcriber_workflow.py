"""Unit tests for transcriber workflow graph assembly."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

import pytest
from pytest import MonkeyPatch

import kyrg.workflows.base as workflow_base_module
from kyrg.workflows.base import CheckpointerBase
from kyrg.workflows.core import WORKFLOW_END, WORKFLOW_START
from kyrg.workflows.transcriber.nodes import (
    audio_text_converter,
    correction_transcriber,
    extract_audio,
    extract_hybrid_context,
    measure_audio,
    prepare_audio,
    primary_router,
    secondary_router,
)
from kyrg.workflows.transcriber.schemas import TranscriberWorkflowContext
from kyrg.workflows.transcriber.state import TranscriberState
from kyrg.workflows.transcriber.workflow import TranscriberWorkflow


NodeCallable = Callable[..., Any]
RouterCallable = Callable[[TranscriberState], str]


@dataclass(frozen=True)
class NodeRegistration:
    """Record one node registration."""

    name: str
    action: NodeCallable


@dataclass(frozen=True)
class EdgeRegistration:
    """Record one direct edge registration."""

    source: str
    target: str


@dataclass(frozen=True)
class ConditionalRegistration:
    """Record one conditional edge registration."""

    source: str
    router: RouterCallable
    path_map: dict[str, str]


class GraphBuilderSpy:
    """Capture graph assembly calls without compiling or running nodes."""

    def __init__(
        self,
        state_schema: type[Any],
        context_schema: type[Any],
    ) -> None:
        """Record schemas and initialize registration logs."""
        self.state_schema = state_schema
        self.context_schema = context_schema
        self.nodes: list[NodeRegistration] = []
        self.edges: list[EdgeRegistration] = []
        self.conditionals: list[ConditionalRegistration] = []

    def add_node(self, name: str, action: NodeCallable) -> None:
        """Record a node without invoking its action."""
        self.nodes.append(NodeRegistration(name, action))

    def add_edge(self, source: str, target: str) -> None:
        """Record a direct graph edge."""
        self.edges.append(EdgeRegistration(source, target))

    def add_conditional_edges(
        self,
        source: str,
        router: RouterCallable,
        path_map: dict[str, str],
    ) -> None:
        """Record a router and a defensive copy of its destination map."""
        self.conditionals.append(
            ConditionalRegistration(source, router, dict(path_map))
        )


def build_with_spy(
    monkeypatch: MonkeyPatch,
    checkpointer: CheckpointerBase | None = None,
) -> tuple[TranscriberWorkflow, GraphBuilderSpy]:
    """Build the workflow against an inert graph spy."""
    monkeypatch.setattr(
        workflow_base_module,
        "WorkflowStateGraph",
        GraphBuilderSpy,
    )
    workflow = TranscriberWorkflow(
        initial_state={},
        checkpointer=checkpointer,
    )
    graph = cast(GraphBuilderSpy, workflow.graph)
    return workflow, graph


@pytest.fixture
def built_workflow(
    monkeypatch: MonkeyPatch,
) -> tuple[TranscriberWorkflow, GraphBuilderSpy]:
    """Provide a transcriber workflow assembled through the graph spy."""
    return build_with_spy(monkeypatch)


def conditional_from(
    graph: GraphBuilderSpy,
    source: str,
) -> ConditionalRegistration:
    """Return the sole conditional registration for a source."""
    matches = [
        registration
        for registration in graph.conditionals
        if registration.source == source
    ]
    assert len(matches) == 1
    return matches[0]


def test_workflow_declares_state_and_context_schemas(
    built_workflow: tuple[TranscriberWorkflow, GraphBuilderSpy],
) -> None:
    """Use the declared state and context schemas to create the graph."""
    workflow, graph = built_workflow

    assert TranscriberWorkflow.STATE_SCHEMA is TranscriberState
    assert TranscriberWorkflow.CONTEXT_SCHEMA is TranscriberWorkflowContext
    assert graph.state_schema is TranscriberState
    assert graph.context_schema is TranscriberWorkflowContext
    assert workflow._compiled_graph is None


def test_workflow_registers_exactly_six_current_nodes(
    built_workflow: tuple[TranscriberWorkflow, GraphBuilderSpy],
) -> None:
    """Register exactly the six active nodes with their current callables."""
    _, graph = built_workflow
    registered_nodes = {
        registration.name: registration.action
        for registration in graph.nodes
    }

    assert registered_nodes == {
        "extract_audio": extract_audio,
        "prepare_audio": prepare_audio,
        "audio_text_converter": audio_text_converter,
        "measure_audio": measure_audio,
        "extract_hybrid_context": extract_hybrid_context,
        "correction_transcriber": correction_transcriber,
    }
    assert len(graph.nodes) == 6


def test_initial_router_has_current_destination_map(
    built_workflow: tuple[TranscriberWorkflow, GraphBuilderSpy],
) -> None:
    """Map both initial route names to their audio preparation nodes."""
    _, graph = built_workflow
    registration = conditional_from(graph, WORKFLOW_START)

    assert registration.router is primary_router
    assert registration.path_map == {
        "normalize_audio": "prepare_audio",
        "extract_audio": "extract_audio",
    }


def test_audio_origins_converge_on_text_converter(
    built_workflow: tuple[TranscriberWorkflow, GraphBuilderSpy],
) -> None:
    """Converge extracted and normalized audio on text conversion."""
    _, graph = built_workflow

    assert EdgeRegistration(
        "extract_audio",
        "audio_text_converter",
    ) in graph.edges
    assert EdgeRegistration(
        "prepare_audio",
        "audio_text_converter",
    ) in graph.edges


def test_text_converter_flows_to_audio_measurement(
    built_workflow: tuple[TranscriberWorkflow, GraphBuilderSpy],
) -> None:
    """Connect audio text conversion directly to duration measurement."""
    _, graph = built_workflow

    assert EdgeRegistration(
        "audio_text_converter",
        "measure_audio",
    ) in graph.edges


def test_measurement_router_has_current_destination_map(
    built_workflow: tuple[TranscriberWorkflow, GraphBuilderSpy],
) -> None:
    """Map correction and completion routes from audio measurement."""
    _, graph = built_workflow
    registration = conditional_from(graph, "measure_audio")

    assert registration.router is secondary_router
    assert registration.path_map == {
        "to_correction": "extract_hybrid_context",
        "not_correction": WORKFLOW_END,
    }


def test_correction_path_flows_through_context_to_end(
    built_workflow: tuple[TranscriberWorkflow, GraphBuilderSpy],
) -> None:
    """Connect domain context to correction and then workflow completion."""
    _, graph = built_workflow

    assert EdgeRegistration(
        "extract_hybrid_context",
        "correction_transcriber",
    ) in graph.edges
    assert EdgeRegistration(
        "correction_transcriber",
        WORKFLOW_END,
    ) in graph.edges


def test_workflow_has_no_quality_agent_components(
    built_workflow: tuple[TranscriberWorkflow, GraphBuilderSpy],
) -> None:
    """Exclude quality-agent nodes, edges, and routers from assembly."""
    _, graph = built_workflow
    registered_node_names = {node.name for node in graph.nodes}
    registered_routers = {
        conditional.router for conditional in graph.conditionals
    }
    edge_labels = {
        label
        for edge in graph.edges
        for label in (edge.source, edge.target)
    }

    assert all("quality" not in name for name in registered_node_names)
    assert all("quality" not in label for label in edge_labels)
    assert registered_routers == {primary_router, secondary_router}


def test_workflow_has_no_inactive_control_components(
    built_workflow: tuple[TranscriberWorkflow, GraphBuilderSpy],
) -> None:
    """Exclude inactive recovery, review, cleanup, and checkpoint controls."""
    _, graph = built_workflow
    forbidden_fragments = {
        "retry",
        "fallback",
        "human",
        "review",
        "accept",
        "cleanup",
        "checkpoint",
    }
    labels = {node.name for node in graph.nodes}
    labels.update(edge.source for edge in graph.edges)
    labels.update(edge.target for edge in graph.edges)
    for conditional in graph.conditionals:
        labels.add(conditional.source)
        labels.update(conditional.path_map)
        labels.update(conditional.path_map.values())

    assert not {
        fragment
        for fragment in forbidden_fragments
        if any(fragment in label for label in labels)
    }


def test_imported_checkpointer_does_not_participate_in_build(
    monkeypatch: MonkeyPatch,
) -> None:
    """Store an inert checkpointer without consulting it during assembly."""
    inert_checkpointer = cast(CheckpointerBase, object())

    workflow, graph = build_with_spy(monkeypatch, inert_checkpointer)

    assert workflow.checkpointer is inert_checkpointer
    assert len(graph.nodes) == 6
    assert len(graph.edges) == 5
    assert len(graph.conditionals) == 2
    assert workflow._compiled_graph is None


@pytest.mark.parametrize(
    ("source_type", "expected_route"),
    (("audio", "normalize_audio"), ("video", "extract_audio")),
)
def test_primary_router_returns_registered_origin_routes(
    built_workflow: tuple[TranscriberWorkflow, GraphBuilderSpy],
    source_type: str,
    expected_route: str,
) -> None:
    """Return a registered route for each supported source origin."""
    _, graph = built_workflow
    registration = conditional_from(graph, WORKFLOW_START)
    state = cast(TranscriberState, {"source_type": source_type})

    route = registration.router(state)

    assert route == expected_route
    assert route in registration.path_map


@pytest.mark.parametrize(
    ("duration", "need_correction", "expected_route"),
    (
        (180.0, True, "to_correction"),
        (180.001, True, "not_correction"),
        (30.0, False, "not_correction"),
    ),
)
def test_secondary_router_returns_registered_duration_routes(
    built_workflow: tuple[TranscriberWorkflow, GraphBuilderSpy],
    duration: float,
    need_correction: bool,
    expected_route: str,
) -> None:
    """Return registered correction routes with an inclusive 180 limit."""
    _, graph = built_workflow
    registration = conditional_from(graph, "measure_audio")
    state = cast(
        TranscriberState,
        {
            "audio_duration_in_seconds": duration,
            "need_correction": need_correction,
        },
    )

    route = registration.router(state)

    assert route == expected_route
    assert route in registration.path_map
