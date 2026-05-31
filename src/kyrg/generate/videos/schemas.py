from pydantic import BaseModel, Field
from typing import Any, Optional

class VideoReferenceImage(BaseModel):
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
    model: str = Field(
        description='Provider-specific image generation model.',
        )
    prompt: str = Field(
        description="Natural-language prompt used to generate videos."
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description='Provider-specific optional generation parameters.',
    )
    image_path: Optional[str] = Field(
        default=None,
        description="Image path for generation",
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
    uri: str = Field(
        description = 'Temporary URL to download the video'
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
    videos: list[VideoGenerated] = Field(
        description="Generated videos."
        )
    provider: str =  Field(
        description="Provider that generated the videos."
        )
    model: str = Field(
        description="Model used for generation."
        )
    
    
    
    
