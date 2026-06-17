from kyrg.workflows.copyadaptation.state import CopyAdaptationState
import json
from typing import Any

def _calculate_time_estimated(state) -> dict[str, Any]:
    MAX_WORDS_PER_MINUTE = 150
    MIN_WORDS_PER_MINUTE = 120
    MEAN_WORDS_PER_MINUTE = (MAX_WORDS_PER_MINUTE + MIN_WORDS_PER_MINUTE) / 2

    sections = state.get("sections")
    desired_duration = state.get("desired_duration")

    if not sections:
        raise ValueError("sections is required to calculate script timing")

    section_texts = [
        section["text"].strip()
        for section in sections
        if section.get("text")
    ]

    word_count = sum(len(text.split()) for text in section_texts)
    estimated_duration = (
        round(word_count / MEAN_WORDS_PER_MINUTE, 2)
        if word_count
        else None
    )

    min_words = None
    max_words = None
    duration_status = "unknown"

    if desired_duration is not None:
        min_words = round(MIN_WORDS_PER_MINUTE * desired_duration)
        max_words = round(MAX_WORDS_PER_MINUTE * desired_duration)

        if word_count < min_words:
            duration_status = "too_short"
        elif word_count > max_words:
            duration_status = "too_long"
        else:
            duration_status = "ok"

    return {
        "word_count": word_count,
        "estimated_duration": estimated_duration,
        "min_words": min_words,
        "max_words": max_words,
        "duration_status": duration_status,
    }
    
def _resolve_final_sections(state: CopyAdaptationState) -> list[dict]:
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
    with open("CopyAdaptationWorkflow.json", "r", encoding="utf-8") as file:
        result = json.load(file)
        
        print(_calculate_time_estimated(result))
        