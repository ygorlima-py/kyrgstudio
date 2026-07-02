"""ElevenLabs voice identity adapters.

This module contains ElevenLabs actions that create or register voices rather
than generating final audio directly. Clone creates a permanent voice from
sample files, while design preview/save supports the two-step ElevenLabs
text-to-voice workflow: generate previews first, then save the chosen preview
as a permanent voice.
"""

import base64
import os
from typing import Any, BinaryIO, cast

from elevenlabs import ElevenLabs, AsyncElevenLabs
from elevenlabs.core import File
from elevenlabs.core.api_error import ApiError

from kyrg.adapters.base import APIAdapterSDKBase
from kyrg.generate.voices.schemas import (
    VoiceCloneInput,
    VoiceDesignInput,
    VoiceIdentityOutput,
    VoiceDesignOutput,
    VoiceDesignPreview,
    VoiceDesignSaveInput
)
 
 
class ElevenLabsVoiceCloner(APIAdapterSDKBase[VoiceIdentityOutput, ElevenLabs]):
    """Create a permanent ElevenLabs voice from audio samples.

    The adapter opens each path from ``clone_input.audio_paths``, sends those
    files to ElevenLabs instant voice cloning, and normalizes the created voice
    metadata into VoiceIdentityOutput.

    Provider-specific options can be passed through ``clone_input.settings``.
    Supported settings currently include ``remove_background_noise``.
    """

    PROVIDER = "elevenlabs"
    
    def __init__(self, api_key: str, clone_input: VoiceCloneInput):
        """Initialize the ElevenLabs voice cloning adapter.

        Args:
            api_key: ElevenLabs API key used to authenticate the SDK client.
            clone_input: Voice name, sample audio paths, labels, and settings.
        """

        client = ElevenLabs(api_key=api_key)
        super().__init__(client)
        self.async_client = AsyncElevenLabs(api_key=api_key)
        self.clone_input = clone_input
 
    def _open_audio_files(self) -> list[BinaryIO]:
        """Open all clone sample files in binary mode.

        The caller is responsible for closing the returned files.
        """

        return [open(path, "rb") for path in self.clone_input.audio_paths]
 
    def _request(self) -> dict[str, Any]:
        """Call ElevenLabs instant voice cloning.

        Returns:
            Raw adapter metadata used later to build VoiceIdentityOutput.

        Raises:
            RuntimeError: If the ElevenLabs SDK returns an ApiError.
        """

        audio_files: list[BinaryIO] = []
 
        try:
            audio_files = self._open_audio_files()
            remove_background_noise = self.clone_input.settings.get("remove_background_noise", True)
 
            response = self.client.voices.ivc.create(
                name=self.clone_input.name,
                files=cast(list[File], audio_files),
                description=self.clone_input.description,
                labels=self.clone_input.labels,
                remove_background_noise=remove_background_noise,
            )
 
            return {
                "voice_id": response.voice_id,
                "name": self.clone_input.name,
                "description": self.clone_input.description,
                "raw_response": response.model_dump() if hasattr(response, "model_dump") else {},
            }
 
        except ApiError as error:
            raise RuntimeError(f"Error calling ElevenLabs voice-cloner: {error}")
 
        finally:
            for f in audio_files:
                f.close()

    async def _arequest(self) -> dict[str, Any]:
        """Call ElevenLabs instant voice cloning asynchronously."""

        audio_files: list[BinaryIO] = []

        try:
            audio_files = self._open_audio_files()
            remove_background_noise = self.clone_input.settings.get("remove_background_noise", True)

            response = await self.async_client.voices.ivc.create(
                name=self.clone_input.name,
                files=cast(list[File], audio_files),
                description=self.clone_input.description,
                labels=self.clone_input.labels,
                remove_background_noise=remove_background_noise,
            )

            return {
                "voice_id": response.voice_id,
                "name": self.clone_input.name,
                "description": self.clone_input.description,
                "raw_response": response.model_dump() if hasattr(response, "model_dump") else {},
            }

        except ApiError as error:
            raise RuntimeError(f"Error calling ElevenLabs voice-cloner: {error}")

        finally:
            for f in audio_files:
                f.close()
 
    def _normalize_response(self, raw_result: dict[str, Any]) -> VoiceIdentityOutput:
        """Convert provider metadata into the public VoiceIdentityOutput schema."""

        return VoiceIdentityOutput(
            provider=self.PROVIDER,
            voice_id=raw_result["voice_id"],
            name=raw_result.get("name"),
            description=raw_result.get("description"),
            raw_response=raw_result.get("raw_response", {}),
        )
 
 
class ElevenLabsVoiceDesignPreview(APIAdapterSDKBase[VoiceDesignOutput, ElevenLabs]):
    """Generate temporary voice design previews from a text description.

    ElevenLabs text-to-voice design returns preview voices, not a final saved
    voice. This adapter saves the preview audio files into
    ``design_input.output_dir`` and returns their generated voice ids so the
    caller can listen, choose one, and save it with ElevenLabsVoiceDesignSaver.

    Provider-specific options can be passed through ``design_input.settings``.
    Supported settings currently include ``output_format``, ``model_id``,
    ``auto_generate_text``, ``loudness``, ``seed``, ``guidance_scale``,
    ``stream_previews``, ``should_enhance``, and ``quality``.
    """

    PROVIDER = "elevenlabs"

    def __init__(self, api_key: str, design_input: VoiceDesignInput):
        """Initialize the ElevenLabs voice design preview adapter.

        Args:
            api_key: ElevenLabs API key used to authenticate the SDK client.
            design_input: Voice description, output directory, text, and settings.
        """

        client = ElevenLabs(api_key=api_key)
        super().__init__(client)
        self.async_client = AsyncElevenLabs(api_key=api_key)
        self.design_input = design_input

    def _build_request_kwargs(self) -> dict[str, Any]:
        """Build the keyword arguments accepted by text-to-voice design."""

        kwargs: dict[str, Any] = {
            "voice_description": self.design_input.description,
        }

        if self.design_input.text is not None:
            kwargs["text"] = self.design_input.text

        for setting in (
            "output_format",
            "model_id",
            "auto_generate_text",
            "loudness",
            "seed",
            "guidance_scale",
            "stream_previews",
            "should_enhance",
            "quality",
        ):
            if setting in self.design_input.settings:
                kwargs[setting] = self.design_input.settings[setting]

        return kwargs

    def _extension_from_media_type(self, media_type: str | None) -> str:
        """Return a file extension for an ElevenLabs preview media type."""

        if media_type == "audio/mpeg":
            return "mp3"

        if media_type == "audio/wav":
            return "wav"

        return "mp3"

    def _save_previews(self, previews: list[Any]) -> list[dict[str, Any]]:
        """Decode and persist all preview audio files.

        Returns:
            A list of preview metadata dictionaries ready for VoiceDesignPreview.
        """

        os.makedirs(self.design_input.output_dir, exist_ok=True)

        saved_previews: list[dict[str, Any]] = []

        for index, preview in enumerate(previews):
            extension = self._extension_from_media_type(preview.media_type)
            audio_path = os.path.join(
                self.design_input.output_dir,
                f"voice_preview_{index}.{extension}",
            )

            audio_bytes = base64.b64decode(preview.audio_base_64)

            with open(audio_path, "wb") as audio_file:
                audio_file.write(audio_bytes)

            saved_previews.append(
                {
                    "generated_voice_id": preview.generated_voice_id,
                    "audio_path": audio_path,
                    "media_type": preview.media_type,
                    "duration_secs": preview.duration_secs,
                    "language": preview.language,
                }
            )

        return saved_previews

    def _request(self) -> dict[str, Any]:
        """Call ElevenLabs text-to-voice design and save preview files.

        Returns:
            Raw adapter metadata used later to build VoiceDesignOutput.

        Raises:
            RuntimeError: If the ElevenLabs SDK returns an ApiError.
        """

        try:
            response = self.client.text_to_voice.design(
                **self._build_request_kwargs()
            )

            raw_response = (
                response.model_dump()
                if hasattr(response, "model_dump")
                else {}
            )

            return {
                "text": response.text,
                "previews": self._save_previews(response.previews),
                "raw_response": raw_response,
            }

        except ApiError as error:
            raise RuntimeError(
                f"Error calling ElevenLabs voice design previews: {error}"
            ) from error

    async def _arequest(self) -> dict[str, Any]:
        """Call ElevenLabs text-to-voice design asynchronously."""

        try:
            response = await self.async_client.text_to_voice.design(
                **self._build_request_kwargs()
            )

            raw_response = (
                response.model_dump()
                if hasattr(response, "model_dump")
                else {}
            )

            return {
                "text": response.text,
                "previews": self._save_previews(response.previews),
                "raw_response": raw_response,
            }

        except ApiError as error:
            raise RuntimeError(
                f"Error calling ElevenLabs voice design previews: {error}"
            ) from error

    def _normalize_response(self, raw_result: dict[str, Any]) -> VoiceDesignOutput:
        """Convert provider metadata into the public VoiceDesignOutput schema."""

        previews = [
            VoiceDesignPreview(**preview)
            for preview in raw_result.get("previews", [])
        ]
        return VoiceDesignOutput(
            provider=self.PROVIDER,
            text=raw_result.get("text"),
            previews=previews,
            raw_response=raw_result.get("raw_response", raw_result),
        )
    
class ElevenLabsVoiceDesignSaver(APIAdapterSDKBase[VoiceIdentityOutput, ElevenLabs]): 
    """Save a selected voice design preview as a permanent ElevenLabs voice.

    The adapter receives a generated voice id from ElevenLabsVoiceDesignPreview
    and calls ElevenLabs text-to-voice create to register the selected preview
    as a reusable voice. The resulting permanent voice id is returned as
    VoiceIdentityOutput.
    """

    PROVIDER = "elevenlabs"

    def __init__(self, api_key: str, save_input: VoiceDesignSaveInput):
        """Initialize the ElevenLabs voice design save adapter.

        Args:
            api_key: ElevenLabs API key used to authenticate the SDK client.
            save_input: Selected preview id, final voice name, description, and labels.
        """

        client = ElevenLabs(api_key=api_key)
        super().__init__(client)
        self.async_client = AsyncElevenLabs(api_key=api_key)
        self.save_input = save_input

    def _request(self) -> dict[str, Any]:
        """Call ElevenLabs to save the selected generated voice.

        Returns:
            Raw adapter metadata used later to build VoiceIdentityOutput.

        Raises:
            RuntimeError: If the ElevenLabs SDK returns an ApiError.
        """

        try:
            response = self.client.text_to_voice.create(
                voice_name=self.save_input.name,
                voice_description=self.save_input.description,
                generated_voice_id=self.save_input.generated_voice_id,
                labels=self.save_input.labels,
            )

            return {
                "voice_id": response.voice_id,
                "name": self.save_input.name,
                "description": self.save_input.description,
                "raw_response": response.model_dump(),
            }
            
        except ApiError as error:
            raise RuntimeError(
                f"Error calling ElevenLabs voice design saver: {error}"
            ) from error

    async def _arequest(self) -> dict[str, Any]:
        """Call ElevenLabs asynchronously to save the selected generated voice."""

        try:
            response = await self.async_client.text_to_voice.create(
                voice_name=self.save_input.name,
                voice_description=self.save_input.description,
                generated_voice_id=self.save_input.generated_voice_id,
                labels=self.save_input.labels,
            )

            return {
                "voice_id": response.voice_id,
                "name": self.save_input.name,
                "description": self.save_input.description,
                "raw_response": response.model_dump(),
            }

        except ApiError as error:
            raise RuntimeError(
                f"Error calling ElevenLabs voice design saver: {error}"
            ) from error

    def _normalize_response(self, raw_result: dict[str, Any]) -> VoiceIdentityOutput:
        """Convert provider metadata into the public VoiceIdentityOutput schema."""

        return VoiceIdentityOutput(
            provider=self.PROVIDER,
            voice_id=raw_result["voice_id"],
            name=raw_result.get("name"),
            description=raw_result.get("description"),
            raw_response=raw_result.get("raw_response", raw_result),
        )
