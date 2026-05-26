"""Video metadata operations backed by FFmpeg.

This module contains command builders for metadata-only media updates. The
operations copy existing streams without re-encoding and only modify container
metadata, making them lightweight compared to visual or audio transformations.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner


class StripMetadata(BaseEditor[MediaContext]):
    """Build an FFmpeg command that removes container metadata from media."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for stripping metadata."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-map_metadata",
            "-1",
            "-c",
            "copy",
            self.context.output_path,
        ]


class AddVideoMetadata(BaseEditor[MediaContext]):
    """Build an FFmpeg command that writes common metadata fields."""

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        title: str | None = None,
        artist: str | None = None,
        comment: str | None = None,
    ) -> None:
        """Initialize metadata fields.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            title: Optional title metadata value.
            artist: Optional artist metadata value.
            comment: Optional comment metadata value.
        """

        super().__init__(context, runner)
        self.title = title
        self.artist = artist
        self.comment = comment

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for writing metadata."""

        command = [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-c",
            "copy",
        ]

        if self.title:
            command.extend(["-metadata", f"title={self.title}"])

        if self.artist:
            command.extend(["-metadata", f"artist={self.artist}"])

        if self.comment:
            command.extend(["-metadata", f"comment={self.comment}"])

        command.append(self.context.output_path)
        return command
