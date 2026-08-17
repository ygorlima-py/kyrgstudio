"""Prompt templates used by copy adaptation actions.

Prompts are centralized here so action classes can focus on input formatting and
structured response handling. The prompt text defines the workflow contracts for
strategy, writing, flow review, validation, and correction passes.
"""


class CopyAdaptationPrompts:
    """Immutable prompt catalog for each LLM-backed workflow step."""

    BUILD_COPY_STRATEGY = """
<target_language>
{target_language}
</target_language>

<platform>
{platform}
</platform>

<desired_duration>
{desired_duration}
</desired_duration>

<reference_copy_analysis>
{copy_analysis}
</reference_copy_analysis>    

<offer_profile>
{user_profile}
</offer_profile>

<mapped_reference_sections>
{mapped_sections}
</mapped_reference_sections>

Sections that must be created from scratch:
<sections_create>
{sections_to_create}
</sections_create>

<gaps_to_fix>
{gaps_to_fix}
</gaps_to_fix>
"""

    WRITE_SCRIPT_SECTIONS = """
<target_language>
{target_language}
</target_language>

<platform>
{platform}
</platform>

<desired_duration>
{desired_duration}
</desired_duration>

<offer_profile>
{user_profile}
</offer_profile>

<mapped_sections>
{mapped_sections}
</mapped_sections>

Sections that must be created from scratch:
<sections_to_create>
{sections_to_create}
</sections_to_create>

<gaps_to_fix>
{gaps_to_fix}
</gaps_to_fix>

<copy_strategy>
- <main_angle>{main_angle}</main_angle>
- <awareness_level>{awareness_level}</awareness_level>
- <main_promise>{main_promise}</main_promise>
- <persuasion_pattern>{persuasion_pattern}</persuasion_pattern>
- <objections_to_address>{objections_to_address}</objections_to_address>
- <unique_mechanism>{unique_mechanism}</unique_mechanism>
- <proof_plan>{proof_plan}</proof_plan>
</copy_strategy>
"""

    CORRECT_SCRIPT_SECTIONS = """

<target_language>
{target_language}
</target_language>

<platform>
{platform}
</platform>

<desired_duration>
{desired_duration}
</desired_duration>

<retry_count>
{retry_count}
</retry_count>

<offer_profile>
{user_profile}
</offer_profile>

<copy_strategy>
<main_angle>{main_angle}</main_angle>
<awareness_level>{awareness_level}</awareness_level>
<main_promise>{main_promise}</main_promise>
<persuasion_pattern>{persuasion_pattern}</persuasion_pattern>
<objections_to_address>{objections_to_address}</objections_to_address>
<proof_plan>{proof_plan}</proof_plan>
<unique_mechanism>{unique_mechanism}</unique_mechanism>
</copy_strategy>

<previous_sections>
{previous_sections}
</previous_sections>

<flow_issues>
{flow_issues}
</flow_issues>

<revision_instructions>
{revision_instructions}
</revision_instructions>

<missing_proofs>
{missing_proofs}
</missing_proofs>
"""

    REVIEW_SECTION_FLOW = """

<target_language>
{target_language}
</target_language>

<platform>
{platform}
</platform>

<desired_duration>
{desired_duration}
</desired_duration>

<copy_strategy>
<main_angle>{main_angle}</main_angle>
<awareness_level>{awareness_level}</awareness_level>
<main_promise>{main_promise}</main_promise>
<persuasion_pattern>{persuasion_pattern}</persuasion_pattern>
<objections_to_address>{objections_to_address}</objections_to_address>
<proof_plan>{proof_plan}</proof_plan>
<unique_mechanism>{unique_mechanism}</unique_mechanism>
</copy_strategy>

<sections>
{sections}
</sections>

<missing_proofs>
{missing_proofs}
</missing_proofs>
"""

    VALIDATE_SCRIPT = """
<target_language>
{target_language}
</target_language>

<platform>
{platform}
</platform>

<desired_duration>
{desired_duration}
</desired_duration>

<offer_profile>
{user_profile}
</offer_profile>

<mapped_reference_sections>
{mapped_sections}
</mapped_reference_sections>

<copy_strategy>
<main_angle>{main_angle}</main_angle>
<main_promise>{main_promise}</main_promise>
<unique_mechanism>{unique_mechanism}</unique_mechanism>
<proof_plan>{proof_plan}</proof_plan>
</copy_strategy>

<sections>
{sections}
</sections>

<missing_proofs>
{missing_proofs}
</missing_proofs>

<timing_metrics>
{timing_metrics}
</timing_metrics>

"""

    CORRECT_VALIDATED_SCRIPT = """
<target_language>
{target_language}
</target_language>

<platform>
{platform}
</platform>

<desired_duration>
{desired_duration}
</desired_duration>

<retry_count>
{retry_count}
</retry_count>

<offer_profile>
{user_profile}
</offer_profile>

<copy_strategy>
<main_angle>{main_angle}</main_angle>
<main_promise>{main_promise}</main_promise>
<unique_mechanism>{unique_mechanism}</unique_mechanism>
<proof_plan>{proof_plan}</proof_plan>
</copy_strategy>

<sections>
{sections}
</sections>

<validation_errors>
{validation_errors}
</validation_errors>

<validation_warnings>
{validation_warnings}
</validation_warnings>

<timing_metrics>
{timing_metrics}
</timing_metrics>

<missing_proofs>
{missing_proofs}
</missing_proofs>

"""
