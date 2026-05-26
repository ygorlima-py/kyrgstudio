"""Audio cleanup operations backed by FFmpeg.

This module contains command builders for removing or detecting unwanted audio
artifacts such as silence, broadband noise, clicks, and clipping. These
operations are intended to prepare speech or production audio for transcription,
mixing, mastering, or final media assembly.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner


class RemoveSilence(BaseEditor[MediaContext]):
    """Build an FFmpeg command that removes silence from an audio stream.

    The operation uses FFmpeg's ``silenceremove`` filter. It can trim silence
    from the beginning and remove matching silent sections later in the stream,
    depending on the configured stop parameters.
    """

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        start_duration: float = 0.2,
        start_threshold: str = "-50dB",
        stop_periods: int = -1,
        stop_duration: float = 0.5,
        stop_threshold: str = "-50dB",
    ) -> None:
        """Initialize silence removal options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            start_duration: Minimum leading silence duration before removal.
            start_threshold: Silence threshold for the beginning of the stream.
            stop_periods: Number of later silence periods to remove. Negative
                values allow repeated removal throughout the stream.
            stop_duration: Minimum silence duration for later sections.
            stop_threshold: Silence threshold for later sections.
        """

        super().__init__(context, runner)
        self.start_duration = start_duration
        self.start_threshold = start_threshold
        self.stop_periods = stop_periods
        self.stop_duration = stop_duration
        self.stop_threshold = stop_threshold

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for silence removal."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            (
                "silenceremove="
                f"start_periods=1:start_duration={self.start_duration}:"
                f"start_threshold={self.start_threshold}:"
                f"stop_periods={self.stop_periods}:"
                f"stop_duration={self.stop_duration}:"
                f"stop_threshold={self.stop_threshold}"
            ),
            self.context.output_path,
        ]


class DetectSilence(BaseEditor[MediaContext]):
    """Build an FFmpeg command that detects silence without rewriting audio.

    The operation uses FFmpeg's ``silencedetect`` filter and writes diagnostic
    information to FFmpeg logs while sending media output to the ``null`` muxer.
    """

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        noise_threshold: str = "-50dB",
        duration: float = 0.5,
    ) -> None:
        """Initialize silence detection options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            noise_threshold: Volume threshold below which audio is treated as
                silence.
            duration: Minimum silence duration required before reporting it.
        """

        super().__init__(context, runner)
        self.noise_threshold = noise_threshold
        self.duration = duration

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for silence detection."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"silencedetect=n={self.noise_threshold}:d={self.duration}",
            "-f",
            "null",
            self.context.output_path,
        ]


class ReduceNoise(BaseEditor[MediaContext]):
    """Build an FFmpeg command that reduces stationary background noise.

    The operation uses FFmpeg's ``afftdn`` filter, which performs frequency
    domain noise reduction. It is useful for voice recordings with constant
    background noise such as room tone, hiss, or fan noise.
    """

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        noise_reduction: int = 12,
        noise_floor: int = -50,
    ) -> None:
        """Initialize FFT denoising options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            noise_reduction: Noise reduction strength passed to ``afftdn``.
            noise_floor: Estimated noise floor in decibels.
        """

        super().__init__(context, runner)
        self.noise_reduction = noise_reduction
        self.noise_floor = noise_floor

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for noise reduction."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"afftdn=nr={self.noise_reduction}:nf={self.noise_floor}:tn=1",
            self.context.output_path,
        ]


class DeClickAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that removes short impulse clicks.

    The operation uses FFmpeg's ``adeclick`` filter to reduce click-like
    artifacts often found in damaged recordings, edits, or noisy captures.
    """

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for click removal."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            "adeclick",
            self.context.output_path,
        ]


class DeClipAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that attempts to repair clipped audio.

    The operation uses FFmpeg's ``adeclip`` filter to reconstruct peaks that
    were flattened by clipping. This can improve harsh recordings, although it
    cannot fully recover detail that was never captured.
    """

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for clipping repair."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            "adeclip",
            self.context.output_path,
        ]
