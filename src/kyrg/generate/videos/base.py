"""Base contracts for video generation adapters.

Video providers share the same public generation contract while keeping
provider-specific request, polling, and response parsing inside concrete
adapters. Implementations normalize successful generations into
``VideoGenerateOutput`` so callers can consume one stable schema across
providers.
"""

from abc import ABC, abstractmethod

from kyrg.adapters.base import APIAdapterBase
from kyrg.generate.videos.schemas import VideoGenerateOutput

class VideoGeneratorBase(APIAdapterBase[VideoGenerateOutput]):
    """Abstract base class for API-backed video generation providers.

    Concrete providers implement synchronous and asynchronous public entry
    points, usually by delegating to ``APIAdapterBase.run`` or the provider's
    async request flow. Provider-specific adapters are responsible for turning
    remote task results into Kyrg's normalized video output schema.
    """
    
    @abstractmethod
    def generate(self) -> VideoGenerateOutput:
        """Generate videos synchronously.

        Returns:
            A normalized video generation result containing remote video
            references and provider metadata.
        """

        ...
    
    @abstractmethod
    async def agenerate(self) -> VideoGenerateOutput:
        """Generate videos asynchronously.

        Returns:
            A normalized video generation result containing remote video
            references and provider metadata.
        """

        ... 
        
    
    
    
