"""Audio extraction and format conversion operations backed by FFmpeg.

This module contains command builders for converting media into audio-focused
representations. Operations in this module cover extracting audio from video,
encoding to common delivery formats, resampling, channel conversion, and
preparing audio for speech-to-text workflows.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner


class ExtractAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that extracts mono WAV audio from media input.

    The operation removes video streams and writes 16 kHz, 16-bit PCM mono
    audio. This format is commonly useful for speech processing and
    transcription pipelines.
    """

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for extracting audio."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            self.context.output_path,
        ]


class ConvertAudio(BaseEditor[MediaContext]):
    """Build a configurable FFmpeg command for general audio conversion.

    This operation exposes common encoding knobs while keeping the command
    structure consistent with the rest of the editor package. Optional
    parameters are only emitted when explicitly provided.
    """

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        codec: str = "aac",
        bitrate: str | None = None,
        sample_rate: int | None = None,
        channels: int | None = None,
    ) -> None:
        """Initialize generic audio conversion options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            codec: FFmpeg audio codec name used for the output stream.
            bitrate: Optional target audio bitrate, such as ``"192k"``.
            sample_rate: Optional output sample rate in hertz.
            channels: Optional number of output audio channels.
        """

        super().__init__(context, runner)
        self.codec = codec
        self.bitrate = bitrate
        self.sample_rate = sample_rate
        self.channels = channels

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for configurable audio conversion."""

        command = [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vn",
            "-c:a",
            self.codec,
        ]

        if self.bitrate:
            command.extend(["-b:a", self.bitrate])

        if self.sample_rate:
            command.extend(["-ar", str(self.sample_rate)])

        if self.channels:
            command.extend(["-ac", str(self.channels)])

        command.append(self.context.output_path)
        return command


class ConvertToWav(BaseEditor[MediaContext]):
    """Build an FFmpeg command that converts input media to PCM WAV audio."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        sample_rate: int = 44100,
        channels: int = 2,
    ) -> None:
        """Initialize WAV conversion options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            sample_rate: Output sample rate in hertz.
            channels: Number of output audio channels.
        """

        super().__init__(context, runner)
        self.sample_rate = sample_rate
        self.channels = channels

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for WAV conversion."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(self.sample_rate),
            "-ac",
            str(self.channels),
            self.context.output_path,
        ]


class ConvertToMp3(BaseEditor[MediaContext]):
    """Build an FFmpeg command that converts input media to MP3 audio."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        bitrate: str = "192k",
    ) -> None:
        """Initialize MP3 conversion options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            bitrate: Target MP3 bitrate, such as ``"128k"`` or ``"192k"``.
        """

        super().__init__(context, runner)
        self.bitrate = bitrate

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for MP3 conversion."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vn",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            self.bitrate,
            self.context.output_path,
        ]


class ConvertToAac(BaseEditor[MediaContext]):
    """Build an FFmpeg command that converts input media to AAC audio."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        bitrate: str = "192k",
    ) -> None:
        """Initialize AAC conversion options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            bitrate: Target AAC bitrate, such as ``"128k"`` or ``"192k"``.
        """

        super().__init__(context, runner)
        self.bitrate = bitrate

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for AAC conversion."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            self.bitrate,
            self.context.output_path,
        ]


class ConvertToWhisperFormat(BaseEditor[MediaContext]):
    """Build an FFmpeg command that prepares audio for Whisper-style models.

    The output is 16 kHz, 16-bit PCM mono WAV audio, a broadly compatible input
    format for local and remote speech-to-text systems.
    """

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for speech-to-text audio preparation."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            self.context.output_path,
        ]


class ResampleAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that changes the audio sample rate."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        sample_rate: int = 48000,
    ) -> None:
        """Initialize resampling options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            sample_rate: Output sample rate in hertz.
        """

        super().__init__(context, runner)
        self.sample_rate = sample_rate

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for audio resampling."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-ar",
            str(self.sample_rate),
            self.context.output_path,
        ]


class ChangeAudioChannels(BaseEditor[MediaContext]):
    """Build an FFmpeg command that changes the number of audio channels."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        channels: int = 1,
    ) -> None:
        """Initialize channel conversion options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            channels: Number of output channels, such as ``1`` for mono or
                ``2`` for stereo.
        """

        super().__init__(context, runner)
        self.channels = channels

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for channel conversion."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-ac",
            str(self.channels),
            self.context.output_path,
        ]
