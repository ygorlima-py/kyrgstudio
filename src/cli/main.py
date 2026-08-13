"""Command-line entry point for Kyrg Studio."""

from __future__ import annotations

import argparse
import getpass
import json
import math
import mimetypes
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import __version__
from .api_client import KyrgApiClient
from .config import CliConfig, resolve_config
from .errors import CliError, CliJobFailedError, CliUsageError
from .output import ConsoleOutput

CLI_DESCRIPTION = "Command-line client for Kyrg Studio."
MAX_LOCAL_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024
MAX_UPLOAD_FILENAME_LENGTH = 255
_MEDIA_SOURCE_TYPES: dict[str, str] = {
    ".mp4": "video",
    ".mov": "video",
    ".webm": "video",
    ".avi": "video",
    ".mp3": "audio",
    ".m4a": "audio",
    ".ogg": "audio",
    ".wav": "audio",
}
_REQUIRED_USER_PROFILE_FIELDS = (
    "product_or_solution",
    "target_audience",
    "core_problem",
    "core_desire",
    "main_promise",
    "call_to_action",
    "desired_duration",
)
_OPTIONAL_USER_PROFILE_TEXT_FIELDS = (
    "unique_mechanism",
    "offer_details",
    "tone",
    "target_language",
    "platform",
)
_USER_PROFILE_LIST_FIELDS = (
    "benefits",
    "objections",
    "proof_assets",
    "restrictions",
)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create the offline parser used by the ``kyrg`` executable."""

    parser = argparse.ArgumentParser(
        prog="kyrg",
        description=CLI_DESCRIPTION,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="show the installed Kyrg Studio version and exit",
    )
    parser.add_argument(
        "--api-url",
        help="API base URL; can also be set with KYRG_API_URL",
    )
    parser.add_argument(
        "--session-file",
        type=Path,
        help="local session file; can also be set with KYRG_SESSION_FILE",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        help="HTTP timeout in seconds; can also be set with KYRG_TIMEOUT_SECONDS",
    )
    parser.add_argument(
        "--output",
        choices=("human", "json"),
        default="human",
        help="output format (default: human)",
    )

    commands = parser.add_subparsers(dest="command", metavar="COMMAND")

    login_parser = commands.add_parser("login", help="log in to Kyrg Studio")
    login_parser.add_argument("--email", help="account email")

    commands.add_parser("logout", help="log out and clear the local session")

    for command_name, help_text in (
        ("analyze", "analyze a sales video or audio file"),
        ("adapt", "adapt a sales reference to an offer profile"),
    ):
        command_parser = commands.add_parser(command_name, help=help_text)
        command_parser.add_argument("file", type=Path, help="video or audio file")
        command_parser.add_argument(
            "--source-type",
            choices=("video", "audio"),
            help="media type; inferred from the file extension when omitted",
        )
        command_parser.add_argument("--language", help="source language")
        command_parser.add_argument(
            "--need-correction",
            action="store_true",
            help="request transcription correction",
        )
        command_parser.add_argument(
            "--idempotency-key",
            help="reuse a key when safely retrying the same submission",
        )
        if command_name == "adapt":
            command_parser.add_argument(
                "--profile",
                type=Path,
                help=(
                    "JSON file containing the public user_profile object; "
                    "when omitted, required fields are requested interactively"
                ),
            )

    status_parser = commands.add_parser("status", help="show a job status")
    status_parser.add_argument("job_id", type=_positive_job_id)

    result_parser = commands.add_parser("result", help="show a completed job result")
    result_parser.add_argument("job_id", type=_positive_job_id)

    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """Run one CLI command and return its documented process exit code."""

    parser = create_argument_parser()
    parsed_arguments = parser.parse_args(arguments)

    if parsed_arguments.command is None:
        parser.print_help()
        return 0

    output = ConsoleOutput(parsed_arguments.output)

    try:
        config = _create_config(parsed_arguments)
        client = KyrgApiClient(config)
        result = _run_command(parsed_arguments, client)
    except KeyboardInterrupt:
        output.write_message("Operation cancelled.")
        return 130
    except CliError as error:
        output.write_error(error)
        return error.exit_code
    except (EOFError, OSError, ValueError) as error:
        cli_error = CliUsageError(f"Invalid command input: {error}")
        output.write_error(cli_error)
        return cli_error.exit_code

    if result is not None:
        if parsed_arguments.command == "status":
            output.write_job_status(result)
        elif parsed_arguments.command == "result":
            output.write_job_result(result)
        else:
            output.write_data(result)

        if parsed_arguments.command == "status" and result.get("status") == "failed":
            return CliJobFailedError.exit_code

    return 0


def _run_command(
    arguments: argparse.Namespace,
    client: KyrgApiClient,
) -> dict[str, Any] | None:
    command = arguments.command

    if command == "login":
        email = arguments.email or input("Email: ").strip()
        password = getpass.getpass("Password: ")
        if not email or not password:
            raise CliUsageError("Email and password are required.")
        client.login(email=email, password=password)
        return {
            "status": "logged_in",
            "message": "Login successful.",
        }

    if command == "logout":
        remote_logout = client.logout()
        return {
            "status": "logged_out",
            "message": (
                "Logged out successfully."
                if remote_logout
                else "Local session cleared; the API could not be reached."
            ),
            "remote_logout": remote_logout,
        }

    if command in {"analyze", "adapt"}:
        return _submit_job(arguments, client)

    if command == "status":
        return client.get_job_status(arguments.job_id)

    if command == "result":
        return client.get_job_result(arguments.job_id)

    raise CliUsageError(f"Unknown command: {command}")


def _submit_job(
    arguments: argparse.Namespace,
    client: KyrgApiClient,
) -> dict[str, Any]:
    file_path = arguments.file.expanduser()
    source_type = _validate_media_file(
        file_path,
        requested_source_type=arguments.source_type,
    )
    metadata: dict[str, Any] = {
        "pipeline_type": "copy_adaptation"
        if arguments.command == "adapt"
        else "copy_analysis",
        "source_type": source_type,
        "need_correction": arguments.need_correction,
    }

    if arguments.language:
        metadata["language"] = arguments.language

    if arguments.command == "adapt":
        metadata["user_profile"] = _load_or_prompt_user_profile(arguments.profile)

    return client.submit_job(
        file_path=file_path,
        request_metadata=metadata,
        idempotency_key=(arguments.idempotency_key or str(uuid.uuid4())),
    )


def _read_user_profile(path: Path) -> Mapping[str, Any]:
    path = path.expanduser()

    if not path.is_file():
        raise CliUsageError(f"User profile file does not exist: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CliUsageError(f"User profile JSON could not be read: {path}") from error

    if not isinstance(payload, Mapping):
        raise CliUsageError("The user profile JSON must contain an object.")

    return _validate_user_profile(payload)


def _load_or_prompt_user_profile(path: Path | None) -> Mapping[str, Any]:
    """Load a profile file or collect the required profile fields interactively."""

    if path is not None:
        return _read_user_profile(path)

    profile: dict[str, Any] = {}
    for field in _REQUIRED_USER_PROFILE_FIELDS[:-1]:
        profile[field] = input(f"{field}: ").strip()

    duration_text = input("desired_duration (minutes): ").strip()
    try:
        profile["desired_duration"] = float(duration_text)
    except ValueError as error:
        raise CliUsageError(
            "The user profile field 'desired_duration' must be a positive number."
        ) from error

    return _validate_user_profile(profile)


def _validate_user_profile(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate the public fields accepted by ``UserProfileOutput``."""

    missing_fields = [
        field for field in _REQUIRED_USER_PROFILE_FIELDS if field not in payload
    ]
    if missing_fields:
        raise CliUsageError(
            "The user profile is missing required fields: " + ", ".join(missing_fields)
        )

    for field in _REQUIRED_USER_PROFILE_FIELDS[:-1]:
        value = payload[field]
        if not isinstance(value, str) or not value.strip():
            raise CliUsageError(
                f"The user profile field '{field}' must be a non-empty string."
            )

    desired_duration = payload["desired_duration"]
    if (
        isinstance(desired_duration, bool)
        or not isinstance(desired_duration, (int, float))
        or not math.isfinite(float(desired_duration))
        or desired_duration <= 0
    ):
        raise CliUsageError(
            "The user profile field 'desired_duration' must be a positive number."
        )

    for field in _OPTIONAL_USER_PROFILE_TEXT_FIELDS:
        value = payload.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise CliUsageError(
                f"The user profile field '{field}' must be text or null."
            )

    for field in _USER_PROFILE_LIST_FIELDS:
        value = payload.get(field)
        if value is None:
            continue
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            raise CliUsageError(
                f"The user profile field '{field}' must be a list of non-empty strings."
            )

    return dict(payload)


def _validate_media_file(
    path: Path,
    *,
    requested_source_type: str | None,
) -> str:
    """Validate a local media file before opening the multipart request."""

    if not path.is_file():
        raise CliUsageError(f"Media file does not exist: {path}")

    filename = path.name.strip()
    if not filename or len(filename) > MAX_UPLOAD_FILENAME_LENGTH:
        raise CliUsageError("The media filename is invalid or too long.")
    if any(ord(character) < 32 for character in filename):
        raise CliUsageError("The media filename contains control characters.")

    source_type = _infer_source_type(path)
    if requested_source_type is not None and requested_source_type != source_type:
        raise CliUsageError(
            f"The file extension indicates a {source_type} file; "
            f"it cannot be submitted as {requested_source_type}."
        )

    try:
        size_bytes = path.stat().st_size
    except OSError as error:
        raise CliUsageError("The media file size could not be read.") from error

    if size_bytes <= 0:
        raise CliUsageError("The media file is empty.")
    if size_bytes > MAX_LOCAL_UPLOAD_BYTES:
        raise CliUsageError("The media file exceeds the local upload size limit.")

    return source_type


def _infer_source_type(path: Path) -> str:
    suffix = path.suffix.lower()
    source_type = _MEDIA_SOURCE_TYPES.get(suffix)
    if source_type is None:
        content_type = mimetypes.guess_type(path.name)[0] or ""
        if content_type.startswith("video/"):
            return "video"
        if content_type.startswith("audio/"):
            return "audio"
        raise CliUsageError(
            "Could not infer whether the file is video or audio. Use --source-type."
        )
    return source_type


def _create_config(arguments: argparse.Namespace) -> CliConfig:
    config = resolve_config(
        api_base_url=arguments.api_url,
        timeout_seconds=arguments.timeout,
    )
    if arguments.session_file is None:
        return config
    return CliConfig(
        api_base_url=config.api_base_url,
        session_file=arguments.session_file.expanduser(),
        timeout_seconds=config.timeout_seconds,
        refresh_cookie_name=config.refresh_cookie_name,
        csrf_cookie_name=config.csrf_cookie_name,
    )


def _positive_job_id(value: str) -> int:
    try:
        job_id = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "JOB_ID must be a positive integer."
        ) from error

    if job_id <= 0:
        raise argparse.ArgumentTypeError("JOB_ID must be a positive integer.")
    return job_id


if __name__ == "__main__":
    raise SystemExit(main())
