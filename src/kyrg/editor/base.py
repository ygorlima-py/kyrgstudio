"""Base contracts for editor command operations.

This module defines the common abstraction used by audio and video editor
operations. Concrete editors receive a context object, build a command-line
invocation, and delegate process execution to a ``CommandRunner``.

The base class keeps command construction and execution separate. This makes
operation classes easier to test, keeps FFmpeg-specific behavior localized in
each command builder, and centralizes process execution behind the runner.
"""

from abc import ABC, abstractmethod
import subprocess
from typing import Generic, TypeVar

from kyrg.editor.runner import CommandRunner

ContextT = TypeVar("ContextT")


class BaseEditor(ABC, Generic[ContextT]):
    """Abstract base class for command-backed editor operations.

    ``BaseEditor`` provides the shared execution flow for editor operations:
    store the operation context, ask the concrete class to build a command, and
    execute that command through the configured runner.

    Type Args:
        ContextT: Context object type required by the concrete operation.
    """

    def __init__(self, context: ContextT, runner: CommandRunner) -> None:
        """Initialize an editor operation.

        Args:
            context: Operation-specific input/output data.
            runner: Command runner responsible for process execution.
        """

        self.context = context
        self.runner = runner

    @abstractmethod
    def build_command(self) -> list[str]:
        """Build the command-line arguments for this operation.

        Returns:
            A command represented as a list of arguments suitable for
            ``subprocess.run``.
        """

        ...

    def execute(self) -> subprocess.CompletedProcess[bytes]:
        """Build and execute this operation's command.

        Returns:
            The completed process returned by the configured command runner.

        Raises:
            subprocess.CalledProcessError: If the command exits with a non-zero
                status and the runner honors ``check=True``.
        """

        command = self.build_command()
        return self.runner.run(command, check=True)
