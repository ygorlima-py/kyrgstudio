"""Public API for the copy analysis workflow package."""

from kyrg.workflows.copyanalysis.actions import (
    AnalysePersuasion,
    ExtractCopyStructure,
    ExtractOfferElements,
)
from kyrg.workflows.copyanalysis.nodes import (
    aanalyse_persuasion,
    aextract_copy_structure,
    aextract_offer_elements,
    analyse_persuasion,
    build_copy_analysis,
    extract_copy_structure,
    extract_offer_elements,
    prepare_copy_input,
)
from kyrg.workflows.copyanalysis.schemas import (
    CopyAnalysisOutput,
    CopyAnalysisWorkflowContext,
    CopySection,
    CopyStructureOutput,
    OfferAnalysisOutput,
    OfferElement,
    PersuasionAnalysisOutput,
    PersuasionSignal,
    PersuasionWeakness,
    SectionGap,
    StructuredTranscript,
)
from kyrg.workflows.copyanalysis.state import CopyAnalysisState
from kyrg.workflows.copyanalysis.workflow import CopyAnalysisWorkflow

__all__ = [
    "AnalysePersuasion",
    "CopyAnalysisOutput",
    "CopyAnalysisState",
    "CopyAnalysisWorkflow",
    "CopyAnalysisWorkflowContext",
    "CopySection",
    "CopyStructureOutput",
    "ExtractCopyStructure",
    "ExtractOfferElements",
    "OfferAnalysisOutput",
    "OfferElement",
    "PersuasionAnalysisOutput",
    "PersuasionSignal",
    "PersuasionWeakness",
    "SectionGap",
    "StructuredTranscript",
    "aanalyse_persuasion",
    "aextract_copy_structure",
    "aextract_offer_elements",
    "analyse_persuasion",
    "build_copy_analysis",
    "extract_copy_structure",
    "extract_offer_elements",
    "prepare_copy_input",
]
