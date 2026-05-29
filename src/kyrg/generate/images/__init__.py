"""Public image generation API.

This package exposes provider adapters and shared schemas for image generation.
Adapters normalize provider-specific responses into Kyrg's image output models,
so callers can work with one stable contract across OpenAI, OpenRouter, and
Gemini.
"""

from kyrg.generate.images.schemas import ImageGeneratorInput, ImageGeneratorOutput
from kyrg.generate.images.gemini_provider import GeminiImageGenerator
from kyrg.generate.images.openai_provider import OpenAIImageGenerator
from kyrg.generate.images.openrouter_provider import OpenRouterImageGenerator

__all__ = [
    "ImageGeneratorInput",
    "ImageGeneratorOutput",
    "GeminiImageGenerator",
    "OpenAIImageGenerator",
    "OpenRouterImageGenerator",
]
