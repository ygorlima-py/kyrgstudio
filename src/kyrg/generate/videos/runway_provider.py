"""Runway video generation adapter.

This module implements video generation through the Runway SDK. The adapter
supports text-to-video and image-to-video requests, waits for Runway tasks to
complete, and normalizes returned asset URLs into Kyrg's
``VideoGenerateOutput`` schema.
"""

from typing import Any

from kyrg.generate.videos.base import VideoGeneratorBase
from kyrg.generate.videos.schemas import (
    VideoGenerateInput,
    VideoGenerateOutput,
    VideoGenerated
    )

from runwayml import RunwayML, TaskFailedError, AsyncRunwayML
from pathlib import Path
import base64

class RunwayVideoGenerator(VideoGeneratorBase):
    """Generate videos with Runway models.

    Runway exposes generation as task-based operations. This adapter builds the
    provider payload from Kyrg's generic video input, resolves optional image
    prompts into Runway-compatible values, and returns normalized remote video
    references without downloading generated assets.
    """

    PROVIDER = 'runway'

    def __init__(self, api_key: str, video_input: VideoGenerateInput) -> None:
        """Initialize the Runway video adapter.

        Args:
            api_key: Runway API key used to authenticate SDK clients.
            video_input: Model, prompt, optional image, and provider settings.
        """

        self.client = RunwayML(api_key=api_key)
        self.async_client = AsyncRunwayML(api_key=api_key)
        self.video_input = video_input
        
    def _resolve_image(self, image: str) -> str:
        """Return a Runway-compatible image prompt value.

        Remote HTTP(S) images are passed through unchanged. Local files are
        read and encoded as data URIs so they can be sent directly in the
        Runway request payload.
        """

        if image.startswith(("http://", "https://")):
            return image

        path = Path(image)
        
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {image}")
        
        mime = self.video_input.image_mime_type or f"image/{path.suffix.lstrip('.')}"
        
        try:
            b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
            return f"data:{mime};base64,{b64}"
        except OSError as error:
            raise RuntimeError(f"Could not read image file: {image}") from error
        
    def _request(self) -> Any:
        """Create a synchronous Runway task and wait for task output."""

        payload: dict[str, Any] = {
            "model": self.video_input.model,
            "prompt_text": self.video_input.prompt,
            **self.video_input.config,
        }
          
        if self.video_input.image:
            payload["prompt_image"] = self._resolve_image(self.video_input.image)
            
        try:
            if self.video_input.image:
                task = self.client.image_to_video.create(**payload)
            else:
                task = self.client.text_to_video.create(**payload)

            return task.wait_for_task_output()
            
        except TaskFailedError as error:
            raise RuntimeError(
                f"Error generating video with {self.PROVIDER}: {error.task_details}"
            ) from error
            
        except Exception as error:
            raise RuntimeError(
                f"Error calling {self.PROVIDER} video provider: {error}"
            ) from error
        
    async def _arequest(self):
        """Create an asynchronous Runway task and wait for task output."""

        payload: dict[str, Any] = {
            "model": self.video_input.model,
            "prompt_text": self.video_input.prompt,
            **self.video_input.config,
        }
        
        if self.video_input.image:
            payload["prompt_image"] = self._resolve_image(self.video_input.image)

        try:
            if self.video_input.image:
                task = await self.async_client.image_to_video.create(**payload)
            else:
                task = await self.async_client.text_to_image.create(**payload)
                
            return await task.wait_for_task_output()
        
        except TaskFailedError as error:
            raise RuntimeError(
                f"Error generating video with {self.PROVIDER}: {error.task_details}"
            ) from error
            
        except Exception as error:
            raise RuntimeError(
                f"Error calling {self.PROVIDER} video provider: {error}"
            ) from error
            
    def _normalize_response(self, raw_result: Any) -> VideoGenerateOutput:
        """Convert Runway task output URLs into Kyrg's video output schema."""

        output = getattr(raw_result, "output", None)
        
        if not output:
            raise RuntimeError(f"{self.PROVIDER} did not return video output URLs")

        videos: list[VideoGenerated] = []
        
        for url in output:
            videos.append(
                VideoGenerated(
                    uri=url,
                    requires_auth=False,
                    media_type="video/mp4",
                )
            )

        return VideoGenerateOutput(
            videos=videos,
            provider=self.PROVIDER,
            model=self.video_input.model,
    )
        
    def generate(self) -> VideoGenerateOutput:
        """Generate videos synchronously and return normalized video URLs."""

        return self.run()
    
    async def agenerate(self) -> VideoGenerateOutput:
        """Generate videos asynchronously and return normalized video URLs."""

        raw_result = await self._arequest()
        return  self._normalize_response(raw_result=raw_result)
    
    
if __name__ == "__main__":
    video_input = VideoGenerateInput(
        model='gen4.5', 
        prompt='A serene mountain landscape at sunrise with mist rolling through the valleys',
        config={
            'ratio': '1280:720',
            'duration': 5,
        }
        )
    
    generator = RunwayVideoGenerator(api_key='fakeapikey', video_input=video_input)
    print(generator.generate())
