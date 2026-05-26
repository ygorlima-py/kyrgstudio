"""Video geometry and spatial transformation operations backed by FFmpeg.

This module contains command builders for changing frame dimensions, cropping,
padding, aspect ratios, rotation, and flipping. These operations are commonly
used to adapt video for platform-specific layouts, correct orientation, or
prepare media for composition.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner


class ResizeVideo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that resizes video to exact dimensions."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        width: int,
        height: int,
    ) -> None:
        """Initialize resize options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            width: Output width in pixels.
            height: Output height in pixels.
        """

        super().__init__(context, runner)
        self.width = width
        self.height = height

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for exact resizing."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"scale={self.width}:{self.height}",
            self.context.output_path,
        ]


class ScaleVideoByWidth(BaseEditor[MediaContext]):
    """Build an FFmpeg command that scales video by width and preserves aspect."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        width: int,
    ) -> None:
        """Initialize width-based scaling options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            width: Output width in pixels. Height is calculated automatically.
        """

        super().__init__(context, runner)
        self.width = width

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for width-based scaling."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"scale={self.width}:-2",
            self.context.output_path,
        ]


class ScaleVideoByHeight(BaseEditor[MediaContext]):
    """Build an FFmpeg command that scales video by height and preserves aspect."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        height: int,
    ) -> None:
        """Initialize height-based scaling options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            height: Output height in pixels. Width is calculated automatically.
        """

        super().__init__(context, runner)
        self.height = height

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for height-based scaling."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"scale=-2:{self.height}",
            self.context.output_path,
        ]


class CropVideo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that crops video to a rectangular region."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        width: int,
        height: int,
        x: str = "(in_w-out_w)/2",
        y: str = "(in_h-out_h)/2",
    ) -> None:
        """Initialize crop options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            width: Crop width in pixels.
            height: Crop height in pixels.
            x: Horizontal crop offset or FFmpeg expression.
            y: Vertical crop offset or FFmpeg expression.
        """

        super().__init__(context, runner)
        self.width = width
        self.height = height
        self.x = x
        self.y = y

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for cropping video."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"crop={self.width}:{self.height}:{self.x}:{self.y}",
            self.context.output_path,
        ]


class CenterCropVertical(BaseEditor[MediaContext]):
    """Build an FFmpeg command that center-crops video into a vertical canvas."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        width: int = 1080,
        height: int = 1920,
    ) -> None:
        """Initialize vertical center-crop options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            width: Target vertical output width in pixels.
            height: Target vertical output height in pixels.
        """

        super().__init__(context, runner)
        self.width = width
        self.height = height

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for vertical center-cropping."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            (
                f"scale=-2:{self.height},"
                f"crop={self.width}:{self.height}:(in_w-out_w)/2:(in_h-out_h)/2"
            ),
            self.context.output_path,
        ]


class PadVideo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that pads video into a larger canvas."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        width: int,
        height: int,
        x: str = "(ow-iw)/2",
        y: str = "(oh-ih)/2",
        color: str = "black",
    ) -> None:
        """Initialize padding options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            width: Output canvas width in pixels.
            height: Output canvas height in pixels.
            x: Horizontal placement offset or FFmpeg expression.
            y: Vertical placement offset or FFmpeg expression.
            color: Padding color.
        """

        super().__init__(context, runner)
        self.width = width
        self.height = height
        self.x = x
        self.y = y
        self.color = color

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for padding video."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"pad={self.width}:{self.height}:{self.x}:{self.y}:color={self.color}",
            self.context.output_path,
        ]


class ChangeDisplayAspectRatio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that changes the display aspect ratio metadata."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        aspect_ratio: str = "16/9",
    ) -> None:
        """Initialize display aspect ratio options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            aspect_ratio: Display aspect ratio, such as ``"16/9"`` or ``"9/16"``.
        """

        super().__init__(context, runner)
        self.aspect_ratio = aspect_ratio

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for display aspect ratio changes."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-aspect",
            self.aspect_ratio,
            self.context.output_path,
        ]


class SetSampleAspectRatio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that changes the sample aspect ratio."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        sample_aspect_ratio: str = "1",
    ) -> None:
        """Initialize sample aspect ratio options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            sample_aspect_ratio: Sample aspect ratio expression, such as ``"1"``.
        """

        super().__init__(context, runner)
        self.sample_aspect_ratio = sample_aspect_ratio

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for sample aspect ratio changes."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"setsar={self.sample_aspect_ratio}",
            self.context.output_path,
        ]


class RotateVideo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that rotates video by an arbitrary angle."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        angle_radians: str = "PI/2",
    ) -> None:
        """Initialize arbitrary rotation options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            angle_radians: Rotation angle expression in radians.
        """

        super().__init__(context, runner)
        self.angle_radians = angle_radians

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for arbitrary rotation."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"rotate={self.angle_radians}",
            self.context.output_path,
        ]


class Rotate90Clockwise(BaseEditor[MediaContext]):
    """Build an FFmpeg command that rotates video 90 degrees clockwise."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for clockwise rotation."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            "transpose=1",
            self.context.output_path,
        ]


class Rotate90CounterClockwise(BaseEditor[MediaContext]):
    """Build an FFmpeg command that rotates video 90 degrees counter-clockwise."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for counter-clockwise rotation."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            "transpose=2",
            self.context.output_path,
        ]


class FlipVideoHorizontal(BaseEditor[MediaContext]):
    """Build an FFmpeg command that flips video horizontally."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for horizontal flipping."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            "hflip",
            self.context.output_path,
        ]


class FlipVideoVertical(BaseEditor[MediaContext]):
    """Build an FFmpeg command that flips video vertically."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for vertical flipping."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            "vflip",
            self.context.output_path,
        ]
