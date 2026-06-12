"""Context objects used by editor command builders.

This module defines small data containers that describe the file inputs and
outputs required by audio and video editing operations. Contexts intentionally
do not contain execution logic, validation, or FFmpeg-specific behavior. They
exist to make operation signatures explicit and to keep command builders
focused on translating a known input shape into a command-line invocation.
"""

from dataclasses import dataclass
from typing import NotRequired


@dataclass
class MediaContext:
    """Context for operations with one media input and one output.

    This is the default context for most audio and video transformations, such
    as trimming, filtering, transcoding, normalization, resizing, and metadata
    operations.

    Attributes:
        input_path: Path to the source media file.
        output_path: Path where the generated media file should be written.
    """

    input_path: str
    output_path: str


@dataclass
class VideoAudioContext:
    """Context for operations that combine a video input with an audio input.

    This context is used by operations that replace, add, or synchronize audio
    against an existing video stream.

    Attributes:
        video_path: Path to the source video file.
        audio_path: Path to the source audio file.
        output_path: Path where the resulting media file should be written.
    """

    video_path: str
    audio_path: str
    output_path: str


@dataclass
class MultiInputContext:
    """Context for operations that require multiple input files.

    This context supports composition-style operations such as concatenation,
    mixing, stacking, grids, and crossfades.

    Attributes:
        input_paths: Ordered paths used as operation inputs.
        output_path: Path where the resulting media file should be written.
    """

    input_paths: list[str]
    output_path: str


@dataclass
class SubtitlesContext:
    """Context for operations that apply or embed subtitles into video.

    Attributes:
        video_path: Path to the source video file.
        srt_path: Path to the subtitle file used by the operation.
        output_path: Path where the resulting video file should be written.
    """

    video_path: str
    srt_path: str
    output_path: str


@dataclass
class VideoOverlayContext:
    """Context for operations that place an external visual asset over video.

    This context is used for watermark, image overlay, and picture-in-picture
    operations where the second input is a visual asset rather than an audio
    stream.

    Attributes:
        video_path: Path to the source video file.
        overlay_path: Path to the overlay image or video asset.
        output_path: Path where the resulting video file should be written.
    """

    video_path: str
    overlay_path: str
    output_path: str


@dataclass
class ImageSequenceContext:
    """Context for operations that turn an image sequence into video.

    Attributes:
        input_pattern: FFmpeg-compatible input pattern, such as
            ``"frame_%04d.png"``.
        output_path: Path where the generated video file should be written.
    """

    input_pattern: str
    output_path: str
