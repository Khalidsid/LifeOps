from __future__ import annotations

import importlib.util
import os
import unittest

from lifeops import PostgresTaskStorage, TaskModule


TEST_DSN = os.environ.get("LIFEOPS_TEST_DSN")
PSYCOPG_AVAILABLE = importlib.util.find_spec("psycopg") is not None


@unittest.skipUnless(
    TEST_DSN and PSYCOPG_AVAILABLE,
    "requires LIFEOPS_TEST_DSN and psycopg",
)
class LivePostgresTaskModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dsn = TEST_DSN
        cls.storage = PostgresTaskStorage.from_dsn(cls.dsn)
        cls.storage.initialize()
        cls.module = TaskModule(cls.storage)

    def setUp(self) -> None:
        import psycopg

        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM tasks")

    def test_create_task_persists_defaults_against_live_postgres(self) -> None:
        task = self.module.create_task("Refine research question", "PROFESSIONAL")

        stored_task = self.storage.fetch_task(task.id)

        self.assertEqual(stored_task, task)
        self.assertEqual(task.state, "BACKLOG")
        self.assertEqual(task.priority, "MEDIUM")
        self.assertIsNone(task.deadline)
        self.assertIsNone(task.next_action)
        self.assertEqual(task.created_at, task.updated_at)


if __name__ == "__main__":
    unittest.main()
