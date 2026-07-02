"""Public generation API.

This package exposes the stable generation adapters and schemas for images,
videos, and voices. Provider-specific implementation details remain inside
their subpackages.
"""

from kyrg.generate.images import (
    GeminiImageGenerator,
    ImageGeneratorInput,
    ImageGeneratorOutput,
    OpenAIImageGenerator,
    OpenRouterImageGenerator,
)
from kyrg.generate.videos import (
    GeminiVideoGenerator,
    OpenRouterVideoGenerator,
    RunwayVideoGenerator,
    VideoGenerated,
    VideoGenerateInput,
    VideoGenerateOutput,
    VideoReferenceImage,
)
from kyrg.generate.voices import (
    ElevenLabsSpeechToSpeech,
    ElevenLabsVoiceCloner,
    ElevenLabsVoiceDesignPreview,
    ElevenLabsVoiceDesignSaver,
    ElevenLabsVoiceGenerator,
    OpenAIVoiceGenerator,
    OpenRouterVoiceGenerator,
    SpeechToSpeechInput,
    TextToSpeechInput,
    VoiceCloneInput,
    VoiceDesignInput,
    VoiceDesignOutput,
    VoiceDesignPreview,
    VoiceDesignSaveInput,
    VoiceIdentityOutput,
    VoiceOutput,
)

__all__ = [
    "ElevenLabsSpeechToSpeech",
    "ElevenLabsVoiceCloner",
    "ElevenLabsVoiceDesignPreview",
    "ElevenLabsVoiceDesignSaver",
    "ElevenLabsVoiceGenerator",
    "GeminiImageGenerator",
    "GeminiVideoGenerator",
    "ImageGeneratorInput",
    "ImageGeneratorOutput",
    "OpenAIImageGenerator",
    "OpenAIVoiceGenerator",
    "OpenRouterImageGenerator",
    "OpenRouterVideoGenerator",
    "OpenRouterVoiceGenerator",
    "RunwayVideoGenerator",
    "SpeechToSpeechInput",
    "TextToSpeechInput",
    "VideoGenerated",
    "VideoGenerateInput",
    "VideoGenerateOutput",
    "VideoReferenceImage",
    "VoiceCloneInput",
    "VoiceDesignInput",
    "VoiceDesignOutput",
    "VoiceDesignPreview",
    "VoiceDesignSaveInput",
    "VoiceIdentityOutput",
    "VoiceOutput",
]
