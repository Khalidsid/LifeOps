from __future__ import annotations

import importlib.util
import os
import unittest
from datetime import datetime, timedelta, timezone
from uuid import UUID

from lifeops import PostgresTaskStorage, TaskRecord


TEST_DSN = os.environ.get("LIFEOPS_TEST_DSN")
PSYCOPG_AVAILABLE = importlib.util.find_spec("psycopg") is not None


@unittest.skipUnless(
    TEST_DSN and PSYCOPG_AVAILABLE,
    "requires LIFEOPS_TEST_DSN and psycopg",
)
class LivePostgresTaskStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dsn = TEST_DSN
        cls._reset_database_objects()
        cls.storage = PostgresTaskStorage.from_dsn(cls.dsn)
        cls.storage.initialize()
        cls.base_time = datetime(2026, 4, 27, 12, 0, tzinfo=timezone.utc)
        cls.task = TaskRecord(
            id=UUID("12345678-1234-5678-1234-567812345678"),
            title="Refine research question",
            category="PROFESSIONAL",
            state="BACKLOG",
            priority="HIGH",
            deadline=cls.base_time + timedelta(days=3),
            next_action="Write 3 bullet points",
            created_at=cls.base_time,
            updated_at=cls.base_time,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._reset_database_objects()

    def setUp(self) -> None:
        self._delete_tasks()

    def test_initialize_creates_live_schema_objects(self) -> None:
        import psycopg

        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT typname
                    FROM pg_type
                    WHERE typname IN ('task_category', 'task_state', 'task_priority')
                    ORDER BY typname ASC
                    """
                )
                enum_names = [row[0] for row in cursor.fetchall()]
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'tasks'
                    ORDER BY ordinal_position ASC
                    """
                )
                column_names = [row[0] for row in cursor.fetchall()]

        self.assertEqual(
            enum_names,
            ["task_category", "task_priority", "task_state"],
        )
        self.assertEqual(
            column_names,
            [
                "id",
                "title",
                "category",
                "state",
                "priority",
                "deadline",
                "next_action",
                "created_at",
                "updated_at",
            ],
        )

    def test_insert_and_fetch_task_against_live_postgres(self) -> None:
        self.storage.insert_task(self.task)

        stored_task = self.storage.fetch_task(self.task.id)

        self.assertEqual(stored_task, self.task)

    def test_data_persists_across_storage_instances_against_live_postgres(self) -> None:
        self.storage.insert_task(self.task)
        second_storage = PostgresTaskStorage.from_dsn(self.dsn)

        stored_task = second_storage.fetch_task(self.task.id)

        self.assertEqual(stored_task, self.task)

    @classmethod
    def _delete_tasks(cls) -> None:
        import psycopg

        with psycopg.connect(cls.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM tasks")

    @classmethod
    def _reset_database_objects(cls) -> None:
        import psycopg

        with psycopg.connect(cls.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DROP TABLE IF EXISTS tasks")
                cursor.execute("DROP TYPE IF EXISTS task_priority")
                cursor.execute("DROP TYPE IF EXISTS task_state")
                cursor.execute("DROP TYPE IF EXISTS task_category")


if __name__ == "__main__":
    unittest.main()
