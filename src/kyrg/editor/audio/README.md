# Audio Editor Operations

This package contains FFmpeg-backed audio operations used by the editor layer.
Each operation is implemented as a small command builder: it receives a context,
stores optional configuration, builds an FFmpeg command, and delegates execution
to the shared command runner.

The package is organized by audio responsibility rather than by FFmpeg filter
name. This keeps the public API closer to the domain language used by the
application: conversion, cleanup, dynamics, filtering, timing, mixing, analysis,
and creative effects.

## Architecture

Audio operations follow the same structure:

```python
operation = SomeAudioOperation(context, runner, ...)
command = operation.build_command()
operation.execute()
```

The operation classes do not execute FFmpeg directly. Execution is delegated to
`CommandRunner`, which keeps command construction separate from process
execution and makes the operation classes easier to test.

Most operations use `MediaContext`, which represents a single input and a single
output:

```python
MediaContext(input_path="input.wav", output_path="output.wav")
```

Operations that require multiple inputs use `MultiInputContext`:

```python
MultiInputContext(input_paths=["voice.wav", "music.wav"], output_path="mix.wav")
```

## Modules

| Module | Responsibility |
| --- | --- |
| `conversion.py` | Extract audio, convert formats, resample audio, change channels, and prepare speech-to-text audio. |
| `cleanup.py` | Remove or detect silence, reduce noise, repair clicks, and repair clipping. |
| `dynamics.py` | Adjust volume, normalize loudness, compress dynamic range, limit peaks, and gate low-level noise. |
| `filters.py` | Apply tonal filters such as high-pass, low-pass, band-pass, band-reject, and parametric EQ. |
| `timing.py` | Trim, delay, pad, loop, reverse, change tempo, fade, and crossfade audio. |
| `mixing.py` | Mix multiple inputs, concatenate audio, merge channels, pan, balance stereo, mix voice with music, and duck music under voice. |
| `analysis.py` | Build FFmpeg analysis commands for volume and detailed audio statistics. |
| `effects.py` | Apply creative effects such as echo, tremolo, vibrato, chorus, phaser, and bit crushing. |

## Usage Example

```python
from kyrg.editor.audio.cleanup import ReduceNoise
from kyrg.editor.context import MediaContext
from kyrg.editor.runner import CommandRunner

context = MediaContext(
    input_path="raw_voice.wav",
    output_path="clean_voice.wav",
)

runner = CommandRunner()
operation = ReduceNoise(
    context=context,
    runner=runner,
    noise_reduction=12,
    noise_floor=-50,
)

operation.execute()
```

## Design Guidelines

- Keep one operation class per FFmpeg operation or domain-level workflow.
- Use `MediaContext` for single-input operations.
- Use `MultiInputContext` for operations that combine or compare multiple audio inputs.
- Keep FFmpeg command construction inside `build_command()`.
- Keep process execution inside `CommandRunner`.
- Prefer clear domain names such as `ReduceNoise` or `MixVoiceWithMusic` over raw FFmpeg filter names.

## Notes

These classes are command builders, not audio processors themselves. They rely
on FFmpeg being available in the runtime environment. Some analysis operations
write their useful output to FFmpeg logs while using the `null` muxer as the
output target.
