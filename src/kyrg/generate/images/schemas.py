"""Input and output schemas for image generation.

These models define the stable contract used by image provider adapters.
Providers may return images as base64 strings, data URLs, raw bytes, or storage
references, but adapters normalize successful generations into raw image bytes.
"""

from pydantic import BaseModel, Field
from typing import Any

class ImageGeneratorInput(BaseModel):
    """Provider-agnostic input for an image generation request."""

    model: str = Field(description="Provider-specific image generation model.")
    prompt: str = Field(description="Natural-language prompt used to generate images.")
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific optional generation parameters.",
    )

class GeneratedImage(BaseModel):
    """A generated image normalized to bytes."""

    data: bytes = Field(description="Raw image bytes.")
    media_type: str = Field(description="Image MIME type, such as image/png.")

class ImageGeneratorOutput(BaseModel):
    """Normalized output returned by image generation adapters."""

    images: list[GeneratedImage] = Field(description="Generated images.")
    provider: str = Field(description="Provider that generated the images.")
    model: str = Field(description="Model used for generation.")
