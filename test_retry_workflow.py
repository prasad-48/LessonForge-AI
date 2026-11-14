#!/usr/bin/env python
"""Retry workflow validation tests with mocked responses."""

import json
from unittest.mock import patch, MagicMock
from lessonforge.graph import run_lesson_workflow, build_graph, MAX_RETRIES
from lessonforge.db import DatabaseManager
from lessonforge.models import EvaluationResult, CriterionResult


def create_mock_evaluation(overall_pass: bool, criteria_passed: list = None):
    """Create a mock EvaluationResult."""
    if criteria_passed is None:
        criteria_passed = [overall_pass] * 6
    
    criteria = []
    criterion_names = [
        "Accuracy and groundedness",
        "Beginner-friendly language", 
        "Practical examples",
        "No unexplained jargon",
        "Coverage of key concepts",
        "Logical teaching flow"
    ]
    
    for i, name in enumerate(criterion_names):
        passed = criteria_passed[i] if i < len(criteria_passed) else overall_pass
        criteria.append(CriterionResult(
            name=name,
            passed=passed,
            evidence="Mock evidence" if passed else "",
            reason="Mock failure reason" if not passed else "",
            improvement_suggestion="Mock suggestion" if not passed else ""
        ))
    
    return EvaluationResult(
        overall_pass=overall_pass,
        criteria=criteria,
        failure_reasons=["Mock failure"] if not overall_pass else [],
        evidence_summary=["Mock evidence"],
        improvement_suggestions=["Mock suggestion"] if not overall_pass else [],
        summary="Mock evaluation"
    )


def test_first_attempt_passes():
    """Test: First attempt passes -> approved."""
    print("\n=== Test 1: First attempt passes ===")
    
    db = DatabaseManager(":memory:")
    # Initialize the database by saving a dummy run
    db.save_run(topic="init", status="init", retry_count=0, attempt_count=0)
    
    # Clear any existing runs
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.execute("DELETE FROM lesson_runs")
    conn.commit()
    conn.close()
    
    mock_eval = create_mock_evaluation(True)
    
    with patch('lessonforge.graph.evaluate_lesson_text', return_value=mock_eval):
        with patch('lessonforge.graph.generate_lesson_text', return_value="Mock lesson content"):
            result = run_lesson_workflow("Test Topic", db=db, inject_error=False)
    
    print(f"Status: {result.get('status')}")
    print(f"Attempt count: {result.get('attempt_count')}")
    print(f"Retry count: {result.get('retry_count')}")
    print(f"Overall pass: {result.get('evaluation', {}).get('overall_pass')}")
    
    # Verify database has exactly one record
    runs = db.list_runs()
    print(f"Database records: {len(runs)}")
    if runs:
        r = runs[0]
        print(f"  Status: {r['status']}, Attempts: {r['attempt_count']}, Retries: {r['retry_count']}")
    
    assert result.get('status') == 'approved', f"Expected approved, got {result.get('status')}"
    assert result.get('attempt_count') == 1, f"Expected 1 attempt, got {result.get('attempt_count')}"
    assert result.get('retry_count') == 0, f"Expected 0 retries, got {result.get('retry_count')}"
    assert len(runs) == 1, f"Expected 1 DB record, got {len(runs)}"
    assert runs[0]['status'] == 'approved', f"Expected approved in DB, got {runs[0]['status']}"
    
    print("✅ PASS")
    return True


def test_first_fails_second_passes():
    """Test: First attempt fails, second passes -> approved after one retry."""
    print("\n=== Test 2: First fails, second passes ===")
    
    db = DatabaseManager(":memory:")
    db.save_run(topic="init", status="init", retry_count=0, attempt_count=0)
    
    # Clear any existing runs
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.execute("DELETE FROM lesson_runs")
    conn.commit()
    conn.close()
    
    eval_fail = create_mock_evaluation(False, [False]*6)
    eval_pass = create_mock_evaluation(True, [True]*6)
    
    eval_call_count = [0]
    def mock_evaluate(topic, lesson):
        eval_call_count[0] += 1
        return eval_fail if eval_call_count[0] == 1 else eval_pass
    
    with patch('lessonforge.graph.evaluate_lesson_text', side_effect=mock_evaluate):
        with patch('lessonforge.graph.generate_lesson_text', return_value="Mock lesson content"):
            result = run_lesson_workflow("Test Topic", db=db, inject_error=False)
    
    print(f"Status: {result.get('status')}")
    print(f"Attempt count: {result.get('attempt_count')}")
    print(f"Retry count: {result.get('retry_count')}")
    print(f"Evaluation calls: {eval_call_count[0]}")
    
    # Verify database has exactly one record
    runs = db.list_runs()
    print(f"Database records: {len(runs)}")
    if runs:
        r = runs[0]
        print(f"  Status: {r['status']}, Attempts: {r['attempt_count']}, Retries: {r['retry_count']}")
    
    assert result.get('status') == 'approved', f"Expected approved, got {result.get('status')}"
    assert result.get('attempt_count') == 2, f"Expected 2 attempts, got {result.get('attempt_count')}"
    assert result.get('retry_count') == 1, f"Expected 1 retry, got {result.get('retry_count')}"
    assert len(runs) == 1, f"Expected 1 DB record, got {len(runs)}"
    assert runs[0]['status'] == 'approved', f"Expected approved in DB, got {runs[0]['status']}"
    assert runs[0]['attempt_count'] == 2, f"Expected 2 attempts in DB, got {runs[0]['attempt_count']}"
    assert runs[0]['retry_count'] == 1, f"Expected 1 retry in DB, got {runs[0]['retry_count']}"
    
    print("✅ PASS")
    return True


def test_all_three_fail():
    """Test: All three attempts fail -> rejected after 3 attempts, retry_count=2."""
    print("\n=== Test 3: All three attempts fail ===")
    
    db = DatabaseManager(":memory:")
    db.save_run(topic="init", status="init", retry_count=0, attempt_count=0)
    
    # Clear any existing runs
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.execute("DELETE FROM lesson_runs")
    conn.commit()
    conn.close()
    
    eval_fail = create_mock_evaluation(False, [False]*6)
    
    with patch('lessonforge.graph.evaluate_lesson_text', return_value=eval_fail):
        with patch('lessonforge.graph.generate_lesson_text', return_value="Mock lesson content"):
            result = run_lesson_workflow("Test Topic", db=db, inject_error=False)
    
    print(f"Status: {result.get('status')}")
    print(f"Attempt count: {result.get('attempt_count')}")
    print(f"Retry count: {result.get('retry_count')}")
    
    # Verify database has exactly one record
    runs = db.list_runs()
    print(f"Database records: {len(runs)}")
    if runs:
        r = runs[0]
        print(f"  Status: {r['status']}, Attempts: {r['attempt_count']}, Retries: {r['retry_count']}")
    
    assert result.get('status') == 'rejected', f"Expected rejected, got {result.get('status')}"
    assert result.get('attempt_count') == 3, f"Expected 3 attempts, got {result.get('attempt_count')}"
    assert result.get('retry_count') == 2, f"Expected 2 retries, got {result.get('retry_count')}"
    assert len(runs) == 1, f"Expected 1 DB record, got {len(runs)}"
    assert runs[0]['status'] == 'rejected', f"Expected rejected in DB, got {runs[0]['status']}"
    assert runs[0]['attempt_count'] == 3, f"Expected 3 attempts in DB, got {runs[0]['attempt_count']}"
    assert runs[0]['retry_count'] == 2, f"Expected 2 retries in DB, got {runs[0]['retry_count']}"
    
    print("✅ PASS")
    return True


def test_incomplete_evaluation():
    """Test: Incomplete evaluation (fewer than 6 criteria) -> treated as failure."""
    print("\n=== Test 4: Incomplete evaluation (3 criteria) ===")
    
    db = DatabaseManager(":memory:")
    db.save_run(topic="init", status="init", retry_count=0, attempt_count=0)
    
    # Clear any existing runs
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.execute("DELETE FROM lesson_runs")
    conn.commit()
    conn.close()
    
    # Create evaluation with only 3 criteria
    criteria = []
    for name in ["Accuracy and groundedness", "Beginner-friendly language", "Practical examples"]:
        criteria.append(CriterionResult(
            name=name,
            passed=True,
            evidence="Mock evidence",
            reason="",
            improvement_suggestion=""
        ))
    
    incomplete_eval = EvaluationResult(
        overall_pass=True,
        criteria=criteria,
        failure_reasons=[],
        evidence_summary=["Mock evidence"],
        improvement_suggestions=[],
        summary="Mock evaluation"
    )
    
    with patch('lessonforge.graph.evaluate_lesson_text', return_value=incomplete_eval):
        with patch('lessonforge.graph.generate_lesson_text', return_value="Mock lesson content"):
            result = run_lesson_workflow("Test Topic", db=db, inject_error=False)
    
    print(f"Status: {result.get('status')}")
    print(f"Attempt count: {result.get('attempt_count')}")
    print(f"Retry count: {result.get('retry_count')}")
    print(f"Criteria count in result: {len(result.get('evaluation', {}).get('criteria', []))}")
    
    # Should be treated as failure and retry (up to max retries)
    runs = db.list_runs()
    print(f"Database records: {len(runs)}")
    
    # The workflow should retry and eventually reject
    assert result.get('status') == 'rejected', f"Expected rejected, got {result.get('status')}"
    assert result.get('attempt_count') == 3, f"Expected 3 attempts, got {result.get('attempt_count')}"
    assert result.get('retry_count') == 2, f"Expected 2 retries, got {result.get('retry_count')}"
    assert len(runs) == 1, f"Expected 1 DB record, got {len(runs)}"
    
    print("✅ PASS")
    return True


def test_evaluator_feedback_passed_to_generator():
    """Test: Evaluator feedback is passed into next generation attempt."""
    print("\n=== Test 5: Evaluator feedback passed to generator ===")
    
    db = DatabaseManager(":memory:")
    db.save_run(topic="init", status="init", retry_count=0, attempt_count=0)
    
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.execute("DELETE FROM lesson_runs")
    conn.commit()
    conn.close()
    
    eval_fail = create_mock_evaluation(False, [False]*6)
    eval_pass = create_mock_evaluation(True, [True]*6)
    
    eval_call_count = [0]
    gen_call_count = [0]
    captured_guidance = []
    
    def mock_evaluate(topic, lesson):
        eval_call_count[0] += 1
        return eval_fail if eval_call_count[0] == 1 else eval_pass
    
    def mock_generate(topic, failure_guidance="", inject_error=False):
        gen_call_count[0] += 1
        captured_guidance.append(failure_guidance)
        return "Mock lesson content"
    
    with patch('lessonforge.graph.evaluate_lesson_text', side_effect=mock_evaluate):
        with patch('lessonforge.graph.generate_lesson_text', side_effect=mock_generate):
            result = run_lesson_workflow("Test Topic", db=db, inject_error=False)
    
    print(f"Generation calls: {gen_call_count[0]}")
    print(f"Evaluation calls: {eval_call_count[0]}")
    print(f"Failure guidance captured on 2nd attempt: {bool(captured_guidance[1]) if len(captured_guidance) > 1 else False}")
    
    # Verify guidance was passed
    assert len(captured_guidance) >= 2, "Generator should be called twice"
    assert captured_guidance[0] == "", "First attempt should have empty guidance"
    assert captured_guidance[1] != "", "Second attempt should have failure guidance"
    
    runs = db.list_runs()
    assert len(runs) == 1, f"Expected 1 DB record, got {len(runs)}"
    
    print("✅ PASS")
    return True


def run_all_tests():
    """Run all validation tests."""
    print("=" * 60)
    print("RETRY WORKFLOW VALIDATION TESTS")
    print("=" * 60)
    
    tests = [
        test_first_attempt_passes,
        test_first_fails_second_passes,
        test_all_three_fail,
        test_incomplete_evaluation,
        test_evaluator_feedback_passed_to_generator,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"❌ FAIL: {e}")
            import traceback
            traceback.print_exc()
            results.append((test.__name__, False))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_pass = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
        if not result:
            all_pass = False
    
    print(f"\nOverall: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
    return all_pass


if __name__ == "__main__":
    run_all_tests()