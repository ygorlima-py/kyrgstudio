"""Video stream mapping operations backed by FFmpeg.

This module contains command builders for operations that rearrange or copy
existing media streams without applying visual filters. These commands are used
to remove audio, extract video-only outputs, and replace or add audio tracks
while preserving the source video stream when possible.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import MediaContext, VideoAudioContext


class RemoveVideoAudio(BaseEditor[MediaContext]):
    """Build an FFmpeg command that removes audio from a video file."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for producing a video-only output."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-an",
            "-c:v",
            "copy",
            self.context.output_path,
        ]


class ExtractVideoStream(BaseEditor[MediaContext]):
    """Build an FFmpeg command that extracts the video stream without audio."""

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for copying only the video stream."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-an",
            "-c:v",
            "copy",
            self.context.output_path,
        ]


class ReplaceVideoAudio(BaseEditor[VideoAudioContext]):
    """Build an FFmpeg command that replaces a video's audio track.

    The video stream is copied from the first input and the audio stream is
    taken from the second input.
    """

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for replacing video audio."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.video_path,
            "-i",
            self.context.audio_path,
            "-c:v",
            "copy",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            self.context.output_path,
        ]


class AddAudioToVideo(BaseEditor[VideoAudioContext]):
    """Build an FFmpeg command that adds an audio track to a video.

    The source video stream is copied and the provided audio input is encoded as
    AAC for broad container compatibility.
    """

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for adding audio to video."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.video_path,
            "-i",
            self.context.audio_path,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            self.context.output_path,
        ]


class ExtractVideoFrameAudioSafe(BaseEditor[MediaContext]):
    """Build an FFmpeg command that explicitly maps only the first video stream.

    This operation is useful when input files contain multiple streams and the
    caller wants a video-only output with predictable stream selection.
    """

    def build_command(self) -> list[str]:
        """Return the FFmpeg command for explicit video stream extraction."""

        return [
            "ffmpeg",
            "-y",
            "-i",
            self.context.input_path,
            "-map",
            "0:v:0",
            "-c:v",
            "copy",
            "-an",
            self.context.output_path,
        ]
