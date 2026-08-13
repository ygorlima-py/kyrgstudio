"""Safe terminal output for human users and automation."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from typing import Any, Literal, Protocol, TextIO

from .errors import CliError

OutputFormat = Literal["human", "json"]
_SENSITIVE_OUTPUT_KEYS = frozenset(
    {
        "access_token",
        "audio_path",
        "cookie",
        "cookies",
        "csrf_token",
        "input_json",
        "input_path",
        "output_json",
        "password",
        "raw_response",
        "refresh_token",
        "secret",
        "storage_path",
        "token",
        "traceback",
    }
)


class OutputWriter(Protocol):
    """Write public command results without interpreting private data."""

    def write_data(self, value: object) -> None:
        """Write one public result."""

    def write_message(self, message: str) -> None:
        """Write one public informational message."""

    def write_error(self, error: CliError) -> None:
        """Write one expected public error."""


class ConsoleOutput:
    """Format command output consistently for a terminal or a pipe."""

    def __init__(
        self,
        output_format: OutputFormat = "human",
        *,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
    ) -> None:
        self.output_format = output_format
        self.stdout = sys.stdout if stdout is None else stdout
        self.stderr = sys.stderr if stderr is None else stderr

    def write_data(self, value: object) -> None:
        """Write data as JSON or as a readable key/value view."""

        safe_value = _sanitize_output_value(value)

        if self.output_format == "json":
            self.stdout.write(json.dumps(safe_value, ensure_ascii=False, indent=2))
            self.stdout.write("\n")
            return

        self.stdout.write(format_human(safe_value))
        self.stdout.write("\n")

    def write_message(self, message: str) -> None:
        """Write a human-readable informational message."""

        self.stdout.write(_sanitize_terminal_text(message))
        self.stdout.write("\n")

    def write_error(self, error: CliError) -> None:
        """Write only the public message and API code for an expected error."""

        message = _sanitize_terminal_text(str(error))
        code = _public_error_code(error)

        if self.output_format == "json":
            payload = {"error": message}
            if code is not None:
                payload["code"] = code
            self.stderr.write(json.dumps(payload, ensure_ascii=False))
            self.stderr.write("\n")
            return

        prefix = f"Error [{code}]" if code is not None else "Error"
        self.stderr.write(f"{prefix}: {message}\n")

    def write_job_status(self, status: Mapping[str, Any]) -> None:
        """Write a status response with a clear lifecycle label."""

        safe_status = _sanitize_output_value(status)
        if not isinstance(safe_status, Mapping):
            safe_status = {}

        if self.output_format == "json":
            self.write_data(safe_status)
            return

        lines = [
            f"Job #{safe_status.get('job_id', '-')}",
            f"Pipeline: {_pipeline_label(safe_status.get('pipeline_type'))}",
            f"Status: {_job_status_label(safe_status.get('status'))}",
        ]
        current_step = safe_status.get("current_step")
        if isinstance(current_step, str) and current_step.strip():
            lines.append(f"Current step: {current_step}")
        error = safe_status.get("error")
        if isinstance(error, Mapping):
            error_code = error.get("code")
            if isinstance(error_code, str) and error_code.strip():
                lines.append(f"Failure code: {error_code}")
        self.stdout.write("\n".join(lines))
        self.stdout.write("\n")

    def write_job_result(self, result: Mapping[str, Any]) -> None:
        """Write a public result as readable sections instead of raw JSON."""

        safe_result = _sanitize_output_value(result)
        if not isinstance(safe_result, Mapping):
            safe_result = {}

        if self.output_format == "json":
            self.write_data(safe_result)
            return

        lines = [
            f"Job #{safe_result.get('job_id', '-')}",
            f"Pipeline: {_pipeline_label(safe_result.get('pipeline_type'))}",
            f"Status: {_job_status_label(safe_result.get('status'))}",
            "Result:",
        ]
        result_output = safe_result.get("output")
        lines.extend(_format_lines(result_output, indent=2))
        self.stdout.write("\n".join(lines))
        self.stdout.write("\n")


def format_human(value: object, *, indent: int = 0) -> str:
    """Format public mappings and sequences without dumping raw JSON."""

    return "\n".join(_format_lines(_sanitize_output_value(value), indent=indent))


def _sanitize_output_value(value: object) -> object:
    """Remove known secret and internal fields before formatting output."""

    if isinstance(value, Mapping):
        return {
            str(key): _sanitize_output_value(item)
            for key, item in value.items()
            if str(key).lower() not in _SENSITIVE_OUTPUT_KEYS
        }

    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [_sanitize_output_value(item) for item in value]

    if value is None or isinstance(value, (bool, int, float, str)):
        return _sanitize_terminal_text(value) if isinstance(value, str) else value

    return None


def _sanitize_terminal_text(value: str) -> str:
    """Strip terminal control characters while preserving normal text."""

    return "".join(
        character
        for character in value
        if character in {"\n", "\t"} or ord(character) >= 32
    )


def _public_error_code(error: CliError) -> str | None:
    code = getattr(error, "code", None)
    return code.strip() if isinstance(code, str) and code.strip() else None


def _format_lines(value: object, *, indent: int) -> list[str]:
    prefix = " " * indent

    if isinstance(value, Mapping):
        lines: list[str] = []
        for key, item in value.items():
            label = _humanize_key(str(key))
            if isinstance(item, (Mapping, Sequence)) and not isinstance(
                item, (str, bytes, bytearray)
            ):
                lines.append(f"{prefix}{label}:")
                lines.extend(_format_lines(item, indent=indent + 2))
            else:
                lines.append(f"{prefix}{label}: {_format_scalar(item)}")
        return lines

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        lines = []
        for item in value:
            if isinstance(item, (Mapping, Sequence)) and not isinstance(
                item, (str, bytes, bytearray)
            ):
                lines.append(f"{prefix}-")
                lines.extend(_format_lines(item, indent=indent + 2))
            else:
                lines.append(f"{prefix}- {_format_scalar(item)}")
        return lines

    return [f"{prefix}{_format_scalar(value)}"]


def _format_scalar(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def _humanize_key(value: str) -> str:
    return value.replace("_", " ").strip().capitalize()


def _job_status_label(value: object) -> str:
    labels = {
        "pending": "Pending",
        "uploaded": "Uploaded",
        "running": "Running",
        "completed": "Completed",
        "failed": "Failed",
    }
    label_key = value if isinstance(value, str) else str(value)
    return labels.get(label_key, _humanize_key(label_key))


def _pipeline_label(value: object) -> str:
    labels = {
        "copy_analysis": "Copy analysis",
        "copy_adaptation": "Copy adaptation",
    }
    label_key = value if isinstance(value, str) else str(value)
    return labels.get(label_key, _humanize_key(label_key))


__all__ = ["ConsoleOutput", "OutputFormat", "OutputWriter", "format_human"]
