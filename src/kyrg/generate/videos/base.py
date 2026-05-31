from abc import ABC, abstractmethod

from kyrg.adapters.base import APIAdapterBase
from kyrg.generate.videos.schemas import VideoGenerateOutput

class VideoGeneratorBase(APIAdapterBase[VideoGenerateOutput]):
    
    @abstractmethod
    def generate(self) -> VideoGenerateOutput:
        ...
    
    @abstractmethod
    async def agenerate(self) -> VideoGenerateOutput:
       ... 
        
    
    
    