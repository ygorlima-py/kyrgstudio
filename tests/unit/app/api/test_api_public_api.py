"""Unit tests for the stable public API package contract."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import app.api as api
from app.api.main import create_app


def test_public_api_exports_expected_symbols() -> None:
    """Expose only the FastAPI application factory from the package root."""

    assert api.create_app is create_app
    assert api.__all__ == ["create_app"]


def test_public_api_does_not_export_internal_routers_or_dependencies() -> None:
    """Keep routers, resources, and request dependencies package-internal."""

    internal_symbols = {
        "app",
        "api_lifespan",
        "auth_router",
        "get_current_user",
        "get_job_store",
        "get_pipeline_service",
        "get_queue",
        "get_session",
        "get_session_factory",
        "get_settings",
        "get_storage",
        "health_router",
        "jobs_router",
        "router",
    }

    assert internal_symbols.isdisjoint(api.__all__)
    assert all(not hasattr(api, symbol) for symbol in internal_symbols)


def test_public_api_imports_without_circular_dependencies() -> None:
    """Import the package from a clean interpreter without import cycles."""

    import_script = textwrap.dedent(
        """
        import app.api
        from app.api import create_app
        from app.api.main import create_app as concrete_create_app

        assert callable(create_app)
        assert create_app is concrete_create_app
        assert app.api.__all__ == ["create_app"]
        """
    )

    completed_process = subprocess.run(
        [sys.executable, "-c", import_script],
        cwd=Path(__file__).resolve().parents[4],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed_process.returncode == 0, completed_process.stderr
