"""Unit tests for Celery worker application configuration."""

from __future__ import annotations

import importlib
import sys
from dataclasses import replace
from types import ModuleType

import pytest
from celery import Celery

from app.errors import ProviderConfigError
from app.settings import load_settings


def test_importing_celery_app_does_not_execute_workflows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Importing Celery configuration should not import or execute worker tasks."""

    monkeypatch.delitem(sys.modules, "app.worker.celery_app", raising=False)
    monkeypatch.delitem(sys.modules, "app.worker.tasks", raising=False)

    module = importlib.import_module("app.worker.celery_app")

    assert isinstance(module, ModuleType)
    assert isinstance(module.celery_app, Celery)
    assert "app.worker.tasks" not in sys.modules


def test_rejects_missing_celery_broker_url() -> None:
    """A blank broker setting should raise a controlled configuration error."""

    module = importlib.import_module("app.worker.celery_app")
    settings = replace(load_settings(), celery_broker_url="   ")

    with pytest.raises(ProviderConfigError) as error:
        module.create_celery_app(settings)

    assert error.value.step == "configuring_worker"
    assert error.value.details == {"field": "celery_broker_url"}
