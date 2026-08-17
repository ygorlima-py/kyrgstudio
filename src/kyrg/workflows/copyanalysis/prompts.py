"""Prompt templates used by copy analysis LLM actions."""

class CopyAnalysisPrompts:
    """Centralized prompt templates for copy structure, offer, and persuasion tasks."""

    EXTRACT_COPY_STRUCTURE = """
    <language>
    {language}
    </language>

    <clean_transcript>
    {clean_transcript}
    </clean_transcript>

    <structured_transcription>
    {structured_transcription}
    </structured_transcription>
    """
    
    EXTRACT_OFFER_ELEMENTS = """
    <language>
    {language}
    </language>

    <clean_transcript>
    {clean_transcript}
    </clean_transcript>

    <copy_structure>
    {copy_structure}
    </copy_structure>
    """
    
    ANALYSE_PERSUASION = """

    <language>
    {language}
    </language>

    <copy_structure>
    {copy_structure}
    </copy_structure>

    <offer_analysis>
    {offer_analysis}
    </offer_analysis>

    """
