"""Video composition operations backed by FFmpeg.

This module contains command builders for combining multiple video inputs into
larger compositions. Operations include sequential concatenation, side-by-side
stacking, grid layouts, and crossfades. Most commands use FFmpeg
``filter_complex`` graphs because they need to coordinate multiple streams.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MultiInputContext
from kyrg.editor.runner import CommandRunner


class ConcatVideos(BaseEditor[MultiInputContext]):
    """Build an FFmpeg command that concatenates video inputs with audio.

    Each input is expected to provide both a video stream and an audio stream.
    The resulting output contains a single concatenated video stream and a
    single concatenated audio stream.
    """

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for audio/video concatenation."""

        command = ["ffmpeg", "-y"]

        for input_path in self.context.input_paths:
            command.extend(["-i", input_path])

        inputs = "".join(
            f"[{index}:v:0][{index}:a:0]"
            for index in range(len(self.context.input_paths))
        )
        command.extend(
            [
                "-filter_complex",
                f"{inputs}concat=n={len(self.context.input_paths)}:v=1:a=1[v][a]",
                "-map",
                "[v]",
                "-map",
                "[a]",
                self.context.output_path,
            ]
        )
        return command


class ConcatVideosWithoutAudio(BaseEditor[MultiInputContext]):
    """Build an FFmpeg command that concatenates video inputs without audio."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for video-only concatenation."""

        command = ["ffmpeg", "-y"]

        for input_path in self.context.input_paths:
            command.extend(["-i", input_path])

        inputs = "".join(
            f"[{index}:v:0]" for index in range(len(self.context.input_paths))
        )
        command.extend(
            [
                "-filter_complex",
                f"{inputs}concat=n={len(self.context.input_paths)}:v=1:a=0[v]",
                "-map",
                "[v]",
                self.context.output_path,
            ]
        )
        return command


class StackVideosHorizontal(BaseEditor[MultiInputContext]):
    """Build an FFmpeg command that stacks videos horizontally."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for horizontal video stacking."""

        command = ["ffmpeg", "-y"]

        for input_path in self.context.input_paths:
            command.extend(["-i", input_path])

        command.extend(
            [
                "-filter_complex",
                f"hstack=inputs={len(self.context.input_paths)}",
                self.context.output_path,
            ]
        )
        return command


class StackVideosVertical(BaseEditor[MultiInputContext]):
    """Build an FFmpeg command that stacks videos vertically."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for vertical video stacking."""

        command = ["ffmpeg", "-y"]

        for input_path in self.context.input_paths:
            command.extend(["-i", input_path])

        command.extend(
            [
                "-filter_complex",
                f"vstack=inputs={len(self.context.input_paths)}",
                self.context.output_path,
            ]
        )
        return command


class GridVideos(BaseEditor[MultiInputContext]):
    """Build an FFmpeg command that arranges videos into a custom grid."""

    def __init__(
        self,
        context: MultiInputContext,
        runner: CommandRunner,
        layout: str,
    ) -> None:
        """Initialize grid composition options.

        Args:
            context: Multiple input paths and one output path used by FFmpeg.
            runner: Command runner responsible for executing the command.
            layout: FFmpeg ``xstack`` layout expression, such as
                ``"0_0|w0_0|0_h0|w0_h0"``.
        """

        super().__init__(context, runner)
        self.layout = layout

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for custom grid composition."""

        command = ["ffmpeg", "-y"]

        for input_path in self.context.input_paths:
            command.extend(["-i", input_path])

        command.extend(
            [
                "-filter_complex",
                f"xstack=inputs={len(self.context.input_paths)}:layout={self.layout}",
                self.context.output_path,
            ]
        )
        return command


class CrossFadeVideos(BaseEditor[MultiInputContext]):
    """Build an FFmpeg command that crossfades two video inputs.

    The first two input paths are used. Video is transitioned with ``xfade`` and
    audio is transitioned with ``acrossfade``.
    """

    def __init__(
        self,
        context: MultiInputContext,
        runner: CommandRunner,
        duration: float = 1.0,
        offset: float = 4.0,
        transition: str = "fade",
    ) -> None:
        """Initialize video crossfade options.

        Args:
            context: Multiple input paths and one output path used by FFmpeg.
                The first two inputs are crossfaded.
            runner: Command runner responsible for executing the command.
            duration: Transition duration in seconds.
            offset: Timestamp in seconds where the transition begins.
            transition: FFmpeg ``xfade`` transition name.
        """

        super().__init__(context, runner)
        self.duration = duration
        self.offset = offset
        self.transition = transition

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for crossfading two videos."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_paths[0],
            "-i",
            self.context.input_paths[1],
            "-filter_complex",
            (
                f"[0:v][1:v]xfade=transition={self.transition}:"
                f"duration={self.duration}:offset={self.offset}[v];"
                f"[0:a][1:a]acrossfade=d={self.duration}[a]"
            ),
            "-map",
            "[v]",
            "-map",
            "[a]",
            self.context.output_path,
        ]
