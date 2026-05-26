"""Video conversion and encoding operations backed by FFmpeg.

This module contains command builders for changing codecs, containers, pixel
formats, bitrate targets, and delivery-oriented encoding settings. These
operations are intended for export, compatibility, compression, and web
delivery workflows.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner


class TranscodeVideo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that transcodes video and audio streams."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        video_codec: str = "libx264",
        audio_codec: str = "aac",
        crf: int = 23,
        preset: str = "medium",
        pixel_format: str = "yuv420p",
    ) -> None:
        """Initialize general transcoding options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            video_codec: FFmpeg video codec used for the output stream.
            audio_codec: FFmpeg audio codec used for the output stream.
            crf: Constant Rate Factor used by CRF-based encoders.
            preset: Encoder speed/compression preset.
            pixel_format: Output pixel format.
        """

        super().__init__(context, runner)
        self.video_codec = video_codec
        self.audio_codec = audio_codec
        self.crf = crf
        self.preset = preset
        self.pixel_format = pixel_format

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for video transcoding."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-c:v",
            self.video_codec,
            "-preset",
            self.preset,
            "-crf",
            str(self.crf),
            "-pix_fmt",
            self.pixel_format,
            "-c:a",
            self.audio_codec,
            self.context.output_path,
        ]


class ConvertToMp4(BaseEditor[MediaContext]):
    """Build an FFmpeg command that exports media as web-friendly MP4."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        crf: int = 23,
        preset: str = "medium",
    ) -> None:
        """Initialize MP4 export options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            crf: Constant Rate Factor for H.264 encoding.
            preset: H.264 encoder speed/compression preset.
        """

        super().__init__(context, runner)
        self.crf = crf
        self.preset = preset

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for MP4 conversion."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-c:v",
            "libx264",
            "-preset",
            self.preset,
            "-crf",
            str(self.crf),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            self.context.output_path,
        ]


class ChangeVideoContainer(BaseEditor[MediaContext]):
    """Build an FFmpeg command that remuxes streams into another container.

    Streams are copied without re-encoding. The output format is inferred from
    the output path extension.
    """

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for container remuxing."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-c",
            "copy",
            self.context.output_path,
        ]


class OptimizeVideoForWeb(BaseEditor[MediaContext]):
    """Build an FFmpeg command that moves MP4 metadata for faster web playback.

    The operation copies streams and applies ``+faststart`` so players can begin
    playback before the full file is downloaded.
    """

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for web playback optimization."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            self.context.output_path,
        ]


class CompressVideo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that compresses video for smaller output files."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        crf: int = 28,
        preset: str = "slow",
        audio_bitrate: str = "128k",
    ) -> None:
        """Initialize video compression options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            crf: Constant Rate Factor; higher values usually produce smaller
                files with lower quality.
            preset: H.264 encoder speed/compression preset.
            audio_bitrate: Target audio bitrate.
        """

        super().__init__(context, runner)
        self.crf = crf
        self.preset = preset
        self.audio_bitrate = audio_bitrate

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for video compression."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-c:v",
            "libx264",
            "-preset",
            self.preset,
            "-crf",
            str(self.crf),
            "-c:a",
            "aac",
            "-b:a",
            self.audio_bitrate,
            "-movflags",
            "+faststart",
            self.context.output_path,
        ]


class SetVideoBitrate(BaseEditor[MediaContext]):
    """Build an FFmpeg command that encodes media with explicit bitrates."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        video_bitrate: str = "2500k",
        audio_bitrate: str = "128k",
    ) -> None:
        """Initialize bitrate encoding options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            video_bitrate: Target video bitrate, such as ``"2500k"``.
            audio_bitrate: Target audio bitrate, such as ``"128k"``.
        """

        super().__init__(context, runner)
        self.video_bitrate = video_bitrate
        self.audio_bitrate = audio_bitrate

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for explicit bitrate encoding."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-b:v",
            self.video_bitrate,
            "-b:a",
            self.audio_bitrate,
            self.context.output_path,
        ]


class SetPixelFormat(BaseEditor[MediaContext]):
    """Build an FFmpeg command that changes the output pixel format."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        pixel_format: str = "yuv420p",
    ) -> None:
        """Initialize pixel format conversion options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            pixel_format: Output pixel format, such as ``"yuv420p"``.
        """

        super().__init__(context, runner)
        self.pixel_format = pixel_format

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for pixel format conversion."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-pix_fmt",
            self.pixel_format,
            self.context.output_path,
        ]
