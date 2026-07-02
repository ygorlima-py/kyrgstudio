
"""Gemini image generation adapter.

This module implements image generation through the Google GenAI SDK. Gemini
may return generated images as raw bytes or as Google Cloud Storage references;
this adapter currently normalizes byte responses and rejects storage references
so Kyrg's image output remains a bytes-based contract.
"""

from typing import Any

from kyrg.generate.images.base import ImageGeneratorBase
from kyrg.generate.images.schemas import ImageGeneratorInput, ImageGeneratorOutput, GeneratedImage

from google import genai
from google.genai import types, errors

class GeminiImageGenerator(ImageGeneratorBase): 
    """Generate images with Google Gemini/Imagen models."""

    PROVIDER = 'google-gemini'
    def __init__(self, api_key: str, image_input: ImageGeneratorInput):
        """Initialize the Gemini image adapter.

        Args:
            api_key: Google GenAI API key used to authenticate the client.
            image_input: Model, prompt, and optional Gemini generation settings.
        """

        self.client = genai.Client(api_key=api_key)
        self.image_input = image_input
    
        
    def _request(self) -> types.GenerateImagesResponse:
        """Call Gemini's image generation endpoint.

        Common config keys include ``number_of_images``, ``image_size``,
        ``aspect_ratio``, and ``person_generation``.

        Returns:
            Raw Gemini image generation response.

        Raises:
            RuntimeError: If the Google GenAI SDK raises an APIError.
        """

        try:
            config = self.image_input.config
            response = self.client.models.generate_images(
                model=self.image_input.model,
                prompt=self.image_input.prompt,
                config=types.GenerateImagesConfig(**config),
            )
            
            return response
        except errors.APIError as error:
            raise RuntimeError(
                f'Error calling {self.PROVIDER} image provider: {error}'
            )

    async def _arequest(self) -> types.GenerateImagesResponse:
        """Call Gemini's image generation endpoint asynchronously."""

        try:
            config = self.image_input.config
            response = await self.client.aio.models.generate_images(
                model=self.image_input.model,
                prompt=self.image_input.prompt,
                config=types.GenerateImagesConfig(**config),
            )

            return response
        except errors.APIError as error:
            raise RuntimeError(
                f'Error calling {self.PROVIDER} image provider: {error}'
            )
        
    def _normalize_response(self, raw_result: Any) -> ImageGeneratorOutput:
        """Convert Gemini byte images into Kyrg's normalized image output."""

        images: list[GeneratedImage] = []
        
        for generated_image in raw_result.generated_images:
            image = generated_image.image
            
            if image.image_bytes:
                image_bytes = image.image_bytes
                
            elif image.gcs_uri:
                raise RuntimeError("Gemini returned gcs_uri instead of image bytes")
            
            else:
                raise RuntimeError("Gemini did not return image data")
            
            media_type = image.mime_type or "image/png"
            images.append(GeneratedImage(
                data=image_bytes,
                media_type=media_type,
            ))
            
        return ImageGeneratorOutput(
            images=images,
            provider=self.PROVIDER,
            model=self.image_input.model,
        )
        
if __name__ == "__main__":
    image_input = ImageGeneratorInput(
        model="imagen-4.0-generate-001",
        prompt="Faça uma imagem de um carro vermelho"
    )
    
    generator = GeminiImageGenerator(api_key='Fake API key', image_input=image_input)
    
    print(generator.run())
    
