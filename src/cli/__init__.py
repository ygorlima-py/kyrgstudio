"""Public package for the Kyrg Studio command-line client.

The CLI is intentionally isolated from ``app.api``, ``app.auth``,
``app.store``, and ``app.worker``. Future commands will communicate with the
public HTTP API instead of importing backend implementation details.
"""

from importlib.metadata import PackageNotFoundError, version

PACKAGE_NAME = "kyrgstudio"
_FALLBACK_VERSION = "0.1.0"


def get_version() -> str:
    """Return the installed project version, with a source-tree fallback."""

    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return _FALLBACK_VERSION


__version__ = get_version()

__all__ = ["PACKAGE_NAME", "__version__", "get_version"]
