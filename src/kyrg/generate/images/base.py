"""Base classes for image generation adapters.

Image adapters follow the generic API adapter lifecycle: perform a provider
request, then normalize the provider response into ``ImageGeneratorOutput``.
"""

from kyrg.adapters.base import APIAdapterBase
from kyrg.generate.images.schemas import ImageGeneratorOutput

class ImageGeneratorBase(APIAdapterBase[ImageGeneratorOutput]):
    """Base contract for image generation providers."""
    
    def generate(self) -> ImageGeneratorOutput:
        """Generate images and return Kyrg's normalized output schema."""

        return self.run()
