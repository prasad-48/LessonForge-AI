from __future__ import annotations

import json
from typing import Any

from langgraph.graph import END, StateGraph

from .db import DatabaseManager
from .llm import LLMError, evaluate_lesson_text, generate_lesson_text
from .models import EvaluationResult

MAX_RETRIES = 2


def should_retry(passed_or_result: bool | EvaluationResult | None, retry_count: int, max_retries: int = MAX_RETRIES) -> bool:
    if passed_or_result is None:
        return False
    if isinstance(passed_or_result, EvaluationResult):
        return (not passed_or_result.overall_pass) and retry_count < max_retries
    return (not bool(passed_or_result)) and retry_count < max_retries


def calculate_next_attempt(retry_count: int, passed: bool) -> int:
    return retry_count + 1 if not passed else retry_count


def _build_failure_result(message: str) -> EvaluationResult:
    return EvaluationResult(
        overall_pass=False,
        criteria=[],
        failure_reasons=[message],
        evidence_summary=["The model or evaluation step failed before a valid lesson was approved."],
        improvement_suggestions=["Retry with a simpler topic or check the Groq API key and connectivity."],
        summary="The evaluation could not complete successfully.",
    )


def generate_lesson_node(state: dict[str, Any]) -> dict[str, Any]:
    db: DatabaseManager = state["db"]
    topic = state["topic"]
    attempt_count = state.get("attempt_count", 0) + 1
    state["attempt_count"] = attempt_count
    state["retry_count"] = state.get("retry_count", 0)
    state["failure_guidance"] = db.get_failure_guidance() if state.get("retry_count", 0) > 0 else ""

    inject_error = bool(state.get("inject_error")) and attempt_count == 1
    try:
        lesson_text = generate_lesson_text(
            topic,
            failure_guidance=state["failure_guidance"],
            inject_error=inject_error,
        )
        state["lesson_text"] = lesson_text
        state["error_message"] = ""

        run_id = state.get("run_id")
        if run_id is None:
            run_id = db.save_run(
                topic=topic,
                status="generated",
                retry_count=state["retry_count"],
                attempt_count=attempt_count,
                lesson_text=lesson_text,
            )
            state["run_id"] = run_id
        else:
            db.update_run(
                run_id,
                status="generated",
                retry_count=state["retry_count"],
                attempt_count=attempt_count,
                lesson_text=lesson_text,
            )
        return state
    except LLMError as exc:
        state["lesson_text"] = ""
        state["error_message"] = str(exc)
        run_id = state.get("run_id")
        if run_id is None:
            run_id = db.save_run(
                topic=topic,
                status="error",
                retry_count=state["retry_count"],
                attempt_count=attempt_count,
                lesson_text="",
                failure_reasons=[str(exc)],
            )
            state["run_id"] = run_id
        else:
            db.update_run(
                run_id,
                status="error",
                retry_count=state["retry_count"],
                attempt_count=attempt_count,
                lesson_text="",
                failure_reasons=[str(exc)],
            )
        state["evaluation"] = _build_failure_result(str(exc))
        return state


def evaluate_lesson_node(state: dict[str, Any]) -> dict[str, Any]:
    run_id = state.get("run_id")
    db: DatabaseManager = state["db"]
    topic = state["topic"]
    lesson_text = state.get("lesson_text", "")

    try:
        evaluation = evaluate_lesson_text(topic, lesson_text)
    except LLMError as exc:
        evaluation = _build_failure_result(str(exc))

    if len(evaluation.criteria) != 6:
        evaluation = _build_failure_result(
            f"Evaluation returned {len(evaluation.criteria)} criteria instead of 6."
        )
    elif any(not criterion.passed for criterion in evaluation.criteria):
        if not evaluation.failure_reasons:
            evaluation.failure_reasons = ["At least one required criterion failed."]
        if not evaluation.improvement_suggestions:
            evaluation.improvement_suggestions = [
                "Review the lesson for factual accuracy, language simplicity, and teaching flow before retrying."
            ]

    state["evaluation"] = evaluation
    if run_id is not None:
        db.update_run(
            run_id,
            status="evaluated",
            evaluation_json=json.dumps(evaluation.model_dump()),
            failure_reasons=evaluation.failure_reasons,
            retry_count=state.get("retry_count", 0),
            attempt_count=state.get("attempt_count", 0),
        )
    return state


def prepare_retry_node(state: dict[str, Any]) -> dict[str, Any]:
    state["retry_count"] = state.get("retry_count", 0) + 1
    return state


def route_decision(state: dict[str, Any]) -> str:
    evaluation: EvaluationResult | None = state.get("evaluation")
    db: DatabaseManager = state["db"]
    run_id = state.get("run_id")

    if evaluation is None:
        if run_id is not None:
            db.update_run(run_id, status="rejected", failure_reasons=["No valid evaluation was produced."])
        return "rejected"

    if evaluation.overall_pass:
        if run_id is not None:
            db.update_run(run_id, status="approved", evaluation_json=json.dumps(evaluation.model_dump()), failure_reasons=evaluation.failure_reasons)
        state["final_status"] = "approved"
        return "approved"

    if state.get("retry_count", 0) >= MAX_RETRIES:
        if run_id is not None:
            db.update_run(run_id, status="rejected", evaluation_json=json.dumps(evaluation.model_dump()), failure_reasons=evaluation.failure_reasons)
        state["final_status"] = "rejected"
        return "rejected"

    state["final_status"] = "retry"
    return "prepare_retry"


def build_graph(db: DatabaseManager | None = None):
    workflow = StateGraph(dict)
    workflow.add_node("generate_lesson", generate_lesson_node)
    workflow.add_node("evaluate_lesson", evaluate_lesson_node)
    workflow.add_node("prepare_retry", prepare_retry_node)
    workflow.set_entry_point("generate_lesson")
    workflow.add_edge("generate_lesson", "evaluate_lesson")
    workflow.add_conditional_edges(
        "evaluate_lesson",
        route_decision,
        {
            "prepare_retry": "prepare_retry",
            "approved": END,
            "rejected": END,
        },
    )
    workflow.add_edge("prepare_retry", "generate_lesson")
    return workflow.compile()


def run_lesson_workflow(topic: str, db: DatabaseManager | None = None, inject_error: bool = False) -> dict[str, Any]:
    db = db or DatabaseManager()
    initial_state = {
        "topic": (topic or "Introduction to RAG").strip() or "Introduction to RAG",
        "db": db,
        "attempt_count": 0,
        "retry_count": 0,
        "inject_error": inject_error,
        "status": "pending",
    }
    graph = build_graph(db)
    final_state = graph.invoke(initial_state)

    runs = db.list_runs()
    if runs:
        latest_run = runs[0]
        latest_status = latest_run.get("status")
        if latest_status in {"approved", "rejected"}:
            final_state["final_status"] = latest_status

    if final_state.get("final_status") is None:
        evaluation = final_state.get("evaluation")
        if isinstance(evaluation, dict):
            final_state["final_status"] = "approved" if evaluation.get("overall_pass") else "rejected"
        elif evaluation is not None:
            final_state["final_status"] = "approved" if getattr(evaluation, "overall_pass", False) else "rejected"
        else:
            final_state["final_status"] = "rejected"

    final_state.pop("db", None)
    final_state.pop("failure_guidance", None)
    final_state.pop("error_message", None)

    evaluation = final_state.get("evaluation")
    if isinstance(evaluation, EvaluationResult):
        final_state["evaluation"] = evaluation.model_dump()
    else:
        final_state["evaluation"] = evaluation or {}

    final_state["status"] = final_state.get("final_status", "rejected")
    final_state["lesson"] = final_state.get("lesson_text", "")
    final_state["topic"] = final_state.get("topic", topic)
    return final_state
