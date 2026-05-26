"""Video color and image treatment operations backed by FFmpeg.

This module contains command builders for visual corrections and stylistic
image treatments. The operations focus on color adjustment, grayscale
conversion, inversion, blur, sharpening, denoising, and vignette effects.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner


class AdjustVideoColor(BaseEditor[MediaContext]):
    """Build an FFmpeg command that adjusts basic video color properties."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        brightness: float = 0,
        contrast: float = 1,
        saturation: float = 1,
        gamma: float = 1,
    ) -> None:
        """Initialize color adjustment options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            brightness: Brightness adjustment passed to FFmpeg's ``eq`` filter.
            contrast: Contrast multiplier passed to FFmpeg's ``eq`` filter.
            saturation: Saturation multiplier passed to FFmpeg's ``eq`` filter.
            gamma: Gamma adjustment passed to FFmpeg's ``eq`` filter.
        """

        super().__init__(context, runner)
        self.brightness = brightness
        self.contrast = contrast
        self.saturation = saturation
        self.gamma = gamma

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for color adjustment."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            (
                f"eq=brightness={self.brightness}:"
                f"contrast={self.contrast}:"
                f"saturation={self.saturation}:"
                f"gamma={self.gamma}"
            ),
            self.context.output_path,
        ]


class ConvertToGrayscale(BaseEditor[MediaContext]):
    """Build an FFmpeg command that converts video frames to grayscale."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for grayscale conversion."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            "format=gray",
            self.context.output_path,
        ]


class InvertVideoColors(BaseEditor[MediaContext]):
    """Build an FFmpeg command that inverts video colors."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for color inversion."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            "negate",
            self.context.output_path,
        ]


class BlurVideo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies a box blur to video frames."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        luma_radius: int = 2,
        luma_power: int = 1,
    ) -> None:
        """Initialize blur options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            luma_radius: Blur radius for the luma plane.
            luma_power: Blur power for the luma plane.
        """

        super().__init__(context, runner)
        self.luma_radius = luma_radius
        self.luma_power = luma_power

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for blurring video."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"boxblur={self.luma_radius}:{self.luma_power}",
            self.context.output_path,
        ]


class SharpenVideo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that sharpens video frames."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        luma_amount: float = 1.0,
    ) -> None:
        """Initialize sharpening options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            luma_amount: Sharpening amount applied to the luma plane.
        """

        super().__init__(context, runner)
        self.luma_amount = luma_amount

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for sharpening video."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"unsharp=5:5:{self.luma_amount}:5:5:0.0",
            self.context.output_path,
        ]


class DenoiseVideo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that reduces spatial and temporal video noise."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        luma_spatial: float = 4,
        chroma_spatial: float = 3,
        luma_temporal: float = 6,
        chroma_temporal: float = 4.5,
    ) -> None:
        """Initialize denoising options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            luma_spatial: Spatial denoise strength for the luma plane.
            chroma_spatial: Spatial denoise strength for chroma planes.
            luma_temporal: Temporal denoise strength for the luma plane.
            chroma_temporal: Temporal denoise strength for chroma planes.
        """

        super().__init__(context, runner)
        self.luma_spatial = luma_spatial
        self.chroma_spatial = chroma_spatial
        self.luma_temporal = luma_temporal
        self.chroma_temporal = chroma_temporal

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for video denoising."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            (
                f"hqdn3d={self.luma_spatial}:"
                f"{self.chroma_spatial}:"
                f"{self.luma_temporal}:"
                f"{self.chroma_temporal}"
            ),
            self.context.output_path,
        ]


class AddVignette(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies a vignette effect."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        angle: str = "PI/4",
    ) -> None:
        """Initialize vignette options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            angle: FFmpeg vignette angle expression.
        """

        super().__init__(context, runner)
        self.angle = angle

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for applying a vignette."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"vignette={self.angle}",
            self.context.output_path,
        ]
