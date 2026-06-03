"""Input and output schemas for video generation.

These Pydantic models define the public data contract shared by video provider
adapters. Inputs describe provider-agnostic generation requests, while outputs
normalize provider responses into stable remote video references.
"""

from pydantic import BaseModel, Field
from typing import Any, Optional

class VideoReferenceImage(BaseModel):
    """Reference image used to guide provider-specific video generation."""

    image_path: str = Field(
        description="Reference image path for video generation.",
    )
    image_mime_type: Optional[str] = Field(
        default=None,
        description="Reference image MIME type, such as image/png or image/jpeg.",
    )
    reference_type: str = Field(
        default="asset",
        description="Provider-specific reference image type.",
    )
    
class VideoGenerateInput(BaseModel):
    """Input payload for text-to-video and image-to-video generation."""

    model: str = Field(
        description='Provider-specific video generation model.',
        )
    prompt: str = Field(
        description="Natural-language prompt used to generate videos."
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description='Provider-specific optional generation parameters.',
    )
    image: Optional[str] = Field(
        default=None,
        description="Image for video generation. Accepts a local file path or a remote URL (http/https). Behavior depends on the provider.",
    )
    image_mime_type: Optional[str] = Field(
        default=None,
        description='Type of image, png or jpeg',
    )
    reference_images: list[VideoReferenceImage] = Field(
        default_factory=list,
        description="Reference images used to guide video generation.",
    )
    
class VideoGenerated(BaseModel):
    """Remote reference to a generated video asset."""

    uri: str = Field(
        description = 'Temporary URI or URL for the generated video.'
    )
    requires_auth: bool = Field(
        default=False,
        description="Whether downloading this URI requires provider authentication.",
    )
    media_type: str = Field(
        default="video/mp4",
        description="Video MIME type.",
    )
    
class VideoGenerateOutput(BaseModel):
    """Normalized output returned by video generation adapters."""

    videos: list[VideoGenerated] = Field(
        description="Generated videos."
        )
    provider: str =  Field(
        description="Provider that generated the videos."
        )
    model: str = Field(
        description="Model used for generation."
        )
    
    
    
    
