"""Creative audio effect operations backed by FFmpeg.

This module contains command builders for non-destructive effect-style audio
processing. These operations are useful for creative treatment, sound design,
or stylistic transformations after core cleanup and dynamics processing have
already been handled.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner


class AddEcho(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies an echo effect."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        input_gain: float = 0.8,
        output_gain: float = 0.9,
        delays: str = "1000",
        decays: str = "0.3",
    ) -> None:
        """Initialize echo effect options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            input_gain: Input signal gain before the echo is applied.
            output_gain: Output signal gain after the echo is applied.
            delays: Echo delay values in milliseconds. Multiple values can be
                provided using FFmpeg's pipe-separated format.
            decays: Echo decay values. Multiple values can be provided using
                FFmpeg's pipe-separated format.
        """

        super().__init__(context, runner)
        self.input_gain = input_gain
        self.output_gain = output_gain
        self.delays = delays
        self.decays = decays

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for applying echo."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            (
                f"aecho={self.input_gain}:"
                f"{self.output_gain}:"
                f"{self.delays}:"
                f"{self.decays}"
            ),
            self.context.output_path,
        ]


class TremoloAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies amplitude modulation."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        frequency: float = 5.0,
        depth: float = 0.5,
    ) -> None:
        """Initialize tremolo effect options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            frequency: Modulation frequency in hertz.
            depth: Modulation depth, typically between ``0`` and ``1``.
        """

        super().__init__(context, runner)
        self.frequency = frequency
        self.depth = depth

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for applying tremolo."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"tremolo=f={self.frequency}:d={self.depth}",
            self.context.output_path,
        ]


class VibratoAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies pitch modulation."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        frequency: float = 5.0,
        depth: float = 0.5,
    ) -> None:
        """Initialize vibrato effect options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            frequency: Modulation frequency in hertz.
            depth: Modulation depth, typically between ``0`` and ``1``.
        """

        super().__init__(context, runner)
        self.frequency = frequency
        self.depth = depth

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for applying vibrato."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"vibrato=f={self.frequency}:d={self.depth}",
            self.context.output_path,
        ]


class ChorusAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies a chorus effect.

    The operation uses FFmpeg's ``chorus`` filter to blend delayed and
    modulated copies of the original signal, creating a wider and thicker sound.
    """

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        input_gain: float = 0.5,
        output_gain: float = 0.9,
        delays: str = "40",
        decays: str = "0.4",
        speeds: str = "0.25",
        depths: str = "2",
    ) -> None:
        """Initialize chorus effect options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            input_gain: Input signal gain before the chorus is applied.
            output_gain: Output signal gain after the chorus is applied.
            delays: Delay values for chorus voices.
            decays: Decay values for chorus voices.
            speeds: Modulation speed values for chorus voices.
            depths: Modulation depth values for chorus voices.
        """

        super().__init__(context, runner)
        self.input_gain = input_gain
        self.output_gain = output_gain
        self.delays = delays
        self.decays = decays
        self.speeds = speeds
        self.depths = depths

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for applying chorus."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            (
                f"chorus={self.input_gain}:"
                f"{self.output_gain}:"
                f"{self.delays}:"
                f"{self.decays}:"
                f"{self.speeds}:"
                f"{self.depths}"
            ),
            self.context.output_path,
        ]


class PhaserAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies a phaser effect."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        input_gain: float = 0.4,
        output_gain: float = 0.74,
        delay: float = 3,
        decay: float = 0.4,
        speed: float = 0.5,
        phase_type: str = "triangular",
    ) -> None:
        """Initialize phaser effect options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            input_gain: Input signal gain before the phaser is applied.
            output_gain: Output signal gain after the phaser is applied.
            delay: Delay used by the phaser filter.
            decay: Decay factor used by the phaser filter.
            speed: Modulation speed for the phaser sweep.
            phase_type: Phaser waveform type accepted by FFmpeg, such as
                ``"triangular"`` or ``"sinusoidal"``.
        """

        super().__init__(context, runner)
        self.input_gain = input_gain
        self.output_gain = output_gain
        self.delay = delay
        self.decay = decay
        self.speed = speed
        self.phase_type = phase_type

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for applying phaser."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            (
                f"aphaser=in_gain={self.input_gain}:"
                f"out_gain={self.output_gain}:"
                f"delay={self.delay}:"
                f"decay={self.decay}:"
                f"speed={self.speed}:"
                f"type={self.phase_type}"
            ),
            self.context.output_path,
        ]


class CrushAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies bit-crushing distortion."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        level_in: float = 1.0,
        level_out: float = 1.0,
        bits: int = 8,
        mix: float = 1.0,
    ) -> None:
        """Initialize bit-crushing options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            level_in: Input level applied before crushing.
            level_out: Output level applied after crushing.
            bits: Target bit depth used by the crushing effect.
            mix: Wet/dry mix for the processed signal.
        """

        super().__init__(context, runner)
        self.level_in = level_in
        self.level_out = level_out
        self.bits = bits
        self.mix = mix

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for applying bit-crushing."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            (
                f"acrusher=level_in={self.level_in}:"
                f"level_out={self.level_out}:"
                f"bits={self.bits}:"
                f"mix={self.mix}"
            ),
            self.context.output_path,
        ]
