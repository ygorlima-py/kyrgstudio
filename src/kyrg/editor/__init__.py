"""Editor package public API.

This package provides command-based audio and video editing operations backed by
FFmpeg. The top-level package exports shared editor infrastructure, while audio
and video operations are exposed by their own subpackages.
"""

from kyrg.editor.base import BaseEditor
from kyrg.editor.context import (
    ImageSequenceContext,
    MediaContext,
    MultiInputContext,
    SubtitlesContext,
    VideoAudioContext,
    VideoOverlayContext,
)
from kyrg.editor.runner import CommandRunner

__all__ = [
    "BaseEditor",
    "CommandRunner",
    "ImageSequenceContext",
    "MediaContext",
    "MultiInputContext",
    "SubtitlesContext",
    "VideoAudioContext",
    "VideoOverlayContext",
]