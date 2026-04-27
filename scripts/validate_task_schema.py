from __future__ import annotations

import re
import sys
from pathlib import Path


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "task_schema.sql"

EXPECTED_ENUMS = {
    "task_category": [
        "PROFESSIONAL",
        "PERSONAL",
        "HEALTH",
        "SPIRITUAL",
        "ADMIN",
        "FINANCE",
    ],
    "task_state": [
        "BACKLOG",
        "ACTIVE",
        "STALLED",
        "BLOCKED",
        "DORMANT",
        "DONE",
        "DROPPED",
    ],
    "task_priority": [
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    ],
}

EXPECTED_COLUMNS = [
    ("id", "UUID PRIMARY KEY"),
    ("title", "TEXT NOT NULL"),
    ("category", "task_category NOT NULL"),
    ("state", "task_state NOT NULL"),
    ("priority", "task_priority NOT NULL"),
    ("deadline", "TIMESTAMPTZ NULL"),
    ("next_action", "TEXT NULL"),
    ("created_at", "TIMESTAMPTZ NOT NULL"),
    ("updated_at", "TIMESTAMPTZ NOT NULL"),
]


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def extract_enum_values(schema_text: str, enum_name: str) -> list[str]:
    pattern = re.compile(
        rf"CREATE TYPE {enum_name} AS ENUM \((.*?)\);",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(schema_text)
    if not match:
        fail(f"Missing enum definition: {enum_name}")
    return re.findall(r"'([^']+)'", match.group(1))


def extract_columns(schema_text: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"CREATE TABLE tasks \((.*?)\);",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(schema_text)
    if not match:
        fail("Missing tasks table definition")

    body = match.group(1)
    raw_lines = [line.strip().rstrip(",") for line in body.splitlines() if line.strip()]
    columns: list[tuple[str, str]] = []

    for line in raw_lines:
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            fail(f"Invalid column definition: {line}")
        column_name, column_type = parts
        columns.append((column_name, column_type))

    return columns


def main() -> None:
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")

    for enum_name, expected_values in EXPECTED_ENUMS.items():
        values = extract_enum_values(schema_text, enum_name)
        if values != expected_values:
            fail(
                f"Enum mismatch for {enum_name}: expected {expected_values}, got {values}"
            )

    columns = extract_columns(schema_text)
    if columns != EXPECTED_COLUMNS:
        fail(f"Column mismatch: expected {EXPECTED_COLUMNS}, got {columns}")

    print("Task schema matches Phase 1 Step 1.1 requirements.")


if __name__ == "__main__":
    main()
