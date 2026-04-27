from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID, uuid4

from .task_storage import TaskRecord


ALLOWED_CATEGORIES = frozenset(
    {
        "PROFESSIONAL",
        "PERSONAL",
        "HEALTH",
        "SPIRITUAL",
        "ADMIN",
        "FINANCE",
    }
)

DEFAULT_TASK_STATE = "BACKLOG"
DEFAULT_TASK_PRIORITY = "MEDIUM"


class TaskStorageProtocol(Protocol):
    def insert_task(self, task: TaskRecord) -> None:
        ...


@dataclass
class TaskModule:
    storage: TaskStorageProtocol
    now_factory: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    uuid_factory: Callable[[], UUID] = uuid4

    def create_task(self, title: str, category: str) -> TaskRecord:
        normalized_title = title.strip()
        normalized_category = category.strip().upper()

        if not normalized_title:
            raise ValueError("title is required")
        if not normalized_category:
            raise ValueError("category is required")
        if normalized_category not in ALLOWED_CATEGORIES:
            raise ValueError(f"unsupported category: {category}")

        timestamp = self.now_factory()
        task = TaskRecord(
            id=self.uuid_factory(),
            title=normalized_title,
            category=normalized_category,
            state=DEFAULT_TASK_STATE,
            priority=DEFAULT_TASK_PRIORITY,
            deadline=None,
            next_action=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.storage.insert_task(task)
        return task
