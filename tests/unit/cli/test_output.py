"""Unit tests for safe CLI output in terminals, pipes, and CI."""

from __future__ import annotations

import io
import json
from pathlib import Path

from cli.errors import CliApiError, CliError
from cli.output import ConsoleOutput, format_human


def test_human_success_goes_to_stdout_and_stays_readable() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    output = ConsoleOutput(stdout=stdout, stderr=stderr)

    output.write_data({"job_id": 7, "status": "running"})

    assert stdout.getvalue() == "Job id: 7\nStatus: running\n"
    assert stderr.getvalue() == ""


def test_json_success_is_machine_readable_and_goes_to_stdout() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    output = ConsoleOutput("json", stdout=stdout, stderr=stderr)

    output.write_data({"job_id": 7, "status": "completed"})

    assert json.loads(stdout.getvalue()) == {
        "job_id": 7,
        "status": "completed",
    }
    assert stderr.getvalue() == ""


def test_human_output_has_no_ansi_color_codes_for_terminal_or_ci() -> None:
    stdout = io.StringIO()
    output = ConsoleOutput(stdout=stdout, stderr=io.StringIO())

    output.write_data({"status": "running", "message": "Ready"})

    assert "\x1b[" not in stdout.getvalue()


def test_output_can_be_redirected_to_a_file_without_terminal_assumptions(
    tmp_path: Path,
) -> None:
    redirected_output = tmp_path / "kyrg-output.txt"

    with redirected_output.open("w+", encoding="utf-8") as stream:
        output = ConsoleOutput(stdout=stream, stderr=io.StringIO())
        output.write_message("Job submitted.")
        stream.flush()

    assert redirected_output.read_text(encoding="utf-8") == "Job submitted.\n"


def test_human_error_goes_only_to_stderr_and_keeps_public_code() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    output = ConsoleOutput(stdout=stdout, stderr=stderr)
    error = CliApiError(
        "The submitted information is invalid.",
        status_code=422,
        code="invalid_input",
        details={"password": "must not be printed"},
    )

    output.write_error(error)

    assert stdout.getvalue() == ""
    assert stderr.getvalue() == (
        "Error [invalid_input]: The submitted information is invalid.\n"
    )
    assert "must not be printed" not in stderr.getvalue()


def test_json_error_goes_only_to_stderr_without_traceback_or_details() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    output = ConsoleOutput("json", stdout=stdout, stderr=stderr)
    error = CliApiError(
        "The API rejected the request.",
        status_code=503,
        code="pipeline_execution_failed",
        details={"traceback": "private traceback"},
    )

    output.write_error(error)

    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue()) == {
        "error": "The API rejected the request.",
        "code": "pipeline_execution_failed",
    }
    assert "traceback" not in stderr.getvalue()


def test_output_redacts_sensitive_and_internal_fields_in_both_formats() -> None:
    value = {
        "status": "completed",
        "access_token": "access-secret",
        "refresh_token": "refresh-secret",
        "storage_path": "/private/file.mp4",
        "output": {"public": "visible", "raw_response": "private"},
    }

    human_stdout = io.StringIO()
    ConsoleOutput(stdout=human_stdout, stderr=io.StringIO()).write_data(value)
    human_text = human_stdout.getvalue()
    assert "visible" in human_text
    assert "access-secret" not in human_text
    assert "refresh-secret" not in human_text
    assert "/private/file.mp4" not in human_text
    assert "private" not in human_text

    json_stdout = io.StringIO()
    ConsoleOutput("json", stdout=json_stdout, stderr=io.StringIO()).write_data(value)
    json_text = json_stdout.getvalue()
    assert json.loads(json_text) == {
        "status": "completed",
        "output": {"public": "visible"},
    }


def test_format_human_removes_terminal_escape_characters() -> None:
    formatted = format_human({"message": "safe\x1b[31m text"})

    assert formatted == "Message: safe[31m text"


def test_error_without_api_code_remains_short_and_public() -> None:
    stderr = io.StringIO()
    output = ConsoleOutput(stderr=stderr, stdout=io.StringIO())

    output.write_error(CliError("The network is unavailable."))

    assert stderr.getvalue() == "Error: The network is unavailable.\n"
