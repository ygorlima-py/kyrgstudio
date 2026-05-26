"""Audio dynamics operations backed by FFmpeg.

This module contains command builders for controlling loudness, dynamic range,
peaks, and low-level signal behavior. These operations are commonly used to
prepare voice, music, and mixed audio for consistent playback in production
media workflows.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner


class ChangeVolume(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies a direct volume adjustment."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        volume: str = "1.0",
    ) -> None:
        """Initialize volume adjustment options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            volume: FFmpeg volume expression, such as ``"1.0"``, ``"0.5"``,
                or ``"3dB"``.
        """

        super().__init__(context, runner)
        self.volume = volume

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for direct volume adjustment."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"volume={self.volume}",
            self.context.output_path,
        ]


class NormalizeVolume(BaseEditor[MediaContext]):
    """Build an FFmpeg command that performs EBU R128 loudness normalization."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        integrated: int = -16,
        true_peak: float = -1.5,
        lra: int = 11,
    ) -> None:
        """Initialize loudness normalization options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            integrated: Target integrated loudness in LUFS.
            true_peak: Target true peak in dBTP.
            lra: Target loudness range.
        """

        super().__init__(context, runner)
        self.integrated = integrated
        self.true_peak = true_peak
        self.lra = lra

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for loudness normalization."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"loudnorm=I={self.integrated}:TP={self.true_peak}:LRA={self.lra}",
            self.context.output_path,
        ]


class DynamicNormalize(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies dynamic audio normalization.

    This operation uses FFmpeg's ``dynaudnorm`` filter to smooth perceived
    loudness over time. It can be useful for uneven recordings where a single
    static gain adjustment is not enough.
    """

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        frame_length: int = 500,
        gaussian_size: int = 31,
        max_gain: float = 10,
    ) -> None:
        """Initialize dynamic normalization options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            frame_length: Analysis frame length used by ``dynaudnorm``.
            gaussian_size: Smoothing window size used for gain changes.
            max_gain: Maximum gain factor allowed by the filter.
        """

        super().__init__(context, runner)
        self.frame_length = frame_length
        self.gaussian_size = gaussian_size
        self.max_gain = max_gain

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for dynamic normalization."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"dynaudnorm=f={self.frame_length}:g={self.gaussian_size}:m={self.max_gain}",
            self.context.output_path,
        ]


class CompressAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that compresses audio dynamic range.

    The operation uses FFmpeg's ``acompressor`` filter to reduce level
    differences between quieter and louder passages. This is useful for voice
    intelligibility and more consistent playback.
    """

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        threshold: int = -18,
        ratio: int = 3,
        attack: int = 20,
        release: int = 250,
    ) -> None:
        """Initialize compression options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            threshold: Compression threshold in dB.
            ratio: Compression ratio applied above the threshold.
            attack: Attack time in milliseconds.
            release: Release time in milliseconds.
        """

        super().__init__(context, runner)
        self.threshold = threshold
        self.ratio = ratio
        self.attack = attack
        self.release = release

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for dynamic range compression."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            (
                f"acompressor=threshold={self.threshold}dB:"
                f"ratio={self.ratio}:"
                f"attack={self.attack}:"
                f"release={self.release}"
            ),
            self.context.output_path,
        ]


class LimitAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that limits peak audio levels."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        limit: float = 0.95,
        attack: int = 5,
        release: int = 50,
    ) -> None:
        """Initialize peak limiting options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            limit: Linear peak limit passed to FFmpeg's ``alimiter`` filter.
            attack: Limiter attack time in milliseconds.
            release: Limiter release time in milliseconds.
        """

        super().__init__(context, runner)
        self.limit = limit
        self.attack = attack
        self.release = release

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for peak limiting."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"alimiter=limit={self.limit}:attack={self.attack}:release={self.release}",
            self.context.output_path,
        ]


class GateAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies a noise gate.

    The operation uses FFmpeg's ``agate`` filter to attenuate signal below the
    configured threshold. It can help reduce room tone or low-level noise
    between spoken phrases.
    """

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        threshold: float = 0.125,
        ratio: int = 2,
        attack: int = 20,
        release: int = 250,
    ) -> None:
        """Initialize gate options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            threshold: Gate threshold as a linear amplitude value.
            ratio: Gate attenuation ratio.
            attack: Gate attack time in milliseconds.
            release: Gate release time in milliseconds.
        """

        super().__init__(context, runner)
        self.threshold = threshold
        self.ratio = ratio
        self.attack = attack
        self.release = release

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for noise gating."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            (
                f"agate=threshold={self.threshold}:"
                f"ratio={self.ratio}:"
                f"attack={self.attack}:"
                f"release={self.release}"
            ),
            self.context.output_path,
        ]
