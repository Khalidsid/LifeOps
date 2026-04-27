from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import UUID

from lifeops import PostgresTaskStorage, TaskRecord


class PostgresTaskStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = FakePostgresBackend()
        self.storage = PostgresTaskStorage(self.backend.connect)
        self.storage.initialize()
        self.base_time = datetime(2026, 4, 27, 12, 0, tzinfo=timezone.utc)
        self.task = TaskRecord(
            id=UUID("12345678-1234-5678-1234-567812345678"),
            title="Refine research question",
            category="PROFESSIONAL",
            state="BACKLOG",
            priority="HIGH",
            deadline=self.base_time + timedelta(days=3),
            next_action="Write 3 bullet points",
            created_at=self.base_time,
            updated_at=self.base_time,
        )

    def test_initialize_executes_canonical_postgres_schema(self) -> None:
        self.assertTrue(
            any(
                "CREATE TYPE task_category AS ENUM" in statement
                for statement in self.backend.executed_statements
            )
        )
        self.assertTrue(
            any(
                "CREATE TABLE tasks" in statement
                for statement in self.backend.executed_statements
            )
        )

    def test_insert_and_fetch_task(self) -> None:
        self.storage.insert_task(self.task)

        stored_task = self.storage.fetch_task(self.task.id)

        self.assertEqual(stored_task, self.task)

    def test_update_task_replaces_stored_values(self) -> None:
        self.storage.insert_task(self.task)
        updated_task = replace(
            self.task,
            title="Refine LifeOps research question",
            state="ACTIVE",
            next_action="Draft the first paragraph",
            updated_at=self.base_time + timedelta(hours=2),
        )

        self.storage.update_task(updated_task)

        self.assertEqual(self.storage.fetch_task(self.task.id), updated_task)

    def test_delete_task_removes_record(self) -> None:
        self.storage.insert_task(self.task)

        self.storage.delete_task(self.task.id)

        self.assertIsNone(self.storage.fetch_task(self.task.id))

    def test_list_tasks_returns_all_records_in_created_order(self) -> None:
        earlier_task = replace(
            self.task,
            id=UUID("aaaaaaaa-1234-5678-1234-567812345678"),
            title="Earlier task",
            created_at=self.base_time - timedelta(hours=1),
            updated_at=self.base_time - timedelta(hours=1),
        )
        later_task = replace(
            self.task,
            id=UUID("bbbbbbbb-1234-5678-1234-567812345678"),
            title="Later task",
            created_at=self.base_time + timedelta(hours=1),
            updated_at=self.base_time + timedelta(hours=1),
        )

        self.storage.insert_task(later_task)
        self.storage.insert_task(earlier_task)

        self.assertEqual(self.storage.list_tasks(), [earlier_task, later_task])

    def test_data_persists_across_storage_instances(self) -> None:
        self.storage.insert_task(self.task)
        second_storage = PostgresTaskStorage(self.backend.connect)

        stored_task = second_storage.fetch_task(self.task.id)

        self.assertEqual(stored_task, self.task)

    def test_from_dsn_returns_storage_or_explicit_driver_error(self) -> None:
        try:
            storage = PostgresTaskStorage.from_dsn(
                "postgresql://lifeops:test@localhost/lifeops"
            )
        except RuntimeError as error:
            self.assertIn("psycopg", str(error))
        else:
            self.assertIsInstance(storage, PostgresTaskStorage)


class FakePostgresBackend:
    def __init__(self) -> None:
        self.rows: dict[str, tuple[object, ...]] = {}
        self.executed_statements: list[str] = []

    def connect(self) -> FakePostgresConnection:
        return FakePostgresConnection(self)


class FakePostgresConnection:
    def __init__(self, backend: FakePostgresBackend) -> None:
        self.backend = backend

    def cursor(self) -> FakePostgresCursor:
        return FakePostgresCursor(self.backend)

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


class FakePostgresCursor:
    def __init__(self, backend: FakePostgresBackend) -> None:
        self.backend = backend
        self.rowcount = 0
        self._one: tuple[object, ...] | None = None
        self._many: list[tuple[object, ...]] = []

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> object:
        normalized = " ".join(query.split()).upper()
        self.backend.executed_statements.append(query.strip())
        self.rowcount = 0
        self._one = None
        self._many = []

        if normalized.startswith("CREATE TYPE") or normalized.startswith("CREATE TABLE"):
            return self

        if normalized.startswith("INSERT INTO TASKS"):
            assert params is not None
            self.backend.rows[str(params[0])] = tuple(params)
            self.rowcount = 1
            return self

        if normalized.startswith("SELECT") and "WHERE ID =" in normalized:
            assert params is not None
            row = self.backend.rows.get(str(params[0]))
            self._one = row
            self.rowcount = 0 if row is None else 1
            return self

        if normalized.startswith("SELECT") and "ORDER BY CREATED_AT ASC" in normalized:
            self._many = sorted(
                self.backend.rows.values(),
                key=lambda row: row[7],
            )
            self.rowcount = len(self._many)
            return self

        if normalized.startswith("UPDATE TASKS"):
            assert params is not None
            task_id = str(params[-1])
            if task_id in self.backend.rows:
                self.backend.rows[task_id] = (
                    params[-1],
                    params[0],
                    params[1],
                    params[2],
                    params[3],
                    params[4],
                    params[5],
                    params[6],
                    params[7],
                )
                self.rowcount = 1
            return self

        if normalized.startswith("DELETE FROM TASKS"):
            assert params is not None
            task_id = str(params[0])
            if task_id in self.backend.rows:
                del self.backend.rows[task_id]
                self.rowcount = 1
            return self

        raise AssertionError(f"Unexpected query: {query}")

    def fetchone(self) -> tuple[object, ...] | None:
        return self._one

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._many

    def close(self) -> None:
        return None


if __name__ == "__main__":
    unittest.main()
