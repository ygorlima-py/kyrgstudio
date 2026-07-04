from abc import ABC, abstractmethod
from typing import Any

class JobStoreBase(ABC):
    @abstractmethod
    async def create_job(self, payload: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def mark_uploaded(self, job_id: int, payload: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def mark_running(self, job_id: int, step: str) -> Any:
        ...

    @abstractmethod
    async def mark_step_completed(
        self,
        job_id: int,
        step: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        ...

    @abstractmethod
    async def mark_completed(self, job_id: int, output: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def mark_failed(self, job_id: int, error: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def get_job(self, job_id: int) -> Any:
        ...

    @abstractmethod
    async def get_job_by_run_id(self, run_id: str) -> Any:
        ...

    @abstractmethod
    async def list_user_jobs(
        self,
        user_id: int,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Any]:
        ...
        
class UserStoreBase(ABC):
    @abstractmethod
    async def create_user(self, payload: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def get_user(self, user_id: int) -> Any:
        ...

    @abstractmethod
    async def get_user_by_email(self, email: str) -> Any:
        ...

    @abstractmethod
    async def get_user_by_google_sub(self, google_sub: str) -> Any:
        ...
        
class BillingStoreBase(ABC):
    @abstractmethod
    async def upsert_subscription(self, payload: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def record_billing_event(self, payload: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def get_subscription_by_user_id(self, user_id: int) -> Any:
        ...