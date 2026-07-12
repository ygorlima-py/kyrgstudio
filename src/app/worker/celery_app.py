"""Celery application configuration for background pipeline workers.

This module configures message delivery only. Importing it creates the Celery
application required by the worker CLI, but never executes a workflow or opens
a database connection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from celery import Celery

from app.errors import ProviderConfigError
from app.settings import AppSettings, load_settings


CELERY_APP_NAME: Final = "kyrgstudio"
PIPELINE_TASK_MODULE: Final = "app.worker.tasks"
PIPELINE_TASK_NAME: Final = "app.worker.run_pipeline_job"


@dataclass(frozen=True)
class CeleryWorkerConfig:
    """Validated settings used to configure the Celery worker."""

    broker_url: str
    queue_name: str
    soft_time_limit_seconds: int
    time_limit_seconds: int

    @classmethod
    def from_settings(cls, settings: AppSettings) -> CeleryWorkerConfig:
        """Build and validate worker configuration from application settings."""

        broker_url = _required_text(
            settings.celery_broker_url,
            field="celery_broker_url",
        )
        queue_name = _required_text(
            settings.celery_queue_name,
            field="celery_queue_name",
        )
        soft_time_limit = _positive_integer(
            settings.celery_task_soft_time_limit_seconds,
            field="celery_task_soft_time_limit_seconds",
        )
        time_limit = _positive_integer(
            settings.celery_task_time_limit_seconds,
            field="celery_task_time_limit_seconds",
        )

        if time_limit <= soft_time_limit:
            raise _configuration_error(
                "Celery hard time limit must be greater than its soft time limit.",
                field="celery_task_time_limit_seconds",
            )

        return cls(
            broker_url=broker_url,
            queue_name=queue_name,
            soft_time_limit_seconds=soft_time_limit,
            time_limit_seconds=time_limit,
        )


def create_celery_app(settings: AppSettings | None = None) -> Celery:
    """Create the Celery app without executing jobs or application workflows."""

    worker_config = CeleryWorkerConfig.from_settings(
        settings if settings is not None else load_settings()
    )
    app = Celery(
        CELERY_APP_NAME,
        broker=worker_config.broker_url,
        include=[PIPELINE_TASK_MODULE],
    )

    app.conf.update(
        accept_content=["json"],
        task_serializer="json",
        result_serializer="json",
        task_ignore_result=True,
        task_store_errors_even_if_ignored=False,
        task_track_started=False,
        task_default_queue=worker_config.queue_name,
        task_routes={
            PIPELINE_TASK_NAME: {"queue": worker_config.queue_name},
        },
        task_soft_time_limit=worker_config.soft_time_limit_seconds,
        task_time_limit=worker_config.time_limit_seconds,
        # Late acknowledgement requires recovery for abandoned running jobs.
        task_acks_late=False,
        task_reject_on_worker_lost=False,
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
        enable_utc=True,
        timezone="UTC",
    )

    return app


def _required_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _configuration_error(
            f"Celery setting '{field}' is required.",
            field=field,
        )

    return value.strip()


def _positive_integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise _configuration_error(
            f"Celery setting '{field}' must be a positive integer.",
            field=field,
        )

    return value


def _configuration_error(message: str, *, field: str) -> ProviderConfigError:
    return ProviderConfigError(
        technical_message=message,
        step="configuring_worker",
        details={"field": field},
    )


# Celery's CLI imports this object; construction only reads configuration.
celery_app = create_celery_app()


__all__ = [
    "CELERY_APP_NAME",
    "PIPELINE_TASK_MODULE",
    "PIPELINE_TASK_NAME",
    "CeleryWorkerConfig",
    "celery_app",
    "create_celery_app",
]
