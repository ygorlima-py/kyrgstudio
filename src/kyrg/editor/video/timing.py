"""Video timing and temporal transformation operations backed by FFmpeg.

This module contains command builders for changing frame rate, playback speed,
direction, duration, and temporal transitions. These operations affect how video
is sampled, played, looped, frozen, or faded over time.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner


class ChangeFrameRate(BaseEditor[MediaContext]):
    """Build an FFmpeg command that changes the output frame rate."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        fps: int = 30,
    ) -> None:
        """Initialize frame rate conversion options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            fps: Target output frames per second.
        """

        super().__init__(context, runner)
        self.fps = fps

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for frame rate conversion."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-r",
            str(self.fps),
            self.context.output_path,
        ]


class ChangeVideoSpeed(BaseEditor[MediaContext]):
    """Build an FFmpeg command that changes video speed without audio.

    The operation modifies video presentation timestamps and drops audio from
    the output.
    """

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        speed: float = 1.0,
    ) -> None:
        """Initialize video-only speed adjustment options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            speed: Playback speed multiplier.
        """

        super().__init__(context, runner)
        self.speed = speed

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for video-only speed adjustment."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-filter:v",
            f"setpts={1 / self.speed}*PTS",
            "-an",
            self.context.output_path,
        ]


class ChangePlaybackSpeed(BaseEditor[MediaContext]):
    """Build an FFmpeg command that changes video and audio playback speed."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        speed: float = 1.0,
    ) -> None:
        """Initialize synchronized playback speed options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            speed: Playback speed multiplier applied to video and audio.
        """

        super().__init__(context, runner)
        self.speed = speed

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for synchronized playback speed changes."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-filter_complex",
            f"[0:v]setpts={1 / self.speed}*PTS[v];[0:a]atempo={self.speed}[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            self.context.output_path,
        ]


class ReverseVideo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that reverses video playback."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        reverse_audio: bool = True,
    ) -> None:
        """Initialize reverse playback options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            reverse_audio: Whether to reverse the audio stream as well.
        """

        super().__init__(context, runner)
        self.reverse_audio = reverse_audio

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for reversing video."""

        if not self.reverse_audio:
            return [
                "ffmpeg",
                "-y",
                "-i",
                self.context.input_path,
                "-vf",
                "reverse",
                "-an",
                self.context.output_path,
            ]

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            "reverse",
            "-af",
            "areverse",
            self.context.output_path,
        ]


class LoopVideo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that loops a video input."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        loop_count: int = 1,
        duration: float | None = None,
    ) -> None:
        """Initialize video loop options.

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
        """Return the FFmpeg command for looping video."""

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

        command.extend(["-c", "copy", self.context.output_path])
        return command


class FreezeLastFrame(BaseEditor[MediaContext]):
    """Build an FFmpeg command that extends video by freezing the last frame."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        duration: float = 2.0,
    ) -> None:
        """Initialize last-frame freeze options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            duration: Duration in seconds to hold the final frame.
        """

        super().__init__(context, runner)
        self.duration = duration

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for freezing the last frame."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"tpad=stop_mode=clone:stop_duration={self.duration}",
            self.context.output_path,
        ]


class FadeInVideo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies a video fade-in."""

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
        """Return the FFmpeg command for applying a video fade-in."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"fade=t=in:st={self.start_time}:d={self.duration}",
            "-c:a",
            "copy",
            self.context.output_path,
        ]


class FadeOutVideo(BaseEditor[MediaContext]):
    """Build an FFmpeg command that applies a video fade-out."""

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
        """Return the FFmpeg command for applying a video fade-out."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-vf",
            f"fade=t=out:st={self.start_time}:d={self.duration}",
            "-c:a",
            "copy",
            self.context.output_path,
        ]
