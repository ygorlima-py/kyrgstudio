from kyrg.workflows.copyanalysis.state import CopyAnalysisState


def prepare_copy_input(state: CopyAnalysisState) -> dict:
    ...


def extract_copy_structure(state: CopyAnalysisState) -> dict:
    ...


def extract_offer_elements(state: CopyAnalysisState) -> dict:
    ...


def analyse_persuasion(state: CopyAnalysisState) -> dict:
    ...


def build_copy_analysis(state: CopyAnalysisState) -> dict:
    ...
