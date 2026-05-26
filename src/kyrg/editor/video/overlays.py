"""Video overlay and visual layer operations backed by FFmpeg.

This module contains command builders for placing text, watermarks, images, and
picture-in-picture layers on top of a base video. Overlay operations generally
use FFmpeg filter graphs and preserve the base video's audio stream when
available.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext, VideoOverlayContext
from kyrg.editor.runner import CommandRunner


class AddTextOverlay(BaseEditor[MediaContext]):
    """Build an FFmpeg command that draws text over a video."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        text: str,
        x: str = "(w-text_w)/2",
        y: str = "(h-text_h)/2",
        font_size: int = 48,
        font_color: str = "white",
        box: bool = False,
        box_color: str = "black@0.5",
    ) -> None:
        """Initialize text overlay options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            text: Text content rendered by FFmpeg's ``drawtext`` filter.
            x: Horizontal text position or FFmpeg expression.
            y: Vertical text position or FFmpeg expression.
            font_size: Text font size.
            font_color: Text color.
            box: Whether to render a background box behind the text.
            box_color: Background box color when ``box`` is enabled.
        """

        super().__init__(context, runner)
        self.text = text
        self.x = x
        self.y = y
        self.font_size = font_size
        self.font_color = font_color
        self.box = box
        self.box_color = box_color

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for adding a text overlay."""

        filter_value = (
            f"drawtext=text='{self.text}':"
            f"x={self.x}:"
            f"y={self.y}:"
            f"fontsize={self.font_size}:"
            f"fontcolor={self.font_color}"
        )

        if self.box:
            filter_value = f"{filter_value}:box=1:boxcolor={self.box_color}"

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            filter_value,
            "-c:a",
            "copy",
            self.context.output_path,
        ]


class AddWatermark(BaseEditor[VideoOverlayContext]):
    """Build an FFmpeg command that overlays a watermark on a base video."""

    def __init__(
        self,
        context: VideoOverlayContext,
        runner: CommandRunner,
        x: str = "main_w-overlay_w-20",
        y: str = "main_h-overlay_h-20",
    ) -> None:
        """Initialize watermark placement options.

        Args:
            context: Base video, overlay asset, and output paths.
            runner: Command runner responsible for executing the command.
            x: Horizontal overlay position or FFmpeg expression.
            y: Vertical overlay position or FFmpeg expression.
        """

        super().__init__(context, runner)
        self.x = x
        self.y = y

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for adding a watermark."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.video_path,
            "-i",
            self.context.overlay_path,
            "-filter_complex",
            f"[0:v][1:v]overlay={self.x}:{self.y}[v]",
            "-map",
            "[v]",
            "-map",
            "0:a?",
            "-c:a",
            "copy",
            self.context.output_path,
        ]


class OverlayImage(BaseEditor[VideoOverlayContext]):
    """Build an FFmpeg command that places an image over a video."""

    def __init__(
        self,
        context: VideoOverlayContext,
        runner: CommandRunner,
        x: str = "0",
        y: str = "0",
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Initialize image overlay options.

        Args:
            context: Base video, overlay image, and output paths.
            runner: Command runner responsible for executing the command.
            x: Horizontal overlay position or FFmpeg expression.
            y: Vertical overlay position or FFmpeg expression.
            width: Optional overlay width in pixels.
            height: Optional overlay height in pixels.
        """

        super().__init__(context, runner)
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for image overlay composition."""

        if self.width is not None and self.height is not None:
            filter_complex = (
                f"[1:v]scale={self.width}:{self.height}[ov];"
                f"[0:v][ov]overlay={self.x}:{self.y}[v]"
            )
        else:
            filter_complex = f"[0:v][1:v]overlay={self.x}:{self.y}[v]"

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.video_path,
            "-i",
            self.context.overlay_path,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "0:a?",
            "-c:a",
            "copy",
            self.context.output_path,
        ]


class PictureInPicture(BaseEditor[VideoOverlayContext]):
    """Build an FFmpeg command that creates a picture-in-picture composition."""

    def __init__(
        self,
        context: VideoOverlayContext,
        runner: CommandRunner,
        width: int = 320,
        height: int = 180,
        x: str = "main_w-overlay_w-20",
        y: str = "20",
    ) -> None:
        """Initialize picture-in-picture options.

        Args:
            context: Base video, secondary video, and output paths.
            runner: Command runner responsible for executing the command.
            width: Picture-in-picture layer width in pixels.
            height: Picture-in-picture layer height in pixels.
            x: Horizontal overlay position or FFmpeg expression.
            y: Vertical overlay position or FFmpeg expression.
        """

        super().__init__(context, runner)
        self.width = width
        self.height = height
        self.x = x
        self.y = y

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for picture-in-picture composition."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.video_path,
            "-i",
            self.context.overlay_path,
            "-filter_complex",
            (
                f"[1:v]scale={self.width}:{self.height}[pip];"
                f"[0:v][pip]overlay={self.x}:{self.y}[v]"
            ),
            "-map",
            "[v]",
            "-map",
            "0:a?",
            "-c:a",
            "copy",
            self.context.output_path,
        ]
