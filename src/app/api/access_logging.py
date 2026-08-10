"""Access-log redaction for credentials carried by verification links.

Email verification tokens must be present in the link the user clicks, but
they must not be retained in HTTP access logs. This module redacts only the
token query parameter on the verification endpoint and leaves every other
access-log message unchanged.
"""

from __future__ import annotations

import logging
import re
from typing import Final


UVICORN_ACCESS_LOGGER: Final = "uvicorn.access"
REDACTED_VALUE: Final = "[REDACTED]"

_VERIFICATION_URL_PATTERN = re.compile(
    r"(?P<prefix>(?:https?://[^\s\"']+)?/v1/auth/verify-email\?)"
    r"(?P<query>[^\s\"']*)"
)
_TOKEN_QUERY_PARAMETER_PATTERN = re.compile(
    r"(?P<prefix>(?:^|&)token=)[^&\s\"']*"
)


class VerificationTokenAccessLogFilter(logging.Filter):
    """Remove verification-token values from rendered access-log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact the token while allowing the log record to be emitted."""

        try:
            rendered_message = record.getMessage()
        except (TypeError, ValueError):
            return True

        redacted_message = _redact_verification_token(rendered_message)

        if redacted_message != rendered_message:
            record.msg = redacted_message
            record.args = ()

        return True


def install_verification_token_access_log_filter() -> None:
    """Install the redaction filter once on Uvicorn's access logger."""

    access_logger = logging.getLogger(UVICORN_ACCESS_LOGGER)

    if not any(
        isinstance(log_filter, VerificationTokenAccessLogFilter)
        for log_filter in access_logger.filters
    ):
        access_logger.addFilter(VerificationTokenAccessLogFilter())


def _redact_verification_token(message: str) -> str:
    """Redact only ``token`` on the email-verification URL."""

    def replace_url(match: re.Match[str]) -> str:
        query = match.group("query")
        redacted_query = _TOKEN_QUERY_PARAMETER_PATTERN.sub(
            rf"\g<prefix>{REDACTED_VALUE}",
            query,
        )
        return f"{match.group('prefix')}{redacted_query}"

    return _VERIFICATION_URL_PATTERN.sub(replace_url, message)


__all__ = [
    "REDACTED_VALUE",
    "UVICORN_ACCESS_LOGGER",
    "VerificationTokenAccessLogFilter",
    "install_verification_token_access_log_filter",
]
