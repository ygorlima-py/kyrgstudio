from dataclasses import dataclass, field

from kyrg.llms.base import LLMBase

@dataclass(frozen=True)
class CopyAnalysisWorkflowContext:
    analysis_llm: LLMBase = field(
        metadata={
            "description": "LLM used to extract copy structure, offer elements, and persuasion analysis."
        }
    )