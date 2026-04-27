from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID


DEFAULT_POSTGRES_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "db" / "task_schema.sql"
)


class CursorProtocol(Protocol):
    rowcount: int

    def execute(
        self,
        query: str,
        params: Sequence[object] | None = None,
    ) -> object:
        ...

    def fetchone(self) -> Sequence[object] | None:
        ...

    def fetchall(self) -> list[Sequence[object]]:
        ...

    def close(self) -> None:
        ...


class ConnectionProtocol(Protocol):
    def cursor(self) -> CursorProtocol:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...

    def close(self) -> None:
        ...


@dataclass(frozen=True)
class TaskRecord:
    id: UUID
    title: str
    category: str
    state: str
    priority: str
    deadline: datetime | None
    next_action: str | None
    created_at: datetime
    updated_at: datetime

    def as_storage_tuple(
        self,
    ) -> tuple[
        UUID,
        str,
        str,
        str,
        str,
        datetime | None,
        str | None,
        datetime,
        datetime,
    ]:
        return (
            self.id,
            self.title,
            self.category,
            self.state,
            self.priority,
            self.deadline,
            self.next_action,
            self.created_at,
            self.updated_at,
        )

    @classmethod
    def from_row(cls, row: Sequence[object]) -> TaskRecord:
        return cls(
            id=_coerce_uuid(row[0]),
            title=str(row[1]),
            category=str(row[2]),
            state=str(row[3]),
            priority=str(row[4]),
            deadline=_coerce_datetime(row[5]),
            next_action=_coerce_optional_string(row[6]),
            created_at=_coerce_required_datetime(row[7]),
            updated_at=_coerce_required_datetime(row[8]),
        )


class PostgresTaskStorage:
    def __init__(
        self,
        connection_factory: Callable[[], ConnectionProtocol],
        schema_path: str | Path = DEFAULT_POSTGRES_SCHEMA_PATH,
    ) -> None:
        self._connection_factory = connection_factory
        self._schema_path = Path(schema_path)

    @classmethod
    def from_dsn(
        cls,
        dsn: str,
        schema_path: str | Path = DEFAULT_POSTGRES_SCHEMA_PATH,
    ) -> PostgresTaskStorage:
        try:
            import psycopg
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "psycopg is required to use PostgresTaskStorage.from_dsn()."
            ) from error

        return cls(lambda: psycopg.connect(dsn), schema_path=schema_path)

    def initialize(self) -> None:
        schema_sql = self._schema_path.read_text(encoding="utf-8")
        with self._cursor() as cursor:
            for statement in _split_sql_statements(schema_sql):
                cursor.execute(statement)

    def insert_task(self, task: TaskRecord) -> None:
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tasks (
                    id,
                    title,
                    category,
                    state,
                    priority,
                    deadline,
                    next_action,
                    created_at,
                    updated_at
                )
                VALUES (
                    %s::uuid,
                    %s,
                    %s::task_category,
                    %s::task_state,
                    %s::task_priority,
                    %s::timestamptz,
                    %s,
                    %s::timestamptz,
                    %s::timestamptz
                )
                """,
                task.as_storage_tuple(),
            )

    def fetch_task(self, task_id: UUID) -> TaskRecord | None:
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    title,
                    category,
                    state,
                    priority,
                    deadline,
                    next_action,
                    created_at,
                    updated_at
                FROM tasks
                WHERE id = %s::uuid
                """,
                (task_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return TaskRecord.from_row(row)

    def update_task(self, task: TaskRecord) -> None:
        with self._cursor() as cursor:
            cursor.execute(
                """
                UPDATE tasks
                SET
                    title = %s,
                    category = %s::task_category,
                    state = %s::task_state,
                    priority = %s::task_priority,
                    deadline = %s::timestamptz,
                    next_action = %s,
                    created_at = %s::timestamptz,
                    updated_at = %s::timestamptz
                WHERE id = %s::uuid
                """,
                (
                    task.title,
                    task.category,
                    task.state,
                    task.priority,
                    task.deadline,
                    task.next_action,
                    task.created_at,
                    task.updated_at,
                    task.id,
                ),
            )
        if cursor.rowcount == 0:
            raise KeyError(f"Task not found: {task.id}")

    def delete_task(self, task_id: UUID) -> None:
        with self._cursor() as cursor:
            cursor.execute(
                "DELETE FROM tasks WHERE id = %s::uuid",
                (task_id,),
            )
        if cursor.rowcount == 0:
            raise KeyError(f"Task not found: {task_id}")

    def list_tasks(self) -> list[TaskRecord]:
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    title,
                    category,
                    state,
                    priority,
                    deadline,
                    next_action,
                    created_at,
                    updated_at
                FROM tasks
                ORDER BY created_at ASC
                """
            )
            rows = cursor.fetchall()
        return [TaskRecord.from_row(row) for row in rows]

    @contextmanager
    def _cursor(self) -> Iterator[CursorProtocol]:
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            yield cursor
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()


def _split_sql_statements(sql_text: str) -> list[str]:
    return [statement.strip() for statement in sql_text.split(";") if statement.strip()]


def _coerce_uuid(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise TypeError(f"Unsupported UUID value: {value!r}")


def _coerce_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"Unsupported datetime value: {value!r}")


def _coerce_required_datetime(value: object) -> datetime:
    result = _coerce_datetime(value)
    if result is None:
        raise TypeError("Expected datetime value, got None")
    return result


def _coerce_optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
