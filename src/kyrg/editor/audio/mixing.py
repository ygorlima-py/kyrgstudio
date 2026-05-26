"""Audio mixing and routing operations backed by FFmpeg.

This module contains command builders for combining multiple audio sources,
concatenating streams, routing channels, balancing stereo content, and building
voice-over/music mixes. Operations here typically use FFmpeg ``filter_complex``
graphs because they need multiple inputs or explicit channel routing.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext, MultiInputContext
from kyrg.editor.runner import CommandRunner


class MixAudios(BaseEditor[MultiInputContext]):
    """Build an FFmpeg command that mixes multiple audio inputs together."""

    def __init__(
        self,
        context: MultiInputContext,
        runner: CommandRunner,
        duration: str = "longest",
        dropout_transition: float = 2,
    ) -> None:
        """Initialize audio mixing options.

        Args:
            context: Multiple input paths and one output path used by FFmpeg.
            runner: Command runner responsible for executing the command.
            duration: Duration strategy used by FFmpeg's ``amix`` filter.
            dropout_transition: Transition duration when an input stream ends.
        """

        super().__init__(context, runner)
        self.duration = duration
        self.dropout_transition = dropout_transition

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for mixing multiple audio inputs."""

        command = ["ffmpeg", "-y"]

        for input_path in self.context.input_paths:
            command.extend(["-i", input_path])

        command.extend(
            [
                "-filter_complex",
                (
                    f"amix=inputs={len(self.context.input_paths)}:"
                    f"duration={self.duration}:"
                    f"dropout_transition={self.dropout_transition}"
                ),
                self.context.output_path,
            ]
        )
        return command


class ConcatAudios(BaseEditor[MultiInputContext]):
    """Build an FFmpeg command that concatenates audio inputs sequentially."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for audio concatenation."""

        command = ["ffmpeg", "-y"]

        for input_path in self.context.input_paths:
            command.extend(["-i", input_path])

        inputs = "".join(
            f"[{index}:a]" for index in range(len(self.context.input_paths))
        )
        command.extend(
            [
                "-filter_complex",
                f"{inputs}concat=n={len(self.context.input_paths)}:v=0:a=1[outa]",
                "-map",
                "[outa]",
                self.context.output_path,
            ]
        )
        return command


class MergeAudioChannels(BaseEditor[MultiInputContext]):
    """Build an FFmpeg command that merges inputs into a multi-channel stream."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for merging audio channels."""

        command = ["ffmpeg", "-y"]

        for input_path in self.context.input_paths:
            command.extend(["-i", input_path])

        command.extend(
            [
                "-filter_complex",
                f"amerge=inputs={len(self.context.input_paths)}[outa]",
                "-map",
                "[outa]",
                self.context.output_path,
            ]
        )
        return command


class PanAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that routes or remaps audio channels."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        layout: str = "stereo",
        left_expression: str = "c0",
        right_expression: str = "c1",
    ) -> None:
        """Initialize channel panning options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            layout: Output channel layout, such as ``"stereo"``.
            left_expression: FFmpeg expression used to build output channel 0.
            right_expression: FFmpeg expression used to build output channel 1.
        """

        super().__init__(context, runner)
        self.layout = layout
        self.left_expression = left_expression
        self.right_expression = right_expression

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for channel panning."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            (
                f"pan={self.layout}|"
                f"c0={self.left_expression}|"
                f"c1={self.right_expression}"
            ),
            self.context.output_path,
        ]


class BalanceStereo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies independent stereo channel gains."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        left_gain: float = 1.0,
        right_gain: float = 1.0,
    ) -> None:
        """Initialize stereo balance options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            left_gain: Gain multiplier applied to the left channel.
            right_gain: Gain multiplier applied to the right channel.
        """

        super().__init__(context, runner)
        self.left_gain = left_gain
        self.right_gain = right_gain

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for stereo balance adjustment."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"pan=stereo|c0={self.left_gain}*c0|c1={self.right_gain}*c1",
            self.context.output_path,
        ]


class MixVoiceWithMusic(BaseEditor[MultiInputContext]):
    """Build an FFmpeg command that mixes a voice track with music.

    The first input is treated as the voice track and the second input is
    treated as the music bed. Each stream receives its own gain before being
    combined with ``amix``.
    """

    def __init__(
        self,
        context: MultiInputContext,
        runner: CommandRunner,
        voice_volume: float = 1.0,
        music_volume: float = 0.25,
        duration: str = "first",
        dropout_transition: float = 2,
    ) -> None:
        """Initialize voice/music mixing options.

        Args:
            context: Multiple input paths and one output path used by FFmpeg.
                The first input is expected to be voice and the second music.
            runner: Command runner responsible for executing the command.
            voice_volume: Gain multiplier applied to the voice input.
            music_volume: Gain multiplier applied to the music input.
            duration: Duration strategy used by FFmpeg's ``amix`` filter.
            dropout_transition: Transition duration when an input stream ends.
        """

        super().__init__(context, runner)
        self.voice_volume = voice_volume
        self.music_volume = music_volume
        self.duration = duration
        self.dropout_transition = dropout_transition

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for mixing voice with music."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_paths[0],
            "-i",
            self.context.input_paths[1],
            "-filter_complex",
            (
                f"[0:a]volume={self.voice_volume}[voice];"
                f"[1:a]volume={self.music_volume}[music];"
                "[voice][music]"
                f"amix=inputs=2:duration={self.duration}:"
                f"dropout_transition={self.dropout_transition}[outa]"
            ),
            "-map",
            "[outa]",
            self.context.output_path,
        ]


class DuckBackgroundMusic(BaseEditor[MultiInputContext]):
    """Build an FFmpeg command that ducks music under a voice track.

    The first input is treated as the voice sidechain source and the second
    input is treated as the music bed. The music is compressed against the
    voice signal and then mixed back with the voice.
    """

    def __init__(
        self,
        context: MultiInputContext,
        runner: CommandRunner,
        threshold: float = 0.05,
        ratio: int = 8,
        attack: int = 20,
        release: int = 500,
    ) -> None:
        """Initialize sidechain ducking options.

        Args:
            context: Multiple input paths and one output path used by FFmpeg.
                The first input is expected to be voice and the second music.
            runner: Command runner responsible for executing the command.
            threshold: Sidechain compression threshold.
            ratio: Compression ratio applied to the music bed.
            attack: Compressor attack time in milliseconds.
            release: Compressor release time in milliseconds.
        """

        super().__init__(context, runner)
        self.threshold = threshold
        self.ratio = ratio
        self.attack = attack
        self.release = release

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for sidechain music ducking."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_paths[0],
            "-i",
            self.context.input_paths[1],
            "-filter_complex",
            (
                "[1:a][0:a]"
                f"sidechaincompress=threshold={self.threshold}:"
                f"ratio={self.ratio}:attack={self.attack}:"
                f"release={self.release}[ducked];"
                "[0:a][ducked]amix=inputs=2:duration=first[outa]"
            ),
            "-map",
            "[outa]",
            self.context.output_path,
        ]
