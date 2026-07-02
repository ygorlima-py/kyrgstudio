"""Deterministic assembly and timing helpers for adapted scripts.

LLM nodes produce section content, but final script assembly, word counts,
timing estimates, pauses, and review-revision merging are deterministic. Keeping
that logic here makes the workflow output reproducible and easier to validate.
"""

from __future__ import annotations

from kyrg.workflows.copyadaptation.state import CopyAdaptationState
from kyrg.workflows.copyadaptation.schemas import (
    ScriptSectionOutput,
    TimedScriptSectionOutput,
    WriteScriptSectionsOutput,
    ValidationIssue,
)
from kyrg.workflows.copyadaptation.constants import PAUSE_INTENT_COEFFICIENT, SECTION_PAUSE_SECONDS

import json
from typing import Any

class _BuildScriptOutput:
    """Build final output projections from the latest workflow state.

    The builder resolves the final section list, exposes human-readable and
    voice-ready script text, extracts hooks and CTA content, and enriches
    sections with deterministic timing metadata.
    """

    def __init__(self, state: CopyAdaptationState):
        sections = _resolve_final_sections(state)
        desired_duration = state.get("desired_duration")
        if not sections:
            raise ValueError("sections is required to build script")

        if desired_duration is None:
            raise ValueError("desired_duration is required to build script")

        self.sections = sections
        self.desired_duration = desired_duration
        self.max_words_per_minute = state.get("max_words_per_minute", 160)
        self.min_words_per_minute = state.get("min_words_per_minute", 140)
        self.mean_words_per_minutes = (
            self.max_words_per_minute + self.min_words_per_minute
        ) / 2
        self.issues = state.get("validation_errors")
        self.warnings = state.get("validation_warnings")
    
    def _voice_ready_text(self) -> str:
        """Return narration text without markdown headings or metadata."""

        section_texts = [
            section["text"].strip()
            for section in self.sections
            if section.get("text")
        ]
        
        return "\n\n".join(section_texts)
    
    def _script(self) -> str:
        """Return review-friendly script text grouped by section heading."""

        script = "\n\n".join(
        f"## {section.get('section_type', 'section')}\n{section.get('text', '').strip()}"
        for section in self.sections
        if section.get("text")
    )
        return script

    def _hooks(self) -> list[Any]:
        """Return hook texts that can be surfaced as script openers."""

        
        return [
            section["text"].strip()
            for section in self.sections
            if section.get("section_type") == "hook" and section.get("text")
        ]
        
    def _cta_sections(self) -> list[Any]:
        """Return all CTA section texts, preserving final section order."""

        return  [
            section["text"].strip()
            for section in self.sections
            if section.get("section_type") == "cta" and section.get("text")
        ]
        
    def _final_sections(self) -> list[TimedScriptSectionOutput]:
        """Validate sections and attach word count, duration, and cue timing."""

        sections = [
            ScriptSectionOutput.model_validate(section)
            for section in self.sections
        ]

        final_sections = []
        cursor = 0.0

        for index, section in enumerate(sections):
            word_count = len(section.text.split())

            duration = round(
                (word_count / self.mean_words_per_minutes) * 60,
                2,
            )
            is_last_section = index == len(sections) - 1
            pause = (
                0.0
                if is_last_section
                else _resolve_pause(
                    section_type=section.section_type,
                    pause_intent=section.pause_intent,
                )
            )

            start = round(cursor, 2)
            end = round(start + duration, 2)

            final_sections.append(
                TimedScriptSectionOutput(
                    **section.model_dump(),
                    word_count=word_count,
                    estimated_duration_seconds=duration,
                    pause_after_seconds=pause,
                    start_seconds=start,
                    end_seconds=end,
                )
            )

            cursor = round(end + pause, 2)
                
        return final_sections
    
    @property
    def _validation_issues_from_state(self) -> list[ValidationIssue]:
            """Return validation errors from state as typed issue objects."""

            return [
                ValidationIssue.model_validate(issue)
                for issue in self.issues or []
            ]
            
    @property
    def _validation_warnings_from_state(self) -> list[ValidationIssue]:
            """Return validation warnings from state as typed issue objects."""

            return [
                ValidationIssue.model_validate(warnings)
                for warnings in self.warnings or []
            ]

def _add_words_count_per_section(script_sections: WriteScriptSectionsOutput) -> list[dict[str, Any]]:
    """Return generated sections as dictionaries with deterministic word counts."""

    sections = [
        section.model_dump()
        for section in script_sections.sections
    ]
    
    for section in sections:
        section["word_count"] = len(section["text"].split())

    return sections

def _resolve_pause(section_type: str, pause_intent: str = "medium") -> float:
    """Resolve semantic pause intent into a bounded pause duration in seconds."""

    base = SECTION_PAUSE_SECONDS.get(section_type, 0.4)
    coefficient = PAUSE_INTENT_COEFFICIENT.get(pause_intent, 1.0)

    return round(min(max(base * coefficient, 0.1), 1.8), 2)
    
def _calculate_time_estimated(state) -> dict[str, Any]:
    """Estimate script duration and target-duration fit from current sections."""

    MAX_WORDS_PER_MINUTE = state.get("max_words_per_minute", 160)
    MIN_WORDS_PER_MINUTE = state.get("min_words_per_minute", 140)
    MEAN_WORDS_PER_MINUTE = (MAX_WORDS_PER_MINUTE + MIN_WORDS_PER_MINUTE) / 2

    sections = _resolve_final_sections(state)
    desired_duration = state.get("desired_duration")

    if not sections:
        raise ValueError("sections is required to calculate script timing")

    word_count = 0
    speech_seconds = 0.0
    pause_seconds = 0.0

    for index, section in enumerate(sections):
        text = section.get("text", "")
        words = len(text.split())
        word_count += words
        speech_seconds += round((words / MEAN_WORDS_PER_MINUTE) * 60, 2)

        is_last_section = index == len(sections) - 1
        if not is_last_section:
            pause_seconds += _resolve_pause(
                section_type=section.get("section_type", "section"),
                pause_intent=section.get("pause_intent", "medium"),
            )

    total_seconds = speech_seconds + pause_seconds
    estimated_duration_seconds = round(total_seconds, 2) if word_count else None

    min_words = None
    max_words = None
    duration_status = "unknown"

    if desired_duration is not None:
        target_seconds = desired_duration * 60
        available_speech_seconds = max(target_seconds - pause_seconds, 0)
        min_words = round((available_speech_seconds / 60) * MIN_WORDS_PER_MINUTE)
        max_words = round((available_speech_seconds / 60) * MAX_WORDS_PER_MINUTE)

        if total_seconds > target_seconds:
            duration_status = "too_long"
        elif word_count < min_words:
            duration_status = "too_short"
        else:
            duration_status = "ok"

    return {
        "word_count": word_count,
        "speech_seconds": round(speech_seconds, 2),
        "pause_seconds": round(pause_seconds, 2),
        "total_seconds": round(total_seconds, 2),
        "estimated_duration_seconds": estimated_duration_seconds,
        "min_words": min_words,
        "max_words": max_words,
        "duration_status": duration_status,
    }
    
def _resolve_final_sections(state: CopyAdaptationState) -> list[dict]:
    """Merge reviewer-adjusted sections into the latest generated section list.

    Review nodes may return only the sections they adjusted. This helper applies
    those replacements by section order, appends new revised sections when
    needed, and returns a stable order for final validation or assembly.
    """

    sections = state.get("sections")

    if not sections:
        raise ValueError("sections is required to resolve final script sections")

    sections_revised = state.get("sections_revised") or []

    if not sections_revised:
        return sections

    final_sections = [section.copy() for section in sections]
    sections_by_order = {
        section.get("order"): index
        for index, section in enumerate(final_sections)
        if section.get("order") is not None
    }

    for revised_section in sections_revised:
        order = revised_section.get("order")

        if order in sections_by_order:
            final_sections[sections_by_order[order]] = revised_section
            continue

        final_sections.append(revised_section)

    return sorted(
        final_sections,
        key=lambda section: section.get("order", 0),
    )
    
 
if __name__ == "__main__":
    from rich import print
    
    with open("CopyAdaptationWorkflow.json", "r", encoding="utf-8") as file:
        result = json.load(file)
        
        build_copy = _BuildScriptOutput(result)
        
        print(build_copy._final_sections())
