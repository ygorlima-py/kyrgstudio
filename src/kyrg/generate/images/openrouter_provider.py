"""OpenRouter image generation adapter.

OpenRouter exposes an OpenAI-compatible chat completions interface for models
that can return images. This adapter builds the chat payload expected by
OpenRouter, requests image output, and normalizes returned data URLs or base64
strings into raw image bytes.
"""

from typing import Any
from openai import OpenAI
import base64

from kyrg.generate.images.base import ImageGeneratorBase
from kyrg.generate.images.schemas import ImageGeneratorInput, ImageGeneratorOutput, GeneratedImage


class OpenRouterImageGenerator(ImageGeneratorBase):
    """Generate images through OpenRouter's OpenAI-compatible API."""

    URL = "https://openrouter.ai/api/v1"
    PROVIDER = "openrouter"
    
    def __init__(self, api_key: str, image_input: ImageGeneratorInput) -> None:
        """Initialize the OpenRouter image adapter.

        Args:
            api_key: OpenRouter API key used by the OpenAI-compatible client.
            image_input: Model, prompt, and optional OpenRouter settings.
        """

        self.client = OpenAI(api_key=api_key, base_url=self.URL)
        self.image_input = image_input
    
    def _build_payload(self) -> dict[str, Any]:
        """Build the OpenRouter chat completions payload for image output."""

        messages: list[dict] = []
            
        system_prompt = self.image_input.config.get('system_prompt')
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
            
        messages.append({
                    "role": "user",
                    "content": self.image_input.prompt
                    })

        args = {
           "model": self.image_input.model,
           "messages": messages,
            "extra_body": {
                "modalities": ["image"],
            }
        }

        return args
     
    def _request(self) -> Any:
        """Call OpenRouter and return the image fields needed for normalization.

        Returns:
            A small metadata dictionary containing provider images and model.

        Raises:
            RuntimeError: If the OpenRouter request fails.
        """
        
        args = self._build_payload()
        
        try:
            # Generate an image
            response = self.client.chat.completions.create(**args)
            message = response.choices[0].message

            return {
            "images": message.images or [],
            "model": response.model or self.image_input.model,
        }
    
        except Exception as error:
            raise RuntimeError(
                f"Error calling {self.PROVIDER} image provider: {error}"
            ) from error
      
        
    def _normalize_response(self, raw_result: Any) -> ImageGeneratorOutput:
        """Convert OpenRouter image data URLs or base64 strings into bytes."""
        
        try:
            images: list[GeneratedImage] = []
            for image in raw_result['images']:
                image_url_base64 = image['image_url']['url']
                
                if "," in image_url_base64:
                    header, encoded = image_url_base64.split(",", 1)
                    media_type = header.removeprefix("data:").removesuffix(";base64")
                else:
                    encoded = image_url_base64
                    media_type = "image/png" 
                
                images.append(GeneratedImage(
                    data=base64.b64decode(encoded),
                    media_type=media_type
                    ))
        
            return ImageGeneratorOutput(
                images=images,
                provider=self.PROVIDER,
                model=raw_result['model'],
            )
            
        except (KeyError, IndexError, ValueError, TypeError) as error:
            raise RuntimeError(
                f"Invalid image response from {self.PROVIDER}: {error}"
            ) from error
            
