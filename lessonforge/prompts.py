from __future__ import annotations


def build_generator_prompt(topic: str, failure_guidance: str = "") -> str:
    guidance = f"\n\nPrior failure guidance: {failure_guidance}\n" if failure_guidance else ""
    return f"""
You are an expert lesson designer for Indian Grade 12 students.

Goal:
Write a standalone, beginner-friendly lesson on the topic: {topic}.

Audience:
- Indian 12th-grade student
- Limited English vocabulary
- Needs clear, simple explanation
- likely new to technical topics

Requirements:
1. Keep the language simple, clear, and easy to read.
2. Explain key ideas without unexplained jargon.
3. Include at least 2 practical examples.
4. Use simple examples from Indian school or daily life.
5. Include no false or unsupported claims.
6. Structure the lesson with a clear teaching flow.
7. Use Markdown headings, bullet points, and short paragraphs.
8. Do not include hidden technical assumptions.
9. Be accurate and grounded in real-world learning.
10. Keep the lesson self-contained and complete.

{guidance}

Output only the lesson content in Markdown.
"""


def build_evaluator_prompt(topic: str, lesson_text: str) -> str:
    return f"""
You are an independent evaluator. Evaluate the lesson below for a Grade 12 beginner audience.

Topic: {topic}

Evaluate strictly against these six criteria:
1. Accuracy and groundedness
2. Beginner-friendly language
3. Practical examples
4. No unexplained jargon
5. Coverage of key concepts
6. Logical teaching flow

Return a structured JSON object with this schema:
{{
  "overall_pass": true,
  "criteria": [
    {{
      "name": "Accuracy and groundedness",
      "passed": true,
      "evidence": "Quote or paraphrase from the lesson showing this criterion is met.",
      "reason": "Brief explanation if it fails; otherwise empty string.",
      "improvement_suggestion": "Suggested improvement if it fails; otherwise empty string."
    }}
  ],
  "failure_reasons": ["Clear failure reason if a criterion failed."],
  "evidence_summary": ["Relevant evidence from the lesson."],
  "improvement_suggestions": ["Suggested improvements for the next version."],
  "summary": "Short summary of the evaluation."
}}

Rules:
- overall_pass must be true only if all six criteria pass.
- If any criterion fails, include specific reason, evidence, and improvement suggestions.
- Never mark it as pass if there is any factual error or ambiguous explanation.
- Be strict and realistic.
- Use only evidence from the lesson itself.

Lesson to evaluate:

{lesson_text}
"""
