"""Public router objects composed by the FastAPI application factory."""

from app.api.routers.auth import router as auth_router
from app.api.routers.health import router as health_router
from app.api.routers.jobs import router as jobs_router


__all__ = [
    "auth_router",
    "health_router",
    "jobs_router",
]
