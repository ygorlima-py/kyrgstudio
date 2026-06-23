from typing import Any

from kyrg.workflows.copyanalysis.schemas import CopyAnalysisOutput
from kyrg.workflows.copyadaptation.constants import SECTION_ADAPTATION_FIELDS
from kyrg.workflows.copyadaptation.schemas import UserProfileOutput

def _deduplicate(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))

def _collect_profile_gaps(
    user_profile: UserProfileOutput,
) -> list[str]:
    gaps = []

    if not user_profile.proof_assets:
        gaps.append("User profile has no proof assets available")

    if user_profile.unique_mechanism is None:
        gaps.append("User profile has no unique mechanism defined")

    return gaps

def _collect_persuasion_gaps(
    copy_analysis: CopyAnalysisOutput,
) -> list[str]:
    persuasion = copy_analysis.persuasion_analysis
    gaps = []

    strengths = {
        "hook_strength": persuasion.hook_strength,
        "promise_clarity": persuasion.promise_clarity,
        "proof_strength": persuasion.proof_strength,
        "urgency_strength": persuasion.urgency_strength,
        "cta_strength": persuasion.cta_strength,
    }

    for field_name, strength in strengths.items():
        if strength == "low":
            gaps.append(f"Low persuasion score: {field_name}")

    gaps.extend(weakness.issue for weakness in persuasion.weaknesses)
    return gaps

def _classify_section_gaps(
    copy_analysis: CopyAnalysisOutput,
) -> tuple[list[str], list[str]]:
    sections_to_create = []
    gaps_to_fix = []

    for gap in copy_analysis.copy_structure.section_gaps:
        if gap.gap_type == "missing":
            if gap.section_type not in sections_to_create:
                sections_to_create.append(gap.section_type)
            continue

        gaps_to_fix.append(
            f"{gap.gap_type} section '{gap.section_type}': {gap.reason}"
        )

    return sections_to_create, gaps_to_fix

def _map_reference_sections(
    copy_analysis: CopyAnalysisOutput,
) -> list[dict[str, Any]]:
    mapped_sections = []

    for section in copy_analysis.copy_structure.sections:
        section_type = section.section_type.strip().lower()

        mapped_sections.append(
            {
                "reference_section_type": section.section_type,
                "reference_text": section.text,
                "reference_purpose": section.purpose,
                "start": section.start,
                "end": section.end,
                "has_direct_equivalent": (
                    section_type in SECTION_ADAPTATION_FIELDS
                ),
                "user_profile_fields": SECTION_ADAPTATION_FIELDS.get(
                    section_type,
                    [
                        "product_or_solution",
                        "target_audience",
                        "main_promise",
                    ],
                ),
            }
        )

    return mapped_sections

def _resolve_target_language(
    copy_analysis: CopyAnalysisOutput,
    user_profile: UserProfileOutput,
) -> str:
    language = (
        user_profile.target_language
        or copy_analysis.language
        or copy_analysis.copy_structure.language
    )

    if language is None:
        raise ValueError("target_language is required to prepare adaptation input")

    return language


def _build_adaptation_input(
    copy_analysis: CopyAnalysisOutput,
    user_profile: UserProfileOutput,
) -> dict[str, Any]:
    target_language = _resolve_target_language(copy_analysis, user_profile)
    mapped_sections = _map_reference_sections(copy_analysis)
    sections_to_create, structural_gaps = _classify_section_gaps(copy_analysis)

    gaps_to_fix = _deduplicate(
        [
            *structural_gaps,
            *_collect_persuasion_gaps(copy_analysis),
            *_collect_profile_gaps(user_profile),
        ]
    )

    output = {
        "mapped_sections": mapped_sections,
        "sections_to_create": sections_to_create,
        "gaps_to_fix": gaps_to_fix,
        "target_language": target_language,
        "platform": user_profile.platform or "generic",
    }

    if user_profile.desired_duration is not None:
        output["desired_duration"] = user_profile.desired_duration

    return output

