from kyrg.generate.videos.base import VideoGeneratorBase
from kyrg.generate.videos.schemas import (
    VideoGenerateInput,
    VideoGenerateOutput,
    VideoGenerated
    )

from typing import Any

import time
import asyncio
import requests
import json
import httpx

class OpenRouterVideoGenerator(VideoGeneratorBase):
    URL = "https://openrouter.ai/api/v1/videos"
    PROVIDER = "openrouter"
    
    def __init__(self, api_key: str, video_input: VideoGenerateInput):
        self.api_key = api_key
        self.video_input = video_input
        
    def _request(self) -> dict[str, Any]:
        job = self._submit()
        return self._wait(job)

    async def _arequest(self) -> dict[str, Any]:
        
        async with httpx.AsyncClient() as client:
            job = await self._asubmit(client)
            return await self._await(job, client)

    def _submit(self) -> dict[str, Any]:
        # POST /videos
        try:
            job = requests.post(
                url=self.URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": self.video_input.model,
                    "prompt": self.video_input.prompt,
                })
                )
            job.raise_for_status()
            return job.json()
            
        except requests.HTTPError as error:
            raise RuntimeError(
                f"Submit failed {self.PROVIDER}: {error}"
            ) from error

        except requests.RequestException as error:
            raise RuntimeError(
                f"Connection error {self.PROVIDER}: {error}"
            ) from error

    def _poll_status(self, job: dict) -> dict[str, Any]:
        
        try:
            polling_url = job["polling_url"]
            poll_response = requests.get(
                    url=polling_url,
                    headers={
                    "Authorization": f"Bearer {self.api_key}",
                    }
                )
            
            poll_response.raise_for_status()
            return poll_response.json()
        
        except KeyError as error:
            raise RuntimeError(
                f"Missing polling_url {self.PROVIDER}: {job}"
            ) from error

        except requests.HTTPError as error:
            raise RuntimeError(
                f"Poll status failed {self.PROVIDER}: {error}"
            ) from error
            
        except requests.RequestException as error:
            raise RuntimeError(
                f"Connection error {self.PROVIDER}: {error}"
            ) from error
            
    def _wait(self, job: dict) -> dict:
        while True:
            status = self._poll_status(job)

            if status["status"] == "completed":
                return status

            if status["status"] == "failed":
                raise RuntimeError(status.get("error", "Video generation failed"))

            time.sleep(5)

    async def _asubmit(self, client: httpx.AsyncClient) -> dict:
        
        try:
            job = await client.post(
                    url=self.URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.video_input.model,
                        "prompt": self.video_input.prompt,
                    }
                )
            job.raise_for_status()
            return job.json()
        
        except requests.HTTPError as error:
            raise RuntimeError(
                f"Submit failed {self.PROVIDER}: {error}"
            ) from error

        except requests.RequestException as error:
            raise RuntimeError(
                f"Connection error {self.PROVIDER}: {error}"
            ) from error
        
    async def _apoll_status(self, job: dict, client: httpx.AsyncClient) -> dict:
        try:
            polling_url = job["polling_url"]
            poll_response = await client.get(
                    url=polling_url,
                    headers={
                    "Authorization": f"Bearer {self.api_key}",
                })
            return poll_response.json()
        
        except KeyError as error:
            raise RuntimeError(
                f"Missing polling_url {self.PROVIDER}: {job}"
            ) from error

        except requests.HTTPError as error:
            raise RuntimeError(
                f"Poll status failed {self.PROVIDER}: {error}"
            ) from error
            
        except requests.RequestException as error:
            raise RuntimeError(
                f"Connection error {self.PROVIDER}: {error}"
            ) from error

    async def _await(self, job: dict, client: httpx.AsyncClient) -> dict:
        while True:
            status = await self._apoll_status(job, client)

            if status["status"] == "completed":
                return status

            if status["status"] == "failed":
                raise RuntimeError(status.get("error", "Video generation failed"))

            await asyncio.sleep(5)
            
    def _normalize_response(self, raw_result: Any) -> VideoGenerateOutput:
        videos: list[VideoGenerated] = []
        for url in raw_result.get("unsigned_urls", []):
            videos.append(VideoGenerated(
                uri=url,
                requires_auth=False,
                media_type="video/mp4",
            ))
        
        return VideoGenerateOutput(
            videos=videos,
            provider=self.PROVIDER,
            model=self.video_input.model,
        )
    
    def generate(self) -> VideoGenerateOutput:
        return self.run()
    
    async def agenerate(self) -> VideoGenerateOutput:
        response = await self._arequest()
        return self._normalize_response(response)

if __name__ == "__main__":
    video_input = VideoGenerateInput(
        model='x-ai/grok-imagine-video',
        prompt='Gere um vídeo de uma pessoa esquiando',
        )
    
    generator = OpenRouterVideoGenerator(api_key='123456', video_input=video_input)
    # print(generator.generate())
    print(asyncio.run(generator.agenerate()))