"""Audio analysis operations backed by FFmpeg.

This module contains command builders for audio inspection workflows. Unlike
audio transformation operations, these commands primarily emit diagnostic
metadata through FFmpeg logs while using the ``null`` muxer as the output sink.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner


class AnalyzeVolume(BaseEditor[MediaContext]):
    """Build an FFmpeg command that reports basic volume statistics.

    The operation uses FFmpeg's ``volumedetect`` filter to calculate values such
    as mean volume and maximum volume. The media stream is not written to a real
    output file; FFmpeg emits the analysis data in its process logs.
    """

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for volume analysis."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            "volumedetect",
            "-f",
            "null",
            self.context.output_path,
        ]


class AnalyzeAudioStats(BaseEditor[MediaContext]):
    """Build an FFmpeg command that reports detailed audio statistics.

    The operation uses FFmpeg's ``astats`` filter with metadata enabled. It is
    intended for deeper inspection of channel levels, peaks, RMS values, dynamic
    range, and other low-level audio characteristics exposed by FFmpeg.
    """

    def __init__(
        self,
        context: MediaContext,
        runner: CommandRunner,
        reset: int = 1,
    ) -> None:
        """Initialize audio statistics analysis options.

        Args:
            context: Input and output paths used by the FFmpeg command.
            runner: Command runner responsible for executing the command.
            reset: Number of frames after which ``astats`` resets cumulative
                measurements. A value of ``1`` favors per-frame statistics.
        """

        super().__init__(context, runner)
        self.reset = reset

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for detailed audio statistics."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-af",
            f"astats=metadata=1:reset={self.reset}",
            "-f",
            "null",
            self.context.output_path,
        ]

class AudioSize(BaseEditor[MediaContext]):
    CAPTURE_OUTPUT = True
    
    def build_command(self) -> list[str]:
        return [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            self.context.input_path,
        ]
    
if __name__ == "__main__":
    context = MediaContext(
        input_path='src/data/output/audio_extraido.wav',
        output_path='')
    
    action = AudioSize(context=context, runner=CommandRunner())
    result = action.execute()
    
    