from lessonforge.graph import should_retry, calculate_next_attempt
from lessonforge.db import DatabaseManager


def test_should_retry_before_limit():
    assert should_retry(False, 1, 2) is True
    assert should_retry(False, 1, 1) is False


def test_calculate_next_attempt_after_failed_eval():
    assert calculate_next_attempt(0, False) == 1
    assert calculate_next_attempt(1, False) == 2


def test_db_persists_run_record(tmp_path):
    db_path = tmp_path / "lessonforge.db"
    db = DatabaseManager(str(db_path))

    db.save_run(
        topic="Introduction to RAG",
        status="pending",
        retry_count=0,
        attempt_count=1,
        lesson_text="Sample lesson",
    )

    runs = db.list_runs()
    assert len(runs) == 1
    assert runs[0]["topic"] == "Introduction to RAG"
    assert runs[0]["lesson_text"] == "Sample lesson"
