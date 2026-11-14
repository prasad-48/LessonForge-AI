from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class DatabaseManager:
    def __init__(self, db_path: str | None = None):
        if db_path == ":memory:":
            self.db_path = Path(__file__).resolve().parents[1] / ".lessonforge_memory.db"
        else:
            self.db_path = Path(db_path) if db_path else Path(__file__).resolve().parents[1] / "lessonforge.db"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.db_path))
        self._connection.row_factory = sqlite3.Row
        self._init_db()

    def _connect(self):
        return self._connection

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lesson_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    attempt_count INTEGER DEFAULT 0,
                    lesson_text TEXT,
                    evaluation_json TEXT,
                    failure_reasons TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def save_run(
        self,
        *,
        topic: str,
        status: str,
        retry_count: int,
        attempt_count: int,
        lesson_text: str = "",
        evaluation_json: str | None = None,
        failure_reasons: list[str] | str | None = None,
    ) -> int:
        if isinstance(failure_reasons, list):
            failure_reasons = json.dumps(failure_reasons)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO lesson_runs (
                    topic,
                    status,
                    retry_count,
                    attempt_count,
                    lesson_text,
                    evaluation_json,
                    failure_reasons
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    topic,
                    status,
                    retry_count,
                    attempt_count,
                    lesson_text,
                    evaluation_json,
                    failure_reasons,
                ),
            )
            return int(cursor.lastrowid)

    def update_run(
        self,
        run_id: int,
        *,
        status: str | None = None,
        lesson_text: str | None = None,
        evaluation_json: str | None = None,
        failure_reasons: list[str] | str | None = None,
        retry_count: int | None = None,
        attempt_count: int | None = None,
    ) -> None:
        if isinstance(failure_reasons, list):
            failure_reasons = json.dumps(failure_reasons)

        if status is None and lesson_text is None and evaluation_json is None and failure_reasons is None and retry_count is None and attempt_count is None:
            return

        assignments: list[str] = []
        values: list[Any] = []

        if status is not None:
            assignments.append("status = ?")
            values.append(status)
        if lesson_text is not None:
            assignments.append("lesson_text = ?")
            values.append(lesson_text)
        if evaluation_json is not None:
            assignments.append("evaluation_json = ?")
            values.append(evaluation_json)
        if failure_reasons is not None:
            assignments.append("failure_reasons = ?")
            values.append(failure_reasons)
        if retry_count is not None:
            assignments.append("retry_count = ?")
            values.append(retry_count)
        if attempt_count is not None:
            assignments.append("attempt_count = ?")
            values.append(attempt_count)

        values.append(run_id)

        with self._connect() as conn:
            conn.execute(
                f"UPDATE lesson_runs SET {', '.join(assignments)} WHERE id = ?",
                values,
            )

    def list_runs(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM lesson_runs ORDER BY created_at DESC"
            ).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            if record.get("evaluation_json"):
                record["evaluation"] = json.loads(record["evaluation_json"])
            else:
                record["evaluation"] = None
            if record.get("failure_reasons"):
                try:
                    record["failure_reasons"] = json.loads(record["failure_reasons"])
                except json.JSONDecodeError:
                    record["failure_reasons"] = [record["failure_reasons"]]
            else:
                record["failure_reasons"] = []
            results.append(record)
        return results

    def get_failure_guidance(self, limit: int = 5) -> str:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT failure_reasons
                FROM lesson_runs
                WHERE failure_reasons IS NOT NULL AND failure_reasons != ''
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        patterns: list[str] = []
        for row in rows:
            value = row["failure_reasons"]
            if not value:
                continue
            try:
                items = json.loads(value)
            except json.JSONDecodeError:
                items = [value]
            for item in items:
                if item and item not in patterns:
                    patterns.append(item)

        if not patterns:
            return "No prior failure patterns recorded yet. Focus on clarity, accuracy, and simple explanations."
        return "Avoid repeating these past failure patterns: " + "; ".join(patterns[:8])
