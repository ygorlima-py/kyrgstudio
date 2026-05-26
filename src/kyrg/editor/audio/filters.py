"""Tonal audio filter operations backed by FFmpeg.

This module contains command builders for frequency-domain shaping operations,
including high-pass, low-pass, band-pass, band-reject, and parametric
equalization filters. These operations are useful for voice cleanup, tonal
correction, and preparing audio for mixing or transcription.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner


class HighPassFilter(BaseEditor[MediaContext]):
    """Build an FFmpeg command that removes low-frequency content."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        frequency: int = 80,
    ) -> None:
        """Initialize high-pass filter options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            frequency: Cutoff frequency in hertz.
        """

        super().__init__(context, runner)
        self.frequency = frequency

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for high-pass filtering."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"highpass=f={self.frequency}",
            self.context.output_path,
        ]


class LowPassFilter(BaseEditor[MediaContext]):
    """Build an FFmpeg command that removes high-frequency content."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        frequency: int = 12000,
    ) -> None:
        """Initialize low-pass filter options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            frequency: Cutoff frequency in hertz.
        """

        super().__init__(context, runner)
        self.frequency = frequency

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for low-pass filtering."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"lowpass=f={self.frequency}",
            self.context.output_path,
        ]


class BandPassFilter(BaseEditor[MediaContext]):
    """Build an FFmpeg command that keeps a selected frequency band."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        frequency: int = 1000,
        width_type: str = "h",
        width: int = 200,
    ) -> None:
        """Initialize band-pass filter options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            frequency: Center frequency in hertz.
            width_type: Width unit accepted by FFmpeg, such as ``"h"`` for
                hertz or ``"q"`` for quality factor.
            width: Filter bandwidth using the configured ``width_type``.
        """

        super().__init__(context, runner)
        self.frequency = frequency
        self.width_type = width_type
        self.width = width

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for band-pass filtering."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"bandpass=f={self.frequency}:width_type={self.width_type}:width={self.width}",
            self.context.output_path,
        ]


class BandRejectFilter(BaseEditor[MediaContext]):
    """Build an FFmpeg command that removes a selected frequency band."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        frequency: int = 1000,
        width_type: str = "h",
        width: int = 200,
    ) -> None:
        """Initialize band-reject filter options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            frequency: Center frequency in hertz.
            width_type: Width unit accepted by FFmpeg, such as ``"h"`` for
                hertz or ``"q"`` for quality factor.
            width: Rejected bandwidth using the configured ``width_type``.
        """

        super().__init__(context, runner)
        self.frequency = frequency
        self.width_type = width_type
        self.width = width

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for band-reject filtering."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"bandreject=f={self.frequency}:width_type={self.width_type}:width={self.width}",
            self.context.output_path,
        ]


class EqualizeAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies parametric equalization."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        frequency: int = 1000,
        width_type: str = "q",
        width: float = 1.0,
        gain_db: float = 0,
    ) -> None:
        """Initialize parametric equalizer options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            frequency: Center frequency to adjust in hertz.
            width_type: Width unit accepted by FFmpeg, such as ``"q"`` for
                quality factor or ``"h"`` for hertz.
            width: Bandwidth or quality factor for the equalizer band.
            gain_db: Gain adjustment in decibels.
        """

        super().__init__(context, runner)
        self.frequency = frequency
        self.width_type = width_type
        self.width = width
        self.gain_db = gain_db

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for parametric equalization."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            (
                f"equalizer=f={self.frequency}:"
                f"width_type={self.width_type}:"
                f"width={self.width}:"
                f"gain={self.gain_db}"
            ),
            self.context.output_path,
        ]
