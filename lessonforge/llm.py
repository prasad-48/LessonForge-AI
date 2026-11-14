from __future__ import annotations

import json
from typing import Iterable

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from .config import get_groq_api_key, get_groq_model
from .models import EvaluationResult
from .prompts import build_evaluator_prompt, build_generator_prompt


class LLMError(RuntimeError):
    pass


def _build_llm(model_name: str | None = None, temperature: float = 0.3) -> ChatOpenAI:
    if model_name is None:
        model_name = get_groq_model()
    api_key = get_groq_api_key()
    if not api_key:
        raise LLMError("Missing GROQ_API_KEY in .env")
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        timeout=60,
        max_retries=1,
    )


def inject_error_into_lesson(lesson_text: str) -> str:
    marker = "\n\n> Demonstration note: This sentence is intentionally incorrect to test evaluation safeguards.\n"
    injected = "RAG stands for Random Access Generation and works only with one memory layer."
    if "RAG" in lesson_text and "Random Access Generation" not in lesson_text:
        return lesson_text.replace("RAG", "RAG", 1) + marker + injected + "\n"
    return lesson_text + marker + injected + "\n"


def generate_lesson_text(topic: str, failure_guidance: str = "", inject_error: bool = False) -> str:
    try:
        llm = _build_llm()
        prompt = build_generator_prompt(topic, failure_guidance)
        response = llm.invoke([HumanMessage(content=prompt)])
        lesson = (response.content or "").strip()
        if not lesson:
            raise LLMError("The model returned an empty lesson.")
        if inject_error:
            lesson = inject_error_into_lesson(lesson)
        return lesson
    except Exception as exc:  # pragma: no cover - broad to ensure app resilience
        raise LLMError(f"Lesson generation failed: {exc}") from exc


def _parse_evaluation_json(json_str: str) -> EvaluationResult:
    """Parse evaluation JSON string into EvaluationResult, handling markdown code blocks."""
    import re
    # Extract JSON from markdown code blocks if present
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', json_str, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        # Try to find JSON object in the string
        match = re.search(r'(\{.*\})', json_str, re.DOTALL)
        if match:
            json_str = match.group(1)
    data = json.loads(json_str)
    return EvaluationResult(**data)


def evaluate_lesson_text(topic: str, lesson_text: str) -> EvaluationResult:
    try:
        llm = _build_llm(temperature=0.1)
        prompt = build_evaluator_prompt(topic, lesson_text)
        
        # Try structured output first
        try:
            structured_llm = llm.with_structured_output(EvaluationResult)
            result = structured_llm.invoke([HumanMessage(content=prompt)])
            if isinstance(result, EvaluationResult) and result.criteria:
                return result
        except Exception:
            pass  # Fall back to manual JSON parsing
        
        # Fallback: manual JSON parsing
        response = llm.invoke([HumanMessage(content=prompt)])
        content = (response.content or "").strip()
        if not content:
            raise LLMError("The model returned an empty evaluation.")
        
        result = _parse_evaluation_json(content)
        
        if not isinstance(result, EvaluationResult):
            raise LLMError("LLM returned an unexpected evaluation structure.")
        if not result.criteria:
            raise LLMError("Evaluation returned no criteria.")
        if len(result.criteria) != 6:
            raise LLMError(f"Evaluation returned {len(result.criteria)} criteria, expected 6.")
        return result
    except (ValidationError, TypeError, ValueError, LLMError) as exc:
        raise LLMError(f"Lesson evaluation failed: {exc}") from exc
    except Exception as exc:  # pragma: no cover
        raise LLMError(f"Lesson evaluation failed unexpectedly: {exc}") from exc
