from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from lessonforge.config import get_groq_api_key
from lessonforge.db import DatabaseManager
from lessonforge.graph import run_lesson_workflow

DB = DatabaseManager()


st.set_page_config(page_title="LessonForge AI", page_icon="📚", layout="wide")

st.title("LessonForge AI")
st.caption("Self-Evaluating Lesson Content Generator for beginner-friendly learning")

st.sidebar.header("Project controls")
if not get_groq_api_key():
    st.sidebar.warning("Add GROQ_API_KEY to your .env file before generating lessons.")

with st.sidebar:
    topic = st.text_input("Lesson topic", value="Introduction to RAG")
    inject_error = st.checkbox("Enable deliberate error injection (first lesson only)")
    generate_clicked = st.button("Generate Lesson", type="primary")

if generate_clicked:
    if not get_groq_api_key():
        st.error("Cannot generate a lesson without a valid GROQ_API_KEY in .env.")
    else:
        with st.spinner("Generating and evaluating the lesson..."):
            result = run_lesson_workflow(topic, db=DB, inject_error=inject_error)
        st.session_state["latest_result"] = result

latest_result = st.session_state.get("latest_result")

if latest_result:
    status = latest_result.get("status", "pending")
    evaluation = latest_result.get("evaluation")
    lesson_text = latest_result.get("lesson") or ""

    st.subheader("Generation status")
    if status == "approved":
        st.success("The lesson was approved after passing all checks.")
    elif status == "rejected":
        st.error("The lesson was rejected after the retry limit was reached.")
    else:
        st.warning("The run is still pending or had a generation problem.")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Attempt count", latest_result.get("attempt_count", 0))
    with col2:
        st.metric("Retry count", latest_result.get("retry_count", 0))

    st.subheader("Evaluation results")
    if evaluation:
        criteria = evaluation.get("criteria", [])
        if criteria:
            for criterion in criteria:
                label = criterion.get("name", "Unknown")
                passed = bool(criterion.get("passed", False))
                st.markdown(f"**{label}:** {'✅ PASS' if passed else '❌ FAIL'}")
                if criterion.get("reason"):
                    st.caption(f"Reason: {criterion.get('reason')}")
                if criterion.get("improvement_suggestion"):
                    st.caption(f"Suggestion: {criterion.get('improvement_suggestion')}")
                if criterion.get("evidence"):
                    st.caption(f"Evidence: {criterion.get('evidence')}")
        else:
            st.info("No evaluation criteria were returned.")

        st.markdown(f"**Overall result:** {'✅ PASS' if evaluation.get('overall_pass') else '❌ FAIL'}")
        if evaluation.get("failure_reasons"):
            st.write("Failure reasons:")
            for reason in evaluation["failure_reasons"]:
                st.write(f"- {reason}")
        if evaluation.get("improvement_suggestions"):
            st.write("Improvement suggestions:")
            for item in evaluation["improvement_suggestions"]:
                st.write(f"- {item}")

    st.subheader("Final approved lesson")
    if lesson_text:
        st.markdown(lesson_text)
        st.download_button(
            label="Download lesson as Markdown",
            data=lesson_text,
            file_name=f"{topic.strip().replace(' ', '_').lower()}.md",
            mime="text/markdown",
        )
    else:
        st.info("No lesson is available yet.")

    rejection_log = {
        "topic": topic,
        "status": status,
        "attempt_count": latest_result.get("attempt_count", 0),
        "retry_count": latest_result.get("retry_count", 0),
        "failure_reasons": evaluation.get("failure_reasons", []) if evaluation else [],
        "evaluation": evaluation,
        "lesson": lesson_text,
    }
    st.download_button(
        label="Download rejection log as JSON",
        data=json.dumps(rejection_log, indent=2),
        file_name=f"{topic.strip().replace(' ', '_').lower()}_rejection_log.json",
        mime="application/json",
    )

st.subheader("Rejection history")
rejection_history = [run for run in DB.list_runs() if run.get("status") == "rejected"]
if rejection_history:
    history_df = pd.DataFrame(rejection_history)
    st.dataframe(history_df[["topic", "status", "attempt_count", "retry_count", "failure_reasons", "created_at"]])
else:
    st.info("No rejected runs yet.")

st.subheader("Previous run history")
all_runs = DB.list_runs()
if all_runs:
    runs_df = pd.DataFrame(all_runs)
    display_columns = ["topic", "status", "attempt_count", "retry_count", "created_at"]
    st.dataframe(runs_df[display_columns])
else:
    st.info("No previous runs found yet.")
