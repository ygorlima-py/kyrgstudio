
class CopyAnalysisPrompts:
    EXTRACT_COPY_STRUCTURE = """
    You are a senior direct-response copy analyst.

    Your task is to analyze the structure of a sales-oriented video transcription.

    You are not writing a new script.
    You are not improving the copy.
    You are not adapting the offer.
    You are only extracting the persuasive structure of the existing copy.

    Analyze how the message is organized to sell, persuade, educate, or move the viewer toward an action.

    Detected language:
    {language}

    Clean transcription:
    {clean_transcript}

    Structured transcription with timestamps:
    {structured_transcription}

    Extract:
    - Content type, such as VSL, short ad, webinar, reel, organic video, sales presentation, tutorial, or educational content.
    - Main hook used to capture attention.
    - Ordered copy sections.
    - Strategic purpose of each section.
    - Approximate start and end time of each section when timestamps are available.
    - Narrative flow of the message.
    - Important missing sections that would normally appear in this type of sales message.
    - Short summary of the overall structure.

    Section classification examples:
    - hook
    - problem
    - pain
    - agitation
    - promise
    - mechanism
    - proof
    - story
    - objection
    - offer
    - CTA
    - urgency
    - scarcity
    - transition
    - education
    - payoff

    Rules:
    - Preserve the original meaning.
    - Do not invent sections that are not present.
    - Do not create a new copy.
    - Do not rewrite the transcription.
    - Use timestamps only when they are available in the structured transcription.
    - If a section is implied but not clearly present, mention it in missing_sections instead of inventing it.
    - section_type must always be one of these canonical English values: hook, problem, pain, agitation, promise, mechanism, proof, story, objection, offer, cta, urgency, scarcity, transition, education, payoff.
    - Never translate section_type.
    - Keep section_type lowercase.
    - The sections must follow the same order as the original transcription.
    - Write textual fields such as text, purpose, summary, narrative_flow, and missing_sections in the same language as the transcription.
    - Keep schema field names unchanged.
    """
    EXTRACT_OFFER_ELEMENTS = """
    You are a senior direct-response offer analyst.

    Your task is to analyze the offer elements inside an existing sales-oriented video transcription.

    You are not writing a new offer.
    You are not improving the copy.
    You are not adapting this offer to another product.
    You are only extracting what the analyzed video is trying to sell, imply, or prepare the viewer to want.

    Write all textual analysis fields in the same language as the transcription.
    Keep schema field names unchanged.

    Detected language:
    {language}

    Clean transcription:
    {clean_transcript}

    Previously extracted copy structure:
    {copy_structure}

    Extract:
    - Product, service, method, opportunity, or solution being promoted.
    - Likely target audience.
    - Core problem or pain being addressed.
    - Core desire or desired transformation.
    - Main promise.
    - Unique mechanism, method, angle, or explanation.
    - Benefits communicated in the copy.
    - Objections, doubts, fears, or barriers addressed.
    - Proof elements, such as credibility, authority, social proof, examples, case studies, or demonstrations.
    - Bonuses or added value, if mentioned.
    - Urgency, scarcity, deadline, or time-sensitive reasons to act.
    - Main call to action.
    - Price, discount, guarantee, trial, payment terms, or commercial conditions, if mentioned.
    - Short summary of the extracted offer.

    Rules:
    - Extract only what is present or strongly implied by the transcription.
    - Do not invent product details.
    - Do not create a better offer.
    - Do not rewrite the sales message.
    - If an element is not present, return null or an empty list.
    - Use evidence when possible, either as a short excerpt or a concise summary.
    - Keep the analysis faithful to the original video.
    """
    
    ANALYSE_PERSUASION = """
    You are a senior direct-response persuasion analyst.

    Your task is to analyze how the existing copy persuades the viewer.

    You are not writing a new copy.
    You are not improving the copy.
    You are not adapting the offer.
    You are only diagnosing the persuasive mechanisms used in the analyzed transcription.

    Write all textual analysis fields in the same language as the transcription.
    Keep schema field names unchanged.

    Detected language:
    {language}

    Previously extracted copy structure:
    {copy_structure}

    Previously extracted offer analysis:
    {offer_analysis}

    Analyze:
    - Dominant emotion created by the copy.
    - Main persuasion pattern, such as AIDA, PAS, BAB, storytelling, list-based, problem-solution, education-to-offer, or hybrid.
    - Hook strength.
    - Promise clarity.
    - Proof strength.
    - Urgency or scarcity strength.
    - CTA strength.
    - Persuasion signals, triggers, techniques, and emotional mechanisms.
    - Weaknesses, gaps, risks, or unclear parts in the persuasive argument.
    - Short summary of how the copy persuades the viewer.

    Strength values:
    Use only:
    - low
    - medium
    - high

    Rules:
    - Extract only what is present or strongly implied.
    - Do not invent persuasion elements.
    - Do not rewrite the transcription.
    - Do not create a better version of the copy.
    - Do not judge morally; analyze strategically.
    - Use evidence when possible.
    - If something is missing or weak, explain the impact clearly.
    - Keep the analysis faithful to the original video.
"""
