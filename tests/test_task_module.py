from __future__ import annotations

import unittest
from datetime import datetime, timezone
from uuid import UUID

from lifeops import TaskModule, TaskRecord


class TaskModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.storage = CapturingTaskStorage()
        self.timestamp = datetime(2026, 4, 27, 15, 0, tzinfo=timezone.utc)
        self.task_id = UUID("99999999-1234-5678-1234-567812345678")
        self.module = TaskModule(
            storage=self.storage,
            now_factory=lambda: self.timestamp,
            uuid_factory=lambda: self.task_id,
        )

    def test_create_task_initializes_and_persists_task(self) -> None:
        task = self.module.create_task("Refine research question", "professional")

        self.assertEqual(
            task,
            TaskRecord(
                id=self.task_id,
                title="Refine research question",
                category="PROFESSIONAL",
                state="BACKLOG",
                priority="MEDIUM",
                deadline=None,
                next_action=None,
                created_at=self.timestamp,
                updated_at=self.timestamp,
            ),
        )
        self.assertEqual(self.storage.inserted_tasks, [task])

    def test_create_task_trims_title_and_normalizes_category(self) -> None:
        task = self.module.create_task("  Review roadmap  ", " admin ")

        self.assertEqual(task.title, "Review roadmap")
        self.assertEqual(task.category, "ADMIN")

    def test_create_task_requires_title(self) -> None:
        with self.assertRaisesRegex(ValueError, "title is required"):
            self.module.create_task("   ", "PROFESSIONAL")

    def test_create_task_requires_category(self) -> None:
        with self.assertRaisesRegex(ValueError, "category is required"):
            self.module.create_task("Refine research question", "   ")

    def test_create_task_rejects_unsupported_category(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported category"):
            self.module.create_task("Refine research question", "HOBBY")


class CapturingTaskStorage:
    def __init__(self) -> None:
        self.inserted_tasks: list[TaskRecord] = []

    def insert_task(self, task: TaskRecord) -> None:
        self.inserted_tasks.append(task)


if __name__ == "__main__":
    unittest.main()
