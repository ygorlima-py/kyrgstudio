"""Video subtitle operations backed by FFmpeg.

This module contains command builders for subtitle workflows, including burning
subtitles into video frames, applying subtitle styles, embedding subtitle
streams, and removing existing subtitle streams from a container.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext, SubtitlesContext
from kyrg.editor.runner import CommandRunner


class AddSubtitles(BaseEditor[SubtitlesContext]):
    """Build an FFmpeg command that burns subtitles into the video frames.

    This operation renders subtitle text into the image itself using FFmpeg's
    ``subtitles`` filter. The resulting subtitles are not removable from the
    output video.
    """

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for burning subtitles into video."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.video_path,
            "-vf",
            f"subtitles={self.context.srt_path}",
            "-c:a",
            "copy",
            self.context.output_path,
        ]


class AddStyledSubtitles(BaseEditor[SubtitlesContext]):
    """Build an FFmpeg command that burns styled subtitles into video."""

    def __init__(
        self,
        context: SubtitlesContext,
        runner: CommandRunner,
        force_style: str,
    ) -> None:
        """Initialize styled subtitle rendering options.

        Args:
            context: Video, subtitle, and output paths used by FFmpeg.
            runner: Command runner responsible for executing the command.
            force_style: FFmpeg/libass style override string.
        """

        super().__init__(context, runner)
        self.force_style = force_style

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for burning styled subtitles."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.video_path,
            "-vf",
            f"subtitles={self.context.srt_path}:force_style='{self.force_style}'",
            "-c:a",
            "copy",
            self.context.output_path,
        ]


class EmbedSubtitles(BaseEditor[SubtitlesContext]):
    """Build an FFmpeg command that embeds subtitles as a separate stream.

    Unlike burned-in subtitles, embedded subtitles remain a separate track in
    the output container and can be enabled or disabled by compatible players.
    """

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for embedding subtitles."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.video_path,
            "-i",
            self.context.srt_path,
            "-c",
            "copy",
            "-c:s",
            "mov_text",
            self.context.output_path,
        ]


class RemoveSubtitles(BaseEditor[MediaContext]):
    """Build an FFmpeg command that removes subtitle streams from media."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for removing subtitle streams."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-map",
            "0",
            "-map",
            "-0:s",
            "-c",
            "copy",
            self.context.output_path,
        ]
