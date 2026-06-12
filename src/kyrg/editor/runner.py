"""Command execution utilities for editor operations.

This module defines the execution boundary used by audio and video command
builders. Editor classes are responsible for producing command arguments, while
the runner is responsible for invoking the underlying process.

Keeping process execution centralized makes the editor layer easier to test and
leaves a single extension point for future concerns such as logging, error
handling, telemetry, retries, or alternative execution backends.
"""

import subprocess


class CommandRunner:
    """Default subprocess-backed command runner.

    The runner receives a fully constructed command as an argument list and
    delegates execution to ``subprocess.run``. It intentionally does not know
    about FFmpeg, audio, video, or transcription semantics; those concerns stay
    inside the command builder classes.
    """

    def run(
        self,
        command: list[str],
        *,
        check: bool = False,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[bytes]:
        """Execute a command and return the completed process.

        Args:
            command: Command arguments in ``subprocess.run`` list form. The
                first item is expected to be the executable name, followed by
                its arguments.
            check: When ``True``, raise ``subprocess.CalledProcessError`` if
                the command exits with a non-zero status.

        Returns:
            The ``subprocess.CompletedProcess`` object returned by
            ``subprocess.run``.
        """

        return subprocess.run(command, check=check, capture_output=capture_output)
