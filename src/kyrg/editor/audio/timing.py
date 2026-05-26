"""Audio timing and temporal editing operations backed by FFmpeg.

This module contains command builders for operations that change where audio
starts, stops, repeats, fades, or moves in time. These operations are useful for
editing speech, aligning tracks, preparing clips, and building transitions
before final mixing or video assembly.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext, MultiInputContext
from kyrg.editor.runner import CommandRunner


class TrimAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that trims audio by start, end, or duration."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        start_time: float = 0,
        end_time: float | None = None,
        duration: float | None = None,
    ) -> None:
        """Initialize audio trimming options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            start_time: Start time in seconds.
            end_time: Optional end time in seconds.
            duration: Optional trim duration in seconds.
        """

        super().__init__(context, runner)
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for trimming audio."""

        filter_parts = [f"start={self.start_time}"]

        if self.end_time is not None:
            filter_parts.append(f"end={self.end_time}")

        if self.duration is not None:
            filter_parts.append(f"duration={self.duration}")

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"atrim={':'.join(filter_parts)},asetpts=PTS-STARTPTS",
            self.context.output_path,
        ]


class DelayAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that delays audio playback."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        delay_ms: int = 1000,
    ) -> None:
        """Initialize audio delay options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            delay_ms: Delay amount in milliseconds.
        """

        super().__init__(context, runner)
        self.delay_ms = delay_ms

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for delaying audio."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"adelay={self.delay_ms}:all=1",
            self.context.output_path,
        ]


class PadAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that appends silence to an audio stream."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        pad_duration: float = 1.0,
    ) -> None:
        """Initialize audio padding options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            pad_duration: Duration of silence to append in seconds.
        """

        super().__init__(context, runner)
        self.pad_duration = pad_duration

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for padding audio with silence."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"apad=pad_dur={self.pad_duration}",
            self.context.output_path,
        ]


class LoopAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that loops an audio input."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        loop_count: int = 1,
        duration: float | None = None,
    ) -> None:
        """Initialize audio looping options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            loop_count: Number of additional times FFmpeg should loop input.
            duration: Optional maximum output duration in seconds.
        """

        super().__init__(context, runner)
        self.loop_count = loop_count
        self.duration = duration

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for looping audio."""

        command = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            str(self.loop_count),
            "-i",
            self.context.input_path,
        ]

        if self.duration is not None:
            command.extend(["-t", str(self.duration)])

        command.append(self.context.output_path)
        return command


class ChangeAudioSpeed(BaseEditor[MediaContext]):
    """Build an FFmpeg command that changes audio playback tempo."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        tempo: float = 1.0,
    ) -> None:
        """Initialize tempo adjustment options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            tempo: Playback tempo multiplier.
        """

        super().__init__(context, runner)
        self.tempo = tempo

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for tempo adjustment."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"atempo={self.tempo}",
            self.context.output_path,
        ]


class ReverseAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that reverses an audio stream."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for reversing audio."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            "areverse",
            self.context.output_path,
        ]


class FadeInAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies a fade-in envelope."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        start_time: float = 0,
        duration: float = 1.0,
    ) -> None:
        """Initialize fade-in options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            start_time: Fade start time in seconds.
            duration: Fade duration in seconds.
        """

        super().__init__(context, runner)
        self.start_time = start_time
        self.duration = duration

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for applying a fade-in."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"afade=t=in:st={self.start_time}:d={self.duration}",
            self.context.output_path,
        ]


class FadeOutAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies a fade-out envelope."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        start_time: float,
        duration: float = 1.0,
    ) -> None:
        """Initialize fade-out options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            start_time: Fade start time in seconds.
            duration: Fade duration in seconds.
        """

        super().__init__(context, runner)
        self.start_time = start_time
        self.duration = duration

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for applying a fade-out."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"afade=t=out:st={self.start_time}:d={self.duration}",
            self.context.output_path,
        ]


class CrossFadeAudios(BaseEditor[MultiInputContext]):
    """Build an FFmpeg command that crossfades two audio inputs."""

    def __init__(
        self,
        context: MultiInputContext,
        runner: CommandRunner,
        duration: float = 1.0,
        curve1: str = "tri",
        curve2: str = "tri",
    ) -> None:
        """Initialize audio crossfade options.

        Args:
            context: Multiple input paths and one output path used by FFmpeg.
                The first two inputs are crossfaded.
            runner: Command runner responsible for executing the command.
            duration: Crossfade duration in seconds.
            curve1: Fade curve applied to the first input.
            curve2: Fade curve applied to the second input.
        """

        super().__init__(context, runner)
        self.duration = duration
        self.curve1 = curve1
        self.curve2 = curve2

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for crossfading two audio inputs."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_paths[0],
            "-i",
            self.context.input_paths[1],
            "-filter_complex",
            f"acrossfade=d={self.duration}:c1={self.curve1}:c2={self.curve2}",
            self.context.output_path,
        ]
