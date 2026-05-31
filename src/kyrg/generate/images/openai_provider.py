"""OpenAI image generation adapter.

This module implements image generation through OpenAI's Images API. The
adapter sends Kyrg's provider-agnostic image input to OpenAI and normalizes the
returned image payload into ``GeneratedImage`` objects containing bytes.
"""

from typing import Any
from openai import OpenAI, APIError
import base64

from kyrg.generate.images.base import ImageGeneratorBase
from kyrg.generate.images.schemas import ImageGeneratorInput, ImageGeneratorOutput, GeneratedImage


class OpenAIImageGenerator(ImageGeneratorBase): 
    """Generate images with OpenAI's native Images API."""

    URL = "https://api.openai.com/v1"
    PROVIDER = "openai"
    
    def __init__(self, api_key: str, image_input: ImageGeneratorInput) -> None:
        """Initialize the OpenAI image adapter.

        Args:
            api_key: OpenAI API key used to authenticate the SDK client.
            image_input: Model, prompt, and optional OpenAI generation settings.
        """

        self.client = OpenAI(api_key=api_key, base_url=self.URL)
        self.image_input = image_input
    
    def _request(self) -> Any:
        """Call OpenAI's image generation endpoint.

        Returns:
            Raw OpenAI image generation response.

        Raises:
            RuntimeError: If the OpenAI SDK raises an APIError.
        """

        try:
            response = self.client.images.generate(
                    model=self.image_input.model,
                    prompt=self.image_input.prompt,
                    **self.image_input.config,
                    )   
            return response
        
        except APIError as error:
            raise RuntimeError(
                f"Error calling {self.PROVIDER} image provider: {error}"
            ) from error
    
    def _normalize_response(self, raw_result: Any) -> ImageGeneratorOutput:
        """Convert OpenAI's response into Kyrg's normalized image output."""
        
        images: list[GeneratedImage] = []
        for image_base64 in raw_result.data:
            image_bytes = base64.b64decode(image_base64)
        
            images.append(GeneratedImage(
                data=image_bytes,
                media_type="image/png",
            ))
        
        return ImageGeneratorOutput(
            images=images,
            provider=self.PROVIDER,
            model=self.image_input.model,
        )
        
if __name__ == '__main__':
    image_input = ImageGeneratorInput(
        model="gpt-image-2",
        prompt="Faça uma imagem de um carro vermelho"
    )
    
    generator = OpenAIImageGenerator(api_key='Fake key', image_input=image_input)
    print(generator.run())
