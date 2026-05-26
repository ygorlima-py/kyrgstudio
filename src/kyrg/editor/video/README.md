# Video Editor Operations

This package contains FFmpeg-backed video operations used by the editor layer.
Each operation is implemented as a command builder: it receives a context,
stores optional configuration, builds an FFmpeg command, and delegates execution
to the shared command runner.

The package is organized by video editing responsibility rather than by FFmpeg
filter name. This keeps the public API closer to the domain language used by
the application: streams, cutting, conversion, geometry, timing, color,
overlays, subtitles, composition, frames, metadata, and stabilization.

## Architecture

Video operations follow the same structure:

```python
operation = SomeVideoOperation(context, runner, ...)
command = operation.build_command()
operation.execute()
```

The operation classes do not execute FFmpeg directly. Execution is delegated to
`CommandRunner`, which keeps command construction separate from process
execution and makes operations easier to test.

Most operations use `MediaContext`, which represents a single input and a single
output:

```python
MediaContext(input_path="input.mp4", output_path="output.mp4")
```

Operations that combine multiple inputs use `MultiInputContext`:

```python
MultiInputContext(input_paths=["intro.mp4", "main.mp4"], output_path="final.mp4")
```

Operations with specialized inputs use dedicated contexts:

```python
VideoAudioContext(video_path="video.mp4", audio_path="voice.wav", output_path="final.mp4")
SubtitlesContext(video_path="video.mp4", srt_path="captions.srt", output_path="subtitled.mp4")
VideoOverlayContext(video_path="video.mp4", overlay_path="logo.png", output_path="watermarked.mp4")
ImageSequenceContext(input_pattern="frame_%04d.png", output_path="render.mp4")
```

## Modules

| Module | Responsibility |
| --- | --- |
| `streams.py` | Remove audio, extract video-only streams, replace audio, and add audio tracks. |
| `cutting.py` | Trim videos and extract fixed-duration segments. |
| `conversion.py` | Transcode video, convert to MP4, remux containers, optimize for web, compress, and set encoding options. |
| `geometry.py` | Resize, scale, crop, pad, set aspect ratios, rotate, and flip video. |
| `timing.py` | Change frame rate, adjust playback speed, reverse, loop, freeze frames, and apply fades. |
| `color.py` | Adjust color, convert to grayscale, invert, blur, sharpen, denoise, and add vignette effects. |
| `overlays.py` | Add text, watermarks, image overlays, and picture-in-picture layers. |
| `subtitles.py` | Burn subtitles, apply subtitle styles, embed subtitle streams, and remove subtitle streams. |
| `composition.py` | Concatenate videos, stack videos, build grids, and crossfade clips. |
| `frames.py` | Extract frames, generate thumbnails, detect scene frames, create video from image sequences, and export GIFs. |
| `metadata.py` | Strip metadata and write common container metadata fields. |
| `stabilization.py` | Detect stabilization transforms and apply video stabilization. |

## Usage Example

```python
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner
from kyrg.editor.video import TrimVideo

context = MediaContext(
    input_path="source.mp4",
    output_path="clip.mp4",
)

runner = CommandRunner()
operation = TrimVideo(
    context=context,
    runner=runner,
    start_time=10,
    duration=30,
)

operation.execute()
```

## Import Style

The package exports its public operation classes from `kyrg.editor.video`:

```python
from kyrg.editor.video import ResizeVideo, AddSubtitles, ReplaceVideoAudio
```

You can also import from the internal module when the category matters:

```python
from kyrg.editor.video.geometry import ResizeVideo
from kyrg.editor.video.subtitles import AddSubtitles
from kyrg.editor.video.streams import ReplaceVideoAudio
```

## Design Guidelines

- Keep one operation class per FFmpeg operation or domain-level workflow.
- Use `MediaContext` for single-input video operations.
- Use `MultiInputContext` for operations that compose multiple videos.
- Use dedicated contexts when the input shape is meaningful, such as video plus audio, subtitles, overlay asset, or image sequence.
- Keep FFmpeg command construction inside `build_command()`.
- Keep process execution inside `CommandRunner`.
- Prefer domain names such as `CenterCropVertical` or `ReplaceVideoAudio` over raw FFmpeg filter names.
- Use `filter_complex` for operations that combine multiple streams or require explicit stream mapping.

## Notes

These classes are command builders, not video processors themselves. They rely
on FFmpeg being available in the runtime environment. Some operations copy
streams without re-encoding, while others apply filters and therefore require
re-encoding. Stabilization is a two-step workflow: detect transforms first, then
apply those transforms to produce the stabilized video.
