"""Video frame extraction and image sequence operations backed by FFmpeg.

This module contains command builders for extracting still frames, generating
thumbnails, sampling frames over time, detecting scene-change frames, creating
video from image sequences, and exporting lightweight GIF previews.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import ImageSequenceContext, MediaContext
from kyrg.editor.runner import CommandRunner


class ExtractFrame(BaseEditor[MediaContext]):
    """Build an FFmpeg command that extracts a single frame from a video."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        timestamp: float = 0,
    ) -> None:
        """Initialize single-frame extraction options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            timestamp: Timestamp in seconds from which the frame is extracted.
        """

        super().__init__(context, runner)
        self.timestamp = timestamp

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for single-frame extraction."""

        return [
            "ffmpeg",
            "-y",
            "-ss",
            str(self.timestamp),
            "-i",
            self.context.input_path,
            "-frames:v",
            "1",
            self.context.output_path,
        ]


class GenerateThumbnail(BaseEditor[MediaContext]):
    """Build an FFmpeg command that generates a thumbnail image."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        timestamp: float = 1,
        width: int | None = None,
    ) -> None:
        """Initialize thumbnail generation options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            timestamp: Timestamp in seconds used as the thumbnail source.
            width: Optional output width. Height is calculated automatically.
        """

        super().__init__(context, runner)
        self.timestamp = timestamp
        self.width = width

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for thumbnail generation."""

        command = [
            "ffmpeg",
            "-y",
            "-ss",
            str(self.timestamp),
            "-i",
            self.context.input_path,
            "-frames:v",
            "1",
        ]

        if self.width is not None:
            command.extend(["-vf", f"scale={self.width}:-2"])

        command.append(self.context.output_path)
        return command


class ExtractFrames(BaseEditor[MediaContext]):
    """Build an FFmpeg command that samples frames at a fixed frame rate."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        fps: float = 1,
    ) -> None:
        """Initialize frame sampling options.

        Args:
            context: Input path and output image pattern used by FFmpeg.
            runner: Command runner responsible for executing the command.
            fps: Number of frames to extract per second.
        """

        super().__init__(context, runner)
        self.fps = fps

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for fixed-rate frame extraction."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"fps={self.fps}",
            self.context.output_path,
        ]


class ExtractSceneFrames(BaseEditor[MediaContext]):
    """Build an FFmpeg command that extracts frames at scene changes."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        threshold: float = 0.3,
    ) -> None:
        """Initialize scene-frame extraction options.

        Args:
            context: Input path and output image pattern used by FFmpeg.
            runner: Command runner responsible for executing the command.
            threshold: Scene change threshold used by FFmpeg's ``select`` filter.
        """

        super().__init__(context, runner)
        self.threshold = threshold

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for scene-change frame extraction."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"select='gt(scene,{self.threshold})',showinfo",
            "-vsync",
            "vfr",
            self.context.output_path,
        ]


class CreateVideoFromImages(BaseEditor[ImageSequenceContext]):
    """Build an FFmpeg command that creates a video from an image sequence."""

    def __init__(
        self,
        context: ImageSequenceContext,
        runner: CommandRunner,
        framerate: int = 30,
        video_codec: str = "libx264",
        pixel_format: str = "yuv420p",
    ) -> None:
        """Initialize image sequence encoding options.

        Args:
            context: Input image pattern and output path used by FFmpeg.
            runner: Command runner responsible for executing the command.
            framerate: Frame rate used to read the input sequence.
            video_codec: FFmpeg video codec used for the output stream.
            pixel_format: Output pixel format.
        """

        super().__init__(context, runner)
        self.framerate = framerate
        self.video_codec = video_codec
        self.pixel_format = pixel_format

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for image sequence encoding."""

        return [
            "ffmpeg",
            "-y",
            "-framerate",
            str(self.framerate),
            "-i",
            self.context.input_pattern,
            "-c:v",
            self.video_codec,
            "-pix_fmt",
            self.pixel_format,
            self.context.output_path,
        ]


class ConvertVideoToGif(BaseEditor[MediaContext]):
    """Build an FFmpeg command that converts a video into an animated GIF."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        fps: int = 12,
        width: int = 480,
    ) -> None:
        """Initialize GIF export options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            fps: GIF frame rate.
            width: Output GIF width. Height is calculated automatically.
        """

        super().__init__(context, runner)
        self.fps = fps
        self.width = width

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for GIF conversion."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"fps={self.fps},scale={self.width}:-1:flags=lanczos",
            self.context.output_path,
        ]
