from typing import Any
from google import genai
from google.genai import types, errors

import asyncio
import time

from kyrg.generate.videos.base import VideoGeneratorBase
from kyrg.generate.videos.schemas import (
    VideoGenerateInput,
    VideoGenerateOutput,
    VideoGenerated
    )

class GeminiVideoGenerator(VideoGeneratorBase):
    PROVIDER = 'google-gemini'
    
    def __init__(self, api_key: str, video_input: VideoGenerateInput) -> None:
        self.client = genai.Client(api_key=api_key)
        self.video_input = video_input
    
    def build_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
           'model': self.video_input.model,
           'prompt': self.video_input.prompt,
        }
        
        if self.video_input.config:
            try:
                payload['config'] = types.GenerateVideosConfig(**self.video_input.config)
            except TypeError as error:
                 raise ValueError(
                    f"Invalid config parameter for GenerateVideosConfig: {error}"
                ) from error
        
        if self.video_input.image_path and self.video_input.config.get("reference_images"):
            raise ValueError(
            "Use either image_path or config.reference_images, not both"
            )

        if self.video_input.image_path:
            try:
                payload['image'] = types.Image.from_file(
                    location=self.video_input.image_path,
                    mime_type=self.video_input.image_mime_type,
                )
                
            except FileNotFoundError as error:
                raise FileNotFoundError(
                    f"Image file not found: {self.video_input.image_path}"
                ) from error

            except TypeError as error:
                raise ValueError(
                    f"Invalid Gemini video image input: {error}"
                ) from error

            except OSError as error:
                raise RuntimeError(
                    f"Could not read image file: {self.video_input.image_path}"
                ) from error
                            
        return payload
        
    def _request(self) -> Any:
        payload = self.build_payload()
        
        try: 
            operation = self.client.models.generate_videos(**payload)
            
        except errors.APIError as error:
            raise RuntimeError(
                f'Error calling {self.PROVIDER} video provider: {error}'
            )
            
        while not operation.done:
            time.sleep(10)
            
            try:
                operation = self.client.operations.get(operation)
                
            except errors.APIError as error:
                raise RuntimeError(
                    f'Error calling {self.PROVIDER} video worker: {error}'
                ) from error
                
        return operation
    
    async def _arequest(self) -> Any:
        payload = self.build_payload()

        try:
            operation = await self.client.aio.models.generate_videos(**payload)
        except errors.APIError as error:
            raise RuntimeError(
                f"Error calling {self.PROVIDER} video provider: {error}"
            ) from error
            
        while not operation.done:
            await asyncio.sleep(10)

            try:
                operation = await self.client.aio.operations.get(operation)
            except errors.APIError as error:
                raise RuntimeError(
                    f"Error calling {self.PROVIDER} video worker: {error}"
                ) from error

        return operation
            
    def _normalize_response(self, raw_result: Any) -> VideoGenerateOutput:
        videos: list[VideoGenerated] = []
        for generated_video in raw_result.response.generated_videos:
            video = generated_video.video
            
            if video is None or not video.uri:
                raise  RuntimeError(f"{self.PROVIDER} did not return a video URI")
            
            videos.append(
            VideoGenerated(
                uri=video.uri,
                requires_auth=True,
                media_type=video.mime_type or "video/mp4",
            )
        )
        
        return VideoGenerateOutput(
            videos=videos,
            provider=self.PROVIDER,
            model=self.video_input.model, 
        )

    def generate(self) -> VideoGenerateOutput:
        return self.run()
    
    async def agenerate(self) -> VideoGenerateOutput:
        operation = await self._arequest()
        return self._normalize_response(operation)
    
if __name__ == '__main__':
    video_input = VideoGenerateInput(
        model='veo-3.1-generate-preview',
        prompt='rack the butterfly into the garden as it lands on an orange origami flower. A fluffy white puppy runs up and gently pats the flower.',
        
        )
    
    generator = GeminiVideoGenerator(api_key='Fake api key', video_input=video_input)
    
    # print(generator.generate())
    print(asyncio.run(generator.agenerate()))