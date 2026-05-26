"""Video cutting and segment extraction operations backed by FFmpeg.

This module contains command builders for trimming and extracting sections of
video files. It separates fast stream-copy cuts from more accurate re-encoded
cuts so callers can choose between speed and frame-level precision.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner


class TrimVideo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that trims video with optional stream copy.

    When ``copy_streams`` is enabled, FFmpeg avoids re-encoding and performs a
    fast cut near stream boundaries. This is efficient but may be less precise
    than a re-encoded trim.
    """

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        start_time: float = 0,
        end_time: float | None = None,
        duration: float | None = None,
        copy_streams: bool = True,
    ) -> None:
        """Initialize video trim options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            start_time: Start time in seconds.
            end_time: Optional end time in seconds.
            duration: Optional output duration in seconds.
            copy_streams: Whether to copy streams instead of re-encoding.
        """

        super().__init__(context, runner)
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration
        self.copy_streams = copy_streams

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for fast or copy-based trimming."""

        command = [
            "ffmpeg",
            "-y",
            "-ss",
            str(self.start_time),
            "-i",
            self.context.input_path,
        ]

        if self.end_time is not None:
            command.extend(["-to", str(self.end_time)])

        if self.duration is not None:
            command.extend(["-t", str(self.duration)])

        if self.copy_streams:
            command.extend(["-c", "copy"])

        command.append(self.context.output_path)
        return command


class TrimVideoAccurate(BaseEditor[MediaContext]):
    """Build an FFmpeg command that trims video with re-encoding.

    This operation places the seek after the input and re-encodes the output,
    favoring more accurate trimming at the cost of additional processing time.
    """

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        start_time: float = 0,
        end_time: float | None = None,
        duration: float | None = None,
        video_codec: str = "libx264",
        audio_codec: str = "aac",
    ) -> None:
        """Initialize accurate trim options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            start_time: Start time in seconds.
            end_time: Optional end time in seconds.
            duration: Optional output duration in seconds.
            video_codec: Video codec used for re-encoding.
            audio_codec: Audio codec used for re-encoding.
        """

        super().__init__(context, runner)
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration
        self.video_codec = video_codec
        self.audio_codec = audio_codec

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for accurate re-encoded trimming."""

        command = [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-ss",
            str(self.start_time),
        ]

        if self.end_time is not None:
            command.extend(["-to", str(self.end_time)])

        if self.duration is not None:
            command.extend(["-t", str(self.duration)])

        command.extend(
            [
                "-c:v",
                self.video_codec,
                "-c:a",
                self.audio_codec,
                self.context.output_path,
            ]
        )
        return command


class SplitVideoSegment(BaseEditor[MediaContext]):
    """Build an FFmpeg command that extracts a fixed-duration video segment."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        start_time: float,
        duration: float,
    ) -> None:
        """Initialize segment extraction options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            start_time: Segment start time in seconds.
            duration: Segment duration in seconds.
        """

        super().__init__(context, runner)
        self.start_time = start_time
        self.duration = duration

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for fixed-duration segment extraction."""

        return [
            "ffmpeg",
            "-y",
            "-ss",
            str(self.start_time),
            "-i",
            self.context.input_path,
            "-t",
            str(self.duration),
            "-c",
            "copy",
            self.context.output_path,
        ]
