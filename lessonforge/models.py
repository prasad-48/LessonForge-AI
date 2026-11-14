from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class CriterionResult(BaseModel):
    name: str
    passed: bool
    evidence: str = ""
    reason: str = ""
    improvement_suggestion: str = ""


class EvaluationResult(BaseModel):
    overall_pass: bool
    criteria: List[CriterionResult] = Field(default_factory=list)
    failure_reasons: List[str] = Field(default_factory=list)
    evidence_summary: List[str] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)
    summary: str = ""


class RunResult(BaseModel):
    topic: str
    lesson: str
    status: str
    attempt_count: int
    retry_count: int
    evaluation: EvaluationResult | None = None
    rejection_reasons: List[str] = Field(default_factory=list)
