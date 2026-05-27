"""OpenRouter voice generation adapter.

OpenRouter is treated as an OpenAI-compatible speech provider, so this module
only defines the provider name and base URL while reusing OpenAITTSBase for the
request and normalization behavior.
"""

from kyrg.generate.voices.openai import OpenAITTSBase


class OpenRouterVoiceGenerator(OpenAITTSBase):
    """Generate speech audio through OpenRouter's OpenAI-compatible API."""

    PROVIDER = 'openrouter'
    URL = "https://openrouter.ai/api/v1"
