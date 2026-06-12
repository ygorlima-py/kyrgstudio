from __future__ import annotations

from dataclasses import dataclass, field
from pydantic import BaseModel, Field

from kyrg.llms.base import LLMBase

@dataclass(frozen=True)
class CopyAnalysisWorkflowContext:
    analysis_llm: LLMBase = field(
        metadata={
            "description": "LLM used to extract copy structure, offer elements, and persuasion analysis."
        }
    )

class StructuredTranscript(BaseModel):
    start: float | None = Field(
        default=None,
        description="Start time of the transcript segment in seconds, when available."
    )
    end: float | None = Field(
        default=None,
        description="End time of the transcript segment in seconds, when available."
    )
    text: str = Field(
        description="Transcript text spoken during this segment."
    )
    
class CopyStructureOutput(BaseModel):
    language: str | None = Field(
        default=None,
        description="Detected language of the copy."
    )
    content_type: str = Field(
        description="Type of content, such as VSL, short ad, webinar, organic video, reel, or sales presentation."
    )
    main_hook: str | None = Field(
        default=None,
        description="Main opening hook used to capture attention."
    )
    sections: list[CopySection] = Field(
        default_factory=list,
        description="Ordered list of structural sections found in the copy."
    )
    narrative_flow: list[str] = Field(
        default_factory=list,
        description="High-level sequence of how the message progresses from start to end."
    )
    missing_sections: list[str] = Field(
        default_factory=list,
        description="Important copy sections that were expected but not found."
    )
    summary: str = Field(
        description="Short explanation of the overall copy structure."
    )
    
class CopySection(BaseModel):
    section_type: str = Field(
        description="Type of copy section, such as hook, problem, promise, proof, offer, CTA, story, objection, or transition."
    )
    text: str = Field(
        description="Exact or summarized text that represents this section."
    )
    purpose: str = Field(
        description="Strategic role of this section inside the sales message."
    )
    start: float | None = Field(
        default=None,
        description="Start time of this section in seconds, when available."
    )
    end: float | None = Field(
        default=None,
        description="End time of this section in seconds, when available."
    )

class OfferElement(BaseModel):
    name: str = Field(
        description="Name or short label of the offer element."
    )
    description: str = Field(
        description="Explanation of how this element appears in the analyzed copy."
    )
    evidence: str | None = Field(
        default=None,
        description="Text excerpt or summary that supports this extraction."
    )


class OfferAnalysisOutput(BaseModel):
    product_or_solution: str | None = Field(
        default=None,
        description="Product, service, method, opportunity, or solution being promoted."
    )
    target_audience: str | None = Field(
        default=None,
        description="Likely audience the offer is trying to reach."
    )
    core_problem: str | None = Field(
        default=None,
        description="Main problem, pain, or frustration addressed by the offer."
    )
    core_desire: str | None = Field(
        default=None,
        description="Main desire, aspiration, or outcome the audience wants."
    )
    main_promise: str | None = Field(
        default=None,
        description="Primary promise or transformation suggested by the offer."
    )
    unique_mechanism: str | None = Field(
        default=None,
        description="Unique mechanism, method, angle, or explanation used to make the offer feel different."
    )
    benefits: list[OfferElement] = Field(
        default_factory=list,
        description="Benefits communicated in the copy."
    )
    objections: list[OfferElement] = Field(
        default_factory=list,
        description="Objections, doubts, fears, or barriers addressed by the copy."
    )
    proof_elements: list[OfferElement] = Field(
        default_factory=list,
        description="Proof, credibility, authority, social proof, case studies, demonstrations, or evidence used."
    )
    bonuses: list[OfferElement] = Field(
        default_factory=list,
        description="Bonuses, extras, added value, or secondary deliverables mentioned."
    )
    urgency_or_scarcity: list[OfferElement] = Field(
        default_factory=list,
        description="Urgency, scarcity, deadline, limited availability, or time-sensitive reasons to act."
    )
    call_to_action: str | None = Field(
        default=None,
        description="Main action the viewer is asked to take."
    )
    price_or_terms: str | None = Field(
        default=None,
        description="Price, discount, payment terms, guarantee, trial, or commercial condition mentioned."
    )
    summary: str = Field(
        description="Short summary of the offer extracted from the copy."
    )
    
class PersuasionSignal(BaseModel):
    name: str = Field(
        description="Name of the persuasion signal, trigger, technique, or pattern detected."
    )
    description: str = Field(
        description="Explanation of how this persuasion signal appears in the copy."
    )
    evidence: str | None = Field(
        default=None,
        description="Text excerpt or concise summary from the analyzed copy that supports this signal."
    )
    strength: str = Field(
        description="Estimated strength of this signal. Use only: low, medium, or high."
    )


class PersuasionWeakness(BaseModel):
    issue: str = Field(
        description="Persuasive weakness, gap, risk, or unclear element found in the copy."
    )
    impact: str = Field(
        description="Explanation of how this weakness may reduce clarity, trust, urgency, desire, or conversion."
    )
    evidence: str | None = Field(
        default=None,
        description="Text excerpt or concise summary from the analyzed copy that supports this weakness."
    )


class PersuasionAnalysisOutput(BaseModel):
    dominant_emotion: str | None = Field(
        default=None,
        description="Main emotion the copy tries to create, such as fear, desire, curiosity, urgency, hope, frustration, relief, aspiration, or trust."
    )
    persuasion_pattern: str | None = Field(
        default=None,
        description="Main persuasion structure detected, such as AIDA, PAS, BAB, storytelling, list-based, problem-solution, education-to-offer, or hybrid."
    )
    hook_strength: str | None = Field(
        default=None,
        description="Estimated strength of the opening hook. Use only: low, medium, or high."
    )
    promise_clarity: str | None = Field(
        default=None,
        description="Estimated clarity of the main promise. Use only: low, medium, or high."
    )
    proof_strength: str | None = Field(
        default=None,
        description="Estimated strength of proof and credibility. Use only: low, medium, or high."
    )
    urgency_strength: str | None = Field(
        default=None,
        description="Estimated strength of urgency or scarcity. Use only: low, medium, or high."
    )
    cta_strength: str | None = Field(
        default=None,
        description="Estimated strength and clarity of the call to action. Use only: low, medium, or high."
    )
    persuasion_signals: list[PersuasionSignal] = Field(
        default_factory=list,
        description="Persuasion techniques, emotional triggers, conversion mechanisms, or strategic signals detected in the copy."
    )
    weaknesses: list[PersuasionWeakness] = Field(
        default_factory=list,
        description="Weaknesses, gaps, risks, or unclear parts in the persuasive argument."
    )
    summary: str = Field(
        description="Short summary explaining how the copy persuades the viewer."
    )
    
class CopyAnalysisOutput(BaseModel):
    language: str | None = Field(
        default=None,
        description="Language detected in the analyzed copy."
    )
    copy_structure: CopyStructureOutput = Field(
        description="Structural analysis of how the copy is organized."
    )
    offer_analysis: OfferAnalysisOutput = Field(
        description="Extracted offer, audience, promise, objections, proof, and CTA elements."
    )
    persuasion_analysis: PersuasionAnalysisOutput = Field(
        description="Persuasion diagnosis based on the copy structure and offer analysis."
    )