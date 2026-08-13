"""Synchronous HTTP boundary for the Kyrg Studio command-line client.

The default transport is ``requests``. It supports connection/read timeouts,
but it does not provide portable cooperative cancellation for an already
running request. A caller that needs cancellation can inject a compatible
transport with that capability in a later stage.
"""

from __future__ import annotations

import json
import mimetypes
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

import requests
from requests.cookies import CookieConflictError

from .config import CliConfig, CliSession, SessionStore
from .errors import (
    CliApiError,
    CliAuthenticationError,
    CliConflictError,
    CliError,
    CliNetworkError,
    CliNotFoundError,
    CliUsageError,
)

_PUBLIC_DETAIL_KEYS = frozenset(
    {
        "accepted_media_types",
        "allowed",
        "backend",
        "code",
        "driver",
        "error_type",
        "errors",
        "field",
        "input_type",
        "job_id",
        "max_upload_bytes",
        "message",
        "minimum",
        "operation",
        "path",
        "pipeline_type",
        "size_bytes",
        "status",
        "supported_values",
        "type",
    }
)
_PUBLIC_JOB_STATUSES = frozenset(
    {"pending", "uploaded", "running", "completed", "failed"}
)
_PUBLIC_ADAPTED_SCRIPT_FIELDS = frozenset(
    {
        "script",
        "sections",
        "hooks",
        "cta",
        "estimated_duration_seconds",
        "word_count",
        "voice_ready_text",
        "adaptation_notes",
    }
)


class HttpTransport(Protocol):
    """Minimal request contract required by ``KyrgApiClient``."""

    def request(
        self,
        *,
        method: str,
        url: str,
        json: Mapping[str, Any] | None = None,
        data: Mapping[str, str] | None = None,
        files: Mapping[str, tuple[str, Any, str]] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float,
    ) -> requests.Response:
        """Send one request and return a response-like object."""

        ...


class ApiClient(Protocol):
    """Public operations required by CLI commands."""

    def login(self, *, email: str, password: str) -> None:
        """Authenticate and persist a protected local session."""

        ...

    def logout(self) -> bool:
        """Revoke the remote session when possible and clear local state."""

        ...

    def submit_job(
        self,
        *,
        file_path: Path,
        request_metadata: Mapping[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Upload a media file and return the public submission response."""

        ...

    def get_job_status(self, job_id: int) -> dict[str, Any]:
        """Return the public status of one owned job."""

        ...

    def get_job_result(self, job_id: int) -> dict[str, Any]:
        """Return the public result of one completed owned job."""

        ...


class KyrgApiClient:
    """HTTP client that owns authentication headers and session rotation."""

    def __init__(
        self,
        config: CliConfig,
        *,
        session_store: SessionStore | None = None,
        transport: HttpTransport | None = None,
        http_session: HttpTransport | None = None,
    ) -> None:
        if transport is not None and http_session is not None:
            raise ValueError("Pass either transport or http_session, not both.")

        self.config = config
        self.session_store = session_store or SessionStore(config.session_file)
        self.transport = transport or http_session or requests.Session()
        self._session = self.session_store.load()

    def login(self, *, email: str, password: str) -> None:
        """Authenticate credentials and persist the API-issued cookies."""

        response = self._request_raw(
            "POST",
            "/auth/login",
            json_payload={"email": email, "password": password},
        )
        payload = self._successful_payload(response)
        self._store_authentication(response, payload, previous=None)

    def logout(self) -> bool:
        """Clear local credentials even when the remote logout is unavailable."""

        if self._session is None:
            self.session_store.clear()
            return True

        remote_logout_succeeded = False
        try:
            self._request_json(
                "POST",
                "/auth/logout",
                headers=self._csrf_headers(),
                authenticated=False,
            )
            remote_logout_succeeded = True
        except (CliApiError, CliAuthenticationError, CliNetworkError):
            # Local credentials are still removed below. The caller can tell
            # the difference through the boolean result without seeing a
            # response body or a token.
            remote_logout_succeeded = False
        finally:
            self._clear_session()

        return remote_logout_succeeded

    def submit_job(
        self,
        *,
        file_path: Path,
        request_metadata: Mapping[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Upload one media file using the API multipart contract."""

        normalized_key = idempotency_key.strip()
        content_type = mimetypes.guess_type(file_path.name)[0]
        if content_type is None:
            content_type = "application/octet-stream"

        for attempt in range(2):
            try:
                with file_path.open("rb") as file_handle:
                    response = self._request_raw(
                        "POST",
                        "/jobs",
                        data={
                            "request": json.dumps(
                                dict(request_metadata),
                                ensure_ascii=False,
                            )
                        },
                        files={
                            "file": (
                                file_path.name,
                                file_handle,
                                content_type,
                            )
                        },
                        headers={
                            "Authorization": self._authorization_header(),
                            "Idempotency-Key": normalized_key,
                        },
                    )
                return _public_submission(self._successful_payload(response))
            except CliAuthenticationError:
                if attempt == 1:
                    raise
                self.refresh_session()

        raise AssertionError("The upload request did not return a response.")

    def get_job_status(self, job_id: int) -> dict[str, Any]:
        """Fetch a public status, refreshing access authentication once."""

        _validate_job_id(job_id)
        payload = _require_payload(self._request_json("GET", f"/jobs/{job_id}"))
        return _public_status(payload)

    def get_job_result(self, job_id: int) -> dict[str, Any]:
        """Fetch a completed public result, refreshing access authentication once."""

        _validate_job_id(job_id)
        payload = _require_payload(self._request_json("GET", f"/jobs/{job_id}/result"))
        return _public_result(payload)

    def refresh_session(self) -> None:
        """Rotate the refresh session and replace the local access token."""

        previous = self._session
        if previous is None:
            raise CliAuthenticationError("No local login session was found.")

        try:
            response = self._request_raw(
                "POST",
                "/auth/refresh",
                headers=self._csrf_headers(),
            )
            payload = self._successful_payload(response)
            self._store_authentication(response, payload, previous=previous)
        except CliAuthenticationError:
            self._clear_session()
            raise

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_payload: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        authenticated: bool = True,
        retry_authentication: bool = True,
    ) -> dict[str, Any] | None:
        request_headers = dict(headers or {})
        if authenticated:
            request_headers["Authorization"] = self._authorization_header()

        response = self._request_raw(
            method,
            path,
            json_payload=json_payload,
            headers=request_headers,
        )

        try:
            return self._successful_payload(response)
        except CliAuthenticationError:
            if not authenticated or not retry_authentication:
                raise
            self.refresh_session()
            return self._request_json(
                method,
                path,
                json_payload=json_payload,
                headers=headers,
                authenticated=True,
                retry_authentication=False,
            )

    def _request_raw(
        self,
        method: str,
        path: str,
        *,
        json_payload: Mapping[str, Any] | None = None,
        data: Mapping[str, str] | None = None,
        files: Mapping[str, tuple[str, Any, str]] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> requests.Response:
        try:
            response = self.transport.request(
                method=method,
                url=f"{self.config.api_base_url}{path}",
                json=json_payload,
                data=data,
                files=files,
                headers=dict(headers or {}),
                timeout=self.config.timeout_seconds,
            )
        except requests.RequestException as error:
            raise CliNetworkError(
                "The Kyrg API could not be reached. Check the API URL and network connection."
            ) from error

        return response

    def _successful_payload(self, response: requests.Response) -> dict[str, Any]:
        if response.status_code >= 400:
            raise _api_error_from_response(response)

        if response.status_code == 204:
            return {}

        try:
            payload = response.json()
        except ValueError as error:
            raise CliApiError(
                "The API returned an invalid response.",
                status_code=response.status_code,
                code="invalid_api_response",
            ) from error

        if not isinstance(payload, dict):
            raise CliApiError(
                "The API returned an invalid response.",
                status_code=response.status_code,
                code="invalid_api_response",
            )

        return payload

    def _authorization_header(self) -> str:
        if self._session is None:
            raise CliAuthenticationError("You must log in before using this command.")
        return f"Bearer {self._session.access_token}"

    def _csrf_headers(self) -> dict[str, str]:
        if self._session is None:
            raise CliAuthenticationError("You must log in before using this command.")

        return {
            "Cookie": (
                f"{self.config.refresh_cookie_name}={self._session.refresh_token}; "
                f"{self.config.csrf_cookie_name}={self._session.csrf_token}"
            ),
            "X-CSRF-Token": self._session.csrf_token,
            "Origin": self.config.api_origin,
            "Referer": f"{self.config.api_origin}/",
        }

    def _store_authentication(
        self,
        response: requests.Response,
        payload: Mapping[str, Any],
        *,
        previous: CliSession | None,
    ) -> None:
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            raise CliAuthenticationError(
                "The API returned an invalid authentication response."
            )

        refresh_token = _response_cookie(
            response,
            self.config.refresh_cookie_name,
        ) or (previous.refresh_token if previous else None)
        csrf_token = _response_cookie(
            response,
            self.config.csrf_cookie_name,
        ) or (previous.csrf_token if previous else None)

        if not refresh_token or not csrf_token:
            raise CliAuthenticationError(
                "The API did not return the protected session cookies."
            )

        expires_at = payload.get("access_token_expires_at")
        if expires_at is not None and not isinstance(expires_at, str):
            expires_at = None

        self._session = CliSession(
            access_token=access_token,
            refresh_token=refresh_token,
            csrf_token=csrf_token,
            access_token_expires_at=expires_at,
        )
        self.session_store.save(self._session)

    def _clear_session(self) -> None:
        self._session = None
        self.session_store.clear()


def _api_error_from_response(response: requests.Response) -> CliError:
    payload: Mapping[str, Any] = {}
    try:
        decoded = response.json()
    except ValueError:
        decoded = None

    if isinstance(decoded, Mapping):
        payload = decoded

    code = payload.get("code")
    code = code.strip() if isinstance(code, str) and code.strip() else "api_error"
    step = payload.get("step")
    step = step.strip() if isinstance(step, str) and step.strip() else None
    details = _public_error_details(payload.get("details"))
    message = _public_error_message(code, response.status_code)

    if response.status_code in {401, 403}:
        return CliAuthenticationError(
            message,
            status_code=response.status_code,
            code=code,
        )
    if response.status_code == 404:
        return CliNotFoundError(
            message,
            status_code=response.status_code,
            code=code,
        )
    if response.status_code == 409:
        return CliConflictError(
            message,
            status_code=response.status_code,
            code=code,
        )

    return CliApiError(
        message,
        status_code=response.status_code,
        code=code,
        step=step,
        details=details,
    )


def _public_error_message(code: str, status_code: int) -> str:
    messages = {
        "invalid_credentials": "The email or password is incorrect.",
        "email_verification_required": "Verify your email before logging in.",
        "refresh_token_invalid": "Your session expired. Please log in again.",
        "invalid_token": "Your session is invalid. Please log in again.",
        "job_result_not_ready": "This job does not have a completed result yet.",
        "invalid_input": "The submitted information is invalid.",
        "unsupported_media_type": "This media format is not supported.",
        "upload_too_large": "The media file is larger than the allowed limit.",
        "pipeline_execution_failed": "The pipeline could not process this job.",
    }
    return messages.get(code, f"The API rejected the request (HTTP {status_code}).")


def _response_cookie(response: requests.Response, name: str) -> str | None:
    try:
        value = response.cookies.get(name)
    except CookieConflictError:
        value = None

    return value if isinstance(value, str) and value else None


def _public_error_details(value: object) -> dict[str, Any]:
    """Keep only the public error keys allowed by the API contract."""

    if not isinstance(value, Mapping):
        return {}

    return {
        str(key): _sanitize_public_value(item)
        for key, item in value.items()
        if str(key) in _PUBLIC_DETAIL_KEYS
    }


def _sanitize_public_value(value: object) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _sanitize_public_value(item)
            for key, item in value.items()
            if str(key) in _PUBLIC_DETAIL_KEYS
        }

    if isinstance(value, list):
        return [_sanitize_public_value(item) for item in value]

    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    return None


def _public_submission(payload: Mapping[str, Any]) -> dict[str, Any]:
    return _select_fields(
        payload,
        fields=("job_id", "run_id", "status", "current_step", "pipeline_type"),
    )


def _require_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        raise CliApiError(
            "The API returned an empty response.",
            status_code=502,
            code="invalid_api_response",
        )
    return payload


def _public_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    status = payload.get("status")
    if status not in _PUBLIC_JOB_STATUSES:
        raise CliApiError(
            "The API returned an invalid job status.",
            status_code=502,
            code="invalid_api_response",
        )

    public_status = _select_fields(
        payload,
        fields=(
            "job_id",
            "run_id",
            "pipeline_type",
            "status",
            "current_step",
            "created_at",
            "started_at",
            "finished_at",
            "execution_time_seconds",
        ),
    )

    error = payload.get("error")
    if isinstance(error, Mapping):
        public_error: dict[str, Any] = {}
        code = error.get("code")
        if isinstance(code, str) and code.strip():
            public_error["code"] = code.strip()
        if public_error:
            public_status["error"] = public_error

    return public_status


def _public_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("status") != "completed":
        raise CliApiError(
            "The API returned a result that is not completed.",
            status_code=502,
            code="invalid_api_response",
        )

    output = payload.get("output")
    if not isinstance(output, Mapping):
        raise CliApiError(
            "The API returned an invalid job result.",
            status_code=502,
            code="invalid_api_response",
        )

    public_result = _select_fields(
        payload,
        fields=("job_id", "run_id", "pipeline_type", "status"),
    )
    public_result["output"] = _public_result_output(output)
    return public_result


def _public_result_output(output: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only fields exposed by the backend's public result contract."""

    public_output: dict[str, Any] = {}

    copy_analysis = output.get("copy_analysis")
    if not isinstance(copy_analysis, Mapping):
        raise CliApiError(
            "The API returned an invalid job result.",
            status_code=502,
            code="invalid_api_response",
        )
    public_output["copy_analysis"] = dict(copy_analysis)

    transcription = output.get("transcription")
    if transcription is not None:
        if not isinstance(transcription, Mapping) or not isinstance(
            transcription.get("text"), str
        ):
            raise CliApiError(
                "The API returned an invalid transcription.",
                status_code=502,
                code="invalid_api_response",
            )
        public_output["transcription"] = _select_fields(
            transcription,
            fields=("language", "text"),
        )

    adapted_script = output.get("adapted_script")
    if adapted_script is not None:
        if not isinstance(adapted_script, Mapping):
            raise CliApiError(
                "The API returned an invalid adapted script.",
                status_code=502,
                code="invalid_api_response",
            )
        public_output["adapted_script"] = {
            field: adapted_script[field]
            for field in _PUBLIC_ADAPTED_SCRIPT_FIELDS
            if field in adapted_script
        }

    for field in (
        "validation",
        "missing_proofs",
        "token_usage",
        "execution_time_seconds",
    ):
        if field in output:
            public_output[field] = output[field]

    if not public_output:
        raise CliApiError(
            "The API returned an invalid job result.",
            status_code=502,
            code="invalid_api_response",
        )

    return public_output


def _validate_job_id(job_id: int) -> None:
    """Reject invalid identifiers before constructing an API URL."""

    if isinstance(job_id, bool) or not isinstance(job_id, int) or job_id <= 0:
        raise CliUsageError("JOB_ID must be a positive integer.")


def _select_fields(
    payload: Mapping[str, Any],
    *,
    fields: tuple[str, ...],
) -> dict[str, Any]:
    return {field: payload[field] for field in fields if field in payload}


__all__ = ["ApiClient", "HttpTransport", "KyrgApiClient"]
